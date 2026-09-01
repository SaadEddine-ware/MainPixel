from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog
from uuid import UUID
from typing import Optional


async def log_audit(
    db: AsyncSession,
    action: str,
    entity_type: str,
    entity_id: Optional[UUID] = None,
    school_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
):
    entry = AuditLog(
        school_id=school_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.commit()
