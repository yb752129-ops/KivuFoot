"""
Orchestration du workflow de validation - le cœur de KivuFoot (§3.1, §5.2).

Règles appliquées ici (issues du rapport Phase 0 / Phase 1) :
- Un événement ne peut être validé/rejeté que si le MATCH n'est pas locked.
- Valider un événement déclenche immédiatement : mise à jour du score
  (si pertinent), mise à jour des stats joueur, verrouillage de
  l'événement (locked=True, il devient immuable), écriture d'audit.
- Rejeter un événement exige un commentaire (contrainte applicative,
  reflète le NOT NULL logique de commentaire_rejet).
- La validation du MATCH lui-même (action distincte, finale) n'est
  possible que si plus aucun événement n'est en_attente. Elle déclenche
  la feuille de match (minutes/titularisations) et verrouille le match.
"""
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ActionAudit, StatutMatch, StatutValidationEvenement
from app.models.evenement import EvenementMatch
from app.models.match import Match
from app.services.audit import log_audit
from app.services.calcul_stats import appliquer_evenement_valide
from app.services.feuille_de_match import appliquer_feuille_de_match


async def valider_evenement(db: AsyncSession, evenement_id: int, valide_par_id: int) -> EvenementMatch:
    evenement = await db.get(EvenementMatch, evenement_id)
    if evenement is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Événement introuvable.")

    match_ = await db.get(Match, evenement.match_id)
    if match_ is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable.")
    if match_.locked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ce match est verrouillé : aucune saisie n'est plus autorisée.")
    if evenement.locked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cet événement a déjà été validé et est verrouillé.")
    if evenement.statut_validation == StatutValidationEvenement.REJETE:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cet événement a déjà été rejeté.")

    old_data = {"statut_validation": evenement.statut_validation.value}

    evenement.statut_validation = StatutValidationEvenement.VALIDE
    evenement.valide_par = valide_par_id
    evenement.date_validation = datetime.now(timezone.utc)
    evenement.locked = True

    await appliquer_evenement_valide(db, evenement, match_)

    await log_audit(
        db,
        table_name="evenements_match",
        record_id=evenement.id,
        action=ActionAudit.VALIDATE,
        user_id=valide_par_id,
        old_data=old_data,
        new_data={"statut_validation": "valide"},
    )
    return evenement


async def rejeter_evenement(
    db: AsyncSession, evenement_id: int, commentaire: str, valide_par_id: int
) -> EvenementMatch:
    evenement = await db.get(EvenementMatch, evenement_id)
    if evenement is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Événement introuvable.")

    match_ = await db.get(Match, evenement.match_id)
    if match_ and match_.locked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ce match est verrouillé.")
    if evenement.locked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cet événement est déjà validé et verrouillé.")

    old_data = {"statut_validation": evenement.statut_validation.value}

    evenement.statut_validation = StatutValidationEvenement.REJETE
    evenement.valide_par = valide_par_id
    evenement.date_validation = datetime.now(timezone.utc)
    evenement.commentaire_rejet = commentaire

    await log_audit(
        db,
        table_name="evenements_match",
        record_id=evenement.id,
        action=ActionAudit.REJECT,
        user_id=valide_par_id,
        old_data=old_data,
        new_data={"statut_validation": "rejete", "commentaire_rejet": commentaire},
    )
    return evenement


async def valider_match(db: AsyncSession, match_id: int, valide_par_id: int) -> Match:
    match_ = await db.get(Match, match_id)
    if match_ is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable.")
    if match_.locked:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ce match est déjà validé et verrouillé.")

    result = await db.execute(
        select(EvenementMatch).where(
            EvenementMatch.match_id == match_id,
            EvenementMatch.statut_validation == StatutValidationEvenement.EN_ATTENTE,
        )
    )
    if result.scalars().first() is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Impossible de valider ce match : des événements sont encore en attente de traitement.",
        )

    old_data = {"statut": match_.statut.value, "locked": match_.locked}

    await appliquer_feuille_de_match(db, match_)

    match_.statut = StatutMatch.VALIDE
    match_.valide_par = valide_par_id
    match_.date_validation = datetime.now(timezone.utc)
    match_.locked = True

    await log_audit(
        db,
        table_name="matchs",
        record_id=match_.id,
        action=ActionAudit.VALIDATE,
        user_id=valide_par_id,
        old_data=old_data,
        new_data={"statut": "valide", "locked": True},
    )
    return match_
