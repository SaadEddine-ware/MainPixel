from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.core.database import get_db
from app.models.student import Student
from app.models.note import Note
from app.models.subject import Subject
from app.models.school_class import SchoolClass
from app.models.school import School
from app.core.security import get_current_user

router = APIRouter()


@router.get("/bulletin/{student_id}")
async def get_bulletin(student_id: UUID, semester: int, academic_year: str, payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    student_r = await db.execute(select(Student).where(Student.id == student_id))
    student = student_r.scalar_one_or_none()
    if not student:
        return {"error": "Student not found"}

    class_r = await db.execute(select(SchoolClass).where(SchoolClass.id == student.class_id))
    school_class = class_r.scalar_one_or_none()

    school_r = await db.execute(select(School).where(School.id == student.school_id))
    school = school_r.scalar_one_or_none()

    notes_r = await db.execute(
        select(Note).where(Note.student_id == student_id, Note.semester == semester, Note.academic_year == academic_year)
    )
    notes = notes_r.scalars().all()

    subjects = {}
    for n in notes:
        sub_r = await db.execute(select(Subject).where(Subject.id == n.subject_id))
        sub = sub_r.scalar_one_or_none()
        if sub:
            subjects[str(n.subject_id)] = {
                "name": sub.name,
                "coefficient": n.coefficient,
                "score": n.score,
                "max_score": n.max_score,
            }

    total_weighted = sum(n.score * n.coefficient for n in notes)
    total_coeff = sum(n.coefficient for n in notes)
    moyenne = round(total_weighted / total_coeff, 2) if total_coeff > 0 else 0

    rows = ""
    for sid, info in subjects.items():
        pct = round(info["score"] / info["max_score"] * 100, 1) if info["max_score"] > 0 else 0
        rows += f"<tr><td>{info['name']}</td><td>{info['coefficient']}</td><td>{info['score']}/{info['max_score']}</td><td>{pct}%</td></tr>"

    html = f"""
    <html><head><style>
        body {{ font-family: Arial; margin: 40px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        th {{ background: #2563eb; color: white; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .moyenne {{ font-size: 24px; font-weight: bold; color: {'#16a34a' if moyenne >= 10 else '#dc2626'}; }}
    </style></head><body>
        <div class="header">
            <h1>{school.name if school else 'School'}</h1>
            <h2>Bulletin - Semester {semester}</h2>
            <p>Student: {student.first_name} {student.last_name} | Class: {school_class.name if school_class else 'N/A'} | Year: {academic_year}</p>
        </div>
        <table>
            <tr><th>Subject</th><th>Coefficient</th><th>Score</th><th>Percentage</th></tr>
            {rows}
        </table>
        <p style="margin-top:20px;">Moyenne: <span class="moyenne">{moyenne}/20</span></p>
        <p>Decision: {'PASS' if moyenne >= 10 else 'FAIL'}</p>
    </body></html>
    """
    return HTMLResponse(content=html)
