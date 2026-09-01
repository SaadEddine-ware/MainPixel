import sys
import customtkinter as ctk
from app.i18n.translator import _, anchor
from app.services.stats_service import get_statistics
from app.repositories.database import is_initialized
from app.ui.theme import *


class DashboardView:
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
            self.frame, text=_("stats.title"),
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_WHITE
        ).pack(anchor=anchor("w"), pady=(0, 20))

        if not is_initialized():
            ctk.CTkLabel(
                self.frame, text=_("stats.not_configured"),
                text_color=TEXT_LIGHT, font=(FONT_FAMILY, FONT_SIZE_NORMAL)
            ).pack(anchor=anchor("w"))
            return

        stats = get_statistics()
        summary = ctk.CTkFrame(self.frame, fg_color=BG_INPUT, corner_radius=0, border_width=1, border_color=BORDER_COLOR)
        summary.pack(fill="x", pady=5)
        ctk.CTkLabel(
            summary, text=_("stats.overview"),
            font=(FONT_FAMILY, FONT_SIZE_LARGE, "bold"), text_color=TEXT_WHITE
        ).pack(anchor=anchor("w"), padx=15, pady=(10, 5))
        ctk.CTkLabel(
            summary, text=_("stats.total", levels=stats['total_levels'],
                            classes=stats['total_classes'], students=stats['total_students']),
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_LIGHT
        ).pack(anchor=anchor("w"), padx=15, pady=(0, 10))

        for level_name, ld in stats["level_data"].items():
            card = ctk.CTkFrame(self.frame, fg_color=BG_INPUT, corner_radius=0, border_width=1, border_color=BORDER_COLOR)
            card.pack(fill="x", pady=4)
            ctk.CTkLabel(
                card, text=f"{level_name} — {ld['classes']} classe(s), {ld['students']} élève(s)",
                font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_WHITE
            ).pack(anchor=anchor("w"), padx=15, pady=(8, 2))
            for y, classes in ld["years"].items():
                if classes:
                    cls_str = ", ".join(f"{n}({c})" for _, n, c in classes)
                    ctk.CTkLabel(
                        card, text=f"  Année {y}: {cls_str}",
                        font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_LIGHT
                    ).pack(anchor=anchor("w"), padx=25, pady=1)

        ctk.CTkButton(
            self.frame, text=_("stats.refresh"),
            command=lambda: self.app.show_view("stats"),
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(pady=15)

    def destroy(self):
        if self.frame:
            self.frame.destroy()

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
