"""Admin network settings: server control + teacher list management."""
import sys
import customtkinter as ctk
from tkinter import messagebox, simpledialog
from app.i18n.translator import _, anchor
from app.network.server import get_registry
from app.network.crypto import get_local_ip
from app.repositories.database import get_cfg, save_cfg
from app.ui.theme import *


class NetworkView:
    def __init__(self, master, app_ref):
        self.master = master
        self.app = app_ref
        self.frame = None
        self._server = get_registry()
        self._refresh_id = None

    def destroy(self):
        self._cancel_refresh()
        if self.frame:
            self.frame.destroy()

    # ── Core ───────────────────────────────────────────────────────────

    def build(self):
        cfg = get_cfg()
        self.frame = ctk.CTkScrollableFrame(
            self.master, fg_color="transparent", corner_radius=0,
        )
        self.frame.grid(row=0, column=0, sticky="nsew")
        self.frame.grid_columnconfigure(0, weight=1)
        self._fix_scroll(self.frame)

        ctk.CTkLabel(
            self.frame, text=_("network.title"),
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_WHITE,
        ).pack(anchor=anchor("w"), pady=(0, 15))

        self._build_server_section(cfg)
        self._build_teacher_section(cfg)
        self._build_add_form()

        ctk.CTkButton(
            self.frame, text=_("network.guide"),
            command=self._show_guide,
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(pady=10)

        self._update_status()
        self._start_auto_refresh()
        self._rebuild_teacher_list()

    # ── Section 1: Server ──────────────────────────────────────────────

    def _build_server_section(self, cfg):
        card = ctk.CTkFrame(self.frame, fg_color=BG_CARD, corner_radius=0,
                            border_width=1, border_color=BORDER_COLOR)
        card.pack(fill="x", pady=(0, 10))
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            card, text=_("network.server_label"),
            font=(FONT_FAMILY, FONT_SIZE_LARGE, "bold"), text_color=TEXT_WHITE,
        ).grid(row=0, column=0, columnspan=3, sticky=anchor("w"), padx=15, pady=(10, 5))

        # Row 1 – Local IP
        ip = get_local_ip()
        ctk.CTkLabel(
            card, text=_("network.your_ip", ip=ip),
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_WHITE,
        ).grid(row=1, column=0, sticky=anchor("w"), padx=15, pady=3)
        ctk.CTkButton(
            card, text=_("network.copy_ip"), width=60,
            command=lambda: self._copy_ip(ip),
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).grid(row=1, column=1, sticky=anchor("w"), padx=5, pady=3)
        self._ip_status_label = ctk.CTkLabel(
            card, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=WARNING,
        )
        self._ip_status_label.grid(row=1, column=2, sticky=anchor("w"), padx=5, pady=3)

        # Row 2 – Port
        ctk.CTkLabel(
            card, text=_("network.port_label"),
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_LIGHT,
        ).grid(row=2, column=0, sticky=anchor("w"), padx=15, pady=3)
        self._port_entry = ctk.CTkEntry(card, width=100, corner_radius=0)
        self._port_entry.grid(row=2, column=1, sticky=anchor("w"), padx=5, pady=3)
        self._port_entry.insert(0, str(cfg.get("admin_port", 8765)))

        # Row 3 – Password
        ctk.CTkLabel(
            card, text=_("network.password_label"),
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_LIGHT,
        ).grid(row=3, column=0, sticky=anchor("w"), padx=15, pady=3)
        self._pwd_entry = ctk.CTkEntry(card, width=200, corner_radius=0)
        self._pwd_entry.grid(row=3, column=1, sticky=anchor("w"), padx=5, pady=3)
        self._pwd_entry.insert(0, cfg.get("network_password", ""))

        # Row 4 – Status + buttons
        self._status_label = ctk.CTkLabel(
            card, text=_("network.stopped"),
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=DANGER,
        )
        self._status_label.grid(row=4, column=0, sticky=anchor("w"), padx=15, pady=(10, 2))

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.grid(row=4, column=1, columnspan=2, sticky=anchor("w"), padx=5, pady=(10, 2))
        self._start_btn = ctk.CTkButton(
            btn_row, text=_("network.start"),
            command=self._toggle_server,
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        )
        self._start_btn.pack(side="left", padx=2)

        ctk.CTkButton(
            btn_row, text=_("network.refresh"),
            command=self._rebuild_teacher_list,
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(side="left", padx=2)

    # ── Section 2: Teacher list ────────────────────────────────────────

    def _build_teacher_section(self, cfg):
        sep = ctk.CTkFrame(self.frame, height=1, fg_color=BORDER_COLOR)
        sep.pack(fill="x", pady=(0, 10))

        header = ctk.CTkFrame(self.frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(
            header, text=_("network.teachers_label"),
            font=(FONT_FAMILY, FONT_SIZE_LARGE, "bold"), text_color=TEXT_WHITE,
        ).pack(side="left")

        # Column headers
        col_header = ctk.CTkFrame(self.frame, fg_color=BG_CARD, corner_radius=0,
                                  border_width=1, border_color=BORDER_COLOR)
        col_header.pack(fill="x", pady=1)
        for i, (txt, w) in enumerate([
            (_("network.th_name"), 180),
            (_("network.th_ip"), 160),
            (_("network.th_status"), 140),
            ("", 120),
        ]):
            ctk.CTkLabel(
                col_header, text=txt,
                font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"), text_color=TEXT_WHITE,
                width=w, anchor=anchor("w"),
            ).grid(row=0, column=i, padx=8, pady=4, sticky=anchor("w"))

        self._list_container = ctk.CTkFrame(self.frame, fg_color="transparent")
        self._list_container.pack(fill="x")

        self._no_teacher_label = ctk.CTkLabel(
            self.frame, text=_("network.no_teachers"),
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_LIGHT,
        )

    def _rebuild_teacher_list(self):
        cfg = get_cfg()
        teachers = cfg.get("teachers", [])
        server_teachers = {t["name"]: t for t in self._server.teachers}

        for w in self._list_container.winfo_children():
            w.destroy()

        if not teachers:
            self._no_teacher_label.pack(anchor=anchor("w"), pady=5)
        else:
            self._no_teacher_label.pack_forget()
            for t in teachers:
                self._build_teacher_row(t, server_teachers.get(t["name"]))

    def _build_teacher_row(self, t: dict, live: dict = None):
        row = ctk.CTkFrame(self._list_container, fg_color=BG_INPUT, corner_radius=0,
                           border_width=1, border_color=BORDER_COLOR)
        row.pack(fill="x", pady=1)

        status_text = "—"
        status_color = TEXT_LIGHT
        if live:
            if live.get("has_data"):
                status_text = _("network.data_available")
                status_color = SUCCESS

        for i, (txt, w) in enumerate([
            (t["name"], 180),
            (t["ip"], 160),
            (status_text, 140),
            ("", 120),
        ]):
            ctk.CTkLabel(
                row, text=txt,
                font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=status_color
                         if i == 2 else TEXT_WHITE,
                width=w, anchor=anchor("w"),
            ).grid(row=0, column=i, padx=8, pady=6, sticky=anchor("w"))

        # Action buttons
        act = ctk.CTkFrame(row, fg_color="transparent")
        act.grid(row=0, column=4, padx=5, pady=4)
        ctk.CTkButton(
            act, text=_("network.edit"), width=50,
            command=lambda name=t["name"]: self._edit_teacher(name),
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(side="left", padx=1)
        ctk.CTkButton(
            act, text=_("network.delete"), width=50,
            command=lambda name=t["name"]: self._delete_teacher(name),
            fg_color=DANGER, hover_color="#cccccc", text_color=TEXT_WHITE,
            corner_radius=0, border_width=0,
        ).pack(side="left", padx=1)

    # ── Section 3: Add teacher form ────────────────────────────────────

    def _build_add_form(self):
        form = ctk.CTkFrame(self.frame, fg_color=BG_CARD, corner_radius=0,
                            border_width=1, border_color=BORDER_COLOR)
        form.pack(fill="x", pady=(10, 0))
        form.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(
            form, text=_("network.add_teacher_title"),
            font=(FONT_FAMILY, FONT_SIZE_LARGE, "bold"), text_color=TEXT_WHITE,
        ).grid(row=0, column=0, columnspan=4, sticky=anchor("w"), padx=15, pady=(10, 5))

        ctk.CTkLabel(
            form, text=_("network.name_placeholder"),
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_LIGHT,
        ).grid(row=1, column=0, sticky=anchor("w"), padx=15, pady=3)
        self._add_name_entry = ctk.CTkEntry(form, width=150, corner_radius=0)
        self._add_name_entry.grid(row=1, column=1, sticky=anchor("w"), padx=5, pady=3)

        ctk.CTkLabel(
            form, text=_("network.ip_placeholder"),
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_LIGHT,
        ).grid(row=1, column=2, sticky=anchor("w"), padx=(15, 0), pady=3)
        self._add_ip_entry = ctk.CTkEntry(form, width=150, corner_radius=0)
        self._add_ip_entry.grid(row=1, column=3, sticky=anchor("w"), padx=5, pady=3)

        ctk.CTkButton(
            form, text=_("network.add_btn"),
            command=self._add_teacher,
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).grid(row=2, column=0, columnspan=4, sticky=anchor("w"), padx=15, pady=(5, 10))

    # ── Actions ────────────────────────────────────────────────────────

    def _toggle_server(self):
        if self._server.is_running:
            self._server.stop()
            self._start_btn.configure(text=_("network.start"))
        else:
            try:
                port = int(self._port_entry.get().strip())
            except ValueError:
                messagebox.showerror(_("dialog.error"), _("network.invalid_port"))
                return
            pwd = self._pwd_entry.get().strip()
            self._server.set_password(pwd)
            cfg = get_cfg()
            cfg["admin_port"] = port
            cfg["network_password"] = pwd
            save_cfg(cfg)
            self._server.start(port=port)
            self._start_btn.configure(text=_("network.stop"))
        self._update_status()

    def _update_status(self):
        if self._server.is_running:
            port = self._port_entry.get().strip()
            self._status_label.configure(
                text=_("network.running", port=port),
                text_color=SUCCESS,
            )
        else:
            self._status_label.configure(
                text=_("network.stopped"),
                text_color=DANGER,
            )

    def _copy_ip(self, ip: str):
        self.frame.clipboard_clear()
        self.frame.clipboard_append(ip)
        self._ip_status_label.configure(text=_("network.ip_copied"))
        self.frame.after(2000, lambda: self._ip_status_label.configure(text=""))

    def _add_teacher(self):
        name = self._add_name_entry.get().strip()
        ip = self._add_ip_entry.get().strip()
        if not name or not ip:
            messagebox.showerror(_("dialog.error"), _("network.fields_required"))
            return
        cfg = get_cfg()
        teachers = cfg.setdefault("teachers", [])
        if any(t["name"] == name for t in teachers):
            messagebox.showerror(_("dialog.error"), _("network.teacher_exists", name=name))
            return
        teachers.append({"name": name, "ip": ip})
        save_cfg(cfg)
        self._add_name_entry.delete(0, "end")
        self._add_ip_entry.delete(0, "end")
        self._rebuild_teacher_list()

    def _edit_teacher(self, name: str):
        cfg = get_cfg()
        teachers = cfg.get("teachers", [])
        t = next((t for t in teachers if t["name"] == name), None)
        if not t:
            return
        new_name = simpledialog.askstring(
            _("network.edit"), _("network.name_placeholder"),
            initialvalue=t["name"],
        )
        if not new_name or not new_name.strip():
            return
        new_ip = simpledialog.askstring(
            _("network.edit"), _("network.ip_placeholder"),
            initialvalue=t["ip"],
        )
        if not new_ip or not new_ip.strip():
            return
        t["name"] = new_name.strip()
        t["ip"] = new_ip.strip()
        save_cfg(cfg)
        self._rebuild_teacher_list()

    def _delete_teacher(self, name: str):
        if not messagebox.askyesno(
            _("dialog.confirm"),
            _("network.delete_confirm", name=name),
        ):
            return
        cfg = get_cfg()
        teachers = cfg.get("teachers", [])
        cfg["teachers"] = [t for t in teachers if t["name"] != name]
        save_cfg(cfg)
        self._rebuild_teacher_list()

    # ── Auto-refresh ───────────────────────────────────────────────────

    def _start_auto_refresh(self):
        self._cancel_refresh()
        self._poll()

    def _poll(self):
        self._rebuild_teacher_list()
        self._refresh_id = self.frame.after(5000, self._poll)

    def _cancel_refresh(self):
        if self._refresh_id:
            try:
                self.frame.after_cancel(self._refresh_id)
            except Exception:
                pass
            self._refresh_id = None

    # ── Guide ──────────────────────────────────────────────────────────

    def _show_guide(self):
        win = ctk.CTkToplevel(self.frame)
        win.title(_("network.guide_title"))
        win.geometry("650x550")
        win.configure(fg_color=BG_DARK)
        text = ctk.CTkTextbox(win, wrap="word", fg_color=BG_INPUT,
                              text_color=TEXT_WHITE, corner_radius=0,
                              font=(FONT_FAMILY, FONT_SIZE_NORMAL),
                              border_width=1, border_color=BORDER_COLOR)
        text.pack(fill="both", expand=True, padx=15, pady=15)
        text.insert("1.0", _("network.guide_text"))
        text.configure(state="disabled")
        ctk.CTkButton(
            win, text=_("dialog.close"),
            command=win.destroy,
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(pady=(0, 15))

    # ── Scroll fix ─────────────────────────────────────────────────────

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
