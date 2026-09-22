from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import require_roles, verifier_organisateur_du_match, verifier_organisateur_de_competition, verifier_scope_club
from app.database import get_db
from app.models.club import Club
from app.models.competition import Saison, SaisonClub
from app.models.effectif import EffectifClub
from app.models.enums import ActionAudit, RoleUtilisateur, StatutEffectif
from app.models.match import Match
from app.models.user import User
from app.schemas.effectif import ControleEffectifMatchOut, EffectifClubOut, EffectifRetour
from app.services.audit import log_audit
from app.services.effectifs import ligne_effectif, resume_effectif

router = APIRouter(prefix="/effectifs", tags=["Effectifs"])

ROLES_CLUB = (RoleUtilisateur.CLUB_MANAGER, RoleUtilisateur.COACH)
ROLES_ORGANISATEUR = (RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)


async def _saison(db: AsyncSession, saison_id: int) -> Saison:
    saison = await db.get(Saison, saison_id)
    if saison is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Saison introuvable.")
    return saison


async def _inscription(db: AsyncSession, saison_id: int, club_id: int) -> SaisonClub:
    result = await db.execute(
        select(SaisonClub).where(
            SaisonClub.saison_id == saison_id,
            SaisonClub.club_id == club_id,
        )
    )
    inscription = result.scalar_one_or_none()
    if inscription is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ce club n'est pas inscrit à cette saison.")
    return inscription


async def _club(db: AsyncSession, club_id: int) -> Club:
    club = await db.get(Club, club_id)
    if club is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Équipe introuvable.")
    return club


async def _resume(db: AsyncSession, saison_id: int, club_id: int) -> dict:
    club = await _club(db, club_id)
    return await resume_effectif(db, saison_id, club)


def _out(data: dict) -> EffectifClubOut:
    return EffectifClubOut(**data)


@router.get("/saisons/{saison_id}/mon-club", response_model=EffectifClubOut)
async def mon_effectif(
    saison_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ROLES_CLUB)),
):
    await _saison(db, saison_id)
    if not current_user.club_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Votre compte n'est rattaché à aucun club.")
    await _inscription(db, saison_id, current_user.club_id)
    return _out(await _resume(db, saison_id, current_user.club_id))


@router.post("/saisons/{saison_id}/mon-club/soumettre", response_model=EffectifClubOut)
async def soumettre_mon_effectif(
    saison_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ROLES_CLUB)),
):
    await _saison(db, saison_id)
    if not current_user.club_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Votre compte n'est rattaché à aucun club.")
    await _inscription(db, saison_id, current_user.club_id)
    club = await _club(db, current_user.club_id)
    resume = await resume_effectif(db, saison_id, club)
    if resume["total_joueurs"] < 1:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Ajoutez au moins un joueur avant de soumettre l'effectif.",
        )
    ligne = await ligne_effectif(db, saison_id, current_user.club_id)
    nouvelle_ligne = ligne is None
    if ligne is not None and ligne.statut == StatutEffectif.SOUMIS:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cet effectif est déjà soumis aux organisateurs.")
    if ligne is not None and ligne.statut == StatutEffectif.VALIDE:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cet effectif est déjà validé par les organisateurs.")

    now = datetime.now(timezone.utc)
    if ligne is None:
        ligne = EffectifClub(
            saison_id=saison_id,
            club_id=current_user.club_id,
        )
        db.add(ligne)
        await db.flush()
    ancien = getattr(ligne.statut, "value", ligne.statut)
    ligne.statut = StatutEffectif.SOUMIS
    ligne.soumis_at = now
    ligne.soumis_par_id = current_user.id
    ligne.traite_at = None
    ligne.traite_par_id = None
    ligne.motif_retour = None
    await log_audit(
        db,
        "effectifs_clubs",
        ligne.id,
        ActionAudit.INSERT if nouvelle_ligne else ActionAudit.UPDATE,
        current_user.id,
        {"statut": ancien},
        {"statut": StatutEffectif.SOUMIS.value, "total_joueurs": resume["total_joueurs"]},
    )
    await db.commit()
    return _out(await _resume(db, saison_id, current_user.club_id))


@router.get("/saisons/{saison_id}/clubs", response_model=list[EffectifClubOut])
async def lister_effectifs_saison(
    saison_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ROLES_ORGANISATEUR)),
):
    saison = await _saison(db, saison_id)
    await verifier_organisateur_de_competition(saison.competition_id, current_user, db)
    result = await db.execute(
        select(SaisonClub, Club)
        .join(Club, Club.id == SaisonClub.club_id)
        .where(SaisonClub.saison_id == saison_id)
        .order_by(Club.nom, Club.id)
    )
    return [_out(await resume_effectif(db, saison_id, club)) for _, club in result.all()]


async def _ligne_organisateur(
    saison_id: int,
    club_id: int,
    db: AsyncSession,
    current_user: User,
) -> tuple[Saison, Club, EffectifClub]:
    saison = await _saison(db, saison_id)
    await verifier_organisateur_de_competition(saison.competition_id, current_user, db)
    await _inscription(db, saison_id, club_id)
    club = await _club(db, club_id)
    ligne = await ligne_effectif(db, saison_id, club_id)
    if ligne is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cet effectif n'a pas encore été soumis.")
    return saison, club, ligne


@router.post("/saisons/{saison_id}/clubs/{club_id}/valider", response_model=EffectifClubOut)
async def valider_effectif(
    saison_id: int,
    club_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ROLES_ORGANISATEUR)),
):
    _, club, ligne = await _ligne_organisateur(saison_id, club_id, db, current_user)
    if ligne.statut != StatutEffectif.SOUMIS:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Seul un effectif soumis peut être validé.",
        )
    ancien = getattr(ligne.statut, "value", ligne.statut)
    ligne.statut = StatutEffectif.VALIDE
    ligne.traite_at = datetime.now(timezone.utc)
    ligne.traite_par_id = current_user.id
    ligne.motif_retour = None
    await log_audit(
        db,
        "effectifs_clubs",
        ligne.id,
        ActionAudit.VALIDATE,
        current_user.id,
        {"statut": ancien},
        {"statut": StatutEffectif.VALIDE.value},
    )
    await db.commit()
    return _out(await resume_effectif(db, saison_id, club, ligne))


@router.post("/saisons/{saison_id}/clubs/{club_id}/retour", response_model=EffectifClubOut)
async def demander_correction_effectif(
    saison_id: int,
    club_id: int,
    payload: EffectifRetour,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ROLES_ORGANISATEUR)),
):
    _, club, ligne = await _ligne_organisateur(saison_id, club_id, db, current_user)
    if ligne.statut not in (StatutEffectif.SOUMIS, StatutEffectif.VALIDE):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Cet effectif doit être soumis avant de demander une correction.",
        )
    ancien = getattr(ligne.statut, "value", ligne.statut)
    ligne.statut = StatutEffectif.A_CORRIGER
    ligne.traite_at = datetime.now(timezone.utc)
    ligne.traite_par_id = current_user.id
    ligne.motif_retour = payload.motif.strip()
    await log_audit(
        db,
        "effectifs_clubs",
        ligne.id,
        ActionAudit.UPDATE,
        current_user.id,
        {"statut": ancien},
        {"statut": StatutEffectif.A_CORRIGER.value, "motif": ligne.motif_retour},
    )
    await db.commit()
    return _out(await resume_effectif(db, saison_id, club, ligne))


@router.get("/matchs/{match_id}", response_model=ControleEffectifMatchOut)
async def controle_effectifs_match(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ROLES_ORGANISATEUR)),
):
    match_ = await verifier_organisateur_du_match(match_id, current_user, db)
    if match_.equipe_domicile_id is None or match_.equipe_exterieur_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Les deux équipes du match sont nécessaires.")
    domicile = await _club(db, match_.equipe_domicile_id)
    exterieur = await _club(db, match_.equipe_exterieur_id)
    dom = await resume_effectif(db, match_.saison_id, domicile)
    ext = await resume_effectif(db, match_.saison_id, exterieur)
    return {
        "match_id": match_id,
        "saison_id": match_.saison_id,
        "domicile": dom,
        "exterieur": ext,
        "validation_requise": dom["statut"] != StatutEffectif.VALIDE
        or ext["statut"] != StatutEffectif.VALIDE,
        "blocage_automatique": False,
    }
