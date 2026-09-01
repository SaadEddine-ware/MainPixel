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
from app.models.user import User
from app.schemas.student_schema import StudentOut
from app.schemas.grade_schema import GradeOut
from app.schemas.attendance_schema import AttendanceOut

router = APIRouter()


async def verify_parent_owns_student(student_id: UUID, payload: dict, db: AsyncSession):
    parent_user_id = UUID(payload["sub"])
    parent_r = await db.execute(select(User).where(User.id == parent_user_id, User.role == "parent"))
    parent_obj = parent_r.scalar_one_or_none()
    if not parent_obj:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a parent account")
    student_r = await db.execute(select(Student).where(Student.id == student_id, Student.is_active == True))
    student = student_r.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if student.parent_email != parent_obj.email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return student


@router.get("/children", response_model=List[StudentOut])
async def get_children(payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    parent_user_id = UUID(payload["sub"])
    parent_r = await db.execute(select(User).where(User.id == parent_user_id, User.role == "parent"))
    parent_obj = parent_r.scalar_one_or_none()
    if not parent_obj:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a parent account")
    result = await db.execute(select(Student).where(Student.parent_email == parent_obj.email, Student.is_active == True))
    return result.scalars().all()


@router.get("/grades/{student_id}", response_model=List[GradeOut])
async def get_child_grades(student_id: UUID, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await verify_parent_owns_student(student_id, payload, db)
    result = await db.execute(select(Grade).where(Grade.student_id == student_id))
    return result.scalars().all()


@router.get("/attendance/{student_id}", response_model=List[AttendanceOut])
async def get_child_attendance(student_id: UUID, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await verify_parent_owns_student(student_id, payload, db)
    result = await db.execute(select(Attendance).where(Attendance.student_id == student_id))
    return result.scalars().all()


@router.get("/student/{student_id}", response_model=StudentOut)
async def get_student_detail(student_id: UUID, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await verify_parent_owns_student(student_id, payload, db)
    result = await db.execute(select(Student).where(Student.id == student_id))
    return result.scalar_one_or_none()
