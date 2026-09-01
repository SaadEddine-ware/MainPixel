from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from uuid import UUID
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.notification import Notification
from app.models.notification_preference import NotificationPreference
from app.models.user import User
from app.schemas.notification_schema import (
    NotificationCreate, NotificationUpdate, NotificationOut,
    BulkMarkRead, NotificationStats, NotificationPreferenceOut,
    NotificationPreferenceUpdate, BroadcastNotification,
)

router = APIRouter()


async def create_notification_for_user(
    db: AsyncSession,
    school_id: UUID,
    user_id: UUID,
    title: str,
    message: str,
    notification_type: str = "info",
) -> Notification:
    pref_result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.school_id == school_id,
        )
    )
    pref = pref_result.scalar_one_or_none()

    if pref:
        type_map = {
            "admission": pref.admission_updates,
            "payment": pref.payment_updates,
            "grade": pref.grade_updates,
            "attendance": pref.attendance_updates,
            "invoice": pref.invoice_updates,
            "general": pref.general_notifications,
        }
        enabled = type_map.get(notification_type, True)
        if not enabled:
            return None

    obj = Notification(
        school_id=school_id,
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
    )
    db.add(obj)
    await db.flush()
    return obj


@router.get("/", response_model=List[NotificationOut])
async def list_notifications(school_id: UUID, user_id: UUID = None, is_read: bool = None, notification_type: str = None, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    query = select(Notification).where(Notification.school_id == school_id)
    if user_id:
        query = query.where(Notification.user_id == user_id)
    if is_read is not None:
        query = query.where(Notification.is_read == is_read)
    if notification_type:
        query = query.where(Notification.notification_type == notification_type)
    query = query.order_by(Notification.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=NotificationOut, status_code=status.HTTP_201_CREATED)
async def create_notification(school_id: UUID, data: NotificationCreate, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    obj = Notification(school_id=school_id, **data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.post("/broadcast", response_model=dict)
async def broadcast_notification(school_id: UUID, data: BroadcastNotification, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    query = select(User).where(User.school_id == school_id, User.is_active == True)
    if data.role_filter:
        query = query.where(User.role == data.role_filter)

    if data.user_ids:
        query = query.where(User.id.in_(data.user_ids))

    users_result = await db.execute(query)
    users = users_result.scalars().all()

    created = 0
    for user in users:
        obj = Notification(
            school_id=school_id,
            user_id=user.id,
            title=data.title,
            message=data.message,
            notification_type=data.notification_type,
        )
        db.add(obj)
        created += 1

    await db.commit()
    return {"detail": f"Broadcast sent to {created} users"}


@router.get("/unread-count")
async def get_unread_count(school_id: UUID, user_id: UUID, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.school_id == school_id,
            Notification.user_id == user_id,
            Notification.is_read == False,
        )
    )
    count = result.scalar() or 0
    return {"user_id": str(user_id), "unread_count": count}


@router.get("/stats", response_model=NotificationStats)
async def get_notification_stats(school_id: UUID, user_id: UUID = None, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    base_query = select(Notification).where(Notification.school_id == school_id)
    if user_id:
        base_query = base_query.where(Notification.user_id == user_id)

    all_result = await db.execute(base_query)
    all_notifications = all_result.scalars().all()

    total = len(all_notifications)
    unread = sum(1 for n in all_notifications if not n.is_read)
    by_type = {}
    for n in all_notifications:
        by_type[n.notification_type] = by_type.get(n.notification_type, 0) + 1

    return NotificationStats(total=total, unread=unread, by_type=by_type)


@router.get("/{notification_id}", response_model=NotificationOut)
async def get_notification(notification_id: UUID, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Notification).where(Notification.id == notification_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Notification not found")
    return obj


@router.put("/{notification_id}", response_model=NotificationOut)
async def update_notification(notification_id: UUID, data: NotificationUpdate, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Notification).where(Notification.id == notification_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Notification not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.post("/{notification_id}/mark-read", response_model=NotificationOut)
async def mark_read(notification_id: UUID, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Notification).where(Notification.id == notification_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Notification not found")
    obj.is_read = True
    await db.commit()
    await db.refresh(obj)
    return obj


@router.post("/mark-all-read")
async def mark_all_read(school_id: UUID, user_id: UUID, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    await db.execute(
        update(Notification).where(
            Notification.school_id == school_id,
            Notification.user_id == user_id,
            Notification.is_read == False,
        ).values(is_read=True)
    )
    await db.commit()
    return {"detail": "All notifications marked as read"}


@router.post("/bulk-mark-read")
async def bulk_mark_read(data: BulkMarkRead, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    await db.execute(
        update(Notification).where(Notification.id.in_(data.notification_ids)).values(is_read=True)
    )
    await db.commit()
    return {"detail": f"{len(data.notification_ids)} notifications marked as read"}


@router.delete("/{notification_id}")
async def delete_notification(notification_id: UUID, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Notification).where(Notification.id == notification_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Notification not found")
    await db.delete(obj)
    await db.commit()
    return {"detail": "Notification deleted"}


# ---- Notification Preferences ----

@router.get("/preferences/{user_id}", response_model=NotificationPreferenceOut)
async def get_preferences(user_id: UUID, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )
    pref = result.scalar_one_or_none()
    if not pref:
        raise HTTPException(status_code=404, detail="Preferences not found")
    return pref


@router.put("/preferences/{user_id}", response_model=NotificationPreferenceOut)
async def update_preferences(user_id: UUID, data: NotificationPreferenceUpdate, school_id: UUID = None, payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )
    pref = result.scalar_one_or_none()

    if not pref:
        if not school_id:
            raise HTTPException(status_code=400, detail="school_id required to create preferences")
        pref = NotificationPreference(user_id=user_id, school_id=school_id)
        db.add(pref)
        await db.flush()

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(pref, key, value)
    await db.commit()
    await db.refresh(pref)
    return pref
