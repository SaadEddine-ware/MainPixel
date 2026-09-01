from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import List
from app.core.database import get_db
from app.models.assignment import Assignment
from app.models.grade import Grade
from app.models.user import User
from app.core.security import decode_token
from fastapi import Header
from typing import Optional

router = APIRouter()


def get_current_user_id(authorization: Optional[str] = Header(None)):
    if authorization and authorization.startswith("Bearer "):
        payload = decode_token(authorization.split(" ")[1])
        if payload:
            return UUID(payload["sub"])
    return None


@router.get("/", response_model=List[dict])
async def list_assignments(school_id: UUID, class_id: UUID = None, subject_id: UUID = None, db: AsyncSession = Depends(get_db)):
    query = select(Assignment).where(Assignment.school_id == school_id, Assignment.is_active == True)
    if class_id:
        query = query.where(Assignment.class_id == class_id)
    if subject_id:
        query = query.where(Assignment.subject_id == subject_id)
    result = await db.execute(query)
    assignments = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "school_id": str(a.school_id),
            "class_id": str(a.class_id),
            "subject_id": str(a.subject_id),
            "teacher_id": str(a.teacher_id),
            "title": a.title,
            "description": a.description,
            "assignment_type": a.assignment_type,
            "due_date": a.due_date.isoformat() if a.due_date else None,
            "max_score": a.max_score,
            "is_active": a.is_active,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in assignments
    ]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_assignment(school_id: UUID, data: dict, authorization: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    teacher_id = get_current_user_id(authorization)
    obj = Assignment(school_id=school_id, teacher_id=teacher_id, **data)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return {"id": str(obj.id), "title": obj.title}


@router.post("/{assignment_id}/grades", status_code=status.HTTP_201_CREATED)
async def add_grade(assignment_id: UUID, data: dict, authorization: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    graded_by = get_current_user_id(authorization)
    result = await db.execute(select(Assignment).where(Assignment.id == assignment_id))
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    obj = Grade(
        school_id=assignment.school_id,
        assignment_id=assignment_id,
        student_id=data["student_id"],
        score=data["score"],
        max_score=data.get("max_score", assignment.max_score),
        comment=data.get("comment"),
        graded_by=graded_by,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return {"id": str(obj.id), "score": obj.score}


@router.get("/{assignment_id}/grades")
async def list_grades(assignment_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Grade).where(Grade.assignment_id == assignment_id))
    grades = result.scalars().all()
    return [
        {
            "id": str(g.id),
            "student_id": str(g.student_id),
            "score": g.score,
            "max_score": g.max_score,
            "comment": g.comment,
            "created_at": g.created_at.isoformat() if g.created_at else None,
        }
        for g in grades
    ]


@router.get("/{assignment_id}")
async def get_assignment(assignment_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Assignment).where(Assignment.id == assignment_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return {
        "id": str(obj.id),
        "title": obj.title,
        "description": obj.description,
        "assignment_type": obj.assignment_type,
        "due_date": obj.due_date.isoformat() if obj.due_date else None,
        "max_score": obj.max_score,
    }
