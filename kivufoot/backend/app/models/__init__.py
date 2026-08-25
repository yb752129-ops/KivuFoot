"""
Regroupe tous les modèles pour garantir qu'ils sont enregistrés auprès de
Base.metadata avant toute génération de migration Alembic ou création de
tables. Importer `app.models` suffit à charger l'intégralité du schéma.
"""
from app.models.audit import AuditLog
from app.models.club import Club
from app.models.competition import Competition, OrganisateurCompetition, Saison, SaisonClub
from app.models.evenement import EvenementMatch
from app.models.joueur import Joueur, JoueurModificationProposee
from app.models.match import Match, MatchParticipation
from app.models.stats import Consentement, StatistiqueJoueur
from app.models.sync import ConflitSynchronisation, StockageSynchronisation
from app.models.user import RefreshToken, User

__all__ = [
    "AuditLog",
    "Club",
    "Competition",
    "OrganisateurCompetition",
    "Saison",
    "SaisonClub",
    "EvenementMatch",
    "Joueur",
    "JoueurModificationProposee",
    "Match",
    "MatchParticipation",
    "Consentement",
    "StatistiqueJoueur",
    "ConflitSynchronisation",
    "StockageSynchronisation",
    "RefreshToken",
    "User",
]
