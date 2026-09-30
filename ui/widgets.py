from __future__ import annotations

import tkinter as tk
from collections import deque
from tkinter import ttk
from typing import Iterable

from ui.theme import COLORS


class MetricCard(ttk.Frame):
    def __init__(self, parent, title: str, value: str = "--", subtitle: str = "") -> None:
        super().__init__(parent, style="Panel.TFrame", padding=16)
        self.columnconfigure(0, weight=1)
        ttk.Label(self, text=title, style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.value_var = tk.StringVar(value=value)
        ttk.Label(self, textvariable=self.value_var, style="Metric.TLabel").grid(row=1, column=0, sticky="w", pady=(7, 2))
        self.subtitle_var = tk.StringVar(value=subtitle)
        ttk.Label(self, textvariable=self.subtitle_var, style="PanelMuted.TLabel", wraplength=220).grid(row=2, column=0, sticky="w")

    def set(self, value: str, subtitle: str | None = None) -> None:
        self.value_var.set(value)
        if subtitle is not None:
            self.subtitle_var.set(subtitle)


class StatusPill(tk.Label):
    def __init__(self, parent, text: str = "Offline", kind: str = "muted") -> None:
        super().__init__(parent, text=text, font=("Segoe UI Semibold", 9), padx=10, pady=5, bd=0)
        self.set(text, kind)

    def set(self, text: str, kind: str = "muted") -> None:
        palette = {
            "success": ("#063C32", COLORS["success"]),
            "warning": ("#3A2A08", "#FCD34D"),
            "danger": ("#43111C", "#FDA4AF"),
            "info": ("#0C3348", "#7DD3FC"),
            "muted": (COLORS["surface"], COLORS["muted"]),
        }
        bg, fg = palette.get(kind, palette["muted"])
        self.configure(text=text, background=bg, foreground=fg)


class LiveChart(tk.Canvas):
    def __init__(self, parent, max_points: int = 120, **kwargs) -> None:
        super().__init__(parent, background=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["border"], **kwargs)
        self.max_points = max_points
        self.series: dict[str, deque[float]] = {}
        self.units: dict[str, str] = {}
        self.palette = ["#2DD4BF", "#38BDF8", "#F59E0B", "#A78BFA", "#FB7185", "#A3E635"]
        self.legend_aliases = {
            "Engine RPM": "RPM",
            "Engine Coolant Temperature": "Coolant",
            "Control Module Voltage": "Module Voltage",
            "Short-Term Fuel Trim Bank 1": "STFT B1",
            "Long-Term Fuel Trim Bank 1": "LTFT B1",
            "MAF Air Flow Rate": "MAF",
            "Throttle Position": "Throttle",
            "Calculated Engine Load": "Engine Load",
            "Vehicle Speed": "Speed",
        }
        self.bind("<Configure>", lambda _e: self.redraw())

    def add_values(self, values: dict[str, tuple[float, str]]) -> None:
        for name, (value, unit) in values.items():
            self.series.setdefault(name, deque(maxlen=self.max_points)).append(float(value))
            self.units[name] = unit
        self.redraw()

    def reset(self) -> None:
        self.series.clear()
        self.units.clear()
        self.redraw()

    def redraw(self) -> None:
        self.delete("all")
        width = max(self.winfo_width(), 300)
        height = max(self.winfo_height(), 220)
        margin_left, margin_right, margin_top, margin_bottom = 55, 20, 32, 64
        plot_w = width - margin_left - margin_right
        plot_h = height - margin_top - margin_bottom
        nonempty = [(name, series) for name, series in self.series.items() if series]
        unit_set = {self.units.get(name, "") for name, _ in nonempty}
        normalized = len(unit_set) > 1
        title = "Live PID Trend - normalized per series" if normalized else "Live PID Trend"
        self.create_text(16, 16, anchor="w", text=title, fill=COLORS["text"], font=("Segoe UI Semibold", 11))
        if not self.series or not any(self.series.values()):
            self.create_text(width/2, height/2, text="Select PIDs to begin charting", fill=COLORS["muted"], font=("Segoe UI", 10))
            return

        all_values = [v for _, series in nonempty for v in series]
        low, high = min(all_values), max(all_values)
        if not normalized:
            if abs(high - low) < 1e-9:
                high, low = high + 1, low - 1
            pad = (high - low) * 0.12
            low -= pad; high += pad

        for i in range(5):
            y = margin_top + plot_h * i / 4
            if normalized:
                label = f"{100 - i * 25}%"
            else:
                val = high - (high - low) * i / 4
                label = f"{val:.1f}"
            self.create_line(margin_left, y, width - margin_right, y, fill="#223047")
            self.create_text(margin_left - 8, y, anchor="e", text=label, fill=COLORS["muted"], font=("Segoe UI", 8))

        legend_x = margin_left
        legend_y = height - 42
        for idx, (name, series) in enumerate(self.series.items()):
            if not series:
                continue
            color = self.palette[idx % len(self.palette)]
            points: list[float] = []
            n = max(2, self.max_points - 1)
            series_low, series_high = min(series), max(series)
            if abs(series_high - series_low) < 1e-9:
                series_high, series_low = series_high + 1, series_low - 1
            for i, value in enumerate(series):
                x = margin_left + plot_w * i / n
                if normalized:
                    y = margin_top + plot_h * (series_high - value) / (series_high - series_low)
                else:
                    y = margin_top + plot_h * (high - value) / (high - low)
                points.extend([x, y])
            if len(points) >= 4:
                self.create_line(*points, fill=color, width=2, smooth=True)
            short_name = self.legend_aliases.get(name, name)
            label = f"{short_name} ({self.units.get(name,'')})"
            if len(label) > 30:
                label = label[:27] + "..."
            item_width = min(195, 40 + len(label) * 5)
            if legend_x + item_width > width - margin_right and legend_x > margin_left:
                legend_x = margin_left
                legend_y += 18
            self.create_rectangle(legend_x, legend_y-5, legend_x+10, legend_y+5, fill=color, outline="")
            self.create_text(legend_x+14, legend_y, anchor="w", text=label, fill=COLORS["muted"], font=("Segoe UI", 8))
            legend_x += item_width
