"""Teacher app main window — simplified sidebar with only relevant views."""
import sys
import customtkinter as ctk
from app.i18n.translator import _, set_language, get_language, anchor
from app.ui.theme import *
from app.ui.views.connect_view import ConnectView
from app.ui.views.assignments_view import AssignmentsView


class MainWindow:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title(_("app.title"))
        try:
            self.root.state("zoomed")
        except Exception:
            self.root.geometry("1000x700")
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.root.configure(fg_color=BG_DARK)

        self.views = {}
        self.current_view = None
        self.client = None  # RegistryClient instance, set after connect

        self._build_layout()
        self.show_view("connect")

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_layout(self):
        self.root.grid_columnconfigure(0, weight=0)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self.root, width=180, fg_color=BG_CARD, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)
        border = ctk.CTkFrame(self.root, width=1, fg_color=BORDER_COLOR, corner_radius=0)
        border.grid(row=0, column=0, sticky="ns", padx=(179, 0))

        ctk.CTkLabel(
            self.sidebar, text="mainpixel",
            font=(FONT_FAMILY, 18, "bold"), text_color=TEXT_WHITE
        ).pack(pady=(15, 2))
        ctk.CTkLabel(
            self.sidebar, text=_("app.subtitle"),
            font=(FONT_FAMILY, 10), text_color=TEXT_LIGHT
        ).pack(pady=(0, 15))

        sep = ctk.CTkFrame(self.sidebar, height=1, fg_color=BORDER_COLOR)
        sep.pack(fill="x", padx=10, pady=5)

        nav_items = [
            ("connect", _("nav.connect")),
            ("assignments", _("nav.assignments")),
        ]
        for vid, vlabel in nav_items:
            btn = ctk.CTkButton(
                self.sidebar, text=vlabel,
                command=lambda v=vid: self.show_view(v),
                fg_color="transparent", text_color=TEXT_WHITE,
                hover_color="#ebebeb", anchor=anchor("w"),
                corner_radius=0, border_width=0,
            )
            btn.pack(fill="x", padx=10, pady=2)

        sep2 = ctk.CTkFrame(self.sidebar, height=1, fg_color=BORDER_COLOR)
        sep2.pack(fill="x", padx=10, pady=10)

        # Guide button
        ctk.CTkButton(
            self.sidebar, text=_("nav.guide"),
            command=self._show_guide,
            fg_color="transparent", text_color=TEXT_LIGHT,
            hover_color="#ebebeb", anchor=anchor("w"),
            corner_radius=0, border_width=0,
        ).pack(fill="x", padx=10, pady=2)

        lang_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        lang_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(
            lang_frame, text="Langue:", font=(FONT_FAMILY, 10), text_color=TEXT_LIGHT
        ).pack(anchor=anchor("w"))
        self.lang_var = ctk.StringVar(value=get_language())
        lang_menu = ctk.CTkOptionMenu(
            lang_frame, values=["fr", "en", "ar"],
            variable=self.lang_var,
            command=self._change_lang,
            fg_color="#f5f5f5", button_color="#e0e0e0",
            text_color="#000000", dropdown_fg_color="#ffffff",
            dropdown_text_color="#000000", dropdown_hover_color="#ebebeb",
            corner_radius=0,
        )
        lang_menu.pack(fill="x", pady=2)

    def _build_main(self):
        self.main = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(0, weight=1)

    def _change_lang(self, lang):
        set_language(lang)
        self.root.after(100, self._rebuild_all)

    def clear_main(self):
        for w in self.main.winfo_children():
            w.destroy()

    def _rebuild_all(self):
        self.root.title(_("app.title"))
        for w in self.sidebar.winfo_children():
            w.destroy()
        self._build_sidebar()
        self.clear_main()
        self.current_view = None
        self.views = {}
        self.show_view("connect")

    def show_view(self, view_name):
        self.clear_main()
        if self.current_view and self.current_view in self.views:
            v = self.views[self.current_view]
            if hasattr(v, "destroy"):
                v.destroy()

        if view_name not in self.views:
            if view_name == "connect":
                self.views["connect"] = ConnectView(self.main, self)
            elif view_name == "assignments":
                self.views["assignments"] = AssignmentsView(self.main, self)

        self.current_view = view_name
        v = self.views.get(view_name)
        if v:
            v.build()

    def set_client(self, client):
        self.client = client
        # Rebuild assignments view if it exists so it uses the new client
        if "assignments" in self.views:
            self.views["assignments"].destroy()
            del self.views["assignments"]

    def _show_guide(self):
        win = ctk.CTkToplevel(self.root)
        win.title(_("guide.title"))
        win.geometry("550x500")
        win.configure(fg_color=BG_DARK)
        text = ctk.CTkTextbox(win, wrap="word", fg_color=BG_INPUT,
                              text_color=TEXT_WHITE, corner_radius=0,
                              font=(FONT_FAMILY, FONT_SIZE_NORMAL),
                              border_width=1, border_color=BORDER_COLOR)
        text.pack(fill="both", expand=True, padx=15, pady=15)
        text.insert("1.0", _("guide.text"))
        text.configure(state="disabled")
        ctk.CTkButton(
            win, text=_("dialog.close"),
            command=win.destroy,
            fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=TEXT_WHITE,
            corner_radius=0, border_width=1, border_color=BTN_BORDER,
        ).pack(pady=(0, 15))

    def run(self):
        self.root.mainloop()

    def _on_close(self):
        self.root.destroy()
