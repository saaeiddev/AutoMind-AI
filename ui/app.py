from __future__ import annotations

import logging
import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from ai.provider import AIProviderError
from app.controller import AutoMindController
from app.version import APP_NAME, PRODUCT_NAME
from core.paths import resource_path
from core.units import format_value
from simulator.scenarios import VehicleSimulator
from ui.theme import COLORS, apply_theme
from ui.widgets import LiveChart, MetricCard, PolygonButton, StatusPill
from vehicle.models import DiagnosticSession, VehicleProfile

log = logging.getLogger("automind.ui")


class AutoMindApplication(tk.Tk):
    NAV_ITEMS = [
        ("Dashboard", "dashboard"),
        ("Connect Vehicle", "connect"),
        ("Diagnostics", "diagnostics"),
        ("Trouble Codes", "dtc"),
        ("Live Data", "live"),
        ("AI Assistant", "ai"),
        ("Vehicle Profiles", "profiles"),
        ("Diagnostic History", "history"),
        ("Reports", "reports"),
        ("Settings", "settings"),
    ]

    def __init__(self, controller: AutoMindController) -> None:
        super().__init__()
        self.controller = controller
        self.title(PRODUCT_NAME)
        self.geometry("1460x900")
        self.minsize(960, 640)
        self.configure(bg=COLORS["bg"])
        try:
            if os.name == "nt":
                self.iconbitmap(str(resource_path("assets/automind.ico")))
            else:
                self._app_icon = tk.PhotoImage(file=str(resource_path("assets/automind.png")))
                self.iconphoto(True, self._app_icon)
        except Exception:
            pass
        apply_theme(self)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._live_paused = False
        self._live_fetch_inflight = False
        self._live_selected: list[str] = ["010C", "0105", "0142", "0106"]
        self._pages: dict[str, ttk.Frame] = {}
        self._status_after_id: str | None = None
        self._notes_session_id: str | None = None

        self._build_shell()
        self._build_pages()
        self.show_page("dashboard")
        self._refresh_everything()
        self.after(600, self._maybe_first_run)
        self.after(750, self._live_tick)

    def _build_shell(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        sidebar = ttk.Frame(self, style="Panel.TFrame", width=224)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        brand = ttk.Frame(sidebar, style="Panel.TFrame", padding=(18, 20))
        brand.grid(row=0, column=0, sticky="ew")
        tk.Label(brand, text="◈", bg=COLORS["panel"], fg=COLORS["accent"], font=("Segoe UI", 25)).pack(side="left")
        brand_text = ttk.Frame(brand, style="Panel.TFrame")
        brand_text.pack(side="left", padx=(9, 0))
        ttk.Label(brand_text, text="AutoMind AI", style="Panel.TLabel", font=("Segoe UI Semibold", 14)).pack(anchor="w")
        ttk.Label(brand_text, text="Automotive Diagnostics", style="PanelMuted.TLabel", font=("Segoe UI", 8)).pack(anchor="w")

        for idx, (label, key) in enumerate(self.NAV_ITEMS, start=1):
            PolygonButton(sidebar, text=label, style="Nav.TButton", command=lambda k=key: self.show_page(k)).grid(row=idx, column=0, sticky="ew", padx=8, pady=1)

        footer = ttk.Frame(sidebar, style="Panel.TFrame", padding=16)
        footer.grid(row=99, column=0, sticky="sew")
        sidebar.grid_rowconfigure(99, weight=1)
        ttk.Label(footer, text="READ-ONLY MVP", style="PanelMuted.TLabel", font=("Segoe UI Semibold", 8)).pack(anchor="w")
        ttk.Label(footer, text="No ECU flashing or arbitrary CAN writes", style="PanelMuted.TLabel", wraplength=185, font=("Segoe UI", 8)).pack(anchor="w", pady=(3, 0))

        main = ttk.Frame(self)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)
        top = ttk.Frame(main, padding=(22, 14))
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(0, weight=1)
        self.page_title = ttk.Label(top, text="Dashboard", style="Title.TLabel")
        self.page_title.grid(row=0, column=0, sticky="w")
        status_box = ttk.Frame(top)
        status_box.grid(row=0, column=1, sticky="e")
        self.vehicle_pill = StatusPill(status_box, "Vehicle Disconnected")
        self.vehicle_pill.pack(side="left", padx=4)
        self.adapter_pill = StatusPill(status_box, "Adapter Disconnected")
        self.adapter_pill.pack(side="left", padx=4)
        self.ai_pill = StatusPill(status_box, "AI Offline")
        self.ai_pill.pack(side="left", padx=4)

        self.page_host = ttk.Frame(main)
        self.page_host.grid(row=1, column=0, sticky="nsew", padx=22, pady=(0, 18))
        self.page_host.grid_rowconfigure(0, weight=1)
        self.page_host.grid_columnconfigure(0, weight=1)

    def _build_pages(self) -> None:
        builders = {
            "dashboard": self._build_dashboard,
            "connect": self._build_connect,
            "diagnostics": self._build_diagnostics,
            "dtc": self._build_dtc,
            "live": self._build_live,
            "ai": self._build_ai,
            "profiles": self._build_profiles,
            "history": self._build_history,
            "reports": self._build_reports,
            "settings": self._build_settings,
        }
        for key, builder in builders.items():
            frame = ttk.Frame(self.page_host)
            frame.grid(row=0, column=0, sticky="nsew")
            self._pages[key] = frame
            builder(frame)

    def show_page(self, key: str) -> None:
        self._pages[key].tkraise()
        label = next((name for name, k in self.NAV_ITEMS if k == key), key.title())
        self.page_title.configure(text=label)
        if key == "history": self._refresh_history()
        if key == "profiles": self._refresh_profiles()
        if key == "dtc": self._refresh_dtc_page()
        if key == "reports": self._refresh_reports()
        if key == "settings": self._load_settings_controls()

    # ---------- Dashboard ----------
    def _build_dashboard(self, page: ttk.Frame) -> None:
        page.grid_columnconfigure((0,1,2,3), weight=1, uniform="cards")
        page.grid_rowconfigure(3, weight=1)
        self.card_health = MetricCard(page, "Vehicle Health", "--", "Start a session to evaluate OBD data")
        self.card_health.grid(row=0, column=0, sticky="nsew", padx=(0,8), pady=(0,12))
        self.card_rpm = MetricCard(page, "Engine RPM", "--", "Unavailable")
        self.card_rpm.grid(row=0, column=1, sticky="nsew", padx=4, pady=(0,12))
        self.card_speed = MetricCard(page, "Vehicle Speed", "--", "Unavailable")
        self.card_speed.grid(row=0, column=2, sticky="nsew", padx=4, pady=(0,12))
        self.card_temp = MetricCard(page, "Coolant", "--", "Unavailable")
        self.card_temp.grid(row=0, column=3, sticky="nsew", padx=(8,0), pady=(0,12))

        self.card_voltage = MetricCard(page, "Module Voltage", "--", "Unavailable")
        self.card_voltage.grid(row=1, column=0, sticky="nsew", padx=(0,8), pady=(0,12))
        self.card_load = MetricCard(page, "Engine Load", "--", "Unavailable")
        self.card_load.grid(row=1, column=1, sticky="nsew", padx=4, pady=(0,12))
        self.card_fuel = MetricCard(page, "Fuel Level", "--", "Unavailable")
        self.card_fuel.grid(row=1, column=2, sticky="nsew", padx=4, pady=(0,12))
        self.card_trim = MetricCard(page, "Fuel Trim B1", "--", "Unavailable")
        self.card_trim.grid(row=1, column=3, sticky="nsew", padx=(8,0), pady=(0,12))

        overview = ttk.Frame(page, style="Panel.TFrame", padding=18)
        overview.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=(0,6), pady=(0,12))
        ttk.Label(overview, text="Current Vehicle", style="Panel.TLabel", font=("Segoe UI Semibold", 12)).pack(anchor="w")
        self.dashboard_vehicle = ttk.Label(overview, text="No vehicle session", style="PanelMuted.TLabel")
        self.dashboard_vehicle.pack(anchor="w", pady=(8,2))
        self.dashboard_vin = ttk.Label(overview, text="VIN: Unavailable", style="PanelMuted.TLabel")
        self.dashboard_vin.pack(anchor="w")
        self.dashboard_mode = ttk.Label(overview, text="Mode: Disconnected", style="PanelMuted.TLabel")
        self.dashboard_mode.pack(anchor="w", pady=(2,0))
        self.dashboard_engine = ttk.Label(overview, text="Engine: Unavailable", style="PanelMuted.TLabel")
        self.dashboard_engine.pack(anchor="w", pady=(2,0))

        faults = ttk.Frame(page, style="Panel.TFrame", padding=18)
        faults.grid(row=2, column=2, columnspan=2, sticky="nsew", padx=(6,0), pady=(0,12))
        ttk.Label(faults, text="Fault Summary", style="Panel.TLabel", font=("Segoe UI Semibold", 12)).pack(anchor="w")
        self.dashboard_faults = ttk.Label(faults, text="No active session", style="PanelMuted.TLabel", wraplength=520, justify="left")
        self.dashboard_faults.pack(anchor="w", pady=(8,0))

        quick = ttk.Frame(page, style="Panel.TFrame", padding=18)
        quick.grid(row=3, column=0, columnspan=4, sticky="nsew")
        ttk.Label(quick, text="Quick Actions", style="Panel.TLabel", font=("Segoe UI Semibold", 12)).pack(anchor="w")
        row = ttk.Frame(quick, style="Panel.TFrame")
        row.pack(fill="x", pady=(14,10))
        PolygonButton(row, text="Start Healthy Simulation", style="Accent.TButton", command=lambda: self._start_simulation("healthy")).pack(side="left", padx=(0,8))
        PolygonButton(row, text="Run Diagnostic Scan", command=self._run_scan).pack(side="left", padx=8)
        PolygonButton(row, text="Generate PDF Report", command=self._generate_report).pack(side="left", padx=8)
        PolygonButton(row, text="Open AI Assistant", command=lambda: self.show_page("ai")).pack(side="left", padx=8)
        ttk.Separator(quick).pack(fill="x", pady=10)
        ttk.Label(quick, text="AutoMind separates ECU-reported data from diagnostic hypotheses. Suggested causes are never treated as confirmed mechanical diagnoses without testing.", style="PanelMuted.TLabel", wraplength=900).pack(anchor="w")

    # ---------- Connect ----------
    def _build_connect(self, page: ttk.Frame) -> None:
        page.grid_columnconfigure(0, weight=1)
        page.grid_columnconfigure(1, weight=1)
        page.grid_rowconfigure(0, weight=1)
        real = ttk.Frame(page, style="Panel.TFrame", padding=18)
        real.grid(row=0, column=0, sticky="nsew", padx=(0,7))
        ttk.Label(real, text="Real Vehicle / ELM327", style="Panel.TLabel", font=("Segoe UI Semibold", 13)).pack(anchor="w")
        ttk.Label(real, text="USB/serial first. Communication runs off the UI thread.", style="PanelMuted.TLabel").pack(anchor="w", pady=(4,14))
        self.port_tree = ttk.Treeview(real, columns=("port","desc"), show="headings", height=11)
        self.port_tree.heading("port", text="Port"); self.port_tree.heading("desc", text="Description")
        self.port_tree.column("port", width=100, anchor="w"); self.port_tree.column("desc", width=330, anchor="w")
        self.port_tree.pack(fill="both", expand=True)
        real_buttons = ttk.Frame(real, style="Panel.TFrame")
        real_buttons.pack(fill="x", pady=(12,0))
        PolygonButton(real_buttons, text="Refresh Ports", command=self._refresh_ports).pack(side="left")
        PolygonButton(real_buttons, text="Connect", style="Accent.TButton", command=self._connect_selected_port).pack(side="left", padx=8)
        PolygonButton(real_buttons, text="Reconnect", command=self._reconnect_real).pack(side="left")
        PolygonButton(real_buttons, text="Disconnect", command=self._disconnect).pack(side="left")
        self.adapter_info_var = tk.StringVar(value="No adapter connected")
        ttk.Label(real, textvariable=self.adapter_info_var, style="PanelMuted.TLabel", wraplength=500).pack(anchor="w", pady=(12,0))

        sim = ttk.Frame(page, style="Panel.TFrame", padding=18)
        sim.grid(row=0, column=1, sticky="nsew", padx=(7,0))
        ttk.Label(sim, text="Vehicle Simulator", style="Panel.TLabel", font=("Segoe UI Semibold", 13)).pack(anchor="w")
        ttk.Label(sim, text="Full diagnostic workflow without a physical vehicle. All generated values are clearly marked as simulation data.", style="PanelMuted.TLabel", wraplength=500).pack(anchor="w", pady=(4,16))
        names = VehicleSimulator.scenario_names()
        self.sim_key_by_name = {name: key for key, name in names}
        self.sim_scenario_var = tk.StringVar(value=names[0][1])
        ttk.Combobox(sim, textvariable=self.sim_scenario_var, values=[n for _,n in names], state="readonly").pack(fill="x")
        PolygonButton(sim, text="Start Simulation", style="Accent.TButton", command=self._start_selected_simulation).pack(anchor="w", pady=12)
        self.sim_desc = tk.Text(sim, height=15, bg=COLORS["surface"], fg=COLORS["text"], insertbackground=COLORS["text"], relief="flat", wrap="word", font=("Segoe UI", 10), padx=12, pady=12)
        self.sim_desc.pack(fill="both", expand=True)
        self.sim_desc.insert("1.0", "SIMULATION MODE\n\nChoose a scenario and start. AutoMind will create realistic DTCs, live PID values, freeze-frame-like data, local diagnostic findings, history entries, and PDF reports.\n\nSimulated data is never presented as real vehicle data.")
        self.sim_desc.configure(state="disabled")
        self.after(100, self._refresh_ports)

    # ---------- Diagnostics ----------
    def _build_diagnostics(self, page: ttk.Frame) -> None:
        toolbar = ttk.Frame(page)
        toolbar.pack(fill="x", pady=(0,10))
        PolygonButton(toolbar, text="Run Full Read-Only Scan", style="Accent.TButton", command=self._run_scan).pack(side="left")
        PolygonButton(toolbar, text="Refresh Live Snapshot", command=self._refresh_live_manual).pack(side="left", padx=8)
        self.diag_summary_var = tk.StringVar(value="No active diagnostic session")
        ttk.Label(toolbar, textvariable=self.diag_summary_var, style="Muted.TLabel").pack(side="right")
        panel = ttk.Frame(page, style="Panel.TFrame", padding=14)
        panel.pack(fill="both", expand=True)
        self.diagnostics_text = tk.Text(panel, bg=COLORS["panel"], fg=COLORS["text"], insertbackground=COLORS["text"], relief="flat", wrap="word", font=("Consolas", 10), padx=10, pady=10)
        self.diagnostics_text.pack(fill="both", expand=True)
        notes = ttk.Frame(panel, style="Panel.TFrame")
        notes.pack(fill="x", pady=(12,0))
        ttk.Label(notes, text="Technician / User Notes", style="Panel.TLabel", font=("Segoe UI Semibold", 10)).pack(anchor="w")
        self.notes_text = tk.Text(notes, height=4, bg=COLORS["surface"], fg=COLORS["text"], insertbackground=COLORS["text"], relief="flat", wrap="word", font=("Segoe UI", 9), padx=9, pady=7)
        self.notes_text.pack(fill="x", pady=(6,6))
        PolygonButton(notes, text="Save Notes", command=self._save_notes_from_ui).pack(anchor="e")
        self._set_text(self.diagnostics_text, "Connect a real vehicle or start Simulation Mode, then run a read-only diagnostic scan.")

    # ---------- DTC ----------
    def _build_dtc(self, page: ttk.Frame) -> None:
        page.grid_columnconfigure(0, weight=1); page.grid_columnconfigure(1, weight=2); page.grid_rowconfigure(0, weight=1)
        left = ttk.Frame(page, style="Panel.TFrame", padding=12); left.grid(row=0,column=0,sticky="nsew",padx=(0,7))
        self.dtc_tree = ttk.Treeview(left, columns=("code","status","severity"), show="headings")
        for c,t,w in (("code","Code",85),("status","Status",100),("severity","Severity",90)):
            self.dtc_tree.heading(c,text=t); self.dtc_tree.column(c,width=w,anchor="w")
        self.dtc_tree.pack(fill="both",expand=True)
        self.dtc_tree.bind("<<TreeviewSelect>>", self._show_selected_dtc)
        PolygonButton(left,text="Refresh from Current Session",command=self._refresh_dtc_page).pack(anchor="w",pady=(10,0))
        right = ttk.Frame(page, style="Panel.TFrame", padding=14); right.grid(row=0,column=1,sticky="nsew",padx=(7,0))
        self.dtc_detail = tk.Text(right,bg=COLORS["panel"],fg=COLORS["text"],insertbackground=COLORS["text"],relief="flat",wrap="word",font=("Segoe UI",10),padx=8,pady=8)
        self.dtc_detail.pack(fill="both",expand=True)
        self._set_text(self.dtc_detail,"Select a DTC to view observed data, common causes, symptoms and recommended checks.")

    # ---------- Live Data ----------
    def _build_live(self, page: ttk.Frame) -> None:
        page.grid_columnconfigure(0, minsize=250); page.grid_columnconfigure(1, weight=1); page.grid_rowconfigure(0, weight=1)
        controls = ttk.Frame(page, style="Panel.TFrame", padding=12); controls.grid(row=0,column=0,sticky="nsew",padx=(0,7))
        ttk.Label(controls,text="Available PIDs",style="Panel.TLabel",font=("Segoe UI Semibold",12)).pack(anchor="w")
        self.pid_search_var=tk.StringVar(); self.pid_search_var.trace_add("write",lambda *_: self._refresh_pid_list())
        ttk.Entry(controls,textvariable=self.pid_search_var).pack(fill="x",pady=(10,8))
        self.pid_list=tk.Listbox(controls,selectmode="multiple",bg=COLORS["surface"],fg=COLORS["text"],selectbackground="#134E4A",selectforeground=COLORS["white"],relief="flat",exportselection=False,font=("Segoe UI",9))
        self.pid_list.pack(fill="both",expand=True)
        self.pid_list.bind("<<ListboxSelect>>",lambda _e:self._pid_selection_changed())
        ttk.Label(controls,text="Sampling interval",style="PanelMuted.TLabel").pack(anchor="w",pady=(10,4))
        self.interval_var=tk.StringVar(value=str(self.controller.config.get("diagnostics","sample_interval_ms",750)))
        ttk.Combobox(controls,textvariable=self.interval_var,values=["250","500","750","1000","1500","2000"],state="readonly").pack(fill="x")
        buttons=ttk.Frame(controls,style="Panel.TFrame");buttons.pack(fill="x",pady=10)
        PolygonButton(buttons,text="Pause",command=lambda:self._set_pause(True)).pack(side="left")
        PolygonButton(buttons,text="Resume",command=lambda:self._set_pause(False)).pack(side="left",padx=5)
        PolygonButton(buttons,text="Reset",command=self._reset_chart).pack(side="left")
        right=ttk.Frame(page);right.grid(row=0,column=1,sticky="nsew",padx=(7,0));right.grid_rowconfigure(0,weight=2);right.grid_rowconfigure(1,weight=1);right.grid_columnconfigure(0,weight=1)
        self.live_chart=LiveChart(right);self.live_chart.grid(row=0,column=0,sticky="nsew",pady=(0,8))
        self.live_tree=ttk.Treeview(right,columns=("pid","name","value","unit"),show="headings",height=8)
        for c,t,w in (("pid","PID",85),("name","Measurement",300),("value","Value",100),("unit","Unit",80)):
            self.live_tree.heading(c,text=t);self.live_tree.column(c,width=w,anchor="w")
        self.live_tree.grid(row=1,column=0,sticky="nsew")
        self._refresh_pid_list()

    # ---------- AI ----------
    def _build_ai(self, page: ttk.Frame) -> None:
        page.grid_rowconfigure(0,weight=1);page.grid_columnconfigure(0,weight=1)
        chat_panel=ttk.Frame(page,style="Panel.TFrame",padding=14);chat_panel.grid(row=0,column=0,sticky="nsew")
        top=ttk.Frame(chat_panel,style="Panel.TFrame");top.pack(fill="x")
        ttk.Label(top,text="AutoMind AI Assistant",style="Panel.TLabel",font=("Segoe UI Semibold",13)).pack(side="left")
        ttk.Label(top,text="Cloud AI is optional; local rules work offline.",style="PanelMuted.TLabel").pack(side="right")
        quick=ttk.Frame(chat_panel,style="Panel.TFrame");quick.pack(fill="x",pady=(10,8))
        for label,q in [("Analyze Faults","Analyze the current faults."),("Explain DTCs","Explain the current DTCs and distinguish observed facts from possible causes."),("Recommend Tests","What should be tested first and why?"),("Analyze Live Data","Analyze the current live-data snapshot."),("Generate Summary","Summarize this diagnostic session.")]:
            PolygonButton(quick,text=label,command=lambda question=q:self._send_ai_question(question)).pack(side="left",padx=(0,6))
        self.ai_chat=tk.Text(chat_panel,bg=COLORS["surface"],fg=COLORS["text"],insertbackground=COLORS["text"],relief="flat",wrap="word",font=("Segoe UI",10),padx=12,pady=12)
        self.ai_chat.pack(fill="both",expand=True,pady=(0,10))
        self.ai_chat.insert("end","AutoMind AI Assistant\n\nStart a diagnostic session. When Cloud AI is disabled, questions are answered using the deterministic local diagnostic engine.\n\n")
        input_row=ttk.Frame(chat_panel,style="Panel.TFrame");input_row.pack(fill="x")
        self.ai_question_var=tk.StringVar();entry=ttk.Entry(input_row,textvariable=self.ai_question_var);entry.pack(side="left",fill="x",expand=True);entry.bind("<Return>",lambda _e:self._send_ai_question())
        PolygonButton(input_row,text="Send",style="Accent.TButton",command=self._send_ai_question).pack(side="left",padx=(8,0))

    # ---------- Profiles ----------
    def _build_profiles(self, page: ttk.Frame) -> None:
        page.grid_columnconfigure(0,weight=1);page.grid_columnconfigure(1,weight=1);page.grid_rowconfigure(0,weight=1)
        left=ttk.Frame(page,style="Panel.TFrame",padding=12);left.grid(row=0,column=0,sticky="nsew",padx=(0,7))
        self.profile_tree=ttk.Treeview(left,columns=("vehicle","vin"),show="headings")
        self.profile_tree.heading("vehicle",text="Vehicle");self.profile_tree.heading("vin",text="VIN")
        self.profile_tree.column("vehicle",width=260);self.profile_tree.column("vin",width=180)
        self.profile_tree.pack(fill="both",expand=True);self.profile_tree.bind("<<TreeviewSelect>>",self._profile_selected)
        PolygonButton(left,text="Refresh",command=self._refresh_profiles).pack(anchor="w",pady=(10,0))
        form=ttk.Frame(page,style="Panel.TFrame",padding=18);form.grid(row=0,column=1,sticky="nsew",padx=(7,0));form.grid_columnconfigure(1,weight=1)
        ttk.Label(form,text="Vehicle Profile",style="Panel.TLabel",font=("Segoe UI Semibold",13)).grid(row=0,column=0,columnspan=2,sticky="w",pady=(0,12))
        self.profile_vars={k:tk.StringVar() for k in ("manufacturer","model","year","engine","fuel_type","vin","mileage","notes")}
        labels=[("Manufacturer","manufacturer"),("Model","model"),("Year","year"),("Engine","engine"),("Fuel Type","fuel_type"),("VIN","vin"),("Mileage","mileage"),("Notes","notes")]
        for i,(label,key) in enumerate(labels,1):
            ttk.Label(form,text=label,style="PanelMuted.TLabel").grid(row=i,column=0,sticky="w",pady=5,padx=(0,8));ttk.Entry(form,textvariable=self.profile_vars[key]).grid(row=i,column=1,sticky="ew",pady=5)
        self.edit_profile_id=""
        row=ttk.Frame(form,style="Panel.TFrame");row.grid(row=10,column=0,columnspan=2,sticky="w",pady=(14,0))
        PolygonButton(row,text="New",command=self._new_profile).pack(side="left")
        PolygonButton(row,text="Save",style="Accent.TButton",command=self._save_profile).pack(side="left",padx=6)
        PolygonButton(row,text="Delete",style="Danger.TButton",command=self._delete_profile).pack(side="left")

    # ---------- History ----------
    def _build_history(self, page: ttk.Frame) -> None:
        panel=ttk.Frame(page,style="Panel.TFrame",padding=12);panel.pack(fill="both",expand=True)
        self.history_tree=ttk.Treeview(panel,columns=("date","mode","scenario","health","faults"),show="headings")
        for c,t,w in (("date","Date / Time",230),("mode","Mode",100),("scenario","Scenario",220),("health","Health",180),("faults","Faults",70)):
            self.history_tree.heading(c,text=t);self.history_tree.column(c,width=w,anchor="w")
        self.history_tree.pack(fill="both",expand=True)
        row=ttk.Frame(panel,style="Panel.TFrame");row.pack(fill="x",pady=(10,0))
        PolygonButton(row,text="Refresh",command=self._refresh_history).pack(side="left")
        PolygonButton(row,text="Open Selected Session",style="Accent.TButton",command=self._open_history_session).pack(side="left",padx=8)

    # ---------- Reports ----------
    def _build_reports(self, page: ttk.Frame) -> None:
        panel=ttk.Frame(page,style="Panel.TFrame",padding=20);panel.pack(fill="both",expand=True)
        ttk.Label(panel,text="Vehicle Health Report",style="Panel.TLabel",font=("Segoe UI Semibold",14)).pack(anchor="w")
        ttk.Label(panel,text="Generate a workshop-style PDF from the current diagnostic session.",style="PanelMuted.TLabel").pack(anchor="w",pady=(4,16))
        self.report_status=tk.StringVar(value="No report generated in this run.")
        ttk.Label(panel,textvariable=self.report_status,style="PanelMuted.TLabel",wraplength=850).pack(anchor="w",pady=(0,14))
        row=ttk.Frame(panel,style="Panel.TFrame");row.pack(anchor="w")
        PolygonButton(row,text="Generate PDF Report",style="Accent.TButton",command=self._generate_report).pack(side="left")
        PolygonButton(row,text="Save Report As...",command=self._generate_report_as).pack(side="left",padx=8)
        PolygonButton(row,text="Open Reports Folder",command=self.controller.open_reports_folder).pack(side="left")
        ttk.Separator(panel).pack(fill="x",pady=20)
        ttk.Label(panel,text="Generated Reports",style="Panel.TLabel",font=("Segoe UI Semibold",11)).pack(anchor="w")
        self.reports_tree=ttk.Treeview(panel,columns=("date","session","path"),show="headings",height=8)
        for c,t,w in (("date","Created",180),("session","Session",210),("path","File",520)):
            self.reports_tree.heading(c,text=t);self.reports_tree.column(c,width=w,anchor="w")
        self.reports_tree.pack(fill="both",expand=True,pady=(8,8))
        report_actions=ttk.Frame(panel,style="Panel.TFrame");report_actions.pack(fill="x")
        PolygonButton(report_actions,text="Refresh List",command=self._refresh_reports).pack(side="left")
        PolygonButton(report_actions,text="Open Selected Report",command=self._open_selected_report).pack(side="left",padx=8)
        ttk.Separator(panel).pack(fill="x",pady=20)
        ttk.Label(panel,text="Report includes",style="Panel.TLabel",font=("Segoe UI Semibold",11)).pack(anchor="w")
        ttk.Label(panel,text="Vehicle information • detected DTCs • live-data summary • freeze frame • local diagnostic interpretation • optional AI analysis • notes • disclaimer",style="PanelMuted.TLabel",wraplength=900).pack(anchor="w",pady=(6,0))

    # ---------- Settings ----------
    def _build_settings(self, page: ttk.Frame) -> None:
        notebook=ttk.Notebook(page);notebook.pack(fill="both",expand=True)
        self.settings_tabs={}
        for name in ("General","Units","OBD Adapter","AI","Privacy","Appearance","Diagnostics","Logs","About"):
            tab=ttk.Frame(notebook,style="Panel.TFrame",padding=18);notebook.add(tab,text=name);self.settings_tabs[name]=tab
        gen=self.settings_tabs["General"]
        ttk.Label(gen,text="AutoMind AI 0.1.0 MVP",style="Panel.TLabel",font=("Segoe UI Semibold",13)).pack(anchor="w")
        ttk.Label(gen,text="Read-focused diagnostics. Simulation Mode remains available without an adapter or Internet connection.",style="PanelMuted.TLabel",wraplength=760).pack(anchor="w",pady=(6,0))
        units=self.settings_tabs["Units"];self.units_var=tk.StringVar()
        ttk.Label(units,text="Measurement Units",style="Panel.TLabel").grid(row=0,column=0,sticky="w",pady=6);ttk.Combobox(units,textvariable=self.units_var,values=["metric","imperial"],state="readonly").grid(row=0,column=1,sticky="w",pady=6)
        obd=self.settings_tabs["OBD Adapter"];self.obd_port_var=tk.StringVar();self.obd_baud_var=tk.StringVar()
        ttk.Label(obd,text="Preferred Serial Port",style="Panel.TLabel").grid(row=0,column=0,sticky="w",pady=6);ttk.Entry(obd,textvariable=self.obd_port_var,width=24).grid(row=0,column=1,pady=6)
        ttk.Label(obd,text="Baud Rate",style="Panel.TLabel").grid(row=1,column=0,sticky="w",pady=6);ttk.Combobox(obd,textvariable=self.obd_baud_var,values=["9600","38400","57600","115200"],state="readonly").grid(row=1,column=1,pady=6)
        ai=self.settings_tabs["AI"];self.ai_enabled_var=tk.BooleanVar();self.ai_allowed_var=tk.BooleanVar();self.ai_url_var=tk.StringVar();self.ai_token_env_var=tk.StringVar()
        ttk.Checkbutton(ai,text="AI Enabled",variable=self.ai_enabled_var,style="Panel.TCheckbutton").grid(row=0,column=0,columnspan=2,sticky="w",pady=5)
        ttk.Checkbutton(ai,text="Allow AI Cloud Analysis",variable=self.ai_allowed_var,style="Panel.TCheckbutton").grid(row=1,column=0,columnspan=2,sticky="w",pady=5)
        ttk.Label(ai,text="AutoMind Backend URL",style="Panel.TLabel").grid(row=2,column=0,sticky="w",pady=6);ttk.Entry(ai,textvariable=self.ai_url_var,width=58).grid(row=2,column=1,sticky="ew",pady=6)
        ttk.Label(ai,text="Client token env variable",style="Panel.TLabel").grid(row=3,column=0,sticky="w",pady=6);ttk.Entry(ai,textvariable=self.ai_token_env_var,width=30).grid(row=3,column=1,sticky="w",pady=6)
        ttk.Label(ai,text="Production provider secrets belong on the AutoMind backend, not in this desktop executable.",style="PanelMuted.TLabel",wraplength=750).grid(row=4,column=0,columnspan=2,sticky="w",pady=(10,0))
        privacy=self.settings_tabs["Privacy"];self.send_vin_var=tk.BooleanVar();self.send_notes_var=tk.BooleanVar();self.store_ai_var=tk.BooleanVar();self.report_vin_var=tk.BooleanVar()
        ttk.Checkbutton(privacy,text="Allow VIN to be sent to AI backend",variable=self.send_vin_var,style="Panel.TCheckbutton").pack(anchor="w",pady=5)
        ttk.Checkbutton(privacy,text="Allow current session notes to be sent to AI backend",variable=self.send_notes_var,style="Panel.TCheckbutton").pack(anchor="w",pady=5)
        ttk.Checkbutton(privacy,text="Store AI results in local diagnostic history",variable=self.store_ai_var,style="Panel.TCheckbutton").pack(anchor="w",pady=5)
        ttk.Checkbutton(privacy,text="Include VIN in local PDF reports",variable=self.report_vin_var,style="Panel.TCheckbutton").pack(anchor="w",pady=5)
        ttk.Label(privacy,text="VIN and session notes are excluded from cloud AI context by default. Technical OBD data continues to work locally when Cloud AI is off.",style="PanelMuted.TLabel",wraplength=760).pack(anchor="w",pady=(12,0))
        appearance=self.settings_tabs["Appearance"];self.theme_var=tk.StringVar()
        ttk.Label(appearance,text="Theme",style="Panel.TLabel").grid(row=0,column=0,sticky="w",pady=6);ttk.Combobox(appearance,textvariable=self.theme_var,values=["dark"],state="readonly").grid(row=0,column=1,sticky="w",pady=6)
        diag=self.settings_tabs["Diagnostics"];self.settings_interval_var=tk.StringVar()
        ttk.Label(diag,text="Default live-data interval (ms)",style="Panel.TLabel").grid(row=0,column=0,sticky="w",pady=6);ttk.Combobox(diag,textvariable=self.settings_interval_var,values=["250","500","750","1000","1500","2000"],state="readonly").grid(row=0,column=1,pady=6)
        logs=self.settings_tabs["Logs"];PolygonButton(logs,text="Open Log Folder",command=self.controller.open_logs_folder).pack(anchor="w");ttk.Label(logs,text="Logs contain application state and errors but never intentionally include AI secrets.",style="PanelMuted.TLabel",wraplength=700).pack(anchor="w",pady=(10,0))
        about=self.settings_tabs["About"];ttk.Label(about,text=PRODUCT_NAME,style="Panel.TLabel",font=("Segoe UI Semibold",14)).pack(anchor="w");ttk.Label(about,text="Read-focused OBD-II diagnostic assistant with local deterministic reasoning and optional cloud AI.",style="PanelMuted.TLabel",wraplength=750).pack(anchor="w",pady=(6,0))
        PolygonButton(page,text="Save Settings",style="Accent.TButton",command=self._save_settings).pack(anchor="e",pady=(10,0))

    # ---------- Actions ----------
    def _run_bg(self, work: Callable, success: Callable | None = None, title: str = "Operation failed") -> None:
        def runner():
            try:
                result=work()
            except Exception as exc:
                log.exception("Background operation failed")
                self.after(0,lambda e=exc:messagebox.showerror(title,str(e),parent=self))
            else:
                if success:self.after(0,lambda r=result:success(r))
        threading.Thread(target=runner,daemon=True).start()

    def _start_selected_simulation(self) -> None:
        key=self.sim_key_by_name.get(self.sim_scenario_var.get(),"healthy");self._start_simulation(key)

    def _start_simulation(self,key:str) -> None:
        try:self.controller.start_simulation(key)
        except Exception as exc:messagebox.showerror("Simulation Error",str(exc),parent=self);return
        self._refresh_everything();self.show_page("dashboard")

    def _refresh_ports(self) -> None:
        for item in self.port_tree.get_children():self.port_tree.delete(item)
        ports=self.controller.list_ports()
        for p in ports:self.port_tree.insert("","end",iid=p.device,values=(p.device,p.description))
        if not ports:self.port_tree.insert("","end",iid="__none__",values=("—","No serial ports detected"))

    def _connect_selected_port(self) -> None:
        sel=self.port_tree.selection()
        if not sel or sel[0]=="__none__":messagebox.showinfo("Select Adapter","Select a detected serial port first.",parent=self);return
        port=sel[0];self.adapter_info_var.set(f"Connecting to {port}...")
        self._run_bg(lambda:self.controller.connect_real(port),lambda info:self._connected_real(info),"Vehicle Connection Error")

    def _connected_real(self,info:dict) -> None:
        details = [
            info.get('identity','ELM327'), info.get('protocol',''), info.get('voltage',''),
            f"VIN {info.get('vin') or 'Unavailable'}",
            f"Supported PIDs {info.get('supported_pid_count','0')}"
        ]
        if info.get('ecu_name'): details.append(f"ECU {info['ecu_name']}")
        if info.get('calibration_id'): details.append(f"CALID {info['calibration_id']}")
        self.adapter_info_var.set(" • ".join(x for x in details if x))
        self._refresh_everything()

    def _reconnect_real(self) -> None:
        self.adapter_info_var.set("Reconnecting to the saved adapter...")
        self._run_bg(self.controller.reconnect_real,lambda info:self._connected_real(info),"Vehicle Reconnection Error")

    def _disconnect(self) -> None:
        self.controller.disconnect();self._refresh_everything()

    def _run_scan(self) -> None:
        if self.controller.mode=="disconnected":messagebox.showinfo("No Active Session","Connect a vehicle or start Simulation Mode first.",parent=self);return
        self.diag_summary_var.set("Scanning...")
        self._run_bg(self.controller.scan_diagnostics,lambda _r:self._scan_complete(),"Diagnostic Scan Error")

    def _scan_complete(self) -> None:
        self._refresh_everything();self.show_page("diagnostics")

    def _refresh_live_manual(self) -> None:
        if self.controller.mode=="disconnected":return
        self._run_bg(lambda:self.controller.refresh_live_data(self._live_selected),lambda _r:self._refresh_everything(),"Live Data Error")

    def _send_ai_question(self,question:str|None=None) -> None:
        q=(question if question is not None else self.ai_question_var.get()).strip()
        if not q:return
        if not self.controller.current_session:messagebox.showinfo("No Active Session","Start a diagnostic session first.",parent=self);return
        self.ai_question_var.set("");self.ai_chat.insert("end",f"\nYou: {q}\n\n");self.ai_chat.see("end")
        ai_enabled=bool(self.controller.config.get("ai","enabled",False) and self.controller.config.get("ai","cloud_analysis_allowed",False))
        if not ai_enabled:
            answer=self.controller.local_answer(q);self.ai_chat.insert("end",f"AutoMind Local Engine:\n{answer}\n");self.ai_chat.see("end");return
        self.ai_chat.insert("end","AutoMind AI: analyzing securely through configured backend...\n");self.ai_chat.see("end")
        def success(a):
            lines=[a.summary,"","Observed Evidence:"]+[f"- {x}" for x in a.observed_evidence]+["","Possible Causes (not confirmed):"]+[f"- {x}" for x in a.possible_causes]+["","Recommended Steps:"]+[f"{i}. {x}" for i,x in enumerate(a.recommended_steps,1)]
            if a.additional_measurements:lines += ["","Additional Measurements:"]+[f"- {x}" for x in a.additional_measurements]
            lines += ["",f"Confidence / Uncertainty: {a.confidence}"]
            if a.warnings:lines += ["","Warnings:"]+[f"- {x}" for x in a.warnings]
            self.ai_chat.insert("end","AutoMind AI:\n"+"\n".join(lines)+"\n");self.ai_chat.see("end");self._refresh_status()
        self._run_bg(lambda:self.controller.ai_analysis(q),success,"AI Analysis Error")

    def _generate_report(self) -> None:
        if not self.controller.current_session:messagebox.showinfo("No Active Session","Start a diagnostic session first.",parent=self);return
        self._run_bg(self.controller.generate_report,lambda p:self._report_done(p),"Report Generation Error")

    def _generate_report_as(self) -> None:
        if not self.controller.current_session:messagebox.showinfo("No Active Session","Start a diagnostic session first.",parent=self);return
        path=filedialog.asksaveasfilename(parent=self,defaultextension=".pdf",filetypes=[("PDF Report","*.pdf")],initialfile="AutoMindAI-Diagnostic-Report.pdf")
        if path:self._run_bg(lambda:self.controller.generate_report(Path(path)),lambda p:self._report_done(p),"Report Generation Error")

    def _report_done(self,path:Path) -> None:
        self.report_status.set(f"Generated: {path}");self._refresh_reports();messagebox.showinfo("Report Generated",f"PDF report created:\n{path}",parent=self)

    def _refresh_reports(self) -> None:
        if not hasattr(self,"reports_tree"):return
        for item in self.reports_tree.get_children():self.reports_tree.delete(item)
        try:reports=self.controller.db.list_reports()
        except Exception as exc:
            log.warning("Could not list reports: %s",exc);return
        for report in reports:
            iid=str(report["id"])
            self.reports_tree.insert("","end",iid=iid,values=(report["created_at"],report["session_id"],report["path"]))

    def _open_selected_report(self) -> None:
        if not hasattr(self,"reports_tree"):return
        sel=self.reports_tree.selection()
        if not sel:return
        values=self.reports_tree.item(sel[0],"values")
        if len(values)<3:return
        try:self.controller.open_report_file(str(values[2]))
        except Exception as exc:messagebox.showerror("Open Report",str(exc),parent=self)

    def _pid_selection_changed(self) -> None:
        rows=self._filtered_pid_rows();selected=[]
        for idx in self.pid_list.curselection():
            if idx<len(rows):selected.append(rows[idx][0])
        self._live_selected=selected[:6] or self._live_selected

    def _filtered_pid_rows(self):
        q=self.pid_search_var.get().lower().strip() if hasattr(self,"pid_search_var") else ""
        rows=self.controller.supported_pid_rows()
        if q:rows=[r for r in rows if q in " ".join(r).lower()]
        return rows

    def _refresh_pid_list(self) -> None:
        if not hasattr(self,"pid_list"):return
        rows=self._filtered_pid_rows();self.pid_list.delete(0,"end")
        for pid,name,unit in rows:self.pid_list.insert("end",f"{pid}  {name}  [{unit}]")
        for i,(pid,_,_) in enumerate(rows):
            if pid in self._live_selected:self.pid_list.selection_set(i)

    def _set_pause(self,value:bool) -> None:self._live_paused=value
    def _reset_chart(self) -> None:self.live_chart.reset()

    def _live_tick(self) -> None:
        try:
            interval=int(self.interval_var.get()) if hasattr(self,"interval_var") else int(self.controller.config.get("diagnostics","sample_interval_ms",750))
        except ValueError:interval=750
        interval=max(250,min(5000,interval))
        if self.controller.mode == "real":
            interval=max(500,interval)
        if self.controller.mode!="disconnected" and not self._live_paused:
            if self.controller.mode == "real":
                if not self._live_fetch_inflight:
                    self._live_fetch_inflight = True
                    def worker():
                        try:
                            values = self.controller.refresh_live_data(self._live_selected)
                        except Exception as exc:
                            log.warning("Live polling error: %s", exc)
                            self.after(0, lambda: setattr(self, "_live_fetch_inflight", False))
                        else:
                            def done():
                                self._live_fetch_inflight = False
                                self._update_live_views(values)
                                self._refresh_dashboard()
                            self.after(0, done)
                    threading.Thread(target=worker, daemon=True).start()
            else:
                try:
                    values=self.controller.refresh_live_data(self._live_selected)
                    self._update_live_views(values)
                    self._refresh_dashboard()
                except Exception as exc:
                    log.warning("Live polling error: %s",exc)
        self.after(interval,self._live_tick)

    # ---------- Refresh ----------
    def _refresh_everything(self) -> None:
        self._refresh_status();self._refresh_dashboard();self._refresh_diagnostics_text();self._refresh_dtc_page();self._refresh_history();self._refresh_profiles();self._refresh_reports()
        if self.controller.current_session:self._update_live_views(self.controller.current_session.live_data)

    def _refresh_status(self) -> None:
        s=self.controller.status_snapshot();
        self.vehicle_pill.set(s["vehicle"],"success" if "Connected" in s["vehicle"] or "SIMULATION" in s["vehicle"] else ("danger" if "Error" in s["vehicle"] else "muted"))
        self.adapter_pill.set(s["adapter"],"success" if "Connected" in s["adapter"] or "Active" in s["adapter"] else "muted")
        self.ai_pill.set(s["ai"],"success" if s["ai"]=="AI Online" else ("info" if "Connecting" in s["ai"] else "muted"))

    def _refresh_dashboard(self) -> None:
        session=self.controller.current_session;vehicle=self.controller.current_vehicle
        if not session:
            self.card_health.set("--","No active session");self.card_rpm.set("--","Unavailable");self.card_speed.set("--","Unavailable");self.card_temp.set("--","Unavailable");self.card_voltage.set("--","Unavailable");self.card_load.set("--","Unavailable");self.card_fuel.set("--","Unavailable");self.card_trim.set("--","Unavailable")
            self.dashboard_vehicle.configure(text="No vehicle session");self.dashboard_vin.configure(text="VIN: Unavailable");self.dashboard_mode.configure(text="Mode: Disconnected");self.dashboard_engine.configure(text="Engine: Unavailable");self.dashboard_faults.configure(text="No active session");return
        health_label = {"Attention Required":"Attention", "Check Recommended":"Check", "No OBD Faults Detected":"No OBD Faults"}.get(session.health_status, session.health_status)
        self.card_health.set(health_label,f"{session.health_status} • {len(session.dtcs)} fault code(s)")
        self._set_metric(self.card_rpm,session,"010C","rpm");self._set_metric(self.card_speed,session,"010D","km/h");self._set_metric(self.card_temp,session,"0105","°C");self._set_metric(self.card_voltage,session,"0142","V");self._set_metric(self.card_load,session,"0104","%");self._set_metric(self.card_fuel,session,"012F","%");self._set_metric(self.card_trim,session,"0106","%")
        self.dashboard_vehicle.configure(text=vehicle.display_name if vehicle else "Unidentified Vehicle")
        self.dashboard_vin.configure(text=f"VIN: {vehicle.vin if vehicle and vehicle.vin else 'Unavailable'}")
        self.dashboard_mode.configure(text=f"Mode: {'SIMULATION MODE' if session.connection_mode=='simulation' else 'Real OBD-II'}")
        rpm=session.live_data.get("010C")
        if rpm and rpm.supported and isinstance(rpm.value,(int,float)):
            engine_state="Running" if float(rpm.value)>100 else "Stopped"
        else:engine_state="Unavailable"
        self.dashboard_engine.configure(text=f"Engine: {engine_state}")
        if session.dtcs:self.dashboard_faults.configure(text="\n".join(f"{d.code} — {d.description} [{d.status}]" for d in session.dtcs[:5]))
        else:self.dashboard_faults.configure(text="No stored OBD-II DTCs in current scan. This does not prove the vehicle has no mechanical fault.")

    def _set_metric(self,card:MetricCard,session:DiagnosticSession,pid:str,unit:str) -> None:
        v=session.live_data.get(pid)
        if v and v.supported and v.value is not None:
            text, target_unit = format_value(v.value, v.unit or unit, str(self.controller.config.get("general","units","metric")))
            card.set(f"{text} {target_unit}".strip(),v.name)
        else:card.set("Unavailable","Not Supported or no value")

    def _refresh_diagnostics_text(self) -> None:
        if not hasattr(self,"diagnostics_text"):return
        session=self.controller.current_session
        if not session:
            self._set_text(self.diagnostics_text,"Connect a vehicle or start Simulation Mode, then run a read-only diagnostic scan.");self.diag_summary_var.set("No active diagnostic session");self._load_notes_for_session(None);return
        lines=[f"MODE: {'SIMULATION MODE' if session.connection_mode=='simulation' else 'REAL OBD-II'}",f"HEALTH: {session.health_status}",f"DTC COUNT: {len(session.dtcs)}","","CONFIRMED / OBSERVED DATA"]
        if session.dtcs:lines.extend(f"• {d.code} [{d.status}] {d.description}" for d in session.dtcs)
        else:lines.append("• No stored DTCs in this scan.")
        for pid in ("010C","0105","0142","0106","0107","0110"):
            v=session.live_data.get(pid)
            if v and v.supported and v.value is not None:lines.append(f"• {v.name}: {v.value} {v.unit}".rstrip())
        lines += ["","POSSIBLE DIAGNOSTIC CAUSES / RECOMMENDED CHECKS"]
        for finding in session.findings:
            lines += ["",finding.title,"Evidence:"]+[f"  - {x}" for x in finding.evidence]
            if finding.possible_causes:lines += ["Possible causes (NOT confirmed):"]+[f"  - {c.get('cause')} [{c.get('priority')}] — {c.get('reason')}" for c in finding.possible_causes[:7]]
            lines += ["Recommended sequence:"]+[f"  {i}. {x}" for i,x in enumerate(finding.recommended_steps[:8],1)]
            for w in finding.warnings:lines.append(f"WARNING: {w}")
        self._set_text(self.diagnostics_text,"\n".join(lines));self.diag_summary_var.set(f"{session.connection_mode.upper()} • {len(session.dtcs)} DTC(s) • {session.health_status}");self._load_notes_for_session(session)

    def _load_notes_for_session(self,session:DiagnosticSession|None) -> None:
        if not hasattr(self,"notes_text"):return
        session_id=session.id if session else None
        if session_id==self._notes_session_id:return
        self._notes_session_id=session_id
        self.notes_text.delete("1.0","end")
        if session and session.user_notes:self.notes_text.insert("1.0",session.user_notes)

    def _save_notes_from_ui(self) -> None:
        if not self.controller.current_session:
            messagebox.showinfo("No Active Session","Start a diagnostic session first.",parent=self);return
        notes=self.notes_text.get("1.0","end").strip()
        try:self.controller.save_notes(notes)
        except Exception as exc:messagebox.showerror("Save Notes",str(exc),parent=self);return
        messagebox.showinfo("Notes Saved","Session notes were saved locally.",parent=self)

    def _refresh_dtc_page(self) -> None:
        if not hasattr(self,"dtc_tree"):return
        for item in self.dtc_tree.get_children():self.dtc_tree.delete(item)
        session=self.controller.current_session
        if not session:return
        for d in session.dtcs:self.dtc_tree.insert("","end",iid=f"{d.code}-{d.status}",values=(d.code,d.status,d.severity))

    def _show_selected_dtc(self,_event=None) -> None:
        sel=self.dtc_tree.selection();session=self.controller.current_session
        if not sel or not session:return
        code,status=sel[0].split("-",1);d=next((x for x in session.dtcs if x.code==code and x.status==status),None)
        if not d:return
        lines=[f"{d.code} — {d.description}",f"Status: {d.status}",f"Subsystem: {d.subsystem}",f"Severity: {d.severity}","","Confirmed data:",f"• ECU reported {d.code} with status {d.status}."]
        if d.freeze_frame:lines += ["","Freeze Frame:"]+[f"• {k}: {v}" for k,v in d.freeze_frame.items()]
        related_values=[]
        for pid in d.related_pids:
            v=session.live_data.get(pid)
            if v and v.supported and v.value is not None:
                text, unit = format_value(v.value, v.unit, str(self.controller.config.get("general","units","metric")))
                related_values.append(f"• {pid} {v.name}: {text} {unit}".rstrip())
        lines += ["","Possible causes (not confirmed):"]+[f"• {x}" for x in d.possible_causes]+["","Possible symptoms:"]+[f"• {x}" for x in d.symptoms]+["","Recommended checks:"]+[f"{i}. {x}" for i,x in enumerate(d.recommended_checks,1)]+["","Related sensor values:"]+(related_values or ["• No related live value is available in the current snapshot."])+["","Related PIDs:",", ".join(d.related_pids) or "None listed"]
        self._set_text(self.dtc_detail,"\n".join(lines))

    def _update_live_views(self,values) -> None:
        if not hasattr(self,"live_tree"):return
        for item in self.live_tree.get_children():self.live_tree.delete(item)
        chart={}
        for pid in self._live_selected:
            v=values.get(pid) or (self.controller.current_session.live_data.get(pid) if self.controller.current_session else None)
            if not v:continue
            if not v.supported:
                display, display_unit = "Not Supported", v.unit
            elif v.value is None:
                display, display_unit = "Unavailable", v.unit
            else:
                display, display_unit = format_value(v.value, v.unit, str(self.controller.config.get("general","units","metric")))
            self.live_tree.insert("","end",values=(pid,v.name,display,display_unit))
            if v.supported and isinstance(v.value,(int,float)):
                converted_text, converted_unit = format_value(v.value, v.unit, str(self.controller.config.get("general","units","metric")))
                try: chart[v.name]=(float(converted_text),converted_unit)
                except ValueError: pass
        if chart:self.live_chart.add_values(chart)

    def _refresh_history(self) -> None:
        if not hasattr(self,"history_tree"):return
        for item in self.history_tree.get_children():self.history_tree.delete(item)
        try:sessions=self.controller.db.list_sessions()
        except Exception:return
        for s in sessions:self.history_tree.insert("","end",iid=s.id,values=(s.started_at,s.connection_mode,s.scenario or "—",s.health_status,len(s.dtcs)))

    def _open_history_session(self) -> None:
        sel=self.history_tree.selection()
        if not sel:return
        s=self.controller.db.get_session(sel[0])
        if not s:return
        self.controller.current_session=s;self.controller.current_vehicle=self.controller.db.get_vehicle(s.vehicle_id) if s.vehicle_id else None
        self.controller.simulator=None;self.controller.elm=None;self.controller.connection_state="Historical Session";self.controller.adapter_state="Not Connected"
        self._refresh_everything();self.show_page("diagnostics")

    def _refresh_profiles(self) -> None:
        if not hasattr(self,"profile_tree"):return
        for item in self.profile_tree.get_children():self.profile_tree.delete(item)
        try:vehicles=self.controller.db.list_vehicles()
        except Exception:return
        for v in vehicles:self.profile_tree.insert("","end",iid=v.id,values=(v.display_name,v.vin or "—"))

    def _profile_selected(self,_e=None) -> None:
        sel=self.profile_tree.selection()
        if not sel:return
        v=self.controller.db.get_vehicle(sel[0])
        if not v:return
        self.edit_profile_id=v.id
        for key,var in self.profile_vars.items():var.set(str(getattr(v,key) if getattr(v,key) is not None else ""))

    def _new_profile(self) -> None:
        self.edit_profile_id=""
        for var in self.profile_vars.values():var.set("")
        self.profile_vars["fuel_type"].set("Gasoline")

    def _save_profile(self) -> None:
        try:
            year=int(self.profile_vars["year"].get()) if self.profile_vars["year"].get().strip() else None
            mileage=float(self.profile_vars["mileage"].get()) if self.profile_vars["mileage"].get().strip() else None
        except ValueError:messagebox.showerror("Invalid Profile","Year and mileage must be numeric when provided.",parent=self);return
        kwargs={k:v.get().strip() for k,v in self.profile_vars.items() if k not in ("year","mileage")};kwargs.update(year=year,mileage=mileage)
        if self.edit_profile_id:kwargs["id"]=self.edit_profile_id
        v=VehicleProfile(**kwargs);self.controller.db.save_vehicle(v);self.edit_profile_id=v.id;self._refresh_profiles()

    def _delete_profile(self) -> None:
        if not self.edit_profile_id:return
        if messagebox.askyesno("Delete Vehicle Profile","Delete this vehicle profile? Existing sessions will remain and detach from the profile.",parent=self):
            self.controller.db.delete_vehicle(self.edit_profile_id);self._new_profile();self._refresh_profiles()

    def _load_settings_controls(self) -> None:
        if not hasattr(self,"units_var"):return
        c=self.controller.config
        self.units_var.set(c.get("general","units","metric"));self.theme_var.set(c.get("general","theme","dark"));self.obd_port_var.set(c.get("obd","serial_port",""));self.obd_baud_var.set(str(c.get("obd","baud_rate",38400)))
        self.ai_enabled_var.set(bool(c.get("ai","enabled",False)));self.ai_allowed_var.set(bool(c.get("ai","cloud_analysis_allowed",False)));self.ai_url_var.set(c.get("ai","backend_url",""));self.ai_token_env_var.set(c.get("ai","client_token_env","AUTOMIND_CLIENT_TOKEN"));self.send_vin_var.set(bool(c.get("ai","send_vin",False)));self.send_notes_var.set(bool(c.get("ai","send_session_notes",False)))
        self.store_ai_var.set(bool(c.get("privacy","store_ai_results",True)));self.report_vin_var.set(bool(c.get("privacy","include_vin_in_reports",True)));self.settings_interval_var.set(str(c.get("diagnostics","sample_interval_ms",750)))

    def _save_settings(self) -> None:
        c=self.controller.config
        c.set("general","units",self.units_var.get(),False);c.set("general","theme",self.theme_var.get(),False);c.set("obd","serial_port",self.obd_port_var.get(),False);c.set("obd","baud_rate",int(self.obd_baud_var.get() or 38400),False)
        c.set("ai","enabled",bool(self.ai_enabled_var.get()),False);c.set("ai","cloud_analysis_allowed",bool(self.ai_allowed_var.get()),False);c.set("ai","backend_url",self.ai_url_var.get().strip(),False);c.set("ai","client_token_env",self.ai_token_env_var.get().strip() or "AUTOMIND_CLIENT_TOKEN",False);c.set("ai","send_vin",bool(self.send_vin_var.get()),False);c.set("ai","send_session_notes",bool(self.send_notes_var.get()),False)
        c.set("privacy","store_ai_results",bool(self.store_ai_var.get()),False);c.set("privacy","include_vin_in_reports",bool(self.report_vin_var.get()),False);c.set("diagnostics","sample_interval_ms",int(self.settings_interval_var.get() or 750),False);c.save();messagebox.showinfo("Settings Saved","AutoMind AI settings were saved.",parent=self)

    # ---------- First run ----------
    def _maybe_first_run(self) -> None:
        if self.controller.config.get("general","first_run_complete",False):return
        win=tk.Toplevel(self);win.title("Welcome to AutoMind AI");win.configure(bg=COLORS["panel"]);win.geometry("620x430");win.transient(self);win.grab_set();win.resizable(False,False)
        body=ttk.Frame(win,style="Panel.TFrame",padding=28);body.pack(fill="both",expand=True)
        ttk.Label(body,text="Welcome to AutoMind AI",style="Panel.TLabel",font=("Segoe UI Semibold",20)).pack(anchor="w")
        ttk.Label(body,text="A read-focused automotive diagnostic assistant built around real OBD-II data, deterministic local rules, history, reporting, and optional cloud AI.",style="PanelMuted.TLabel",wraplength=540).pack(anchor="w",pady=(8,18))
        warn=tk.Label(body,text="Diagnostic assistant only — suggested causes are hypotheses. Verify repairs with qualified inspection and vehicle-specific service information.",bg="#3A2A08",fg="#FCD34D",font=("Segoe UI Semibold",9),justify="left",wraplength=520,padx=12,pady=10);warn.pack(fill="x",pady=(0,18))
        ttk.Label(body,text="Choose how to begin:",style="Panel.TLabel").pack(anchor="w",pady=(0,8))
        def finish(mode):
            self.controller.config.set("general","first_run_complete",True);win.destroy()
            if mode=="sim":self._start_simulation("healthy")
            else:self.show_page("connect")
        PolygonButton(body,text="Try Simulation Mode",style="Accent.TButton",command=lambda:finish("sim")).pack(fill="x",pady=5)
        PolygonButton(body,text="Connect Real Vehicle",command=lambda:finish("real")).pack(fill="x",pady=5)

    @staticmethod
    def _set_text(widget:tk.Text,text:str) -> None:
        widget.configure(state="normal");widget.delete("1.0","end");widget.insert("1.0",text);widget.configure(state="disabled")

    def _on_close(self) -> None:
        try:self.controller.disconnect()
        finally:self.destroy()
