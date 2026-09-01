import sys
import customtkinter as ctk
from tkinter import messagebox
from app.i18n.translator import _, anchor
from app.repositories.database import get_cfg
from app.services.grade_service import (
    list_matieres, add_matiere, update_matiere, delete_matiere, seed_matieres,
    list_branches_for_year,
)
from app.ui.theme import *


class SubjectsView:
    def __init__(self, master, app_ref):
        self.master = master
        self.app = app_ref
        self.frame = None
        self.cfg = get_cfg()

    def build(self):
        self.frame = ctk.CTkScrollableFrame(self.master, fg_color="transparent", corner_radius=0)
        self.frame.grid(row=0, column=0, sticky="nsew")
        self.frame.grid_columnconfigure(0, weight=1)
        self._fix_scroll(self.frame)

        ctk.CTkLabel(
            self.frame, text=_("subjects.title"),
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_WHITE
        ).pack(anchor=anchor("w"), pady=(0, 10))

        levels = self.cfg.get("levels", {})
        level_keys = list(levels.keys())
        years_struct = self.cfg.get("years_structure", {})

        self._level_selector = ctk.CTkComboBox(
            self.frame, values=[levels[lk] for lk in level_keys],
            state="readonly", corner_radius=0,
        )
        self._level_selector.pack(anchor=anchor("w"), pady=5)
        if level_keys:
            self._level_selector.set(levels[level_keys[0]])

        self._year_selector = ctk.CTkComboBox(
            self.frame, values=years_struct.get(level_keys[0], []),
            state="readonly", corner_radius=0,
        )
        self._year_selector.pack(anchor=anchor("w"), pady=5)
        if years_struct.get(level_keys[0]):
            self._year_selector.set(years_struct[level_keys[0]][0])

        self._branch_selector = ctk.CTkComboBox(
            self.frame, values=[_("classes.no_branch")],
            state="readonly", corner_radius=0,
        )
        self._branch_selector.pack(anchor=anchor("w"), pady=5)

        def _update_branches(lk, yr):
            if lk == "lycee":
                branches = list_branches_for_year(yr)
                self._branch_selector.configure(values=[_("classes.no_branch")] + branches)
                self._branch_selector.set(_("classes.no_branch"))
            else:
                self._branch_selector.configure(values=[_("classes.no_branch")])
                self._branch_selector.set(_("classes.no_branch"))

        def on_level_change(choice):
            lk = self._get_current_level_key()
            yrs = years_struct.get(lk, [])
            self._year_selector.configure(values=yrs)
            if yrs:
                self._year_selector.set(yrs[0])
            _update_branches(lk, self._year_selector.get())
            self._refresh_list()

        self._level_selector.configure(command=on_level_change)

        def on_year_change(choice):
            lk = self._get_current_level_key()
            _update_branches(lk, choice)
            self._refresh_list()

        self._year_selector.configure(command=on_year_change)

        # initialise branch
        if level_keys:
            _update_branches(level_keys[0], self._year_selector.get())

        ctk.CTkButton(
            self.frame, text=_("subjects.seed"),
            command=self._seed,
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(anchor=anchor("w"), pady=5)

        self._list_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self._list_frame.pack(fill="x", pady=10)

        self._build_add_form()
        self._refresh_list()

    def _get_current_level_key(self):
        levels = self.cfg.get("levels", {})
        for k, v in levels.items():
            if v == self._level_selector.get():
                return k
        return list(levels.keys())[0]

    def _get_current_year(self):
        return self._year_selector.get()

    def _get_current_branch(self):
        val = self._branch_selector.get()
        return "" if val == _("classes.no_branch") else val

    def _refresh_list(self):
        for w in self._list_frame.winfo_children():
            w.destroy()
        lk = self._get_current_level_key()
        yr = self._get_current_year()
        br = self._get_current_branch()
        if not yr:
            return
        matieres = list_matieres(lk, yr, branch=br)

        if not matieres:
            ctk.CTkLabel(
                self._list_frame, text=_("subjects.empty"),
                text_color=TEXT_LIGHT
            ).pack(pady=10)
            return

        header = ctk.CTkFrame(self._list_frame, fg_color=BG_CARD, corner_radius=0,
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

        for m in matieres:
            row = ctk.CTkFrame(self._list_frame, fg_color=BG_INPUT, corner_radius=0,
                               border_width=1, border_color=BORDER_COLOR)
            row.pack(fill="x", pady=1)
            name_var = ctk.StringVar(value=m.name)
            coef_var = ctk.StringVar(value=str(m.coefficient))

            name_e = ctk.CTkEntry(row, textvariable=name_var, width=200, corner_radius=0)
            name_e.pack(side="left", padx=5, pady=4)
            coef_e = ctk.CTkEntry(row, textvariable=coef_var, width=60, corner_radius=0)
            coef_e.pack(side="left", padx=5, pady=4)

            def save(mid=m.id, nv=name_var, cv=coef_var):
                try:
                    update_matiere(mid, nv.get().strip(), float(cv.get().strip()))
                    self._refresh_list()
                except ValueError as e:
                    messagebox.showerror(_("dialog.error"), str(e))

            ctk.CTkButton(
                row, text=_("subjects.save_btn"), width=60,
                command=save, fg_color=BTN_BG, hover_color=BTN_HOVER,
                text_color=TEXT_WHITE, corner_radius=0, border_width=1, border_color=BTN_BORDER,
            ).pack(side="left", padx=2)

            def delete(mid=m.id):
                if messagebox.askyesno(_("dialog.confirm"), _("subjects.delete_confirm", name=name_var.get())):
                    delete_matiere(mid)
                    self._refresh_list()

            ctk.CTkButton(
                row, text=_("classes.delete"), width=60,
                command=delete, fg_color=BTN_BG, hover_color=BTN_HOVER,
                text_color=TEXT_WHITE, corner_radius=0, border_width=1, border_color=BTN_BORDER,
            ).pack(side="left", padx=2)

    def _build_add_form(self):
        self._add_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self._add_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(self._add_frame, text=_("subjects.add_title"),
                     font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_WHITE
                     ).pack(anchor=anchor("w"))

        inner = ctk.CTkFrame(self._add_frame, fg_color="transparent")
        inner.pack(fill="x", pady=2)

        self._new_name = ctk.CTkEntry(inner, placeholder_text=_("subjects.name_placeholder"), width=200, corner_radius=0)
        self._new_name.pack(side="left", padx=5)
        self._new_coef = ctk.CTkEntry(inner, placeholder_text=_("subjects.coef_placeholder"), width=60, corner_radius=0)
        self._new_coef.pack(side="left", padx=5)
        self._new_coef.insert(0, "1")

        ctk.CTkButton(
            inner, text=_("subjects.add_btn"),
            command=self._add_new,
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(side="left", padx=5)

    def _add_new(self):
        name = self._new_name.get().strip()
        if not name:
            messagebox.showerror(_("dialog.error"), _("subjects.name_required"))
            return
        try:
            coef = float(self._new_coef.get().strip())
        except ValueError:
            messagebox.showerror(_("dialog.error"), _("subjects.coef_invalid"))
            return
        lk = self._get_current_level_key()
        yr = self._get_current_year()
        br = self._get_current_branch()
        add_matiere(name, coef, lk, yr, branch=br)
        self._new_name.delete(0, "end")
        self._new_coef.delete(0, "end")
        self._new_coef.insert(0, "1")
        self._refresh_list()

    def _seed(self):
        count = seed_matieres()
        if count:
            messagebox.showinfo(_("dialog.success"), _("subjects.seeded", count=count))
        else:
            messagebox.showinfo(_("dialog.info"), _("subjects.already_seeded"))
        self._refresh_list()

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
