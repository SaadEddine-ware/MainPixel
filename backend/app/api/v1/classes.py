from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import List
from app.core.database import get_db
from app.models.school_class import SchoolClass
from app.schemas.class_schema import ClassCreate, ClassUpdate, ClassOut
from app.core.security import get_current_user

router = APIRouter()


@router.get("/", response_model=List[ClassOut])
async def list_classes(school_id: UUID, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SchoolClass).where(SchoolClass.school_id == school_id, SchoolClass.is_active == True))
    return result.scalars().all()


@router.post("/", response_model=ClassOut, status_code=status.HTTP_201_CREATED)
async def create_class(school_id: UUID, data: ClassCreate, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    obj = SchoolClass(school_id=school_id, **data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/{class_id}", response_model=ClassOut)
async def get_class(class_id: UUID, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SchoolClass).where(SchoolClass.id == class_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Class not found")
    return obj


@router.put("/{class_id}", response_model=ClassOut)
async def update_class(class_id: UUID, data: ClassUpdate, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SchoolClass).where(SchoolClass.id == class_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Class not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{class_id}")
async def delete_class(class_id: UUID, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SchoolClass).where(SchoolClass.id == class_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Class not found")
    obj.is_active = False
    await db.commit()
    return {"detail": "Class deleted"}
