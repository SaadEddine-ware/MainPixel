import os
import json
import csv
from datetime import datetime
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

DATA_DIR = os.path.expanduser("~/.mainpixel")
DB_PATH = os.path.join(DATA_DIR, "mainpixel.db")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
DATA_ROOT = os.path.join(DATA_DIR, "data")
REPORTS_DIR = os.path.join(DATA_DIR, "reports")

engine = None
SessionLocal = None
Base = declarative_base()


def init_db():
    global engine, SessionLocal
    os.makedirs(DATA_DIR, exist_ok=True)

    engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SessionLocal = sessionmaker(bind=engine)
    import app.models  # ensure all models registered
    Base.metadata.create_all(engine)
    _migrate_db()
    return engine


def _migrate_db():
    with engine.connect() as conn:
        cursor = conn.connection.cursor()
        for table, col, col_def in [
            ("classes", "branch", "VARCHAR(100) DEFAULT ''"),
            ("matieres", "branch", "VARCHAR(100) DEFAULT ''"),
            ("students", "comment", "VARCHAR(500) DEFAULT ''"),
        ]:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
            except Exception:
                pass
        # Rename old "secondary" level_key to "lycee" in existing rows
        for table in ("classes", "matieres"):
            try:
                cursor.execute(
                    f"UPDATE {table} SET level_key = 'lycee' WHERE level_key = 'secondary'"
                )
            except Exception:
                pass
        conn.connection.commit()


def get_session():
    if SessionLocal is None:
        init_db()
    return SessionLocal()


def get_cfg():
    if not os.path.exists(CONFIG_FILE):
        return _create_default_config()
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    # Migrate old "secondary" key → "lycee"
    changed = False
    if "secondary" in cfg.get("levels", {}):
        cfg["levels"]["lycee"] = cfg["levels"].pop("secondary")
        changed = True
    if "secondary" in cfg.get("years_structure", {}):
        cfg["years_structure"]["lycee"] = cfg["years_structure"].pop("secondary")
        changed = True
    if "baccalaureate" in cfg.get("years_structure", {}).get("lycee", []):
        cfg["years_structure"]["lycee"] = [
            y for y in cfg["years_structure"]["lycee"] if y != "baccalaureate"
        ]
        changed = True
    if changed:
        save_cfg(cfg)
    return cfg


def _create_default_config():
    cfg = {
        "is_initialized": True,
        "created_at": datetime.now().isoformat(),
        "levels": {
            "primary": "Primaire",
            "middle": "Collège",
            "lycee": "Lycée",
        },
        "years_structure": {
            "primary": ["1", "2", "3", "4", "5", "6"],
            "middle": ["1", "2", "3"],
            "lycee": ["1", "2", "3"],
        },
    }
    save_cfg(cfg)
    return cfg


def save_cfg(cfg):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def is_initialized():
    cfg = get_cfg()
    return cfg is not None and cfg.get("is_initialized", False)


def ensure_data_dirs():
    cfg = get_cfg()
    level_keys = ["primary", "middle", "lycee"]
    for lk in level_keys:
        level_name = cfg["levels"].get(lk, lk.capitalize())
        years = cfg["years_structure"].get(lk, ["1"])
        for y in years:
            os.makedirs(os.path.join(DATA_ROOT, level_name, y), exist_ok=True)


def migrate_csv_to_sqlite(session):
    from app.models.classe import Classe
    from app.models.student import Student

    cfg = get_cfg()
    level_keys = ["primary", "middle", "lycee"]
    migrated = 0

    existing = session.query(Classe).count()
    if existing > 0:
        return 0

    for lk in level_keys:
        level_name = cfg["levels"].get(lk, lk.capitalize())
        years = cfg["years_structure"].get(lk, ["1"])
        for y in years:
            year_dir = os.path.join(DATA_ROOT, level_name, y)
            if not os.path.isdir(year_dir):
                continue
            for fname in sorted(os.listdir(year_dir)):
                if not fname.endswith(".csv"):
                    continue
                class_name = fname[:-4]
                csv_path = os.path.join(year_dir, fname)
                students_data = _read_csv_file(csv_path)
                if students_data is None:
                    continue
                classe = Classe(
                    level_key=lk,
                    level_name=level_name,
                    year_name=y,
                    name=class_name,
                    academic_year="",
                    created_at=datetime.now(),
                )
                session.add(classe)
                session.flush()
                for i, s in enumerate(students_data):
                    student = Student(
                        class_id=classe.id,
                        code_massar=s.get("code_massar", ""),
                        full_name=s.get("name", ""),
                        birth_date=s.get("birth", ""),
                        notes=s.get("notes", ""),
                        sort_order=i,
                        created_at=datetime.now(),
                    )
                    session.add(student)
                    migrated += 1
    session.commit()
    return migrated


def _read_csv_file(path):
    if not os.path.exists(path):
        return None
    students = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return []
        is_standard = header == ["Nom complet", "Numero scolaire", "Date de naissance", "Notes"]
        is_legacy = (not is_standard and len(header) == 5
                     and header[0] == "#"
                     and header[1:] == ["Nom complet", "Numero scolaire", "Date de naissance", "Notes"])
        for row in reader:
            if not row or all(c.strip() == "" for c in row):
                continue
            if is_standard:
                students.append({
                    "name": row[0].strip() if len(row) > 0 else "",
                    "code_massar": row[1].strip() if len(row) > 1 else "",
                    "birth": row[2].strip() if len(row) > 2 else "",
                    "notes": row[3].strip() if len(row) > 3 else "",
                })
            elif is_legacy:
                students.append({
                    "name": row[1].strip() if len(row) > 1 else "",
                    "code_massar": row[2].strip() if len(row) > 2 else "",
                    "birth": row[3].strip() if len(row) > 3 else "",
                    "notes": row[4].strip() if len(row) > 4 else "",
                })
            else:
                students.append({
                    "name": row[0].strip() if len(row) > 0 else "",
                    "code_massar": row[1].strip() if len(row) > 1 else "",
                    "birth": row[2].strip() if len(row) > 2 else "",
                    "notes": row[3].strip() if len(row) > 3 else "",
                })
    return students
