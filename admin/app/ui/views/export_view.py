import subprocess
import sys
import customtkinter as ctk
from tkinter import messagebox
from app.i18n.translator import _
from app.services.class_service import list_all_classes
from app.services.export_service import (
    export_class_html, export_liste_eleves, export_certificat_scolarite,
    backup_all as export_backup,
)
from app.repositories.database import is_initialized
from app.ui.theme import *


class ExportView:
    def __init__(self, master, app_ref):
        self.master = master
        self.app = app_ref
        self.frame = None

    def build(self):
        self.frame = ctk.CTkScrollableFrame(self.master, fg_color="transparent", corner_radius=0)
        self.frame.grid(row=0, column=0, sticky="nsew")
        self.frame.grid_columnconfigure(0, weight=1)
        self._fix_scroll(self.frame)

        ctk.CTkLabel(
            self.frame, text=_("export.title"),
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_WHITE
        ).pack(anchor="w", pady=(0, 15))

        if not is_initialized():
            ctk.CTkLabel(
                self.frame, text=_("classes.not_configured"),
                text_color=TEXT_LIGHT
            ).pack()
            return

        ctk.CTkLabel(
            self.frame, text=_("export.select_class"),
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_LIGHT
        ).pack(anchor="w")

        self._build_class_export_list()

        sep = ctk.CTkFrame(self.frame, height=1, fg_color=BORDER_COLOR)
        sep.pack(fill="x", pady=20)

        ctk.CTkButton(
            self.frame, text=_("export.backup"),
            command=self._do_backup,
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(pady=5)

    def _build_class_export_list(self):
        for cid, level_name, year, class_name, count, _br in list_all_classes():
            card = ctk.CTkFrame(self.frame, fg_color=BG_INPUT, corner_radius=0, border_width=1, border_color=BORDER_COLOR)
            card.pack(fill="x", pady=3)
            ctk.CTkLabel(
                card,
                text=f"{class_name} — {level_name} / Année {year} ({count} {_('student') if count == 1 else _('students_plural')})",
                font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_WHITE
            ).pack(side="left", padx=10, pady=8)

            btn_row = ctk.CTkFrame(card, fg_color="transparent")
            btn_row.pack(side="right")

            ctk.CTkButton(
                btn_row, text=_("export.html"), width=70,
                fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
                corner_radius=0, border_width=1, border_color=BTN_BORDER,
                command=lambda cid=cid: self._export_html(cid)
            ).pack(side="left", padx=2)
            ctk.CTkButton(
                btn_row, text="Liste", width=60,
                fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
                corner_radius=0, border_width=1, border_color=BTN_BORDER,
                command=lambda cid=cid: self._export_liste(cid)
            ).pack(side="left", padx=2)
            ctk.CTkButton(
                btn_row, text="Certificat", width=80,
                fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
                corner_radius=0, border_width=1, border_color=BTN_BORDER,
                command=lambda cid=cid: self._export_certificat(cid)
            ).pack(side="left", padx=2)
            ctk.CTkButton(
                btn_row, text=_("export.print"), width=70,
                fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
                corner_radius=0, border_width=1, border_color=BTN_BORDER,
                command=lambda cid=cid: self._print(cid)
            ).pack(side="left", padx=2)

    def _open_file(self, path):
        if path:
            subprocess.run(["xdg-open", path], stderr=subprocess.DEVNULL)

    def _export_html(self, class_id):
        path = export_class_html(class_id)
        if path:
            messagebox.showinfo(_("dialog.success"), f"Exporté : {path}")
            self._open_file(path)

    def _export_liste(self, class_id):
        path = export_liste_eleves(class_id, ecole="")
        if path:
            messagebox.showinfo(_("dialog.success"), f"Liste créée : {path}")
            self._open_file(path)

    def _export_certificat(self, class_id):
        path = export_liste_eleves(class_id, ecole="")
        if path:
            messagebox.showinfo(_("dialog.success"), f"Document créé : {path}")
            self._open_file(path)

    def _print(self, class_id):
        path = export_class_html(class_id)
        if path:
            try:
                subprocess.run(["xdg-open", path], stderr=subprocess.DEVNULL)
                messagebox.showinfo(_("dialog.success"), _("dialog.print_sent"))
            except Exception as e:
                messagebox.showerror(_("dialog.error"), str(e))

    def _do_backup(self):
        path = export_backup()
        if path:
            messagebox.showinfo(_("dialog.success"), _("backup.success", path=path))
        else:
            messagebox.showerror(_("dialog.error"), _("backup.error", error="Voir les logs"))

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
