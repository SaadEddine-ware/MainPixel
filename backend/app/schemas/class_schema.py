from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime


class ClassCreate(BaseModel):
    name: str
    level: str
    section: Optional[str] = None
    academic_year: str
    capacity: int = 40


class ClassUpdate(BaseModel):
    name: Optional[str] = None
    level: Optional[str] = None
    section: Optional[str] = None
    academic_year: Optional[str] = None
    capacity: Optional[int] = None
    is_active: Optional[bool] = None


class ClassOut(BaseModel):
    id: UUID
    school_id: UUID
    name: str
    level: str
    section: Optional[str]
    academic_year: str
    capacity: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
