"""
Détection de doublons (§7.2) et fusion de joueurs (§7.3, admin uniquement).
"""
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import StatutVerificationJoueur
from app.models.evenement import EvenementMatch
from app.models.joueur import Joueur
from app.models.match import MatchParticipation
from app.models.stats import StatistiqueJoueur


async def rechercher_doublons(
    db: AsyncSession, nom_complet: str, date_naissance: date, poste: str | None
) -> list[Joueur]:
    """Recherche sur nom_complet + date_naissance + poste (règle §7.1)."""
    query = select(Joueur).where(
        func.lower(Joueur.nom_complet) == nom_complet.strip().lower(),
        Joueur.date_naissance == date_naissance,
        Joueur.fusionne.is_(False),
    )
    if poste:
        query = query.where(Joueur.poste == poste)
    result = await db.execute(query)
    return list(result.scalars().all())


async def fusionner_joueurs(db: AsyncSession, joueur_maitre_id: int, joueur_esclave_id: int) -> Joueur:
    """
    Transfère tous les événements, participations et statistiques du
    joueur "esclave" vers le joueur "maître", puis marque l'esclave
    comme fusionné (§7.3). Opération réservée à l'admin (vérifié en
    amont dans la route). Un match validé/locked n'empêche PAS la
    fusion : c'est une correction de référentiel joueur, pas une
    modification du fait sportif lui-même.
    """
    maitre = await db.get(Joueur, joueur_maitre_id)
    esclave = await db.get(Joueur, joueur_esclave_id)
    if maitre is None or esclave is None:
        raise ValueError("Joueur maître ou esclave introuvable.")
    if esclave.fusionne:
        raise ValueError("Ce joueur a déjà été fusionné.")

    # Transfert des événements
    await db.execute(
        EvenementMatch.__table__.update()
        .where(EvenementMatch.joueur_id == joueur_esclave_id)
        .values(joueur_id=joueur_maitre_id)
    )
    await db.execute(
        EvenementMatch.__table__.update()
        .where(EvenementMatch.joueur_secondaire_id == joueur_esclave_id)
        .values(joueur_secondaire_id=joueur_maitre_id)
    )
    # Transfert des participations
    await db.execute(
        MatchParticipation.__table__.update()
        .where(MatchParticipation.joueur_id == joueur_esclave_id)
        .values(joueur_id=joueur_maitre_id)
    )

    # Fusion des statistiques déjà calculées (sommées par compétition/saison)
    result = await db.execute(select(StatistiqueJoueur).where(StatistiqueJoueur.joueur_id == joueur_esclave_id))
    stats_esclave = result.scalars().all()
    for s_esclave in stats_esclave:
        result_maitre = await db.execute(
            select(StatistiqueJoueur).where(
                StatistiqueJoueur.joueur_id == joueur_maitre_id,
                StatistiqueJoueur.competition_id == s_esclave.competition_id,
                StatistiqueJoueur.saison_id == s_esclave.saison_id,
            )
        )
        s_maitre = result_maitre.scalar_one_or_none()
        if s_maitre is None:
            s_maitre = StatistiqueJoueur(
                joueur_id=joueur_maitre_id,
                competition_id=s_esclave.competition_id,
                saison_id=s_esclave.saison_id,
            )
            db.add(s_maitre)
            await db.flush()
        s_maitre.matchs_joues += s_esclave.matchs_joues
        s_maitre.titularisations += s_esclave.titularisations
        s_maitre.buts += s_esclave.buts
        s_maitre.passes_decisives += s_esclave.passes_decisives
        s_maitre.cartons_jaunes += s_esclave.cartons_jaunes
        s_maitre.cartons_rouges += s_esclave.cartons_rouges
        s_maitre.minutes_jouees += s_esclave.minutes_jouees
        await db.delete(s_esclave)

    esclave.fusionne = True
    esclave.fusionne_vers_id = joueur_maitre_id
    return maitre
