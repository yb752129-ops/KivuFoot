"""
Contrôle d'accès basé sur les rôles (RBAC) + portée (scope).

Principe fondamental de la spécification : la validation des données
sportives est réservée à l'organisateur DE LA COMPÉTITION concernée.
Un club_manager ne voit que les données de SON club. Ces contrôles de
portée s'appuient sur les tables `organisateur_competitions` et
`users.club_id` (ajout Phase 0, sans lesquelles ces règles RBAC ne
sont pas applicables techniquement).
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.competition import OrganisateurCompetition, Saison
from app.models.enums import RoleUtilisateur
from app.models.match import Match
from app.models.user import User


def require_roles(*roles: RoleUtilisateur):
    """Dépendance FastAPI : autorise uniquement les rôles listés."""

    async def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'avez pas les droits nécessaires pour cette action.",
            )
        return current_user

    return _checker


async def verifier_organisateur_de_competition(
    competition_id: int,
    current_user: User,
    db: AsyncSession,
) -> None:
    """Lève 403 si l'utilisateur n'est ni admin, ni organisateur de cette compétition précise."""
    if current_user.role == RoleUtilisateur.ADMIN:
        return
    if current_user.role != RoleUtilisateur.ORGANISATEUR:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Réservé aux organisateurs.")
    result = await db.execute(
        select(OrganisateurCompetition).where(
            OrganisateurCompetition.user_id == current_user.id,
            OrganisateurCompetition.competition_id == competition_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Vous n'êtes pas organisateur de cette compétition.",
        )


async def verifier_organisateur_du_match(
    match_id: int,
    current_user: User,
    db: AsyncSession,
) -> Match:
    """Charge le match et vérifie que l'utilisateur peut le gérer (via sa compétition)."""
    match_ = await db.get(Match, match_id)
    if match_ is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match introuvable.")
    saison = await db.get(Saison, match_.saison_id)
    competition_id = saison.competition_id if saison else None
    if competition_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compétition introuvable pour ce match.")
    await verifier_organisateur_de_competition(competition_id, current_user, db)
    return match_


def verifier_scope_club(current_user: User, club_id: int) -> None:
    """Un club_manager ne peut agir que sur son propre club."""
    if current_user.role == RoleUtilisateur.ADMIN:
        return
    if current_user.role in (RoleUtilisateur.CLUB_MANAGER, RoleUtilisateur.COACH) and current_user.club_id != club_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Vous ne gérez pas ce club.")
