from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime


class SubjectCreate(BaseModel):
    name: str
    code: Optional[str] = None
    coefficient: float = 1.0
    level: str
    max_score: float = 20.0


class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    coefficient: Optional[float] = None
    level: Optional[str] = None
    max_score: Optional[float] = None
    is_active: Optional[bool] = None


class SubjectOut(BaseModel):
    id: UUID
    school_id: UUID
    name: str
    code: Optional[str]
    coefficient: float
    level: str
    max_score: float
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
