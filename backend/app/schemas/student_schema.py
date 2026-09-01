from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime, date


class StudentCreate(BaseModel):
    class_id: Optional[UUID] = None
    student_number: str
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    place_of_birth: Optional[str] = None
    gender: Optional[str] = None
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None
    parent_email: Optional[str] = None
    address: Optional[str] = None


class StudentUpdate(BaseModel):
    class_id: Optional[UUID] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    place_of_birth: Optional[str] = None
    gender: Optional[str] = None
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None
    parent_email: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


class StudentOut(BaseModel):
    id: UUID
    school_id: UUID
    class_id: Optional[UUID]
    student_number: str
    first_name: str
    last_name: str
    date_of_birth: Optional[date]
    place_of_birth: Optional[str]
    gender: Optional[str]
    parent_name: Optional[str]
    parent_phone: Optional[str]
    parent_email: Optional[str]
    address: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
