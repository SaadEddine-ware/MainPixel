from app.repositories.database import get_session, get_cfg
from app.models.classe import Classe
from app.models.student import Student


def get_statistics():
    cfg = get_cfg()
    session = get_session()
    try:
        stats = {}
        total_classes = 0
        total_students = 0
        level_data = {}

        for lk in ["primary", "middle", "lycee"]:
            level_name = cfg["levels"].get(lk, lk.capitalize())
            years = cfg["years_structure"].get(lk, [])
            year_data = {}
            lc = 0
            ls = 0
            for y in years:
                classes = session.query(Classe).filter_by(
                    level_key=lk, year_name=y
                ).order_by(Classe.name).all()
                cls_list = [(c.id, c.name, c.student_count) for c in classes]
                year_data[y] = cls_list
                lc += len(classes)
                ls += sum(c.student_count for c in classes)
            level_data[level_name] = {"classes": lc, "students": ls, "years": year_data}
            total_classes += lc
            total_students += ls

        stats["level_data"] = level_data
        stats["total_levels"] = 3
        stats["total_classes"] = total_classes
        stats["total_students"] = total_students
        return stats
    finally:
        session.close()
