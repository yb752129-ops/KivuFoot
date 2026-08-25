from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.enums import ActionAudit


async def log_audit(
    db: AsyncSession,
    table_name: str,
    record_id: int,
    action: ActionAudit,
    user_id: int | None,
    old_data: dict | None = None,
    new_data: dict | None = None,
) -> None:
    """
    Écrit une entrée d'audit. Ne fait PAS de commit lui-même : l'appelant
    est responsable de la transaction, pour que l'audit soit toujours
    atomique avec l'action métier qu'il documente (jamais l'un sans
    l'autre).
    """
    entry = AuditLog(
        table_name=table_name,
        record_id=record_id,
        action=action,
        user_id=user_id,
        old_data=old_data,
        new_data=new_data,
    )
    db.add(entry)
