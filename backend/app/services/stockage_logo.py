"""Dépôt des logos de clubs dans le bucket Supabase `logos-clubs`.

Le bucket est public en lecture ; l’écriture passe par la clé service,
fournie uniquement par variable d’environnement (jamais en dur).
"""
import httpx

from app.config import settings

EXTS = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "svg": "image/svg+xml"}
MAX_OCTETS = 512 * 1024


class DepotRefus(Exception):
    """Message directement montrable à l’utilisateur."""


async def uploader_logo(club_id: int, nom_fichier: str, data: bytes) -> str:
    if not settings.supabase_url or not settings.supabase_service_role:
        raise DepotRefus("Stockage non configuré côté serveur.")
    ext = nom_fichier.rsplit(".", 1)[-1].lower() if "." in nom_fichier else ""
    if ext not in EXTS:
        raise DepotRefus("Format refusé : PNG, JPG ou SVG seulement.")
    if len(data) > MAX_OCTETS:
        raise DepotRefus("Fichier trop lourd : 512 Ko maximum.")
    base = settings.supabase_url.rstrip("/")
    chemin = f"clubs/{club_id}.{ext}"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{base}/storage/v1/object/logos-clubs/{chemin}",
            content=data,
            headers={
                "Authorization": f"Bearer {settings.supabase_service_role}",
                "Content-Type": EXTS[ext],
                "x-upsert": "true",
            },
        )
    if r.status_code >= 400:
        raise DepotRefus(f"Le stockage a refusé le fichier (code {r.status_code}).")
    return f"{base}/storage/v1/object/public/logos-clubs/{chemin}"
