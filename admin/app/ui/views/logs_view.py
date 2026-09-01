import sys
import customtkinter as ctk
from app.i18n.translator import _
from app.repositories.database import get_session
from app.models import AuditLog
from app.ui.theme import *


class LogsView:
    def __init__(self, master, app_ref):
        self.master = master
        self.app = app_ref
        self.frame = None
        self.textbox = None

    def build(self):
        self.frame = ctk.CTkFrame(self.master, fg_color="transparent")
        self.frame.grid(row=0, column=0, sticky="nsew")
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(1, weight=1)
        self._fix_scroll(self.frame)

        top = ctk.CTkFrame(self.frame, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(
            top, text=_("logs.title"),
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_WHITE
        ).pack(side="left")

        ctk.CTkButton(
            top, text=_("logs.refresh"),
            command=self._load_logs,
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(side="right", padx=5)
        ctk.CTkButton(
            top, text=_("logs.clear"),
            command=self._clear,
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(side="right", padx=5)

        self.textbox = ctk.CTkTextbox(self.frame, fg_color=BG_INPUT, text_color=TEXT_LIGHT, corner_radius=0, border_width=1, border_color=BORDER_COLOR)
        self.textbox.grid(row=1, column=0, sticky="nsew")
        self._load_logs()

    def _load_logs(self):
        self.textbox.delete("1.0", "end")
        with get_session() as session:
            logs = session.query(AuditLog).order_by(AuditLog.id.desc()).limit(500).all()
        if not logs:
            self.textbox.insert("1.0", _("logs.empty"))
        for log in logs:
            self.textbox.insert("1.0", f"[{log.created_at}] {log.action} — {log.details}\n")

    def _clear(self):
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", _("logs.empty"))

    def _fix_scroll(self, frame):
        if sys.platform.startswith("linux"):
            pass

    def destroy(self):
        if self.frame:
            self.frame.destroy()
