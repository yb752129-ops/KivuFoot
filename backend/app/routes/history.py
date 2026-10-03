from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.competition import Saison
from app.services.progression import progression_saison
from app.services.records import calculer_records
from app.services.timeline import historique_public, timeline_saison

router = APIRouter(tags=["Historique et progression"])


@router.get("/saisons/{saison_id}/progression")
async def progression(saison_id: int, db: AsyncSession = Depends(get_db)):
    if await db.get(Saison, saison_id) is None:
        raise HTTPException(404, "Édition introuvable.")
    return await progression_saison(db, saison_id)


@router.get("/saisons/{saison_id}/qualification")
async def qualification(saison_id: int, db: AsyncSession = Depends(get_db)):
    if await db.get(Saison, saison_id) is None:
        raise HTTPException(404, "Édition introuvable.")
    return await progression_saison(db, saison_id)


@router.get("/saisons/{saison_id}/timeline")
async def timeline(saison_id: int, db: AsyncSession = Depends(get_db)):
    if await db.get(Saison, saison_id) is None:
        raise HTTPException(404, "Édition introuvable.")
    return await timeline_saison(db, saison_id)


@router.get("/records")
async def records(saison_id: int, db: AsyncSession = Depends(get_db)):
    if await db.get(Saison, saison_id) is None:
        raise HTTPException(404, "Édition introuvable.")
    return await calculer_records(db, saison_id)


@router.get("/historique-public")
async def historique(saison_id: int, db: AsyncSession = Depends(get_db)):
    if await db.get(Saison, saison_id) is None:
        raise HTTPException(404, "Édition introuvable.")
    return await historique_public(db, saison_id)
