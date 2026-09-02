"""
Synchronisation offline-first (§5.1, §6).

Règles appliquées :
- Idempotence : chaque événement poussé porte un `temp_id` (UUID généré
  côté client). S'il existe déjà un événement avec ce temp_id, on ne le
  recrée PAS - on renvoie simplement son état actuel (règle critique
  pour la fiabilité en cas de retry réseau, rapport Phase 0 point B).
- Statut à l'arrivée : toujours 'en_attente' (jamais 'brut', qui n'est
  qu'un concept client - voir rapport Phase 0 point A2).
- Cas 2 (§6.3) : un événement arrivant pour un match déjà `locked` est
  automatiquement rejeté (statut_validation='rejete') avec un
  commentaire explicite, PAS silencieusement ignoré : l'utilisateur
  doit être notifié du rejet à la prochaine synchronisation.
- Cas 1 (§6.3) : conflit de saisie (deux collecteurs, même
  match/minute/type/joueur) -> le premier arrivé est accepté
  normalement, le second est marqué conflit=True et une entrée est
  créée dans conflits_synchronisation pour arbitrage par l'organisateur.
"""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import StatutValidationEvenement
from app.services.validation import assert_joueur_peut_recevoir_fait
from app.models.evenement import EvenementMatch
from app.models.match import Match
from app.models.sync import ConflitSynchronisation
from app.schemas.evenement import EvenementCreate
from app.schemas.sync import SyncPushResultItem
from app.models.enums import StatutSync


async def _trouver_conflit_potentiel(db: AsyncSession, match_id: int, ev: EvenementCreate) -> EvenementMatch | None:
    """Même match, même minute, même type, même joueur principal -> conflit probable."""
    result = await db.execute(
        select(EvenementMatch).where(
            EvenementMatch.match_id == match_id,
            EvenementMatch.minute == ev.minute,
            EvenementMatch.type == ev.type,
            EvenementMatch.joueur_id == ev.joueur_id,
            EvenementMatch.statut_validation != StatutValidationEvenement.REJETE,
            EvenementMatch.refuse.is_(False),
        )
    )
    return result.scalars().first()


async def pousser_evenement(
    db: AsyncSession, match_id: int, ev: EvenementCreate, utilisateur_id: int
) -> SyncPushResultItem:
    # 1. Idempotence : l'événement a-t-il déjà été synchronisé ?
    existing = await db.execute(select(EvenementMatch).where(EvenementMatch.temp_id == ev.temp_id))
    deja_present = existing.scalar_one_or_none()
    if deja_present is not None:
        return SyncPushResultItem(temp_id=ev.temp_id, statut=StatutSync.CONFIRME, evenement_id=deja_present.id)

    match_ = await db.get(Match, match_id)
    if match_ is None:
        return SyncPushResultItem(temp_id=ev.temp_id, statut=StatutSync.LOCAL, erreur="Match introuvable.")

    # 2. Cas 2 §6.3 : match déjà verrouillé -> rejet automatique tracé.
    try:
        await assert_joueur_peut_recevoir_fait(db, match_id, ev.joueur_id, ev.type)
        if ev.joueur_secondaire_id:
            await assert_joueur_peut_recevoir_fait(db, match_id, ev.joueur_secondaire_id, ev.type)
    except HTTPException as ex:
        return SyncPushResultItem(temp_id=ev.temp_id, statut=StatutSync.LOCAL, erreur=ex.detail)

    if match_.locked:
        rejet = EvenementMatch(
            match_id=match_id,
            minute=ev.minute,
            minute_additionnelle=ev.minute_additionnelle or 0,
            periode=ev.periode,
            type=ev.type,
            joueur_id=ev.joueur_id,
            joueur_secondaire_id=ev.joueur_secondaire_id,
            resultat=ev.resultat,
            equipe_concernee=ev.equipe_concernee,
            statut_validation=StatutValidationEvenement.REJETE,
            commentaire_rejet="Rejet automatique : le match était déjà validé/verrouillé au moment de la synchronisation.",
            temp_id=ev.temp_id,
            cree_par_id=utilisateur_id,
        )
        db.add(rejet)
        await db.flush()
        return SyncPushResultItem(
            temp_id=ev.temp_id, statut=StatutSync.CONFIRME, evenement_id=rejet.id,
            erreur="Match verrouillé : événement automatiquement rejeté.",
        )

    # 3. Cas 1 §6.3 : conflit potentiel avec un événement déjà présent.
    conflit_existant = await _trouver_conflit_potentiel(db, match_id, ev)

    periode = ev.periode
    if periode is None:
        mp = match_.periode.value if match_.periode and hasattr(match_.periode, "value") else match_.periode
        periode = mp if mp in ("1", "2") else None

    nouvel_evenement = EvenementMatch(
        match_id=match_id,
        minute=ev.minute,
        minute_additionnelle=ev.minute_additionnelle or 0,
        periode=periode,
        type=ev.type,
        joueur_id=ev.joueur_id,
        joueur_secondaire_id=ev.joueur_secondaire_id,
        resultat=ev.resultat,
        equipe_concernee=ev.equipe_concernee,
        statut_validation=StatutValidationEvenement.EN_ATTENTE,
        temp_id=ev.temp_id,
        cree_par_id=utilisateur_id,
        conflit=conflit_existant is not None,
    )
    db.add(nouvel_evenement)
    await db.flush()

    if conflit_existant is not None:
        conflit = ConflitSynchronisation(
            evenement_id=nouvel_evenement.id,
            version_a={
                "evenement_id": conflit_existant.id,
                "joueur_id": conflit_existant.joueur_id,
                "cree_par_id": conflit_existant.cree_par_id,
            },
            version_b={
                "evenement_id": nouvel_evenement.id,
                "joueur_id": nouvel_evenement.joueur_id,
                "cree_par_id": utilisateur_id,
            },
            utilisateur_a_id=conflit_existant.cree_par_id,
            utilisateur_b_id=utilisateur_id,
        )
        db.add(conflit)

    return SyncPushResultItem(temp_id=ev.temp_id, statut=StatutSync.CONFIRME, evenement_id=nouvel_evenement.id)
