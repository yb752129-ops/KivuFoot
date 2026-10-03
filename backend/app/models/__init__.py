"""
Regroupe tous les modèles pour garantir qu'ils sont enregistrés auprès de
Base.metadata avant toute génération de migration Alembic ou création de
tables. Importer `app.models` suffit à charger l'intégralité du schéma.
"""
from app.models.actualite import Actualite, ActualiteImage, ActualiteLecture, ActualiteLike, HommeMatch
from app.models.audit import AuditLog
from app.models.club import Club
from app.models.competition import Competition, OrganisateurCompetition, Saison, SaisonClub
from app.models.document import DocumentOfficiel
from app.models.effectif import EffectifClub
from app.models.evenement import EvenementMatch
from app.models.joueur import Joueur, JoueurModificationProposee
from app.models.photo import Photo
from app.models.possession import PossessionCorrection, PossessionIntervalle, PossessionMatch, PossessionOperation
from app.models.staff import Staff
from app.models.match import Match, MatchParticipation
from app.models.stats import Consentement, StatistiqueJoueur
from app.models.sport_engine import (
    AnomalieHistorique,
    ControleValidationMatch,
    DecisionSportive,
    EffectifVersion,
    EffectifVersionJoueur,
    ReglementVersion,
    SanctionDisciplinaire,
    SanctionMatch,
)
from app.models.sync import ConflitSynchronisation, StockageSynchronisation
from app.models.user import RefreshToken, User

__all__ = [
    "Actualite",
    "ActualiteImage",
    "ActualiteLike",
    "ActualiteLecture",
    "HommeMatch",
    "AuditLog",
    "Club",
    "DocumentOfficiel",
    "Competition",
    "OrganisateurCompetition",
    "Saison",
    "SaisonClub",
    "EffectifClub",
    "EvenementMatch",
    "Joueur",
    "JoueurModificationProposee",
    "Photo",
    "PossessionMatch",
    "PossessionIntervalle",
    "PossessionOperation",
    "PossessionCorrection",
    "Staff",
    "Match",
    "MatchParticipation",
    "Consentement",
    "StatistiqueJoueur",
    "ReglementVersion",
    "EffectifVersion",
    "EffectifVersionJoueur",
    "SanctionDisciplinaire",
    "SanctionMatch",
    "DecisionSportive",
    "ControleValidationMatch",
    "AnomalieHistorique",
    "ConflitSynchronisation",
    "StockageSynchronisation",
    "RefreshToken",
    "User",
]
