"""
Point d'entrée de l'API KivuFoot.

Documentation OpenAPI générée automatiquement par FastAPI, accessible
sur /docs et /redoc (règle §16.20 de la spécification).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.middlewares.error_handler import register_error_handlers
from app.routes import (
    audit,
    auth,
    classement,
    clubs,
    competitions,
    evenements,
    joueurs,
    matchs,
    public,
    stats,
    sync,
    validation,
)

app = FastAPI(
    title=settings.app_name,
    description=(
        "API de l'infrastructure numérique du football local de Bukavu. "
        "La fiabilité des données est le seul actif du projet : toute "
        "donnée validée est immuable, toute action critique est auditée."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

PREFIX = settings.api_v1_prefix
app.include_router(auth.router, prefix=PREFIX)
app.include_router(competitions.router, prefix=PREFIX)
app.include_router(clubs.router, prefix=PREFIX)
app.include_router(joueurs.router, prefix=PREFIX)
app.include_router(matchs.router, prefix=PREFIX)
app.include_router(evenements.router, prefix=PREFIX)
app.include_router(public.router, prefix=PREFIX)
app.include_router(validation.router, prefix=PREFIX)
app.include_router(classement.router, prefix=PREFIX)
app.include_router(stats.router, prefix=PREFIX)
app.include_router(sync.router, prefix=PREFIX)
app.include_router(audit.router, prefix=PREFIX)


@app.get("/health", tags=["Santé"])
async def health_check():
    return {"status": "ok", "environment": settings.environment}
