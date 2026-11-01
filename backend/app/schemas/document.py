from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type_document: str
    scope_id: int
    competition_id: int | None
    saison_id: int | None
    version: int
    statut: str
    titre: str
    empreinte_source: str
    storage_key: str | None
    message_erreur: str | None
    genere_par_id: int | None
    publie_par_id: int | None
    created_at: datetime
    published_at: datetime | None
    url: str | None = None
