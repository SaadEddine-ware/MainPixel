from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime


class AssignmentCreate(BaseModel):
    class_id: UUID
    subject_id: UUID
    title: str
    description: Optional[str] = None
    assignment_type: str = "homework"
    due_date: Optional[datetime] = None
    max_score: float = 20.0


class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignment_type: Optional[str] = None
    due_date: Optional[datetime] = None
    max_score: Optional[float] = None
    is_active: Optional[bool] = None


class AssignmentOut(BaseModel):
    id: UUID
    school_id: UUID
    class_id: UUID
    subject_id: UUID
    teacher_id: UUID
    title: str
    description: Optional[str]
    assignment_type: str
    due_date: Optional[datetime]
    max_score: float
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
