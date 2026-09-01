from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime


class GradeCreate(BaseModel):
    assignment_id: UUID
    student_id: UUID
    score: float
    max_score: float = 20.0
    comment: Optional[str] = None


class GradeUpdate(BaseModel):
    score: Optional[float] = None
    max_score: Optional[float] = None
    comment: Optional[str] = None


class GradeOut(BaseModel):
    id: UUID
    school_id: UUID
    assignment_id: UUID
    student_id: UUID
    score: float
    max_score: float
    comment: Optional[str]
    graded_by: Optional[UUID]
    created_at: datetime

    class Config:
        from_attributes = True
