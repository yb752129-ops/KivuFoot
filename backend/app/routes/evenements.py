from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import require_roles
from app.database import get_db
from app.models.enums import EquipeConcernee, RoleUtilisateur, StatutMatch, TypeEvenement
from app.models.evenement import EvenementMatch
from app.models.joueur import Joueur
from app.models.match import Match
from app.models.user import User
from app.schemas.evenement import EvenementCreate, EvenementOut
from app.services.sync_offline import pousser_evenement
from app.services.validation import valider_evenement

router = APIRouter(prefix="/matchs", tags=["Événements"])


def _club_equipe(match_: Match, equipe) -> int | None:
    val = equipe.value if hasattr(equipe, "value") else equipe
    if val == EquipeConcernee.EXTERIEUR.value:
        return match_.equipe_exterieur_id
    return match_.equipe_domicile_id


async def verifier_joueurs_du_fait(db: AsyncSession, match_: Match, payload: EvenementCreate) -> None:
    typ = payload.type.value if hasattr(payload.type, "value") else payload.type
    club_id = _club_equipe(match_, payload.equipe_concernee)
    if payload.joueur_id:
        joueur = await db.get(Joueur, payload.joueur_id)
        if joueur is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Joueur introuvable.")
        if joueur.club_actuel_id and club_id and joueur.club_actuel_id != club_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ce joueur n'appartient pas à cette équipe.")
    if typ == TypeEvenement.BUT_CONTRE_SON_CAMP.value and payload.joueur_secondaire_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Un but contre son camp n'a pas de passeur.")
    if typ == TypeEvenement.BUT.value and payload.joueur_secondaire_id:
        passeur = await db.get(Joueur, payload.joueur_secondaire_id)
        if passeur is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Passeur introuvable.")
        buteur = await db.get(Joueur, payload.joueur_id) if payload.joueur_id else None
        if buteur and passeur.club_actuel_id and buteur.club_actuel_id and passeur.club_actuel_id != buteur.club_actuel_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Le passeur doit être de la même équipe que le buteur.")


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
    statut = match_.statut.value if hasattr(match_.statut, "value") else match_.statut
    if staff_orga and statut != StatutMatch.EN_COURS.value:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Le match n'est pas en cours.")
    periode = match_.periode.value if match_.periode and hasattr(match_.periode, "value") else match_.periode
    if staff_orga and periode == "mi_temps":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mi-temps : la saisie reprend à la reprise.")
    await verifier_joueurs_du_fait(db, match_, payload)
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
