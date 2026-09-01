from typing import List, Dict, Optional, Tuple
from datetime import datetime
from app.repositories.database import get_session
from app.models.assignment import Assignment
from app.models.assignment_grade import AssignmentGrade
from app.models.matiere import Matiere
from app.models.student import Student
from app.models.note import Note
from sqlalchemy import text


# ── Assignment CRUD ──────────────────────────────────────────────────────

def list_assignments(classe_id: int, matiere_id: int, semester: int) -> List[Assignment]:
    with get_session() as session:
        return session.query(Assignment).filter_by(
            classe_id=classe_id, matiere_id=matiere_id, semester=semester
        ).order_by(Assignment.id).all()


def add_assignment(classe_id: int, matiere_id: int, semester: int,
                   title: str, coefficient: float = 1.0, date: str = "") -> Assignment:
    with get_session() as session:
        a = Assignment(
            classe_id=classe_id, matiere_id=matiere_id, semester=semester,
            title=title, coefficient=coefficient, date=date,
            created_at=datetime.now(),
        )
        session.add(a)
        session.commit()
        session.refresh(a)
        return a


def delete_assignment(assignment_id: int):
    with get_session() as session:
        a = session.get(Assignment, assignment_id)
        if a:
            session.execute(
                text("DELETE FROM assignment_grades WHERE assignment_id = :aid"),
                {"aid": assignment_id}
            )
            session.delete(a)
            session.commit()


def rename_assignment(assignment_id: int, title: str):
    with get_session() as session:
        a = session.get(Assignment, assignment_id)
        if a:
            a.title = title
            session.commit()


def update_assignment_coefficient(assignment_id: int, coefficient: float):
    with get_session() as session:
        a = session.get(Assignment, assignment_id)
        if a:
            a.coefficient = coefficient
            session.commit()


# ── Assignment Grade CRUD ───────────────────────────────────────────────

def get_assignment_grades(assignment_id: int) -> Dict[int, float]:
    with get_session() as session:
        rows = session.query(AssignmentGrade).filter_by(
            assignment_id=assignment_id
        ).all()
        return {g.student_id: g.valeur for g in rows}


def save_assignment_grades(assignment_id: int, grades: Dict[int, float]):
    with get_session() as session:
        for student_id, valeur in grades.items():
            existing = session.query(AssignmentGrade).filter_by(
                assignment_id=assignment_id, student_id=student_id
            ).first()
            if existing:
                existing.valeur = valeur
            else:
                session.add(AssignmentGrade(
                    assignment_id=assignment_id, student_id=student_id, valeur=valeur
                ))
        session.commit()


# ── Subject average calculation ─────────────────────────────────────────

def calc_subject_moyenne(student_id: int, matiere_id: int, semester: int) -> float:
    with get_session() as session:
        assignments = session.query(Assignment).filter_by(
            matiere_id=matiere_id, semester=semester
        ).all()
        if not assignments:
            return 0.0
        aids = [a.id for a in assignments]
        if not aids:
            return 0.0
        grades = session.query(AssignmentGrade).filter(
            AssignmentGrade.assignment_id.in_(aids),
            AssignmentGrade.student_id == student_id
        ).all()
        if not grades:
            return 0.0
        grade_map = {g.assignment_id: g.valeur for g in grades}
        weighted_sum = 0.0
        total_coef = 0.0
        for a in assignments:
            v = grade_map.get(a.id)
            if v is not None:
                weighted_sum += v * a.coefficient
                total_coef += a.coefficient
        return weighted_sum / total_coef if total_coef > 0 else 0.0


def calc_all_moyennes(classe_id: int, matiere_id: int, semester: int) -> Dict[int, float]:
    with get_session() as session:
        students = session.query(Student).filter_by(class_id=classe_id).order_by(Student.sort_order).all()
        sids = [s.id for s in students]
        assignments = session.query(Assignment).filter_by(
            matiere_id=matiere_id, semester=semester
        ).all()
        if not assignments:
            return {s.id: 0.0 for s in students}
        aids = [a.id for a in assignments]
        grade_rows = session.query(AssignmentGrade).filter(
            AssignmentGrade.assignment_id.in_(aids),
            AssignmentGrade.student_id.in_(sids)
        ).all()
    grade_map: Dict[int, Dict[int, float]] = {}
    for g in grade_rows:
        if g.student_id not in grade_map:
            grade_map[g.student_id] = {}
        grade_map[g.student_id][g.assignment_id] = g.valeur

    result = {}
    for s in students:
        weighted_sum = 0.0
        total_coef = 0.0
        gs = grade_map.get(s.id, {})
        for a in assignments:
            v = gs.get(a.id)
            if v is not None:
                weighted_sum += v * a.coefficient
                total_coef += a.coefficient
        result[s.id] = weighted_sum / total_coef if total_coef > 0 else 0.0
    return result


# ── Sync to Note ────────────────────────────────────────────────────────

def sync_moyennes_to_notes(classe_id: int, matiere_id: int, semester: int):
    """Calculate subject averages from assignment grades and write to Note table."""
    moyennes = calc_all_moyennes(classe_id, matiere_id, semester)
    with get_session() as session:
        for student_id, valeur in moyennes.items():
            if valeur == 0.0:
                continue
            existing = session.query(Note).filter_by(
                student_id=student_id, matiere_id=matiere_id, semester=semester
            ).first()
            if existing:
                existing.valeur = round(valeur, 2)
            else:
                session.add(Note(
                    student_id=student_id, matiere_id=matiere_id,
                    semester=semester, valeur=round(valeur, 2)
                ))
        session.commit()


# ── Export / Import JSON ────────────────────────────────────────────────

def export_assignments_json(classe_id: int, matiere_id: int, semester: int) -> dict:
    with get_session() as session:
        matiere = session.get(Matiere, matiere_id)
        if not matiere:
            raise ValueError("Matiere not found")
        assignments = session.query(Assignment).filter_by(
            classe_id=classe_id, matiere_id=matiere_id, semester=semester
        ).order_by(Assignment.id).all()
        students = session.query(Student).filter_by(
            class_id=classe_id
        ).order_by(Student.sort_order).all()
    data = {
        "matiere": matiere.name if matiere else "",
        "matiere_id": matiere_id,
        "classe_id": classe_id,
        "semester": semester,
        "exported_at": datetime.now().isoformat(),
        "assignments": [],
        "grades": {},
    }
    for a in assignments:
        data["assignments"].append({
            "id": a.id, "title": a.title, "coefficient": a.coefficient,
            "date": a.date or "",
        })
        grades = get_assignment_grades(a.id)
        data["grades"][str(a.id)] = {str(sid): v for sid, v in grades.items()}
    return data


def import_assignments_json(data: dict) -> Tuple[int, int]:
    """Import from JSON dict. Returns (assignments_created, grades_saved)."""
    matiere_id = data.get("matiere_id")
    classe_id = data.get("classe_id")
    semester = data.get("semester", 1)
    if not matiere_id or not classe_id:
        raise ValueError("Missing matiere_id or classe_id")

    a_count = 0
    g_count = 0
    with get_session() as session:
        for idx, adef in enumerate(data.get("assignments", [])):
            existing = session.query(Assignment).filter_by(
                classe_id=classe_id, matiere_id=matiere_id,
                semester=semester, title=adef["title"]
            ).first()
            if not existing:
                a = Assignment(
                    classe_id=classe_id, matiere_id=matiere_id,
                    semester=semester, title=adef["title"],
                    coefficient=adef.get("coefficient", 1.0),
                    date=adef.get("date", ""),
                    created_at=datetime.now(),
                )
                session.add(a)
                session.flush()
                a_count += 1
                existing = a
            aid = existing.id
            assignment_key = str(adef.get("id", idx + 1))
            all_grades = data.get("grades", {})
            for sid_str, student_grades in all_grades.items():
                if assignment_key not in student_grades:
                    continue
                student_id = int(sid_str)
                valeur = student_grades[assignment_key]
                existing_g = session.query(AssignmentGrade).filter_by(
                    assignment_id=aid, student_id=student_id
                ).first()
                if existing_g:
                    existing_g.valeur = valeur
                else:
                    session.add(AssignmentGrade(
                        assignment_id=aid, student_id=student_id, valeur=valeur
                    ))
                g_count += 1
        session.commit()
    return a_count, g_count
