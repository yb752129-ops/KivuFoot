from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import require_roles
from app.database import get_db
from app.models.enums import RoleUtilisateur, StatutMatch, StatutValidationEvenement
from app.models.evenement import EvenementMatch
from app.models.match import Match
from app.models.user import User
from app.schemas.evenement import EvenementCreate, EvenementOut
from app.services.sync_offline import pousser_evenement
from app.services.validation import valider_evenement

router = APIRouter(prefix="/matchs", tags=["Événements"])


@router.get("/{match_id}/evenements", response_model=list[EvenementOut])
async def lister_evenements(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(
        RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR,
        RoleUtilisateur.COLLECTEUR, RoleUtilisateur.CLUB_MANAGER,
    )),
):
    """
    NB : cette route "staff" liste TOUS les statuts. La vue publique
    (événements validés uniquement, intégrée à la fiche de match) est
    exposée séparément par routes/public.py pour ne jamais mélanger les
    deux publics (§5.3 : les données brutes ne sont jamais visibles du
    public).
    """
    match_ = await db.get(Match, match_id)
    if match_ is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable.")
    result = await db.execute(select(EvenementMatch).where(EvenementMatch.match_id == match_id))
    return result.scalars().all()


@router.post("/{match_id}/evenements", response_model=EvenementOut, status_code=status.HTTP_201_CREATED)
async def saisir_evenement(
    match_id: int,
    payload: EvenementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleUtilisateur.COLLECTEUR, RoleUtilisateur.ADMIN, RoleUtilisateur.ORGANISATEUR)
    ),
):
    """
    Saisie directe (en ligne). Le flux principal offline-first passe par
    POST /sync/push (voir routes/sync.py) ; cette route sert la saisie
    en direct quand le réseau est disponible, avec les mêmes garanties
    d'idempotence (temp_id) et de gestion de conflit.
    L'organisateur qui saisit depuis le tableau de bord voit l'événement
    validé tout de suite (score à jour) — le collecteur reste en attente.
    """
    match_ = await db.get(Match, match_id)
    if match_ is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable.")
    staff_orga = current_user.role in (RoleUtilisateur.ORGANISATEUR, RoleUtilisateur.ADMIN)
    if staff_orga and match_.statut != StatutMatch.EN_COURS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Le match n'est pas en cours.")
    try:
        resultat = await pousser_evenement(db, match_id, payload, current_user.id)
        if resultat.evenement_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, resultat.erreur or "Erreur de saisie.")
        evenement = await db.get(EvenementMatch, resultat.evenement_id)
        if evenement is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Événement non créé.")
        if staff_orga:
            evenement = await valider_evenement(db, evenement.id, current_user.id)
        await db.commit()
        await db.refresh(evenement)
        return evenement
    except HTTPException:
        await db.rollback()
        raise
    except Exception as ex:
        await db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(ex)) from ex
