import csv
import tempfile
import shutil
from datetime import datetime
from app.repositories.database import get_session
from app.models.student import Student
from app.models.classe import Classe
from app.models.audit_log import AuditLog

MAX_STUDENTS_PER_CLASS = 60


def load_students(class_id):
    session = get_session()
    try:
        students = session.query(Student).filter_by(
            class_id=class_id
        ).order_by(Student.sort_order).all()
        return students
    finally:
        session.close()


def list_students_for_class(class_id):
    return load_students(class_id)


def search_students(class_id, query):
    return search_students_in_class(class_id, query)


def add_student(class_id, full_name, code_massar="", birth_date="", notes=""):
    session = get_session()
    try:
        count = session.query(Student).filter_by(class_id=class_id).count()
        if count >= MAX_STUDENTS_PER_CLASS:
            raise ValueError(f"Maximum {MAX_STUDENTS_PER_CLASS} students per class")
        if code_massar:
            dup = session.query(Student).filter_by(code_massar=code_massar).first()
            if dup:
                raise ValueError(f"Student number '{code_massar}' already exists")
        student = Student(
            class_id=class_id,
            code_massar=code_massar,
            full_name=full_name,
            birth_date=birth_date,
            comment=notes,
            sort_order=count,
            created_at=datetime.now(),
        )
        session.add(student)
        session.flush()
        student_id = student.id
        session.add(AuditLog(action="create", entity_type="student", entity_id=student_id,
                             details=f"Added student {full_name}"))
        session.commit()
        return student_id
    finally:
        session.close()


def update_student(student_id, full_name=None, code_massar=None, birth_date=None, notes=None):
    session = get_session()
    try:
        student = session.query(Student).filter_by(id=student_id).first()
        if not student:
            raise IndexError("Student not found")
        if full_name is not None:
            student.full_name = full_name
        if code_massar is not None:
            if code_massar and code_massar != student.code_massar:
                dup = session.query(Student).filter(
                    Student.code_massar == code_massar,
                    Student.id != student_id
                ).first()
                if dup:
                    raise ValueError(f"Student number '{code_massar}' already exists")
            student.code_massar = code_massar
        if birth_date is not None:
            student.birth_date = birth_date
        if notes is not None:
            student.comment = notes
        student.updated_at = datetime.now()
        session.commit()
        session.add(AuditLog(action="update", entity_type="student", entity_id=student_id,
                             details=f"Updated student {full_name}"))
        session.commit()
        return student
    finally:
        session.close()


def delete_student(student_id):
    session = get_session()
    try:
        student = session.query(Student).filter_by(id=student_id).first()
        if not student:
            raise IndexError("Student not found")
        name = student.full_name
        class_id = student.class_id
        session.delete(student)
        session.commit()
        _renumber_students(session, class_id)
        session.add(AuditLog(action="delete", entity_type="student", entity_id=student_id,
                             details=f"Deleted student {name}"))
        session.commit()
    finally:
        session.close()


def _renumber_students(session, class_id):
    students = session.query(Student).filter_by(class_id=class_id).order_by(Student.sort_order).all()
    for i, s in enumerate(students):
        s.sort_order = i
    session.commit()


def search_students_in_class(class_id, query):
    session = get_session()
    try:
        q = f"%{query}%"
        students = session.query(Student).filter(
            Student.class_id == class_id,
            (Student.full_name.ilike(q) | Student.code_massar.ilike(q))
        ).order_by(Student.sort_order).all()
        return students
    finally:
        session.close()


def import_csv_to_class(class_id, csv_path):
    session = get_session()
    try:
        imported = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                return 0
            for row in reader:
                if not row or all(c.strip() == "" for c in row):
                    continue
                imported.append({
                    "name": row[0].strip() if len(row) > 0 else "",
                    "number": row[1].strip() if len(row) > 1 else "",
                    "birth": row[2].strip() if len(row) > 2 else "",
                    "notes": row[3].strip() if len(row) > 3 else "",
                })

        existing = session.query(Student).filter_by(class_id=class_id).count()
        existing_nums = {
            s.code_massar for s in
            session.query(Student.code_massar).filter_by(class_id=class_id).all()
            if s.code_massar
        }
        added = 0
        for s in imported:
            if s["number"] in existing_nums:
                continue
            if existing + added >= MAX_STUDENTS_PER_CLASS:
                break
            student = Student(
                class_id=class_id,
                code_massar=s["number"],
                full_name=s["name"],
                birth_date=s["birth"],
                comment=s["notes"],
                sort_order=existing + added,
                created_at=datetime.now(),
            )
            session.add(student)
            added += 1
        if added > 0:
            session.commit()
            session.add(AuditLog(action="import", entity_type="student", entity_id=class_id,
                                 details=f"Imported {added} students via CSV"))
            session.commit()
        return added
    finally:
        session.close()
