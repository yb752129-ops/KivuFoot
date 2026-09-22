"""Routes publiques et de collecte pour Possession V1."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import require_roles, verifier_organisateur_du_match
from app.database import get_db
from app.models.enums import EtatPossession, RoleUtilisateur
from app.models.match import Match
from app.models.user import User
from app.schemas.possession import (
    PossessionCorrectionCreate,
    PossessionDetailOut,
    PossessionPublicOut,
    PossessionTransitionCreate,
)
from app.services.possession import (
    corriger_intervalle_possession,
    get_possession,
    snapshot_possession,
    snapshot_public_possession,
    transition_possession,
)

router = APIRouter(prefix="/matchs", tags=["Possession"])
_GESTION_ROLES = (RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR, RoleUtilisateur.COLLECTEUR)


async def _match_existant(db: AsyncSession, match_id: int) -> Match:
    match = await db.get(Match, match_id)
    if match is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable.")
    return match


async def _verifier_gestion(match_id: int, current_user: User, db: AsyncSession) -> Match:
    if current_user.role == RoleUtilisateur.ORGANISATEUR or current_user.role == RoleUtilisateur.ADMIN:
        return await verifier_organisateur_du_match(match_id, current_user, db)
    return await _match_existant(db, match_id)


@router.get("/{match_id}/possession", response_model=PossessionPublicOut)
async def lire_possession_publique(match_id: int, db: AsyncSession = Depends(get_db)):
    """La possession n'est publique qu'après validation du match ET de la capture."""
    match = await _match_existant(db, match_id)
    return await snapshot_public_possession(db, match, await get_possession(db, match_id))


@router.get("/{match_id}/possession/gestion", response_model=PossessionDetailOut)
async def lire_possession_gestion(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*_GESTION_ROLES)),
):
    match = await _verifier_gestion(match_id, current_user, db)
    return await snapshot_possession(db, match, await get_possession(db, match_id))


@router.post("/{match_id}/possession/transition", response_model=PossessionDetailOut)
async def changer_possession(
    match_id: int,
    payload: PossessionTransitionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*_GESTION_ROLES)),
):
    if current_user.role == RoleUtilisateur.ORGANISATEUR:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "L'organisateur ne remplace pas le collecteur : utilisez la route de correction auditée.",
        )
    if payload.correction and current_user.role not in (RoleUtilisateur.ADMIN,):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Seul l'organisateur autorisé peut enregistrer une correction de possession.",
        )
    match = await _verifier_gestion(match_id, current_user, db)
    possession = await transition_possession(
        db,
        match_id,
        payload.etat,
        current_user.id,
        payload.operation_id,
        correction=payload.correction,
    )
    await db.commit()
    await db.refresh(possession)
    return await snapshot_possession(db, match, possession)


@router.post("/{match_id}/possession/correction", response_model=PossessionDetailOut)
async def corriger_possession(
    match_id: int,
    payload: PossessionCorrectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    match = await _verifier_gestion(match_id, current_user, db)
    possession = await corriger_intervalle_possession(
        db,
        match_id,
        payload.intervalle_id,
        payload.etat,
        current_user.id,
        payload.operation_id,
        payload.motif,
        debut_at=payload.debut_at,
        fin_at=payload.fin_at,
    )
    await db.commit()
    await db.refresh(possession)
    return await snapshot_possession(db, match, possession)
