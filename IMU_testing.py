"""
Enhanced Drone IMU Serial Monitor
----------------------------------
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
from tkinter import ttk, scrolledtext, messagebox
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
import re

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import matplotlib.pyplot as plt
import numpy as np

DEBUG_MODE = '--debug' in sys.argv
plt.ion()


class DataBlockParser:
    """Parser for <DATA> ... </DATA> marked blocks"""
    def __init__(self):
        self.in_block = False
        self.current_block = []
        self.metadata = {}
        self.block_start_time = None
        
    def parse_line(self, line):
        """Returns: None (still parsing), or (metadata, data_list) when block complete"""
        if line.startswith("<DATA"):
            self.in_block = True
            self.current_block = []
            self.block_start_time = time.time()
            self.metadata = self.extract_metadata(line)
            return None
            
        elif line == "</DATA>":
            self.in_block = False
            result = (self.metadata, self.current_block.copy())
            self.current_block = []
            self.metadata = {}
            return result
            
        elif self.in_block:
            self.current_block.append(line)
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
        self.root.title("Enhanced IMU Monitor")
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
        
        # Chart data buffers
        self.chart_buffer_size = 68000  # 10s at 6.8kHz
        self.chart_times = deque(maxlen=self.chart_buffer_size)
        self.chart_roll = deque(maxlen=self.chart_buffer_size)
        self.chart_pitch = deque(maxlen=self.chart_buffer_size)
        self.chart_yaw = deque(maxlen=self.chart_buffer_size)
        self.chart_start_time = time.time()
        
        # Statistics
        self.stats_samples = 0
        self.stats_sum_roll = 0
        self.stats_sum_pitch = 0
        self.stats_sum_yaw = 0
        self.stats_sum_sq_roll = 0
        self.stats_sum_sq_pitch = 0
        self.stats_sum_sq_yaw = 0
        
        # UI state
        self.auto_update_3d = tk.BooleanVar(value=True)
        self.autoscroll = tk.BooleanVar(value=True)
        self.show_chart = tk.BooleanVar(value=True)
        self.chart_mode = tk.StringVar(value="drift")  # drift, raw, comparison
        self.paused = False
        self.connected = False
        
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
        """Left panel: controls, commands, logs"""
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
        ttk.Combobox(baud_frame, textvariable=self.baud_var, values=["115200", "230400", "460800", "921600"], 
                    width=12, state="readonly").pack(side="left")
        
        self.connect_btn = tk.Button(conn_frame, text="Connect", command=self.toggle_connection,
                                     bg="#22aa55", fg="white", font=("Segoe UI", 10, "bold"),
                                     relief=tk.RAISED, bd=2, cursor="hand2")
        self.connect_btn.pack(fill="x", pady=(10, 5))
        
        self.pause_btn = tk.Button(conn_frame, text="⏸ Pause", command=self.toggle_pause,
                                   bg="#ff8800", fg="white", font=("Segoe UI", 9, "bold"),
                                   relief=tk.RAISED, bd=2, cursor="hand2", state="disabled")
        self.pause_btn.pack(fill="x")
        
        # Command Presets
        preset_frame = ttk.LabelFrame(parent, text="Quick Tests", padding=10)
        preset_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Button(preset_frame, text="🎯 Drift Test (5min)", 
                  command=lambda: self.send_preset("MODE:FILTERED\nRATE:100\nDURATION:300\nSTART")).pack(fill="x", pady=2)
        ttk.Button(preset_frame, text="📊 Raw Analysis (5000 samples)", 
                  command=lambda: self.send_preset("MODE:RAW\nRATE:100\nSAMPLES:5000\nSTART")).pack(fill="x", pady=2)
        ttk.Button(preset_frame, text="🔧 Filter Tuning (1min)", 
                  command=lambda: self.send_preset("MODE:BOTH\nRATE:100\nDURATION:60\nSTART")).pack(fill="x", pady=2)
        ttk.Button(preset_frame, text="⚙ Calibrate (1000 samples)", 
                  command=lambda: self.send_preset("CALIBRATE:1000")).pack(fill="x", pady=2)
        ttk.Button(preset_frame, text="❌ Stop Streaming", 
                  command=lambda: self.send_command_direct("STOP")).pack(fill="x", pady=2)
        
        # Manual Command
        cmd_frame = ttk.LabelFrame(parent, text="Manual Command", padding=10)
        cmd_frame.pack(fill="x", pady=(0, 10))
        
        cmd_grid = ttk.Frame(cmd_frame)
        cmd_grid.pack(fill="x")
        
        # Mode
        ttk.Label(cmd_grid, text="Mode:").grid(row=0, column=0, sticky="w", pady=2)
        self.cmd_mode = tk.StringVar(value="FILTERED")
        mode_combo = ttk.Combobox(cmd_grid, textvariable=self.cmd_mode, 
                                  values=["RAW", "FILTERED", "BOTH"], width=12, state="readonly")
        mode_combo.grid(row=0, column=1, sticky="ew", padx=(5, 0), pady=2)
        
        # Rate
        ttk.Label(cmd_grid, text="Rate (Hz):").grid(row=1, column=0, sticky="w", pady=2)
        self.cmd_rate = tk.StringVar(value="100")
        rate_combo = ttk.Combobox(cmd_grid, textvariable=self.cmd_rate,
                                  values=["50", "100", "200", "500", "1000"], width=12, state="readonly")
        rate_combo.grid(row=1, column=1, sticky="ew", padx=(5, 0), pady=2)
        
        # Alpha
        ttk.Label(cmd_grid, text="Alpha:").grid(row=2, column=0, sticky="w", pady=2)
        self.cmd_alpha = tk.StringVar(value="0.98")
        alpha_entry = ttk.Entry(cmd_grid, textvariable=self.cmd_alpha, width=14)
        alpha_entry.grid(row=2, column=1, sticky="ew", padx=(5, 0), pady=2)
        
        # Duration
        ttk.Label(cmd_grid, text="Duration (s):").grid(row=3, column=0, sticky="w", pady=2)
        self.cmd_duration = tk.StringVar(value="60")
        dur_entry = ttk.Entry(cmd_grid, textvariable=self.cmd_duration, width=14)
        dur_entry.grid(row=3, column=1, sticky="ew", padx=(5, 0), pady=2)
        
        cmd_grid.columnconfigure(1, weight=1)
        
        ttk.Button(cmd_frame, text="▶ Send & Start", command=self.send_manual_command).pack(fill="x", pady=(10, 0))
        
        # ESP32 Status
        status_frame = ttk.LabelFrame(parent, text="ESP32 Status", padding=10)
        status_frame.pack(fill="x", pady=(0, 10))
        
        self.status_text = tk.Text(status_frame, height=4, bg="#0d0d0d", fg="#00ff00",
                                   font=("Consolas", 9), relief=tk.FLAT)
        self.status_text.pack(fill="x")
        self.update_status_display()
        
        # Statistics
        stats_frame = ttk.LabelFrame(parent, text="Statistics", padding=10)
        stats_frame.pack(fill="x", pady=(0, 10))
        
        self.stats_text = tk.Text(stats_frame, height=6, bg="#0d0d0d", fg="#00aaff",
                                 font=("Consolas", 9), relief=tk.FLAT)
        self.stats_text.pack(fill="x")
        self.update_stats_display()
        
        # Serial Monitor
        log_frame = ttk.LabelFrame(parent, text="Serial Monitor", padding=10)
        log_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15,
                                                  background="#0d0d0d", foreground="#00ff00",
                                                  insertbackground="white", font=("Consolas", 8))
        self.log_text.pack(fill="both", expand=True)
        self.log_text.config(state="disabled")
        
        # Actions
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill="x")
        
        ttk.Button(action_frame, text="Clear", command=self.clear_log).pack(side="left", padx=(0, 5))
        ttk.Button(action_frame, text="Export", command=self.export_data_simple).pack(side="left")
        
        self.refresh_ports()
    
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
        
        ttk.Label(chart_ctrl, text="View:").pack(side="left", padx=(0, 10))
        ttk.Radiobutton(chart_ctrl, text="Drift", variable=self.chart_mode, value="drift").pack(side="left", padx=5)
        ttk.Radiobutton(chart_ctrl, text="Raw Sensors", variable=self.chart_mode, value="raw").pack(side="left", padx=5)
        
        ttk.Button(chart_ctrl, text="Clear Chart", command=self.clear_chart).pack(side="left", padx=(20, 0))
        ttk.Checkbutton(chart_ctrl, text="Show Chart", variable=self.show_chart).pack(side="right")
        
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
    
    def create_drone_model(self):
        """Create simplified 3D drone model"""
        # Simple body cube
        s = 0.5
        verts = [[-s,-s,-s],[s,-s,-s],[s,s,-s],[-s,s,-s],[-s,-s,s],[s,-s,s],[s,s,s],[-s,s,s]]
        verts = np.array(verts)
        
        faces = [[verts[j] for j in [0,1,5,4]], [verts[j] for j in [2,3,7,6]],
                 [verts[j] for j in [0,3,7,4]], [verts[j] for j in [1,2,6,5]],
                 [verts[j] for j in [0,1,2,3]], [verts[j] for j in [4,5,6,7]]]
        
        self.drone_body = Poly3DCollection(faces, alpha=0.9, facecolors='#2563eb', edgecolors='white', linewidths=1.5)
        self.ax_3d.add_collection3d(self.drone_body)
        
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
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect first")
            return
        for cmd in commands.strip().split("\n"):
            self.send_command_direct(cmd)
            time.sleep(0.05)
    
    def send_manual_command(self):
        """Send manually configured command"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect first")
            return
        
        commands = [
            f"MODE:{self.cmd_mode.get()}",
            f"RATE:{self.cmd_rate.get()}",
            f"ALPHA:{self.cmd_alpha.get()}",
            f"DURATION:{self.cmd_duration.get()}",
            "START"
        ]
        
        for cmd in commands:
            self.send_command_direct(cmd)
            time.sleep(0.05)
    
    def send_command_direct(self, cmd):
        """Send single command"""
        if not self.connected:
            return
        
        try:
            self.serial_port.write((cmd + "\n").encode())
            timestamp = time.time()
            self.data_queue.put(("sent", timestamp, cmd))
            self.logger.info(f"Sent: {cmd}")
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
                    
        except Exception as e:
            self.logger.error(f"Update loop error: {e}")
        finally:
            self.root.after(50, self.update_loop)
    
    def process_received(self, timestamp, line):
        """Process received line"""
        # Check for data block markers
        block_result = self.parser.parse_line(line)
        
        if line.startswith("<DATA"):
            self.recording_block = True
            self.current_block_metadata = self.parser.metadata
            self.pending_log_lines.append(f"[{datetime.fromtimestamp(timestamp).strftime('%H:%M:%S.%f')[:-3]}] 🟢 DATA BLOCK START: {self.current_block_metadata}\n")
            return
        elif line == "</DATA>":
            self.recording_block = False
            self.pending_log_lines.append(f"[{datetime.fromtimestamp(timestamp).strftime('%H:%M:%S.%f')[:-3]}] 🔴 DATA BLOCK END\n")
            if block_result:
                meta, data = block_result
                self.logger.info(f"Block complete: {len(data)} samples, metadata: {meta}")
            return
        
        # Store all data
        self.log_data.append(("RX", timestamp, line))
        
        # Queue log text (only if not in data block or show all)
        if not self.recording_block:
            time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S.%f")[:-3]
            self.pending_log_lines.append(f"[{time_str}] {line}\n")
        
        # Parse status messages
        if line.startswith("[STATUS]"):
            self.parse_status_message(line)
        
        # Parse orientation data
        if self.auto_update_3d.get() and not line.startswith("[") and not line.startswith("<"):
            self.parse_orientation(timestamp, line)
    
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
                        self.esp_rate = val.replace("Hz", "")
                    elif key == "Alpha":
                        self.esp_alpha = val
            self.update_status_display()
        except:
            pass
    
    def parse_orientation(self, timestamp, line):
        """Parse orientation data and update displays"""
        try:
            parts = line.split(",")
            if len(parts) >= 3:
                self.roll = float(parts[0].strip())
                self.pitch = float(parts[1].strip())
                self.yaw = float(parts[2].strip())
                
                # Add to chart buffers
                relative_time = timestamp - self.chart_start_time
                self.chart_times.append(relative_time)
                self.chart_roll.append(self.roll)
                self.chart_pitch.append(self.pitch)
                self.chart_yaw.append(self.yaw)
                
                # Update statistics
                self.stats_samples += 1
                self.stats_sum_roll += self.roll
                self.stats_sum_pitch += self.pitch
                self.stats_sum_yaw += self.yaw
                self.stats_sum_sq_roll += self.roll ** 2
                self.stats_sum_sq_pitch += self.pitch ** 2
                self.stats_sum_sq_yaw += self.yaw ** 2
                
                # Throttled 3D update
                current_time = time.time()
                if current_time - self.last_3d_update >= self.min_3d_interval:
                    self.update_3d()
                    self.last_3d_update = current_time
        except:
            pass
    
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
            
            # Update body
            s = 0.5
            verts = np.array([[-s,-s,-s],[s,-s,-s],[s,s,-s],[-s,s,-s],[-s,-s,s],[s,-s,s],[s,s,s],[-s,s,s]])
            rot_verts = verts @ R.T
            faces = [[rot_verts[j] for j in [0,1,5,4]], [rot_verts[j] for j in [2,3,7,6]],
                     [rot_verts[j] for j in [0,3,7,4]], [rot_verts[j] for j in [1,2,6,5]],
                     [rot_verts[j] for j in [0,1,2,3]], [rot_verts[j] for j in [4,5,6,7]]]
            self.drone_body.set_verts(faces)
            
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
        if not self.chart_times or not self.show_chart.get():
            return
        
        try:
            self.ax_chart.clear()
            self.ax_chart.set_facecolor("#0d0d0d")
            self.ax_chart.grid(True, color="#333", linestyle="--", alpha=0.5)
            self.ax_chart.set_xlabel("Time (s)", color="white")
            self.ax_chart.tick_params(colors="white")
            
            times = list(self.chart_times)
            
            if self.chart_mode.get() == "drift":
                self.ax_chart.set_ylabel("Angle (°)", color="white")
                self.ax_chart.plot(times, list(self.chart_roll), 'r-', label='Roll', linewidth=1.5)
                self.ax_chart.plot(times, list(self.chart_pitch), 'g-', label='Pitch', linewidth=1.5)
                self.ax_chart.plot(times, list(self.chart_yaw), 'c-', label='Yaw', linewidth=1.5)
                self.ax_chart.legend(loc='upper right', facecolor='#1e1e1e', edgecolor='white', labelcolor='white')
            
            self.canvas_chart.draw_idle()
        except Exception as e:
            self.logger.error(f"Chart update error: {e}")
    
    def clear_chart(self):
        """Clear chart buffers"""
        self.chart_times.clear()
        self.chart_roll.clear()
        self.chart_pitch.clear()
        self.chart_yaw.clear()
        self.chart_start_time = time.time()
        self.stats_samples = 0
        self.stats_sum_roll = 0
        self.stats_sum_pitch = 0
        self.stats_sum_yaw = 0
        self.stats_sum_sq_roll = 0
        self.stats_sum_sq_pitch = 0
        self.stats_sum_sq_yaw = 0
        self.ax_chart.clear()
        self.canvas_chart.draw_idle()
    
    def update_status_display(self):
        """Update ESP32 status display"""
        self.status_text.config(state="normal")
        self.status_text.delete(1.0, tk.END)
        self.status_text.insert(tk.END, f"Mode: {self.esp_mode}\n")
        self.status_text.insert(tk.END, f"Rate: {self.esp_rate} Hz\n")
        self.status_text.insert(tk.END, f"Alpha: {self.esp_alpha}\n")
        self.status_text.insert(tk.END, f"Recording: {'🟢 YES' if self.recording_block else '⚪ NO'}")
        self.status_text.config(state="disabled")
    
    def update_stats_display(self):
        """Update statistics display"""
        if self.stats_samples == 0:
            mean_r = mean_p = mean_y = 0
            std_r = std_p = std_y = 0
        else:
            mean_r = self.stats_sum_roll / self.stats_samples
            mean_p = self.stats_sum_pitch / self.stats_samples
            mean_y = self.stats_sum_yaw / self.stats_samples
            
            var_r = (self.stats_sum_sq_roll / self.stats_samples) - (mean_r ** 2)
            var_p = (self.stats_sum_sq_pitch / self.stats_samples) - (mean_p ** 2)
            var_y = (self.stats_sum_sq_yaw / self.stats_samples) - (mean_y ** 2)
            
            std_r = math.sqrt(max(0, var_r))
            std_p = math.sqrt(max(0, var_p))
            std_y = math.sqrt(max(0, var_y))
        
        self.stats_text.config(state="normal")
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(tk.END, f"Samples: {self.stats_samples}\n")
        self.stats_text.insert(tk.END, f"Current: R={self.roll:.2f}° P={self.pitch:.2f}° Y={self.yaw:.2f}°\n")
        self.stats_text.insert(tk.END, f"Mean:    R={mean_r:.2f}° P={mean_p:.2f}° Y={mean_y:.2f}°\n")
        self.stats_text.insert(tk.END, f"StdDev:  R={std_r:.2f}° P={std_p:.2f}° Y={std_y:.2f}°\n")
        self.stats_text.config(state="disabled")
    
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