import sys
import customtkinter as ctk
from app.i18n.translator import _, set_language, get_language, anchor
from app.repositories.database import init_db, is_initialized, get_cfg
from app.services.grade_service import seed_matieres
from app.ui.theme import *
from app.ui.views.dashboard_view import DashboardView
from app.ui.views.classes_view import ClassesView
from app.ui.views.students_view import StudentsView
from app.ui.views.export_view import ExportView
from app.ui.views.logs_view import LogsView
from app.ui.views.config_view import ConfigView
from app.ui.views.subjects_view import SubjectsView
from app.ui.views.grades_view import GradesView
from app.ui.views.assignments_view import AssignmentsView
from app.ui.views.network_view import NetworkView


class MainWindow:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("mainpixel — gestion scolaire")
        try:
            self.root.state("zoomed")
        except Exception:
            self.root.geometry("1200x800")
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.root.configure(fg_color=BG_DARK)

        self.views = {}
        self.current_view = None
        self.current_class_id = None
        self.students_view = None

        self._build_layout()
        init_db()
        seed_matieres()
        self.show_view("stats")

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_layout(self):
        self.root.grid_columnconfigure(0, weight=0)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self.root, width=200, fg_color=BG_CARD, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)
        border = ctk.CTkFrame(self.root, width=1, fg_color=BORDER_COLOR, corner_radius=0)
        border.grid(row=0, column=0, sticky="ns", padx=(199, 0))

        ctk.CTkLabel(
            self.sidebar, text="mainpixel",
            font=(FONT_FAMILY, 20, "bold"), text_color=TEXT_WHITE
        ).pack(pady=(15, 5))
        ctk.CTkLabel(
            self.sidebar, text=_("app.subtitle"),
            font=(FONT_FAMILY, 10), text_color=TEXT_LIGHT
        ).pack(pady=(0, 15))

        sep = ctk.CTkFrame(self.sidebar, height=1, fg_color=BORDER_COLOR)
        sep.pack(fill="x", padx=10, pady=5)

        nav_items = [
            ("stats", _("nav.stats")),
            ("classes", _("nav.classes")),
            ("subjects", _("nav.subjects")),
            ("assignments", _("nav.assignments")),
            ("grades", _("nav.grades")),
            ("export", _("nav.export")),
            ("logs", _("nav.logs")),
            ("network", _("nav.network")),
            ("config", _("nav.config")),
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

        lang_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        lang_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(lang_frame, text="Langue:", font=(FONT_FAMILY, 10), text_color=TEXT_LIGHT).pack(anchor=anchor("w"))
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
        self.show_view("stats")

    def show_view(self, view_name):
        self.clear_main()
        if self.current_view and self.current_view in self.views:
            v = self.views[self.current_view]
            if hasattr(v, "destroy"):
                v.destroy()

        if view_name not in self.views:
            if view_name == "stats":
                self.views["stats"] = DashboardView(self.main, self)
            elif view_name == "classes":
                self.views["classes"] = ClassesView(self.main, self)
            elif view_name == "students":
                sv = StudentsView(self.main, self)
                if self.current_class_id:
                    sv.class_id = self.current_class_id
                    sv.class_name = "Classe"
                self.views["students"] = sv
            elif view_name == "export":
                self.views["export"] = ExportView(self.main, self)
            elif view_name == "logs":
                self.views["logs"] = LogsView(self.main, self)
            elif view_name == "config":
                self.views["config"] = ConfigView(self.main, self)
            elif view_name == "subjects":
                self.views["subjects"] = SubjectsView(self.main, self)
            elif view_name == "grades":
                self.views["grades"] = GradesView(self.main, self)
            elif view_name == "assignments":
                self.views["assignments"] = AssignmentsView(self.main, self)
            elif view_name == "network":
                self.views["network"] = NetworkView(self.main, self)

        self.current_view = view_name
        v = self.views.get(view_name)
        if v:
            v.build()

    def open_class(self, class_id):
        from app.services.class_service import get_class_name
        name = get_class_name(class_id) or "Classe"
        self.current_class_id = class_id

        if "students" in self.views:
            self.views["students"].destroy()
            del self.views["students"]

        sv = StudentsView(self.main, self)
        sv.class_id = class_id
        sv.class_name = name
        self.views["students"] = sv
        self.show_view("students")

    def run(self):
        self.root.mainloop()

    def _on_close(self):
        self.root.destroy()
