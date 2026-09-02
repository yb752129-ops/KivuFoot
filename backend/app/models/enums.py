"""
Enums partagés. Chaque enum correspond à une contrainte CHECK en base
(voir migrations Alembic) : la validation existe donc à deux niveaux
(application + base de données), ce qui protège l'intégrité des
données même en cas d'écriture directe en base (fiabilité prioritaire).
"""
import enum


class RoleUtilisateur(str, enum.Enum):
    COLLECTEUR = "collecteur"
    ORGANISATEUR = "organisateur"
    CLUB_MANAGER = "club_manager"
    ADMIN = "admin"
    SUPPORTER = "supporter"


class TypeCompetition(str, enum.Enum):
    CHAMPIONNAT = "championnat"
    COUPE = "coupe"
    TOURNOI = "tournoi"


class PosteJoueur(str, enum.Enum):
    GARDIEN = "gardien"
    DEFENSEUR = "defenseur"
    MILIEU = "milieu"
    ATTAQUANT = "attaquant"


class StatutVerificationJoueur(str, enum.Enum):
    VERIFIE = "verifie"
    EN_ATTENTE_VERIFICATION = "en_attente_verification"
    DOUBLON_SUSPECTE = "doublon_suspecte"


class StatutMatch(str, enum.Enum):
    PROGRAMME = "programme"
    EN_COURS = "en_cours"
    TERMINE = "termine"
    VALIDE = "valide"
    CONTESTE = "conteste"


class PeriodeMatch(str, enum.Enum):
    """Phase de jeu — distincte du statut C5. Un match EN COURS a une période."""
    PREMIERE = "1"
    MI_TEMPS = "mi_temps"
    SECONDE = "2"


class EquipeConcernee(str, enum.Enum):
    DOMICILE = "domicile"
    EXTERIEUR = "exterieur"


class TypeEvenement(str, enum.Enum):
    BUT = "but"
    BUT_CONTRE_SON_CAMP = "but_contre_son_camp"
    PASSE_DECISIVE = "passe_decisive"
    CARTON_JAUNE = "carton_jaune"
    CARTON_ROUGE = "carton_rouge"
    REMPLACEMENT = "remplacement"
    PENALTY = "penalty"


class ResultatPenalty(str, enum.Enum):
    MARQUE = "marque"
    RATE = "rate"


class StatutValidationEvenement(str, enum.Enum):
    # NB : 'brut' n'existe QUE côté client (IndexedDB), jamais persisté
    # côté serveur (voir rapport Phase 0, point A2). Dès réception par
    # l'API de synchronisation, le statut serveur est 'en_attente'.
    EN_ATTENTE = "en_attente"
    VALIDE = "valide"
    REJETE = "rejete"


class StatutParticipation(str, enum.Enum):
    TITULAIRE = "titulaire"
    REMPLACANT = "remplacant"


class StatutPropositionModification(str, enum.Enum):
    EN_ATTENTE = "en_attente"
    APPROUVEE = "approuvee"
    REJETEE = "rejetee"


class TypeConsentement(str, enum.Enum):
    PUBLIC = "public"
    STATS = "stats"
    CONTACT = "contact"


class TypeSync(str, enum.Enum):
    EVENEMENT = "evenement"
    MATCH = "match"
    JOUEUR = "joueur"


class StatutSync(str, enum.Enum):
    LOCAL = "local"
    ENVOYE = "envoye"
    CONFIRME = "confirme"


class StatutConflit(str, enum.Enum):
    EN_ATTENTE = "en_attente"
    RESOLU = "resolu"


class ActionAudit(str, enum.Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    VALIDATE = "VALIDATE"
    REJECT = "REJECT"
    MERGE = "MERGE"
