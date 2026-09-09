"""Dépôt des photos officielles (joueurs, staff) dans le bucket Supabase
`photos-kivufoot`. Lecture publique, écriture par la clé service seulement.

Le bucket est créé automatiquement au premier dépôt s'il n'existe pas
(publique en lecture) : aucun geste manuel n'est nécessaire.
"""
import httpx

from app.config import settings

BUCKET = "photos-kivufoot"
MIMES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MAX_OCTETS = 2 * 1024 * 1024


class DepotRefus(Exception):
    """Message directement montrable à l'utilisateur."""


def url_publique(storage_key: str) -> str:
    base = (settings.supabase_url or "").rstrip("/")
    return f"{base}/storage/v1/object/public/{BUCKET}/{storage_key}"


async def _assurer_bucket(client: httpx.AsyncClient, base: str, cle: str) -> None:
    r = await client.post(
        f"{base}/storage/v1/bucket",
        json={"id": BUCKET, "name": BUCKET, "public": True},
        headers={"Authorization": f"Bearer {cle}", "apikey": cle, "Content-Type": "application/json"},
    )
    # 409 = le bucket existe déjà : c'est le cas nominal.
    if r.status_code >= 400 and r.status_code != 409:
        raise DepotRefus(f"Impossible de préparer le stockage (code {r.status_code}).")


async def uploader_photo(sujet_type: str, sujet_id: int, version: int, mime: str, data: bytes) -> tuple[str, int]:
    """Dépose le fichier et renvoie (storage_key, taille). Ne valide rien."""
    if not settings.supabase_url or not settings.supabase_service_role:
        raise DepotRefus("Stockage non configuré côté serveur.")
    if mime not in MIMES:
        raise DepotRefus("Format refusé : JPG, PNG ou WEBP seulement.")
    if len(data) > MAX_OCTETS:
        raise DepotRefus("Fichier trop lourd : 2 Mo maximum.")
    if len(data) == 0:
        raise DepotRefus("Fichier vide.")
    base = settings.supabase_url.rstrip("/")
    cle = settings.supabase_service_role
    dossier = "joueurs" if sujet_type == "joueur" else "coachs"
    key = f"{dossier}/{sujet_id}/v{version}{MIMES[mime]}"
    async with httpx.AsyncClient(timeout=60) as client:
        await _assurer_bucket(client, base, cle)
        r = await client.post(
            f"{base}/storage/v1/object/{BUCKET}/{key}",
            content=data,
            headers={
                "Authorization": f"Bearer {cle}",
                "apikey": cle,
                "Content-Type": mime,
                "x-upsert": "true",
            },
        )
    if r.status_code >= 400:
        detail = r.text[:180]
        raise DepotRefus(f"Le stockage a refusé le fichier (code {r.status_code}) : {detail}")
    return key, len(data)
