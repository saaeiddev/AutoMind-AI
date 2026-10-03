from __future__ import annotations

import tkinter as tk
from collections import deque
from tkinter import ttk

from ui.theme import COLORS, FONT, FONT_SEMIBOLD


class PolygonButton(tk.Canvas):
    """Cut-corner automotive button with ttk.Button-like construction semantics."""

    def __init__(self, parent, text: str = "", command=None, style: str = "TButton", **kwargs) -> None:
        self.command = command
        self.text = text
        self.style_name = style or "TButton"
        self._enabled = True
        self._hover = False
        self._pressed = False

        nav = self.style_name == "Nav.TButton"
        width = kwargs.pop("width", 176 if nav else 150)
        height = kwargs.pop("height", 42 if nav else 38)
        super().__init__(
            parent,
            width=width,
            height=height,
            bd=0,
            highlightthickness=0,
            relief="flat",
            cursor="hand2",
            background=self._parent_bg(parent),
        )
        self._cut = 11 if nav else 9
        self._anchor = "w" if nav else "center"
        self._pad_x = 17 if nav else 0
        self.bind("<Configure>", lambda _e: self._draw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<space>", lambda _e: self.invoke())
        self.bind("<Return>", lambda _e: self.invoke())
        self._draw()

    @staticmethod
    def _parent_bg(parent) -> str:
        try:
            return parent.cget("background")
        except Exception:
            return COLORS["bg"]

    def _palette(self) -> tuple[str, str, str, str]:
        if self.style_name == "Accent.TButton":
            return COLORS["accent"], COLORS["black"], COLORS["accent2"], "#D96200"
        if self.style_name == "Danger.TButton":
            return "#B52A2A", COLORS["white"], "#D83A3A", "#8F2020"
        if self.style_name == "Nav.TButton":
            return COLORS["panel"], COLORS["muted"], COLORS["surface"], "#2D2D2D"
        return COLORS["surface"], COLORS["text"], "#303030", "#181818"

    def _draw(self) -> None:
        self.delete("all")
        w=max(self.winfo_width(), int(float(self.cget("width"))))
        h=max(self.winfo_height(), int(float(self.cget("height"))))
        cut=min(self._cut, h//3, w//5)
        normal, fg, hover, pressed=self._palette()
        fill=pressed if self._pressed else hover if self._hover else normal
        if not self._enabled:
            fill="#1B1B1B"; fg="#666666"
        pts=[0,cut,cut,0,w-cut,0,w,cut,w,h-cut,w-cut,h,cut,h,0,h-cut]
        self.create_polygon(pts, fill=fill, outline=COLORS["border"], width=1)
        if self.style_name == "Accent.TButton":
            self.create_line(cut+2, h-3, w-cut-2, h-3, fill="#FFD0A3", width=2)
        if self.style_name == "Nav.TButton" and self._hover:
            self.create_polygon([0,cut,5,5,5,h-5,0,h-cut], fill=COLORS["accent"], outline="")
        x=self._pad_x if self._anchor=="w" else w/2
        self.create_text(x,h/2,text=self.text,anchor=self._anchor,fill=fg,font=(FONT_SEMIBOLD,10))

    def _on_enter(self, _event=None) -> None:
        if self._enabled:
            self._hover=True
            self._draw()

    def _on_leave(self, _event=None) -> None:
        self._hover=False
        self._pressed=False
        self._draw()

    def _on_press(self, _event=None) -> None:
        if self._enabled:
            self._pressed=True
            self.focus_set()
            self._draw()

    def _on_release(self, event=None) -> None:
        was_pressed=self._pressed
        self._pressed=False
        inside=True
        if event is not None:
            inside=0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height()
        self._draw()
        if was_pressed and inside:
            self.invoke()

    def invoke(self):
        if self._enabled and callable(self.command):
            return self.command()
        return None

    def configure(self, cnf=None, **kwargs):
        if cnf:
            kwargs.update(cnf)
        if "text" in kwargs:
            self.text=kwargs.pop("text")
        if "command" in kwargs:
            self.command=kwargs.pop("command")
        if "state" in kwargs:
            self._enabled=kwargs.pop("state") not in ("disabled", tk.DISABLED)
        if "style" in kwargs:
            self.style_name=kwargs.pop("style")
        result=super().configure(**kwargs) if kwargs else None
        self._draw()
        return result

    config=configure

    def state(self, statespec=None):
        if statespec is None:
            return ("!disabled",) if self._enabled else ("disabled",)
        for state in statespec:
            if state == "disabled":
                self._enabled=False
            elif state == "!disabled":
                self._enabled=True
        self._draw()
        return self.state()


class MetricCard(ttk.Frame):
    def __init__(self, parent, title: str, value: str = "--", subtitle: str = "") -> None:
        super().__init__(parent, style="Panel.TFrame", padding=16)
        self.columnconfigure(0, weight=1)
        ttk.Label(self, text=title, style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.value_var=tk.StringVar(value=value)
        ttk.Label(self, textvariable=self.value_var, style="Metric.TLabel").grid(row=1, column=0, sticky="w", pady=(7,2))
        self.subtitle_var=tk.StringVar(value=subtitle)
        ttk.Label(self, textvariable=self.subtitle_var, style="PanelMuted.TLabel", wraplength=220).grid(row=2,column=0,sticky="w")

    def set(self, value: str, subtitle: str | None = None) -> None:
        self.value_var.set(value)
        if subtitle is not None:
            self.subtitle_var.set(subtitle)


class StatusPill(tk.Label):
    def __init__(self, parent, text: str = "Offline", kind: str = "muted") -> None:
        super().__init__(parent, text=text, font=(FONT_SEMIBOLD,9), padx=10, pady=5, bd=0)
        self.set(text, kind)

    def set(self, text: str, kind: str = "muted") -> None:
        palette={
            "success":("#102514", COLORS["success"]),
            "warning":("#3A2208", COLORS["warning"]),
            "danger":("#351010", "#FF8585"),
            "info":("#3A1D05", COLORS["accent2"]),
            "muted":(COLORS["surface"], COLORS["muted"]),
        }
        bg,fg=palette.get(kind,palette["muted"])
        self.configure(text=text,background=bg,foreground=fg)


class LiveChart(tk.Canvas):
    def __init__(self, parent, max_points: int = 120, **kwargs) -> None:
        super().__init__(parent, background=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["border"], **kwargs)
        self.max_points=max_points
        self.series: dict[str, deque[float]]={}
        self.units: dict[str,str]={}
        self.palette=["#FF7A00","#FFFFFF","#FFB347","#C9C9C9","#FF4D4D","#7EE787"]
        self.legend_aliases={
            "Engine RPM":"RPM",
            "Engine Coolant Temperature":"Coolant",
            "Control Module Voltage":"Module Voltage",
            "Short-Term Fuel Trim Bank 1":"STFT B1",
            "Long-Term Fuel Trim Bank 1":"LTFT B1",
            "MAF Air Flow Rate":"MAF",
            "Throttle Position":"Throttle",
            "Calculated Engine Load":"Engine Load",
            "Vehicle Speed":"Speed",
        }
        self.bind("<Configure>", lambda _e:self.redraw())

    def add_values(self, values: dict[str,tuple[float,str]]) -> None:
        for name,(value,unit) in values.items():
            self.series.setdefault(name,deque(maxlen=self.max_points)).append(float(value))
            self.units[name]=unit
        self.redraw()

    def reset(self) -> None:
        self.series.clear(); self.units.clear(); self.redraw()

    def redraw(self) -> None:
        self.delete("all")
        width=max(self.winfo_width(),300); height=max(self.winfo_height(),220)
        ml,mr,mt,mb=55,20,32,64
        pw=width-ml-mr; ph=height-mt-mb
        nonempty=[(name,series) for name,series in self.series.items() if series]
        unit_set={self.units.get(name,"") for name,_ in nonempty}
        normalized=len(unit_set)>1
        title="Live PID Trend - normalized per series" if normalized else "Live PID Trend"
        self.create_text(16,16,anchor="w",text=title,fill=COLORS["accent2"],font=(FONT_SEMIBOLD,11))
        if not self.series or not any(self.series.values()):
            self.create_text(width/2,height/2,text="Select PIDs to begin charting",fill=COLORS["muted"],font=(FONT,10))
            return
        all_values=[v for _,series in nonempty for v in series]
        low,high=min(all_values),max(all_values)
        if not normalized:
            if abs(high-low)<1e-9: high,low=high+1,low-1
            pad=(high-low)*0.12; low-=pad; high+=pad
        for i in range(5):
            y=mt+ph*i/4
            label=f"{100-i*25}%" if normalized else f"{high-(high-low)*i/4:.1f}"
            self.create_line(ml,y,width-mr,y,fill="#2A2A2A")
            self.create_text(ml-8,y,anchor="e",text=label,fill=COLORS["muted"],font=(FONT,8))
        legend_x=ml; legend_y=height-42
        for idx,(name,series) in enumerate(self.series.items()):
            if not series: continue
            color=self.palette[idx%len(self.palette)]
            points=[]; n=max(2,self.max_points-1)
            slo,shi=min(series),max(series)
            if abs(shi-slo)<1e-9: shi,slo=shi+1,slo-1
            for i,value in enumerate(series):
                x=ml+pw*i/n
                y=mt+ph*((shi-value)/(shi-slo) if normalized else (high-value)/(high-low))
                points.extend([x,y])
            if len(points)>=4:
                self.create_line(*points,fill=color,width=2,smooth=True)
            short=self.legend_aliases.get(name,name)
            label=f"{short} ({self.units.get(name,'')})"
            if len(label)>30: label=label[:27]+"..."
            item_width=min(195,40+len(label)*5)
            if legend_x+item_width>width-mr and legend_x>ml:
                legend_x=ml; legend_y+=18
            self.create_rectangle(legend_x,legend_y-5,legend_x+10,legend_y+5,fill=color,outline="")
            self.create_text(legend_x+14,legend_y,anchor="w",text=label,fill=COLORS["muted"],font=(FONT,8))
            legend_x+=item_width
