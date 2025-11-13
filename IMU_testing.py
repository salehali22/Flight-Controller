"""
IMU Monitor
-----------
Full-featured IMU evaluation suite with command system and charting

Features:
- Command presets for common tests
- Data marker protocol (<DATA> ... </DATA>)
- Real-time charting with multiple views
- Statistics and drift analysis
- High-speed data capture (up to 6.8kHz)

Run with --debug flag for detailed console logging
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, simpledialog
import serial
import serial.tools.list_ports
import threading
import queue
import time
import math
import os
import sys
from datetime import datetime
from collections import deque
from dataclasses import dataclass, field
import binascii
import shutil
import subprocess
import re
from typing import Optional, List
import bisect

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np

DEBUG_MODE = '--debug' in sys.argv
plt.ion()


@dataclass
class CommandPreset:
    name: str
    description: str
    commands: list[str]


@dataclass
class DataBlock:
    metadata: dict = field(default_factory=dict)
    lines: List[str] = field(default_factory=list)
    start_ts: float = 0.0
    end_ts: float = 0.0
    missing_end: bool = False
    crc_status: Optional[str] = None
    sample_count_expected: Optional[int] = None
    warnings: List[str] = field(default_factory=list)
    block_id: int = 0
    sample_count_actual: int = 0

    def to_csv_rows(self):
        return self.lines

    def duration(self):
        if not self.start_ts or not self.end_ts:
            return 0.0
        return self.end_ts - self.start_ts


class DataBlockParser:
    """Parser for <DATA> ... </DATA> marked blocks"""
    def __init__(self):
        self.in_block = False
        self.current_block: Optional[DataBlock] = None
        self.metadata = {}
        self.block_start_time: Optional[float] = None
        self._last_line_ts: Optional[float] = None
    
    def parse_line(self, line, timestamp=None):
        """Returns: None (still parsing), or DataBlock when block complete"""
        if timestamp is None:
            timestamp = time.time()
        self._last_line_ts = timestamp
        
        if line.startswith("<DATA"):
            self.in_block = True
            self.block_start_time = timestamp
            self.metadata = self.extract_metadata(line)
            self.current_block = DataBlock(metadata=self.metadata.copy(), start_ts=timestamp)
            return None
            
        elif line == "</DATA>":
            if not self.in_block or not self.current_block:
                return None
            self.in_block = False
            self.current_block.end_ts = timestamp
            result = self.current_block
            self.current_block = None
            self.metadata = {}
            self.block_start_time = None
            return result
            
        elif self.in_block:
            if not self.current_block:
                # Should not happen, but guard
                self.current_block = DataBlock(metadata=self.metadata.copy(), start_ts=self.block_start_time or timestamp)
            self.current_block.lines.append(line)
            return None
            
        return None
    
    def extract_metadata(self, line):
        """Extract metadata from <DATA:key=val,key=val> format"""
        meta = {}
        match = re.search(r'<DATA:(.+)>', line)
        if match:
            pairs = match.group(1).split(',')
            for pair in pairs:
                if '=' in pair:
                    key, val = pair.split('=', 1)
                    meta[key.strip()] = val.strip()
        return meta

    def finalize_if_timed_out(self, timeout=2.0):
        """If a block is open too long without closing tag, mark missing end"""
        if not self.in_block or not self.current_block or not self.block_start_time:
            return None
        if time.time() - self.block_start_time < timeout:
            return None
        self.current_block.missing_end = True
        self.current_block.end_ts = self._last_line_ts or time.time()
        result = self.current_block
        self.in_block = False
        self.current_block = None
        self.metadata = {}
        self.block_start_time = None
        return result


class DebugLogger:
    """Debug logger"""
    def __init__(self):
        self.enabled = DEBUG_MODE
        self.logs = deque(maxlen=1000)
    
    def log(self, level, message):
        if not self.enabled:
            return
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        entry = f"[{timestamp}] {level}: {message}"
        self.logs.append(entry)
        print(entry, flush=True)
    
    def info(self, message):
        self.log("INFO", message)
    
    def warning(self, message):
        self.log("WARNING", message)
    
    def error(self, message):
        self.log("ERROR", message)
    
    def get_logs(self):
        return "\n".join(self.logs)


class EnhancedIMUMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("IMU Monitor")
        self.root.geometry("1600x900")
        self.root.configure(bg="#1e1e1e")
        
        self.logger = DebugLogger()
        self.logger.info("Application starting")
        
        # Serial
        self.serial_port = None
        self.reading = False
        self.data_queue = queue.Queue(maxsize=10000)
        
        # Data storage (large buffers for high-speed capture)
        self.log_data = deque(maxlen=100000)  # ~15s at 6.8kHz
        self.sent_commands = deque(maxlen=1000)
        
        # Data block parser
        self.parser = DataBlockParser()
        self.recording_block = False
        self.current_block_metadata = {}
        self.data_blocks: List[DataBlock] = []
        self.csv_buffer: List[str] = []
        self.block_sample_counter = 0
        self.total_samples_captured = 0
        self.block_start_timestamp = None
        self.last_block_summary = "No data blocks captured yet."
        self.data_block_counter = 0
        self.data_block_index = {}
        
        # Chart data buffers
        self.chart_buffer_size = 250000  # ~5 minutes at 500 Hz
        self.chart_keys = ["roll", "pitch", "yaw", "gx", "gy", "gz", "ax", "ay", "az", "roll_raw", "pitch_raw", "yaw_raw"]
        self.chart_data = {key: deque(maxlen=self.chart_buffer_size) for key in ["time"] + self.chart_keys}
        self.chart_start_time = time.time()
        self.chart_window_var = tk.StringVar(value="1min")
        self.chart_axis_var = tk.StringVar(value="roll")
        self.chart_paused = tk.BooleanVar(value=False)
        self.chart_autoscale = tk.BooleanVar(value=True)
        self.chart_axis_options = {
            "roll": "Roll (°)",
            "pitch": "Pitch (°)",
            "yaw": "Yaw (°)",
            "gx": "Gyro X (°/s)",
            "gy": "Gyro Y (°/s)",
            "gz": "Gyro Z (°/s)",
            "ax": "Accel X (g)",
            "ay": "Accel Y (g)",
            "az": "Accel Z (g)",
            "roll_raw": "Raw Roll (°)",
            "pitch_raw": "Raw Pitch (°)",
            "yaw_raw": "Raw Yaw (°)",
        }
        self.chart_axis_label_map = {label: key for key, label in self.chart_axis_options.items()}
        self.chart_axis_label_var = tk.StringVar(value=self.chart_axis_options["roll"])
        self.chart_manual_min = tk.StringVar(value="-180")
        self.chart_manual_max = tk.StringVar(value="180")
        
        # Statistics
        self.stats_samples = 0
        self.stats_sum_roll = 0
        self.stats_sum_pitch = 0
        self.stats_sum_yaw = 0
        self.stats_sum_sq_roll = 0
        self.stats_sum_sq_pitch = 0
        self.stats_sum_sq_yaw = 0
        self.stats_min_roll = float("inf")
        self.stats_min_pitch = float("inf")
        self.stats_min_yaw = float("inf")
        self.stats_max_roll = float("-inf")
        self.stats_max_pitch = float("-inf")
        self.stats_max_yaw = float("-inf")
        self.stats_min_roll = float("inf")
        self.stats_min_pitch = float("inf")
        self.stats_min_yaw = float("inf")
        self.stats_max_roll = float("-inf")
        self.stats_max_pitch = float("-inf")
        self.stats_max_yaw = float("-inf")
        self.sample_interval_history = deque(maxlen=2000)
        self.last_sample_timestamp = None
        self.latest_sample = {"time": 0.0}
        for key in self.chart_keys:
            self.latest_sample[key] = math.nan
        
        # UI state
        self.auto_update_3d = tk.BooleanVar(value=True)
        self.autoscroll = tk.BooleanVar(value=True)
        self.show_chart = tk.BooleanVar(value=True)
        self.chart_mode = tk.StringVar(value="drift")  # drift, raw, comparison
        self.paused = False
        self.connected = False
        self.data_format = "Unknown"
        self.expected_sample_rate = None
        self.sample_rate_warning_active = False
        self.recording_indicator = tk.StringVar(value="⚪ Not Recording")
        self.recording_light_color = tk.StringVar(value="#444444")
        self.sample_counter_var = tk.StringVar(value="Samples: 0")
        self.data_rate_var = tk.StringVar(value="Rate: 0.0 Hz")
        self.command_history = deque(maxlen=200)
        self.recording_active = False
        self.recording_start_time = None
        self.recording_capture_active = False
        self.recordings = []
        self.recording_session_counter = 0
        self.record_elapsed_var = tk.StringVar(value="Elapsed: 00:00")
        self.record_status_text = tk.StringVar(value="Not Recording")
        self.recording_current_blocks = []
        self.record_timer_job = None
        self.recording_start_block_id = None
        self.pending_recording_finalize = False
        self.free_run_var = tk.BooleanVar(value=False)
        self.stats_samples_var = tk.StringVar(value="Samples: 0")
        self.stats_current_var = tk.StringVar(value="Current: R=0.00° P=0.00° Y=0.00°")
        self.stats_mean_var = tk.StringVar(value="Mean: R=0.00° P=0.00° Y=0.00°")
        self.stats_std_var = tk.StringVar(value="StdDev: R=0.00° P=0.00° Y=0.00°")
        self.stats_min_var = tk.StringVar(value="Min: R=0.00° P=0.00° Y=0.00°")
        self.stats_max_var = tk.StringVar(value="Max: R=0.00° P=0.00° Y=0.00°")
        self.stats_drift_var = tk.StringVar(value="Drift Rate: 0.00°/min")
        self.stats_quality_var = tk.StringVar(value="Quality: n/a")
        self.stats_rate_var = tk.StringVar(value="Sample Rate: 0.0 Hz")
        self.stats_quality_color = "#00ff00"
        self.suggestion_var = tk.StringVar(value="Suggestion: Monitor drift performance")
        
        # Command builder state
        self.cmd_mode = tk.StringVar(value="FILTERED")
        self.cmd_rate = tk.StringVar(value="100")
        self.cmd_duration = tk.StringVar(value="60")
        self.cmd_samples = tk.StringVar(value="")
        self.cmd_alpha = tk.DoubleVar(value=0.98)
        self.cmd_calibrate = tk.StringVar(value="1000")
        self.manual_preview_var = tk.StringVar(value="")
        self.custom_command_var = tk.StringVar()
        self.alpha_display_var = tk.StringVar(value="0.98")
        self.preset_hint_var = tk.StringVar(value="Select a preset to populate default commands.")
        self.command_presets: List[CommandPreset] = [
            CommandPreset("Static Drift Test", "5 min filtered capture @100Hz",
                          ["MODE:FILTERED", "RATE:100", "DURATION:300", "START"]),
            CommandPreset("Raw Data Analysis", "5000 raw samples @500Hz",
                          ["MODE:RAW", "RATE:500", "SAMPLES:5000", "START"]),
            CommandPreset("Filter Comparison", "30 sec both modes @200Hz",
                          ["MODE:BOTH", "RATE:200", "DURATION:30", "START"]),
            CommandPreset("Quick Calibration", "Collect calibration samples",
                          ["CALIBRATE:1000"]),
        ]
        for var in (self.cmd_mode, self.cmd_rate, self.cmd_duration, self.cmd_samples):
            var.trace_add("write", self.update_manual_preview)
        self.chart_mode.trace_add("write", self.on_chart_mode_changed)
        
        # IMU data
        self.roll = 0
        self.pitch = 0
        self.yaw = 0
        
        # ESP32 status
        self.esp_mode = "UNKNOWN"
        self.esp_rate = "0"
        self.esp_alpha = "0.00"
        
        # 3D update throttling
        self.last_3d_update = 0
        self.min_3d_interval = 0.016  # 60 FPS
        
        # Chart update throttling
        self.last_chart_update = 0
        self.min_chart_interval = 0.1  # 10 FPS
        
        # Statistics update throttling
        self.last_stats_update = 0
        self.min_stats_interval = 0.5  # 2 FPS
        
        # Batch text updates
        self.pending_log_lines = []
        self.last_log_update = 0
        self.log_update_interval = 0.1
        
        # 3D view
        self.view_elev = 20
        self.view_azim = 45
        
        self.setup_ui()
        self.update_loop()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.logger.info("UI setup complete")
    
    def setup_ui(self):
        """Create UI"""
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background="#1e1e1e", foreground="white", fieldbackground="#2b2b2b")
        style.configure("TButton", background="#333", foreground="white", padding=6)
        style.configure("TLabel", background="#1e1e1e", foreground="white")
        style.configure("TCheckbutton", background="#1e1e1e", foreground="white")
        style.configure("TRadiobutton", background="#1e1e1e", foreground="white")
        style.configure("TFrame", background="#1e1e1e")
        style.configure("TLabelframe", background="#1e1e1e", foreground="white")
        style.configure("TLabelframe.Label", background="#1e1e1e", foreground="white")
        
        # Main container: 30% left, 70% right
        main = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg="#1e1e1e", sashwidth=4)
        main.pack(fill="both", expand=True, padx=10, pady=10)
        
        left = ttk.Frame(main, width=480)
        left.pack_propagate(False)
        
        right = ttk.Frame(main)
        
        main.add(left, width=480)
        main.add(right)
        
        self.create_left_panel(left)
        self.create_right_panel(right)
    
    def create_left_panel(self, parent):
        """Left panel: connection, command system, logging"""
        # Connection
        conn_frame = ttk.LabelFrame(parent, text="Connection", padding=10)
        conn_frame.pack(fill="x", pady=(0, 10))
        
        port_frame = ttk.Frame(conn_frame)
        port_frame.pack(fill="x", pady=5)
        ttk.Label(port_frame, text="Port:").pack(side="left", padx=(0, 5))
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(port_frame, textvariable=self.port_var, width=12, state="readonly")
        self.port_combo.pack(side="left", padx=(0, 5))
        ttk.Button(port_frame, text="↻", width=3, command=self.refresh_ports).pack(side="left")
        
        baud_frame = ttk.Frame(conn_frame)
        baud_frame.pack(fill="x", pady=5)
        ttk.Label(baud_frame, text="Baud:").pack(side="left", padx=(0, 5))
        self.baud_var = tk.StringVar(value="115200")
        ttk.Combobox(baud_frame, textvariable=self.baud_var,
                     values=["115200", "230400", "460800", "921600"],
                    width=12, state="readonly").pack(side="left")
        
        self.connect_btn = tk.Button(conn_frame, text="Connect", command=self.toggle_connection,
                                     bg="#22aa55", fg="white", font=("Segoe UI", 10, "bold"),
                                     relief=tk.RAISED, bd=2, cursor="hand2")
        self.connect_btn.pack(fill="x", pady=(10, 5))
        
        self.pause_btn = tk.Button(conn_frame, text="⏸ Pause", command=self.toggle_pause,
                                   bg="#ff8800", fg="white", font=("Segoe UI", 9, "bold"),
                                   relief=tk.RAISED, bd=2, cursor="hand2", state="disabled")
        self.pause_btn.pack(fill="x")
        
        # Presets
        preset_frame = ttk.LabelFrame(parent, text="Command Presets", padding=10)
        preset_frame.pack(fill="x", pady=(0, 10))
        
        for idx, preset in enumerate(self.command_presets):
            btn = ttk.Button(preset_frame, text=preset.name, command=lambda p=preset: self.apply_command_preset(p))
            btn.grid(row=idx, column=0, sticky="ew", pady=2)
        preset_frame.columnconfigure(0, weight=1)
        
        preset_hint = ttk.Label(preset_frame, textvariable=self.preset_hint_var, wraplength=420, foreground="#bbbbbb", justify="left")
        preset_hint.grid(row=len(self.command_presets), column=0, sticky="w", pady=(6, 0))
        
        preset_actions = ttk.Frame(preset_frame)
        preset_actions.grid(row=len(self.command_presets)+1, column=0, sticky="ew", pady=(10, 0))
        ttk.Button(preset_actions, text="STATUS", command=lambda: self.send_command_sequence(["STATUS"])).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(preset_actions, text="RESET", command=lambda: self.send_command_sequence(["RESET"])).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(preset_actions, text="STOP", command=lambda: self.send_command_sequence(["STOP"])).pack(side="left", expand=True, fill="x", padx=2)
        
        # Manual command builder
        cmd_frame = ttk.LabelFrame(parent, text="Manual Command Builder", padding=10)
        cmd_frame.pack(fill="x", pady=(0, 10))
        cmd_frame.columnconfigure(1, weight=1)
        
        ttk.Label(cmd_frame, text="Mode:").grid(row=0, column=0, sticky="w")
        mode_combo = ttk.Combobox(cmd_frame, textvariable=self.cmd_mode,
                                  values=["RAW", "FILTERED", "BOTH"], width=14, state="readonly")
        mode_combo.grid(row=0, column=1, sticky="ew", pady=2)
        
        ttk.Label(cmd_frame, text="Rate (Hz):").grid(row=1, column=0, sticky="w")
        rate_combo = ttk.Combobox(cmd_frame, textvariable=self.cmd_rate,
                                  values=["50", "100", "200", "500"], width=14, state="readonly")
        rate_combo.grid(row=1, column=1, sticky="ew", pady=2)
        
        ttk.Label(cmd_frame, text="Duration (s):").grid(row=2, column=0, sticky="w")
        ttk.Entry(cmd_frame, textvariable=self.cmd_duration).grid(row=2, column=1, sticky="ew", pady=2)
        
        ttk.Label(cmd_frame, text="Samples:").grid(row=3, column=0, sticky="w")
        ttk.Entry(cmd_frame, textvariable=self.cmd_samples).grid(row=3, column=1, sticky="ew", pady=2)
        
        alpha_frame = ttk.Frame(cmd_frame)
        alpha_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=4)
        ttk.Label(alpha_frame, text="Alpha:").pack(side="left")
        self.alpha_scale = ttk.Scale(alpha_frame, from_=0.0, to=1.0, variable=self.cmd_alpha, command=self.on_alpha_change)
        self.alpha_scale.pack(side="left", fill="x", expand=True, padx=(6, 6))
        ttk.Label(alpha_frame, textvariable=self.alpha_display_var, width=5).pack(side="right")
        
        calib_frame = ttk.Frame(cmd_frame)
        calib_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=4)
        ttk.Label(calib_frame, text="Calibrate (samples):").pack(side="left")
        ttk.Entry(calib_frame, textvariable=self.cmd_calibrate, width=8).pack(side="left", padx=(5, 10))
        ttk.Button(calib_frame, text="Send", command=self.send_calibration_command).pack(side="left")
        
        ttk.Label(cmd_frame, text="Preview:").grid(row=6, column=0, sticky="nw", pady=(6, 0))
        preview_label = ttk.Label(cmd_frame, textvariable=self.manual_preview_var, font=("Consolas", 9),
                                  wraplength=420, justify="left")
        preview_label.grid(row=6, column=1, sticky="ew", pady=(6, 0))
        
        ttk.Checkbutton(cmd_frame, text="Enable Free Run (continuous)", variable=self.free_run_var,
                        command=self.update_manual_preview).grid(row=7, column=0, columnspan=2, sticky="w", pady=(6, 0))
        
        cmd_buttons = ttk.Frame(cmd_frame)
        cmd_buttons.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(cmd_buttons, text="Send Sequence", command=self.send_manual_command).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(cmd_buttons, text="START", command=lambda: self.send_command_sequence(["START"])).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(cmd_buttons, text="FREE RUN", command=self.send_free_run_command).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(cmd_buttons, text="STOP", command=lambda: self.send_command_sequence(["STOP"])).pack(side="left", expand=True, fill="x", padx=2)
        
        custom_frame = ttk.Frame(cmd_frame)
        custom_frame.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Entry(custom_frame, textvariable=self.custom_command_var).pack(side="left", fill="x", expand=True)
        ttk.Button(custom_frame, text="Send Command", command=self.send_custom_command).pack(side="left", padx=(6, 0))
        
        # Command history
        history_frame = ttk.LabelFrame(parent, text="Command History", padding=10)
        history_frame.pack(fill="x", pady=(0, 10))
        self.history_list = tk.Listbox(history_frame, height=6, bg="#0d0d0d", fg="#00ff00", font=("Consolas", 9))
        self.history_list.pack(fill="x")
        
        # Recording controls
        rec_frame = ttk.LabelFrame(parent, text="Recording Controls", padding=10)
        rec_frame.pack(fill="x", pady=(0, 10))
        
        rec_top = ttk.Frame(rec_frame)
        rec_top.pack(fill="x")
        self.record_btn = tk.Button(rec_top, text="⬤ Start Recording", command=self.toggle_recording,
                                    bg="#bb2244", fg="white", font=("Segoe UI", 10, "bold"),
                                    relief=tk.RAISED, bd=2, cursor="hand2")
        self.record_btn.pack(side="left", padx=(0, 6))
        
        self.record_canvas = tk.Canvas(rec_top, width=26, height=26, bg="#1e1e1e", highlightthickness=0)
        self.record_canvas.pack(side="left", padx=(6, 6))
        self.record_indicator_item = self.record_canvas.create_oval(4, 4, 22, 22,
                                                                    fill=self.recording_light_color.get(),
                                                                    outline="")
        ttk.Label(rec_top, textvariable=self.record_status_text).pack(side="left")
        
        rec_stats = ttk.Frame(rec_frame)
        rec_stats.pack(fill="x", pady=(8, 0))
        ttk.Label(rec_stats, textvariable=self.sample_counter_var).pack(side="left")
        ttk.Label(rec_stats, textvariable=self.record_elapsed_var).pack(side="left", padx=(10, 0))
        ttk.Label(rec_stats, textvariable=self.data_rate_var).pack(side="right")
        
        # Session manager
        session_frame = ttk.LabelFrame(parent, text="Session Manager", padding=10)
        session_frame.pack(fill="x", pady=(0, 10))
        self.session_list = tk.Listbox(session_frame, height=4, bg="#0d0d0d", fg="#00ff00",
                                       font=("Consolas", 9), selectmode=tk.EXTENDED)
        self.session_list.pack(fill="x")
        session_btns = ttk.Frame(session_frame)
        session_btns.pack(fill="x", pady=(6, 0))
        ttk.Button(session_btns, text="Open", command=self.open_selected_session_folder).pack(side="left", padx=2)
        ttk.Button(session_btns, text="Export", command=self.export_selected_session).pack(side="left", padx=2)
        ttk.Button(session_btns, text="Load", command=self.load_selected_session).pack(side="left", padx=2)
        ttk.Button(session_btns, text="Compare", command=self.compare_selected_sessions).pack(side="left", padx=2)
        ttk.Button(session_btns, text="Delete", command=self.delete_selected_session).pack(side="right", padx=2)
        
        # ESP32 Status
        status_frame = ttk.LabelFrame(parent, text="ESP32 Status", padding=10)
        status_frame.pack(fill="x", pady=(0, 10))
        
        self.status_text = tk.Text(status_frame, height=4, bg="#0d0d0d", fg="#00ff00",
                                   font=("Consolas", 9), relief=tk.FLAT)
        self.status_text.pack(fill="x")
        self.update_status_display()
        
        # Serial Monitor
        log_frame = ttk.LabelFrame(parent, text="Serial Monitor", padding=10)
        log_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10,
                                                  background="#0d0d0d", foreground="#00ff00",
                                                  insertbackground="white", font=("Consolas", 8))
        self.log_text.pack(fill="both", expand=True)
        self.log_text.config(state="disabled")
        
        # Export & Analysis
        action_frame = ttk.LabelFrame(parent, text="Export & Analysis", padding=10)
        action_frame.pack(fill="x", pady=(0, 10))
        ttk.Button(action_frame, text="Export Data…", command=self.export_data_dialog).pack(side="left", padx=(0, 5))
        ttk.Button(action_frame, text="Export Values…", command=self.export_current_values).pack(side="left", padx=(0, 5))
        ttk.Button(action_frame, text="Import CSV…", command=self.import_data_from_csv).pack(side="left", padx=(0, 5))
        ttk.Button(action_frame, text="Reference PDF", command=self.generate_reference_pdf).pack(side="left", padx=(0, 5))
        ttk.Button(action_frame, text="Clear Monitor", command=self.clear_log).pack(side="left", padx=(0, 5))
        ttk.Button(action_frame, text="Debug Log", command=self.show_debug_log).pack(side="left")
        
        self.refresh_ports()
        self.update_manual_preview()
        self.refresh_recording_indicator()
        self.update_session_list()
    
    def create_right_panel(self, parent):
        """Right panel: 3D view + chart"""
        # Top: 3D visualization
        viz_frame = ttk.LabelFrame(parent, text="IMU Orientation (3D)", padding=10)
        viz_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # 3D controls
        ctrl = ttk.Frame(viz_frame)
        ctrl.pack(fill="x", pady=(0, 10))
        
        ttk.Label(ctrl, text="View:").pack(side="left", padx=(0, 10))
        ttk.Button(ctrl, text="Top", width=8, command=lambda: self.set_view(90, 0)).pack(side="left", padx=2)
        ttk.Button(ctrl, text="Front", width=8, command=lambda: self.set_view(0, 0)).pack(side="left", padx=2)
        ttk.Button(ctrl, text="Side", width=8, command=lambda: self.set_view(0, 90)).pack(side="left", padx=2)
        ttk.Button(ctrl, text="Iso", width=8, command=lambda: self.set_view(20, 45)).pack(side="left", padx=2)
        ttk.Button(ctrl, text="Reset", width=8, command=self.reset_drone).pack(side="left", padx=2)
        
        ttk.Checkbutton(ctrl, text="Auto-update", variable=self.auto_update_3d).pack(side="right")
        
        # 3D figure
        self.fig_3d = plt.Figure(figsize=(8, 6), facecolor="#000000", dpi=80)
        self.ax_3d = self.fig_3d.add_subplot(111, projection="3d")
        self.ax_3d.set_facecolor("#000000")
        self.ax_3d.set_xlim(-4, 4)
        self.ax_3d.set_ylim(-4, 4)
        self.ax_3d.set_zlim(-3, 3)
        self.ax_3d.set_box_aspect([4, 4, 3])
        self.ax_3d.view_init(elev=20, azim=45)
        self.ax_3d.set_xlabel("")
        self.ax_3d.set_ylabel("")
        self.ax_3d.set_zlabel("")
        self.ax_3d.set_xticks([])
        self.ax_3d.set_yticks([])
        self.ax_3d.set_zticks([])
        self.ax_3d.grid(True, color="white", linestyle="--", linewidth=2, alpha=0.6)
        
        self.create_drone_model()
        
        self.canvas_3d = FigureCanvasTkAgg(self.fig_3d, viz_frame)
        self.canvas_3d.get_tk_widget().pack(fill="both", expand=True)
        
        # Bottom: Chart
        chart_frame = ttk.LabelFrame(parent, text="Real-Time Chart", padding=10)
        chart_frame.pack(fill="both", expand=True)
        
        # Chart controls
        chart_ctrl = ttk.Frame(chart_frame)
        chart_ctrl.pack(fill="x", pady=(0, 10))
        
        view_row = ttk.Frame(chart_ctrl)
        view_row.pack(fill="x")
        ttk.Label(view_row, text="View:").pack(side="left", padx=(0, 10))
        ttk.Radiobutton(view_row, text="Drift", variable=self.chart_mode, value="drift").pack(side="left", padx=4)
        ttk.Radiobutton(view_row, text="Raw Sensors", variable=self.chart_mode, value="raw").pack(side="left", padx=4)
        ttk.Radiobutton(view_row, text="Comparison", variable=self.chart_mode, value="comparison").pack(side="left", padx=4)
        ttk.Radiobutton(view_row, text="Per-Axis", variable=self.chart_mode, value="axis").pack(side="left", padx=4)
        ttk.Checkbutton(view_row, text="Show Chart", variable=self.show_chart).pack(side="right")
        
        options_row = ttk.Frame(chart_ctrl)
        options_row.pack(fill="x", pady=(6, 0))
        ttk.Label(options_row, text="Time Window:").pack(side="left")
        self.chart_window_combo = ttk.Combobox(options_row, textvariable=self.chart_window_var,
                                               values=["10s", "30s", "1min", "5min", "all"], width=8, state="readonly")
        self.chart_window_combo.pack(side="left", padx=(4, 12))
        ttk.Checkbutton(options_row, text="Auto-scale", variable=self.chart_autoscale,
                        command=self.on_chart_autoscale_toggle).pack(side="left")
        self.chart_min_entry = ttk.Entry(options_row, textvariable=self.chart_manual_min, width=8)
        self.chart_max_entry = ttk.Entry(options_row, textvariable=self.chart_manual_max, width=8)
        ttk.Label(options_row, text="Y Min:").pack(side="left", padx=(12, 2))
        self.chart_min_entry.pack(side="left")
        ttk.Label(options_row, text="Y Max:").pack(side="left", padx=(12, 2))
        self.chart_max_entry.pack(side="left")
        
        axis_row = ttk.Frame(chart_ctrl)
        axis_row.pack(fill="x", pady=(6, 0))
        ttk.Label(axis_row, text="Axis:").pack(side="left")
        self.chart_axis_combo = ttk.Combobox(axis_row, textvariable=self.chart_axis_label_var,
                                             values=list(self.chart_axis_options.values()), width=18, state="readonly")
        self.chart_axis_combo.pack(side="left", padx=(4, 12))
        self.chart_axis_combo.bind("<<ComboboxSelected>>", self.on_chart_axis_selected)
        
        action_row = ttk.Frame(chart_ctrl)
        action_row.pack(fill="x", pady=(6, 0))
        self.chart_pause_btn = ttk.Button(action_row, text="Pause", command=self.toggle_chart_pause)
        self.chart_pause_btn.pack(side="left", padx=2)
        ttk.Button(action_row, text="Clear", command=self.clear_chart).pack(side="left", padx=2)
        ttk.Button(action_row, text="Export Chart", command=self.export_chart).pack(side="left", padx=2)
        ttk.Button(action_row, text="Reset Scale", command=self.reset_chart_scale).pack(side="left", padx=2)
        ttk.Button(action_row, text="Refresh", command=self.update_chart).pack(side="left", padx=2)
        ttk.Label(action_row, textvariable=self.data_rate_var).pack(side="right")
        
        stats_panel = ttk.LabelFrame(parent, text="Statistics & Analysis", padding=10)
        stats_panel.pack(fill="x", pady=(10, 0))
        ttk.Label(stats_panel, textvariable=self.stats_samples_var).pack(anchor="w")
        ttk.Label(stats_panel, textvariable=self.stats_current_var).pack(anchor="w")
        ttk.Label(stats_panel, textvariable=self.stats_mean_var).pack(anchor="w")
        ttk.Label(stats_panel, textvariable=self.stats_std_var).pack(anchor="w")
        ttk.Label(stats_panel, textvariable=self.stats_min_var).pack(anchor="w")
        ttk.Label(stats_panel, textvariable=self.stats_max_var).pack(anchor="w")
        ttk.Label(stats_panel, textvariable=self.stats_drift_var).pack(anchor="w")
        self.drift_quality_label = ttk.Label(stats_panel, textvariable=self.stats_quality_var, foreground=self.stats_quality_color)
        self.drift_quality_label.pack(anchor="w")
        ttk.Label(stats_panel, textvariable=self.stats_rate_var).pack(anchor="w")
        ttk.Label(stats_panel, textvariable=self.suggestion_var).pack(anchor="w")
        self.update_stats_display()
        
        # Chart figure
        self.fig_chart = plt.Figure(figsize=(10, 4), facecolor="#0d0d0d", dpi=80)
        self.ax_chart = self.fig_chart.add_subplot(111)
        self.ax_chart.set_facecolor("#0d0d0d")
        self.ax_chart.grid(True, color="#333", linestyle="--", alpha=0.5)
        self.ax_chart.set_xlabel("Time (s)", color="white")
        self.ax_chart.set_ylabel("Angle (°)", color="white")
        self.ax_chart.tick_params(colors="white")
        
        self.canvas_chart = FigureCanvasTkAgg(self.fig_chart, chart_frame)
        self.canvas_chart.get_tk_widget().pack(fill="both", expand=True)
    
        self.chart_window_combo.bind("<<ComboboxSelected>>", lambda event: self.update_chart())
        self.on_chart_autoscale_toggle()
        self.on_chart_mode_changed()
    
    def refresh_recording_indicator(self):
        if hasattr(self, "record_canvas"):
            self.record_canvas.itemconfig(self.record_indicator_item, fill=self.recording_light_color.get())
        if hasattr(self, "record_status_text"):
            self.record_status_text.set(self.recording_indicator.get())
    
    def on_alpha_change(self, value):
        try:
            val = float(value)
        except (TypeError, ValueError):
            val = self.cmd_alpha.get()
        self.alpha_display_var.set(f"{val:.2f}")
        self.update_manual_preview()
    
    def update_manual_preview(self, *args):
        commands = []
        mode = self.cmd_mode.get().strip().upper()
        if mode:
            commands.append(f"MODE:{mode}")
        rate = self.cmd_rate.get().strip()
        if rate:
            commands.append(f"RATE:{rate}")
        duration = self.cmd_duration.get().strip()
        samples = self.cmd_samples.get().strip()
        if duration and not self.free_run_var.get():
            commands.append(f"DURATION:{duration}")
        if samples and not self.free_run_var.get():
            commands.append(f"SAMPLES:{samples}")
        alpha = self.cmd_alpha.get()
        commands.append(f"ALPHA:{alpha:.2f}")
        commands.append("FREE" if self.free_run_var.get() else "START")
        self.manual_preview_var.set(" | ".join(commands))
    
    def apply_command_preset(self, preset: CommandPreset):
        """Apply preset settings and send commands"""
        self.preset_hint_var.set(preset.description)
        self.cmd_samples.set("")
        self.cmd_duration.set("")
        self.free_run_var.set(False)
        for cmd in preset.commands:
            if ":" not in cmd:
                continue
            key, val = cmd.split(":", 1)
            key = key.strip().upper()
            val = val.strip()
            if key == "MODE":
                self.cmd_mode.set(val.upper())
            elif key == "RATE":
                self.cmd_rate.set(val)
            elif key == "DURATION":
                self.cmd_duration.set(val)
            elif key == "SAMPLES":
                self.cmd_samples.set(val)
            elif key == "ALPHA":
                try:
                    self.cmd_alpha.set(float(val))
                    self.alpha_display_var.set(f"{float(val):.2f}")
                except ValueError:
                    pass
        self.update_manual_preview()
        self.send_command_sequence(preset.commands)
    
    def update_command_history_display(self):
        if not hasattr(self, "history_list"):
            return
        self.history_list.delete(0, tk.END)
        for ts, cmd in list(self.command_history):
            time_str = datetime.fromtimestamp(ts).strftime("%H:%M:%S")
            self.history_list.insert(0, f"{time_str}  {cmd}")
    
    def send_command_sequence(self, commands, delay=0.05):
        if isinstance(commands, str):
            commands = [cmd.strip() for cmd in commands.splitlines() if cmd.strip()]
        if not commands:
            return False
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect to the ESP32 before sending commands.")
            return False
        for idx, cmd in enumerate(commands):
            self.send_command_direct(cmd)
            if delay and idx < len(commands) - 1:
                time.sleep(delay)
        return True
    
    def send_manual_command(self):
        """Send manually configured command sequence"""
        commands = []
        mode = self.cmd_mode.get().strip().upper()
        if mode:
            commands.append(f"MODE:{mode}")
        rate = self.cmd_rate.get().strip()
        if rate:
            commands.append(f"RATE:{rate}")
        duration = self.cmd_duration.get().strip()
        samples = self.cmd_samples.get().strip()
        if duration and not self.free_run_var.get():
            commands.append(f"DURATION:{duration}")
        if samples and not self.free_run_var.get():
            commands.append(f"SAMPLES:{samples}")
        alpha = self.cmd_alpha.get()
        commands.append(f"ALPHA:{alpha:.2f}")
        final_command = "FREE" if self.free_run_var.get() else "START"
        commands.append(final_command)
        sent = self.send_command_sequence(commands)
        if sent:
            self.update_manual_preview()
    
    def send_free_run_command(self):
        self.free_run_var.set(True)
        self.update_manual_preview()
        self.send_manual_command()
    
    def send_calibration_command(self):
        value = self.cmd_calibrate.get().strip()
        if not value.isdigit():
            messagebox.showerror("Invalid Value", "Calibration samples must be a positive integer.")
            return
        self.send_command_sequence([f"CALIBRATE:{value}"])
    
    def send_custom_command(self):
        cmd_text = self.custom_command_var.get().strip()
        if not cmd_text:
            return
        if "\n" in cmd_text or ";" in cmd_text:
            parts = re.split(r'[;\n]+', cmd_text)
        else:
            parts = [cmd_text]
        commands = [p.strip() for p in parts if p.strip()]
        self.send_command_sequence(commands)
        self.custom_command_var.set("")
    
    def toggle_recording(self):
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect first to control recording.")
            return
        if not self.recording_active:
            self.recording_active = True
            self.recording_capture_active = True
            self.pending_recording_finalize = False
            self.recording_current_blocks = []
            self.record_btn.config(text="■ Stop Recording", bg="#1e3a8a")
            self.recording_indicator.set("🟢 Recording")
            self.recording_light_color.set("#bb2233")
            self.refresh_recording_indicator()
            self.recording_start_time = time.time()
            self.recording_start_block_id = self.data_block_counter
            self.sample_counter_var.set("Samples: 0")
            self.update_recording_timer()
            self.send_command_sequence(["START"])
        else:
            self.recording_active = False
            self.recording_capture_active = False
            self.record_btn.config(text="⬤ Start Recording", bg="#bb2244")
            self.recording_indicator.set("⚪ Not Recording")
            self.recording_light_color.set("#444444")
            self.refresh_recording_indicator()
            self.stop_recording_timer()
            self.send_command_sequence(["STOP"])
            self.pending_recording_finalize = True
            self.root.after(1200, self._finalize_recording_if_pending)
    
    def export_data_dialog(self):
        if not self.data_blocks:
            messagebox.showinfo("No Data", "No captured data blocks available to export yet.")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Export Data")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg="#1e1e1e")
        dialog.geometry("640x640")
        
        block_frame = ttk.LabelFrame(dialog, text="Data Blocks", padding=10)
        block_frame.pack(fill="both", expand=True, padx=10, pady=10)
        block_scroll = ttk.Scrollbar(block_frame, orient=tk.VERTICAL)
        block_list = tk.Listbox(block_frame, selectmode=tk.MULTIPLE, height=8,
                                bg="#0d0d0d", fg="#00ff00", activestyle="dotbox",
                                highlightbackground="#444444", selectbackground="#2563eb")
        block_scroll.pack(side="right", fill="y")
        block_list.pack(side="left", fill="both", expand=True)
        block_list.config(yscrollcommand=block_scroll.set)
        block_scroll.config(command=block_list.yview)
        for block in self.data_blocks:
            block_list.insert(tk.END, self.describe_block(block))
        
        range_frame = ttk.LabelFrame(dialog, text="Time Range", padding=10)
        range_frame.pack(fill="x", padx=10, pady=(0, 10))
        range_var = tk.StringVar(value="all")
        last_minutes_var = tk.StringVar(value="1")
        custom_start_var = tk.StringVar(value="0")
        custom_end_var = tk.StringVar(value="60")
        
        ttk.Radiobutton(range_frame, text="All data", variable=range_var, value="all").grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(range_frame, text="Last N minutes", variable=range_var, value="last").grid(row=1, column=0, sticky="w")
        ttk.Radiobutton(range_frame, text="Custom range (seconds)", variable=range_var, value="custom").grid(row=2, column=0, sticky="w")
        ttk.Radiobutton(range_frame, text="Between markers (selected blocks)", variable=range_var, value="markers").grid(row=3, column=0, sticky="w")
        
        ttk.Label(range_frame, text="Minutes:").grid(row=1, column=1, padx=(10, 2))
        last_entry = ttk.Entry(range_frame, textvariable=last_minutes_var, width=10)
        last_entry.grid(row=1, column=2, padx=(0, 10))
        
        ttk.Label(range_frame, text="Start (s):").grid(row=2, column=1, padx=(10, 2))
        custom_start_entry = ttk.Entry(range_frame, textvariable=custom_start_var, width=10)
        custom_start_entry.grid(row=2, column=2, padx=(0, 10))
        ttk.Label(range_frame, text="End (s):").grid(row=2, column=3, padx=(10, 2))
        custom_end_entry = ttk.Entry(range_frame, textvariable=custom_end_var, width=10)
        custom_end_entry.grid(row=2, column=4, padx=(0, 10))
        
        options_frame = ttk.LabelFrame(dialog, text="Export Options", padding=10)
        options_frame.pack(fill="x", padx=10, pady=(0, 10))
        include_metadata_var = tk.BooleanVar(value=True)
        include_stats_var = tk.BooleanVar(value=True)
        include_chart_var = tk.BooleanVar(value=True)
        include_3d_var = tk.BooleanVar(value=False)
        
        ttk.Checkbutton(options_frame, text="Include metadata headers", variable=include_metadata_var).pack(anchor="w")
        ttk.Checkbutton(options_frame, text="Include statistics summary", variable=include_stats_var).pack(anchor="w")
        ttk.Checkbutton(options_frame, text="Include chart image (PNG/SVG)", variable=include_chart_var).pack(anchor="w")
        ttk.Checkbutton(options_frame, text="Include 3D orientation snapshot", variable=include_3d_var).pack(anchor="w")
        
        naming_frame = ttk.LabelFrame(dialog, text="Output", padding=10)
        naming_frame.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Label(naming_frame, text="Base file name:").grid(row=0, column=0, sticky="w")
        default_name = datetime.now().strftime("imu_export_%Y-%m-%d_%H-%M-%S")
        base_name_var = tk.StringVar(value=default_name)
        ttk.Entry(naming_frame, textvariable=base_name_var, width=32).grid(row=0, column=1, padx=(5, 0))
        ttk.Label(naming_frame, text="(folder will be created under ./imu_exports)").grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
        
        status_var = tk.StringVar(value="")
        status_label = ttk.Label(dialog, textvariable=status_var, foreground="#facc15")
        status_label.pack(fill="x", padx=10, pady=(0, 10))
        
        def update_range_controls(*args):
            mode = range_var.get()
            if mode == "last":
                last_entry.config(state="normal")
            else:
                last_entry.config(state="disabled")
            if mode == "custom":
                custom_start_entry.config(state="normal")
                custom_end_entry.config(state="normal")
            else:
                custom_start_entry.config(state="disabled")
                custom_end_entry.config(state="disabled")
            if mode != "markers":
                status_var.set("")
        
        range_var.trace_add("write", update_range_controls)
        update_range_controls()
        
        def perform_export():
            nonlocal dialog
            try:
                selected_indices = block_list.curselection()
                if selected_indices:
                    blocks = [self.data_blocks[i] for i in selected_indices]
                else:
                    blocks = list(self.data_blocks)
                if range_var.get() == "markers" and not selected_indices:
                    status_var.set("Select at least one block for 'between markers' export.")
                    return
                block_rows_map = {block.block_id: self.collect_block_rows(block) for block in blocks}
                all_rows = [row for rows in block_rows_map.values() for row in rows]
                if not all_rows:
                    messagebox.showinfo("No Data", "No samples available within the selected blocks.")
                    return
                valid_abs = [row["time_absolute"] for row in all_rows if not math.isnan(row["time_absolute"])]
                if valid_abs:
                    latest_time = max(valid_abs)
                    time_accessor = lambda r: r["time_absolute"]
                else:
                    latest_time = max(row["timestamp"] for row in all_rows)
                    time_accessor = lambda r: r["timestamp"]
                range_mode = range_var.get()
                filtered_blocks = []
                try:
                    last_minutes = float(last_minutes_var.get())
                except ValueError:
                    last_minutes = 1.0
                try:
                    custom_start = float(custom_start_var.get())
                    custom_end = float(custom_end_var.get())
                except ValueError:
                    custom_start = 0.0
                    custom_end = 0.0
                if custom_end < custom_start:
                    custom_start, custom_end = custom_end, custom_start
                for block in blocks:
                    rows = block_rows_map[block.block_id]
                    filtered = []
                    for row in rows:
                        current_time = time_accessor(row)
                        if range_mode == "all" or range_mode == "markers":
                            filtered.append(row)
                        elif range_mode == "last":
                            cutoff = latest_time - last_minutes * 60.0
                            if current_time >= cutoff:
                                filtered.append(row)
                        elif range_mode == "custom":
                            if custom_start <= row["timestamp"] <= custom_end:
                                filtered.append(row)
                    if filtered:
                        filtered_blocks.append((block, filtered))
                if not filtered_blocks:
                    messagebox.showinfo("No Data", "No samples matched the selected time range.")
                    return
                
                export_root = os.path.join(os.getcwd(), "imu_exports")
                base_name = base_name_var.get().strip() or default_name
                folder = self._write_export_artifacts(
                    filtered_blocks,
                    base_name,
                    range_mode,
                    include_metadata_var.get(),
                    include_stats_var.get(),
                    include_chart_var.get(),
                    include_3d_var.get(),
                    export_root,
                )
                
                dialog.grab_release()
                dialog.destroy()
                messagebox.showinfo("Export Complete", f"Export saved to:\n{folder}")
            except Exception as exc:
                status_var.set(f"Export failed: {exc}")
                self.logger.error(f"Export error: {exc}")
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(button_frame, text="Cancel", command=lambda: (dialog.grab_release(), dialog.destroy())).pack(side="right")
        ttk.Button(button_frame, text="Export", command=perform_export).pack(side="right", padx=(0, 10))
    
    def show_debug_log(self):
        logs = self.logger.get_logs()
        if not logs:
            logs = "No debug logs captured."
        messagebox.showinfo("Debug Log", logs)

    def export_current_values(self):
        """Export current live buffer to CSV"""
        times = list(self.chart_data["time"])
        if not times:
            messagebox.showinfo("No Data", "No live data available to export.")
            return
        default_name = datetime.now().strftime("imu_live_%Y-%m-%d_%H-%M-%S.csv")
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=default_name,
                                            filetypes=[("CSV Files", "*.csv")])
        if not path:
            return
        try:
            data_lists = {key: list(self.chart_data[key]) for key in self.chart_keys}
            columns = ["time"] + self.chart_keys
            with open(path, "w", encoding="utf-8") as f:
                f.write(",".join(columns) + "\n")
                for idx, t in enumerate(times):
                    row_values = [f"{t:.6f}"]
                    for key in self.chart_keys:
                        values = data_lists.get(key, [])
                        value = values[idx] if idx < len(values) else float("nan")
                        if value is None or math.isnan(value):
                            row_values.append("")
                        else:
                            row_values.append(f"{value:.6f}")
                    f.write(",".join(row_values) + "\n")
            messagebox.showinfo("Export Complete", f"Live data exported to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export Failed", f"Unable to export data:\n{exc}")

    def import_data_from_csv(self):
        """Import external CSV data for analysis"""
        path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if not path:
            return
        try:
            rows = self._load_rows_from_csv(path)
            if not rows:
                messagebox.showinfo("No Data", "No usable rows found in selected file.")
                return
            self._display_loaded_rows(rows)
            self.last_block_summary = f"Imported data from '{os.path.basename(path)}'"
            self.update_status_display()
            messagebox.showinfo("Import Complete", "CSV data imported and analysed.")
        except Exception as exc:
            messagebox.showerror("Import Failed", f"Unable to import file:\n{exc}")
            self.logger.error(f"Import CSV error: {exc}")

    def generate_reference_pdf(self):
        """Generate reference PDF with feature overview and visuals"""
        docs_dir = os.path.join(os.getcwd(), "docs")
        os.makedirs(docs_dir, exist_ok=True)
        path = os.path.join(docs_dir, "IMU_monitor_reference.pdf")
        try:
            with PdfPages(path) as pdf:
                fig = plt.figure(figsize=(8.27, 11.69), facecolor="white")
                fig.suptitle("IMU Monitor Reference", fontsize=18, fontweight="bold")
                text_y = 0.92
                bullet_points = [
                    "Serial command system with presets and manual controls.",
                    "Data block parser with metadata, CRC validation, and session auto-save.",
                    "Real-time charting modes: drift, raw sensors, comparisons, per-axis views.",
                    "Statistics panel with drift analysis, sample-rate monitoring, and suggestions.",
                    "Export suite: block selection, live buffer export, session replays, PDF reference.",
                    "Recording workflow: auto-save sessions, comparison overlay, and CSV import.",
                    "Free run mode for continuous streaming without duration or sample limits.",
                ]
                for point in bullet_points:
                    fig.text(0.08, text_y, f"• {point}", fontsize=11)
                    text_y -= 0.045
                fig.text(0.08, text_y - 0.02, "Generated on: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                         fontsize=10, color="#555555")
                pdf.savefig(fig)
                plt.close(fig)

                # Visual page: sample chart
                fig, axes = plt.subplots(2, 1, figsize=(8.27, 11.69), facecolor="white")
                t = np.linspace(0, 30, 600)
                axes[0].plot(t, 5 * np.sin(t / 3), label="Roll", color="#ef4444")
                axes[0].plot(t, 4 * np.cos(t / 4), label="Pitch", color="#22c55e")
                axes[0].plot(t, 2 * np.sin(t / 5), label="Yaw", color="#06b6d4")
                axes[0].set_title("Sample Drift Plot", fontsize=14)
                axes[0].set_xlabel("Time (s)")
                axes[0].set_ylabel("Angle (°)")
                axes[0].grid(True, linestyle="--", alpha=0.5)
                axes[0].legend(loc="upper right")

                axes[1].plot(t, np.sin(t) * 50, label="Gyro X", color="#f97316")
                axes[1].plot(t, np.cos(t / 2) * 50, label="Gyro Y", color="#facc15")
                axes[1].plot(t, np.sin(t / 1.5) * 50, label="Gyro Z", color="#f43f5e")
                axes[1].set_title("Sample Raw Sensor Plot", fontsize=14)
                axes[1].set_xlabel("Time (s)")
                axes[1].set_ylabel("°/s")
                axes[1].grid(True, linestyle="--", alpha=0.5)
                axes[1].legend(loc="upper right")

                plt.tight_layout()
                pdf.savefig(fig)
                plt.close(fig)
            messagebox.showinfo("Reference Generated", f"Reference PDF saved to:\n{path}")
        except Exception as exc:
            messagebox.showerror("PDF Error", f"Failed to generate reference PDF:\n{exc}")
            self.logger.error(f"PDF generation error: {exc}")
    
    def create_drone_model(self):
        """Create simplified quadcopter model"""
        body_half_length = 0.6
        body_half_width = 0.2
        body_half_height = 0.05
        
        self.body_vertices_base = np.array([
            [-body_half_length, -body_half_width, -body_half_height],
            [ body_half_length, -body_half_width, -body_half_height],
            [ body_half_length,  body_half_width, -body_half_height],
            [-body_half_length,  body_half_width, -body_half_height],
            [-body_half_length, -body_half_width,  body_half_height],
            [ body_half_length, -body_half_width,  body_half_height],
            [ body_half_length,  body_half_width,  body_half_height],
            [-body_half_length,  body_half_width,  body_half_height],
        ])
        body_faces_idx = [
            [0, 1, 5, 4],
            [1, 2, 6, 5],
            [2, 3, 7, 6],
            [3, 0, 4, 7],
            [4, 5, 6, 7],
            [0, 1, 2, 3],
        ]
        body_faces = [[self.body_vertices_base[idx] for idx in face] for face in body_faces_idx]
        self.drone_body = Poly3DCollection(body_faces, alpha=0.85, facecolors='#1d4ed8', edgecolors='white', linewidths=1.0)
        self.ax_3d.add_collection3d(self.drone_body)
        
        arm_length = 1.2
        arm_height = 0.02
        self.arm_segments_base = [
            np.array([[0, 0, arm_height], [ arm_length,  0, arm_height]]),
            np.array([[0, 0, arm_height], [-arm_length,  0, arm_height]]),
            np.array([[0, 0, arm_height], [0,  arm_length, arm_height]]),
            np.array([[0, 0, arm_height], [0, -arm_length, arm_height]]),
        ]
        self.arm_collection = Line3DCollection(self.arm_segments_base, colors='#facc15', linewidths=4, alpha=0.9)
        self.ax_3d.add_collection3d(self.arm_collection)
        
        rotor_radius = 0.35
        rotor_z = arm_height + 0.02
        theta = np.linspace(0, 2 * np.pi, 60)
        def rotor_circle(center):
            circle = np.column_stack((
                center[0] + rotor_radius * np.cos(theta),
                center[1] + rotor_radius * np.sin(theta),
                np.full_like(theta, rotor_z)
            ))
            return circle
        
        rotor_centers = [
            np.array([ arm_length,  0, rotor_z]),
            np.array([-arm_length,  0, rotor_z]),
            np.array([0,  arm_length, rotor_z]),
            np.array([0, -arm_length, rotor_z]),
        ]
        self.rotor_segments_base = [rotor_circle(center) for center in rotor_centers]
        self.rotor_collection = Line3DCollection(self.rotor_segments_base, colors='#e5e7eb', linewidths=1.5, alpha=0.9)
        self.ax_3d.add_collection3d(self.rotor_collection)
        
        # Orientation vectors
        self.x_vec = self.ax_3d.quiver(0,0,0,1.5,0,0, color='#ef4444', arrow_length_ratio=0.2, linewidth=3)
        self.y_vec = self.ax_3d.quiver(0,0,0,0,1.5,0, color='#22c55e', arrow_length_ratio=0.2, linewidth=3)
        self.z_vec = self.ax_3d.quiver(0,0,0,0,0,1.5, color='#06b6d4', arrow_length_ratio=0.2, linewidth=3)
    
    def set_view(self, elev, azim):
        self.view_elev = elev
        self.view_azim = azim
        self.ax_3d.view_init(elev=elev, azim=azim)
        self.canvas_3d.draw_idle()
    
    def reset_drone(self):
        self.roll = self.pitch = self.yaw = 0
        self.update_3d()
    
    def refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_combo["values"] = ports
        if ports:
            self.port_combo.current(0)
    
    def toggle_connection(self):
        if self.connected:
            self.disconnect()
        else:
            self.connect()
    
    def connect(self):
        port = self.port_var.get()
        if not port:
            messagebox.showerror("Error", "Select a port")
            return
        
        try:
            baud = int(self.baud_var.get())
            self.serial_port = serial.Serial(port, baudrate=baud, timeout=0.1)
            self.reading = True
            threading.Thread(target=self.read_serial, daemon=True).start()
            self.connected = True
            self.connect_btn.config(text="Disconnect", bg="#d22")
            self.pause_btn.config(state="normal")
            self.logger.info(f"Connected to {port}")
            
            # Request status
            time.sleep(0.5)
            self.send_command_direct("STATUS")
        except Exception as e:
            messagebox.showerror("Error", f"Connection failed:\n{e}")
    
    def disconnect(self):
        if self.recording_active:
            self.recording_active = False
            self.pending_recording_finalize = True
        if self.pending_recording_finalize or self.recording_current_blocks:
            self.finalize_recording_session()
        self.reading = False
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except:
                pass
        self.connected = False
        self.connect_btn.config(text="Connect", bg="#22aa55")
        self.pause_btn.config(state="disabled")
        self.logger.info("Disconnected")
    
    def toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            self.pause_btn.config(text="▶ Resume", bg="#22aa55")
        else:
            self.pause_btn.config(text="⏸ Pause", bg="#ff8800")
    
    def send_preset(self, commands):
        """Send multiple commands from preset"""
        self.send_command_sequence(commands)
    
    def send_command_direct(self, cmd):
        """Send single command"""
        if not self.connected:
            return
        
        try:
            self.serial_port.write((cmd + "\n").encode())
            timestamp = time.time()
            self.data_queue.put(("sent", timestamp, cmd))
            self.logger.info(f"Sent: {cmd}")
            self.command_history.appendleft((timestamp, cmd))
            self.update_command_history_display()
        except Exception as e:
            self.logger.error(f"Send failed: {e}")
    
    def read_serial(self):
        """Background serial read thread"""
        self.logger.info("Serial thread started")
        try:
            while self.reading and self.serial_port and self.serial_port.is_open:
                try:
                    if self.serial_port.in_waiting:
                        line = self.serial_port.readline().decode(errors="ignore").strip()
                        if line:
                            timestamp = time.time()
                            try:
                                self.data_queue.put_nowait(("received", timestamp, line))
                            except queue.Full:
                                self.logger.warning("Queue full")
                except Exception as e:
                    self.logger.error(f"Read error: {e}")
                    break
                time.sleep(0.001)
        finally:
            self.logger.info("Serial thread stopped")
    
    def update_loop(self):
        """Main update loop"""
        try:
            if not self.paused:
                processed = 0
                while not self.data_queue.empty() and processed < 200:
                    try:
                        msg_type, timestamp, line = self.data_queue.get_nowait()
                        if msg_type == "received":
                            self.process_received(timestamp, line)
                        elif msg_type == "sent":
                            self.process_sent(timestamp, line)
                        processed += 1
                    except queue.Empty:
                        break
                
                # Batch log updates
                current_time = time.time()
                if self.pending_log_lines and current_time - self.last_log_update > self.log_update_interval:
                    self.flush_log_updates()
                    self.last_log_update = current_time
                
                # Update chart
                if self.show_chart.get() and current_time - self.last_chart_update > self.min_chart_interval:
                    self.update_chart()
                    self.last_chart_update = current_time
                
                # Update statistics
                if current_time - self.last_stats_update > self.min_stats_interval:
                    self.update_stats_display()
                    self.last_stats_update = current_time
                
                timed_out_block = self.parser.finalize_if_timed_out()
                if timed_out_block:
                    self.recording_block = False
                    timed_out_block.warnings.append("Timed out waiting for </DATA>")
                    self.pending_log_lines.append(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] ⚠ DATA BLOCK TIMEOUT\n")
                    self.handle_completed_block(timed_out_block)
                    
        except Exception as e:
            self.logger.error(f"Update loop error: {e}")
        finally:
            self.root.after(50, self.update_loop)
    
    def process_received(self, timestamp, line):
        """Process received line"""
        # Check for data block markers
        block_result = self.parser.parse_line(line, timestamp=timestamp)
        
        if line.startswith("<DATA"):
            self.recording_block = True
            self.current_block_metadata = self.parser.metadata
            self.block_sample_counter = 0
            self.block_start_timestamp = timestamp
            self.recording_indicator.set("🟢 Recording")
            self.recording_light_color.set("#22c55e")
            self.refresh_recording_indicator()
            self.sample_counter_var.set("Samples: 0")
            self.pending_log_lines.append(f"[{datetime.fromtimestamp(timestamp).strftime('%H:%M:%S.%f')[:-3]}] 🟢 DATA BLOCK START: {self.current_block_metadata}\n")
            return
        elif line == "</DATA>":
            self.recording_block = False
            self.pending_log_lines.append(f"[{datetime.fromtimestamp(timestamp).strftime('%H:%M:%S.%f')[:-3]}] 🔴 DATA BLOCK END\n")
            if block_result:
                self.handle_completed_block(block_result)
            return
        
        # Store all data
        self.log_data.append(("RX", timestamp, line))
        
        # Queue log text
        time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S.%f")[:-3]
        prefix = "[DATA] " if self.recording_block else ""
        self.pending_log_lines.append(f"[{time_str}] {prefix}{line}\n")
        
        # Parse status messages
        if line.startswith("[STATUS]"):
            self.parse_status_message(line)
        
        # Parse data rows
        if not line.startswith("[") and not line.startswith("<"):
            self.process_data_row(timestamp, line)
        
        if self.recording_block and self.parser.current_block:
            self.block_sample_counter = len(self.parser.current_block.lines)
            self.sample_counter_var.set(f"Samples: {self.block_sample_counter}")
            if self.block_start_timestamp:
                elapsed = max(timestamp - self.block_start_timestamp, 1e-3)
                rate = self.block_sample_counter / elapsed
                self.data_rate_var.set(f"Rate: {rate:.1f} Hz")
    
    def handle_completed_block(self, block: DataBlock):
        """Store completed data block"""
        block_samples = len(block.lines)
        meta_mode = block.metadata.get("MODE", self.current_block_metadata.get("MODE", "UNKNOWN"))
        meta_rate = block.metadata.get("RATE", self.current_block_metadata.get("RATE", "0"))
        alpha_val = block.metadata.get("ALPHA", self.current_block_metadata.get("ALPHA", "0"))
        block.block_id = self.data_block_counter
        self.data_block_counter += 1
        rate_float = self._parse_float(meta_rate)
        if rate_float:
            self.expected_sample_rate = rate_float
        
        if block.metadata:
            self.current_block_metadata = block.metadata.copy()
        block.sample_count_expected = self._parse_int(block.metadata.get("SAMPLES") or block.metadata.get("COUNT"))
        
        if block.sample_count_expected is not None and block_samples != block.sample_count_expected:
            block.warnings.append(f"Sample count mismatch expected={block.sample_count_expected} got={block_samples}")
        
        if block.missing_end and "Missing </DATA>" not in block.warnings:
            block.warnings.insert(0, "Missing </DATA>")
        
        meta_crc = block.metadata.get("CRC")
        if meta_crc:
            joined = "\n".join(block.lines).encode("utf-8", errors="ignore")
            crc_val = binascii.crc32(joined) & 0xFFFFFFFF
            crc_hex = f"{crc_val:08X}"
            if meta_crc.strip().upper() == crc_hex.upper():
                block.crc_status = "OK"
            else:
                block.crc_status = f"MISMATCH:{crc_hex}"
                block.warnings.append(f"CRC mismatch expected={meta_crc} got={crc_hex}")
        
        self.data_blocks.append(block)
        block.sample_count_actual = block_samples
        self.data_block_index[block.block_id] = block
        self.total_samples_captured += block_samples
        self.block_sample_counter = 0
        self.sample_counter_var.set("Samples: 0")
        self.csv_buffer.extend(block.lines)
        self.recording_indicator.set("⚪ Ready" if not block.warnings else "⚠ Check Data")
        if block.warnings:
            self.recording_light_color.set("#ffaa00")
        else:
            self.recording_light_color.set("#33bb66")
        self.block_start_timestamp = None
        self.refresh_recording_indicator()
        
        if self.recording_capture_active or self.pending_recording_finalize:
            self.recording_current_blocks.append(block.block_id)
        if self.pending_recording_finalize and not self.recording_capture_active:
            self.finalize_recording_session()
        
        rate_display = 0.0
        duration = block.duration()
        if block_samples and duration:
            rate_display = block_samples / duration
        else:
            try:
                rate_display = float(meta_rate)
            except (TypeError, ValueError):
                rate_display = 0.0
        self.data_rate_var.set(f"Rate: {rate_display:.1f} Hz")
        
        summary = f"{meta_mode} {meta_rate}Hz α={alpha_val} samples={block_samples}"
        if block.warnings:
            summary += f" ⚠ {'; '.join(block.warnings)}"
        self.last_block_summary = summary
        self.pending_log_lines.append(f"[DATA] Stored block: {summary}\n")
        self.update_status_display()
    
    def _parse_int(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    
    def _parse_float(self, value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    
    def describe_block(self, block: DataBlock):
        mode = block.metadata.get("MODE", "UNKNOWN")
        rate = block.metadata.get("RATE", "n/a")
        duration = block.duration()
        warning_flag = " ⚠" if block.warnings else ""
        return f"#{block.block_id} {mode} - {block.sample_count_actual or len(block.lines)} samples @ {rate}Hz ({duration:.1f}s){warning_flag}"
    
    def collect_block_rows(self, block: DataBlock):
        rows = []
        rate = self._parse_float(block.metadata.get("RATE"))
        dt = (1.0 / rate) if rate and rate > 0 else None
        for idx, line in enumerate(block.lines):
            parts = [p.strip() for p in line.split(",")]
            floats = []
            for part in parts:
                try:
                    floats.append(float(part))
                except ValueError:
                    floats.append(float("nan"))
            row = {
                "block_id": block.block_id,
                "index": idx,
                "timestamp": math.nan,
                "time_absolute": math.nan,
                "roll": math.nan,
                "pitch": math.nan,
                "yaw": math.nan,
                "gx": math.nan,
                "gy": math.nan,
                "gz": math.nan,
                "ax": math.nan,
                "ay": math.nan,
                "az": math.nan,
                "roll_raw": math.nan,
                "pitch_raw": math.nan,
                "yaw_raw": math.nan,
                "raw_line": line,
            }
            timestamp_val = None
            if len(floats) >= 10:
                if not math.isnan(floats[0]):
                    timestamp_val = floats[0]
                row["roll"] = floats[1]
                row["pitch"] = floats[2]
                row["yaw"] = floats[3]
                row["gx"] = floats[4]
                row["gy"] = floats[5]
                row["gz"] = floats[6]
                row["ax"] = floats[7]
                row["ay"] = floats[8]
                row["az"] = floats[9]
                if len(floats) >= 13:
                    row["roll_raw"] = floats[10]
                    row["pitch_raw"] = floats[11]
                    row["yaw_raw"] = floats[12]
            elif len(floats) >= 4:
                if not math.isnan(floats[0]):
                    timestamp_val = floats[0]
                row["roll"] = floats[-3]
                row["pitch"] = floats[-2]
                row["yaw"] = floats[-1]
            elif len(floats) >= 3:
                row["roll"], row["pitch"], row["yaw"] = floats[:3]
            else:
                continue
            if timestamp_val is None:
                if dt is not None:
                    timestamp_val = idx * dt
                else:
                    timestamp_val = float(idx)
            row["timestamp"] = timestamp_val
            base_ts = block.start_ts or 0.0
            row["time_absolute"] = base_ts + timestamp_val
            rows.append(row)
        return rows
    
    def _ensure_unique_folder(self, base_path):
        if not os.path.exists(base_path):
            return base_path
        counter = 1
        while True:
            candidate = f"{base_path}_{counter}"
            if not os.path.exists(candidate):
                return candidate
            counter += 1
    
    def _format_export_value(self, value):
        if value is None:
            return ""
        if isinstance(value, float):
            if math.isnan(value):
                return ""
            return f"{value:.6f}"
        return str(value)
    
    def _write_export_artifacts(self, filtered_blocks, base_name, range_mode,
                                include_metadata, include_stats, include_chart,
                                include_3d, export_root):
        os.makedirs(export_root, exist_ok=True)
        folder = self._ensure_unique_folder(os.path.join(export_root, base_name))
        os.makedirs(folder, exist_ok=True)
        
        csv_path = os.path.join(folder, f"{base_name}.csv")
        header_lines = [
            "# IMU Data Export",
            f"# Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"# Blocks: {len(filtered_blocks)}",
            f"# Range: {range_mode}",
        ]
        if include_metadata:
            for block, rows in filtered_blocks:
                header_lines.append(f"# Block {block.block_id}: Mode={block.metadata.get('MODE', 'UNKNOWN')} Rate={block.metadata.get('RATE', 'n/a')} Samples={len(rows)} Duration={block.duration():.2f}s")
                for key, value in block.metadata.items():
                    header_lines.append(f"#   {key}={value}")
                if block.warnings:
                    header_lines.append(f"#   WARNINGS: {'; '.join(block.warnings)}")
        
        columns = ["block_id", "timestamp_s", "datetime", "roll", "pitch", "yaw",
                   "gx", "gy", "gz", "ax", "ay", "az", "roll_raw", "pitch_raw", "yaw_raw"]
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            for line in header_lines:
                f.write(line + "\n")
            f.write(",".join(columns) + "\n")
            for block, rows in filtered_blocks:
                for row in rows:
                    timestamp = row["timestamp"]
                    dt_str = ""
                    if block.start_ts:
                        try:
                            dt_obj = datetime.fromtimestamp(row["time_absolute"])
                            dt_str = dt_obj.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                        except Exception:
                            dt_str = ""
                    values = [
                        str(block.block_id),
                        self._format_export_value(timestamp),
                        dt_str,
                        self._format_export_value(row["roll"]),
                        self._format_export_value(row["pitch"]),
                        self._format_export_value(row["yaw"]),
                        self._format_export_value(row["gx"]),
                        self._format_export_value(row["gy"]),
                        self._format_export_value(row["gz"]),
                        self._format_export_value(row["ax"]),
                        self._format_export_value(row["ay"]),
                        self._format_export_value(row["az"]),
                        self._format_export_value(row["roll_raw"]),
                        self._format_export_value(row["pitch_raw"]),
                        self._format_export_value(row["yaw_raw"]),
                    ]
                    f.write(",".join(values) + "\n")
        
        if include_stats:
            stats_path = os.path.join(folder, f"{base_name}_stats.txt")
            with open(stats_path, "w", encoding="utf-8") as stats_file:
                stats_file.write(f"Samples: {self.stats_samples}\n")
                stats_file.write(f"{self.stats_current_var.get()}\n")
                stats_file.write(f"{self.stats_mean_var.get()}\n")
                stats_file.write(f"{self.stats_std_var.get()}\n")
                stats_file.write(f"{self.stats_min_var.get()}\n")
                stats_file.write(f"{self.stats_max_var.get()}\n")
                stats_file.write(f"{self.stats_drift_var.get()}\n")
                stats_file.write(f"{self.stats_quality_var.get()}\n")
                stats_file.write(f"{self.stats_rate_var.get()}\n")
        
        if include_chart:
            chart_png = os.path.join(folder, f"{base_name}_chart.png")
            chart_svg = os.path.join(folder, f"{base_name}_chart.svg")
            try:
                self.fig_chart.savefig(chart_png, dpi=150, facecolor=self.fig_chart.get_facecolor())
                self.fig_chart.savefig(chart_svg, format="svg", facecolor=self.fig_chart.get_facecolor())
            except Exception as e:
                self.logger.warning(f"Chart export failed: {e}")
        if include_3d:
            orientation_png = os.path.join(folder, f"{base_name}_orientation.png")
            try:
                self.fig_3d.savefig(orientation_png, dpi=150, facecolor=self.fig_3d.get_facecolor())
            except Exception as e:
                self.logger.warning(f"3D export failed: {e}")
        
        return folder
    
    def process_sent(self, timestamp, cmd):
        """Process sent command"""
        self.log_data.append(("TX", timestamp, cmd))
        self.sent_commands.append((timestamp, cmd))
        
        time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S.%f")[:-3]
        self.pending_log_lines.append(f"[{time_str}] >> {cmd}\n")
    
    def parse_status_message(self, line):
        """Parse ESP32 status messages"""
        # Expected format: [STATUS] Mode=FILTERED Rate=100Hz Alpha=0.98
        try:
            parts = line.replace("[STATUS]", "").strip().split()
            for part in parts:
                if "=" in part:
                    key, val = part.split("=", 1)
                    if key == "Mode":
                        self.esp_mode = val
                    elif key == "Rate":
                        cleaned = val.replace("Hz", "")
                        self.esp_rate = cleaned
                        rate_val = self._parse_float(cleaned)
                        if rate_val:
                            self.expected_sample_rate = rate_val
                    elif key == "Alpha":
                        self.esp_alpha = val
            self.update_status_display()
        except:
            pass
    
    def process_data_row(self, timestamp, line):
        """Parse incoming numeric data rows for charts and stats"""
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            return
        floats = []
        for part in parts:
            try:
                floats.append(float(part))
            except ValueError:
                return
        detected_format = self.data_format
        if len(floats) >= 13:
            detected_format = "Filtered + Raw"
        elif len(floats) >= 10:
            detected_format = "Full Sensors"
        elif len(floats) >= 4:
            detected_format = "Timestamp + Angles"
        elif len(floats) >= 3:
            detected_format = "Angles"
        if detected_format != self.data_format:
            self.data_format = detected_format
            self.update_status_display()
        rel_time = timestamp - self.chart_start_time
        self.chart_data["time"].append(rel_time)
        
        values = {key: math.nan for key in self.chart_keys}
        if len(floats) == 3:
            values["roll"], values["pitch"], values["yaw"] = floats
        elif len(floats) >= 10:
            values["roll"] = floats[1]
            values["pitch"] = floats[2]
            values["yaw"] = floats[3]
            values["gx"] = floats[4]
            values["gy"] = floats[5]
            values["gz"] = floats[6]
            values["ax"] = floats[7]
            values["ay"] = floats[8]
            values["az"] = floats[9]
            if len(floats) >= 13:
                values["roll_raw"] = floats[10]
                values["pitch_raw"] = floats[11]
                values["yaw_raw"] = floats[12]
        elif len(floats) >= 4:
            values["roll"] = floats[-3]
            values["pitch"] = floats[-2]
            values["yaw"] = floats[-1]
        
        for key in self.chart_keys:
            self.chart_data[key].append(values.get(key, math.nan))
            self.latest_sample[key] = values.get(key, math.nan)
        self.latest_sample["time"] = rel_time
        
        roll_val = values.get("roll")
        pitch_val = values.get("pitch")
        yaw_val = values.get("yaw")
        updated = False
        if roll_val is not None and not math.isnan(roll_val):
            self.roll = roll_val
            self.stats_sum_roll += roll_val
            self.stats_sum_sq_roll += roll_val ** 2
            self.stats_min_roll = min(self.stats_min_roll, roll_val)
            self.stats_max_roll = max(self.stats_max_roll, roll_val)
            updated = True
        if pitch_val is not None and not math.isnan(pitch_val):
            self.pitch = pitch_val
            self.stats_sum_pitch += pitch_val
            self.stats_sum_sq_pitch += pitch_val ** 2
            self.stats_min_pitch = min(self.stats_min_pitch, pitch_val)
            self.stats_max_pitch = max(self.stats_max_pitch, pitch_val)
            updated = True
        if yaw_val is not None and not math.isnan(yaw_val):
            self.yaw = yaw_val
            self.stats_sum_yaw += yaw_val
            self.stats_sum_sq_yaw += yaw_val ** 2
            self.stats_min_yaw = min(self.stats_min_yaw, yaw_val)
            self.stats_max_yaw = max(self.stats_max_yaw, yaw_val)
            updated = True
        
        if updated:
            self.stats_samples += 1
            now = time.time()
            if self.last_sample_timestamp:
                interval = timestamp - self.last_sample_timestamp
                if interval > 0:
                    self.sample_interval_history.append(interval)
            self.last_sample_timestamp = timestamp
            if self.auto_update_3d.get():
                if now - self.last_3d_update >= self.min_3d_interval:
                    self.update_3d()
                    self.last_3d_update = now
    
    def update_3d(self):
        """Update 3D orientation"""
        try:
            r = math.radians(self.roll)
            p = math.radians(self.pitch)
            y = math.radians(self.yaw)
            
            Rx = np.array([[1, 0, 0], [0, np.cos(r), -np.sin(r)], [0, np.sin(r), np.cos(r)]])
            Ry = np.array([[np.cos(p), 0, np.sin(p)], [0, 1, 0], [-np.sin(p), 0, np.cos(p)]])
            Rz = np.array([[np.cos(y), -np.sin(y), 0], [np.sin(y), np.cos(y), 0], [0, 0, 1]])
            R = Rz @ Ry @ Rx
            
            rot_body = self.body_vertices_base @ R.T
            body_faces_idx = [
                [0, 1, 5, 4],
                [1, 2, 6, 5],
                [2, 3, 7, 6],
                [3, 0, 4, 7],
                [4, 5, 6, 7],
                [0, 1, 2, 3],
            ]
            faces = [[rot_body[idx] for idx in face] for face in body_faces_idx]
            self.drone_body.set_verts(faces)
            
            rot_arms = [segment @ R.T for segment in self.arm_segments_base]
            self.arm_collection.set_segments(rot_arms)
            
            rot_rotors = [circle @ R.T for circle in self.rotor_segments_base]
            self.rotor_collection.set_segments(rot_rotors)
            
            # Update vectors
            self.x_vec.remove()
            self.y_vec.remove()
            self.z_vec.remove()
            
            x = R @ np.array([1.5, 0, 0])
            y = R @ np.array([0, 1.5, 0])
            z = R @ np.array([0, 0, 1.5])
            
            self.x_vec = self.ax_3d.quiver(0,0,0,x[0],x[1],x[2], color='#ef4444', arrow_length_ratio=0.2, linewidth=3)
            self.y_vec = self.ax_3d.quiver(0,0,0,y[0],y[1],y[2], color='#22c55e', arrow_length_ratio=0.2, linewidth=3)
            self.z_vec = self.ax_3d.quiver(0,0,0,z[0],z[1],z[2], color='#06b6d4', arrow_length_ratio=0.2, linewidth=3)
            
            self.canvas_3d.draw_idle()
        except Exception as e:
            self.logger.error(f"3D update error: {e}")
    
    def update_chart(self):
        """Update real-time chart"""
        if not self.show_chart.get() or self.chart_paused.get():
            return
        
        try:
            self.ax_chart.clear()
            self.ax_chart.set_facecolor("#0d0d0d")
            self.ax_chart.grid(True, color="#333", linestyle="--", alpha=0.5)
            self.ax_chart.set_xlabel("Time (s)", color="white")
            self.ax_chart.tick_params(colors="white")
            
            times = list(self.chart_data["time"])
            if not times:
                self.ax_chart.set_ylabel("")
                self.canvas_chart.draw_idle()
                return
            
            window_seconds = self.get_chart_window_seconds()
            idx = 0
            if window_seconds is not None:
                start_time = times[-1] - window_seconds
                idx = bisect.bisect_left(times, start_time)
                if idx >= len(times):
                    idx = max(0, len(times) - 1)
            times_slice = times[idx:]
            if not times_slice:
                times_slice = times[-1:]
                idx = len(times) - 1
            
            data_slices = {key: list(self.chart_data[key])[idx:] for key in self.chart_keys}
            colors_drift = {"roll": "#ef4444", "pitch": "#22c55e", "yaw": "#06b6d4"}
            gyro_colors = {"gx": "#f97316", "gy": "#facc15", "gz": "#f43f5e"}
            accel_colors = {"ax": "#3b82f6", "ay": "#8b5cf6", "az": "#22d3ee"}
            
            mode = self.chart_mode.get()
            if mode == "drift":
                self.ax_chart.set_ylabel("Angle (°)", color="white")
                for axis in ["roll", "pitch", "yaw"]:
                    self.ax_chart.plot(times_slice, data_slices[axis], label=axis.upper(), color=colors_drift[axis], linewidth=1.5)
                self.ax_chart.legend(loc='upper right', facecolor='#1e1e1e', edgecolor='white', labelcolor='white')
            elif mode == "raw":
                self.ax_chart.set_ylabel("Sensor Outputs", color="white")
                for axis, color in gyro_colors.items():
                    self.ax_chart.plot(times_slice, data_slices[axis], label=f"{axis.upper()} (gyro)", color=color, linewidth=1)
                for axis, color in accel_colors.items():
                    self.ax_chart.plot(times_slice, data_slices[axis], label=f"{axis.upper()} (accel)", color=color, linewidth=1, linestyle="--")
                self.ax_chart.legend(loc='upper right', facecolor='#1e1e1e', edgecolor='white', labelcolor='white', fontsize=8)
            elif mode == "comparison":
                self.ax_chart.set_ylabel("Angle (°)", color="white")
                raw_available = any(not math.isnan(v) for v in data_slices["roll_raw"])
                if not raw_available:
                    self.ax_chart.text(0.5, 0.5, "Raw angle data not available", transform=self.ax_chart.transAxes,
                                       ha="center", va="center", color="white", fontsize=12)
                else:
                    self.ax_chart.plot(times_slice, data_slices["roll"], label="Roll Filtered", color=colors_drift["roll"], linewidth=1.5)
                    self.ax_chart.plot(times_slice, data_slices["roll_raw"], label="Roll Raw", color=colors_drift["roll"], linestyle="--", linewidth=1)
                    self.ax_chart.plot(times_slice, data_slices["pitch"], label="Pitch Filtered", color=colors_drift["pitch"], linewidth=1.5)
                    self.ax_chart.plot(times_slice, data_slices["pitch_raw"], label="Pitch Raw", color=colors_drift["pitch"], linestyle="--", linewidth=1)
                    self.ax_chart.plot(times_slice, data_slices["yaw"], label="Yaw Filtered", color=colors_drift["yaw"], linewidth=1.5)
                    self.ax_chart.plot(times_slice, data_slices["yaw_raw"], label="Yaw Raw", color=colors_drift["yaw"], linestyle="--", linewidth=1)
                    self.ax_chart.legend(loc='upper right', facecolor='#1e1e1e', edgecolor='white', labelcolor='white')
            elif mode == "axis":
                axis_key = self.chart_axis_var.get()
                label = self.chart_axis_options.get(axis_key, axis_key)
                values = data_slices.get(axis_key, [])
                if not any(not math.isnan(v) for v in values):
                    self.ax_chart.text(0.5, 0.5, "No data for selected axis", transform=self.ax_chart.transAxes,
                                       ha="center", va="center", color="white", fontsize=12)
                else:
                    self.ax_chart.set_ylabel(label, color="white")
                    self.ax_chart.plot(times_slice, values, color="#38bdf8", linewidth=1.5)
            else:
                self.ax_chart.text(0.5, 0.5, "Unknown chart mode", transform=self.ax_chart.transAxes,
                                   ha="center", va="center", color="white", fontsize=12)
            
            if window_seconds is not None and times_slice:
                self.ax_chart.set_xlim(times_slice[0], times_slice[-1])
            if not self.chart_autoscale.get():
                try:
                    ymin = float(self.chart_manual_min.get())
                    ymax = float(self.chart_manual_max.get())
                    if ymin < ymax:
                        self.ax_chart.set_ylim(ymin, ymax)
                except ValueError:
                    pass
            
            self.canvas_chart.draw_idle()
        except Exception as e:
            self.logger.error(f"Chart update error: {e}")
    
    def clear_chart(self):
        """Clear chart buffers"""
        for key in self.chart_data:
            self.chart_data[key].clear()
        self.chart_start_time = time.time()
        self.stats_samples = 0
        self.stats_sum_roll = 0
        self.stats_sum_pitch = 0
        self.stats_sum_yaw = 0
        self.stats_sum_sq_roll = 0
        self.stats_sum_sq_pitch = 0
        self.stats_sum_sq_yaw = 0
        self.sample_interval_history.clear()
        self.last_sample_timestamp = None
        self.latest_sample = {"time": 0.0}
        for key in self.chart_keys:
            self.latest_sample[key] = math.nan
        self.sample_rate_warning_active = False
        self.ax_chart.clear()
        self.canvas_chart.draw_idle()
        self.update_stats_display()
    
    def get_chart_window_seconds(self):
        mapping = {"10s": 10, "30s": 30, "1min": 60, "5min": 300}
        value = self.chart_window_var.get()
        return mapping.get(value)
    
    def on_chart_autoscale_toggle(self):
        state = "disabled" if self.chart_autoscale.get() else "normal"
        if hasattr(self, "chart_min_entry"):
            self.chart_min_entry.config(state=state)
        if hasattr(self, "chart_max_entry"):
            self.chart_max_entry.config(state=state)
        self.update_chart()
    
    def on_chart_axis_selected(self, event=None):
        label = self.chart_axis_label_var.get()
        key = self.chart_axis_label_map.get(label, "roll")
        self.chart_axis_var.set(key)
        if self.chart_mode.get() == "axis":
            self.update_chart()
    
    def on_chart_mode_changed(self, *args):
        is_axis = self.chart_mode.get() == "axis"
        state = "readonly" if is_axis else "disabled"
        if hasattr(self, "chart_axis_combo"):
            self.chart_axis_combo.config(state=state)
        self.update_chart()
    
    def toggle_chart_pause(self):
        new_state = not self.chart_paused.get()
        self.chart_paused.set(new_state)
        if hasattr(self, "chart_pause_btn"):
            self.chart_pause_btn.config(text="Resume" if new_state else "Pause")
        if not new_state:
            self.update_chart()
    
    def reset_chart_scale(self):
        self.chart_autoscale.set(True)
        self.chart_manual_min.set("-180")
        self.chart_manual_max.set("180")
        self.on_chart_autoscale_toggle()
    
    def update_recording_timer(self):
        if self.record_timer_job:
            self.root.after_cancel(self.record_timer_job)
            self.record_timer_job = None
        if self.recording_active and self.recording_start_time:
            elapsed = max(0.0, time.time() - self.recording_start_time)
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            self.record_elapsed_var.set(f"Elapsed: {minutes:02d}:{seconds:02d}")
            self.record_timer_job = self.root.after(1000, self.update_recording_timer)
        else:
            self.record_elapsed_var.set("Elapsed: 00:00")
    
    def stop_recording_timer(self):
        if self.record_timer_job:
            self.root.after_cancel(self.record_timer_job)
            self.record_timer_job = None
        self.record_elapsed_var.set("Elapsed: 00:00")
    
    def _finalize_recording_if_pending(self):
        if self.pending_recording_finalize:
            self.finalize_recording_session()
    
    def finalize_recording_session(self):
        self.pending_recording_finalize = False
        self.recording_capture_active = False
        self.recording_start_time = None
        self.stop_recording_timer()
        self.record_btn.config(text="⬤ Start Recording", bg="#bb2244")
        self.recording_indicator.set("⚪ Not Recording")
        self.recording_light_color.set("#444444")
        self.refresh_recording_indicator()
        self.recording_start_block_id = None
        block_ids = list(dict.fromkeys(self.recording_current_blocks))
        self.recording_current_blocks = []
        if not block_ids:
            self.recording_indicator.set("⚪ Not Recording")
            self.recording_light_color.set("#444444")
            self.refresh_recording_indicator()
            self.logger.info("Recording stopped with no completed data blocks.")
            return
        blocks = []
        for block_id in block_ids:
            block = self.data_block_index.get(block_id)
            if block:
                blocks.append(block)
        if not blocks:
            self.logger.info("Recording stopped but associated data blocks were not found.")
            return
        filtered_blocks = [(block, self.collect_block_rows(block)) for block in blocks]
        base_name = datetime.now().strftime("drift_test_%Y-%m-%d_%H-%M")
        export_root = os.path.join(os.getcwd(), "recordings")
        try:
            folder = self._write_export_artifacts(
                filtered_blocks,
                base_name,
                "markers",
                True,
                True,
                False,
                False,
                export_root,
            )
        except Exception as exc:
            self.logger.error(f"Recording export failed: {exc}")
            return
        total_samples = sum(len(rows) for _, rows in filtered_blocks)
        total_duration = sum(block.duration() for block, _ in filtered_blocks)
        session_info = {
            "id": self.recording_session_counter,
            "name": base_name,
            "folder": folder,
            "timestamp": datetime.now(),
            "samples": total_samples,
            "duration": total_duration,
            "block_ids": block_ids,
        }
        self.recordings.append(session_info)
        self.recording_session_counter += 1
        self.update_session_list()
        self.recording_indicator.set("⚪ Saved")
        self.recording_light_color.set("#33bb66")
        self.refresh_recording_indicator()
        self.logger.info(f"Recording auto-saved to {folder}")
    
    def update_session_list(self):
        if not hasattr(self, "session_list"):
            return
        self.session_list.delete(0, tk.END)
        for session in self.recordings:
            duration = session.get("duration", 0.0)
            samples = session.get("samples", 0)
            label = f"{session['name']} ({samples} samples, {duration:.1f}s)"
            self.session_list.insert(tk.END, label)
    
    def _get_selected_session(self):
        if not hasattr(self, "session_list"):
            return None
        selection = self.session_list.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Select a recording from the list.")
            return None
        index = selection[0]
        if index >= len(self.recordings):
            return None
        return self.recordings[index], index
    
    def _get_selected_sessions_list(self):
        if not hasattr(self, "session_list"):
            return []
        indices = self.session_list.curselection()
        sessions = []
        for idx in indices:
            if idx < len(self.recordings):
                sessions.append(self.recordings[idx])
        return sessions
    
    def open_selected_session_folder(self):
        result = self._get_selected_session()
        if not result:
            return
        session, _ = result
        folder = session.get("folder")
        if not folder or not os.path.exists(folder):
            messagebox.showerror("Missing Folder", "Recorded folder not found on disk.")
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.call(["open", folder])
            else:
                subprocess.call(["xdg-open", folder])
        except Exception as exc:
            messagebox.showerror("Open Folder", f"Failed to open folder:\n{exc}")
    
    def export_selected_session(self):
        result = self._get_selected_session()
        if not result:
            return
        session, _ = result
        block_ids = session.get("block_ids", [])
        if not block_ids:
            messagebox.showinfo("No Data", "Recording does not reference any data blocks.")
            return
        new_name = simpledialog.askstring("Export Recording", "Enter export name:", initialvalue=f"{session['name']}_export")
        if not new_name:
            return
        blocks = []
        for block_id in block_ids:
            block = self.data_block_index.get(block_id)
            if block:
                blocks.append(block)
        if not blocks:
            messagebox.showerror("Export Failed", "Original data blocks are no longer available in memory.")
            return
        filtered_blocks = [(block, self.collect_block_rows(block)) for block in blocks]
        folder = self._write_export_artifacts(
            filtered_blocks,
            new_name,
            "markers",
            True,
            True,
            True,
            False,
            os.path.join(os.getcwd(), "imu_exports"),
        )
        messagebox.showinfo("Export Complete", f"Recording exported to:\n{folder}")
    
    def delete_selected_session(self):
        result = self._get_selected_session()
        if not result:
            return
        session, index = result
        if not messagebox.askyesno("Delete Recording", f"Delete recording '{session['name']}'? This cannot be undone."):
            return
        folder = session.get("folder")
        if folder and os.path.exists(folder):
            try:
                shutil.rmtree(folder)
            except Exception as exc:
                self.logger.warning(f"Failed to remove folder {folder}: {exc}")
        del self.recordings[index]
        self.update_session_list()
    
    def load_selected_session(self):
        result = self._get_selected_session()
        if not result:
            return
        session, _ = result
        folder = session.get("folder")
        if not folder or not os.path.exists(folder):
            messagebox.showerror("Missing Folder", "Recorded folder not found on disk.")
            return
        csv_path = os.path.join(folder, f"{session['name']}.csv")
        if not os.path.exists(csv_path):
            messagebox.showerror("Missing File", f"Recording file not found:\n{csv_path}")
            return
        try:
            parsed_rows = self._load_rows_from_csv(csv_path)
            self._display_loaded_rows(parsed_rows)
            self.last_block_summary = f"Loaded recording '{session['name']}'"
            self.update_status_display()
            messagebox.showinfo("Recording Loaded", f"Recording '{session['name']}' loaded into the viewer.")
        except Exception as exc:
            messagebox.showerror("Load Failed", f"Unable to load recording:\n{exc}")
            self.logger.error(f"Load recording error: {exc}")
    
    def compare_selected_sessions(self):
        sessions = self._get_selected_sessions_list()
        if len(sessions) < 2:
            messagebox.showinfo("Select Sessions", "Select at least two recordings to compare.")
            return
        data_sets = []
        for session in sessions:
            folder = session.get("folder")
            if not folder or not os.path.exists(folder):
                continue
            csv_path = os.path.join(folder, f"{session['name']}.csv")
            if not os.path.exists(csv_path):
                continue
            try:
                rows = self._load_rows_from_csv(csv_path)
                if rows:
                    data_sets.append((session["name"], rows))
            except Exception as exc:
                self.logger.warning(f"Comparison load failed for {session['name']}: {exc}")
        if len(data_sets) < 2:
            messagebox.showerror("Comparison Failed", "Unable to load sufficient data for comparison.")
            return
        
        compare_window = tk.Toplevel(self.root)
        compare_window.title("Session Comparison")
        fig = plt.Figure(figsize=(8, 6), facecolor="#0d0d0d")
        axes = [
            fig.add_subplot(311),
            fig.add_subplot(312),
            fig.add_subplot(313),
        ]
        labels = ["Roll (°)", "Pitch (°)", "Yaw (°)"]
        colors = ["#ef4444", "#22c55e", "#3b82f6", "#f97316", "#8b5cf6", "#22d3ee"]
        for idx, (name, rows) in enumerate(data_sets):
            base_time = rows[0]["timestamp"] if rows else 0.0
            times = [row.get("timestamp", 0.0) - base_time for row in rows]
            roll_vals = [row.get("roll", math.nan) for row in rows]
            pitch_vals = [row.get("pitch", math.nan) for row in rows]
            yaw_vals = [row.get("yaw", math.nan) for row in rows]
            color = colors[idx % len(colors)]
            axes[0].plot(times, roll_vals, label=name, color=color, linewidth=1.2)
            axes[1].plot(times, pitch_vals, label=name, color=color, linewidth=1.2)
            axes[2].plot(times, yaw_vals, label=name, color=color, linewidth=1.2)
        for ax, label in zip(axes, labels):
            ax.set_facecolor("#0d0d0d")
            ax.grid(True, color="#333333", linestyle="--", alpha=0.5)
            ax.set_ylabel(label, color="white")
            ax.tick_params(colors="white")
        axes[-1].set_xlabel("Time (s)", color="white")
        axes[0].legend(loc="upper right")
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=compare_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
    
    def _load_rows_from_csv(self, file_path):
        parsed_rows = []
        header = None
        with open(file_path, encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if header is None:
                    header = [h.strip() for h in line.split(",")]
                    continue
                values = line.split(",")
                row_dict = dict(zip(header, values))
                def to_float(key):
                    value = row_dict.get(key, "")
                    try:
                        return float(value) if value != "" else math.nan
                    except ValueError:
                        return math.nan
                parsed_rows.append({
                    "timestamp": to_float("timestamp_s"),
                    "roll": to_float("roll"),
                    "pitch": to_float("pitch"),
                    "yaw": to_float("yaw"),
                    "gx": to_float("gx"),
                    "gy": to_float("gy"),
                    "gz": to_float("gz"),
                    "ax": to_float("ax"),
                    "ay": to_float("ay"),
                    "az": to_float("az"),
                    "roll_raw": to_float("roll_raw"),
                    "pitch_raw": to_float("pitch_raw"),
                    "yaw_raw": to_float("yaw_raw"),
                })
        return parsed_rows
    
    def _display_loaded_rows(self, rows):
        self.clear_chart()
        if not rows:
            return
        self.chart_start_time = time.time()
        previous_timestamp = None
        for row in rows:
            timestamp = row.get("timestamp", math.nan)
            if math.isnan(timestamp):
                if previous_timestamp is None:
                    timestamp = 0.0
                else:
                    timestamp = previous_timestamp
            self.chart_data["time"].append(timestamp)
            for key in self.chart_keys:
                self.chart_data[key].append(row.get(key, math.nan))
            if previous_timestamp is not None:
                interval = timestamp - previous_timestamp
                if interval > 0:
                    self.sample_interval_history.append(interval)
            previous_timestamp = timestamp
            
            roll_val = row.get("roll", math.nan)
            pitch_val = row.get("pitch", math.nan)
            yaw_val = row.get("yaw", math.nan)
            if not math.isnan(roll_val):
                self.roll = roll_val
                self.stats_sum_roll += roll_val
                self.stats_sum_sq_roll += roll_val ** 2
                self.stats_min_roll = min(self.stats_min_roll, roll_val)
                self.stats_max_roll = max(self.stats_max_roll, roll_val)
            if not math.isnan(pitch_val):
                self.pitch = pitch_val
                self.stats_sum_pitch += pitch_val
                self.stats_sum_sq_pitch += pitch_val ** 2
                self.stats_min_pitch = min(self.stats_min_pitch, pitch_val)
                self.stats_max_pitch = max(self.stats_max_pitch, pitch_val)
            if not math.isnan(yaw_val):
                self.yaw = yaw_val
                self.stats_sum_yaw += yaw_val
                self.stats_sum_sq_yaw += yaw_val ** 2
                self.stats_min_yaw = min(self.stats_min_yaw, yaw_val)
                self.stats_max_yaw = max(self.stats_max_yaw, yaw_val)
            if (not math.isnan(roll_val)) or (not math.isnan(pitch_val)) or (not math.isnan(yaw_val)):
                self.stats_samples += 1
        self.update_chart()
        self.update_stats_display()
        self.sample_counter_var.set(f"Samples: {self.stats_samples}")
    
    def export_chart(self):
        if not self.chart_data["time"]:
            messagebox.showinfo("No Data", "No chart data available to export.")
            return
        filetypes = [
            ("PNG Image", "*.png"),
            ("SVG Vector", "*.svg"),
        ]
        default_name = datetime.now().strftime("imu_chart_%Y-%m-%d_%H-%M-%S.png")
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=filetypes, initialfile=default_name)
        if not path:
            return
        try:
            self.fig_chart.savefig(path, facecolor=self.fig_chart.get_facecolor())
            messagebox.showinfo("Export Complete", f"Chart saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to save chart:\n{e}")
    
    def update_status_display(self):
        """Update ESP32 status display"""
        self.status_text.config(state="normal")
        self.status_text.delete(1.0, tk.END)
        self.status_text.insert(tk.END, f"Mode: {self.esp_mode}\n")
        self.status_text.insert(tk.END, f"Rate: {self.esp_rate} Hz\n")
        self.status_text.insert(tk.END, f"Alpha: {self.esp_alpha}\n")
        self.status_text.insert(tk.END, f"Format: {self.data_format}\n")
        self.status_text.insert(tk.END, f"Recording: {'🟢 YES' if self.recording_block else '⚪ NO'}\n")
        self.status_text.insert(tk.END, f"Blocks: {len(self.data_blocks)}\n")
        summary = self.last_block_summary
        if len(summary) > 60:
            summary = summary[:57] + "..."
        self.status_text.insert(tk.END, f"Last: {summary}")
        self.status_text.config(state="disabled")
    
    def update_stats_display(self):
        """Update statistics display"""
        if self.stats_samples == 0:
            mean_r = mean_p = mean_y = 0.0
            std_r = std_p = std_y = 0.0
            min_r = min_p = min_y = 0.0
            max_r = max_p = max_y = 0.0
        else:
            mean_r = self.stats_sum_roll / self.stats_samples
            mean_p = self.stats_sum_pitch / self.stats_samples
            mean_y = self.stats_sum_yaw / self.stats_samples
            
            var_r = (self.stats_sum_sq_roll / self.stats_samples) - (mean_r ** 2)
            var_p = (self.stats_sum_sq_pitch / self.stats_samples) - (mean_p ** 2)
            var_y = (self.stats_sum_sq_yaw / self.stats_samples) - (mean_y ** 2)
            
            std_r = math.sqrt(max(0.0, var_r))
            std_p = math.sqrt(max(0.0, var_p))
            std_y = math.sqrt(max(0.0, var_y))
            
            min_r = self.stats_min_roll if self.stats_min_roll != float("inf") else mean_r
            min_p = self.stats_min_pitch if self.stats_min_pitch != float("inf") else mean_p
            min_y = self.stats_min_yaw if self.stats_min_yaw != float("inf") else mean_y
            max_r = self.stats_max_roll if self.stats_max_roll != float("-inf") else mean_r
            max_p = self.stats_max_pitch if self.stats_max_pitch != float("-inf") else mean_p
            max_y = self.stats_max_yaw if self.stats_max_yaw != float("-inf") else mean_y
        
        if self.sample_interval_history:
            avg_interval = sum(self.sample_interval_history) / len(self.sample_interval_history)
            sample_rate = 1.0 / avg_interval if avg_interval > 0 else 0.0
        else:
            sample_rate = 0.0
        
        drift_rate = 0.0
        times = list(self.chart_data["time"])
        yaw_values = list(self.chart_data["yaw"])
        if len(times) >= 10:
            window_seconds = self.get_chart_window_seconds()
            idx = 0
            if window_seconds is not None:
                start_time = times[-1] - window_seconds
                idx = bisect.bisect_left(times, start_time)
            times_slice = np.array(times[idx:], dtype=float)
            yaw_slice = np.array(yaw_values[idx:], dtype=float)
            mask = np.isfinite(yaw_slice)
            if mask.sum() >= 5 and times_slice.size > 0:
                rel_time = times_slice[mask] - times_slice[mask][0]
                if np.ptp(rel_time) > 0:
                    try:
                        slope, _ = np.polyfit(rel_time, yaw_slice[mask], 1)
                        drift_rate = slope * 60.0
                    except Exception:
                        drift_rate = 0.0
        
        abs_drift = abs(drift_rate)
        if abs_drift < 1.0:
            quality_color = "#22c55e"
            quality_text = "Quality: green (<1°/min)"
        elif abs_drift <= 5.0:
            quality_color = "#facc15"
            quality_text = "Quality: yellow (1-5°/min)"
        else:
            quality_color = "#ef4444"
            quality_text = "Quality: red (>5°/min)"
        
        rate_warning = False
        if self.expected_sample_rate and self.expected_sample_rate > 0 and sample_rate > 0:
            if sample_rate < 0.8 * self.expected_sample_rate:
                rate_warning = True
                if not self.sample_rate_warning_active:
                    self.sample_rate_warning_active = True
                    self.pending_log_lines.append("⚠ Sample rate below expected threshold.\n")
            else:
                self.sample_rate_warning_active = False
        else:
            self.sample_rate_warning_active = False
        
        self.stats_samples_var.set(f"Samples: {self.stats_samples}")
        self.stats_current_var.set(f"Current: R={self.roll:.2f}° P={self.pitch:.2f}° Y={self.yaw:.2f}°")
        self.stats_mean_var.set(f"Mean: R={mean_r:.2f}° P={mean_p:.2f}° Y={mean_y:.2f}°")
        self.stats_std_var.set(f"StdDev: R={std_r:.2f}° P={std_p:.2f}° Y={std_y:.2f}°")
        self.stats_min_var.set(f"Min: R={min_r:.2f}° P={min_p:.2f}° Y={min_y:.2f}°")
        self.stats_max_var.set(f"Max: R={max_r:.2f}° P={max_p:.2f}° Y={max_y:.2f}°")
        self.stats_drift_var.set(f"Drift Rate: {drift_rate:.2f}°/min")
        self.stats_quality_var.set(quality_text)
        if hasattr(self, "drift_quality_label"):
            self.drift_quality_label.config(foreground=quality_color)
        
        if self.expected_sample_rate and self.expected_sample_rate > 0:
            rate_text = f"Rate: {sample_rate:.1f} Hz (target {self.expected_sample_rate:.0f} Hz)"
            if rate_warning:
                rate_text += " ⚠"
        else:
            rate_text = f"Rate: {sample_rate:.1f} Hz"
        self.data_rate_var.set(rate_text)
        self.stats_rate_var.set(f"Sample Rate: {sample_rate:.1f} Hz")
        
        if rate_warning:
            suggestion = "Suggestion: Check wiring or lower sample rate."
        elif abs_drift > 5.0:
            suggestion = "Suggestion: Try alpha=0.95 for less drift."
        elif abs_drift > 1.0:
            suggestion = "Suggestion: Slightly lower alpha to reduce drift."
        else:
            suggestion = "Suggestion: Stable readings."
        self.suggestion_var.set(suggestion)
    
    def flush_log_updates(self):
        """Batch update log text"""
        if not self.pending_log_lines:
            return
        
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, "".join(self.pending_log_lines))
        self.log_text.config(state="disabled")
        
        if self.autoscroll.get():
            self.log_text.see(tk.END)
        
        self.pending_log_lines.clear()
    
    def clear_log(self):
        """Clear all logs"""
        self.log_text.config(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state="disabled")
        self.log_data.clear()
        self.sent_commands.clear()
        self.pending_log_lines.clear()
    
    def export_data_simple(self):
        """Simple export all data"""
        if not self.log_data:
            messagebox.showinfo("No Data", "No data to export")
            return
        
        now = datetime.now()
        folder = now.strftime("imu_export_%Y-%m-%d_%H-%M-%S")
        
        try:
            os.makedirs(folder, exist_ok=True)
            filename = os.path.join(folder, now.strftime("imu_log_%Y-%m-%d_%H-%M-%S.csv"))
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write("# IMU Data Export\n")
                f.write(f"# Exported: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Total Samples: {len(self.log_data)}\n")
                f.write("#\n")
                f.write("Type,Timestamp,Time,Data\n")
                
                for msg_type, ts, data in self.log_data:
                    time_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    data_escaped = data.replace('"', '""')
                    f.write(f'{msg_type},{ts},{time_str},"{data_escaped}"\n')
            
            messagebox.showinfo("Export Complete", f"Data saved to:\n{filename}\n\nTotal: {len(self.log_data)} records")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed:\n{e}")
    
    def on_close(self):
        """Cleanup"""
        self.logger.info("Closing")
        self.disconnect()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = EnhancedIMUMonitor(root)
    root.mainloop()