from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.models.massar_sync import MassarSyncLog, MassarConfig
from app.core.security import get_current_user

router = APIRouter()


class MassarConfigCreate(BaseModel):
    massar_school_code: str
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    auto_sync_enabled: bool = False
    sync_interval_minutes: int = 60


class MassarConfigUpdate(BaseModel):
    massar_school_code: Optional[str] = None
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    auto_sync_enabled: Optional[bool] = None
    sync_interval_minutes: Optional[int] = None


@router.get("/config")
async def get_config(school_id: UUID, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(MassarConfig).where(MassarConfig.school_id == school_id))
    config = r.scalar_one_or_none()
    if not config:
        return {"configured": False}
    return {
        "configured": True,
        "massar_school_code": config.massar_school_code,
        "api_endpoint": config.api_endpoint,
        "auto_sync_enabled": config.auto_sync_enabled,
        "sync_interval_minutes": config.sync_interval_minutes,
        "last_sync_at": config.last_sync_at.isoformat() if config.last_sync_at else None,
        "total_synced": config.total_synced,
        "total_failed": config.total_failed,
        "total_rejected": config.total_rejected,
    }


@router.post("/config")
async def create_config(school_id: UUID, body: MassarConfigCreate, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(MassarConfig).where(MassarConfig.school_id == school_id))
    existing = r.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Config already exists. Use PUT to update.")
    config = MassarConfig(school_id=school_id, **body.model_dump())
    db.add(config)
    await db.commit()
    return {"message": "Config created"}


@router.put("/config")
async def update_config(school_id: UUID, body: MassarConfigUpdate, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(MassarConfig).where(MassarConfig.school_id == school_id))
    config = r.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(config, k, v)
    config.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Config updated"}


@router.get("/logs")
async def get_logs(school_id: UUID, entity_type: Optional[str] = None, status: Optional[str] = None, limit: int = 50, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    q = select(MassarSyncLog).where(MassarSyncLog.school_id == school_id)
    if entity_type:
        q = q.where(MassarSyncLog.entity_type == entity_type)
    if status:
        q = q.where(MassarSyncLog.status == status)
    q = q.order_by(MassarSyncLog.created_at.desc()).limit(limit)
    r = await db.execute(q)
    logs = r.scalars().all()
    return [
        {
            "id": str(l.id), "entity_type": l.entity_type, "entity_id": str(l.entity_id),
            "massar_id": l.massar_id, "sync_type": l.sync_type, "status": l.status,
            "error_message": l.error_message, "synced_at": l.synced_at.isoformat() if l.synced_at else None,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]


@router.get("/stats")
async def get_stats(school_id: UUID, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    total = await db.execute(select(func.count(MassarSyncLog.id)).where(MassarSyncLog.school_id == school_id))
    synced = await db.execute(select(func.count(MassarSyncLog.id)).where(MassarSyncLog.school_id == school_id, MassarSyncLog.status == "synced"))
    failed = await db.execute(select(func.count(MassarSyncLog.id)).where(MassarSyncLog.school_id == school_id, MassarSyncLog.status == "failed"))
    pending = await db.execute(select(func.count(MassarSyncLog.id)).where(MassarSyncLog.school_id == school_id, MassarSyncLog.status == "pending"))
    return {
        "total": total.scalar() or 0,
        "synced": synced.scalar() or 0,
        "failed": failed.scalar() or 0,
        "pending": pending.scalar() or 0,
    }


@router.post("/sync")
async def trigger_sync(school_id: UUID, entity_type: str, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    config_r = await db.execute(select(MassarConfig).where(MassarConfig.school_id == school_id))
    config = config_r.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=400, detail="Massar not configured. Please configure first.")
    log = MassarSyncLog(
        school_id=school_id, entity_type=entity_type, entity_id=school_id,
        sync_type="push", status="pending"
    )
    db.add(log)
    config.last_sync_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": f"Sync triggered for {entity_type}", "log_id": str(log.id)}
