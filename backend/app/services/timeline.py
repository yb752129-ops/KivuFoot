"""Timeline publique dérivée des sources officielles existantes."""
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.actualite import Actualite
from app.models.audit import AuditLog
from app.models.document import DocumentOfficiel
from app.models.enums import StatutActualite, StatutMatch
from app.models.match import Match
from app.models.sport_engine import DecisionSportive


async def timeline_saison(db: AsyncSession, saison_id: int) -> list[dict]:
    entries: list[dict] = []
    matches = (
        await db.execute(select(Match).where(Match.saison_id == saison_id, Match.statut == StatutMatch.VALIDE))
    ).scalars().all()
    for match in matches:
        entries.append({
            "type": "match_valide",
            "date": match.date_heure,
            "titre": f"Match #{match.id} validé",
            "match_id": match.id,
            "official": True,
            "source": "match",
        })
    news = (
        await db.execute(
            select(Actualite).where(Actualite.saison_id == saison_id, Actualite.statut == StatutActualite.PUBLIE)
        )
    ).scalars().all()
    for item in news:
        entries.append({
            "type": "communication_officielle",
            "date": item.date_publication or item.date_creation,
            "titre": item.titre,
            "actualite_id": item.id,
            "official": True,
            "source": "actualite",
        })
    decisions = (
        await db.execute(select(DecisionSportive).where(DecisionSportive.saison_id == saison_id, DecisionSportive.statut == "confirmee"))
    ).scalars().all()
    for decision in decisions:
        entries.append({
            "type": "decision_sportive",
            "date": decision.created_at,
            "titre": decision.type_decision,
            "decision_id": decision.id,
            "match_id": decision.match_id,
            "joueur_id": decision.joueur_id,
            "official": True,
            "source": "decision_sportive",
        })
    documents = (
        await db.execute(select(DocumentOfficiel).where(DocumentOfficiel.saison_id == saison_id, DocumentOfficiel.statut == "publie"))
    ).scalars().all()
    for document in documents:
        entries.append({
            "type": "document_officiel",
            "date": document.published_at or document.created_at,
            "titre": document.titre,
            "document_id": document.id,
            "official": True,
            "source": "document",
        })
    entries.sort(key=lambda item: item["date"] or 0)
    return entries


async def historique_public(db: AsyncSession, saison_id: int) -> list[dict]:
    """Projection blanche de l'audit : jamais old_data/new_data."""
    # L'audit est global et ne contient pas toujours saison_id. On rattache
    # uniquement les tables dont le record est explicitement dans l'édition;
    # les autres lignes restent volontairement absentes plutôt que devinées.
    season_filter = or_(
        and_(AuditLog.table_name == "matchs", AuditLog.record_id.in_(select(Match.id).where(Match.saison_id == saison_id))),
        and_(AuditLog.table_name == "actualites", AuditLog.record_id.in_(select(Actualite.id).where(Actualite.saison_id == saison_id))),
        and_(AuditLog.table_name == "decisions_sportives", AuditLog.record_id.in_(select(DecisionSportive.id).where(DecisionSportive.saison_id == saison_id))),
        and_(AuditLog.table_name == "documents_officiels", AuditLog.record_id.in_(select(DocumentOfficiel.id).where(DocumentOfficiel.saison_id == saison_id))),
    )
    result = await db.execute(
        select(AuditLog)
        .where(season_filter)
        .order_by(AuditLog.created_at.desc())
        .limit(200)
    )
    rows = []
    for row in result.scalars().all():
        # Le rattachement saison peut être absent dans l'audit ancien. Le
        # détail public reste volontairement minimal plutôt que de deviner.
        rows.append({
            "id": row.id,
            "table_name": row.table_name,
            "record_id": row.record_id,
            "action": row.action,
            "created_at": row.created_at,
            "source": "audit_public_projection",
        })
    return rows
