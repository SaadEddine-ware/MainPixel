#!/usr/bin/env python3
"""mainpixel — Teacher Assignment App"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import customtkinter as ctk
try:
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
except Exception:
    pass

from app.ui.views.main_window import MainWindow


def main():
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()
