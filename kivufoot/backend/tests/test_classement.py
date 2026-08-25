import pytest

from app.models.enums import StatutMatch
from app.services.calcul_classement import calculer_classement
from tests.factories import creer_club, creer_competition_avec_saison, creer_match

pytestmark = pytest.mark.asyncio


async def test_classement_ignore_matchs_non_valides(db_session):
    _, saison = await creer_competition_avec_saison(db_session)
    club_a = await creer_club(db_session, "Club A")
    club_b = await creer_club(db_session, "Club B")
    match_ = await creer_match(db_session, saison.id, club_a.id, club_b.id)
    match_.score_domicile = 3
    match_.score_exterieur = 0
    match_.statut = StatutMatch.TERMINE  # PAS validé
    await db_session.flush()

    classement = await calculer_classement(db_session, saison.id)

    assert classement == []  # aucun match validé -> classement vide


async def test_classement_points_et_tri(db_session):
    _, saison = await creer_competition_avec_saison(db_session)
    club_a = await creer_club(db_session, "Club A")
    club_b = await creer_club(db_session, "Club B")
    club_c = await creer_club(db_session, "Club C")

    # A bat B 2-0 (validé)
    m1 = await creer_match(db_session, saison.id, club_a.id, club_b.id)
    m1.score_domicile, m1.score_exterieur, m1.statut = 2, 0, StatutMatch.VALIDE

    # B et C font match nul 1-1 (validé)
    m2 = await creer_match(db_session, saison.id, club_b.id, club_c.id)
    m2.score_domicile, m2.score_exterieur, m2.statut = 1, 1, StatutMatch.VALIDE

    await db_session.flush()

    classement = await calculer_classement(db_session, saison.id)
    par_club = {l.club_nom: l for l in classement}

    assert par_club["Club A"].points == 3
    assert par_club["Club B"].points == 1
    assert par_club["Club C"].points == 1
    # Club A a la meilleure différence de buts -> premier du classement
    assert classement[0].club_nom == "Club A"


async def test_classement_forfait_compte_dans_le_score(db_session):
    """Un forfait (3-0 tracé) doit être compté dans le classement comme un résultat normal une fois le match validé."""
    _, saison = await creer_competition_avec_saison(db_session)
    club_a = await creer_club(db_session, "Club A")
    club_b = await creer_club(db_session, "Club B")
    m1 = await creer_match(db_session, saison.id, club_a.id, club_b.id)
    m1.score_domicile, m1.score_exterieur = 3, 0
    m1.forfait = True
    m1.forfait_equipe = "exterieur"
    m1.statut = StatutMatch.VALIDE
    await db_session.flush()

    classement = await calculer_classement(db_session, saison.id)
    par_club = {l.club_nom: l for l in classement}
    assert par_club["Club A"].points == 3
    assert par_club["Club B"].points == 0
