"""Stockage des images éditoriales d'actualités.

Le bucket public existant `photos-kivufoot` est réutilisé, avec un préfixe
séparé. Les actualités ne réutilisent pas la table Photo des joueurs : cela
permet de distinguer clairement une photo de profil d'une photo éditoriale.
"""
from uuid import uuid4

import httpx

from app.config import settings
from app.services.stockage_photo import BUCKET, MIMES, _assurer_bucket, url_publique

MAX_OCTETS = 10 * 1024 * 1024


class ActualiteDepotRefus(Exception):
    """Erreur sûre et montrable à l'auteur de l'actualité."""


async def uploader_image_actualite(actualite_id: int, mime: str, data: bytes) -> tuple[str, int]:
    if not settings.supabase_url or not settings.supabase_service_role:
        raise ActualiteDepotRefus("Stockage non configuré côté serveur.")
    if mime not in MIMES:
        raise ActualiteDepotRefus("Format refusé : JPG, PNG ou WEBP seulement.")
    if not data:
        raise ActualiteDepotRefus("Fichier vide.")
    if len(data) > MAX_OCTETS:
        raise ActualiteDepotRefus("Fichier trop lourd : 10 Mo maximum.")

    extension = MIMES[mime]
    key = f"actualites/{actualite_id}/{uuid4().hex}{extension}"
    base = settings.supabase_url.rstrip("/")
    cle = settings.supabase_service_role
    async with httpx.AsyncClient(timeout=60) as client:
        await _assurer_bucket(client, base, cle)
        response = await client.post(
            f"{base}/storage/v1/object/{BUCKET}/{key}",
            content=data,
            headers={
                "Authorization": f"Bearer {cle}",
                "apikey": cle,
                "Content-Type": mime,
                "x-upsert": "false",
            },
        )
    if response.status_code >= 400:
        raise ActualiteDepotRefus(
            f"Le stockage a refusé le fichier (code {response.status_code})."
        )
    return key, len(data)


__all__ = ["ActualiteDepotRefus", "MAX_OCTETS", "uploader_image_actualite", "url_publique"]
