from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import List
from app.core.database import get_db
from app.models.subject import Subject
from app.schemas.subject_schema import SubjectCreate, SubjectUpdate, SubjectOut
from app.core.security import get_current_user

router = APIRouter()


@router.get("/", response_model=List[SubjectOut])
async def list_subjects(school_id: UUID, level: str = None, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = select(Subject).where(Subject.school_id == school_id, Subject.is_active == True)
    if level:
        query = query.where(Subject.level == level)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=SubjectOut, status_code=status.HTTP_201_CREATED)
async def create_subject(school_id: UUID, data: SubjectCreate, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    obj = Subject(school_id=school_id, **data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/{subject_id}", response_model=SubjectOut)
async def get_subject(subject_id: UUID, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Subject).where(Subject.id == subject_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Subject not found")
    return obj


@router.put("/{subject_id}", response_model=SubjectOut)
async def update_subject(subject_id: UUID, data: SubjectUpdate, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Subject).where(Subject.id == subject_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Subject not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{subject_id}")
async def delete_subject(subject_id: UUID, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Subject).where(Subject.id == subject_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Subject not found")
    obj.is_active = False
    await db.commit()
    return {"detail": "Subject deleted"}
