from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PointsReglement(BaseModel):
    victoire: int | None = Field(default=None, ge=0)
    nul: int | None = Field(default=None, ge=0)
    defaite: int | None = Field(default=None, ge=0)
    forfait_victoire: int | None = Field(default=None, ge=0)
    forfait_defaite: int | None = Field(default=None, ge=0)


class CompositionReglement(BaseModel):
    titulaires_min: int | None = Field(default=None, ge=0, le=99)
    titulaires_max: int | None = Field(default=None, ge=0, le=99)
    remplacants_min: int | None = Field(default=None, ge=0, le=99)
    remplacants_max: int | None = Field(default=None, ge=0, le=99)
    changements_max: int | None = Field(default=None, ge=0, le=99)


class DisciplineReglement(BaseModel):
    jaunes_pour_suspension: int | None = Field(default=None, ge=1, le=99)
    suspension_apres_rouge: int | None = Field(default=None, ge=1, le=99)
    suspension_apres_deuxieme_jaune: int | None = Field(default=None, ge=1, le=99)
    duree_accumulation: int | None = Field(default=None, ge=1, le=99)
    portee_accumulation: Literal["saison", "edition", "competition"] | None = None
    mode_decision: Literal["automatique", "confirmation_comite"] = "confirmation_comite"


class QualificationReglement(BaseModel):
    groupes: int | None = Field(default=None, ge=1)
    qualifies_par_groupe: int | None = Field(default=None, ge=0)
    meilleurs_suivants: int | None = Field(default=None, ge=0)
    criteres_departage: list[str] = Field(default_factory=list)
    # Le Comité peut déclarer le calendrier complet avant d'autoriser une
    # projection de qualification. Faux par défaut : les résultats partiels
    # ne fabriquent jamais un qualifié.
    calendrier_complet: bool = False
    intervention_comite: bool = True


class ReglementConfiguration(BaseModel):
    """Configuration volontairement incomplète par défaut.

    Une valeur absente signifie « règle non fournie », jamais une règle
    inventée par la plateforme. Les champs supplémentaires sont conservés
    afin de permettre les règles propres à une compétition.
    """

    model_config = ConfigDict(extra="allow")

    mode_moteur: Literal["legacy", "report_only", "enforced"] = "report_only"
    points: PointsReglement | None = None
    departages: list[str] = Field(default_factory=list)
    groupes: dict[str, Any] | None = None
    composition: CompositionReglement | None = None
    discipline: DisciplineReglement | None = None
    qualification: QualificationReglement | None = None
    match: dict[str, Any] = Field(default_factory=dict)
    forfait: dict[str, Any] = Field(default_factory=dict)


class ReglementCreate(BaseModel):
    competition_id: int
    saison_id: int
    version: int = Field(ge=1)
    configuration: ReglementConfiguration
    source_officielle: str | None = Field(default=None, max_length=5000)
    reference_decision: str | None = Field(default=None, max_length=255)
    date_effet: date | None = None
    date_fin: date | None = None


class ReglementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    competition_id: int
    saison_id: int
    version: int
    statut: str
    schema_version: str
    configuration: dict
    source_officielle: str | None
    reference_decision: str | None
    date_effet: date | None
    date_fin: date | None
    cree_par_id: int | None
    active_par_id: int | None
    activated_at: datetime | None
    closed_at: datetime | None


class ReglementSimulationRequest(BaseModel):
    configuration: ReglementConfiguration


class RattachementReglementRequest(BaseModel):
    match_ids: list[int] = Field(min_length=1, max_length=500)
    motif: str = Field(min_length=10, max_length=2000)


class EligibiliteOut(BaseModel):
    joueur_id: int
    joueur_nom: str | None = None
    club_id: int | None = None
    statut: Literal["OK", "ATTENTION", "BLOQUANT"]
    code: str
    message: str
    sources: list[dict] = Field(default_factory=list)


class ControleOut(BaseModel):
    code: str
    libelle: str
    statut: Literal["OK", "ATTENTION", "BLOQUANT"]
    message: str
    sources: list[dict] = Field(default_factory=list)


class ChecklistOut(BaseModel):
    match_id: int
    resultat: Literal["OK", "ATTENTION", "BLOQUANT"]
    mode: str
    reglement_version_id: int | None = None
    controles: list[ControleOut]
    generated_at: datetime


class AnomalieOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    saison_id: int
    match_id: int | None
    joueur_id: int | None
    club_id: int | None
    type_anomalie: str
    severite: str
    statut: str
    observation: dict
    empreinte: str
    decision: str | None
    decide_par_id: int | None
    decide_at: datetime | None
    created_at: datetime
    updated_at: datetime | None


class AnomalieUpdate(BaseModel):
    statut: Literal[
        "a_examiner",
        "confirmee",
        "derogation_officielle",
        "corrigee_par_decision_officielle",
    ]
    decision: str = Field(min_length=10, max_length=3000)


class DisciplineOut(BaseModel):
    joueur_id: int
    saison_id: int
    reglement_version_id: int | None
    jaunes_valides: int
    rouges_valides: int
    sanctions: list[dict] = Field(default_factory=list)
    statut: Literal["OK", "ATTENTION", "BLOQUANT"]
    message: str
    sources: list[dict] = Field(default_factory=list)


class DecisionSportiveCreate(BaseModel):
    type_decision: str = Field(min_length=3, max_length=50)
    action: Literal["confirmer", "modifier", "annuler", "prolonger", "autoriser_participation"]
    motif: str = Field(min_length=10, max_length=3000)
    details: dict | None = None


class DecisionSportiveOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    competition_id: int | None
    saison_id: int | None
    match_id: int | None
    joueur_id: int | None
    club_id: int | None
    sanction_id: int | None
    anomalie_id: int | None
    type_decision: str
    action: str
    statut: str
    motif: str
    details: dict | None
    decide_par_id: int | None
    created_at: datetime
