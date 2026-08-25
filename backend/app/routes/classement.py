from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.sync import ClassementLigne
from app.services.calcul_classement import calculer_classement

router = APIRouter(prefix="/classement", tags=["Classement"])


@router.get("", response_model=list[ClassementLigne])
async def classement_saison(saison_id: int, db: AsyncSession = Depends(get_db)):
    lignes = await calculer_classement(db, saison_id)
    return [
        ClassementLigne(
            club_id=l.club_id,
            club_nom=l.club_nom,
            matchs_joues=l.matchs_joues,
            victoires=l.victoires,
            nuls=l.nuls,
            defaites=l.defaites,
            buts_marques=l.buts_marques,
            buts_encaisses=l.buts_encaisses,
            difference_buts=l.difference_buts,
            points=l.points,
        )
        for l in lignes
    ]


@router.get("/club/{club_id}")
async def position_club(club_id: int, saison_id: int, db: AsyncSession = Depends(get_db)):
    lignes = await calculer_classement(db, saison_id)
    for position, ligne in enumerate(lignes, start=1):
        if ligne.club_id == club_id:
            return {
                "position": position,
                "club_id": ligne.club_id,
                "club_nom": ligne.club_nom,
                "points": ligne.points,
                "matchs_joues": ligne.matchs_joues,
                "difference_buts": ligne.difference_buts,
            }
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Ce club n'apparaît pas dans le classement de cette saison.")
