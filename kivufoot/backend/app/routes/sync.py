from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import require_roles
from app.database import get_db
from app.models.enums import RoleUtilisateur, StatutValidationEvenement
from app.models.evenement import EvenementMatch
from app.models.match import Match
from app.models.user import User
from app.schemas.sync import SyncPullResponse, SyncPushRequest, SyncPushResponse
from app.services.sync_offline import pousser_evenement

router = APIRouter(prefix="/sync", tags=["Synchronisation offline"])


@router.post("/push", response_model=SyncPushResponse)
async def push(
    payload: SyncPushRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.COLLECTEUR, RoleUtilisateur.ADMIN)),
):
    """
    Réception en lot des données saisies hors-ligne. Chaque item est
    traité indépendamment et de façon idempotente (temp_id) : un item
    déjà connu ne provoque aucune duplication, même après un retry
    complet du batch suite à une coupure réseau en cours de synchro.
    """
    resultats = []
    for item in payload.items:
        if item.type.value == "evenement" and item.evenement is not None and item.match_id is not None:
            resultat = await pousser_evenement(db, item.match_id, item.evenement, current_user.id)
            resultats.append(resultat)
    await db.commit()
    return SyncPushResponse(resultats=resultats)


@router.get("/pull", response_model=SyncPullResponse)
async def pull(
    depuis: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.COLLECTEUR, RoleUtilisateur.ADMIN)),
):
    """
    Récupère les statuts de validation mis à jour côté serveur, pour que
    l'app collecteur puisse rafraîchir son état local (§6.2). Utilise le
    polling (WebSocket/Redis explicitement différés en V1 - décision C4).
    """
    query_ev = select(EvenementMatch).where(EvenementMatch.cree_par_id == current_user.id)
    if depuis:
        query_ev = query_ev.where(EvenementMatch.date_validation >= depuis)
    else:
        query_ev = query_ev.where(EvenementMatch.statut_validation != StatutValidationEvenement.EN_ATTENTE)
    result_ev = await db.execute(query_ev.limit(200))
    evenements = result_ev.scalars().all()

    return SyncPullResponse(
        matchs_maj=[],
        evenements_maj=[
            {"id": e.id, "temp_id": str(e.temp_id) if e.temp_id else None, "statut_validation": e.statut_validation,
             "commentaire_rejet": e.commentaire_rejet}
            for e in evenements
        ],
        derniere_sync=datetime.now(timezone.utc),
    )
