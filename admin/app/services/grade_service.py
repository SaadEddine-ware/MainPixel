from typing import List, Dict, Optional, Tuple
from app.repositories.database import get_session
from app.models.matiere import Matiere
from app.models.note import Note
from app.models.student import Student

# ── Seed data (Moroccan official coefficients) ──────────────────────────

_PRIMARY_1 = [
    ("Langue arabe", 3), ("Langue francaise", 3), ("Mathematiques", 3),
    ("Sciences de la Vie et de la Terre", 2), ("Activites artistiques", 1),
    ("Education physique", 1), ("Education islamique", 1),
]
_PRIMARY_3 = [
    ("Langue arabe", 3), ("Langue francaise", 3), ("Mathematiques", 3),
    ("Sciences de la Vie et de la Terre", 2), ("Histoire-Geographie", 2),
    ("Activites artistiques", 1), ("Education physique", 1), ("Education islamique", 1),
]
_PRIMARY_5 = [
    ("Langue arabe", 3), ("Langue francaise", 3), ("Mathematiques", 3),
    ("Sciences de la Vie et de la Terre", 2), ("Physique-Chimie", 2),
    ("Histoire-Geographie", 2), ("Activites artistiques", 1),
    ("Education physique", 1), ("Education islamique", 1),
]

SEED_MATIERES = {
    "primary": {
        "1": _PRIMARY_1, "2": _PRIMARY_1,
        "3": _PRIMARY_3, "4": _PRIMARY_3,
        "5": _PRIMARY_5, "6": _PRIMARY_5,
    },
    "middle": {
        "1": [("Langue arabe", 4), ("Langue francaise", 4), ("Mathematiques", 3),
               ("Physique-Chimie", 2), ("Sciences de la Vie et de la Terre", 2),
               ("Histoire-Geographie", 2), ("Education islamique", 1), ("Education physique", 1)],
        "2": [("Langue arabe", 4), ("Langue francaise", 4), ("Mathematiques", 3),
               ("Physique-Chimie", 2), ("Sciences de la Vie et de la Terre", 2),
               ("Histoire-Geographie", 2), ("Education islamique", 1), ("Education physique", 1)],
        "3": [("Langue arabe", 4), ("Langue francaise", 4), ("Mathematiques", 3),
               ("Physique-Chimie", 2), ("Sciences de la Vie et de la Terre", 2),
               ("Histoire-Geographie", 2), ("Education islamique", 1),
               ("Education physique", 1), ("Informatique", 1)],
    },
}

# Default Tronc Commun subjects for secondary (no branch)
_TC_1 = [
    ("Langue arabe", 2), ("Langue francaise", 3), ("Langue anglaise", 2),
    ("Mathematiques", 4), ("Physique-Chimie", 4),
    ("Sciences de la Vie et de la Terre", 2), ("Histoire-Geographie", 2),
    ("Education islamique", 2), ("Philosophie", 2),
    ("Informatique", 2), ("Education physique", 2),
]
_TC_2 = _TC_1.copy()
_TC_3 = _TC_1.copy()

# Lycee branches: (branch_name, year, [(name, coef)])
LYCEE_BRANCHES = [
    ("Tronc Commun Scientifique", "1", [
        ("Langue arabe", 2), ("Langue francaise", 3), ("Langue anglaise", 2),
        ("Mathematiques", 4), ("Physique-Chimie", 4),
        ("Sciences de la Vie et de la Terre", 2), ("Histoire-Geographie", 2),
        ("Education islamique", 2), ("Philosophie", 2),
        ("Informatique", 2), ("Education physique", 2),
    ]),
    ("Tronc Commun Lettres", "1", [
        ("Langue arabe", 4), ("Langue francaise", 4), ("Langue anglaise", 3),
        ("Mathematiques", 2), ("Sciences de la Vie et de la Terre", 2),
        ("Histoire-Geographie", 4), ("Education islamique", 2),
        ("Philosophie", 2), ("Informatique", 2),
        ("Culture artistique", 2), ("Education physique", 2),
    ]),
    ("Tronc Commun Technologique", "1", [
        ("Langue arabe", 2), ("Langue francaise", 3), ("Langue anglaise", 2),
        ("Mathematiques", 4), ("Physique-Chimie", 4),
        ("Sciences de l'Ingenieur", 4), ("Histoire-Geographie", 2),
        ("Education islamique", 2), ("Philosophie", 2),
        ("Informatique", 2), ("Education physique", 2),
    ]),
    ("1BAC Sciences Mathematiques", "2", [
        ("Mathematiques", 9), ("Physique-Chimie", 7),
        ("Sciences de la Vie et de la Terre", 3),
        ("Langue arabe", 2), ("Langue francaise", 4), ("Langue anglaise", 2),
        ("Histoire-Geographie", 2), ("Education islamique", 2),
        ("Philosophie", 2), ("Education physique", 1),
    ]),
    ("1BAC Sciences de la Vie et de la Terre", "2", [
        ("Sciences de la Vie et de la Terre", 7),
        ("Mathematiques", 7), ("Physique-Chimie", 7),
        ("Langue arabe", 2), ("Langue francaise", 4), ("Langue anglaise", 2),
        ("Histoire-Geographie", 2), ("Education islamique", 2),
        ("Philosophie", 2), ("Education physique", 1),
    ]),
    ("1BAC Physique-Chimie", "2", [
        ("Physique-Chimie", 8), ("Mathematiques", 7),
        ("Sciences de la Vie et de la Terre", 3),
        ("Langue arabe", 2), ("Langue francaise", 4), ("Langue anglaise", 2),
        ("Histoire-Geographie", 2), ("Education islamique", 2),
        ("Philosophie", 2), ("Education physique", 1),
    ]),
    ("1BAC Lettres et Sciences Humaines", "2", [
        ("Langue arabe", 6), ("Histoire-Geographie", 4),
        ("Langue francaise", 4), ("Philosophie", 4),
        ("Langue anglaise", 3), ("Education islamique", 2),
        ("Mathematiques", 2), ("Culture artistique", 2),
        ("Education physique", 1),
    ]),
    ("1BAC Sciences Economiques et Gestion", "2", [
        ("Economie et Gestion", 5), ("Mathematiques", 5),
        ("Histoire-Geographie", 3), ("Langue arabe", 3),
        ("Langue francaise", 4), ("Langue anglaise", 2),
        ("Education islamique", 2), ("Philosophie", 2),
        ("Education physique", 1),
    ]),
    ("1BAC Sciences et Technologie Electrique", "2", [
        ("Physique appliquee", 6), ("Sciences de l'Ingenieur electrique", 6),
        ("Mathematiques", 5), ("Informatique", 3),
        ("Langue arabe", 2), ("Langue francaise", 4), ("Langue anglaise", 2),
        ("Histoire-Geographie", 2), ("Education islamique", 2),
        ("Philosophie", 2), ("Education physique", 1),
    ]),
    ("1BAC Sciences et Technologie Mecanique", "2", [
        ("Sciences de l'Ingenieur mecanique", 6), ("Physique appliquee", 6),
        ("Mathematiques", 5), ("Informatique", 3),
        ("Langue arabe", 2), ("Langue francaise", 4), ("Langue anglaise", 2),
        ("Histoire-Geographie", 2), ("Education islamique", 2),
        ("Philosophie", 2), ("Education physique", 1),
    ]),
    ("2BAC Sciences Mathematiques A", "3", [
        ("Mathematiques", 9), ("Physique-Chimie", 7),
        ("Sciences de l'Ingenieur", 5),
        ("Langue arabe", 2), ("Langue francaise", 4), ("Langue anglaise", 2),
        ("Education islamique", 2), ("Education physique", 1),
    ]),
    ("2BAC Sciences Mathematiques B", "3", [
        ("Mathematiques", 9), ("Physique-Chimie", 7),
        ("Sciences de la Vie et de la Terre", 4),
        ("Langue arabe", 2), ("Langue francaise", 4), ("Langue anglaise", 2),
        ("Education islamique", 2), ("Education physique", 1),
    ]),
    ("2BAC Sciences de la Vie et de la Terre", "3", [
        ("Sciences de la Vie et de la Terre", 8),
        ("Physique-Chimie", 5), ("Mathematiques", 5),
        ("Langue arabe", 2), ("Langue francaise", 4), ("Langue anglaise", 2),
        ("Education islamique", 2), ("Education physique", 1),
    ]),
    ("2BAC Sciences Physiques", "3", [
        ("Physique-Chimie", 9), ("Mathematiques", 7),
        ("Sciences de la Vie et de la Terre", 3),
        ("Langue arabe", 2), ("Langue francaise", 4), ("Langue anglaise", 2),
        ("Education islamique", 2), ("Education physique", 1),
    ]),
    ("2BAC Lettres et Sciences Humaines", "3", [
        ("Langue arabe", 7), ("Histoire-Geographie", 5),
        ("Philosophie", 5), ("Langue francaise", 4),
        ("Langue anglaise", 3), ("Education islamique", 2),
        ("Education physique", 1),
    ]),
    ("2BAC Sciences Economiques et Gestion", "3", [
        ("Economie et Gestion", 7), ("Mathematiques", 5),
        ("Histoire-Geographie", 4), ("Langue arabe", 3),
        ("Langue francaise", 4), ("Langue anglaise", 3),
        ("Education islamique", 2), ("Education physique", 1),
    ]),
    ("2BAC Sciences et Technologie Electrique", "3", [
        ("Physique appliquee et Chimie", 7),
        ("Sciences de l'Ingenieur electrique", 7),
        ("Mathematiques", 5), ("Informatique industrielle", 3),
        ("Langue arabe", 2), ("Langue francaise", 4), ("Langue anglaise", 2),
        ("Education islamique", 2), ("Education physique", 1),
    ]),
    ("2BAC Sciences et Technologie Mecanique", "3", [
        ("Sciences de l'Ingenieur mecanique", 7), ("Physique appliquee", 7),
        ("Mathematiques", 5), ("Informatique industrielle", 3),
        ("Langue arabe", 2), ("Langue francaise", 4), ("Langue anglaise", 2),
        ("Education islamique", 2), ("Education physique", 1),
    ]),
]


def seed_matieres(session=None):
    if session is None:
        with get_session() as s:
            return _do_seed(s)
    return _do_seed(session)


def _do_seed(session):
    session.query(Matiere).filter(
        Matiere.year_name.in_(["1-2", "3-4", "5-6"])
    ).delete(synchronize_session=False)
    count = 0
    for level_key, years in SEED_MATIERES.items():
        existing = session.query(Matiere).filter_by(level_key=level_key).count()
        if existing > 0:
            continue
        for year_name, subjects in years.items():
            for name, coeff in subjects:
                session.add(Matiere(
                    name=name, coefficient=coeff,
                    level_key=level_key, year_name=year_name, branch="",
                ))
                count += 1
    existing = session.query(Matiere).filter_by(level_key="lycee").count()
    if existing == 0:
        for yr in ("1", "2", "3"):
            for name, coeff in _TC_1:
                session.add(Matiere(
                    name=name, coefficient=coeff,
                    level_key="lycee", year_name=yr, branch="",
                ))
                count += 1
        for branch_name, year_name, subjects in LYCEE_BRANCHES:
            for name, coeff in subjects:
                session.add(Matiere(
                    name=name, coefficient=coeff,
                    level_key="lycee", year_name=year_name, branch=branch_name,
                ))
                count += 1
    if count > 0:
        session.commit()
    return count


# ── Matiere CRUD ────────────────────────────────────────────────────────

def list_matieres(level_key: str, year_name: str, branch: str = "") -> List[Matiere]:
    with get_session() as session:
        q = session.query(Matiere).filter_by(
            level_key=level_key, year_name=year_name
        )
        if branch:
            q = q.filter(Matiere.branch == branch)
        else:
            q = q.filter(Matiere.branch == "")
        return q.order_by(Matiere.id).all()


def list_branches_for_year(year_name: str) -> List[str]:
    """Return list of available branch names for a given secondary year."""
    seen = set()
    for bname, yname, _ in LYCEE_BRANCHES:
        if yname == year_name:
            seen.add(bname)
    return sorted(seen)


def list_all_matieres() -> List[Matiere]:
    with get_session() as session:
        return session.query(Matiere).order_by(Matiere.level_key, Matiere.year_name, Matiere.branch, Matiere.id).all()


def add_matiere(name: str, coefficient: float, level_key: str, year_name: str, branch: str = "") -> Matiere:
    with get_session() as session:
        m = Matiere(name=name, coefficient=coefficient,
                    level_key=level_key, year_name=year_name, branch=branch)
        session.add(m)
        session.commit()
        session.refresh(m)
        return m


def update_matiere(matiere_id: int, name: str, coefficient: float) -> Matiere:
    with get_session() as session:
        m = session.get(Matiere, matiere_id)
        if not m:
            raise ValueError("Matiere not found")
        m.name = name
        m.coefficient = coefficient
        session.commit()
        session.refresh(m)
        return m


def delete_matiere(matiere_id: int):
    with get_session() as session:
        m = session.get(Matiere, matiere_id)
        if m:
            session.delete(m)
            session.commit()


# ── Note CRUD ───────────────────────────────────────────────────────────

def get_notes(student_id: int, semester: int) -> Dict[int, float]:
    with get_session() as session:
        rows = session.query(Note).filter_by(
            student_id=student_id, semester=semester
        ).all()
        return {n.matiere_id: n.valeur for n in rows}


def save_notes(student_id: int, semester: int, notes: Dict[int, float]):
    with get_session() as session:
        for matiere_id, valeur in notes.items():
            existing = session.query(Note).filter_by(
                student_id=student_id, matiere_id=matiere_id, semester=semester
            ).first()
            if existing:
                existing.valeur = valeur
            else:
                session.add(Note(
                    student_id=student_id, matiere_id=matiere_id,
                    semester=semester, valeur=valeur
                ))
        session.commit()


# ── Calculation ─────────────────────────────────────────────────────────

def calc_semester_averages(student_id: int, semester: int, coeffs: Dict[int, float]) -> Tuple[Dict[int, float], float]:
    session_local = get_session()
    try:
        student = session_local.get(Student, student_id)
        if not student:
            return {}, 0.0
        level_key = student.classe.level_key
        year_name = student.classe.year_name
        branch = student.classe.branch or ""

        notes = session_local.query(Note).filter_by(
            student_id=student_id, semester=semester
        ).all()
        notes_map = {n.matiere_id: n.valeur for n in notes}

        q = session_local.query(Matiere).filter_by(
            level_key=level_key, year_name=year_name
        )
        if branch:
            q = q.filter(Matiere.branch == branch)
        else:
            q = q.filter(Matiere.branch == "")
        matieres = q.all()
    finally:
        session_local.close()

    subject_avgs: Dict[int, float] = {}
    weighted_sum = 0.0
    total_coef = 0.0

    for m in matieres:
        val = notes_map.get(m.id)
        if val is not None:
            subject_avgs[m.id] = val
            coef = coeffs.get(m.id, m.coefficient)
            weighted_sum += val * coef
            total_coef += coef

    overall = weighted_sum / total_coef if total_coef > 0 else 0.0
    return subject_avgs, overall


def calc_year_averages(student_id: int, coeffs: Dict[int, float]) -> Tuple[float, float, float]:
    _, s1 = calc_semester_averages(student_id, 1, coeffs)
    _, s2 = calc_semester_averages(student_id, 2, coeffs)
    year = (s1 + s2) / 2
    return s1, s2, year


def get_coeffs_map(level_key: str, year_name: str, branch: str = "") -> Dict[int, float]:
    with get_session() as session:
        q = session.query(Matiere).filter_by(
            level_key=level_key, year_name=year_name
        )
        if branch:
            q = q.filter(Matiere.branch == branch)
        else:
            q = q.filter(Matiere.branch == "")
        rows = q.all()
        return {m.id: m.coefficient for m in rows}
