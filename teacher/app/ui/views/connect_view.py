"""Teacher connection view — first screen shown on launch."""
import os
import json
import customtkinter as ctk
from tkinter import messagebox
from app.i18n.translator import _, anchor
from app.network.crypto import get_local_ip
from app.ui.theme import *


CONFIG_DIR = os.path.expanduser("~/.mainpixel")
CONFIG_PATH = os.path.join(CONFIG_DIR, "teacher_config.json")


def load_teacher_config() -> dict:
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def save_teacher_config(cfg: dict):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


class ConnectView:
    def __init__(self, master, app_ref):
        self.master = master
        self.app = app_ref
        self.frame = None

    def destroy(self):
        if self.frame:
            self.frame.destroy()

    def build(self):
        self.frame = ctk.CTkScrollableFrame(
            self.master, fg_color="transparent", corner_radius=0,
        )
        self.frame.grid(row=0, column=0, sticky="nsew")
        self.frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.frame, text=_("connect.title"),
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_WHITE,
        ).pack(anchor=anchor("w"), pady=(0, 25))

        card = ctk.CTkFrame(self.frame, fg_color=BG_CARD, corner_radius=0,
                            border_width=1, border_color=BORDER_COLOR)
        card.pack(fill="x", pady=(0, 10))
        card.grid_columnconfigure(1, weight=1)

        row = 0

        # Local IP display
        local_ip = get_local_ip()
        ip_frame = ctk.CTkFrame(card, fg_color="transparent")
        ip_frame.grid(row=row, column=0, columnspan=3, sticky=anchor("w"), padx=15, pady=(10, 2))
        ctk.CTkLabel(
            ip_frame, text=_("connect.my_ip", ip=local_ip),
            font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"), text_color=TEXT_LIGHT,
        ).pack(side="left")
        self._ip_copy_label = ctk.CTkLabel(
            ip_frame, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=SUCCESS,
        )
        self._ip_copy_label.pack(side="left", padx=5)
        ctk.CTkButton(
            ip_frame, text=_("connect.copy_ip"), width=50,
            command=lambda: self._copy_ip(local_ip),
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(side="left", padx=5)
        row += 1

        ctk.CTkLabel(
            card, text=_("connect.name_label"),
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_LIGHT,
        ).grid(row=row, column=0, sticky=anchor("w"), padx=15, pady=(15, 5))
        self._name_entry = ctk.CTkEntry(card, width=250, corner_radius=0)
        self._name_entry.grid(row=row, column=1, sticky=anchor("w"), padx=5, pady=(15, 5))
        row += 1

        ctk.CTkLabel(
            card, text=_("connect.ip_label"),
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_LIGHT,
        ).grid(row=row, column=0, sticky=anchor("w"), padx=15, pady=5)
        self._ip_entry = ctk.CTkEntry(card, width=250, corner_radius=0)
        self._ip_entry.grid(row=row, column=1, sticky=anchor("w"), padx=5, pady=5)
        row += 1

        ctk.CTkLabel(
            card, text=_("connect.password_label"),
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_LIGHT,
        ).grid(row=row, column=0, sticky=anchor("w"), padx=15, pady=5)
        self._pwd_entry = ctk.CTkEntry(card, width=250, corner_radius=0)
        self._pwd_entry.grid(row=row, column=1, sticky=anchor("w"), padx=5, pady=5)
        row += 1

        self._status_label = ctk.CTkLabel(
            card, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=SUCCESS,
        )
        self._status_label.grid(row=row, column=0, columnspan=2, sticky=anchor("w"),
                                padx=15, pady=(5, 5))
        row += 1

        ctk.CTkButton(
            card, text=_("connect.btn"),
            command=self._do_connect,
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).grid(row=row, column=0, columnspan=2, sticky=anchor("w"), padx=15, pady=(5, 15))

        # Load saved config
        self._load_config()

    def _copy_ip(self, ip: str):
        self.frame.clipboard_clear()
        self.frame.clipboard_append(ip)
        self._ip_copy_label.configure(text=_("connect.ip_copied"))
        self.frame.after(2000, lambda: self._ip_copy_label.configure(text=""))

    def _load_config(self):
        cfg = load_teacher_config()
        self._name_entry.insert(0, cfg.get("teacher_name", ""))
        self._ip_entry.insert(0, cfg.get("admin_host", ""))
        self._pwd_entry.insert(0, cfg.get("network_password", ""))
        if cfg.get("teacher_name") and cfg.get("admin_host"):
            self._status_label.configure(
                text=_("connect.status_ok", host=cfg["admin_host"]),
                text_color=SUCCESS,
            )

    def _do_connect(self):
        name = self._name_entry.get().strip()
        ip = self._ip_entry.get().strip()
        pwd = self._pwd_entry.get().strip()
        if not name or not ip:
            messagebox.showerror(_("dialog.error"), _("connect.required"))
            return

        from app.network.client import RegistryClient
        client = RegistryClient(teacher_name=name)
        client.set_password(pwd)
        client.admin_host = ip

        try:
            client.register()
            # Save config
            cfg = {
                "teacher_name": name,
                "admin_host": ip,
                "network_password": pwd,
            }
            save_teacher_config(cfg)

            self._status_label.configure(
                text=_("connect.status_ok", host=ip),
                text_color=SUCCESS,
            )
            self.app.set_client(client)
            messagebox.showinfo(
                _("dialog.success"),
                _("connect.success", name=name),
            )
            # Switch to assignments
            self.app.show_view("assignments")
        except Exception as e:
            self._status_label.configure(
                text=_("connect.status_error"),
                text_color=DANGER,
            )
            messagebox.showerror(
                _("dialog.error"),
                _("connect.fail", error=str(e)),
            )
