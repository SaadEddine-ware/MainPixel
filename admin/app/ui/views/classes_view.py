import sys
import customtkinter as ctk
from tkinter import messagebox
from app.i18n.translator import _, anchor
from app.services.class_service import (
    list_levels, list_years_for_level, create_class, delete_class,
    rename_class, list_classes, search_classes,
)
from app.services.grade_service import list_branches_for_year
from app.repositories.database import is_initialized, get_cfg
from app.ui.theme import *


class ClassesView:
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
            self.frame, text=_("classes.title"),
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_WHITE
        ).pack(anchor=anchor("w"), pady=(0, 15))

        if not is_initialized():
            ctk.CTkLabel(
                self.frame, text=_("classes.not_configured"),
                text_color=TEXT_LIGHT
            ).pack()
            return

        self._build_search()
        self._build_class_list()
        self._build_create_form()

    def _build_search(self):
        row = ctk.CTkFrame(self.frame, fg_color="transparent")
        row.pack(fill="x", pady=5)
        entry = ctk.CTkEntry(row, placeholder_text=_("classes.search_placeholder"), width=300)
        entry.pack(side="left", padx=5)
        ctk.CTkButton(
            row, text=_("classes.search"),
            command=lambda: self._do_search(entry.get().strip()),
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(side="left", padx=5)

    def _do_search(self, query):
        if not query:
            return
        results = search_classes(query)
        self.app.clear_main()
        frame = ctk.CTkScrollableFrame(self.master, fg_color="transparent", corner_radius=0)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        self._fix_scroll(frame)
        ctk.CTkLabel(
            frame, text=f"{_('classes.search')} : '{query}'",
            font=(FONT_FAMILY, FONT_SIZE_LARGE, "bold"), text_color=TEXT_WHITE
        ).pack(anchor=anchor("w"), pady=10)
        if not results:
            ctk.CTkLabel(frame, text=_("classes.no_results"), text_color=TEXT_LIGHT).pack()
        for cid, lk, lname, y, cn, cnt, br in results:
            card = ctk.CTkFrame(frame, fg_color=BG_INPUT, corner_radius=0, border_width=1, border_color=BORDER_COLOR)
            card.pack(fill="x", pady=2)
            text = f"{cn} — {lname} / {_('year')} {y} ({cnt} {_('student') if cnt == 1 else _('students_plural')})"
            if br:
                text += f" [{br}]"
            ctk.CTkLabel(
                card, text=text,
                font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_WHITE
            ).pack(side="left", padx=15, pady=8)
            ctk.CTkButton(
                card, text=_("classes.open"), width=80,
                fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
                corner_radius=0, border_width=1, border_color=BTN_BORDER,
                command=lambda cid=cid: self.app.open_class(cid)
            ).pack(side="right", padx=5)
        ctk.CTkButton(
            frame, text=f"← {_('classes.back')}",
            command=lambda: self.app.show_view("classes"),
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(pady=10)

    def _build_class_list(self):
        for lk, lname in list_levels():
            lf = ctk.CTkFrame(self.frame, fg_color="transparent")
            lf.pack(fill="x", pady=5)
            ctk.CTkLabel(
                lf, text=lname,
                font=(FONT_FAMILY, FONT_SIZE_LARGE, "bold"), text_color=TEXT_WHITE
            ).pack(anchor=anchor("w"))
            for y in list_years_for_level(lk):
                yf = ctk.CTkFrame(lf, fg_color=BG_INPUT, corner_radius=0, border_width=1, border_color=BORDER_COLOR)
                yf.pack(fill="x", pady=2, padx=10)
                ctk.CTkLabel(
                    yf, text=f"{_('year')} {y}",
                    font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_WHITE
                ).pack(anchor=anchor("w"), padx=10, pady=(5, 0))
                classes = list_classes(lk, y)
                if not classes:
                    ctk.CTkLabel(
                        yf, text=f"  {_('classes.no_classes')}",
                        text_color=TEXT_LIGHT, font=(FONT_FAMILY, FONT_SIZE_SMALL)
                    ).pack(anchor=anchor("w"), padx=15)
                for cid, cn, cnt, br in classes:
                    row_f = ctk.CTkFrame(yf, fg_color="transparent")
                    row_f.pack(fill="x", padx=15, pady=1)
                    label_text = f"  {cn}  ({cnt} {_('student') if cnt == 1 else _('students_plural')})"
                    if br:
                        label_text += f"  [{br}]"
                    ctk.CTkLabel(
                        row_f, text=label_text,
                        font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_LIGHT
                    ).pack(side="left")
                    ctk.CTkButton(
                        row_f, text=_("classes.open"), width=65,
                        fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
                        corner_radius=0, border_width=1, border_color=BTN_BORDER,
                        command=lambda cid=cid: self.app.open_class(cid)
                    ).pack(side="right", padx=2)
                    ctk.CTkButton(
                        row_f, text=_("classes.rename"), width=80,
                        fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
                        corner_radius=0, border_width=1, border_color=BTN_BORDER,
                        command=lambda cid=cid, cn=cn: self._rename_dialog(cid, cn)
                    ).pack(side="right", padx=2)
                    ctk.CTkButton(
                        row_f, text=_("classes.delete"), width=65,
                        fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
                        corner_radius=0, border_width=1, border_color=BTN_BORDER,
                        command=lambda cid=cid, cn=cn: self._delete_dialog(cid, cn)
                    ).pack(side="right", padx=2)

    def _build_create_form(self):
        f = ctk.CTkFrame(self.frame, fg_color="transparent")
        f.pack(fill="x", pady=(15, 5))
        ctk.CTkLabel(
            f, text=_("classes.new_class") + ":",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_WHITE
        ).pack(anchor=anchor("w"))
        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x", pady=2)
        levels = list_levels()
        lv = ctk.CTkComboBox(row, values=[ln for _, ln in levels], width=140, state="readonly", corner_radius=0)
        lv.pack(side="left", padx=5)
        if levels:
            lv.set(levels[0][1])
        yr = ctk.CTkComboBox(row, values=list_years_for_level(levels[0][0]) if levels else [], width=100, state="readonly", corner_radius=0)
        yr.pack(side="left", padx=5)
        if levels and list_years_for_level(levels[0][0]):
            yr.set(list_years_for_level(levels[0][0])[0])
        cn_entry = ctk.CTkEntry(row, placeholder_text=_("classes.name_placeholder"), width=150)
        cn_entry.pack(side="left", padx=5)

        br_var = ctk.StringVar(value="")
        br_combo = ctk.CTkComboBox(row, values=[], width=200, state="readonly", corner_radius=0, variable=br_var)
        br_combo.pack(side="left", padx=5)
        br_combo.set(_("classes.no_branch"))

        def on_level_change(choice):
            for k, ln in levels:
                if ln == choice:
                    yrs = list_years_for_level(k)
                    yr.configure(values=yrs)
                    if yrs:
                        yr.set(yrs[0])
                    if k == "lycee":
                        branches = list_branches_for_year(yr.get())
                        br_combo.configure(values=[_("classes.no_branch")] + branches)
                        br_var.set("")
                    else:
                        br_combo.configure(values=[_("classes.no_branch")])
                        br_var.set("")
                    break

        def on_year_change(choice):
            for k, ln in levels:
                if lv.get() == ln and k == "lycee":
                    branches = list_branches_for_year(choice)
                    br_combo.configure(values=[_("classes.no_branch")] + branches)
                    br_var.set("")
                    break

        lv.configure(command=on_level_change)
        yr.configure(command=on_year_change)

        # initialise branch combo
        first_lk = levels[0][0] if levels else "primary"
        if first_lk == "lycee":
            branches = list_branches_for_year(yr.get()) if levels and list_years_for_level(first_lk) else []
            br_combo.configure(values=[_("classes.no_branch")] + branches)
        else:
            br_combo.configure(values=[_("classes.no_branch")])
        br_combo.set(_("classes.no_branch"))

        def do_create():
            choice = lv.get()
            lk = None
            for k, ln in levels:
                if ln == choice:
                    lk = k
                    break
            if not lk:
                return
            y = yr.get()
            name = cn_entry.get().strip()
            branch = br_var.get() if br_var.get() != _("classes.no_branch") else ""
            if not name:
                messagebox.showerror(_("dialog.error"), _("dialog.class_name_required"))
                return
            try:
                create_class(lk, y, name, branch)
                self.app.show_view("classes")
            except FileExistsError:
                messagebox.showerror(_("dialog.error"), _("dialog.class_exists", name=name))
        ctk.CTkButton(
            row, text=_("classes.create"), command=do_create,
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(side="left", padx=5)

    def _rename_dialog(self, class_id, current_name):
        d = ctk.CTkInputDialog(
            title=_("classes.rename"),
            text=f"{_('classes.rename')} '{current_name}' :"
        )
        new_name = d.get_input()
        if new_name and new_name.strip():
            try:
                rename_class(class_id, new_name.strip())
                self.app.show_view("classes")
            except (FileNotFoundError, FileExistsError) as e:
                messagebox.showerror(_("dialog.error"), str(e))

    def _delete_dialog(self, class_id, class_name):
        if messagebox.askyesno(
            _("dialog.confirm"),
            _("dialog.class_delete_confirm", name=class_name)
        ):
            try:
                delete_class(class_id)
                self.app.show_view("classes")
            except FileNotFoundError as e:
                messagebox.showerror(_("dialog.error"), str(e))

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
