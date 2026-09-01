"""Teacher assignment view — fetch data from admin via network, grade grid, push back."""
import sys
import customtkinter as ctk
from tkinter import messagebox, simpledialog
from app.i18n.translator import _, anchor
from app.ui.theme import *


class AssignmentsView:
    def __init__(self, master, app_ref):
        self.master = master
        self.app = app_ref
        self.frame = None

        self._classes = []
        self._subjects = []
        self._students = []
        self._class_id = None
        self._matiere_id = None
        self._semester = 1
        self._assignments = []  # list of {"title": …, "coefficient": 1.0, "id": int}
        self._grades = {}  # {student_id: {assignment_id: float}}
        self._entry_widgets = {}
        self._avg_labels = {}
        self._next_id = 1

    def destroy(self):
        if self.frame:
            self.frame.destroy()

    def _client(self):
        return self.app.client

    def _ensure_client(self):
        if not self._client():
            from tkinter import messagebox
            messagebox.showinfo(_("dialog.info"), _("connect.status_error"))
            self.app.show_view("connect")
            return False
        return True

    def build(self):
        self.frame = ctk.CTkScrollableFrame(
            self.master, fg_color="transparent", corner_radius=0,
        )
        self.frame.grid(row=0, column=0, sticky="nsew")
        self.frame.grid_columnconfigure(0, weight=1)
        self._fix_scroll(self.frame)

        if not self._ensure_client():
            return
        self._show_class_list()

    def _clear(self):
        for w in self.frame.winfo_children():
            w.destroy()

    # ── Level 1: Class list ────────────────────────────────────────────

    def _show_class_list(self):
        self._clear()
        self._class_id = None
        self._matiere_id = None
        self._assignments = []
        self._grades = {}
        self._students = []

        outer = ctk.CTkScrollableFrame(self.frame, fg_color="transparent", corner_radius=0)
        outer.pack(fill="both", expand=True)
        outer.grid_columnconfigure(0, weight=1)
        self._fix_scroll(outer)

        ctk.CTkLabel(
            outer, text=_("assignments.select_class"),
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_WHITE,
        ).pack(anchor=anchor("w"), pady=(0, 15))

        try:
            self._classes = self._client().fetch_classes()
        except Exception as e:
            ctk.CTkLabel(
                outer, text=_("connect.fail", error=str(e)),
                text_color=DANGER, font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            ).pack(anchor=anchor("w"))
            return

        if not self._classes:
            ctk.CTkLabel(
                outer, text=_("assignments.no_subjects"),
                text_color=TEXT_LIGHT, font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            ).pack(anchor=anchor("w"))
            return

        current_level = None
        for c in self._classes:
            level_name = c.get("level_name", "")
            if current_level != level_name:
                if current_level is not None:
                    ctk.CTkFrame(outer, height=1, fg_color=BORDER_COLOR).pack(fill="x", pady=5)
                current_level = level_name
                ctk.CTkLabel(
                    outer, text=level_name,
                    font=(FONT_FAMILY, FONT_SIZE_LARGE, "bold"), text_color=TEXT_WHITE,
                ).pack(anchor=anchor("w"), pady=(5, 2))

            count = c.get("count", 0)
            label_text = f"{c['name']} — {_('year')} {c['year']} ({count} {_('student') if count == 1 else _('students_plural')})"
            if c.get("branch"):
                label_text += f" [{c['branch']}]"
            card = ctk.CTkFrame(outer, fg_color=BG_INPUT, corner_radius=0,
                                border_width=1, border_color=BORDER_COLOR)
            card.pack(fill="x", pady=2)
            ctk.CTkLabel(
                card, text=label_text,
                font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_WHITE,
            ).pack(side="left", padx=15, pady=8)
            ctk.CTkButton(
                card, text=_("assignments.select_subject"),
                width=80,
                fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
                corner_radius=0, border_width=1, border_color=BTN_BORDER,
                command=lambda cid=c["id"]: self._show_subject_list(cid),
            ).pack(side="right", padx=5)

    # ── Level 2: Subject list ──────────────────────────────────────────

    def _show_subject_list(self, class_id):
        self._clear()
        self._class_id = class_id
        self._matiere_id = None
        self._assignments = []
        self._grades = {}

        class_name = ""
        for c in self._classes:
            if c["id"] == class_id:
                class_name = c["name"]
                break

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
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_WHITE,
        ).pack(anchor=anchor("w"), pady=(0, 15))

        try:
            self._subjects = self._client().fetch_subjects(class_id)
        except Exception as e:
            ctk.CTkLabel(
                outer, text=str(e),
                text_color=DANGER, font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            ).pack(anchor=anchor("w"))
            return

        if not self._subjects:
            ctk.CTkLabel(
                outer, text=_("assignments.no_subjects"),
                text_color=TEXT_LIGHT, font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            ).pack(anchor=anchor("w"))
            return

        for m in self._subjects:
            card = ctk.CTkFrame(outer, fg_color=BG_INPUT, corner_radius=0,
                                border_width=1, border_color=BORDER_COLOR)
            card.pack(fill="x", pady=2)
            ctk.CTkLabel(
                card, text=f"{m['name']} (coef {m['coefficient']})",
                font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_WHITE,
            ).pack(side="left", padx=15, pady=8)
            ctk.CTkButton(
                card, text=_("nav.assignments"), width=80,
                fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
                corner_radius=0, border_width=1, border_color=BTN_BORDER,
                command=lambda mid=m["id"]: self._show_grade_grid(class_id, mid),
            ).pack(side="right", padx=5)

    # ── Level 3: Grade grid ────────────────────────────────────────────

    def _show_grade_grid(self, class_id, matiere_id):
        self._clear()
        self._class_id = class_id
        self._matiere_id = matiere_id

        matiere_name = ""
        for m in self._subjects:
            if m["id"] == matiere_id:
                matiere_name = m["name"]
                break

        class_name = ""
        for c in self._classes:
            if c["id"] == class_id:
                class_name = c["name"]
                break

        try:
            self._students = self._client().fetch_students(class_id)
        except Exception as e:
            messagebox.showerror(_("dialog.error"), str(e))
            self._show_subject_list(class_id)
            return

        outer = ctk.CTkScrollableFrame(self.frame, fg_color="transparent", corner_radius=0)
        outer.pack(fill="both", expand=True)
        outer.grid_columnconfigure(0, weight=1)
        self._fix_scroll(outer)

        ctk.CTkButton(
            outer, text=f"\u2190 {_('assignments.back_to_subjects')}",
            command=lambda: self._show_subject_list(class_id),
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(anchor=anchor("w"), pady=(0, 5))

        ctk.CTkLabel(
            outer, text=f"{matiere_name} — {class_name}",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_WHITE,
        ).pack(anchor=anchor("w"), pady=(0, 5))

        # Semester tabs
        sem_row = ctk.CTkFrame(outer, fg_color="transparent")
        sem_row.pack(fill="x", pady=5)
        self._sem1_btn = ctk.CTkButton(
            sem_row, text=_("assignments.sem1"),
            command=lambda: self._switch_sem(1),
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER, width=100,
        )
        self._sem1_btn.pack(side="left", padx=5)
        self._sem2_btn = ctk.CTkButton(
            sem_row, text=_("assignments.sem2"),
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

        self._send_btn = ctk.CTkButton(
            toolbar, text=_("assignments.send"),
            command=self._push_data,
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        )
        self._send_btn.pack(side="left", padx=2)

        # Grid container
        self._grid_outer = ctk.CTkFrame(outer, fg_color="transparent")
        self._grid_outer.pack(fill="x", pady=10)

        self._semester = 1
        self._build_grid()

    def _build_grid(self):
        for w in self._grid_outer.winfo_children():
            w.destroy()

        if not self._students:
            ctk.CTkLabel(
                self._grid_outer, text=_("assignments.no_students"),
                text_color=TEXT_LIGHT, font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            ).pack(pady=20)
            return

        # Header
        header = ctk.CTkFrame(self._grid_outer, fg_color=BG_CARD, corner_radius=0,
                              border_width=1, border_color=BORDER_COLOR)
        header.pack(fill="x", pady=1)

        ctk.CTkLabel(
            header, text=_("assignments.student_header"),
            font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"), text_color=TEXT_WHITE,
            width=200, anchor="w",
        ).pack(side="left", padx=10)

        for a in self._assignments:
            col_frame = ctk.CTkFrame(header, fg_color="transparent", width=130)
            col_frame.pack(side="left", padx=2)
            col_frame.pack_propagate(False)
            ctk.CTkLabel(
                col_frame, text=a["title"],
                font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"), text_color=TEXT_WHITE,
                anchor="center",
            ).pack()
            ctk.CTkLabel(
                col_frame, text=f"(x{a['coefficient']})",
                font=(FONT_FAMILY, 10), text_color=TEXT_LIGHT, anchor="center",
            ).pack()
            ctk.CTkButton(
                col_frame, text="×", width=20,
                command=lambda aid=a["id"]: self._delete_assignment(aid),
                fg_color=DANGER, hover_color="#cccccc", text_color=TEXT_WHITE,
                corner_radius=0, border_width=0, font=(FONT_FAMILY, 10),
            ).pack(anchor="e")

        ctk.CTkLabel(
            header, text=_("assignments.avg_header"),
            font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"), text_color=TEXT_WHITE,
            width=80, anchor="center",
        ).pack(side="left", padx=5)

        # Data rows
        self._entry_widgets = {}
        self._avg_labels = {}

        for s in self._students:
            sid = s["id"]
            row = ctk.CTkFrame(self._grid_outer, fg_color=BG_INPUT, corner_radius=0,
                               border_width=1, border_color=BORDER_COLOR)
            row.pack(fill="x", pady=1)

            ctk.CTkLabel(
                row, text=s["full_name"],
                font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_WHITE,
                width=200, anchor="w",
            ).pack(side="left", padx=10, pady=4)

            self._entry_widgets[sid] = {}
            for a in self._assignments:
                entry = ctk.CTkEntry(row, width=60, corner_radius=0)
                entry.pack(side="left", padx=2, pady=2)
                val = self._grades.get(sid, {}).get(a["id"])
                if val is not None:
                    entry.insert(0, str(val))
                entry.bind("<KeyRelease>", lambda e, s=sid: self._update_avg(s))
                entry.bind("<FocusOut>", lambda e, s=sid: self._save_row(s))
                self._entry_widgets[sid][a["id"]] = entry

            avg_label = ctk.CTkLabel(
                row, text="0.00",
                font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_WHITE,
                width=80, anchor="center",
            )
            avg_label.pack(side="left", padx=5)
            self._avg_labels[sid] = avg_label

        self._refresh_averages()

    def _update_avg(self, student_id):
        s = 0.0
        c = 0.0
        for a in self._assignments:
            entry = self._entry_widgets.get(student_id, {}).get(a["id"])
            if not entry:
                continue
            val_str = entry.get().strip()
            if val_str:
                try:
                    v = float(val_str)
                    s += v * a["coefficient"]
                    c += a["coefficient"]
                except ValueError:
                    pass
        avg = s / c if c > 0 else 0.0
        lbl = self._avg_labels.get(student_id)
        if lbl:
            lbl.configure(text=f"{avg:.2f}")

    def _save_row(self, student_id):
        for a in self._assignments:
            entry = self._entry_widgets.get(student_id, {}).get(a["id"])
            if entry:
                val_str = entry.get().strip()
                if val_str:
                    try:
                        v = float(val_str)
                        if 0 <= v <= 20:
                            self._grades.setdefault(student_id, {})[a["id"]] = v
                    except ValueError:
                        pass

    def _save_all(self):
        for s in self._students:
            self._save_row(s["id"])

    def _refresh_averages(self):
        for s in self._students:
            self._update_avg(s["id"])

    def _switch_sem(self, sem):
        self._save_all()
        self._semester = sem
        self._sem1_btn.configure(fg_color=BTN_BG if sem != 1 else "#cccccc")
        self._sem2_btn.configure(fg_color=BTN_BG if sem != 2 else "#cccccc")
        self._build_grid()

    def _add_assignment_dialog(self):
        title = simpledialog.askstring(
            _("assignments.add_assignment"),
            _("assignments.title_prompt"),
        )
        if not title or not title.strip():
            return
        aid = self._next_id
        self._next_id += 1
        self._assignments.append({
            "id": aid,
            "title": title.strip(),
            "coefficient": 1.0,
        })
        self._build_grid()

    def _delete_assignment(self, assignment_id):
        a = next((a for a in self._assignments if a["id"] == assignment_id), None)
        if not a:
            return
        if messagebox.askyesno(_("dialog.confirm"),
                               _("dialog.delete_confirm", name=a["title"])):
            self._assignments = [a for a in self._assignments if a["id"] != assignment_id]
            for sid in self._grades:
                self._grades[sid].pop(assignment_id, None)
            self._build_grid()

    # ── Push data to admin ─────────────────────────────────────────────

    def _push_data(self):
        if not self._assignments:
            messagebox.showinfo(_("dialog.info"), _("assignments.no_assignments"))
            return
        if not self._ensure_client():
            return

        self._save_all()

        data = {
            "matiere_id": self._matiere_id,
            "classe_id": self._class_id,
            "semester": self._semester,
            "assignments": [
                {"title": a["title"], "coefficient": a["coefficient"]}
                for a in self._assignments
            ],
            "grades": {
                str(sid): {str(aid): v for aid, v in gs.items()}
                for sid, gs in self._grades.items()
            },
        }

        self._send_btn.configure(text=_("assignments.sending"), state="disabled")
        try:
            self._client().push_data(data)
            a_count = len(self._assignments)
            g_count = sum(len(gs) for gs in self._grades.values())
            messagebox.showinfo(
                _("dialog.success"),
                _("assignments.sent", assignments=a_count, grades=g_count),
            )
        except Exception as e:
            messagebox.showerror(
                _("dialog.error"),
                _("assignments.send_fail", error=str(e)),
            )
        finally:
            self._send_btn.configure(text=_("assignments.send"), state="normal")

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
