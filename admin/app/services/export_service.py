import os
import zipfile
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from app.repositories.database import get_session, DATA_DIR, REPORTS_DIR
from app.models.student import Student
from app.models.classe import Classe

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
_jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


def _render_template(template_name, **kwargs):
    tmpl = _jinja_env.get_template(template_name)
    return tmpl.render(**kwargs)


def export_certificat_scolarite(class_id, student_id, **cfg_overrides):
    cfg = {"province": "", "ecole": "", "directeur": "", "ville": "", "telephone": ""}
    cfg.update(cfg_overrides)
    session = get_session()
    try:
        student = session.query(Student).filter_by(id=student_id).first()
        classe = session.query(Classe).filter_by(id=class_id).first()
        if not student or not classe:
            raise FileNotFoundError("Student or class not found")
        html = _render_template("certificat_de_scolarite.html",
            province=cfg["province"], ecole=cfg["ecole"],
            directeur=cfg["directeur"], ville=cfg["ville"],
            telephone=cfg["telephone"],
            student_name=student.full_name,
            code_massar=student.code_massar or "",
            birth_date=student.birth_date or "",
            class_name=classe.name,
            level_name=classe.level_name,
            academic_year=classe.academic_year or "",
            date=datetime.now().strftime("%d/%m/%Y"),
        )
        os.makedirs(REPORTS_DIR, exist_ok=True)
        path = os.path.join(REPORTS_DIR, f"Certificat_{student.full_name}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return path
    finally:
        session.close()


def export_liste_eleves(class_id, **cfg_overrides):
    cfg = {"ecole": ""}
    cfg.update(cfg_overrides)
    session = get_session()
    try:
        classe = session.query(Classe).filter_by(id=class_id).first()
        if not classe:
            raise FileNotFoundError("Class not found")
        students = session.query(Student).filter_by(class_id=class_id).order_by(Student.sort_order).all()
        html = _render_template("liste_eleves.html",
            class_name=classe.name, level_name=classe.level_name,
            year_name=classe.year_name, academic_year=classe.academic_year or "",
            ecole=cfg["ecole"], students=students,
            generation_date=datetime.now().strftime("%d/%m/%Y %H:%M"),
        )
        os.makedirs(REPORTS_DIR, exist_ok=True)
        path = os.path.join(REPORTS_DIR, f"Liste_{classe.name}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return path
    finally:
        session.close()


def export_class_html(class_id):
    return export_html(class_id)


def export_html(class_id):
    from app.repositories.database import get_session, DATA_ROOT, DATA_DIR
    session = get_session()
    try:
        classe = session.query(Classe).filter_by(id=class_id).first()
        if not classe:
            raise FileNotFoundError("Class not found")
        students = session.query(Student).filter_by(class_id=class_id).order_by(Student.sort_order).all()

        html = f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"><title>{classe.name} - {classe.level_name} Année {classe.year_name}</title>
<style>
body {{ font-family: 'Segoe UI', sans-serif; margin: 20px; color: #333; }}
h1 {{ color: #1f6aa5; border-bottom: 2px solid #1f6aa5; padding-bottom: 8px; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 15px; }}
th {{ background: #1f6aa5; color: white; padding: 10px; text-align: left; }}
td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
tr:hover {{ background: #f5f5f5; }}
</style>
</head><body>
<h1>{classe.name} - {classe.level_name} (Année {classe.year_name})</h1>
<p><strong>Total élèves :</strong> {len(students)}</p>
<table>
<tr><th>#</th><th>Nom complet</th><th>Code Massar</th><th>Date de naissance</th></tr>"""
        for i, s in enumerate(students, 1):
            html += f"<tr><td>{i}</td><td>{s.full_name}</td><td>{s.code_massar or ''}</td><td>{s.birth_date or ''}</td></tr>"
        html += "</table></body></html>"
        os.makedirs(REPORTS_DIR, exist_ok=True)
        out_path = os.path.join(REPORTS_DIR, f"{classe.name}_{classe.level_name}_{classe.year_name}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        return out_path
    finally:
        session.close()


def export_pdf(class_id):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
    except ImportError:
        raise RuntimeError("ReportLab is required. Install: pip install reportlab")

    session = get_session()
    try:
        classe = session.query(Classe).filter_by(id=class_id).first()
        if not classe:
            raise FileNotFoundError("Class not found")
        students = session.query(Student).filter_by(class_id=class_id).order_by(Student.sort_order).all()

        os.makedirs(REPORTS_DIR, exist_ok=True)
        out_path = os.path.join(REPORTS_DIR, f"{classe.name}_{classe.level_name}_{classe.year_name}.pdf")
        doc = SimpleDocTemplate(out_path, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []
        elements.append(Paragraph(f"{classe.name} - {classe.level_name} (Année {classe.year_name})", styles["Title"]))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"Total élèves: {len(students)}", styles["Normal"]))
        elements.append(Spacer(1, 12))
        data = [["#", "Nom complet", "Code Massar", "Date de naissance"]]
        for i, s in enumerate(students, 1):
            data.append([str(i), s.full_name, s.code_massar or "", s.birth_date or ""])
        table = Table(data, colWidths=[30, 200, 120, 120])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f6aa5")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 12),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ]))
        elements.append(table)
        doc.build(elements)
        return out_path
    finally:
        session.close()


def print_direct(class_id):
    import subprocess
    try:
        subprocess.run(["which", "lpr"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError("lpr not available. Install CUPS or use PDF export.")
    pdf_path = export_pdf(class_id)
    subprocess.run(["lpr", pdf_path], check=True)
    return pdf_path


def backup_all():
    zip_name = f"mainpixel_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    os.makedirs(REPORTS_DIR, exist_ok=True)
    zip_path = os.path.join(REPORTS_DIR, zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if os.path.exists(DATA_DIR):
            for root, dirs, files in os.walk(DATA_DIR):
                for f in files:
                    fp = os.path.join(root, f)
                    arcname = os.path.relpath(fp, os.path.dirname(DATA_DIR))
                    zf.write(fp, arcname)
    return zip_path
