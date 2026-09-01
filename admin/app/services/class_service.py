from sqlalchemy import or_
from app.repositories.database import get_session, get_cfg, save_cfg
from app.models.classe import Classe
from app.models.audit_log import AuditLog
from datetime import datetime


def list_levels():
    cfg = get_cfg()
    levels = cfg.get("levels", {})
    if not levels:
        return []
    if isinstance(levels, dict):
        return [(k, levels[k]) for k in ["primary", "middle", "lycee"] if k in levels]
    return levels


def get_class_name(class_id):
    session = get_session()
    try:
        c = session.query(Classe).filter_by(id=class_id).first()
        return c.name if c else None
    finally:
        session.close()


def list_all_classes():
    session = get_session()
    try:
        classes = session.query(Classe).order_by(Classe.level_name, Classe.year_name, Classe.name).all()
        return [(c.id, c.level_name, c.year_name, c.name, c.student_count, c.branch or "") for c in classes]
    finally:
        session.close()


def list_years_for_level(level_key):
    cfg = get_cfg()
    return cfg["years_structure"].get(level_key, [])


def get_class(class_id):
    session = get_session()
    try:
        return session.query(Classe).filter_by(id=class_id).first()
    finally:
        session.close()


def get_class_by_path(level_key, year, class_name, branch=""):
    session = get_session()
    try:
        return session.query(Classe).filter_by(
            level_key=level_key, year_name=year, name=class_name, branch=branch
        ).first()
    finally:
        session.close()


def class_exists(level_key, year, class_name, branch=""):
    session = get_session()
    try:
        return session.query(Classe).filter_by(
            level_key=level_key, year_name=year, name=class_name, branch=branch
        ).count() > 0
    finally:
        session.close()


def create_class(level_key, year, class_name, branch=""):
    cfg = get_cfg()
    level_name = cfg["levels"].get(level_key, level_key)
    session = get_session()
    try:
        existing = session.query(Classe).filter_by(
            level_key=level_key, year_name=year, name=class_name, branch=branch
        ).count()
        if existing > 0:
            raise FileExistsError(f"Class '{class_name}' already exists in {year}")
        classe = Classe(
            level_key=level_key,
            level_name=level_name,
            year_name=year,
            name=class_name,
            branch=branch,
            created_at=datetime.now(),
        )
        session.add(classe)
        session.flush()
        class_id = classe.id
        details = f"Created class {class_name} in {level_name}/{year}"
        if branch:
            details += f" ({branch})"
        session.add(AuditLog(action="create", entity_type="class", entity_id=class_id,
                             details=details))
        session.commit()
        return class_id
    finally:
        session.close()


def delete_class(class_id):
    session = get_session()
    try:
        classe = session.query(Classe).filter_by(id=class_id).first()
        if not classe:
            raise FileNotFoundError("Class not found")
        name = classe.name
        session.delete(classe)
        session.commit()
        session.add(AuditLog(action="delete", entity_type="class", entity_id=class_id,
                             details=f"Deleted class {name}"))
        session.commit()
    finally:
        session.close()


def rename_class(class_id, new_name):
    session = get_session()
    try:
        classe = session.query(Classe).filter_by(id=class_id).first()
        if not classe:
            raise FileNotFoundError("Class not found")
        old_name = classe.name
        clash = session.query(Classe).filter_by(
            level_key=classe.level_key, year_name=classe.year_name, name=new_name
        ).count()
        if clash > 0:
            raise FileExistsError(f"Class '{new_name}' already exists")
        classe.name = new_name
        classe.updated_at = datetime.now()
        session.commit()
        session.add(AuditLog(action="rename", entity_type="class", entity_id=class_id,
                             details=f"Renamed class {old_name} -> {new_name}"))
        session.commit()
    finally:
        session.close()


def list_classes(level_key, year):
    session = get_session()
    try:
        classes = session.query(Classe).filter_by(
            level_key=level_key, year_name=year
        ).order_by(Classe.name).all()
        return [(c.id, c.name, c.student_count, c.branch or "") for c in classes]
    finally:
        session.close()


def search_classes(query):
    session = get_session()
    try:
        q = f"%{query}%"
        classes = session.query(Classe).filter(
            Classe.name.ilike(q)
        ).order_by(Classe.level_name, Classe.year_name, Classe.name).all()
        return [(c.id, c.level_key, c.level_name, c.year_name, c.name, c.student_count, c.branch or "")
                for c in classes]
    finally:
        session.close()
