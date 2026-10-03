"""Scanner idempotent des anomalies historiques, sans réécriture sportive."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ActionAudit, StatutMatch
from app.models.match import Match
from app.models.sport_engine import AnomalieHistorique
from app.services.checklist_validation import run_checklist
from app.services.audit import log_audit


def _hash(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


async def scan_saison(db: AsyncSession, saison_id: int, user_id: int) -> list[AnomalieHistorique]:
    matches = (
        await db.execute(
            select(Match).where(Match.saison_id == saison_id, Match.statut == StatutMatch.VALIDE).order_by(Match.id)
        )
    ).scalars().all()
    created: list[AnomalieHistorique] = []
    for match in matches:
        checklist = await run_checklist(db, match)
        for control in checklist.controles:
            if control.statut == "OK":
                continue
            observation = {
                "controle": control.model_dump(mode="json"),
                "checklist_mode": checklist.mode,
                "reglement_version_id": checklist.reglement_version_id,
                "observed_at": datetime.now(timezone.utc).isoformat(),
            }
            fingerprint = _hash({"match_id": match.id, "code": control.code, "observation": observation["controle"]})
            existing = await db.scalar(
                select(AnomalieHistorique).where(
                    AnomalieHistorique.saison_id == saison_id,
                    AnomalieHistorique.match_id == match.id,
                    AnomalieHistorique.type_anomalie == control.code,
                    AnomalieHistorique.empreinte == fingerprint,
                )
            )
            if existing is not None:
                continue
            row = AnomalieHistorique(
                saison_id=saison_id,
                match_id=match.id,
                type_anomalie=control.code,
                severite="bloquant" if control.statut == "BLOQUANT" else "attention",
                statut="a_examiner",
                observation=observation,
                empreinte=fingerprint,
            )
            db.add(row)
            await db.flush()
            await log_audit(
                db,
                "anomalies_historiques",
                row.id,
                ActionAudit.INSERT,
                user_id,
                None,
                {"match_id": match.id, "type_anomalie": control.code, "statut": "a_examiner"},
            )
            created.append(row)
    return created
