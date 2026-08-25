import uuid

import pytest
from sqlalchemy import select

from app.models.competition import Competition
from app.models.enums import EquipeConcernee, RoleUtilisateur, TypeEvenement
from app.models.evenement import EvenementMatch
from app.services.detection_doublons import fusionner_joueurs, rechercher_doublons
from app.services.validation import valider_evenement
from tests.factories import creer_club, creer_competition_avec_saison, creer_joueur, creer_match, creer_utilisateur

pytestmark = pytest.mark.asyncio


async def test_detection_doublon_par_nom_et_date_naissance(db_session):
    club = await creer_club(db_session)
    j1 = await creer_joueur(db_session, club.id, "Jean Mucyo")
    await db_session.flush()

    doublons = await rechercher_doublons(db_session, "Jean Mucyo", j1.date_naissance, j1.poste)
    assert len(doublons) == 1
    assert doublons[0].id == j1.id


async def test_fusion_transfere_les_evenements_et_marque_esclave(db_session):
    organisateur = await creer_utilisateur(db_session, RoleUtilisateur.ORGANISATEUR, "orga.fusion@test.local")
    _, saison = await creer_competition_avec_saison(db_session, organisateur)
    club_a = await creer_club(db_session, "Club A")
    club_b = await creer_club(db_session, "Club B")
    maitre = await creer_joueur(db_session, club_a.id, "Joueur Maître")
    esclave = await creer_joueur(db_session, club_a.id, "Joueur Doublon")
    match_ = await creer_match(db_session, saison.id, club_a.id, club_b.id)
    await db_session.flush()

    ev = EvenementMatch(
        match_id=match_.id, minute=15, type=TypeEvenement.BUT, joueur_id=esclave.id,
        equipe_concernee=EquipeConcernee.DOMICILE, temp_id=uuid.uuid4(),
    )
    db_session.add(ev)
    await db_session.flush()

    await fusionner_joueurs(db_session, maitre.id, esclave.id)
    await db_session.flush()
    await db_session.refresh(ev)
    await db_session.refresh(esclave)

    assert ev.joueur_id == maitre.id  # événement transféré
    assert esclave.fusionne is True
    assert esclave.fusionne_vers_id == maitre.id


async def test_impossible_de_fusionner_un_joueur_deja_fusionne(db_session):
    club = await creer_club(db_session)
    maitre = await creer_joueur(db_session, club.id, "Maître")
    esclave = await creer_joueur(db_session, club.id, "Esclave")
    autre = await creer_joueur(db_session, club.id, "Autre")
    await db_session.flush()

    await fusionner_joueurs(db_session, maitre.id, esclave.id)
    await db_session.flush()

    with pytest.raises(ValueError):
        await fusionner_joueurs(db_session, autre.id, esclave.id)


async def test_competition_demo_est_bien_marquee_et_filtrable(db_session):
    """Règle non négociable : les données DEMO doivent être clairement identifiées et séparables."""
    competition_demo, _ = await creer_competition_avec_saison(db_session, est_demo=True)
    competition_reelle = Competition(nom="Ligue régionale de test", type=competition_demo.type, est_demo=False)
    db_session.add(competition_reelle)
    await db_session.flush()

    result = await db_session.execute(select(Competition).where(Competition.est_demo.is_(False)))
    non_demo = result.scalars().all()

    assert competition_demo.nom.startswith("DEMO - ")
    assert all(not c.est_demo for c in non_demo)
    assert competition_demo.id not in [c.id for c in non_demo]
