from __future__ import annotations

import tkinter as tk
from tkinter import ttk

# AutoMind AI 0.2 — industrial automotive palette
COLORS = {
    "bg": "#080808",
    "panel": "#111111",
    "panel2": "#191919",
    "surface": "#222222",
    "surface2": "#2A2A2A",
    "border": "#3A3A3A",
    "text": "#F7F7F7",
    "muted": "#A6A6A6",
    "accent": "#FF7A00",
    "accent2": "#FF9A32",
    "warning": "#FFB347",
    "danger": "#FF4D4D",
    "success": "#7EE787",
    "white": "#FFFFFF",
    "black": "#050505",
}

FONT = "Bahnschrift"
FONT_SEMIBOLD = "Bahnschrift SemiBold"


def apply_theme(root: tk.Tk) -> ttk.Style:
    root.configure(bg=COLORS["bg"])
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", background=COLORS["bg"], foreground=COLORS["text"], font=(FONT, 10))
    style.configure("TFrame", background=COLORS["bg"])
    style.configure("Panel.TFrame", background=COLORS["panel"])
    style.configure("Surface.TFrame", background=COLORS["surface"])

    style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"])
    style.configure("Panel.TLabel", background=COLORS["panel"], foreground=COLORS["text"])
    style.configure("Muted.TLabel", background=COLORS["bg"], foreground=COLORS["muted"])
    style.configure("PanelMuted.TLabel", background=COLORS["panel"], foreground=COLORS["muted"])
    style.configure("Title.TLabel", font=(FONT_SEMIBOLD, 22), foreground=COLORS["white"])
    style.configure("Section.TLabel", font=(FONT_SEMIBOLD, 13), foreground=COLORS["white"])
    style.configure("Metric.TLabel", font=(FONT_SEMIBOLD, 23), foreground=COLORS["white"], background=COLORS["panel"])
    style.configure("CardTitle.TLabel", font=(FONT_SEMIBOLD, 10), foreground=COLORS["accent2"], background=COLORS["panel"])

    # Fallback button styles. Main UI buttons use PolygonButton for the cut-corner shape.
    style.configure("TButton", background=COLORS["surface"], foreground=COLORS["text"], borderwidth=0, padding=(12, 8), font=(FONT_SEMIBOLD, 10))
    style.map("TButton", background=[("active", COLORS["surface2"]), ("pressed", COLORS["border"])])
    style.configure("Accent.TButton", background=COLORS["accent"], foreground=COLORS["black"], font=(FONT_SEMIBOLD, 10), padding=(14, 9))
    style.configure("Danger.TButton", background=COLORS["danger"], foreground=COLORS["white"])
    style.configure("Nav.TButton", background=COLORS["panel"], foreground=COLORS["muted"], anchor="w", padding=(18, 11))

    style.configure("TEntry", fieldbackground=COLORS["surface"], foreground=COLORS["text"], insertcolor=COLORS["accent"], bordercolor=COLORS["border"], padding=8)
    style.configure("TCombobox", fieldbackground=COLORS["surface"], background=COLORS["surface"], foreground=COLORS["text"], arrowcolor=COLORS["accent"], padding=7)
    style.map("TCombobox", fieldbackground=[("readonly", COLORS["surface"])], foreground=[("readonly", COLORS["text"])])
    style.configure("TCheckbutton", background=COLORS["bg"], foreground=COLORS["text"])
    style.configure("Panel.TCheckbutton", background=COLORS["panel"], foreground=COLORS["text"])

    style.configure("Treeview", background=COLORS["panel"], fieldbackground=COLORS["panel"], foreground=COLORS["text"], bordercolor=COLORS["border"], rowheight=30)
    style.configure("Treeview.Heading", background=COLORS["surface"], foreground=COLORS["accent2"], relief="flat", font=(FONT_SEMIBOLD, 9))
    style.map("Treeview", background=[("selected", "#6E3500")], foreground=[("selected", COLORS["white"])])

    style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
    style.configure("TNotebook.Tab", background=COLORS["surface"], foreground=COLORS["muted"], padding=(14, 9), font=(FONT_SEMIBOLD, 9))
    style.map("TNotebook.Tab", background=[("selected", COLORS["accent"])], foreground=[("selected", COLORS["black"])])

    style.configure("TSeparator", background=COLORS["border"])
    return style
