"""
Configuration de l'application KivuFoot.

Toutes les valeurs sensibles proviennent de variables d'environnement.
Aucun secret ne doit jamais être écrit en dur ici (règle non négociable
de la spécification).
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    app_name: str = "KivuFoot API"
    environment: str = "development"  # development | staging | production
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Base de données
    database_url: str = "postgresql+asyncpg://kivufoot:kivufoot@localhost:5432/kivufoot"
    database_url_sync: str = "postgresql+psycopg2://kivufoot:kivufoot@localhost:5432/kivufoot"

    # Sécurité / JWT
    secret_key: str  # OBLIGATOIRE - aucune valeur par défaut pour un secret
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # CORS
    cors_allow_origins: str = "http://localhost:5173"

    # Stockage fichiers (logos clubs, etc.) - optionnel V1
    s3_bucket: str | None = None
    s3_key: str | None = None
    s3_secret: str | None = None
    s3_endpoint: str | None = None

    # Redis - explicitement DIFFÉRÉ en V1 (voir rapport Phase 0/1).
    # Conservé en config pour ne pas casser le déploiement si activé plus tard.
    redis_url: str | None = None

    # Divers
    default_locale: str = "fr"
    supported_locales: str = "fr,sw"  # français par défaut, swahili prévu (i18n)
    pagination_default_limit: int = 20
    pagination_max_limit: int = 100
    rate_limit_login_per_minute: int = 5

    @property
    def cors_origins_list(self) -> list[str]:
        env = [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]
        prod = (
            "https://kivufoot-web.onrender.com",
            "https://foot-web.onrender.com",
        )
        out: list[str] = []
        seen: set[str] = set()
        for o in [*env, *prod]:
            if o and o not in seen:
                seen.add(o)
                out.append(o)
        return out

    @property
    def supported_locales_list(self) -> list[str]:
        return [l.strip() for l in self.supported_locales.split(",") if l.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
