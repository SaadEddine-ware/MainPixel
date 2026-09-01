import sys
import customtkinter as ctk
from tkinter import messagebox
from app.i18n.translator import _, anchor
from app.services.class_service import list_all_classes
from app.services.student_service import list_students_for_class
from app.services.grade_service import (
    list_matieres, get_notes, save_notes,
    get_coeffs_map, calc_semester_averages,
)
from app.repositories.database import get_cfg
from app.ui.theme import *


class GradesView:
    def __init__(self, master, app_ref):
        self.master = master
        self.app = app_ref
        self.frame = None
        self.cfg = get_cfg()
        self._current_class_id = None
        self._current_student_id = None
        self._semester = 1
        self._entries = {}
        self._avg_label = None

    def build(self):
        self.frame = ctk.CTkFrame(self.master, fg_color="transparent")
        self.frame.grid(row=0, column=0, sticky="nsew")
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(0, weight=1)
        self._show_class_list()

    def _clear(self):
        for w in self.frame.winfo_children():
            w.destroy()

    # ── Level 1: Class list ────────────────────────────────────────────

    def _show_class_list(self):
        self._clear()
        self._current_class_id = None
        self._current_student_id = None

        outer = ctk.CTkScrollableFrame(self.frame, fg_color="transparent", corner_radius=0)
        outer.pack(fill="both", expand=True)
        outer.grid_columnconfigure(0, weight=1)
        self._fix_scroll(outer)

        ctk.CTkLabel(
            outer, text=_("grades.select_class"),
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
                card, text=_("classes.open"), width=80,
                fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
                corner_radius=0, border_width=1, border_color=BTN_BORDER,
                command=lambda cid=cid: self._show_student_list(cid)
            ).pack(side="right", padx=5)

    # ── Level 2: Student list ──────────────────────────────────────────

    def _show_student_list(self, class_id):
        self._clear()
        self._current_class_id = class_id
        self._current_student_id = None

        outer = ctk.CTkScrollableFrame(self.frame, fg_color="transparent", corner_radius=0)
        outer.pack(fill="both", expand=True)
        outer.grid_columnconfigure(0, weight=1)
        self._fix_scroll(outer)

        from app.services.class_service import get_class_name
        class_name = get_class_name(class_id) or _("dialog.unknown")

        ctk.CTkButton(
            outer, text=f"\u2190 {_('grades.back_to_classes')}",
            command=self._show_class_list,
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(anchor=anchor("w"), pady=(0, 10))

        ctk.CTkLabel(
            outer, text=f"{_('grades.title')} — {class_name}",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_WHITE
        ).pack(anchor=anchor("w"), pady=(0, 15))

        students = list_students_for_class(class_id)
        if not students:
            ctk.CTkLabel(outer, text=_("students.no_students"), text_color=TEXT_LIGHT).pack(pady=20)
            return

        for s in students:
            card = ctk.CTkFrame(outer, fg_color=BG_INPUT, corner_radius=0,
                                border_width=1, border_color=BORDER_COLOR)
            card.pack(fill="x", pady=2)
            ctk.CTkLabel(
                card, text=s.full_name,
                font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_WHITE
            ).pack(side="left", padx=15, pady=8)
            if s.code_massar:
                ctk.CTkLabel(
                    card, text=f"[{s.code_massar}]",
                    font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_LIGHT
                ).pack(side="left")
            ctk.CTkButton(
                card, text=_("grades.enter"), width=80,
                fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
                corner_radius=0, border_width=1, border_color=BTN_BORDER,
                command=lambda sid=s.id: self._show_grade_entry(sid)
            ).pack(side="right", padx=5)

    # ── Level 3: Grade entry ───────────────────────────────────────────

    def _show_grade_entry(self, student_id):
        self._clear()
        self._current_student_id = student_id

        from app.services.class_service import get_class_name
        from app.repositories.database import get_session
        from app.models import Student

        with get_session() as session:
            student = session.get(Student, student_id)
            if not student:
                messagebox.showerror(_("dialog.error"), _("dialog.unknown"))
                self._show_student_list(self._current_class_id)
                return
            class_name = get_class_name(self._current_class_id) or ""
            level_key = student.classe.level_key
            year_name = student.classe.year_name
            branch = student.classe.branch or ""
            student_name = student.full_name

        matieres = list_matieres(level_key, year_name, branch=branch)
        self._current_branch = branch

        outer = ctk.CTkScrollableFrame(self.frame, fg_color="transparent", corner_radius=0)
        outer.pack(fill="both", expand=True)
        outer.grid_columnconfigure(0, weight=1)
        self._fix_scroll(outer)

        ctk.CTkButton(
            outer, text=f"\u2190 {_('grades.back_to_students')}",
            command=lambda: self._show_student_list(self._current_class_id),
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(anchor=anchor("w"))

        ctk.CTkLabel(
            outer, text=f"{student_name} — {class_name}",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_WHITE
        ).pack(anchor=anchor("w"), pady=10)

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

        self._semester = 1
        self._build_grade_grid(outer, matieres)

        ctk.CTkButton(
            outer, text=_("grades.save"),
            command=self._save_grades,
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(anchor=anchor("w"), pady=10)

        self._refresh_display()

    def _build_grade_grid(self, parent, matieres):
        self._entries = {}
        header = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=0,
                              border_width=1, border_color=BORDER_COLOR)
        header.pack(fill="x", pady=1)
        ctk.CTkLabel(
            header, text=_("subjects.header_name"),
            font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"), text_color=TEXT_WHITE,
            width=200
        ).pack(side="left", padx=10)
        ctk.CTkLabel(
            header, text=_("subjects.header_coef"),
            font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"), text_color=TEXT_WHITE,
            width=60
        ).pack(side="left")
        ctk.CTkLabel(
            header, text=_("grades.note"),
            font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"), text_color=TEXT_WHITE,
            width=80
        ).pack(side="left", padx=5)

        for m in matieres:
            row = ctk.CTkFrame(parent, fg_color=BG_INPUT, corner_radius=0,
                               border_width=1, border_color=BORDER_COLOR)
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(
                row, text=m.name,
                font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_WHITE,
                width=200, anchor="w"
            ).pack(side="left", padx=10, pady=4)
            ctk.CTkLabel(
                row, text=str(m.coefficient),
                font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_LIGHT,
                width=60, anchor="w"
            ).pack(side="left")
            entry = ctk.CTkEntry(row, width=80, corner_radius=0)
            entry.pack(side="left", padx=5, pady=4)
            self._entries[m.id] = entry

        self._avg_label = ctk.CTkLabel(
            parent, text="",
            font=(FONT_FAMILY, FONT_SIZE_LARGE, "bold"), text_color=TEXT_WHITE
        )
        self._avg_label.pack(anchor=anchor("w"), pady=10)

    def _switch_sem(self, sem):
        self._save_current_entries()
        self._semester = sem
        self._sem1_btn.configure(fg_color=BTN_BG if sem != 1 else "#cccccc")
        self._sem2_btn.configure(fg_color=BTN_BG if sem != 2 else "#cccccc")
        self._refresh_display()

    def _save_current_entries(self):
        if not self._current_student_id or not self._entries:
            return
        notes = {}
        for mid, entry in self._entries.items():
            val = entry.get().strip()
            if val:
                try:
                    v = float(val)
                    if 0 <= v <= 20:
                        notes[mid] = v
                except ValueError:
                    pass
        if notes:
            save_notes(self._current_student_id, self._semester, notes)

    def _refresh_display(self):
        if not self._current_student_id:
            return
        notes = get_notes(self._current_student_id, self._semester)
        for mid, entry in self._entries.items():
            entry.delete(0, "end")
            if mid in notes:
                entry.insert(0, str(notes[mid]))
        self._update_average()

    def _update_average(self):
        if not self._current_student_id or not self._entries:
            return
        from app.repositories.database import get_session
        from app.models import Student
        with get_session() as session:
            student = session.get(Student, self._current_student_id)
            if not student:
                return
            level_key = student.classe.level_key
            year_name = student.classe.year_name
            branch = student.classe.branch or ""

        matieres = list_matieres(level_key, year_name, branch=branch)
        coeffs = {m.id: m.coefficient for m in matieres}

        notes = get_notes(self._current_student_id, self._semester)
        total_weighted = 0.0
        total_coef = 0.0
        for m in matieres:
            val = notes.get(m.id)
            if val is not None:
                total_weighted += val * m.coefficient
                total_coef += m.coefficient

        avg = total_weighted / total_coef if total_coef > 0 else 0.0
        self._avg_label.configure(
            text=f"{_('grades.average')}: {avg:.2f} / 20"
        )

    def _save_grades(self):
        self._save_current_entries()
        self._update_average()
        messagebox.showinfo(_("dialog.success"), _("dialog.saved"))

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

    def destroy(self):
        if self.frame:
            self.frame.destroy()
