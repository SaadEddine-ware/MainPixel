from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID, uuid4
from typing import List
import random
import string
from app.core.database import get_db
from app.core.security import hash_password
from app.models.admission import Admission
from app.models.student import Student
from app.models.user import User, UserRole
from app.models.school_class import SchoolClass
from app.schemas.admission_schema import (
    AdmissionCreate, AdmissionUpdate, AdmissionOut,
    PublicAdmissionCreate, EnrollmentResult,
    AdmissionStats, AdmissionClassStat, AdmissionMonthStat,
    AdmissionBulkAction, AdmissionBulkResult,
)
from app.utils.events import emit, EventTypes
from app.core.security import get_current_user

router = APIRouter()

VALID_STATUSES = ["pending", "approved", "rejected", "enrolled"]
STATUS_TRANSITIONS = {
    "pending": ["approved", "rejected"],
    "approved": ["enrolled", "rejected"],
    "rejected": [],
    "enrolled": [],
}


def _generate_student_number(school_id: UUID) -> str:
    prefix = str(school_id)[:4].upper()
    num = random.randint(1000, 9999)
    return f"STU-{prefix}-{num}"


def _generate_temp_password() -> str:
    chars = string.ascii_letters + string.digits + "!@#$%"
    return "".join(random.choices(chars, k=12))


@router.get("/", response_model=List[AdmissionOut])
async def list_admissions(school_id: UUID, academic_year: str = None, admission_status: str = None, class_id: UUID = None, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = select(Admission).where(Admission.school_id == school_id)
    if academic_year:
        query = query.where(Admission.academic_year == academic_year)
    if admission_status:
        query = query.where(Admission.status == admission_status)
    if class_id:
        query = query.where(Admission.class_id == class_id)
    query = query.order_by(Admission.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=AdmissionOut, status_code=status.HTTP_201_CREATED)
async def create_admission(school_id: UUID, data: AdmissionCreate, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    obj = Admission(school_id=school_id, **data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)

    await emit(EventTypes.ADMISSION_CREATED, {
        "school_id": school_id,
        "admission_id": obj.id,
        "student_name": f"{obj.first_name} {obj.last_name}",
    })

    return obj


@router.get("/public/{school_slug}", response_model=List[AdmissionOut])
async def list_public_admissions(school_slug: str, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.models.school import School
    school_result = await db.execute(select(School).where(School.slug == school_slug, School.is_active == True))
    school = school_result.scalar_one_or_none()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")

    result = await db.execute(
        select(Admission).where(
            Admission.school_id == school.id,
            Admission.status.in_(["pending", "approved"]),
        ).order_by(Admission.created_at.desc())
    )
    return result.scalars().all()


@router.post("/public/{school_slug}", response_model=AdmissionOut, status_code=status.HTTP_201_CREATED)
async def submit_public_admission(school_slug: str, data: PublicAdmissionCreate, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.models.school import School
    school_result = await db.execute(select(School).where(School.slug == school_slug, School.is_active == True))
    school = school_result.scalar_one_or_none()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")

    obj = Admission(school_id=school.id, **data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/{admission_id}", response_model=AdmissionOut)
async def get_admission(admission_id: UUID, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Admission).where(Admission.id == admission_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Admission not found")
    return obj


@router.put("/{admission_id}", response_model=AdmissionOut)
async def update_admission(admission_id: UUID, data: AdmissionUpdate, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Admission).where(Admission.id == admission_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Admission not found")
    if data.status and data.status != obj.status:
        allowed = STATUS_TRANSITIONS.get(obj.status, [])
        if data.status not in allowed:
            raise HTTPException(status_code=400, detail=f"Cannot transition from '{obj.status}' to '{data.status}'")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.post("/{admission_id}/approve", response_model=AdmissionOut)
async def approve_admission(admission_id: UUID, reviewed_by: UUID = None, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Admission).where(Admission.id == admission_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Admission not found")
    if obj.status != "pending":
        raise HTTPException(status_code=400, detail=f"Cannot approve admission in '{obj.status}' status")
    obj.status = "approved"
    if reviewed_by:
        obj.reviewed_by = reviewed_by
    await db.commit()
    await db.refresh(obj)

    await emit(EventTypes.ADMISSION_APPROVED, {
        "school_id": obj.school_id,
        "admission_id": obj.id,
        "student_name": f"{obj.first_name} {obj.last_name}",
    })

    return obj


@router.post("/{admission_id}/enroll", response_model=EnrollmentResult)
async def enroll_admission(admission_id: UUID, reviewed_by: UUID = None, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Admission).where(Admission.id == admission_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Admission not found")
    if obj.status != "approved":
        raise HTTPException(status_code=400, detail=f"Cannot enroll admission in '{obj.status}' status. Must be 'approved'.")

    student_number = _generate_student_number(obj.school_id)
    student = Student(
        school_id=obj.school_id,
        class_id=obj.class_id,
        student_number=student_number,
        first_name=obj.first_name,
        last_name=obj.last_name,
        date_of_birth=obj.date_of_birth,
        place_of_birth=obj.place_of_birth,
        gender=obj.gender,
        parent_name=obj.parent_name,
        parent_phone=obj.parent_phone,
        parent_email=obj.parent_email,
        address=obj.address,
        is_active=True,
    )
    db.add(student)
    await db.flush()

    user_created = False
    user_email = None

    if obj.parent_email:
        existing_user = await db.execute(select(User).where(User.email == obj.parent_email))
        if not existing_user.scalar_one_or_none():
            temp_password = _generate_temp_password()
            parent_user = User(
                school_id=obj.school_id,
                email=obj.parent_email,
                hashed_password=hash_password(temp_password),
                first_name=obj.parent_name.split()[0] if obj.parent_name else "Parent",
                last_name=" ".join(obj.parent_name.split()[1:]) if obj.parent_name and len(obj.parent_name.split()) > 1 else "",
                role=UserRole.PARENT,
                phone=obj.parent_phone,
                is_active=True,
            )
            db.add(parent_user)
            user_created = True
            user_email = obj.parent_email

    obj.status = "enrolled"
    if reviewed_by:
        obj.reviewed_by = reviewed_by

    await db.commit()
    await db.refresh(obj)
    await db.refresh(student)

    await emit(EventTypes.ADMISSION_ENROLLED, {
        "school_id": obj.school_id,
        "admission_id": obj.id,
        "student_id": student.id,
        "student_name": f"{student.first_name} {student.last_name}",
        "student_number": student_number,
    })

    return EnrollmentResult(
        admission=AdmissionOut.model_validate(obj),
        student_id=student.id,
        student_number=student_number,
        user_created=user_created,
        user_email=user_email,
        message=f"Student {student.first_name} {student.last_name} enrolled successfully with number {student_number}" + (f". Parent account created at {user_email}" if user_created else ""),
    )


@router.post("/{admission_id}/reject", response_model=AdmissionOut)
async def reject_admission(admission_id: UUID, reviewed_by: UUID = None, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Admission).where(Admission.id == admission_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Admission not found")
    if obj.status in ["enrolled"]:
        raise HTTPException(status_code=400, detail=f"Cannot reject admission in '{obj.status}' status")
    obj.status = "rejected"
    if reviewed_by:
        obj.reviewed_by = reviewed_by
    await db.commit()
    await db.refresh(obj)

    await emit(EventTypes.ADMISSION_REJECTED, {
        "school_id": obj.school_id,
        "admission_id": obj.id,
        "student_name": f"{obj.first_name} {obj.last_name}",
    })

    return obj


@router.post("/bulk-action", response_model=AdmissionBulkResult)
async def bulk_admission_action(school_id: UUID, data: AdmissionBulkAction, reviewed_by: UUID = None, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    processed = 0
    failed = 0
    errors = []

    for adm_id in data.admission_ids:
        try:
            result = await db.execute(select(Admission).where(Admission.id == adm_id, Admission.school_id == school_id))
            obj = result.scalar_one_or_none()
            if not obj:
                failed += 1
                errors.append(f"Admission {adm_id} not found")
                continue

            if data.action == "approve":
                if obj.status != "pending":
                    failed += 1
                    errors.append(f"Cannot approve admission in '{obj.status}' status")
                    continue
                obj.status = "approved"
            elif data.action == "reject":
                if obj.status == "enrolled":
                    failed += 1
                    errors.append(f"Cannot reject admission in '{obj.status}' status")
                    continue
                obj.status = "rejected"
            elif data.action == "enroll":
                if obj.status != "approved":
                    failed += 1
                    errors.append(f"Cannot enroll admission in '{obj.status}' status")
                    continue
                student_number = _generate_student_number(obj.school_id)
                student = Student(
                    school_id=obj.school_id,
                    class_id=obj.class_id,
                    student_number=student_number,
                    first_name=obj.first_name,
                    last_name=obj.last_name,
                    date_of_birth=obj.date_of_birth,
                    place_of_birth=obj.place_of_birth,
                    gender=obj.gender,
                    parent_name=obj.parent_name,
                    parent_phone=obj.parent_phone,
                    parent_email=obj.parent_email,
                    address=obj.address,
                    is_active=True,
                )
                db.add(student)
                obj.status = "enrolled"
            else:
                failed += 1
                errors.append(f"Unknown action: {data.action}")
                continue

            if reviewed_by:
                obj.reviewed_by = reviewed_by
            processed += 1
        except Exception as e:
            failed += 1
            errors.append(f"Error processing {adm_id}: {str(e)}")

    await db.commit()
    return AdmissionBulkResult(processed=processed, failed=failed, errors=errors)


@router.delete("/{admission_id}")
async def delete_admission(admission_id: UUID, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Admission).where(Admission.id == admission_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Admission not found")
    await db.delete(obj)
    await db.commit()
    return {"detail": "Admission deleted"}


# ---- Statistics ----

@router.get("/stats/overview", response_model=AdmissionStats)
async def get_admission_stats(school_id: UUID, academic_year: str, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    base_query = select(Admission).where(Admission.school_id == school_id, Admission.academic_year == academic_year)

    all_result = await db.execute(base_query)
    all_admissions = all_result.scalars().all()

    total = len(all_admissions)
    pending = sum(1 for a in all_admissions if a.status == "pending")
    approved = sum(1 for a in all_admissions if a.status == "approved")
    rejected = sum(1 for a in all_admissions if a.status == "rejected")
    enrolled = sum(1 for a in all_admissions if a.status == "enrolled")
    approval_rate = round(((approved + enrolled) / total * 100), 1) if total > 0 else 0

    classes_result = await db.execute(select(SchoolClass).where(SchoolClass.school_id == school_id))
    classes_map = {c.id: c.name for c in classes_result.scalars().all()}

    by_class = []
    class_counts = {}
    for a in all_admissions:
        cid = a.class_id
        class_counts[cid] = class_counts.get(cid, 0) + 1
    for cid, count in class_counts.items():
        by_class.append(AdmissionClassStat(
            class_id=cid,
            class_name=classes_map.get(cid, "Unassigned") if cid else "Unassigned",
            count=count,
        ))

    by_month = []
    month_counts = {}
    for a in all_admissions:
        if a.created_at:
            mk = a.created_at.strftime("%Y-%m")
            month_counts[mk] = month_counts.get(mk, 0) + 1
    for mk in sorted(month_counts.keys()):
        by_month.append(AdmissionMonthStat(month=mk, count=month_counts[mk]))

    return AdmissionStats(
        academic_year=academic_year,
        total=total,
        pending=pending,
        approved=approved,
        rejected=rejected,
        enrolled=enrolled,
        approval_rate=approval_rate,
        by_class=by_class,
        by_month=by_month,
    )
