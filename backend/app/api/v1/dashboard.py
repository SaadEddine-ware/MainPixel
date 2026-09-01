from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, extract
from uuid import UUID
from datetime import date, timedelta
from typing import Optional, List
from pydantic import BaseModel
from app.core.database import get_db
from app.models.student import Student
from app.models.attendance import Attendance
from app.models.finance import Payment, Invoice, FeeStructure
from app.models.user import User
from app.models.admission import Admission
from app.models.note import Note
from app.models.grade import Grade
from app.models.school_class import SchoolClass
from app.models.subject import Subject
from app.models.notification import Notification
from app.core.security import get_current_user

router = APIRouter()


class DashboardOverview(BaseModel):
    total_students: int
    total_teachers: int
    total_classes: int
    attendance_rate: float
    total_revenue: float
    pending_invoices: int
    pending_admissions: int
    total_parents: int


class AttendanceTrend(BaseModel):
    date: str
    present: int
    absent: int
    late: int
    excused: int
    rate: float


class AttendanceTrendsResponse(BaseModel):
    period: str
    trends: List[AttendanceTrend]
    overall_rate: float


class GradeDistribution(BaseModel):
    range_label: str
    count: int
    percentage: float


class GradeDistributionResponse(BaseModel):
    class_id: Optional[str]
    subject_id: Optional[str]
    semester: Optional[int]
    total_students: int
    average_score: float
    distribution: List[GradeDistribution]
    top_performers: List[dict]
    struggling_students: List[dict]


class ClassPerformance(BaseModel):
    class_id: str
    class_name: str
    student_count: int
    average_score: float
    attendance_rate: float
    pass_rate: float


class FinancialDashboard(BaseModel):
    total_revenue: float
    total_expected: float
    collection_rate: float
    monthly_revenue: List[dict]
    payment_methods: List[dict]
    overdue_amount: float


class RecentActivity(BaseModel):
    type: str
    description: str
    timestamp: Optional[str]


class TeacherWorkload(BaseModel):
    teacher_id: str
    teacher_name: str
    classes_count: int
    subjects_count: int
    students_count: int


@router.get("/stats", response_model=DashboardOverview)
async def get_dashboard_stats(school_id: UUID, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    student_result = await db.execute(
        select(func.count(Student.id)).where(Student.school_id == school_id, Student.is_active == True)
    )
    total_students = student_result.scalar() or 0

    teacher_result = await db.execute(
        select(func.count(User.id)).where(User.school_id == school_id, User.role == "teacher", User.is_active == True)
    )
    total_teachers = teacher_result.scalar() or 0

    class_result = await db.execute(
        select(func.count(SchoolClass.id)).where(SchoolClass.school_id == school_id, SchoolClass.is_active == True)
    )
    total_classes = class_result.scalar() or 0

    parent_result = await db.execute(
        select(func.count(User.id)).where(User.school_id == school_id, User.role == "parent", User.is_active == True)
    )
    total_parents = parent_result.scalar() or 0

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    att_result = await db.execute(
        select(func.count(Attendance.id)).where(
            Attendance.school_id == school_id,
            Attendance.date >= week_start,
            Attendance.date <= today,
        )
    )
    total_attendance = att_result.scalar() or 0

    present_result = await db.execute(
        select(func.count(Attendance.id)).where(
            Attendance.school_id == school_id,
            Attendance.date >= week_start,
            Attendance.date <= today,
            Attendance.status == "present",
        )
    )
    total_present = present_result.scalar() or 0
    attendance_rate = round((total_present / total_attendance * 100), 1) if total_attendance > 0 else 0

    revenue_result = await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.school_id == school_id)
    )
    total_revenue = float(revenue_result.scalar() or 0)

    pending_result = await db.execute(
        select(func.count(Invoice.id)).where(Invoice.school_id == school_id, Invoice.status == "pending")
    )
    pending_invoices = pending_result.scalar() or 0

    admission_result = await db.execute(
        select(func.count(Admission.id)).where(Admission.school_id == school_id, Admission.status == "pending")
    )
    pending_admissions = admission_result.scalar() or 0

    return DashboardOverview(
        total_students=total_students,
        total_teachers=total_teachers,
        total_classes=total_classes,
        attendance_rate=attendance_rate,
        total_revenue=total_revenue,
        pending_invoices=pending_invoices,
        pending_admissions=pending_admissions,
        total_parents=total_parents,
    )


@router.get("/attendance-trends", response_model=AttendanceTrendsResponse)
async def get_attendance_trends(
    school_id: UUID,
    period: str = "week",
    class_id: UUID = None,
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    if period == "week":
        start_date = today - timedelta(days=7)
    elif period == "month":
        start_date = today - timedelta(days=30)
    elif period == "quarter":
        start_date = today - timedelta(days=90)
    else:
        start_date = today - timedelta(days=7)

    query = select(Attendance).where(
        Attendance.school_id == school_id,
        Attendance.date >= start_date,
        Attendance.date <= today,
    )
    if class_id:
        query = query.where(Attendance.class_id == class_id)

    result = await db.execute(query)
    records = result.scalars().all()

    daily = {}
    for r in records:
        day_str = r.date.isoformat()
        if day_str not in daily:
            daily[day_str] = {"present": 0, "absent": 0, "late": 0, "excused": 0}
        if r.status in daily[day_str]:
            daily[day_str][r.status] += 1

    trends = []
    total_present = 0
    total_records = 0
    for day_str in sorted(daily.keys()):
        d = daily[day_str]
        day_total = d["present"] + d["absent"] + d["late"] + d["excused"]
        rate = round((d["present"] / day_total * 100), 1) if day_total > 0 else 0
        trends.append(AttendanceTrend(
            date=day_str,
            present=d["present"],
            absent=d["absent"],
            late=d["late"],
            excused=d["excused"],
            rate=rate,
        ))
        total_present += d["present"]
        total_records += day_total

    overall_rate = round((total_present / total_records * 100), 1) if total_records > 0 else 0

    return AttendanceTrendsResponse(
        period=period,
        trends=trends,
        overall_rate=overall_rate,
    )


@router.get("/grade-distribution", response_model=GradeDistributionResponse)
async def get_grade_distribution(
    school_id: UUID,
    class_id: UUID = None,
    subject_id: UUID = None,
    semester: int = None,
    academic_year: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Note).where(Note.school_id == school_id)
    if class_id:
        query = query.where(Note.class_id == class_id)
    if subject_id:
        query = query.where(Note.subject_id == subject_id)
    if semester:
        query = query.where(Note.semester == semester)
    if academic_year:
        query = query.where(Note.academic_year == academic_year)

    result = await db.execute(query)
    notes = result.scalars().all()

    if not notes:
        return GradeDistributionResponse(
            class_id=str(class_id) if class_id else None,
            subject_id=str(subject_id) if subject_id else None,
            semester=semester,
            total_students=0,
            average_score=0,
            distribution=[],
            top_performers=[],
            struggling_students=[],
        )

    scores = [n.score for n in notes]
    avg_score = round(sum(scores) / len(scores), 2)

    ranges = [
        ("0-4 (Fail)", 0, 4),
        ("4-8 (Weak)", 4, 8),
        ("8-10 (Average)", 8, 10),
        ("10-12 (Satisfactory)", 10, 12),
        ("12-14 (Good)", 12, 14),
        ("14-16 (Very Good)", 14, 16),
        ("16-18 (Excellent)", 16, 18),
        ("18-20 (Outstanding)", 18, 20),
    ]

    distribution = []
    for label, low, high in ranges:
        count = sum(1 for s in scores if low <= s < high or (high == 20 and s == 20))
        pct = round((count / len(scores) * 100), 1) if scores else 0
        distribution.append(GradeDistribution(range_label=label, count=count, percentage=pct))

    student_scores = {}
    for n in notes:
        sid = str(n.student_id)
        if sid not in student_scores:
            student_scores[sid] = []
        student_scores[sid].append(n.score)

    student_avgs = [(sid, sum(s) / len(s)) for sid, s in student_scores.items()]
    student_avgs.sort(key=lambda x: x[1], reverse=True)

    top_performers = [{"student_id": sid, "average": round(avg, 2)} for sid, avg in student_avgs[:5]]
    struggling_students = [{"student_id": sid, "average": round(avg, 2)} for sid, avg in student_avgs[-5:] if avg < 10]

    return GradeDistributionResponse(
        class_id=str(class_id) if class_id else None,
        subject_id=str(subject_id) if subject_id else None,
        semester=semester,
        total_students=len(student_scores),
        average_score=avg_score,
        distribution=distribution,
        top_performers=top_performers,
        struggling_students=struggling_students,
    )


@router.get("/class-performance", response_model=List[ClassPerformance])
async def get_class_performance(
    school_id: UUID,
    academic_year: str = None,
    db: AsyncSession = Depends(get_db),
):
    classes_result = await db.execute(
        select(SchoolClass).where(SchoolClass.school_id == school_id, SchoolClass.is_active == True)
    )
    classes = classes_result.scalars().all()

    performances = []
    for cls in classes:
        students_result = await db.execute(
            select(func.count(Student.id)).where(Student.class_id == cls.id, Student.is_active == True)
        )
        student_count = students_result.scalar() or 0

        notes_query = select(Note).where(Note.class_id == cls.id)
        if academic_year:
            notes_query = notes_query.where(Note.academic_year == academic_year)
        notes_result = await db.execute(notes_query)
        notes = notes_result.scalars().all()

        if notes:
            avg_score = round(sum(n.score for n in notes) / len(notes), 2)
            pass_count = sum(1 for n in notes if n.score >= 10)
            pass_rate = round((pass_count / len(notes) * 100), 1)
        else:
            avg_score = 0
            pass_rate = 0

        today = date.today()
        week_start = today - timedelta(days=7)
        att_result = await db.execute(
            select(func.count(Attendance.id)).where(
                Attendance.class_id == cls.id,
                Attendance.date >= week_start,
            )
        )
        total_att = att_result.scalar() or 0

        present_result = await db.execute(
            select(func.count(Attendance.id)).where(
                Attendance.class_id == cls.id,
                Attendance.date >= week_start,
                Attendance.status == "present",
            )
        )
        total_present = present_result.scalar() or 0
        attendance_rate = round((total_present / total_att * 100), 1) if total_att > 0 else 0

        performances.append(ClassPerformance(
            class_id=str(cls.id),
            class_name=cls.name,
            student_count=student_count,
            average_score=avg_score,
            attendance_rate=attendance_rate,
            pass_rate=pass_rate,
        ))

    return performances


@router.get("/financial-summary", response_model=FinancialDashboard)
async def get_financial_summary(
    school_id: UUID,
    academic_year: str = None,
    db: AsyncSession = Depends(get_db),
):
    revenue_result = await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.school_id == school_id)
    )
    total_revenue = float(revenue_result.scalar() or 0)

    invoices_query = select(Invoice).where(Invoice.school_id == school_id)
    if academic_year:
        invoices_query = invoices_query.join(FeeStructure, Invoice.fee_structure_id == FeeStructure.id).where(
            FeeStructure.academic_year == academic_year
        )
    invoices_result = await db.execute(invoices_query)
    invoices = invoices_result.scalars().all()

    total_expected = sum(float(inv.amount) for inv in invoices)
    collection_rate = round((total_revenue / total_expected * 100), 1) if total_expected > 0 else 0

    overdue_amount = sum(float(inv.amount) for inv in invoices if inv.status in ["pending", "partial"])

    payments_result = await db.execute(
        select(Payment).where(Payment.school_id == school_id)
    )
    payments = payments_result.scalars().all()

    monthly = {}
    for p in payments:
        if p.payment_date:
            mk = p.payment_date.strftime("%Y-%m")
            monthly[mk] = monthly.get(mk, 0) + float(p.amount)
    monthly_revenue = [{"month": m, "revenue": round(r, 2)} for m, r in sorted(monthly.items())]

    method_counts = {}
    for p in payments:
        method_counts[p.payment_method] = method_counts.get(p.payment_method, 0) + 1
    payment_methods = [{"method": m, "count": c} for m, c in sorted(method_counts.items(), key=lambda x: x[1], reverse=True)]

    return FinancialDashboard(
        total_revenue=total_revenue,
        total_expected=total_expected,
        collection_rate=collection_rate,
        monthly_revenue=monthly_revenue,
        payment_methods=payment_methods,
        overdue_amount=overdue_amount,
    )


@router.get("/recent-activity", response_model=List[RecentActivity])
async def get_recent_activity(school_id: UUID, limit: int = 10, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    activities = []

    recent_students = await db.execute(
        select(Student).where(Student.school_id == school_id, Student.is_active == True)
        .order_by(Student.created_at.desc()).limit(limit)
    )
    for s in recent_students.scalars().all():
        activities.append(RecentActivity(
            type="student_enrolled",
            description=f"{s.first_name} {s.last_name} enrolled",
            timestamp=s.created_at.isoformat() if s.created_at else None,
        ))

    recent_admissions = await db.execute(
        select(Admission).where(Admission.school_id == school_id)
        .order_by(Admission.created_at.desc()).limit(limit)
    )
    for a in recent_admissions.scalars().all():
        activities.append(RecentActivity(
            type=f"admission_{a.status}",
            description=f"Admission for {a.first_name} {a.last_name} - {a.status}",
            timestamp=a.created_at.isoformat() if a.created_at else None,
        ))

    recent_payments = await db.execute(
        select(Payment).where(Payment.school_id == school_id)
        .order_by(Payment.created_at.desc()).limit(limit)
    )
    for p in recent_payments.scalars().all():
        activities.append(RecentActivity(
            type="payment_received",
            description=f"Payment of {p.amount} received",
            timestamp=p.created_at.isoformat() if p.created_at else None,
        ))

    recent_notes = await db.execute(
        select(Note).where(Note.school_id == school_id)
        .order_by(Note.created_at.desc()).limit(limit)
    )
    for n in recent_notes.scalars().all():
        activities.append(RecentActivity(
            type="grade_posted",
            description=f"Grade posted: {n.score}/{n.max_score}",
            timestamp=n.created_at.isoformat() if n.created_at else None,
        ))

    activities.sort(key=lambda x: x.timestamp or "", reverse=True)
    return activities[:limit]


@router.get("/teacher-workload", response_model=List[TeacherWorkload])
async def get_teacher_workload(school_id: UUID, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.models.timetable import Schedule

    teachers_result = await db.execute(
        select(User).where(User.school_id == school_id, User.role == "teacher", User.is_active == True)
    )
    teachers = teachers_result.scalars().all()

    workloads = []
    for teacher in teachers:
        schedules_result = await db.execute(
            select(Schedule).where(Schedule.teacher_id == teacher.id, Schedule.school_id == school_id)
        )
        schedules = schedules_result.scalars().all()

        class_ids = set(s.class_id for s in schedules)
        subject_ids = set(s.subject_id for s in schedules)

        students_count = 0
        for cid in class_ids:
            sc_result = await db.execute(
                select(func.count(Student.id)).where(Student.class_id == cid, Student.is_active == True)
            )
            students_count += sc_result.scalar() or 0

        workloads.append(TeacherWorkload(
            teacher_id=str(teacher.id),
            teacher_name=f"{teacher.first_name} {teacher.last_name}",
            classes_count=len(class_ids),
            subjects_count=len(subject_ids),
            students_count=students_count,
        ))

    return workloads


@router.get("/summary")
async def get_dashboard_summary(school_id: UUID, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    student_count = (await db.execute(
        select(func.count(Student.id)).where(Student.school_id == school_id, Student.is_active == True)
    )).scalar() or 0

    week_att = (await db.execute(
        select(func.count(Attendance.id)).where(
            Attendance.school_id == school_id, Attendance.date >= week_start, Attendance.date <= today
        )
    )).scalar() or 0

    week_present = (await db.execute(
        select(func.count(Attendance.id)).where(
            Attendance.school_id == school_id, Attendance.date >= week_start,
            Attendance.date <= today, Attendance.status == "present"
        )
    )).scalar() or 0

    month_revenue = (await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.school_id == school_id, Payment.payment_date >= month_start
        )
    )).scalar() or 0

    pending_inv = (await db.execute(
        select(func.count(Invoice.id)).where(Invoice.school_id == school_id, Invoice.status == "pending")
    )).scalar() or 0

    pending_adm = (await db.execute(
        select(func.count(Admission.id)).where(Admission.school_id == school_id, Admission.status == "pending")
    )).scalar() or 0

    unread_notif = (await db.execute(
        select(func.count(Notification.id)).where(
            Notification.school_id == school_id, Notification.is_read == False
        )
    )).scalar() or 0

    return {
        "students": student_count,
        "week_attendance_rate": round((week_present / week_att * 100), 1) if week_att > 0 else 0,
        "month_revenue": float(month_revenue),
        "pending_invoices": pending_inv,
        "pending_admissions": pending_adm,
        "unread_notifications": unread_notif,
    }
