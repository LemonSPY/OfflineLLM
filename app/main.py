"""OfflineLLM entry point."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import customtkinter as ctk

from ui.main_window import MainWindow


def main() -> None:
    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")

    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
