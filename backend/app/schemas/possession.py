import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import (
    EtatPossession,
    MethodePossession,
    ProtocolePossession,
    StatutPossession,
)


class PossessionTransitionCreate(BaseModel):
    """Commande idempotente envoyée par le chronomètre terrain."""

    operation_id: uuid.UUID
    etat: EtatPossession
    correction: bool = False


class PossessionCorrectionCreate(BaseModel):
    """Correction append-only d'un intervalle déjà fermé."""

    operation_id: uuid.UUID
    intervalle_id: int
    etat: EtatPossession
    debut_at: datetime | None = None
    fin_at: datetime | None = None
    motif: str = Field(min_length=10, max_length=1000)

    @field_validator("etat")
    @classmethod
    def etat_corrigeable(cls, value: EtatPossession) -> EtatPossession:
        if value not in (EtatPossession.TEAM_A, EtatPossession.TEAM_B, EtatPossession.PAUSE):
            raise ValueError("Une correction porte sur A, B ou PAUSE, jamais sur l'état final.")
        return value


class PossessionIntervalleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    etat: EtatPossession
    sequence_no: int
    debut_at: datetime
    fin_at: datetime | None
    duree_ms: int
    duree_secondes: float = 0
    periode: str | None
    cree_par_id: int | None


class PossessionDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None
    match_id: int
    equipe_a_id: int | None
    equipe_b_id: int | None
    equipe_a_nom: str | None = None
    equipe_b_nom: str | None = None
    mapping: str = "TEAM_A=domicile, TEAM_B=extérieur"
    methode: MethodePossession
    protocole: ProtocolePossession
    etat_courant: EtatPossession
    pause_hors_jeu: bool = False
    statut: StatutPossession
    # Noms métier lisibles (secondes) + millisecondes exactes pour audit.
    temps_a: float = 0
    temps_b: float = 0
    temps_non_attribue: float = 0
    temps_a_ms: int = 0
    temps_b_ms: int = 0
    temps_non_attribue_ms: int = 0
    temps_a_secondes: float = 0
    temps_b_secondes: float = 0
    temps_non_attribue_secondes: float = 0
    temps_mesure_ms: int = 0
    pourcentage_a: int | None = None
    pourcentage_b: int | None = None
    nombre_changements: int = 0
    nombre_sequences_a: int = 0
    nombre_sequences_b: int = 0
    collecteur_id: int | None = None
    valide_par_id: int | None = None
    officialisee_at: datetime | None = None
    derniere_transition_at: datetime | None = None
    intervalle_ouvert_depuis: datetime | None = None
    eligible_public: bool = True
    motif_exclusion_public: str | None = None
    est_disponible: bool = False
    message: str | None = None
    intervalles: list[PossessionIntervalleOut] = Field(default_factory=list)


class PossessionPublicOut(BaseModel):
    """Réponse sans chronologie ni identifiants de collecte pour le public."""

    match_id: int
    disponible: bool
    message: str
    equipe_a_id: int | None = None
    equipe_b_id: int | None = None
    equipe_a_nom: str | None = None
    equipe_b_nom: str | None = None
    mapping: str = "TEAM_A=domicile, TEAM_B=extérieur"
    statut: StatutPossession | None = None
    protocole: ProtocolePossession = ProtocolePossession.KIVUFOOT_POSSESSION_V1
    temps_a: float | None = None
    temps_b: float | None = None
    temps_non_attribue: float | None = None
    temps_a_ms: int | None = None
    temps_b_ms: int | None = None
    temps_mesure_ms: int | None = None
    pourcentage_a: int | None = None
    pourcentage_b: int | None = None
