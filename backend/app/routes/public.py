from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.enums import StatutMatch, StatutValidationEvenement
from app.models.evenement import EvenementMatch
from app.models.match import Match
from app.schemas.evenement import EvenementOut

router = APIRouter(prefix="/matchs", tags=["Public"])


@router.get("/{match_id}/evenements-publics", response_model=list[EvenementOut])
async def evenements_publics(match_id: int, db: AsyncSession = Depends(get_db)):
    """
    Vue publique de la fiche de match (§5.3) : uniquement les événements
    `valide`, et seulement si le match lui-même est publié. Les données
    brutes/en_attente/rejetées ne sont JAMAIS exposées ici.
    """
    match_ = await db.get(Match, match_id)
    statut = match_.statut.value if match_ and hasattr(match_.statut, "value") else match_.statut
    if match_ is None or statut not in ("valide", "en_cours", "termine"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable ou non publié.")
    result = await db.execute(
        select(EvenementMatch).where(
            EvenementMatch.match_id == match_id,
            EvenementMatch.statut_validation == StatutValidationEvenement.VALIDE,
        )
    )
    return result.scalars().all()
