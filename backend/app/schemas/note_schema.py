from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime


class NoteCreate(BaseModel):
    student_id: UUID
    subject_id: UUID
    class_id: UUID
    semester: int
    academic_year: str
    score: float
    max_score: float = 20.0
    coefficient: float = 1.0
    comment: Optional[str] = None


class NoteUpdate(BaseModel):
    score: Optional[float] = None
    max_score: Optional[float] = None
    coefficient: Optional[float] = None
    comment: Optional[str] = None


class NoteOut(BaseModel):
    id: UUID
    school_id: UUID
    student_id: UUID
    subject_id: UUID
    class_id: UUID
    semester: int
    academic_year: str
    score: float
    max_score: float
    coefficient: float
    comment: Optional[str]
    created_by: Optional[UUID]
    created_at: datetime

    class Config:
        from_attributes = True
