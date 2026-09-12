from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
import os
from pydantic import BaseModel
from app.models.joueur import Joueur
from app.services import stockage_logo, stockage_photo
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import require_roles, verifier_scope_club
from app.database import get_db
from app.models.club import Club
from app.models.enums import ActionAudit, RoleUtilisateur
from app.models.match import Match
from app.models.user import User
from app.schemas.competition import ClubCreate, ClubOut, ClubUpdate
from app.services.audit import log_audit
from app.services.stockage_logo import DepotRefus, supprimer_objet, uploader_logo
from app.services.stockage_photo import DepotRefus as PhotoDepotRefus, uploader_photo

from sqlalchemy import func, select
from app.models.photo import Photo, StatutPhoto
from app.schemas.photo import PhotoOut
from app.models.staff import Staff
from app.schemas.staff import StaffCreate, StaffOut
from app.schemas.staff import StaffUpdate
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/clubs", tags=["Clubs"])


async def _coach_noms(db: AsyncSession, club_ids: list[int]) -> dict[int, str]:
    ids = [i for i in club_ids if i]
    if not ids:
        return {}
    result = await db.execute(
        select(User.club_id, User.nom_complet).where(
            User.role == RoleUtilisateur.COACH,
            User.est_actif.is_(True),
            User.club_id.in_(ids),
            User.nom_complet.is_not(None),
        )
    )
    out: dict[int, str] = {}
    for club_id, nom in result.all():
        if club_id and nom and club_id not in out:
            out[club_id] = nom
    return out


def _club_out(club: Club, coach_nom: str | None) -> ClubOut:
    return ClubOut.model_validate(club).model_copy(update={"coach_nom": coach_nom})


@router.get("", response_model=list[ClubOut])
async def lister_clubs(db: AsyncSession = Depends(get_db), limit: int = 20, offset: int = 0):
    result = await db.execute(select(Club).limit(min(limit, 100)).offset(offset))
    clubs = result.scalars().all()
    noms = await _coach_noms(db, [c.id for c in clubs])
    return [_club_out(c, noms.get(c.id)) for c in clubs]


@router.get("/{club_id}", response_model=ClubOut)
async def detail_club(club_id: int, db: AsyncSession = Depends(get_db)):
    club = await db.get(Club, club_id)
    if club is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Club introuvable.")
    noms = await _coach_noms(db, [club_id])
    return _club_out(club, noms.get(club_id))


@router.post("", response_model=ClubOut, status_code=status.HTTP_201_CREATED)
async def creer_club(
    payload: ClubCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    club = Club(**payload.model_dump())
    db.add(club)
    await db.flush()
    await log_audit(db, "clubs", club.id, ActionAudit.INSERT, current_user.id, None, payload.model_dump())
    await db.commit()
    await db.refresh(club)
    return club


@router.put("/{club_id}", response_model=ClubOut)
async def modifier_club(
    club_id: int,
    payload: ClubUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    club = await db.get(Club, club_id)
    if club is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Club introuvable.")
    avant = {"nom": club.nom, "ville": club.ville, "stade": club.stade}
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(club, k, v)
    await log_audit(db, "clubs", club.id, ActionAudit.UPDATE, current_user.id, avant, data)
    await db.commit()
    await db.refresh(club)
    return club


@router.delete("/{club_id}", status_code=status.HTTP_204_NO_CONTENT)
async def supprimer_club(
    club_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    club = await db.get(Club, club_id)
    if club is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Club introuvable.")
    joue = await db.execute(
        select(Match.id).where(
            or_(Match.equipe_domicile_id == club_id, Match.equipe_exterieur_id == club_id)
        ).limit(1)
    )
    if joue.scalar_one_or_none() is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Cette équipe a déjà des matchs. On n’efface pas l’historique — désinscrire si besoin.",
        )
    await log_audit(db, "clubs", club.id, ActionAudit.DELETE, current_user.id, {"nom": club.nom}, None)
    await db.delete(club)
    await db.commit()
    return None


@router.post("/{club_id}/logo", response_model=ClubOut)
async def depot_logo(
    club_id: int,
    fichier: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    club = await db.get(Club, club_id)
    if club is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Club introuvable.")
    data = await fichier.read()
    try:
        url = await uploader_logo(club_id, fichier.filename or "logo.png", data)
    except DepotRefus as ex:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(ex))
    avant = {"logo_url": club.logo_url}
    club.logo_url = url
    await log_audit(db, "clubs", club.id, ActionAudit.UPDATE, current_user.id, avant, {"logo_url": url})
    await db.commit()
    await db.refresh(club)
    noms = await _coach_noms(db, [club_id])
    return _club_out(club, noms.get(club_id))


@router.get("/{club_id}/staff", response_model=list[StaffOut])
async def lister_staff(club_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Staff)
        .where(Staff.club_id == club_id)
        .options(selectinload(Staff.photo_actuelle_rel))
        .order_by(Staff.id)
    )
    membres = result.scalars().all()
    ids = [m.id for m in membres]
    en_attente = set()
    if ids:
        att = await db.execute(
            select(Photo.sujet_id)
            .where(Photo.sujet_type == "staff")
            .where(Photo.sujet_id.in_(ids))
            .where(Photo.statut == StatutPhoto.EN_ATTENTE)
        )
        en_attente = {row[0] for row in att.all()}
    return [
        StaffOut.model_validate(m).model_copy(update={"photo_en_attente": m.id in en_attente})
        for m in membres
    ]


@router.post("/{club_id}/staff", response_model=StaffOut, status_code=status.HTTP_201_CREATED)
async def creer_staff(
    club_id: int,
    payload: StaffCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleUtilisateur.CLUB_MANAGER, RoleUtilisateur.COACH, RoleUtilisateur.ADMIN)
    ),
):
    club = await db.get(Club, club_id)
    if club is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Club introuvable.")
    if current_user.role in (RoleUtilisateur.CLUB_MANAGER, RoleUtilisateur.COACH):
        verifier_scope_club(current_user, club_id)
    membre = Staff(club_id=club_id, nom_complet=payload.nom_complet, role=payload.role)
    db.add(membre)
    await db.flush()
    await log_audit(db, "staffs", membre.id, ActionAudit.INSERT, current_user.id, None,
                    {"nom_complet": membre.nom_complet, "role": getattr(membre.role, "value", membre.role)})
    await db.commit()
    await db.refresh(membre)
    return membre


@router.post("/staff/{staff_id}/photo", response_model=PhotoOut, status_code=status.HTTP_201_CREATED)
async def proposer_photo_staff(
    staff_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleUtilisateur.CLUB_MANAGER, RoleUtilisateur.COACH, RoleUtilisateur.ADMIN)
    ),
):
    membre = await db.get(Staff, staff_id)
    if membre is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Membre du staff introuvable.")
    if current_user.role in (RoleUtilisateur.CLUB_MANAGER, RoleUtilisateur.COACH):
        verifier_scope_club(current_user, membre.club_id)
    data = await file.read()
    rang = await db.execute(
        select(func.coalesce(func.max(Photo.version), 0)).where(
            Photo.sujet_type == "staff", Photo.sujet_id == staff_id
        )
    )
    version = int(rang.scalar() or 0) + 1
    try:
        key, taille = await uploader_photo("staff", staff_id, version, file.content_type or "", data)
    except PhotoDepotRefus as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    except Exception as exc:  # jamais de 500 muet : la cause exacte est montrée
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Le dépôt a échoué : {exc!r}")
    photo = Photo(
        sujet_type="staff",
        sujet_id=staff_id,
        storage_key=key,
        mime_type=file.content_type,
        file_size=taille,
        uploaded_by=current_user.id,
        version=version,
    )
    db.add(photo)
    await db.flush()
    await log_audit(db, "photos", photo.id, ActionAudit.INSERT, current_user.id, None,
                    {"sujet": f"staff:{staff_id}", "version": version})
    await db.commit()
    await db.refresh(photo)
    from app.services.stockage_photo import url_publique
    from app.schemas.photo import PhotoOut as _PhotoOut
    sortie = _PhotoOut.model_validate(photo)
    sortie.url = url_publique(photo.storage_key)
    return sortie


@router.delete("/{club_id}/logo", response_model=ClubOut)
async def supprimer_logo(
    club_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    """Retire un logo erroné ou de test : le monogramme reprend sa place."""
    club = await db.get(Club, club_id)
    if club is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Club introuvable.")
    if not club.logo_url:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ce club n'a pas de logo à retirer.")
    avant = {"logo_url": club.logo_url}
    marque = "/object/public/logos-clubs/"
    chemin = club.logo_url.split(marque)[-1] if marque in club.logo_url else None
    if chemin:
        try:
            await supprimer_objet(chemin)
        except DepotRefus as ex:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(ex))
    club.logo_url = None
    await log_audit(db, "clubs", club.id, ActionAudit.DELETE, current_user.id, avant, {"logo_url": None})
    await db.commit()
    await db.refresh(club)
    noms = await _coach_noms(db, [club_id])
    return _club_out(club, noms.get(club_id))


@router.patch("/staff/{staff_id}", response_model=StaffOut)
async def modifier_staff(
    staff_id: int,
    payload: StaffUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleUtilisateur.CLUB_MANAGER, RoleUtilisateur.COACH, RoleUtilisateur.ADMIN)
    ),
):
    membre = await db.get(Staff, staff_id)
    if membre is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Membre du staff introuvable.")
    if current_user.role in (RoleUtilisateur.CLUB_MANAGER, RoleUtilisateur.COACH):
        verifier_scope_club(current_user, membre.club_id)
    role_avant = getattr(membre.role, "value", membre.role)
    avant = {"nom_complet": membre.nom_complet, "role": role_avant}
    if payload.nom_complet is not None:
        nom = payload.nom_complet.strip()
        if not nom:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nom vide.")
        membre.nom_complet = nom[:255]
    if payload.role is not None:
        membre.role = payload.role
    await log_audit(db, "staffs", membre.id, ActionAudit.UPDATE, current_user.id, avant,
                    {"nom_complet": membre.nom_complet, "role": getattr(membre.role, "value", membre.role)})
    await db.commit()
    await db.refresh(membre)
    return membre


@router.delete("/staff/{staff_id}", status_code=status.HTTP_204_NO_CONTENT)
async def retirer_staff(
    staff_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleUtilisateur.CLUB_MANAGER, RoleUtilisateur.COACH, RoleUtilisateur.ADMIN)
    ),
):
    membre = await db.get(Staff, staff_id)
    if membre is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Membre du staff introuvable.")
    if current_user.role in (RoleUtilisateur.CLUB_MANAGER, RoleUtilisateur.COACH):
        verifier_scope_club(current_user, membre.club_id)
    photos = await db.execute(
        select(Photo.id).where(Photo.sujet_type == "staff").where(Photo.sujet_id == staff_id)
    )
    if photos.first() is not None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Ce membre a un historique photo : modifiez-le au lieu de le retirer.",
        )
    feuilles = await db.execute(
        select(Match.id).where(or_(Match.staff_domicile_id == staff_id, Match.staff_exterieur_id == staff_id))
    )
    if feuilles.first() is not None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Ce membre apparaît dans des feuilles de match : modifiez-le au lieu de le retirer.",
        )
    await log_audit(db, "staffs", membre.id, ActionAudit.DELETE, current_user.id,
                    {"nom_complet": membre.nom_complet, "role": getattr(membre.role, "value", membre.role)}, None)
    await db.delete(membre)
    await db.commit()


class PurgeDemoIn(BaseModel):
    cle: str


@router.post("/purge-demo")
async def purge_demo(payload: PurgeDemoIn, db: AsyncSession = Depends(get_db)):
    """Operation UNIQUE : efface clubs DEMO, users @example.com et leurs objets.
    Double verrou : variable Render PURGE_DEMO_CLE + cle exacte dans le corps.
    Sans la variable, la route repond 404 : elle est morte."""
    cle_attendue = os.getenv("PURGE_DEMO_CLE", "")
    if not cle_attendue or payload.cle != cle_attendue:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Introuvable.")
    sup_photo = getattr(stockage_photo, "supprimer_objet", None)
    rapport = {"objets_photos": 0, "objets_logos": 0, "photos": 0, "matchs": 0,
               "joueurs": 0, "staffs": 0, "clubs": 0, "users": 0}
    etape = "debut"
    try:
        etape = "lecture_clubs"
        clubs_demo = (await db.execute(select(Club).where(Club.nom.like("DEMO %")))).scalars().all()
        club_ids = [c.id for c in clubs_demo]
        etape = "lecture_users"
        users_demo = (await db.execute(select(User).where(User.email.like("%@example.com")))).scalars().all()
        if club_ids:
            etape = "joueurs_staff"
            joueurs = (await db.execute(select(Joueur).where(Joueur.club_actuel_id.in_(club_ids)))).scalars().all()
            joueur_ids = [j.id for j in joueurs]
            staffs = (await db.execute(select(Staff).where(Staff.club_id.in_(club_ids)))).scalars().all()
            staff_ids = [m.id for m in staffs]
            etape = "matchs"
            matchs = (await db.execute(
                select(Match).where(or_(Match.equipe_domicile_id.in_(club_ids), Match.equipe_exterieur_id.in_(club_ids)))
            )).scalars().all()
            for m in matchs:
                await db.delete(m)
            rapport["matchs"] = len(matchs)
            etape = "photos"
            conds = []
            if joueur_ids:
                conds.append((Photo.sujet_type == "joueur") & Photo.sujet_id.in_(joueur_ids))
            if staff_ids:
                conds.append((Photo.sujet_type == "staff") & Photo.sujet_id.in_(staff_ids))
            if conds:
                photos = (await db.execute(select(Photo).where(or_(*conds)))).scalars().all()
                for ph in photos:
                    if sup_photo is not None:
                        try:
                            await sup_photo(ph.storage_key)
                            rapport["objets_photos"] += 1
                        except Exception:
                            pass
                    await db.delete(ph)
                    rapport["photos"] += 1
            etape = "suppression_joueurs"
            for j in joueurs:
                await db.delete(j)
            rapport["joueurs"] = len(joueurs)
            etape = "suppression_staffs"
            for m in staffs:
                await db.delete(m)
            rapport["staffs"] = len(staffs)
            etape = "suppression_clubs"
            marque = "/object/public/logos-clubs/"
            for c in clubs_demo:
                if c.logo_url and marque in c.logo_url:
                    try:
                        await stockage_logo.supprimer_objet(c.logo_url.split(marque)[-1])
                        rapport["objets_logos"] += 1
                    except Exception:
                        pass
                await db.delete(c)
            rapport["clubs"] = len(clubs_demo)
        etape = "suppression_users"
        for u in users_demo:
            await db.delete(u)
        rapport["users"] = len(users_demo)
        etape = "audit"
        await log_audit(db, "purge", 0, ActionAudit.DELETE, None, None, rapport)
        etape = "commit"
        await db.commit()
    except Exception as ex:
        await db.rollback()
        return {"erreur": str(ex), "etape": etape, "rapport_partiel": rapport}
    return rapport
