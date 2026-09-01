from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from typing import List, Optional
from datetime import date
from app.core.database import get_db
from app.models.attendance import Attendance
from app.models.student import Student
from app.schemas.attendance_schema import AttendanceCreate, AttendanceUpdate, AttendanceOut
from app.core.security import get_current_user

router = APIRouter()


@router.get("/", response_model=List[AttendanceOut])
async def list_attendance(school_id: UUID, class_id: UUID = None, student_id: UUID = None, date_from: date = None, date_to: date = None, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = select(Attendance).where(Attendance.school_id == school_id)
    if class_id:
        query = query.where(Attendance.class_id == class_id)
    if student_id:
        query = query.where(Attendance.student_id == student_id)
    if date_from:
        query = query.where(Attendance.date >= date_from)
    if date_to:
        query = query.where(Attendance.date <= date_to)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=AttendanceOut, status_code=status.HTTP_201_CREATED)
async def mark_attendance(school_id: UUID, data: AttendanceCreate, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    existing = await db.execute(
        select(Attendance).where(
            Attendance.student_id == data.student_id,
            Attendance.date == data.date,
            Attendance.class_id == data.class_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Attendance already marked for this student on this date")

    obj = Attendance(school_id=school_id, **data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.post("/bulk", response_model=List[AttendanceOut])
async def bulk_mark_attendance(school_id: UUID, class_id: UUID, date_val: date, records: List[dict], payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    objs = []
    for r in records:
        student_id = r["student_id"]
        existing = await db.execute(
            select(Attendance).where(
                Attendance.student_id == student_id,
                Attendance.date == date_val,
                Attendance.class_id == class_id,
            )
        )
        if not existing.scalar_one_or_none():
            obj = Attendance(
                school_id=school_id,
                student_id=student_id,
                class_id=class_id,
                date=date_val,
                status=r.get("status", "present"),
                reason=r.get("reason"),
            )
            db.add(obj)
            objs.append(obj)
    await db.commit()
    for o in objs:
        await db.refresh(o)
    return objs


@router.get("/stats")
async def attendance_stats(school_id: UUID, class_id: UUID, date_from: date = None, date_to: date = None, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = select(Attendance).where(Attendance.school_id == school_id, Attendance.class_id == class_id)
    if date_from:
        query = query.where(Attendance.date >= date_from)
    if date_to:
        query = query.where(Attendance.date <= date_to)
    result = await db.execute(query)
    records = result.scalars().all()

    total = len(records)
    present = sum(1 for r in records if r.status == "present")
    absent = sum(1 for r in records if r.status == "absent")
    late = sum(1 for r in records if r.status == "late")
    excused = sum(1 for r in records if r.status == "excused")

    students_r = await db.execute(select(Student).where(Student.class_id == class_id, Student.is_active == True))
    total_students = len(students_r.scalars().all())

    return {
        "class_id": str(class_id),
        "total_records": total,
        "total_students": total_students,
        "present": present,
        "absent": absent,
        "late": late,
        "excused": excused,
        "attendance_rate": round(present / total * 100, 1) if total > 0 else 0,
    }


@router.get("/{attendance_id}", response_model=AttendanceOut)
async def get_attendance(attendance_id: UUID, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Attendance).where(Attendance.id == attendance_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    return obj


@router.put("/{attendance_id}", response_model=AttendanceOut)
async def update_attendance(attendance_id: UUID, data: AttendanceUpdate, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Attendance).where(Attendance.id == attendance_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{attendance_id}")
async def delete_attendance(attendance_id: UUID, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Attendance).where(Attendance.id == attendance_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    await db.delete(obj)
    await db.commit()
    return {"detail": "Attendance deleted"}
