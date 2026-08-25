from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import require_roles, verifier_organisateur_du_match
from app.database import get_db
from app.models.audit import AuditLog
from app.models.enums import ActionAudit, RoleUtilisateur, StatutValidationEvenement
from app.models.evenement import EvenementMatch
from app.models.match import Match
from app.models.user import User
from app.schemas.evenement import EvenementOut, ValidationRejetRequest
from app.services.validation import rejeter_evenement, valider_evenement

router = APIRouter(prefix="/validation", tags=["Validation"])


@router.get("/evenements", response_model=list[EvenementOut])
async def lister_evenements_en_attente(
    db: AsyncSession = Depends(get_db),
    match_id: int | None = None,
    equipe_concernee: str | None = None,
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    query = select(EvenementMatch).where(EvenementMatch.statut_validation == StatutValidationEvenement.EN_ATTENTE)
    if match_id:
        query = query.where(EvenementMatch.match_id == match_id)
    if equipe_concernee:
        query = query.where(EvenementMatch.equipe_concernee == equipe_concernee)
    result = await db.execute(query.order_by(EvenementMatch.created_at))
    evenements = result.scalars().all()

    # Filtrage par portée organisateur (seulement ses compétitions), sauf admin.
    if current_user.role == RoleUtilisateur.ADMIN:
        return evenements
    autorises = []
    for ev in evenements:
        try:
            await verifier_organisateur_du_match(ev.match_id, current_user, db)
            autorises.append(ev)
        except HTTPException:
            continue
    return autorises


@router.put("/evenements/{evenement_id}", response_model=EvenementOut)
async def valider(
    evenement_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    ev = await db.get(EvenementMatch, evenement_id)
    if ev is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Événement introuvable.")
    await verifier_organisateur_du_match(ev.match_id, current_user, db)
    evenement = await valider_evenement(db, evenement_id, current_user.id)
    await db.commit()
    await db.refresh(evenement)
    return evenement


@router.put("/evenements/{evenement_id}/rejeter", response_model=EvenementOut)
async def rejeter(
    evenement_id: int,
    payload: ValidationRejetRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    ev = await db.get(EvenementMatch, evenement_id)
    if ev is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Événement introuvable.")
    await verifier_organisateur_du_match(ev.match_id, current_user, db)
    evenement = await rejeter_evenement(db, evenement_id, payload.commentaire, current_user.id)
    await db.commit()
    await db.refresh(evenement)
    return evenement


@router.get("/historique")
async def historique_validations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
    limit: int = 50,
):
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.table_name == "evenements_match", AuditLog.action.in_([ActionAudit.VALIDATE, ActionAudit.REJECT]))
        .order_by(AuditLog.created_at.desc())
        .limit(min(limit, 200))
    )
    return result.scalars().all()
