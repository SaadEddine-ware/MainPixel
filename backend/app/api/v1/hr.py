from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.models.hr import Staff, SalaryRecord, LeaveRequest
from app.core.security import get_current_user

router = APIRouter()


class StaffCreate(BaseModel):
    employee_number: str
    first_name: str
    last_name: str
    position: str
    department: Optional[str] = None
    hire_date: str
    salary: float
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


class StaffUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None
    salary: Optional[float] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None


class LeaveCreate(BaseModel):
    staff_id: UUID
    leave_type: str
    start_date: str
    end_date: str
    reason: Optional[str] = None


class SalaryCreate(BaseModel):
    staff_id: UUID
    month: int
    year: int
    base_salary: float
    bonus: float = 0.0
    deductions: float = 0.0
    payment_method: Optional[str] = None
    notes: Optional[str] = None


@router.get("/staff")
async def list_staff(school_id: UUID, is_active: Optional[bool] = None, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = select(Staff).where(Staff.school_id == school_id)
    if is_active is not None:
        q = q.where(Staff.is_active == is_active)
    r = await db.execute(q.order_by(Staff.created_at.desc()))
    staff = r.scalars().all()
    return [
        {
            "id": str(s.id), "employee_number": s.employee_number,
            "first_name": s.first_name, "last_name": s.last_name,
            "position": s.position, "department": s.department,
            "hire_date": s.hire_date.isoformat() if s.hire_date else None,
            "salary": s.salary, "phone": s.phone, "email": s.email,
            "is_active": s.is_active,
        }
        for s in staff
    ]


@router.post("/staff")
async def create_staff(school_id: UUID, body: StaffCreate, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from datetime import date as dt_date
    staff = Staff(
        school_id=school_id,
        employee_number=body.employee_number,
        first_name=body.first_name,
        last_name=body.last_name,
        position=body.position,
        department=body.department,
        hire_date=dt_date.fromisoformat(body.hire_date),
        salary=body.salary,
        phone=body.phone,
        email=body.email,
        address=body.address,
    )
    db.add(staff)
    await db.commit()
    return {"message": "Staff created", "id": str(staff.id)}


@router.put("/staff/{staff_id}")
async def update_staff(staff_id: UUID, body: StaffUpdate, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Staff).where(Staff.id == staff_id))
    staff = r.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(staff, k, v)
    staff.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Staff updated"}


@router.delete("/staff/{staff_id}")
async def delete_staff(staff_id: UUID, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Staff).where(Staff.id == staff_id))
    staff = r.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    staff.is_active = False
    await db.commit()
    return {"message": "Staff deactivated"}


@router.get("/stats")
async def get_hr_stats(school_id: UUID, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    total = await db.execute(select(func.count(Staff.id)).where(Staff.school_id == school_id))
    active = await db.execute(select(func.count(Staff.id)).where(Staff.school_id == school_id, Staff.is_active == True))
    total_salary = await db.execute(select(func.sum(Staff.salary)).where(Staff.school_id == school_id, Staff.is_active == True))
    pending_leaves = await db.execute(select(func.count(LeaveRequest.id)).where(LeaveRequest.school_id == school_id, LeaveRequest.status == "pending"))
    return {
        "total_staff": total.scalar() or 0,
        "active_staff": active.scalar() or 0,
        "total_salaries": float(total_salary.scalar() or 0),
        "pending_leaves": pending_leaves.scalar() or 0,
    }


@router.get("/leave")
async def list_leave(school_id: UUID, status: Optional[str] = None, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = select(LeaveRequest).where(LeaveRequest.school_id == school_id)
    if status:
        q = q.where(LeaveRequest.status == status)
    r = await db.execute(q.order_by(LeaveRequest.created_at.desc()))
    leaves = r.scalars().all()
    return [
        {
            "id": str(l.id), "staff_id": str(l.staff_id),
            "leave_type": l.leave_type, "start_date": l.start_date.isoformat(),
            "end_date": l.end_date.isoformat(), "reason": l.reason,
            "status": l.status, "created_at": l.created_at.isoformat(),
        }
        for l in leaves
    ]


@router.post("/leave")
async def create_leave(school_id: UUID, body: LeaveCreate, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from datetime import date as dt_date
    leave = LeaveRequest(
        school_id=school_id, staff_id=body.staff_id,
        leave_type=body.leave_type,
        start_date=dt_date.fromisoformat(body.start_date),
        end_date=dt_date.fromisoformat(body.end_date),
        reason=body.reason,
    )
    db.add(leave)
    await db.commit()
    return {"message": "Leave request created", "id": str(leave.id)}


@router.put("/leave/{leave_id}/approve")
async def approve_leave(leave_id: UUID, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(LeaveRequest).where(LeaveRequest.id == leave_id))
    leave = r.scalar_one_or_none()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")
    leave.status = "approved"
    leave.approved_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Leave approved"}


@router.put("/leave/{leave_id}/reject")
async def reject_leave(leave_id: UUID, reason: Optional[str] = None, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(LeaveRequest).where(LeaveRequest.id == leave_id))
    leave = r.scalar_one_or_none()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")
    leave.status = "rejected"
    leave.rejection_reason = reason
    leave.approved_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Leave rejected"}


@router.get("/salaries")
async def list_salaries(school_id: UUID, month: Optional[int] = None, year: Optional[int] = None, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = select(SalaryRecord).where(SalaryRecord.school_id == school_id)
    if month:
        q = q.where(SalaryRecord.month == month)
    if year:
        q = q.where(SalaryRecord.year == year)
    r = await db.execute(q.order_by(SalaryRecord.created_at.desc()))
    records = r.scalars().all()
    return [
        {
            "id": str(s.id), "staff_id": str(s.staff_id),
            "month": s.month, "year": s.year,
            "base_salary": s.base_salary, "bonus": s.bonus,
            "deductions": s.deductions, "net_salary": s.net_salary,
            "payment_date": s.payment_date.isoformat() if s.payment_date else None,
            "is_paid": s.is_paid,
        }
        for s in records
    ]


@router.post("/salaries")
async def create_salary(school_id: UUID, body: SalaryCreate, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    net = body.base_salary + body.bonus - body.deductions
    record = SalaryRecord(
        school_id=school_id, staff_id=body.staff_id,
        month=body.month, year=body.year,
        base_salary=body.base_salary, bonus=body.bonus,
        deductions=body.deductions, net_salary=net,
        payment_method=body.payment_method, notes=body.notes,
    )
    db.add(record)
    await db.commit()
    return {"message": "Salary record created", "net_salary": net}
