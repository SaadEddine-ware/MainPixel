from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.models.timetable import Schedule
from app.schemas.timetable_schema import ScheduleCreate, ScheduleUpdate, ScheduleOut
from app.core.security import get_current_user

router = APIRouter()


@router.get("/", response_model=List[ScheduleOut])
async def list_schedules(school_id: UUID, class_id: UUID = None, subject_id: UUID = None, teacher_id: UUID = None, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = select(Schedule).where(Schedule.school_id == school_id)
    if class_id:
        query = query.where(Schedule.class_id == class_id)
    if subject_id:
        query = query.where(Schedule.subject_id == subject_id)
    if teacher_id:
        query = query.where(Schedule.teacher_id == teacher_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/weekly", response_model=dict)
async def weekly_view(school_id: UUID, class_id: UUID, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = select(Schedule).where(
        Schedule.school_id == school_id,
        Schedule.class_id == class_id,
    ).order_by(Schedule.day_of_week, Schedule.start_time)
    result = await db.execute(query)
    schedules = result.scalars().all()

    days = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"}
    weekly = {}
    for d in range(7):
        day_schedules = [
            ScheduleOut.model_validate(s).model_dump()
            for s in schedules if s.day_of_week == d
        ]
        if day_schedules:
            weekly[days[d]] = day_schedules
    return {"class_id": str(class_id), "week": weekly}


@router.post("/", response_model=ScheduleOut, status_code=status.HTTP_201_CREATED)
async def create_schedule(school_id: UUID, data: ScheduleCreate, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    obj = Schedule(school_id=school_id, **data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/{schedule_id}", response_model=ScheduleOut)
async def get_schedule(schedule_id: UUID, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return obj


@router.put("/{schedule_id}", response_model=ScheduleOut)
async def update_schedule(schedule_id: UUID, data: ScheduleUpdate, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Schedule not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: UUID, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Schedule not found")
    await db.delete(obj)
    await db.commit()
    return {"detail": "Schedule deleted"}
