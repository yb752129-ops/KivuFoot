import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.models.enums import EquipeConcernee, ResultatPenalty, StatutValidationEvenement, TypeEvenement
from app.models.evenement import EvenementMatch
from app.models.stats import StatistiqueJoueur
from app.services.validation import rejeter_evenement, valider_evenement, valider_match
from tests.factories import creer_club, creer_competition_avec_saison, creer_joueur, creer_match, creer_utilisateur
from app.models.enums import RoleUtilisateur

pytestmark = pytest.mark.asyncio


async def _setup_match_avec_joueur(db_session):
    organisateur = await creer_utilisateur(db_session, RoleUtilisateur.ORGANISATEUR, "orga@test.local")
    competition, saison = await creer_competition_avec_saison(db_session, organisateur)
    club_a = await creer_club(db_session, "Club A")
    club_b = await creer_club(db_session, "Club B")
    joueur = await creer_joueur(db_session, club_a.id, "Buteur Test")
    match_ = await creer_match(db_session, saison.id, club_a.id, club_b.id)
    await db_session.flush()
    return organisateur, competition, saison, club_a, club_b, joueur, match_


async def test_but_valide_incremente_score_et_stats(db_session):
    organisateur, _, _, _, _, joueur, match_ = await _setup_match_avec_joueur(db_session)

    ev = EvenementMatch(
        match_id=match_.id, minute=10, type=TypeEvenement.BUT, joueur_id=joueur.id,
        equipe_concernee=EquipeConcernee.DOMICILE, temp_id=uuid.uuid4(),
    )
    db_session.add(ev)
    await db_session.flush()

    await valider_evenement(db_session, ev.id, organisateur.id)
    await db_session.flush()

    assert match_.score_domicile == 1
    assert ev.locked is True
    assert ev.statut_validation == StatutValidationEvenement.VALIDE

    stats = (await db_session.execute(
        select(StatistiqueJoueur).where(StatistiqueJoueur.joueur_id == joueur.id)
    )).scalar_one()
    assert stats.buts == 1


async def test_penalty_marque_compte_comme_but_sans_evenement_separe(db_session):
    """Règle critique du rapport Phase 0 (point A1) : pas de double comptage."""
    organisateur, _, _, _, _, joueur, match_ = await _setup_match_avec_joueur(db_session)

    ev = EvenementMatch(
        match_id=match_.id, minute=45, type=TypeEvenement.PENALTY, joueur_id=joueur.id,
        resultat=ResultatPenalty.MARQUE, equipe_concernee=EquipeConcernee.DOMICILE, temp_id=uuid.uuid4(),
    )
    db_session.add(ev)
    await db_session.flush()

    await valider_evenement(db_session, ev.id, organisateur.id)
    await db_session.flush()

    assert match_.score_domicile == 1  # un seul but compté, pas deux
    stats = (await db_session.execute(
        select(StatistiqueJoueur).where(StatistiqueJoueur.joueur_id == joueur.id)
    )).scalar_one()
    assert stats.buts == 1


async def test_penalty_rate_n_affecte_pas_le_score(db_session):
    organisateur, _, _, _, _, joueur, match_ = await _setup_match_avec_joueur(db_session)

    ev = EvenementMatch(
        match_id=match_.id, minute=45, type=TypeEvenement.PENALTY, joueur_id=joueur.id,
        resultat=ResultatPenalty.RATE, equipe_concernee=EquipeConcernee.DOMICILE, temp_id=uuid.uuid4(),
    )
    db_session.add(ev)
    await db_session.flush()

    await valider_evenement(db_session, ev.id, organisateur.id)
    await db_session.flush()

    assert match_.score_domicile == 0


async def test_but_contre_son_camp_credite_equipe_adverse_pas_le_joueur(db_session):
    organisateur, _, _, _, _, joueur, match_ = await _setup_match_avec_joueur(db_session)
    # joueur appartient au club domicile mais marque contre son camp
    ev = EvenementMatch(
        match_id=match_.id, minute=30, type=TypeEvenement.BUT_CONTRE_SON_CAMP, joueur_id=joueur.id,
        equipe_concernee=EquipeConcernee.DOMICILE, temp_id=uuid.uuid4(),
    )
    db_session.add(ev)
    await db_session.flush()

    await valider_evenement(db_session, ev.id, organisateur.id)
    await db_session.flush()

    assert match_.score_domicile == 0
    assert match_.score_exterieur == 1  # crédité à l'équipe adverse

    result = await db_session.execute(
        select(StatistiqueJoueur).where(StatistiqueJoueur.joueur_id == joueur.id)
    )
    stats = result.scalar_one_or_none()
    assert stats is None or stats.buts == 0  # jamais crédité au joueur


async def test_evenement_deja_valide_ne_peut_pas_etre_revalide(db_session):
    organisateur, _, _, _, _, joueur, match_ = await _setup_match_avec_joueur(db_session)
    ev = EvenementMatch(
        match_id=match_.id, minute=10, type=TypeEvenement.BUT, joueur_id=joueur.id,
        equipe_concernee=EquipeConcernee.DOMICILE, temp_id=uuid.uuid4(),
    )
    db_session.add(ev)
    await db_session.flush()
    await valider_evenement(db_session, ev.id, organisateur.id)
    await db_session.flush()

    with pytest.raises(HTTPException) as exc_info:
        await valider_evenement(db_session, ev.id, organisateur.id)
    assert exc_info.value.status_code == 403


async def test_rejet_exige_un_commentaire_non_vide():
    from pydantic import ValidationError
    from app.schemas.evenement import ValidationRejetRequest

    with pytest.raises(ValidationError):
        ValidationRejetRequest(commentaire="   ")


async def test_match_ne_peut_pas_etre_valide_avec_evenements_en_attente(db_session):
    organisateur, _, _, _, _, joueur, match_ = await _setup_match_avec_joueur(db_session)
    ev = EvenementMatch(
        match_id=match_.id, minute=10, type=TypeEvenement.CARTON_JAUNE, joueur_id=joueur.id,
        equipe_concernee=EquipeConcernee.DOMICILE, temp_id=uuid.uuid4(),
    )
    db_session.add(ev)
    await db_session.flush()

    with pytest.raises(HTTPException) as exc_info:
        await valider_match(db_session, match_.id, organisateur.id)
    assert exc_info.value.status_code == 409


async def test_match_verrouille_apres_validation_bloque_nouveaux_evenements(db_session):
    organisateur, _, _, _, _, joueur, match_ = await _setup_match_avec_joueur(db_session)
    await valider_match(db_session, match_.id, organisateur.id)
    await db_session.flush()
    assert match_.locked is True

    ev_tardif = EvenementMatch(
        match_id=match_.id, minute=95, type=TypeEvenement.BUT, joueur_id=joueur.id,
        equipe_concernee=EquipeConcernee.DOMICILE, temp_id=uuid.uuid4(),
    )
    db_session.add(ev_tardif)
    await db_session.flush()

    with pytest.raises(HTTPException) as exc_info:
        await valider_evenement(db_session, ev_tardif.id, organisateur.id)
    assert exc_info.value.status_code == 403
