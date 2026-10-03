"""Stockage des PDF officiels, distinct du stockage des photos."""
from __future__ import annotations

import httpx

from app.config import settings

BUCKET = "documents-kivufoot"


class DepotDocumentRefus(Exception):
    pass


def url_publique(storage_key: str) -> str:
    base = (settings.supabase_url or "").rstrip("/")
    return f"{base}/storage/v1/object/public/{BUCKET}/{storage_key}"


async def _assurer_bucket(client: httpx.AsyncClient, base: str, cle: str) -> None:
    headers = {"Authorization": f"Bearer {cle}", "apikey": cle}
    response = await client.get(f"{base}/storage/v1/bucket/{BUCKET}", headers=headers)
    if response.status_code == 200:
        return
    response = await client.post(
        f"{base}/storage/v1/bucket",
        json={"id": BUCKET, "name": BUCKET, "public": True},
        headers={**headers, "Content-Type": "application/json"},
    )
    if response.status_code >= 400 and response.status_code not in (400, 409):
        raise DepotDocumentRefus(f"Impossible de préparer le stockage des documents (code {response.status_code}).")


async def uploader_document(storage_key: str, data: bytes) -> tuple[str, int]:
    if not settings.supabase_url or not settings.supabase_service_role:
        raise DepotDocumentRefus("Stockage des documents non configuré côté serveur.")
    if not data or len(data) > 25 * 1024 * 1024:
        raise DepotDocumentRefus("PDF vide ou supérieur à 25 Mo.")
    base = settings.supabase_url.rstrip("/")
    key = settings.supabase_service_role
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            await _assurer_bucket(client, base, key)
            response = await client.post(
                f"{base}/storage/v1/object/{BUCKET}/{storage_key}",
                content=data,
                headers={
                    "Authorization": f"Bearer {key}",
                    "apikey": key,
                    "Content-Type": "application/pdf",
                    "x-upsert": "true",
                },
            )
    except httpx.HTTPError as exc:
        raise DepotDocumentRefus("Le stockage des documents est momentanément indisponible.") from exc
    if response.status_code >= 400:
        raise DepotDocumentRefus(f"Le stockage a refusé le PDF (code {response.status_code}).")
    return storage_key, len(data)
