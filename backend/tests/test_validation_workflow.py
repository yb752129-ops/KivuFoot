import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.models.enums import EquipeConcernee, ResultatPenalty, StatutMatch, StatutValidationEvenement, TypeEvenement
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


async def test_csc_schema_interdit_passeur():
    from pydantic import ValidationError
    from app.schemas.evenement import EvenementCreate

    with pytest.raises(ValidationError):
        EvenementCreate(
            temp_id=uuid.uuid4(),
            minute=12,
            type=TypeEvenement.BUT_CONTRE_SON_CAMP,
            joueur_id=1,
            joueur_secondaire_id=2,
            equipe_concernee=EquipeConcernee.DOMICILE,
        )


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


async def test_refus_arbitral_inverse_score_et_conserve_levenement(db_session):
    from app.models.enums import MotifRefusArbitral
    from app.services.validation import refuser_evenement_arbitral

    organisateur, _, _, _, _, joueur, match_ = await _setup_match_avec_joueur(db_session)
    ev = EvenementMatch(
        match_id=match_.id, minute=17, type=TypeEvenement.BUT, joueur_id=joueur.id,
        equipe_concernee=EquipeConcernee.DOMICILE, temp_id=uuid.uuid4(),
    )
    db_session.add(ev)
    await db_session.flush()
    await valider_evenement(db_session, ev.id, organisateur.id)
    await db_session.flush()
    assert match_.score_domicile == 1

    await refuser_evenement_arbitral(db_session, ev.id, MotifRefusArbitral.HORS_JEU, organisateur.id)
    await db_session.flush()
    assert match_.score_domicile == 0
    assert ev.refuse is True
    assert ev.locked is True
    assert ev.statut_validation == StatutValidationEvenement.VALIDE
    stats = (await db_session.execute(
        select(StatistiqueJoueur).where(StatistiqueJoueur.joueur_id == joueur.id)
    )).scalar_one()
    assert stats.buts == 0
    assert ev.type == TypeEvenement.BUT
    assert ev.joueur_id == joueur.id


async def test_refus_arbitral_cascade_passe_decisive(db_session):
    from app.models.enums import MotifRefusArbitral
    from app.services.validation import refuser_evenement_arbitral

    organisateur, _, _, club_a, _, joueur, match_ = await _setup_match_avec_joueur(db_session)
    passeur = await creer_joueur(db_session, club_a.id, "Passeur Test")
    ev = EvenementMatch(
        match_id=match_.id, minute=22, type=TypeEvenement.BUT, joueur_id=joueur.id,
        joueur_secondaire_id=passeur.id, equipe_concernee=EquipeConcernee.DOMICILE, temp_id=uuid.uuid4(),
    )
    db_session.add(ev)
    await db_session.flush()
    await valider_evenement(db_session, ev.id, organisateur.id)
    await db_session.flush()
    assert match_.score_domicile == 1

    await refuser_evenement_arbitral(db_session, ev.id, MotifRefusArbitral.MAIN, organisateur.id)
    await db_session.flush()
    assert match_.score_domicile == 0
    passes = (await db_session.execute(
        select(EvenementMatch).where(
            EvenementMatch.match_id == match_.id,
            EvenementMatch.type == TypeEvenement.PASSE_DECISIVE,
        )
    )).scalars().all()
    assert len(passes) == 1
    assert passes[0].refuse is True
    assert passes[0].statut_validation == StatutValidationEvenement.VALIDE
    stats_p = (await db_session.execute(
        select(StatistiqueJoueur).where(StatistiqueJoueur.joueur_id == passeur.id)
    )).scalar_one()
    assert stats_p.passes_decisives == 0


async def test_refus_arbitral_interdit_si_match_verrouille(db_session):
    from app.models.enums import MotifRefusArbitral
    from app.services.validation import refuser_evenement_arbitral

    organisateur, _, _, _, _, joueur, match_ = await _setup_match_avec_joueur(db_session)
    ev = EvenementMatch(
        match_id=match_.id, minute=8, type=TypeEvenement.BUT, joueur_id=joueur.id,
        equipe_concernee=EquipeConcernee.DOMICILE, temp_id=uuid.uuid4(),
    )
    db_session.add(ev)
    await db_session.flush()
    await valider_evenement(db_session, ev.id, organisateur.id)
    await db_session.flush()
    match_.locked = True
    await db_session.flush()

    with pytest.raises(HTTPException) as exc_info:
        await refuser_evenement_arbitral(db_session, ev.id, MotifRefusArbitral.HORS_JEU, organisateur.id)
    assert exc_info.value.status_code == 403
    assert match_.score_domicile == 1
    assert ev.refuse is False


async def test_match_verrouille_apres_validation_bloque_nouveaux_evenements(db_session):
    organisateur, _, _, _, _, joueur, match_ = await _setup_match_avec_joueur(db_session)
    match_.statut = StatutMatch.TERMINE
    await db_session.flush()
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
