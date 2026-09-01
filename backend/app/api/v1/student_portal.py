from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.student import Student
from app.models.grade import Grade
from app.models.attendance import Attendance
from app.models.assignment import Assignment
from app.schemas.grade_schema import GradeOut
from app.schemas.attendance_schema import AttendanceOut
from app.schemas.assignment_schema import AssignmentOut

router = APIRouter()


async def verify_student_self(student_id: UUID, payload: dict, db: AsyncSession):
    user_id = UUID(payload["sub"])
    user_role = payload.get("role")
    if user_role == "student":
        student_r = await db.execute(select(Student).where(Student.user_id == user_id, Student.is_active == True))
        student = student_r.scalar_one_or_none()
        if not student or student.id != student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return student
    elif user_role in ("school_admin", "super_admin", "teacher"):
        student_r = await db.execute(select(Student).where(Student.id == student_id, Student.is_active == True))
        student = student_r.scalar_one_or_none()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        return student
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


@router.get("/grades/{student_id}", response_model=List[GradeOut])
async def get_my_grades(student_id: UUID, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await verify_student_self(student_id, payload, db)
    result = await db.execute(select(Grade).where(Grade.student_id == student_id))
    return result.scalars().all()


@router.get("/assignments/{student_id}", response_model=List[AssignmentOut])
async def get_my_assignments(student_id: UUID, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    student = await verify_student_self(student_id, payload, db)
    result = await db.execute(select(Assignment).where(Assignment.class_id == student.class_id, Assignment.is_active == True))
    return result.scalars().all()


@router.get("/attendance/{student_id}", response_model=List[AttendanceOut])
async def get_my_attendance(student_id: UUID, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await verify_student_self(student_id, payload, db)
    result = await db.execute(select(Attendance).where(Attendance.student_id == student_id))
    return result.scalars().all()
