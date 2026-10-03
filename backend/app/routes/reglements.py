from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import require_roles, verifier_organisateur_de_competition
from app.database import get_db
from app.models.competition import Competition, Saison
from app.models.enums import ActionAudit, RoleUtilisateur
from app.models.sport_engine import ReglementVersion
from app.models.user import User
from app.schemas.sport_engine import (
    RattachementReglementRequest,
    ReglementCreate,
    ReglementOut,
    ReglementSimulationRequest,
)
from app.services.audit import log_audit
from app.services.reglements import (
    activer_reglement,
    get_reglement,
    prochaine_version,
    rattacher_reglement_aux_matchs,
    verifier_configuration,
    verifier_saison_competition,
)

router = APIRouter(prefix="/reglements", tags=["Règlements sportifs"])


@router.get("", response_model=list[ReglementOut])
async def lister_reglements(
    saison_id: int | None = None,
    competition_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(ReglementVersion).order_by(ReglementVersion.saison_id, ReglementVersion.version.desc())
    if saison_id is not None:
        query = query.where(ReglementVersion.saison_id == saison_id)
    if competition_id is not None:
        query = query.where(ReglementVersion.competition_id == competition_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{reglement_id}", response_model=ReglementOut)
async def detail_reglement(reglement_id: int, db: AsyncSession = Depends(get_db)):
    return await get_reglement(db, reglement_id)


@router.post("", response_model=ReglementOut, status_code=status.HTTP_201_CREATED)
async def creer_reglement(
    payload: ReglementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    await verifier_saison_competition(db, payload.saison_id, payload.competition_id)
    await verifier_organisateur_de_competition(payload.competition_id, current_user, db)
    configuration = await verifier_configuration(payload.configuration.model_dump(mode="json", exclude_none=True))
    deja = await db.scalar(
        select(ReglementVersion.id).where(
            ReglementVersion.saison_id == payload.saison_id,
            ReglementVersion.version == payload.version,
        )
    )
    if deja is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cette version de règlement existe déjà.")
    reglement = ReglementVersion(
        competition_id=payload.competition_id,
        saison_id=payload.saison_id,
        version=payload.version,
        configuration=configuration,
        source_officielle=payload.source_officielle,
        reference_decision=payload.reference_decision,
        date_effet=payload.date_effet,
        date_fin=payload.date_fin,
        cree_par_id=current_user.id,
    )
    db.add(reglement)
    await db.flush()
    await log_audit(
        db,
        "reglements_versions",
        reglement.id,
        ActionAudit.INSERT,
        current_user.id,
        None,
        {"saison_id": payload.saison_id, "version": payload.version, "statut": "brouillon"},
    )
    await db.commit()
    await db.refresh(reglement)
    return reglement


@router.post("/{reglement_id}/activer", response_model=ReglementOut)
async def activer(
    reglement_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    reglement = await get_reglement(db, reglement_id)
    await verifier_organisateur_de_competition(reglement.competition_id, current_user, db)
    await activer_reglement(db, reglement, current_user)
    await db.commit()
    await db.refresh(reglement)
    return reglement


@router.post("/{reglement_id}/clore", response_model=ReglementOut)
async def clore(
    reglement_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    reglement = await get_reglement(db, reglement_id)
    await verifier_organisateur_de_competition(reglement.competition_id, current_user, db)
    if reglement.statut == "clos":
        return reglement
    ancien = reglement.statut
    reglement.statut = "clos"
    reglement.closed_at = datetime.now(timezone.utc)
    await log_audit(
        db,
        "reglements_versions",
        reglement.id,
        ActionAudit.UPDATE,
        current_user.id,
        {"statut": ancien},
        {"statut": "clos"},
    )
    await db.commit()
    await db.refresh(reglement)
    return reglement


@router.post("/{reglement_id}/rattacher-matchs", response_model=list[dict])
async def rattacher_matchs(
    reglement_id: int,
    payload: RattachementReglementRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    reglement = await get_reglement(db, reglement_id)
    await verifier_organisateur_de_competition(reglement.competition_id, current_user, db)
    rows = await rattacher_reglement_aux_matchs(db, reglement, payload.match_ids, payload.motif, current_user)
    await db.commit()
    return [{"match_id": row.id, "reglement_version_id": row.reglement_version_id} for row in rows]


@router.post("/{reglement_id}/simuler")
async def simuler(
    reglement_id: int,
    payload: ReglementSimulationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)),
):
    reglement = await get_reglement(db, reglement_id)
    await verifier_organisateur_de_competition(reglement.competition_id, current_user, db)
    candidate = await verifier_configuration(payload.configuration.model_dump(mode="json", exclude_none=True))
    return {
        "reglement_id": reglement.id,
        "saison_id": reglement.saison_id,
        "mode": "SIMULATION",
        "configuration_candidate": candidate,
        "message": "Simulation structurée prête. Aucun match ni règlement n'a été modifié.",
    }
