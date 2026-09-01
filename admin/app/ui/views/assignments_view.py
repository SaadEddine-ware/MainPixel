import sys, json, os
import customtkinter as ctk
from tkinter import messagebox, simpledialog
from app.i18n.translator import _, anchor
from app.services.class_service import list_all_classes, list_classes, get_class_name
from app.services.student_service import list_students_for_class
from app.services.grade_service import list_matieres, get_coeffs_map
from app.services.assignment_service import (
    list_assignments, add_assignment, delete_assignment, rename_assignment,
    get_assignment_grades, save_assignment_grades, calc_all_moyennes,
    sync_moyennes_to_notes, export_assignments_json, import_assignments_json,
)
from app.repositories.database import get_cfg, REPORTS_DIR
from app.ui.theme import *


class AssignmentsView:
    def __init__(self, master, app_ref):
        self.master = master
        self.app = app_ref
        self.frame = None
        self.cfg = get_cfg()

        self._class_id = None
        self._matiere_id = None
        self._semester = 1
        self._assignments = []
        self._students = []
        self._entry_widgets = {}
        self._avg_labels = {}
        self._sheet = None

    def destroy(self):
        if self.frame:
            self.frame.destroy()

    # ── Entry point ────────────────────────────────────────────────────

    def build(self):
        self.frame = ctk.CTkFrame(self.master, fg_color="transparent")
        self.frame.grid(row=0, column=0, sticky="nsew")
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(0, weight=1)
        self._show_class_list()

    def _clear(self):
        for w in self.frame.winfo_children():
            w.destroy()

    # ── Level 1: Select class ──────────────────────────────────────────

    def _show_class_list(self):
        self._clear()
        self._class_id = None
        self._matiere_id = None
        self._assignments = []
        self._students = []

        outer = ctk.CTkScrollableFrame(self.frame, fg_color="transparent", corner_radius=0)
        outer.pack(fill="both", expand=True)
        outer.grid_columnconfigure(0, weight=1)
        self._fix_scroll(outer)

        ctk.CTkLabel(
            outer, text=_("assignments.select_class"),
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_WHITE
        ).pack(anchor=anchor("w"), pady=(0, 15))

        current_level = None
        for cid, level_name, year, class_name, count, br in list_all_classes():
            if current_level != level_name:
                if current_level is not None:
                    ctk.CTkFrame(outer, height=1, fg_color=BORDER_COLOR).pack(fill="x", pady=5)
                current_level = level_name
                ctk.CTkLabel(
                    outer, text=level_name,
                    font=(FONT_FAMILY, FONT_SIZE_LARGE, "bold"), text_color=TEXT_WHITE
                ).pack(anchor=anchor("w"), pady=(5, 2))

            label_text = f"{class_name} — {_('year')} {year} ({count} {_('student') if count == 1 else _('students_plural')})"
            if br:
                label_text += f" [{br}]"
            card = ctk.CTkFrame(outer, fg_color=BG_INPUT, corner_radius=0,
                                border_width=1, border_color=BORDER_COLOR)
            card.pack(fill="x", pady=2)
            ctk.CTkLabel(
                card, text=label_text,
                font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_WHITE
            ).pack(side="left", padx=15, pady=8)
            ctk.CTkButton(
                card, text=_("assignments.select"), width=80,
                fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
                corner_radius=0, border_width=1, border_color=BTN_BORDER,
                command=lambda cid=cid: self._show_matiere_list(cid)
            ).pack(side="right", padx=5)

    # ── Level 2: Select subject ────────────────────────────────────────

    def _show_matiere_list(self, class_id):
        self._clear()
        self._class_id = class_id
        self._matiere_id = None
        self._assignments = []

        from app.repositories.database import get_session
        from app.models.classe import Classe
        with get_session() as session:
            cls = session.get(Classe, class_id)
            level_key = cls.level_key if cls else "primary"
            year_name = cls.year_name if cls else "1"
            branch = cls.branch or ""

        matieres = list_matieres(level_key, year_name, branch=branch)
        class_name = get_class_name(class_id) or ""

        outer = ctk.CTkScrollableFrame(self.frame, fg_color="transparent", corner_radius=0)
        outer.pack(fill="both", expand=True)
        outer.grid_columnconfigure(0, weight=1)
        self._fix_scroll(outer)

        ctk.CTkButton(
            outer, text=f"\u2190 {_('assignments.back_to_classes')}",
            command=self._show_class_list,
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(anchor=anchor("w"), pady=(0, 5))

        ctk.CTkLabel(
            outer, text=f"{class_name} — {_('assignments.select_subject')}",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_WHITE
        ).pack(anchor=anchor("w"), pady=(0, 15))

        for m in matieres:
            card = ctk.CTkFrame(outer, fg_color=BG_INPUT, corner_radius=0,
                                border_width=1, border_color=BORDER_COLOR)
            card.pack(fill="x", pady=2)
            ctk.CTkLabel(
                card, text=f"{m.name} (coef {m.coefficient})",
                font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_WHITE
            ).pack(side="left", padx=15, pady=8)
            ctk.CTkButton(
                card, text=_("assignments.open"), width=80,
                fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
                corner_radius=0, border_width=1, border_color=BTN_BORDER,
                command=lambda mid=m.id: self._show_grade_grid(class_id, mid)
            ).pack(side="right", padx=5)

    # ── Level 3: Grade grid ────────────────────────────────────────────

    def _show_grade_grid(self, class_id, matiere_id):
        self._clear()
        self._class_id = class_id
        self._matiere_id = matiere_id

        from app.repositories.database import get_session
        from app.models.matiere import Matiere
        with get_session() as session:
            matiere = session.get(Matiere, matiere_id)
            matiere_name = matiere.name if matiere else ""

        self._students = list_students_for_class(class_id)
        class_name = get_class_name(class_id) or ""

        outer = ctk.CTkScrollableFrame(self.frame, fg_color="transparent", corner_radius=0)
        outer.pack(fill="both", expand=True)
        outer.grid_columnconfigure(0, weight=1)
        self._fix_scroll(outer)

        # Back button
        ctk.CTkButton(
            outer, text=f"\u2190 {_('assignments.back_to_subjects')}",
            command=lambda: self._show_matiere_list(class_id),
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(anchor=anchor("w"), pady=(0, 5))

        # Title
        ctk.CTkLabel(
            outer, text=f"{matiere_name} — {class_name}",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_WHITE
        ).pack(anchor=anchor("w"), pady=(0, 5))

        # Semester tabs
        sem_row = ctk.CTkFrame(outer, fg_color="transparent")
        sem_row.pack(fill="x", pady=5)
        self._sem1_btn = ctk.CTkButton(
            sem_row, text=_("grades.sem1"),
            command=lambda: self._switch_sem(1),
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER, width=100,
        )
        self._sem1_btn.pack(side="left", padx=5)
        self._sem2_btn = ctk.CTkButton(
            sem_row, text=_("grades.sem2"),
            command=lambda: self._switch_sem(2),
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER, width=100,
        )
        self._sem2_btn.pack(side="left", padx=5)

        # Toolbar
        toolbar = ctk.CTkFrame(outer, fg_color="transparent")
        toolbar.pack(fill="x", pady=5)

        ctk.CTkButton(
            toolbar, text=_("assignments.add_assignment"),
            command=self._add_assignment_dialog,
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            toolbar, text=_("assignments.export"),
            command=self._export_json,
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            toolbar, text=_("assignments.import_btn"),
            command=self._import_json,
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            toolbar, text=_("assignments.sync"),
            command=self._sync_notes,
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            toolbar, text=_("assignments.network_fetch"),
            command=self._network_fetch,
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(side="left", padx=2)

        # Grade grid
        self._grid_outer = ctk.CTkFrame(outer, fg_color="transparent")
        self._grid_outer.pack(fill="x", pady=10)

        self._semester = 1
        self._build_grid()

    def _build_grid(self):
        for w in self._grid_outer.winfo_children():
            w.destroy()

        self._assignments = list_assignments(
            self._class_id, self._matiere_id, self._semester
        )

        if not self._students:
            ctk.CTkLabel(
                self._grid_outer, text=_("students.no_students"),
                text_color=TEXT_LIGHT, font=(FONT_FAMILY, FONT_SIZE_NORMAL)
            ).pack(pady=20)
            return

        # Build header
        header = ctk.CTkFrame(self._grid_outer, fg_color=BG_CARD, corner_radius=0,
                              border_width=1, border_color=BORDER_COLOR)
        header.pack(fill="x", pady=1)

        ctk.CTkLabel(
            header, text=_("assignments.student_header"),
            font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"), text_color=TEXT_WHITE,
            width=200, anchor="w"
        ).pack(side="left", padx=10)

        for a in self._assignments:
            col_frame = ctk.CTkFrame(header, fg_color="transparent", width=130)
            col_frame.pack(side="left", padx=2)
            col_frame.pack_propagate(False)
            ctk.CTkLabel(
                col_frame, text=a.title,
                font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"), text_color=TEXT_WHITE,
                anchor="center"
            ).pack()
            ctk.CTkLabel(
                col_frame, text=f"(x{a.coefficient})",
                font=(FONT_FAMILY, 10), text_color=TEXT_LIGHT,
                anchor="center"
            ).pack()

            # Delete assignment button
            ctk.CTkButton(
                col_frame, text="×", width=20,
                command=lambda aid=a.id: self._delete_assignment_confirm(aid),
                fg_color=DANGER, hover_color="#cccccc", text_color=TEXT_WHITE,
                corner_radius=0, border_width=0,
                font=(FONT_FAMILY, 10),
            ).pack(anchor="e")

        ctk.CTkLabel(
            header, text=_("assignments.avg_header"),
            font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"), text_color=TEXT_WHITE,
            width=80, anchor="center"
        ).pack(side="left", padx=5)

        # Load existing grades
        grades_per_assignment = {}
        for a in self._assignments:
            grades_per_assignment[a.id] = get_assignment_grades(a.id)

        # Build data rows
        self._entry_widgets = {}
        self._avg_labels = {}

        for s in self._students:
            row = ctk.CTkFrame(self._grid_outer, fg_color=BG_INPUT, corner_radius=0,
                               border_width=1, border_color=BORDER_COLOR)
            row.pack(fill="x", pady=1)

            ctk.CTkLabel(
                row, text=s.full_name,
                font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_WHITE,
                width=200, anchor="w"
            ).pack(side="left", padx=10, pady=4)

            sid = s.id
            self._entry_widgets[sid] = {}
            for a in self._assignments:
                entry = ctk.CTkEntry(row, width=60, corner_radius=0)
                entry.pack(side="left", padx=2, pady=2)
                val = grades_per_assignment.get(a.id, {}).get(sid)
                if val is not None:
                    entry.insert(0, str(val))
                entry.bind("<KeyRelease>", lambda e, sid=sid: self._update_row_avg(sid))
                entry.bind("<FocusOut>", lambda e, sid=sid: self._save_row(sid))
                self._entry_widgets[sid][a.id] = entry

            avg_label = ctk.CTkLabel(
                row, text="0.00",
                font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_WHITE,
                width=80, anchor="center"
            )
            avg_label.pack(side="left", padx=5)
            self._avg_labels[sid] = avg_label

        # Update averages
        self._refresh_averages()

    def _update_row_avg(self, student_id):
        s = sum(0.0)
        c = 0.0
        for a in self._assignments:
            entry = self._entry_widgets.get(student_id, {}).get(a.id)
            if not entry:
                continue
            val_str = entry.get().strip()
            if val_str:
                try:
                    v = float(val_str)
                    s += v * a.coefficient
                    c += a.coefficient
                except ValueError:
                    pass
        avg = s / c if c > 0 else 0.0
        lbl = self._avg_labels.get(student_id)
        if lbl:
            lbl.configure(text=f"{avg:.2f}")

    def _save_row(self, student_id):
        grades = {}
        for a in self._assignments:
            entry = self._entry_widgets.get(student_id, {}).get(a.id)
            if entry:
                val_str = entry.get().strip()
                if val_str:
                    try:
                        v = float(val_str)
                        if 0 <= v <= 20:
                            grades[a.id] = v
                    except ValueError:
                        pass
        if grades:
            for aid, v in grades.items():
                save_assignment_grades(aid, {student_id: v})

    def _refresh_averages(self):
        for s in self._students:
            self._update_row_avg(s.id)

    def _switch_sem(self, sem):
        self._save_all()
        self._semester = sem
        self._sem1_btn.configure(fg_color=BTN_BG if sem != 1 else "#cccccc")
        self._sem2_btn.configure(fg_color=BTN_BG if sem != 2 else "#cccccc")
        self._build_grid()

    def _save_all(self):
        for s in self._students:
            self._save_row(s.id)

    # ── Assignment management ──────────────────────────────────────────

    def _add_assignment_dialog(self):
        title = simpledialog.askstring(
            _("assignments.add_assignment"),
            _("assignments.assignment_title_prompt"),
        )
        if not title or not title.strip():
            return
        add_assignment(
            self._class_id, self._matiere_id, self._semester,
            title.strip(), coefficient=1.0,
        )
        self._build_grid()

    def _delete_assignment_confirm(self, assignment_id):
        a = next((a for a in self._assignments if a.id == assignment_id), None)
        name = a.title if a else ""
        if messagebox.askyesno(
            _("dialog.confirm"),
            _("assignments.delete_confirm", name=name)
        ):
            delete_assignment(assignment_id)
            self._build_grid()

    # ── Export / Import ────────────────────────────────────────────────

    def _export_json(self):
        if not self._assignments:
            messagebox.showinfo(_("dialog.info"), _("assignments.no_assignments"))
            return
        data = export_assignments_json(self._class_id, self._matiere_id, self._semester)
        os.makedirs(REPORTS_DIR, exist_ok=True)
        path = os.path.join(REPORTS_DIR, f"assignments_s{self._semester}_m{self._matiere_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        messagebox.showinfo(_("dialog.success"), _("assignments.exported", path=path))

    def _import_json(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title=_("assignments.import_btn"),
            filetypes=[("JSON", "*.json")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            a_count, g_count = import_assignments_json(data)
            self._build_grid()
            messagebox.showinfo(
                _("dialog.success"),
                _("assignments.imported", assignments=a_count, grades=g_count)
            )
        except Exception as e:
            messagebox.showerror(_("dialog.error"), str(e))

    def _sync_notes(self):
        self._save_all()
        self._refresh_averages()
        try:
            sync_moyennes_to_notes(self._class_id, self._matiere_id, self._semester)
            messagebox.showinfo(_("dialog.success"), _("assignments.synced"))
        except Exception as e:
            messagebox.showerror(_("dialog.error"), str(e))

    # ── Network fetch ──────────────────────────────────────────────────

    def _network_fetch(self):
        self.app.show_view("network")

    # ── Scroll fix ─────────────────────────────────────────────────────

    def _fix_scroll(self, frame):
        if sys.platform.startswith("linux"):
            try:
                canvas = frame._parent_canvas
            except AttributeError:
                return
            def cb(event, d=1):
                canvas.yview_scroll(-3 * d, "units")
            for widget in (frame, canvas):
                widget.bind("<Button-4>", lambda e: cb(e, 1), add="+")
                widget.bind("<Button-5>", lambda e: cb(e, -1), add="+")
