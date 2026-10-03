"""Accès versionné aux règlements sportifs.

Une configuration absente n'est jamais remplacée par une règle implicite.
Le comportement existant reste disponible pour les éditions LEGACY.
"""
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competition import Competition, Saison
from app.models.enums import ActionAudit
from app.models.match import Match
from app.models.sport_engine import ReglementVersion
from app.models.user import User
from app.schemas.sport_engine import ReglementConfiguration
from app.services.audit import log_audit


async def get_reglement(db: AsyncSession, reglement_id: int) -> ReglementVersion:
    row = await db.get(ReglementVersion, reglement_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Règlement introuvable.")
    return row


async def get_reglement_actif(db: AsyncSession, saison_id: int) -> ReglementVersion | None:
    result = await db.execute(
        select(ReglementVersion)
        .where(ReglementVersion.saison_id == saison_id, ReglementVersion.statut == "actif")
        .order_by(ReglementVersion.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_reglement_pour_match(
    db: AsyncSession, match: Match, *, allow_active_for_new: bool = False
) -> ReglementVersion | None:
    """Retourne le règlement explicitement lié au match.

    Pour un match existant, l'absence de liaison reste une absence : le
    règlement actif de la saison n'est utilisé automatiquement que pour un
    match encore programmé et uniquement si l'appel le demande.
    """
    if match.reglement_version_id:
        return await db.get(ReglementVersion, match.reglement_version_id)
    if allow_active_for_new and getattr(match.statut, "value", match.statut) == "programme":
        return await get_reglement_actif(db, match.saison_id)
    return None


async def verifier_configuration(configuration: dict) -> dict:
    parsed = ReglementConfiguration.model_validate(configuration)
    return parsed.model_dump(mode="json", exclude_none=True)


async def activer_reglement(db: AsyncSession, reglement: ReglementVersion, user: User) -> ReglementVersion:
    if reglement.statut == "clos":
        raise HTTPException(status.HTTP_409_CONFLICT, "Un règlement clos ne peut pas être réactivé.")
    configuration = await verifier_configuration(reglement.configuration)
    if not configuration:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Configuration de règlement vide.")
    active = (
        await db.execute(
            select(ReglementVersion).where(
                ReglementVersion.saison_id == reglement.saison_id,
                ReglementVersion.statut == "actif",
                ReglementVersion.id != reglement.id,
            )
        )
    ).scalars().all()
    for other in active:
        other.statut = "clos"
        other.closed_at = datetime.now(timezone.utc)
    old = {"statut": reglement.statut}
    reglement.configuration = configuration
    reglement.statut = "actif"
    reglement.active_par_id = user.id
    reglement.activated_at = datetime.now(timezone.utc)
    await log_audit(
        db,
        "reglements_versions",
        reglement.id,
        ActionAudit.VALIDATE,
        user.id,
        old,
        {"statut": "actif", "version": reglement.version},
    )
    return reglement


async def rattacher_reglement_aux_matchs(
    db: AsyncSession, reglement: ReglementVersion, match_ids: list[int], motif: str, user: User
) -> list[Match]:
    rows = (
        await db.execute(select(Match).where(Match.id.in_(match_ids), Match.saison_id == reglement.saison_id))
    ).scalars().all()
    if len(rows) != len(set(match_ids)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Un ou plusieurs matchs ne correspondent pas à cette édition.")
    for match in rows:
        if match.reglement_version_id and match.reglement_version_id != reglement.id:
            raise HTTPException(status.HTTP_409_CONFLICT, f"Le match {match.id} est déjà rattaché à un autre règlement.")
        if match.reglement_version_id == reglement.id:
            continue
        match.reglement_version_id = reglement.id
        await log_audit(
            db,
            "matchs",
            match.id,
            ActionAudit.UPDATE,
            user.id,
            {"reglement_version_id": None},
            {"reglement_version_id": reglement.id, "motif": motif},
        )
    return rows


async def prochaine_version(db: AsyncSession, saison_id: int) -> int:
    value = await db.scalar(select(func.max(ReglementVersion.version)).where(ReglementVersion.saison_id == saison_id))
    return int(value or 0) + 1


async def verifier_saison_competition(db: AsyncSession, saison_id: int, competition_id: int) -> Saison:
    saison = await db.get(Saison, saison_id)
    if saison is None or saison.competition_id != competition_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La saison ne correspond pas à la compétition.")
    if await db.get(Competition, competition_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compétition introuvable.")
    return saison
