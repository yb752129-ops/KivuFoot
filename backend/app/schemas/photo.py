from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import MotifRefusPhoto, StatutPhoto


class PhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sujet_type: str
    sujet_id: int
    version: int
    statut: StatutPhoto
    mime_type: str | None
    file_size: int | None
    uploaded_at: datetime | None
    reviewed_at: datetime | None
    motif_refus: MotifRefusPhoto | None
    url: str | None = None


class PhotoEnAttenteOut(PhotoOut):
    sujet_nom: str | None = None
    sujet_club_id: int | None = None
    sujet_poste: str | None = None
    propose_par: str | None = None


class PhotoRejet(BaseModel):
    motif: MotifRefusPhoto
