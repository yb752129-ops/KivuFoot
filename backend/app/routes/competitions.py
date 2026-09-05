from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.rbac import require_roles, verifier_organisateur_de_competition
from app.database import get_db
from app.models.club import Club
from app.models.competition import Competition, OrganisateurCompetition, Saison, SaisonClub
from app.models.enums import ActionAudit, RoleUtilisateur
from app.models.user import User
from app.schemas.competition import ClubOut, CompetitionCreate, CompetitionOut, SaisonClubCreate, SaisonCreate, SaisonOut
from app.services.audit import log_audit

router = APIRouter(tags=["Compétitions"])


@router.get("/competitions", response_model=list[CompetitionOut])
async def lister_competitions(db: AsyncSession = Depends(get_db), inclure_demo: bool = False):
    query = select(Competition)
    if not inclure_demo:
        query = query.where(Competition.est_demo.is_(False))
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/competitions/{competition_id}", response_model=CompetitionOut)
async def detail_competition(competition_id: int, db: AsyncSession = Depends(get_db)):
    comp = await db.get(Competition, competition_id)
    if comp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compétition introuvable.")
    return comp


@router.post("/competitions", response_model=CompetitionOut, status_code=status.HTTP_201_CREATED)
async def creer_competition(
    payload: CompetitionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    # Règle §16 : aucune hypothèse figée sur la compétition pilote - elle
    # se crée entièrement via cette route, sans modification de code.
    comp = Competition(**payload.model_dump())
    db.add(comp)
    await db.flush()
    if current_user.role == RoleUtilisateur.ORGANISATEUR:
        db.add(OrganisateurCompetition(user_id=current_user.id, competition_id=comp.id))
    await log_audit(db, "competitions", comp.id, ActionAudit.INSERT, current_user.id, None, payload.model_dump(mode="json"))
    await db.commit()
    await db.refresh(comp)
    return comp


@router.post("/saisons", response_model=SaisonOut, status_code=status.HTTP_201_CREATED)
async def creer_saison(
    payload: SaisonCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    comp = await db.get(Competition, payload.competition_id)
    if comp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compétition introuvable.")
    await verifier_organisateur_de_competition(payload.competition_id, current_user, db)
    saison = Saison(
        competition_id=payload.competition_id,
        nom=payload.nom,
        date_debut=payload.date_debut,
        date_fin=payload.date_fin,
    )
    db.add(saison)
    await db.flush()
    for club_id in payload.club_ids:
        db.add(SaisonClub(saison_id=saison.id, club_id=club_id))
    await log_audit(db, "saisons", saison.id, ActionAudit.INSERT, current_user.id, None, {"competition_id": payload.competition_id})
    await db.commit()
    await db.refresh(saison)
    return saison


@router.get("/saisons", response_model=list[SaisonOut])
async def lister_saisons(competition_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Saison).where(Saison.competition_id == competition_id))
    return result.scalars().all()


@router.get("/saisons/{saison_id}/clubs", response_model=list[ClubOut])
async def lister_clubs_saison(saison_id: int, db: AsyncSession = Depends(get_db)):
    saison = await db.get(Saison, saison_id)
    if saison is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Saison introuvable.")
    result = await db.execute(
        select(Club)
        .join(SaisonClub, SaisonClub.club_id == Club.id)
        .where(SaisonClub.saison_id == saison_id)
        .order_by(Club.nom)
    )
    return result.scalars().all()


@router.post("/saisons/{saison_id}/clubs", response_model=ClubOut, status_code=status.HTTP_201_CREATED)
async def inscrire_club_saison(
    saison_id: int,
    payload: SaisonClubCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    saison = await db.get(Saison, saison_id)
    if saison is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Saison introuvable.")
    await verifier_organisateur_de_competition(saison.competition_id, current_user, db)
    club = await db.get(Club, payload.club_id)
    if club is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Équipe introuvable.")
    deja = await db.execute(
        select(SaisonClub).where(SaisonClub.saison_id == saison_id, SaisonClub.club_id == payload.club_id)
    )
    if deja.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cette équipe est déjà inscrite à cette saison.")
    db.add(SaisonClub(saison_id=saison_id, club_id=payload.club_id))
    await log_audit(
        db,
        "saison_clubs",
        saison_id,
        ActionAudit.INSERT,
        current_user.id,
        None,
        {"saison_id": saison_id, "club_id": payload.club_id},
    )
    await db.commit()
    await db.refresh(club)
    return club


@router.delete("/saisons/{saison_id}/clubs/{club_id}", status_code=status.HTTP_204_NO_CONTENT)
async def desinscrire_club_saison(
    saison_id: int,
    club_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    saison = await db.get(Saison, saison_id)
    if saison is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Saison introuvable.")
    await verifier_organisateur_de_competition(saison.competition_id, current_user, db)
    from sqlalchemy import or_
    from app.models.match import Match

    joue = await db.execute(
        select(Match.id).where(
            Match.saison_id == saison_id,
            or_(Match.equipe_domicile_id == club_id, Match.equipe_exterieur_id == club_id),
        ).limit(1)
    )
    if joue.scalar_one_or_none() is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Cette équipe a des matchs dans cette saison. Désinscription bloquée.",
        )
    lien = await db.execute(
        select(SaisonClub).where(SaisonClub.saison_id == saison_id, SaisonClub.club_id == club_id)
    )
    row = lien.scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Équipe non inscrite.")
    await db.delete(row)
    await log_audit(
        db, "saison_clubs", saison_id, ActionAudit.DELETE, current_user.id,
        {"club_id": club_id}, None,
    )
    await db.commit()
    return None
