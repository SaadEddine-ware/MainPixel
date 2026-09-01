import sys
import customtkinter as ctk
from tkinter import messagebox, filedialog
from tksheet import Sheet
from app.i18n.translator import _, anchor
from app.services.student_service import (
    list_students_for_class, add_student, delete_student,
    update_student, search_students, import_csv_to_class,
)
from app.repositories.database import get_session
from app.models import Student
from app.ui.theme import *

_MIN_ROWS = 30


class StudentsView:
    def __init__(self, master, app_ref):
        self.master = master
        self.app = app_ref
        self.frame = None
        self.class_id = None
        self.class_name = ""
        self._sheet = None
        self._student_ids = []
        self._is_loading = False

    def build(self):
        self.frame = ctk.CTkFrame(self.master, fg_color="transparent")
        self.frame.grid(row=0, column=0, sticky="nsew")
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(2, weight=1)

        if not self.class_id:
            ctk.CTkLabel(
                self.frame, text=_("students.open_class_first"),
                font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_LIGHT
            ).pack(pady=20)
            return

        top = ctk.CTkFrame(self.frame, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            top, text=f"{_('students.title')} — {self.class_name}",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_WHITE
        ).pack(side="left", pady=(0, 15))
        ctk.CTkButton(
            top, text=f"\u2190 {_('students.back_to_classes')}",
            command=lambda: self.app.show_view("classes"),
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(side="right")

        self._build_toolbar()
        self._build_sheet()
        self._build_statusbar()
        self._load_data()

    def _build_toolbar(self):
        row = ctk.CTkFrame(self.frame, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew", pady=5)

        ctk.CTkButton(
            row, text=_("students.import_csv"),
            command=self._import_csv_dialog,
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(side="left", padx=5)

        self._search_entry = ctk.CTkEntry(
            row, placeholder_text=_("students.search_placeholder"), width=250
        )
        self._search_entry.pack(side="left", padx=5)

        def do_search():
            self._search(query=self._search_entry.get().strip())

        self._search_entry.bind("<Return>", lambda e: do_search())
        ctk.CTkButton(
            row, text=_("classes.search"),
            command=do_search,
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            row, text=_("students.reset"),
            command=self._reset_table,
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            row, text=_("classes.delete"),
            command=self._delete_selected,
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(side="right", padx=2)

    def _build_sheet(self):
        container = ctk.CTkFrame(
            self.frame, fg_color="transparent",
            corner_radius=0, border_width=1, border_color=BORDER_COLOR,
        )
        container.grid(row=2, column=0, sticky="nsew", pady=(5, 0))
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

        self._sheet = Sheet(
            container,
            headers=[
                _("student.name"),
                _("student.code_massar"),
                _("student.birth"),
                _("student.notes"),
            ],
            height=760,
            show_row_index=True,
            theme="light",
            total_rows=_MIN_ROWS,
            header_bg=BG_CARD,
            header_fg=TEXT_WHITE,
            header_font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
            font=(FONT_FAMILY, FONT_SIZE_SMALL, "normal"),
            row_height=28,
            align="w",
        )
        self._sheet.grid(row=0, column=0, sticky="nsew")

        self._sheet.MT.single_selection_enabled = True

        self._sheet.enable_bindings(
            "edit_cell",
            "single_select",
            "arrowkeys",
            "copy",
            "paste",
            "row_select",
        )

        self._sheet.MT.extra_b1_press_func = lambda e: self._sheet.after(50, self._open_editor)

        self._sheet.extra_bindings("edit_cell", self._on_cell_edited)
        self._sheet.bind("<<SheetSelect>>", self._on_selection)

    def _build_statusbar(self):
        self._status_bar = ctk.CTkFrame(self.frame, fg_color=BG_CARD, corner_radius=0, border_width=1, border_color=BORDER_COLOR)
        self._status_bar.grid(row=3, column=0, sticky="ew", pady=(2, 0))
        self._status_bar.grid_columnconfigure(0, weight=1)

        self._status_label = ctk.CTkLabel(
            self._status_bar, text=_("students.ready"),
            font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_WHITE,
        )
        self._status_label.grid(row=0, column=0, padx=10, pady=4, sticky="w")

        self._add_row_btn = ctk.CTkButton(
            self._status_bar, text="+", width=28, height=22,
            command=self._add_row,
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        )
        self._add_row_btn.grid(row=0, column=1, padx=(0, 10), pady=2)

    def _open_editor(self):
        self._sheet.focus_set()
        self._sheet.open_cell()

    def _on_selection(self, event=None):
        try:
            sel = self._sheet.get_currently_selected()
            if not sel:
                self._update_status("", "")
                return
            r, c = sel.row, sel.column
            data = self._sheet.get_sheet_data()
            if r < len(data) and c < len(data[r]):
                val = data[r][c]
                cols = [
                    _("student.name"),
                    _("student.code_massar"),
                    _("student.birth"),
                    _("student.notes"),
                ]
                col_name = cols[c] if c < len(cols) else f"Col {c}"
                self._update_status(f"Ligne {r+1}, {col_name}", val)
        except Exception:
            pass

    def _update_status(self, cell_ref, value):
        if value:
            self._status_label.configure(text=f"{cell_ref} : {value}")
        elif cell_ref:
            self._status_label.configure(text=cell_ref)
        else:
            self._status_label.configure(text=_("students.ready"))

    def _load_data(self, students=None):
        self._is_loading = True
        if students is None:
            students = list_students_for_class(self.class_id)
        data = []
        self._student_ids = []
        for s in students:
            data.append([
                s.full_name,
                s.code_massar or "",
                s.birth_date or "",
                s.comment or "",
            ])
            self._student_ids.append(s.id)
        target = max(len(data) + 1, _MIN_ROWS)
        while len(data) < target:
            data.append(["", "", "", ""])
            self._student_ids.append(None)
        self._sheet.set_sheet_data(data)
        self._sheet.set_column_widths([250, 150, 120, 200])
        self._is_loading = False
        self._update_status("", "")

    def _search(self, query):
        if not query:
            self._reset_table()
            return
        results = search_students(self.class_id, query)
        self._load_data(results)

    def _reset_table(self):
        self._search_entry.delete(0, "end")
        self._load_data()

    def _on_cell_edited(self, event):
        if self._is_loading:
            return
        r = event.get("row")
        c = event.get("column")
        if r is None or c is None:
            return

        data = self._sheet.get_sheet_data()
        if r >= len(data):
            return

        while len(self._student_ids) < len(data):
            self._student_ids.append(None)

        sid = self._student_ids[r] if r < len(self._student_ids) else None
        row = data[r]
        name = row[0].strip() if len(row) > 0 else ""

        if sid is None:
            if name:
                try:
                    new_id = add_student(
                        self.class_id,
                        name,
                        row[1] if len(row) > 1 else "",
                        row[2] if len(row) > 2 else "",
                        row[3] if len(row) > 3 else "",
                    )
                    self._student_ids[r] = new_id
                except ValueError as e:
                    messagebox.showerror(_("dialog.error"), str(e))
        else:
            if name:
                try:
                    update_student(
                        sid,
                        full_name=name,
                        code_massar=row[1] if len(row) > 1 else "",
                        birth_date=row[2] if len(row) > 2 else "",
                        notes=row[3] if len(row) > 3 else "",
                    )
                except ValueError as e:
                    messagebox.showerror(_("dialog.error"), str(e))
        cols = [_("student.name"), _("student.code_massar"), _("student.birth"), _("student.notes")]
        col_name = cols[c] if c < len(cols) else f"Col {c}"
        self._update_status(f"Ligne {r+1}, {col_name}", data[r][c] if c < len(data[r]) else "")

    def _add_row(self):
        self._is_loading = True
        data = self._sheet.get_sheet_data()
        data.append(["", "", "", ""])
        self._student_ids.append(None)
        self._sheet.set_sheet_data(data)
        self._is_loading = False

    def _delete_selected(self):
        sel = self._sheet.get_selected_rows()
        if not sel:
            messagebox.showinfo(_("dialog.info"), _("students.select_first"))
            return
        r = next(iter(sel))
        if r >= len(self._student_ids) or self._student_ids[r] is None:
            return
        sid = self._student_ids[r]
        with get_session() as session:
            student = session.get(Student, sid)
            name = student.full_name if student else _("dialog.unknown")
        if messagebox.askyesno(
            _("dialog.confirm"), _("student.delete_confirm", name=name)
        ):
            delete_student(sid)
            self._load_data()

    def _import_csv_dialog(self):
        path = filedialog.askopenfilename(
            title=_("students.import_csv_title"),
            filetypes=[("CSV files", "*.csv")]
        )
        if not path:
            return
        try:
            added = import_csv_to_class(self.class_id, path)
            messagebox.showinfo(
                _("dialog.success"),
                f"{added} {_('student') if added == 1 else _('students_plural')} importe(s)"
            )
            self._load_data()
        except Exception as e:
            messagebox.showerror(_("dialog.error"), str(e))

    def destroy(self):
        if self.frame:
            self.frame.destroy()
