from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import require_roles
from app.database import get_db
from app.models.audit import AuditLog
from app.models.enums import RoleUtilisateur
from app.models.user import User

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("")
async def lister_audit(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleUtilisateur.ADMIN)),
    table_name: str | None = None,
    record_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
):
    query = select(AuditLog)
    if table_name:
        query = query.where(AuditLog.table_name == table_name)
    if record_id:
        query = query.where(AuditLog.record_id == record_id)
    result = await db.execute(query.order_by(AuditLog.created_at.desc()).limit(min(limit, 200)).offset(offset))
    entries = result.scalars().all()
    return [
        {
            "id": e.id,
            "table_name": e.table_name,
            "record_id": e.record_id,
            "action": e.action,
            "user_id": e.user_id,
            "old_data": e.old_data,
            "new_data": e.new_data,
            "created_at": e.created_at,
        }
        for e in entries
    ]
