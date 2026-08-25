from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.rbac import require_roles
from app.database import get_db
from app.models.competition import Competition, Saison, SaisonClub
from app.models.enums import ActionAudit, RoleUtilisateur
from app.models.user import User
from app.schemas.competition import CompetitionCreate, CompetitionOut, SaisonCreate, SaisonOut
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
