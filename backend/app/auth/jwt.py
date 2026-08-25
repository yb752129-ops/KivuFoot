"""
Gestion des tokens JWT.

- access_token : courte durée de vie (30 min par défaut), stateless,
  contient le rôle et l'id utilisateur.
- refresh_token : plus longue durée, mais son hash est stocké en base
  (table refresh_tokens) pour permettre une vraie révocation au logout
  (gap identifié en Phase 0 - un JWT stateless seul ne peut pas être
  invalidé côté serveur).
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import settings


def create_access_token(user_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token_raw() -> str:
    """Génère un secret opaque (pas un JWT) pour le refresh token."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise ValueError("Token invalide ou expiré.") from exc
    if payload.get("type") != "access":
        raise ValueError("Type de token incorrect.")
    return payload
