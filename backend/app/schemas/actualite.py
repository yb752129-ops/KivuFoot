from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import CategorieActualite, StatutActualite


class ActualiteCreate(BaseModel):
    titre: str = Field(min_length=3, max_length=180)
    categorie: CategorieActualite
    texte: str = Field(min_length=10, max_length=20000)
    competition_id: int | None = None
    saison_id: int | None = None
    journee: str | None = Field(default=None, max_length=30)
    match_id: int | None = None
    club_id: int | None = None
    joueur_id: int | None = None
    telechargement_autorise: bool = True

    @field_validator("titre", "texte", "journee")
    @classmethod
    def texte_normalise(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ActualiteUpdate(BaseModel):
    titre: str | None = Field(default=None, min_length=3, max_length=180)
    categorie: CategorieActualite | None = None
    texte: str | None = Field(default=None, min_length=10, max_length=20000)
    competition_id: int | None = None
    saison_id: int | None = None
    journee: str | None = Field(default=None, max_length=30)
    match_id: int | None = None
    club_id: int | None = None
    joueur_id: int | None = None
    telechargement_autorise: bool | None = None

    @field_validator("titre", "texte", "journee")
    @classmethod
    def texte_normalise(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ActualiteImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    mime_type: str | None
    file_size: int | None
    ordre: int
    principale: bool
    telechargement_autorise: bool


class ActualiteMatchOut(BaseModel):
    id: int
    journee: str | None
    date_heure: datetime
    stade: str | None
    equipe_domicile_id: int | None
    equipe_domicile_nom: str | None
    equipe_exterieur_id: int | None
    equipe_exterieur_nom: str | None
    score_domicile: int
    score_exterieur: int
    statut: str
    groupe: str | None


class ActualiteJoueurOut(BaseModel):
    id: int
    nom_complet: str
    club_id: int | None
    club_nom: str | None
    photo_url: str | None = None


class HommeMatchOut(BaseModel):
    id: int
    match_id: int
    joueur_id: int
    joueur_nom: str
    club_id: int
    club_nom: str
    joueur_photo_url: str | None = None
    designe_par_id: int | None
    designe_at: datetime


class ActualiteListOut(BaseModel):
    id: int
    titre: str
    categorie: CategorieActualite
    statut: StatutActualite
    image_principale_url: str | None = None
    date_creation: datetime
    date_publication: datetime | None
    competition_id: int | None
    competition_nom: str | None
    saison_id: int | None
    saison_nom: str | None
    match_id: int | None
    joueur_id: int | None
    joueur_nom: str | None
    like_count: int = 0


class ActualiteDetailOut(ActualiteListOut):
    texte: str
    auteur_id: int | None
    auteur_nom: str | None
    journee: str | None
    club_id: int | None
    club_nom: str | None
    telechargement_autorise: bool
    images: list[ActualiteImageOut] = []
    match: ActualiteMatchOut | None = None
    joueur: ActualiteJoueurOut | None = None
    homme_match: HommeMatchOut | None = None
    liked: bool = False


class LikePayload(BaseModel):
    client_token: str = Field(min_length=16, max_length=128)


class LikeOut(BaseModel):
    actualite_id: int
    liked: bool
    like_count: int


class HommeMatchCreate(BaseModel):
    joueur_id: int
