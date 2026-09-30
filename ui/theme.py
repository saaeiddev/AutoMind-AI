from __future__ import annotations

import tkinter as tk
from tkinter import ttk


COLORS = {
    "bg": "#0B1220",
    "panel": "#111827",
    "panel2": "#172033",
    "surface": "#1E293B",
    "border": "#2B3A52",
    "text": "#E5EEF8",
    "muted": "#8EA0B8",
    "accent": "#2DD4BF",
    "accent2": "#38BDF8",
    "warning": "#F59E0B",
    "danger": "#FB7185",
    "success": "#34D399",
    "white": "#FFFFFF",
}


def apply_theme(root: tk.Tk) -> ttk.Style:
    root.configure(bg=COLORS["bg"])
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", background=COLORS["bg"], foreground=COLORS["text"], font=("Segoe UI", 10))
    style.configure("TFrame", background=COLORS["bg"])
    style.configure("Panel.TFrame", background=COLORS["panel"])
    style.configure("Surface.TFrame", background=COLORS["surface"])
    style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"])
    style.configure("Panel.TLabel", background=COLORS["panel"], foreground=COLORS["text"])
    style.configure("Muted.TLabel", background=COLORS["bg"], foreground=COLORS["muted"])
    style.configure("PanelMuted.TLabel", background=COLORS["panel"], foreground=COLORS["muted"])
    style.configure("Title.TLabel", font=("Segoe UI Semibold", 20), foreground=COLORS["white"])
    style.configure("Section.TLabel", font=("Segoe UI Semibold", 13), foreground=COLORS["white"])
    style.configure("Metric.TLabel", font=("Segoe UI Semibold", 22), foreground=COLORS["white"], background=COLORS["panel"])
    style.configure("CardTitle.TLabel", font=("Segoe UI Semibold", 10), foreground=COLORS["muted"], background=COLORS["panel"])

    style.configure("TButton", background=COLORS["surface"], foreground=COLORS["text"], borderwidth=0, padding=(12, 8))
    style.map("TButton", background=[("active", COLORS["panel2"]), ("pressed", COLORS["border"])])
    style.configure("Accent.TButton", background=COLORS["accent"], foreground="#041816", font=("Segoe UI Semibold", 10), padding=(14, 9))
    style.map("Accent.TButton", background=[("active", "#5EEAD4"), ("pressed", "#14B8A6")])
    style.configure("Danger.TButton", background=COLORS["danger"], foreground="#2A0710")
    style.configure("Nav.TButton", background=COLORS["panel"], foreground=COLORS["muted"], anchor="w", padding=(18, 11))
    style.map("Nav.TButton", background=[("active", COLORS["surface"])], foreground=[("active", COLORS["white"])])

    style.configure("TEntry", fieldbackground=COLORS["surface"], foreground=COLORS["text"], insertcolor=COLORS["white"], bordercolor=COLORS["border"], padding=7)
    style.configure("TCombobox", fieldbackground=COLORS["surface"], background=COLORS["surface"], foreground=COLORS["text"], arrowcolor=COLORS["text"], padding=6)
    style.map("TCombobox", fieldbackground=[("readonly", COLORS["surface"])], foreground=[("readonly", COLORS["text"])])
    style.configure("TCheckbutton", background=COLORS["bg"], foreground=COLORS["text"])
    style.configure("Panel.TCheckbutton", background=COLORS["panel"], foreground=COLORS["text"])

    style.configure("Treeview", background=COLORS["panel"], fieldbackground=COLORS["panel"], foreground=COLORS["text"], bordercolor=COLORS["border"], rowheight=28)
    style.configure("Treeview.Heading", background=COLORS["surface"], foreground=COLORS["text"], relief="flat", font=("Segoe UI Semibold", 9))
    style.map("Treeview", background=[("selected", "#134E4A")], foreground=[("selected", COLORS["white"])])
    style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
    style.configure("TNotebook.Tab", background=COLORS["surface"], foreground=COLORS["muted"], padding=(13, 8))
    style.map("TNotebook.Tab", background=[("selected", COLORS["panel"])], foreground=[("selected", COLORS["white"])])
    style.configure("TSeparator", background=COLORS["border"])
    return style
