from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import List
import csv
import io
from app.core.database import get_db
from app.models.student import Student
from app.schemas.student_schema import StudentCreate, StudentUpdate, StudentOut
from app.core.security import get_current_user

router = APIRouter()


@router.get("/", response_model=List[StudentOut])
async def list_students(school_id: UUID, class_id: UUID = None, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = select(Student).where(Student.school_id == school_id, Student.is_active == True)
    if class_id:
        query = query.where(Student.class_id == class_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
async def create_student(school_id: UUID, data: StudentCreate, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    obj = Student(school_id=school_id, **data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.post("/import-csv", response_model=List[StudentOut])
async def import_students_csv(school_id: UUID, class_id: UUID, file: UploadFile = File(...), payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
    students = []
    for row in reader:
        obj = Student(
            school_id=school_id,
            class_id=class_id,
            student_number=row.get("student_number", ""),
            first_name=row.get("first_name", ""),
            last_name=row.get("last_name", ""),
            date_of_birth=row.get("date_of_birth"),
            place_of_birth=row.get("place_of_birth"),
            gender=row.get("gender"),
            parent_name=row.get("parent_name"),
            parent_phone=row.get("parent_phone"),
            parent_email=row.get("parent_email"),
            address=row.get("address"),
        )
        db.add(obj)
        students.append(obj)
    await db.commit()
    for s in students:
        await db.refresh(s)
    return students


@router.get("/{student_id}", response_model=StudentOut)
async def get_student(student_id: UUID, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Student).where(Student.id == student_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Student not found")
    return obj


@router.put("/{student_id}", response_model=StudentOut)
async def update_student(student_id: UUID, data: StudentUpdate, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Student).where(Student.id == student_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Student not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{student_id}")
async def delete_student(student_id: UUID, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Student).where(Student.id == student_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Student not found")
    obj.is_active = False
    await db.commit()
    return {"detail": "Student deleted"}
