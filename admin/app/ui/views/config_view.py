import sys
import customtkinter as ctk
from tkinter import messagebox
from app.i18n.translator import _, anchor
from app.repositories.database import get_cfg, save_cfg, is_initialized
from app.ui.theme import *


class ConfigView:
    def __init__(self, master, app_ref):
        self.master = master
        self.app = app_ref
        self.frame = None
        self.entries = {}

    def build(self):
        self.frame = ctk.CTkScrollableFrame(self.master, fg_color="transparent", corner_radius=0)
        self.frame.grid(row=0, column=0, sticky="nsew")
        self.frame.grid_columnconfigure(0, weight=1)
        self._fix_scroll(self.frame)

        ctk.CTkLabel(
            self.frame, text=_("config.title"),
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_WHITE
        ).pack(anchor=anchor("w"), pady=(0, 15))

        ctk.CTkLabel(
            self.frame, text=_("config.header"),
            font=(FONT_FAMILY, FONT_SIZE_LARGE, "bold"), text_color=TEXT_WHITE
        ).pack(anchor=anchor("w"), pady=(5, 2))
        ctk.CTkLabel(
            self.frame, text=_("config.warning"),
            font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_LIGHT
        ).pack(anchor=anchor("w"), pady=(0, 10))

        cfg = get_cfg()
        level_dict = cfg.get("levels", {})
        level_keys = ["primary", "middle", "lycee"]

        for lk in level_keys:
            name = level_dict.get(lk, lk.capitalize())
            row = ctk.CTkFrame(self.frame, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(
                row, text=f"  {lk.capitalize()} :",
                font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_LIGHT
            ).pack(side="left")
            e = ctk.CTkEntry(row, width=200)
            e.insert(0, name)
            e.pack(side="left", padx=10)
            self.entries[lk] = e

        ctk.CTkButton(
            self.frame, text=_("config.save"),
            command=self._save,
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(pady=15)

    def _save(self):
        cfg = get_cfg()
        for lk, entry in self.entries.items():
            val = entry.get().strip()
            if val:
                cfg["levels"][lk] = val
        save_cfg(cfg)
        messagebox.showinfo(_("dialog.success"), _("dialog.success"))
        self.app.show_view("stats")

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
