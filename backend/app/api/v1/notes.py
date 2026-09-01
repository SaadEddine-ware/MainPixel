from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import List
from app.core.database import get_db
from app.models.note import Note
from app.schemas.note_schema import NoteCreate, NoteUpdate, NoteOut

router = APIRouter()


@router.get("/", response_model=List[NoteOut])
async def list_notes(school_id: UUID, student_id: UUID = None, class_id: UUID = None, semester: int = None, academic_year: str = None, db: AsyncSession = Depends(get_db)):
    query = select(Note).where(Note.school_id == school_id)
    if student_id:
        query = query.where(Note.student_id == student_id)
    if class_id:
        query = query.where(Note.class_id == class_id)
    if semester:
        query = query.where(Note.semester == semester)
    if academic_year:
        query = query.where(Note.academic_year == academic_year)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
async def create_note(school_id: UUID, data: NoteCreate, db: AsyncSession = Depends(get_db)):
    obj = Note(school_id=school_id, **data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.post("/bulk", response_model=List[NoteOut])
async def bulk_create_notes(school_id: UUID, notes: List[NoteCreate], db: AsyncSession = Depends(get_db)):
    objs = []
    for data in notes:
        obj = Note(school_id=school_id, **data.model_dump())
        db.add(obj)
        objs.append(obj)
    await db.commit()
    for o in objs:
        await db.refresh(o)
    return objs


@router.get("/{note_id}", response_model=NoteOut)
async def get_note(note_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Note).where(Note.id == note_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Note not found")
    return obj


@router.put("/{note_id}", response_model=NoteOut)
async def update_note(note_id: UUID, data: NoteUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Note).where(Note.id == note_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Note not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{note_id}")
async def delete_note(note_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Note).where(Note.id == note_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Note not found")
    await db.delete(obj)
    await db.commit()
    return {"detail": "Note deleted"}


@router.get("/student/{student_id}/moyenne")
async def get_student_moyenne(student_id: UUID, semester: int, academic_year: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Note).where(
            Note.student_id == student_id,
            Note.semester == semester,
            Note.academic_year == academic_year
        )
    )
    notes = result.scalars().all()
    if not notes:
        return {"moyenne": 0, "total_coefficient": 0, "details": []}

    total_weighted = sum(n.score * n.coefficient for n in notes)
    total_coeff = sum(n.coefficient for n in notes)
    moyenne = total_weighted / total_coeff if total_coeff > 0 else 0

    return {
        "moyenne": round(moyenne, 2),
        "total_coefficient": total_coeff,
        "semester": semester,
        "academic_year": academic_year,
        "details": [{"subject_id": str(n.subject_id), "score": n.score, "coefficient": n.coefficient} for n in notes]
    }
