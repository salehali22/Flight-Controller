# V1.1
"""
Drone IMU Serial Monitor
------------------------
Simple tool for evaluating IMU data from ESP32 + MPU6050
- Real-time 3D visualization of orientation
- Serial data logging with command support
- Export capability with time windows

Run with --debug flag for detailed console logging
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import serial
import serial.tools.list_ports
import threading
import queue
import time
import math
import sys
from datetime import datetime
from collections import deque

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import matplotlib.pyplot as plt
import numpy as np

# Check if debug mode is enabled
DEBUG_MODE = '--debug' in sys.argv

# Enable matplotlib interactive mode
plt.ion()


class DebugLogger:
    """Simple debug logger - only logs when DEBUG_MODE is True"""
    def __init__(self):
        self.enabled = DEBUG_MODE
        self.logs = deque(maxlen=1000)  # Keep only last 1000 entries
    
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


class DroneIMUMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("Drone IMU Monitor")
        self.root.geometry("1400x800")
        self.root.configure(bg="#1e1e1e")
        
        # Initialize debug logger
        self.logger = DebugLogger()
        self.logger.info("Application starting")
        
        # Serial state
        self.serial_port = None
        self.reading = False
        self.data_queue = queue.Queue(maxsize=1000)  # Limit queue size
        
        # Data storage (use deque for better performance)
        self.log_data = deque(maxlen=6000)  # Keep last entries bounded
        
        # UI state
        self.auto_update_3d = tk.BooleanVar(value=True)
        self.paused = False
        self.connected = False
        self.serial_monitor_window = None
        self.log_text = None
        self.max_log_lines = 3000
        self.log_line_count = 0
        self.auto_scroll_log = tk.BooleanVar(value=True)
        self.drone_scale = tk.DoubleVar(value=1.4)
        
        self.cmd_var = tk.StringVar()
        self.cmd_entry = None
        self.cal_samples_var = tk.IntVar(value=1000)
        self.alpha_factor_var = tk.DoubleVar(value=0.83)
        self.run_duration_var = tk.IntVar(value=0)
        self.sample_rate_var = tk.IntVar(value=100)  # Default: 100 Hz
        self.sensor_mode = tk.StringVar(value="MPU6050")
        self.sensor_selection_locked = False
        self._suppress_sensor_event = False
        self.esp_paused = False
        self.waiting_for_calibration = False
        self.sensor_combo = None
        
        # Magnetometer state (Pololu board)
        self.mag_values = {"x": 0.0, "y": 0.0, "z": 0.0}
        self.mag_heading = float("nan")
        self.mag_strength = 0.0
        self.mag_heading_var = tk.StringVar(value="Heading: ---°")
        self.mag_strength_var = tk.StringVar(value="Strength: --- µT")
        self.mag_value_vars = {
            "x": tk.StringVar(value="X: --- µT"),
            "y": tk.StringVar(value="Y: --- µT"),
            "z": tk.StringVar(value="Z: --- µT"),
        }
        self.mag_canvas = None
        self.mag_frame = None
        self.mag_frame_parent = None
        self.mag_canvas_size = 220
        
        # Timed run data storage
        self.timed_run_data = deque(maxlen=50000)  # Limit to 50k samples to prevent memory issues
        self.timed_run_active = False
        self.samples_after_calibration = 0
        self.skip_calibration_samples = 100
        self.timed_run_start_time = None
        self.timed_run_elapsed_time = 0.0
        
        # Frequency counter for serial data
        self.serial_data_times = deque(maxlen=100)  # Store last 100 timestamps
        self.serial_frequency = 0.0
        
        # Chart data
        self.chart_history = deque(maxlen=50000)  # Limit to prevent memory issues
        self.chart_lines = {}
        self.chart_colors = {
            "roll": "#ef4444",
            "pitch": "#22c55e",
            "yaw": "#06b6d4"
        }
        self.chart_axis_enabled = {
            "roll": tk.BooleanVar(value=True),
            "pitch": tk.BooleanVar(value=True),
            "yaw": tk.BooleanVar(value=True)
        }
        self.chart_paused = False
        self.chart_auto_scale = tk.BooleanVar(value=True)
        self.chart_y_min = tk.DoubleVar(value=-180.0)
        self.chart_y_max = tk.DoubleVar(value=180.0)
        self.chart_window_var = tk.IntVar(value=30)
        self.chart_window_options = [("10s", 10), ("30s", 30), ("2min", 120), ("10min", 600), ("All", 0)]
        self.chart_window_choice = tk.StringVar(value="30s")
        self.chart_history_limit = 180000
        self.chart_scale_entries = []
        self.chart_setting_updating = False
        self.chart_y_min.trace_add("write", self._chart_setting_changed)
        self.chart_y_max.trace_add("write", self._chart_setting_changed)
        self.chart_window_choice.trace_add("write", self.on_window_choice_change)
        self.chart_ax = None
        self.chart_canvas = None
        self.chart_fig = None
        self.chart_pause_btn = None
        self.chart_legend = None
        
        # IMU angles
        self.roll = 0
        self.pitch = 0
        self.yaw = 0
        
        # Drone position
        self.pos_x = 0
        self.pos_y = 0
        self.pos_z = 0
        
        # 3D update throttling (limit for performance)
        self.last_3d_update = 0
        self.min_3d_interval = 0.033  # ~30 FPS for smoother updates
        
        # Batch text updates
        self.pending_log_lines = []
        self.last_log_update = 0
        self.log_update_interval = 0.1  # Update text every 100ms
        
        # 3D view settings
        self.view_elev = 20
        self.view_azim = 45
        
        self.setup_ui()
        self.update_loop()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.logger.info("UI setup complete")
    
    def setup_ui(self):
        """Create the user interface"""
        # Configure dark theme
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background="#1e1e1e", foreground="white", fieldbackground="#2b2b2b")
        style.configure("TButton", background="#333", foreground="white", padding=6)
        style.configure("TLabel", background="#1e1e1e", foreground="white")
        style.configure("TCheckbutton", background="#1e1e1e", foreground="white")
        style.configure("TFrame", background="#1e1e1e")
        style.configure("TLabelframe", background="#1e1e1e", foreground="white")
        style.configure("TLabelframe.Label", background="#1e1e1e", foreground="white")
        style.configure("TEntry", fieldbackground="#2b2b2b", foreground="white", insertcolor="white")
        style.configure("TCombobox", fieldbackground="#2b2b2b", foreground="white")
        style.map("TCombobox", fieldbackground=[("readonly", "#2b2b2b")])
        style.map("TCombobox", selectbackground=[("readonly", "#2b2b2b")])
        style.map("TCombobox", selectforeground=[("readonly", "white")])
        
        # Main container
        main = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg="#1e1e1e", 
                             sashwidth=4, sashrelief=tk.RAISED)
        main.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left panel
        left = ttk.Frame(main, width=400)
        left.pack_propagate(False)
        
        # Right panel (3D view)
        right = ttk.Frame(main)
        
        main.add(left, width=400)
        main.add(right)
        
        self.create_controls(left)
        self.create_3d_view(right)
    
    def create_controls(self, parent):
        """Serial connection controls"""
        frame = ttk.LabelFrame(parent, text="Connection", padding=10)
        frame.pack(fill="x", pady=(0, 10))
        
        # Port and baud selection
        selection_frame = ttk.Frame(frame)
        selection_frame.pack(fill="x", pady=5)
        selection_frame.columnconfigure(5, weight=1)
        
        ttk.Label(selection_frame, text="Port:").grid(row=0, column=0, padx=(0, 5), sticky="w")
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(selection_frame, textvariable=self.port_var, 
                                       width=12, state="readonly")
        self.port_combo.grid(row=0, column=1, padx=(0, 5), sticky="w")
        
        ttk.Button(selection_frame, text="Refresh", width=12, 
                  command=self.refresh_ports).grid(row=0, column=2, padx=(0, 15), sticky="ew")
        
        ttk.Label(selection_frame, text="Baud:").grid(row=0, column=3, padx=(0, 5), sticky="w")
        self.baud_var = tk.StringVar(value="115200")
        baud_combo = ttk.Combobox(selection_frame, textvariable=self.baud_var,
                                  values=["9600", "57600", "115200", "230400"],
                                  width=12, state="readonly")
        baud_combo.grid(row=0, column=4, sticky="w")

        ttk.Label(selection_frame, text="Sensor:").grid(row=1, column=0, padx=(0, 5), pady=(8, 0), sticky="w")
        self.sensor_combo = ttk.Combobox(
            selection_frame,
            textvariable=self.sensor_mode,
            values=["MPU6050", "Pololu 0J8003"],
            width=12,
            state="readonly"
        )
        self.sensor_combo.grid(row=1, column=1, padx=(0, 5), pady=(8, 0), sticky="w")
        self.sensor_combo.bind("<<ComboboxSelected>>", self.on_sensor_combo_change)
        
        # Connect button
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=10)
        
        self.connect_btn = tk.Button(btn_frame, text="Connect", 
                                      command=self.toggle_connection,
                                      bg="#22aa55", fg="white", font=("Segoe UI", 10, "bold"),
                                      relief=tk.RAISED, bd=2, cursor="hand2",
                                      activebackground="#33bb66")
        self.connect_btn.pack(fill="x", pady=(0, 5))
        
        # Pause/Resume button
        self.pause_btn = tk.Button(btn_frame, text="⏸ Pause", 
                                    command=self.toggle_pause,
                                    bg="#ff8800", fg="white", font=("Segoe UI", 9, "bold"),
                                    relief=tk.RAISED, bd=2, cursor="hand2",
                                    activebackground="#ff9922", state="disabled")
        self.pause_btn.pack(fill="x")
        
        # Action buttons
        action_frame = ttk.Frame(frame)
        action_frame.pack(fill="x", pady=5)
        
        ttk.Button(action_frame, text="Serial Monitor", 
                  command=self.open_serial_monitor).pack(fill="x", pady=(0, 5))

        if DEBUG_MODE:
            ttk.Button(action_frame, text="Debug Log", 
                      command=self.show_debug_log).pack(fill="x")
            ttk.Label(action_frame, text="🔧 Debug Mode ON",
                      foreground="#ff8800", font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(6, 0))
        
        # IMU configuration
        settings_frame = ttk.LabelFrame(parent, text="IMU Settings", padding=10)
        settings_frame.pack(fill="x", pady=(0, 10))
        for col in range(1, 4):
            settings_frame.columnconfigure(col, weight=1)
        
        ttk.Label(settings_frame, text="Calibration samples").grid(row=0, column=0, sticky="w")
        ttk.Entry(settings_frame, textvariable=self.cal_samples_var, width=10).grid(
            row=0, column=1, padx=(8, 0), sticky="ew"
        )
        ttk.Button(settings_frame, text="Calibrate", width=12,
                   command=self.start_calibration_sequence).grid(
            row=0, column=2, padx=6, sticky="ew"
        )
        
        ttk.Label(settings_frame, text="Alpha factor (0-1)").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(settings_frame, textvariable=self.alpha_factor_var, width=10).grid(
            row=1, column=1, padx=(8, 0), sticky="ew", pady=(6, 0)
        )
        ttk.Button(settings_frame, text="Set Alpha", width=12,
                   command=self.apply_alpha_setting).grid(
            row=1, column=2, padx=6, sticky="ew", pady=(6, 0)
        )
        
        ttk.Label(settings_frame, text="Sample rate (Hz)").grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(settings_frame, textvariable=self.sample_rate_var, width=10).grid(
            row=2, column=1, padx=(8, 0), sticky="ew", pady=(6, 0)
        )
        ttk.Button(settings_frame, text="Set Rate", width=12,
                   command=self.apply_sample_rate).grid(
            row=2, column=2, padx=6, sticky="ew", pady=(6, 0)
        )
        
        ttk.Label(settings_frame, text="Run duration (s)").grid(row=3, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(settings_frame, textvariable=self.run_duration_var, width=10).grid(
            row=3, column=1, padx=(8, 0), sticky="ew", pady=(6, 0)
        )
        run_button_row = ttk.Frame(settings_frame)
        run_button_row.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        run_button_row.columnconfigure(0, weight=1)
        run_button_row.columnconfigure(1, weight=1)
        ttk.Button(run_button_row, text="Run Timed",
                   command=self.start_timed_run).grid(
            row=0, column=0, sticky="ew", padx=(0, 4)
        )
        ttk.Button(run_button_row, text="Free Run",
                   command=self.start_free_run).grid(
            row=0, column=1, sticky="ew", padx=(4, 0)
        )
        
        # Frequency counter display
        freq_frame = ttk.Frame(settings_frame)
        freq_frame.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        ttk.Label(freq_frame, text="Data Rate:").pack(side="left", padx=(0, 8))
        self.freq_label = ttk.Label(freq_frame, text="0.0 Hz", font=("Consolas", 10))
        self.freq_label.pack(side="left")
        
        self.esp_pause_btn = ttk.Button(settings_frame, text="⏸ Pause ESP32",
                   command=self.toggle_esp_pause)
        self.esp_pause_btn.grid(
            row=6, column=0, columnspan=4, padx=(0, 0), sticky="ew", pady=(6, 0)
        )
        
        ttk.Button(settings_frame, text="Wipe Calibration",
                   command=self.wipe_calibration_values).grid(
            row=7, column=0, columnspan=4, padx=(0, 0), sticky="ew", pady=(6, 0)
        )
        
        self.refresh_ports()
        self.create_magnetometer_panel(parent)

    def create_magnetometer_panel(self, parent):
        """Build magnetometer view (visible for Pololu board)"""
        self.mag_frame_parent = parent
        self.mag_frame = ttk.LabelFrame(parent, text="Magnetometer", padding=10)
        self.mag_canvas = tk.Canvas(
            self.mag_frame,
            width=self.mag_canvas_size,
            height=self.mag_canvas_size,
            bg="#0d0d0d",
            highlightthickness=0
        )
        self.mag_canvas.pack(fill="x", pady=(0, 8))

        value_frame = ttk.Frame(self.mag_frame)
        value_frame.pack(fill="x", pady=(0, 6))
        for idx, axis in enumerate(("x", "y", "z")):
            value_frame.columnconfigure(idx, weight=1)
            ttk.Label(
                value_frame,
                textvariable=self.mag_value_vars[axis],
                font=("Consolas", 10)
            ).grid(row=0, column=idx, sticky="ew", padx=4)

        ttk.Label(
            self.mag_frame,
            textvariable=self.mag_heading_var,
            font=("Consolas", 11)
        ).pack(anchor="w", pady=(0, 2))

        ttk.Label(
            self.mag_frame,
            textvariable=self.mag_strength_var,
            font=("Consolas", 11)
        ).pack(anchor="w")

        # Pack then immediately update visibility so default mode hides panel
        self.mag_frame.pack(fill="x", pady=(0, 10))
        self.update_magnetometer_visibility()

    def on_sensor_combo_change(self, _event=None):
        """User manually switched sensor profile"""
        if getattr(self, "_suppress_sensor_event", False):
            return
        self.sensor_selection_locked = True
        self.update_magnetometer_visibility()

    def auto_switch_sensor_mode(self, mode):
        """Auto adjust UI when incoming data format changes"""
        if self.sensor_selection_locked:
            return
        if mode not in ("MPU6050", "Pololu 0J8003"):
            return
        if self.sensor_mode.get() == mode:
            return
        self._suppress_sensor_event = True
        self.sensor_mode.set(mode)
        self._suppress_sensor_event = False
        self.update_magnetometer_visibility()

    def update_magnetometer_visibility(self):
        """Show or hide magnetometer panel based on selection"""
        if not self.mag_frame:
            return
        should_show = self.sensor_mode.get() == "Pololu 0J8003"
        is_visible = self.mag_frame.winfo_manager() != ""
        if should_show and not is_visible:
            self.mag_frame.pack(fill="x", pady=(0, 10))
        elif not should_show and is_visible:
            self.mag_frame.pack_forget()

    def handle_magnetometer_sample(self, mx, my, mz):
        """Store and visualize magnetometer data"""
        self.mag_values["x"] = mx
        self.mag_values["y"] = my
        self.mag_values["z"] = mz

        strength = math.sqrt(mx * mx + my * my + mz * mz)
        heading = (math.degrees(math.atan2(-my, mx)) + 360.0) % 360.0 if strength > 0.05 else float("nan")

        if math.isfinite(heading):
            self.mag_heading = heading
            self.mag_heading_var.set(f"Heading: {heading:6.1f}°")
        else:
            self.mag_heading = float("nan")
            self.mag_heading_var.set("Heading: ---°")

        if strength > 0.05:
            self.mag_strength = strength
            self.mag_strength_var.set(f"Strength: {strength:6.2f} µT")
        else:
            self.mag_strength = 0.0
            self.mag_strength_var.set("Strength: --- µT")

        for axis in ("x", "y", "z"):
            value = self.mag_values[axis]
            self.mag_value_vars[axis].set(f"{axis.upper()}: {value:7.2f} µT")

        if self.sensor_mode.get() == "Pololu 0J8003":
            self.redraw_mag_canvas()

    def redraw_mag_canvas(self):
        """Draw simple compass view for magnetometer vectors"""
        if not self.mag_canvas:
            return
        canvas = self.mag_canvas
        canvas.delete("all")

        size = self.mag_canvas_size
        center = size / 2
        radius = size * 0.4

        # Compass circle and axis lines
        canvas.create_oval(
            center - radius, center - radius,
            center + radius, center + radius,
            outline="#555", width=2
        )
        canvas.create_line(center, center - radius, center, center + radius, fill="#333", width=1)
        canvas.create_line(center - radius, center, center + radius, center, fill="#333", width=1)
        canvas.create_text(center, center - radius - 10, text="N", fill="white", font=("Segoe UI", 10, "bold"))
        canvas.create_text(center, center + radius + 10, text="S", fill="white", font=("Segoe UI", 10, "bold"))
        canvas.create_text(center + radius + 10, center, text="E", fill="white", font=("Segoe UI", 10, "bold"))
        canvas.create_text(center - radius - 10, center, text="W", fill="white", font=("Segoe UI", 10, "bold"))

        if not math.isfinite(self.mag_heading):
            return

        angle_rad = math.radians(self.mag_heading)
        dx = radius * math.sin(angle_rad)
        dy = radius * math.cos(angle_rad)
        canvas.create_line(
            center,
            center,
            center + dx,
            center - dy,
            fill="#22c55e",
            width=3,
            arrow=tk.LAST
        )
    
    
    def create_3d_view(self, parent):
        """3D orientation visualization"""
        frame = ttk.LabelFrame(parent, text="IMU Orientation", padding=10)
        frame.pack(fill="both", expand=True)
        
        # View controls
        control_frame = ttk.Frame(frame)
        control_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(control_frame, text="View:").pack(side="left", padx=(0, 10))
        ttk.Button(control_frame, text="Top", width=8,
                  command=lambda: self.set_view(90, 0)).pack(side="left", padx=2)
        ttk.Button(control_frame, text="Front", width=8,
                  command=lambda: self.set_view(0, 0)).pack(side="left", padx=2)
        ttk.Button(control_frame, text="Side", width=8,
                  command=lambda: self.set_view(0, 90)).pack(side="left", padx=2)
        ttk.Button(control_frame, text="Isometric", width=8,
                  command=lambda: self.set_view(20, 45)).pack(side="left", padx=2)
        ttk.Button(control_frame, text="Reset", width=8,
                  command=self.reset_drone).pack(side="left", padx=2)
        
        # Drone size slider next to view buttons
        ttk.Label(control_frame, text="Size:").pack(side="left", padx=(20, 6))
        self.drone_scale_slider = ttk.Scale(
            control_frame,
            orient=tk.HORIZONTAL,
            from_=3.75,
            to=0.6,
            variable=self.drone_scale,
            command=self.on_drone_scale_change,
            length=150
        )
        self.drone_scale_slider.pack(side="left", padx=(0, 10))
        
        ttk.Checkbutton(control_frame, text="Auto-update 3D",
                        variable=self.auto_update_3d).pack(side="right")
        
        # Container for 3D canvas and chart
        body_frame = tk.Frame(frame, bg="#1e1e1e", highlightthickness=0)
        body_frame.pack(fill="both", expand=True)
        body_frame.columnconfigure(0, weight=1)
        body_frame.rowconfigure(0, weight=2)
        body_frame.rowconfigure(1, weight=3)
        
        view_container = tk.Frame(body_frame, bg="#1e1e1e", highlightthickness=0)
        view_container.grid(row=0, column=0, sticky="nsew")
        
        # Create matplotlib figure
        self.fig = plt.Figure(figsize=(8, 8), facecolor="#000000", dpi=80)
        self.ax = self.fig.add_subplot(111, projection="3d")
        self.ax.set_facecolor("#000000")
        
        # Set initial limits (will be adjusted by scale handler)
        # Default scale is 1.4, so calculate initial limits
        default_scale = 1.4
        max_extent = (2.2 * default_scale) + (0.6 * default_scale) + 0.5
        z_extent = (0.35 * default_scale) + 0.5
        self.ax.set_xlim(-max_extent, max_extent)
        self.ax.set_ylim(-max_extent, max_extent)
        self.ax.set_zlim(-z_extent, z_extent)
        self.ax.set_box_aspect([max_extent*2, max_extent*2, z_extent*2])
        self.ax.view_init(elev=self.view_elev, azim=self.view_azim)
        
        # Remove labels
        self.ax.set_xlabel("")
        self.ax.set_ylabel("")
        self.ax.set_zlabel("")
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.ax.set_zticks([])
        
        # Thick grid
        self.ax.grid(True, color="white", linestyle="--", linewidth=2, alpha=0.6)
        
        # Panes with thick edges
        self.ax.xaxis.pane.fill = False
        self.ax.yaxis.pane.fill = False
        self.ax.zaxis.pane.fill = False
        self.ax.xaxis.pane.set_edgecolor('white')
        self.ax.yaxis.pane.set_edgecolor('white')
        self.ax.zaxis.pane.set_edgecolor('white')
        self.ax.xaxis.pane.set_linewidth(2)
        self.ax.yaxis.pane.set_linewidth(2)
        self.ax.zaxis.pane.set_linewidth(2)
        self.ax.xaxis.pane.set_alpha(0.1)
        self.ax.yaxis.pane.set_alpha(0.1)
        self.ax.zaxis.pane.set_alpha(0.1)
        
        # Create drone
        self.create_drone_body()
        
        # Embed
        self.canvas = FigureCanvasTkAgg(self.fig, view_container)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # Overlay current values in top-right corner with color coding (using Text widget)
        values_frame = tk.Frame(view_container, bg="#000000")
        values_frame.place(relx=0.98, rely=0.0, anchor="ne")
        
        self.values_text = tk.Text(
            values_frame,
            height=3,
            width=15,
            bg="#000000",
            fg="white",
            font=("Consolas", 14, "bold"),
            wrap=tk.NONE,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            padx=5,
            pady=2
        )
        self.values_text.pack()
        self.values_text.insert("1.0", "Roll: 0.0°\nPitch: 0.0°\nYaw: 0.0°")
        self.values_text.config(state="disabled")
        
        # Configure color tags
        self.values_text.tag_config("roll", foreground="#ef4444")
        self.values_text.tag_config("pitch", foreground="#22c55e")
        self.values_text.tag_config("yaw", foreground="#06b6d4")
        
        
        
        # Chart section
        chart_frame = ttk.LabelFrame(body_frame, text="Angle Data", padding=10)
        chart_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        
        chart_controls = tk.Frame(chart_frame, bg="#1e1e1e")
        chart_controls.pack(fill="x", pady=(0, 10))
        chart_controls.columnconfigure(0, weight=0)
        chart_controls.columnconfigure(1, weight=1)
        chart_controls.columnconfigure(2, weight=0)
        chart_controls.columnconfigure(3, weight=0)
        chart_controls.columnconfigure(4, weight=0)
        
        button_group = tk.Frame(chart_controls, bg="#1e1e1e")
        button_group.grid(row=0, column=0, sticky="w")
        
        self.chart_pause_btn = tk.Button(
            button_group,
            text="Pause",
            command=self.toggle_chart_pause,
            bg="#ff8800",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief=tk.RAISED,
            bd=2,
            cursor="hand2",
            activebackground="#ff9922"
        )
        self.chart_pause_btn.pack(side="left")
        
        tk.Button(
            button_group,
            text="Clear",
            command=self.clear_chart_history,
            bg="#444",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief=tk.RAISED,
            bd=2,
            cursor="hand2",
            activebackground="#555"
        ).pack(side="left", padx=(8, 0))
        
        tk.Button(
            button_group,
            text="Export",
            command=self.export_chart_image,
            bg="#2563eb",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief=tk.RAISED,
            bd=2,
            cursor="hand2",
            activebackground="#1d4ed8"
        ).pack(side="left", padx=(8, 0))
        
        # Time display for timed mode
        self.time_label = tk.Label(
            button_group,
            text="",
            bg="#1e1e1e",
            fg="#888888",
            font=("Segoe UI", 9),
            padx=10
        )
        self.time_label.pack(side="left", padx=(16, 0))
        
        axis_toggle_frame = tk.Frame(chart_controls, bg="#1e1e1e")
        axis_toggle_frame.grid(row=0, column=1, sticky="w", padx=(16, 0))
        for axis in ["roll", "pitch", "yaw"]:
            tk.Checkbutton(
                axis_toggle_frame,
                text=axis.title(),
                variable=self.chart_axis_enabled[axis],
                command=self.refresh_chart,
                bg="#1e1e1e",
                fg=self.chart_colors[axis],
                activebackground="#1e1e1e",
                activeforeground=self.chart_colors[axis],
                selectcolor="#2b2b2b",
                font=("Segoe UI", 9, "bold"),
                padx=6
            ).pack(side="left")
        
        auto_frame = tk.Frame(chart_controls, bg="#1e1e1e")
        auto_frame.grid(row=0, column=2, sticky="w", padx=(16, 0))
        ttk.Checkbutton(
            auto_frame,
            text="Auto-scale Y",
            variable=self.chart_auto_scale,
            command=self.on_chart_scale_toggle
        ).pack(side="left")
        
        y_frame = tk.Frame(chart_controls, bg="#1e1e1e")
        y_frame.grid(row=0, column=3, sticky="w", padx=(16, 0))
        ttk.Label(y_frame, text="Y min").pack(side="left")
        self.y_min_entry = ttk.Entry(y_frame, textvariable=self.chart_y_min, width=8)
        self.y_min_entry.pack(side="left", padx=(4, 8))
        ttk.Label(y_frame, text="Y max").pack(side="left")
        self.y_max_entry = ttk.Entry(y_frame, textvariable=self.chart_y_max, width=8)
        self.y_max_entry.pack(side="left", padx=(4, 0))
        self.chart_scale_entries = [self.y_min_entry, self.y_max_entry]
        
        window_frame = tk.Frame(chart_controls, bg="#1e1e1e")
        window_frame.grid(row=0, column=4, sticky="w", padx=(16, 0))
        ttk.Label(window_frame, text="Window").pack(side="left")
        self.window_combo = ttk.Combobox(
            window_frame,
            textvariable=self.chart_window_choice,
            values=[label for label, _ in self.chart_window_options],
            state="readonly",
            width=8
        )
        self.window_combo.pack(side="left", padx=(4, 0))
        
        chart_canvas_frame = ttk.Frame(chart_frame)
        chart_canvas_frame.pack(fill="both", expand=True)
        
        self.chart_fig = plt.Figure(figsize=(11, 11), facecolor="#000000", dpi=80)
        self.chart_ax = self.chart_fig.add_subplot(111)
        self.chart_ax.set_facecolor("#050505")
        self.chart_ax.grid(True, color="#222", linestyle="--", linewidth=0.6)
        self.chart_ax.set_xlabel("Seconds", color="white")
        self.chart_ax.set_ylabel("Angle (°)", color="white")
        self.chart_ax.tick_params(colors="white")
        
        self.chart_canvas = FigureCanvasTkAgg(self.chart_fig, chart_canvas_frame)
        self.chart_canvas.get_tk_widget().pack(fill="both", expand=True)
        self.on_chart_scale_toggle()
        self.refresh_chart()
    
    def open_serial_monitor(self):
        """Open or focus the serial monitor window"""
        if self.serial_monitor_window and self.serial_monitor_window.winfo_exists():
            self.serial_monitor_window.deiconify()
            self.serial_monitor_window.lift()
            return
        
        self.serial_monitor_window = tk.Toplevel(self.root)
        self.serial_monitor_window.title("Serial Monitor")
        self.serial_monitor_window.geometry("800x600")
        self.serial_monitor_window.configure(bg="#1e1e1e")
        self.serial_monitor_window.protocol("WM_DELETE_WINDOW", self.close_serial_monitor)
        
        frame = ttk.Frame(self.serial_monitor_window, padding=10)
        frame.pack(fill="both", expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            frame,
            wrap=tk.WORD,
            background="#0d0d0d",
            foreground="#00ff00",
            insertbackground="white",
            font=("Consolas", 10)
        )
        self.log_text.pack(fill="both", expand=True)
        self.log_text.config(state="disabled")
        self.populate_log_history()
        
        scroll_frame = ttk.Frame(frame)
        scroll_frame.pack(fill="x", pady=(6, 0))
        ttk.Checkbutton(
            scroll_frame,
            text="Auto-scroll",
            variable=self.auto_scroll_log
        ).pack(anchor="w")
        
        cmd_frame = ttk.LabelFrame(frame, text="Send Command", padding=10)
        cmd_frame.pack(fill="x", pady=(10, 0))
        
        input_frame = ttk.Frame(cmd_frame)
        input_frame.pack(fill="x")
        
        self.cmd_entry = tk.Entry(
            input_frame,
            textvariable=self.cmd_var,
            bg="#2b2b2b",
            fg="white",
            insertbackground="white",
            font=("Consolas", 11),
            relief=tk.FLAT,
            bd=2
        )
        self.cmd_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.cmd_entry.bind("<Return>", lambda e: self.send_command())
        
        ttk.Button(input_frame, text="Send", command=self.send_command).pack(side="left")
    
    def close_serial_monitor(self):
        """Close the serial monitor window"""
        if self.serial_monitor_window and self.serial_monitor_window.winfo_exists():
            self.serial_monitor_window.destroy()
        self.serial_monitor_window = None
        self.log_text = None
        self.cmd_entry = None
    
    def populate_log_history(self):
        """Fill the serial monitor with existing log data"""
        if not self.log_text:
            return
        
        self.log_text.config(state="normal")
        self.log_text.delete(1.0, tk.END)
        for msg_type, ts, data in self.log_data:
            time_str = datetime.fromtimestamp(ts).strftime("%H:%M:%S.%f")[:-3]
            prefix = ">> " if msg_type == "TX" else ""
            self.log_text.insert(tk.END, f"[{time_str}] {prefix}{data}\n")
        self.trim_log_widget()
        self.log_text.config(state="disabled")
        if self.auto_scroll_log.get():
            self.log_text.see(tk.END)
    
    def trim_log_widget(self):
        """Limit the number of lines retained in the log widget"""
        if not self.log_text:
            self.log_line_count = 0
            return
        max_lines = self.max_log_lines
        try:
            total_lines = int(float(self.log_text.index("end-1c").split(".")[0]))
        except tk.TclError:
            total_lines = 0
        if total_lines > max_lines:
            excess = total_lines - max_lines
            self.log_text.delete("1.0", f"{excess + 1}.0")
            total_lines = max_lines
        self.log_line_count = total_lines
        if self.auto_scroll_log.get():
            self.log_text.see(tk.END)
    
    def create_drone_body(self):
        """Create quadcopter visualization"""
        scale = self.drone_scale.get()
        s = 0.6 * scale
        h = 0.35 * scale
        bevel = 0.08 * scale
        
        # Main body vertices with beveled corners
        body_verts = np.array([
            # Bottom face (z = -h)
            [-s+bevel, -s, -h], [s-bevel, -s, -h], [s, -s+bevel, -h], [s, s-bevel, -h],
            [s-bevel, s, -h], [-s+bevel, s, -h], [-s, s-bevel, -h], [-s, -s+bevel, -h],
            # Top face (z = h)
            [-s+bevel, -s, h], [s-bevel, -s, h], [s, -s+bevel, h], [s, s-bevel, h],
            [s-bevel, s, h], [-s+bevel, s, h], [-s, s-bevel, h], [-s, -s+bevel, h],
        ])
        
        # Body faces with beveled edges
        body_faces = [
            # Bottom face
            [body_verts[0], body_verts[1], body_verts[2], body_verts[3], 
             body_verts[4], body_verts[5], body_verts[6], body_verts[7]],
            # Top face
            [body_verts[8], body_verts[9], body_verts[10], body_verts[11],
             body_verts[12], body_verts[13], body_verts[14], body_verts[15]],
            # Side faces
            [body_verts[0], body_verts[1], body_verts[9], body_verts[8]],
            [body_verts[1], body_verts[2], body_verts[10], body_verts[9]],
            [body_verts[2], body_verts[3], body_verts[11], body_verts[10]],
            [body_verts[3], body_verts[4], body_verts[12], body_verts[11]],
            [body_verts[4], body_verts[5], body_verts[13], body_verts[12]],
            [body_verts[5], body_verts[6], body_verts[14], body_verts[13]],
            [body_verts[6], body_verts[7], body_verts[15], body_verts[14]],
            [body_verts[7], body_verts[0], body_verts[8], body_verts[15]],
        ]
        
        self.drone_body = Poly3DCollection(body_faces, alpha=0.95, 
                                          facecolors='#2563eb', 
                                          edgecolors='#1e40af', linewidths=1.5)
        self.ax.add_collection3d(self.drone_body)
        
        # Add top marker (landing pad style)
        marker_size = s * 0.6
        marker_verts = np.array([
            [0, -marker_size, h+0.01], [marker_size*0.866, marker_size*0.5, h+0.01],
            [-marker_size*0.866, marker_size*0.5, h+0.01]
        ])
        marker_faces = [[marker_verts[0], marker_verts[1], marker_verts[2]]]
        self.top_marker = Poly3DCollection(marker_faces, alpha=1.0,
                                          facecolors='#fbbf24',
                                          edgecolors='#f59e0b', linewidths=2)
        self.ax.add_collection3d(self.top_marker)
        
        # Arms and motors
        arm_length = 2.2 * scale
        arm_width = 0.15 * scale
        arm_height = 0.1 * scale
        motor_radius = 0.3 * scale
        motor_height = 0.18 * scale
        prop_radius = 0.45 * scale
        
        self.arms = []
        self.motors = []
        self.props = []
        arm_positions = [(1, 1), (-1, 1), (-1, -1), (1, -1)]
        arm_colors = ['#ef4444', '#22c55e', '#3b82f6', '#f59e0b']  # Different colors for each arm
        
        for idx, (dx, dy) in enumerate(arm_positions):
            start = np.array([dx * s, dy * s, 0])
            end = np.array([dx * arm_length, dy * arm_length, 0])
            
            arm_dir = end - start
            arm_dir = arm_dir / np.linalg.norm(arm_dir)
            perp = np.array([-arm_dir[1], arm_dir[0], 0]) * arm_width
            up = np.array([0, 0, arm_height])
            
            arm_verts = np.array([
                start - perp - up, start + perp - up, start + perp + up, start - perp + up,
                end - perp - up, end + perp - up, end + perp + up, end - perp + up
            ])
            
            arm_faces = [
                [arm_verts[0], arm_verts[1], arm_verts[5], arm_verts[4]],
                [arm_verts[2], arm_verts[3], arm_verts[7], arm_verts[6]],
                [arm_verts[0], arm_verts[3], arm_verts[7], arm_verts[4]],
                [arm_verts[1], arm_verts[2], arm_verts[6], arm_verts[5]],
                [arm_verts[4], arm_verts[5], arm_verts[6], arm_verts[7]]
            ]
            
            arm_poly = Poly3DCollection(arm_faces, alpha=0.9, 
                                       facecolors=arm_colors[idx], 
                                       edgecolors='#1e293b', linewidths=1)
            self.ax.add_collection3d(arm_poly)
            self.arms.append(arm_poly)
            
            # Motor at end
            motor_center = end
            theta = np.linspace(0, 2*np.pi, 16)
            z_bottom = np.full(16, -motor_height/2)
            z_top = np.full(16, motor_height/2)
            x_circle = motor_radius * np.cos(theta)
            y_circle = motor_radius * np.sin(theta)
            
            motor_verts = []
            for i in range(16):
                motor_verts.append(motor_center + np.array([x_circle[i], y_circle[i], z_bottom[i]]))
                motor_verts.append(motor_center + np.array([x_circle[i], y_circle[i], z_top[i]]))
            
            motor_verts = np.array(motor_verts)
            motor_faces = []
            for i in range(0, 30, 2):
                j = (i + 2) % 32
                motor_faces.append([motor_verts[i], motor_verts[j], motor_verts[j+1], motor_verts[i+1]])
            
            motor_poly = Poly3DCollection(motor_faces, alpha=0.95, 
                                         facecolors='#1e293b', 
                                         edgecolors='#475569', linewidths=1)
            self.ax.add_collection3d(motor_poly)
            self.motors.append((motor_poly, motor_center, dx, dy))
            
            # Propeller (thin disc)
            prop_z = motor_center[2] + motor_height/2 + 0.05
            prop_theta = np.linspace(0, 2*np.pi, 20)
            prop_x = motor_center[0] + prop_radius * np.cos(prop_theta)
            prop_y = motor_center[1] + prop_radius * np.sin(prop_theta)
            prop_z_arr = np.full(20, prop_z)
            
            prop_verts = []
            for i in range(20):
                prop_verts.append([prop_x[i], prop_y[i], prop_z_arr[i]])
            prop_verts.append([motor_center[0], motor_center[1], prop_z])
            
            prop_verts = np.array(prop_verts)
            prop_faces = []
            for i in range(20):
                j = (i + 1) % 20
                prop_faces.append([prop_verts[20], prop_verts[i], prop_verts[j]])
            
            prop_poly = Poly3DCollection(prop_faces, alpha=0.4,
                                        facecolors='#94a3b8',
                                        edgecolors='#64748b', linewidths=0.5)
            self.ax.add_collection3d(prop_poly)
            self.props.append(prop_poly)
        
        # Orientation vectors
        vec_length = 1.8 * scale
        self.x_vector = self.ax.quiver(0, 0, 0, vec_length, 0, 0, 
                                      color='#ef4444', arrow_length_ratio=0.15, linewidth=4)
        self.y_vector = self.ax.quiver(0, 0, 0, 0, vec_length, 0, 
                                      color='#22c55e', arrow_length_ratio=0.15, linewidth=4)
        self.z_vector = self.ax.quiver(0, 0, 0, 0, 0, vec_length, 
                                      color='#06b6d4', arrow_length_ratio=0.15, linewidth=4)
        
        # Vector labels (will be updated with vectors)
        self.x_label = self.ax.text(vec_length + 0.4, 0, 0, "X", color="#ef4444", fontsize=16, weight='bold')
        self.y_label = self.ax.text(0, vec_length + 0.4, 0, "Y", color="#22c55e", fontsize=16, weight='bold')
        self.z_label = self.ax.text(0, 0, vec_length + 0.4, "Z", color="#06b6d4", fontsize=16, weight='bold')
    
    def toggle_chart_pause(self):
        """Pause or resume chart updates"""
        self.chart_paused = not self.chart_paused
        if self.chart_pause_btn:
            if self.chart_paused:
                self.chart_pause_btn.config(text="Resume", bg="#22aa55", activebackground="#33bb66")
            else:
                self.chart_pause_btn.config(text="Pause", bg="#ff8800", activebackground="#ff9922")
        if not self.chart_paused:
            self.refresh_chart()
    
    def clear_chart_history(self):
        """Clear stored chart data"""
        self.chart_history.clear()
        self.refresh_chart()
    
    def on_drone_scale_change(self, value=None):
        """Handle drone scale slider movement"""
        try:
            scale = float(self.drone_scale.get())
        except (tk.TclError, ValueError):
            scale = 1.0
            self.drone_scale.set(scale)
        scale = max(0.4, min(3.0, scale))
        if self.drone_scale.get() != scale:
            self.drone_scale.set(scale)
        
        # Adjust axis limits based on scale to prevent clipping
        # Maximum extent: arm_length (2.2 * scale) + body half-size (0.6 * scale) + margin
        max_extent = (2.2 * scale) + (0.6 * scale) + 0.5
        z_extent = (0.35 * scale) + 0.5  # body height + margin
        
        if self.ax:
            self.ax.set_xlim(-max_extent, max_extent)
            self.ax.set_ylim(-max_extent, max_extent)
            self.ax.set_zlim(-z_extent, z_extent)
            self.ax.set_box_aspect([max_extent*2, max_extent*2, z_extent*2])
        
        self.update_3d_orientation()
    
    def _chart_setting_changed(self, *args):
        """Trace callback for chart setting vars"""
        self.apply_chart_settings()
    
    def apply_chart_settings(self):
        """Validate and apply chart scale settings"""
        if self.chart_setting_updating:
            return
        self.chart_setting_updating = True
        try:
            try:
                window = int(self.chart_window_var.get())
            except (tk.TclError, ValueError):
                window = 30
            if window < 0:
                window = 0
            elif window != 0:
                window = max(5, window)
            if self.chart_window_var.get() != window:
                self.chart_window_var.set(window)
            matching = next((label for label, val in self.chart_window_options if val == window), None)
            if matching and self.chart_window_choice.get() != matching:
                self.chart_window_choice.set(matching)
            
            try:
                y_min = float(self.chart_y_min.get())
                y_max = float(self.chart_y_max.get())
            except tk.TclError:
                y_min, y_max = -180.0, 180.0
            if y_max <= y_min:
                y_max = y_min + 1.0
                self.chart_y_max.set(y_max)
                self.chart_y_min.set(y_min)
            self.trim_chart_history()
            self.refresh_chart()
        finally:
            self.chart_setting_updating = False
    
    def on_chart_scale_toggle(self):
        """Enable/disable manual scale inputs"""
        state = "disabled" if self.chart_auto_scale.get() else "normal"
        for entry in getattr(self, "chart_scale_entries", []):
            entry.config(state=state)
        self.apply_chart_settings()
    
    def on_window_choice_change(self, *args):
        """Handle window preset selection"""
        if self.chart_setting_updating:
            return
        label = self.chart_window_choice.get()
        value = next((val for lbl, val in self.chart_window_options if lbl == label), None)
        if value is None:
            return
        self.chart_window_var.set(value)
        self.apply_chart_settings()
    
    def trim_chart_history(self):
        """Keep history bounded to configured time window"""
        if not self.chart_history:
            return
        window = self.chart_window_var.get()
        if window <= 0:
            return
        cutoff = self.chart_history[-1][0] - window
        while self.chart_history and self.chart_history[0][0] < cutoff:
            self.chart_history.popleft()
    
    def enforce_chart_limit(self):
        """Prevent unbounded chart history growth even in 'All' mode"""
        if self.chart_history_limit <= 0:
            return
        while len(self.chart_history) > self.chart_history_limit:
            self.chart_history.popleft()
    
    def append_chart_data(self, timestamp):
        """Append the latest angle data for charting"""
        self.chart_history.append((timestamp, self.roll, self.pitch, self.yaw))
        # No need to trim - maxlen handles it automatically
        if not self.chart_paused:
            self.refresh_chart()
    
    def refresh_chart(self):
        """Refresh the angle history chart"""
        if not self.chart_ax or not self.chart_canvas:
            return
        
        if self.chart_legend:
            self.chart_legend.remove()
            self.chart_legend = None
        
        if not self.chart_history:
            for axis in self.chart_colors:
                line = self.chart_lines.get(axis)
                if line:
                    line.set_data([], [])
            self.chart_ax.set_xlim(0, max(5, self.chart_window_var.get()))
            self.chart_ax.set_ylim(-1, 1)
            self.chart_canvas.draw_idle()
            return
        
        base_time = self.chart_history[0][0]
        times = [entry[0] - base_time for entry in self.chart_history]
        axis_data = {
            "roll": [entry[1] for entry in self.chart_history],
            "pitch": [entry[2] for entry in self.chart_history],
            "yaw": [entry[3] for entry in self.chart_history]
        }
        
        visible_values = []
        window = self.chart_window_var.get()
        for axis in ["roll", "pitch", "yaw"]:
            if axis not in self.chart_lines or self.chart_lines[axis] is None:
                line, = self.chart_ax.plot([], [], color=self.chart_colors[axis], linewidth=1.8, label=axis.title())
                self.chart_lines[axis] = line
            line = self.chart_lines[axis]
            line.set_data(times, axis_data[axis])
            is_visible = self.chart_axis_enabled[axis].get()
            line.set_visible(is_visible)
            if is_visible:
                visible_values.extend(axis_data[axis])
        
        x_end = times[-1]
        if window <= 0:
            x_start = 0
        else:
            x_start = max(0, x_end - window)
            if x_end - x_start < 1:
                x_end = x_start + 1
        self.chart_ax.set_xlim(x_start, x_end)
        
        if self.chart_auto_scale.get() and visible_values:
            y_min = min(visible_values)
            y_max = max(visible_values)
            if y_min == y_max:
                y_padding = 5
            else:
                y_padding = max(2, (y_max - y_min) * 0.1)
            self.chart_ax.set_ylim(y_min - y_padding, y_max + y_padding)
        else:
            y_min = float(self.chart_y_min.get())
            y_max = float(self.chart_y_max.get())
            if y_max <= y_min:
                y_max = y_min + 1
                self.chart_y_max.set(y_max)
            self.chart_ax.set_ylim(y_min, y_max)
        
        visible_lines = [self.chart_lines[axis] for axis in self.chart_lines if self.chart_lines[axis].get_visible()]
        if visible_lines:
            self.chart_legend = self.chart_ax.legend(handles=visible_lines, loc="upper right")
        else:
            self.chart_legend = None
        
        self.chart_canvas.draw_idle()
    
    def export_chart_image(self):
        """Export the chart as an image"""
        if not self.chart_fig:
            messagebox.showwarning("Export Chart", "Chart is not available yet.")
            return
        
        default_name = datetime.now().strftime("angle_chart_%Y-%m-%d_%H-%M-%S.png")
        file_path = filedialog.asksaveasfilename(
            title="Save Chart",
            defaultextension=".png",
            initialfile=default_name,
            filetypes=[("PNG Image", "*.png"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        
        try:
            self.chart_fig.savefig(file_path, facecolor=self.chart_fig.get_facecolor(), dpi=120)
            messagebox.showinfo("Export Complete", f"Chart saved to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to save chart:\n{e}")
    
    def set_view(self, elev, azim):
        """Set 3D view angle"""
        self.view_elev = elev
        self.view_azim = azim
        self.ax.view_init(elev=elev, azim=azim)
        self.canvas.draw_idle()
    
    def reset_drone(self):
        """Reset orientation and position"""
        self.roll = 0
        self.pitch = 0
        self.yaw = 0
        self.pos_x = 0
        self.pos_y = 0
        self.pos_z = 0
        self.update_3d_orientation()
        if hasattr(self, 'values_text') and self.values_text:
            self.values_text.config(state="normal")
            self.values_text.delete("1.0", tk.END)
            self.values_text.insert("1.0", "Roll: 0.0°\n", "roll")
            self.values_text.insert(tk.END, "Pitch: 0.0°\n", "pitch")
            self.values_text.insert(tk.END, "Yaw: 0.0°", "yaw")
            self.values_text.config(state="disabled")
    
    def toggle_pause(self):
        """Toggle pause/resume of data processing"""
        self.paused = not self.paused
        if self.paused:
            self.pause_btn.config(text="▶ Resume", bg="#22aa55", activebackground="#33bb66")
            self.logger.info("Data processing paused")
        else:
            self.pause_btn.config(text="⏸ Pause", bg="#ff8800", activebackground="#ff9922")
            self.logger.info("Data processing resumed")
    
    def refresh_ports(self):
        """Scan for serial ports"""
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_combo["values"] = ports
        if ports:
            self.port_combo.current(0)
    
    def toggle_connection(self):
        """Toggle connection"""
        if self.connected:
            self.disconnect()
        else:
            self.connect()
    
    def connect(self):
        """Open serial connection"""
        port = self.port_var.get()
        if not port:
            messagebox.showerror("Error", "Please select a port")
            return
        
        try:
            baud = int(self.baud_var.get())
            self.serial_port = serial.Serial(port, baudrate=baud, timeout=0.1)
            
            self.reading = True
            threading.Thread(target=self.read_serial, daemon=True).start()
            
            self.connected = True
            self.connect_btn.config(text="Disconnect", bg="#d22", activebackground="#f33")
            self.pause_btn.config(state="normal")
            self.logger.info(f"Connected to {port} at {baud} baud")
            
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            messagebox.showerror("Connection Error", f"Failed to connect:\n{e}")
    
    def disconnect(self):
        """Close serial connection"""
        self.reading = False
        
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except Exception as e:
                self.logger.error(f"Error closing port: {e}")
        
        self.connected = False
        self.connect_btn.config(text="Connect", bg="#22aa55", activebackground="#33bb66")
        self.pause_btn.config(state="disabled")
        self.paused = False
        self.pause_btn.config(text="⏸ Pause", bg="#ff8800", activebackground="#ff9922")
        self.esp_paused = False
        if hasattr(self, 'esp_pause_btn') and self.esp_pause_btn:
            self.esp_pause_btn.config(text="⏸ Pause ESP32")
        self.timed_run_active = False
        self.timed_run_data.clear()
        self.logger.info("Disconnected")
    
    def read_serial(self):
        """Read serial data in background thread"""
        self.logger.info("Serial read thread started")
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
                                self.logger.warning("Queue full, dropping data")
                except Exception as e:
                    self.logger.error(f"Serial read error: {e}")
                    break
                time.sleep(0.001)  # Small delay to prevent CPU spinning
        except Exception as e:
            self.logger.error(f"Serial thread error: {e}")
        finally:
            self.logger.info("Serial read thread stopped")
    
    def send_device_command(self, command):
        """Send a command string to the device"""
        if not self.connected or not self.serial_port:
            messagebox.showwarning("Not Connected", "Please connect to a port first")
            return False
        
        cmd = command.strip()
        if not cmd:
            return False
        
        try:
            self.serial_port.write((cmd + "\n").encode())
            timestamp = time.time()
            self.data_queue.put(("sent", timestamp, cmd))
            return True
        except Exception as e:
            messagebox.showerror("Send Error", f"Failed to send:\n{e}")
            return False
    
    def send_command(self):
        """Send command from input over serial"""
        cmd = self.cmd_var.get().strip()
        if not cmd:
            return
        if self.send_device_command(cmd):
            self.cmd_var.set("")
    
    def apply_calibration_samples(self):
        """Apply calibration sample count"""
        try:
            samples = int(self.cal_samples_var.get())
        except (tk.TclError, ValueError):
            samples = 1000
        samples = max(10, min(20000, samples))
        self.cal_samples_var.set(samples)
        self.send_device_command(f"SET_SAMPLES {samples}")
    
    def apply_alpha_setting(self):
        """Apply complementary filter alpha"""
        try:
            alpha = float(self.alpha_factor_var.get())
        except tk.TclError:
            alpha = 0.83
        alpha = max(0.0, min(0.999, alpha))
        self.alpha_factor_var.set(round(alpha, 4))
        self.send_device_command(f"SET_ALPHA {alpha:.4f}")
    
    def apply_sample_rate(self):
        """Apply sample rate setting (converts Hz to milliseconds)"""
        try:
            rate_hz = int(self.sample_rate_var.get())
        except (tk.TclError, ValueError):
            rate_hz = 100
        rate_hz = max(1, min(1000, rate_hz))
        self.sample_rate_var.set(rate_hz)
        
        # Convert Hz to milliseconds: ms = 1000 / Hz
        rate_ms = int(1000 / rate_hz)
        if rate_ms < 1:
            rate_ms = 1
        self.send_device_command(f"SET_SAMPLE_RATE {rate_ms}")
    
    def toggle_esp_pause(self):
        """Toggle ESP32 pause/resume and chart pause"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to a port first")
            return
        
        self.esp_paused = not self.esp_paused
        if self.esp_paused:
            # Pause ESP32 and chart
            self.send_device_command("PAUSE")
            if self.esp_pause_btn:
                self.esp_pause_btn.config(text="▶ Resume ESP32")
            if not self.chart_paused:
                self.chart_paused = True
                if self.chart_pause_btn:
                    self.chart_pause_btn.config(text="Resume", bg="#22aa55", activebackground="#33bb66")
        else:
            # Resume ESP32 and chart
            self.send_device_command("RESUME")
            if self.esp_pause_btn:
                self.esp_pause_btn.config(text="⏸ Pause ESP32")
            if self.chart_paused:
                self.chart_paused = False
                if self.chart_pause_btn:
                    self.chart_pause_btn.config(text="Pause", bg="#ff8800", activebackground="#ff9922")
                self.refresh_chart()
    
    def start_calibration_sequence(self):
        """Trigger calibration routine on the device"""
        self.apply_calibration_samples()
        self.send_device_command("CALIBRATE")
    
    def wipe_calibration_values(self):
        """Clear calibration values on the device"""
        self.send_device_command("CLEAR_CAL")
    
    def start_timed_run(self):
        """Start a timed streaming session"""
        try:
            duration = int(self.run_duration_var.get())
        except (tk.TclError, ValueError):
            duration = 0
        if duration <= 0:
            messagebox.showwarning("Timed Run", "Please enter a duration greater than zero.")
            return
        
        # Pause chart first
        if not self.chart_paused:
            self.chart_paused = True
            if self.chart_pause_btn:
                self.chart_pause_btn.config(text="Resume", bg="#22aa55", activebackground="#33bb66")
        
        # Set flag to wait for calibration completion
        self.waiting_for_calibration = True
        
        # Initialize data storage for timed run
        self.timed_run_data.clear()
        self.timed_run_active = True
        self.samples_after_calibration = 0
        
        # Clear chart and logs
        self.clear_chart_history()
        self.log_data.clear()
        self.pending_log_lines.clear()
        if self.log_text:
            self.log_text.config(state="normal")
            self.log_text.delete(1.0, tk.END)
            self.log_text.config(state="disabled")
        
        messagebox.showinfo(
            "Timed Run",
            f"Preparing device for a {duration}-second run.\n"
            "Calibration will be performed, then streaming will resume."
        )
        
        # Start calibration sequence (will trigger resume after ACK:CALIBRATE_DONE)
        self.start_calibration_sequence()
        self.timed_run_duration = duration
    
    def start_free_run(self):
        """Switch device to continuous streaming"""
        self.timed_run_active = False
        self.timed_run_data.clear()
        self.run_duration_var.set(0)
        self.send_device_command("RUN_FOR 0")
    
    def handle_calibration_done(self):
        """Handle calibration completion during timed run"""
        if not self.waiting_for_calibration:
            return
        
        self.waiting_for_calibration = False
        
        # Reset sample counter after calibration (will skip first 100 samples)
        self.samples_after_calibration = 0
        
        # Set timed run start time (after calibration completes)
        self.timed_run_start_time = time.time()
        
        # Clear chart again after calibration
        self.clear_chart_history()
        
        # Resume chart and start timed run
        self.chart_paused = False
        if self.chart_pause_btn:
            self.chart_pause_btn.config(text="Pause", bg="#ff8800", activebackground="#ff9922")
        
        # Start the timed run with exact duration (skipped samples are only for data collection, not timer)
        self.send_device_command(f"RUN_FOR {self.timed_run_duration}")
    
    def handle_run_complete(self):
        """Handle timed run completion"""
        self.timed_run_active = False
        self.timed_run_start_time = None
        
        # Clear time display
        if hasattr(self, 'time_label') and self.time_label:
            self.time_label.config(text="")
        
        # Pause chart if not already paused
        if not self.chart_paused:
            self.chart_paused = True
            if self.chart_pause_btn:
                self.chart_pause_btn.config(text="Resume", bg="#22aa55", activebackground="#33bb66")
        
        # Calculate and display statistics
        if self.timed_run_data:
            self.calculate_and_display_statistics()
        else:
            messagebox.showinfo(
                "Timed Run Complete",
                "The timed run has finished.\n"
                "No data collected (insufficient samples after calibration)."
            )
    
    def calculate_and_display_statistics(self):
        """Calculate and display statistics for timed run data"""
        if not self.timed_run_data or len(self.timed_run_data) < 2:
            messagebox.showwarning("Statistics", "Insufficient data for statistics calculation.")
            return
        
        # Extract data arrays
        timestamps = np.array([d[0] for d in self.timed_run_data])
        roll_data = np.array([d[1] for d in self.timed_run_data])
        pitch_data = np.array([d[2] for d in self.timed_run_data])
        yaw_data = np.array([d[3] for d in self.timed_run_data])
        
        # Convert timestamps to relative time (seconds from start)
        time_relative = timestamps - timestamps[0]
        
        # Calculate statistics for each axis
        axes = {
            "Roll": roll_data,
            "Pitch": pitch_data,
            "Yaw": yaw_data
        }
        
        stats_window = tk.Toplevel(self.root)
        stats_window.title("Timed Run Statistics")
        stats_window.geometry("700x500")
        stats_window.configure(bg="#1e1e1e")
        
        # Create scrollable frame
        main_frame = ttk.Frame(stats_window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(main_frame, bg="#1e1e1e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        scrollable_frame.bind("<Configure>", on_frame_configure)
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Mouse wheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # Header
        header = tk.Label(
            scrollable_frame,
            text=f"Timed Run Statistics\n({len(self.timed_run_data)} samples, {time_relative[-1]:.2f}s duration)",
            bg="#1e1e1e",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            pady=10
        )
        header.pack()
        
        # Configuration section
        config_frame = ttk.LabelFrame(
            scrollable_frame,
            text="Configuration",
            padding=10
        )
        config_frame.pack(fill="x", padx=10, pady=5)
        
        # Get configuration values
        cal_samples = self.cal_samples_var.get()
        alpha = self.alpha_factor_var.get()
        sample_rate_set = self.sample_rate_var.get()
        
        # Calculate measured average sample rate
        if len(timestamps) > 1 and time_relative[-1] > 0:
            measured_rate = len(timestamps) / time_relative[-1]
        else:
            measured_rate = 0.0
        
        # Note: Calibration values (AccErrorX, AccErrorY, GyroErrorX, etc.) are stored on ESP32
        # We don't have direct access to them, so we'll note that calibration was performed
        config_text = (
            f"Calibration Samples: {cal_samples}\n"
            f"Alpha Factor: {alpha:.4f}\n"
            f"Sample Rate (Set): {sample_rate_set} Hz\n"
            f"Sample Rate (Measured Avg): {measured_rate:.2f} Hz\n"
            f"Note: Calibration error values stored on ESP32"
        )
        
        config_label = tk.Label(
            config_frame,
            text=config_text,
            bg="#1e1e1e",
            fg="white",
            font=("Consolas", 10),
            justify="left",
            anchor="w"
        )
        config_label.pack(anchor="w")
        
        # Statistics for each axis
        for axis_name, data in axes.items():
            # Basic statistics
            min_val = np.min(data)
            max_val = np.max(data)
            mean_val = np.mean(data)
            std_val = np.std(data)
            rms_val = np.sqrt(np.mean(data**2))
            
            # Drift rate (linear regression slope)
            # Fits a line to the angle data over time: angle = slope * time + intercept
            # The slope represents the rate of change (drift) in degrees per second
            # Convert to degrees per minute by multiplying by 60
            if len(time_relative) > 1 and time_relative[-1] > 0:
                # Linear regression: y = mx + b where y is angle, x is time
                coeffs = np.polyfit(time_relative, data, 1)
                drift_rate_per_sec = coeffs[0]  # slope (degrees per second)
                drift_rate = drift_rate_per_sec * 60.0  # convert to degrees per minute
            else:
                drift_rate = 0.0
            
            # Create frame for this axis
            axis_frame = ttk.LabelFrame(
                scrollable_frame,
                text=axis_name,
                padding=10
            )
            axis_frame.pack(fill="x", padx=10, pady=5)
            
            # Statistics labels
            stats_text = (
                f"Min:     {min_val:8.3f}°\n"
                f"Max:     {max_val:8.3f}°\n"
                f"Mean:    {mean_val:8.3f}°\n"
                f"Std Dev: {std_val:8.3f}°\n"
                f"RMS:     {rms_val:8.3f}°\n"
                f"Drift:   {drift_rate:8.3f}°/min"
            )
            
            stats_label = tk.Label(
                axis_frame,
                text=stats_text,
                bg="#1e1e1e",
                fg="white",
                font=("Consolas", 10),
                justify="left",
                anchor="w"
            )
            stats_label.pack(anchor="w")
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Close button
        btn_frame = ttk.Frame(stats_window)
        btn_frame.pack(fill="x", pady=10)
        ttk.Button(btn_frame, text="Export Data", command=lambda: self.export_timed_run_data()).pack(side="left", padx=(0, 5))
        ttk.Button(btn_frame, text="Close", command=stats_window.destroy).pack(side="right")
        
        # Update canvas scroll region after a short delay to ensure all widgets are rendered
        stats_window.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
    
    def export_timed_run_data(self):
        """Export timed run data to CSV file with configuration and statistics"""
        if not self.timed_run_data or len(self.timed_run_data) == 0:
            messagebox.showwarning("Export", "No data to export.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Timed Run Data"
        )
        
        if not filename:
            return
        
        try:
            # Calculate statistics (similar to calculate_and_display_statistics)
            timestamps = np.array([d[0] for d in self.timed_run_data])
            roll_data = np.array([d[1] for d in self.timed_run_data])
            pitch_data = np.array([d[2] for d in self.timed_run_data])
            yaw_data = np.array([d[3] for d in self.timed_run_data])
            
            # Convert timestamps to relative time (seconds from start)
            time_relative = timestamps - timestamps[0]
            duration = time_relative[-1] if len(time_relative) > 0 else 0.0
            
            # Calculate measured sample rate
            if duration > 0:
                measured_rate = len(timestamps) / duration
            else:
                measured_rate = 0.0
            
            # Get configuration values
            cal_samples = self.cal_samples_var.get()
            alpha = self.alpha_factor_var.get()
            sample_rate_set = self.sample_rate_var.get()
            
            # Calculate statistics for each axis
            def calc_stats(data, time_rel):
                stats = {
                    'min': np.min(data),
                    'max': np.max(data),
                    'mean': np.mean(data),
                    'std': np.std(data),
                    'rms': np.sqrt(np.mean(data**2))
                }
                # Drift rate (linear regression slope)
                if len(time_rel) > 1 and time_rel[-1] > 0:
                    coeffs = np.polyfit(time_rel, data, 1)
                    drift_rate_per_sec = coeffs[0]
                    stats['drift'] = drift_rate_per_sec * 60.0  # degrees per minute
                else:
                    stats['drift'] = 0.0
                return stats
            
            roll_stats = calc_stats(roll_data, time_relative)
            pitch_stats = calc_stats(pitch_data, time_relative)
            yaw_stats = calc_stats(yaw_data, time_relative)
            
            # Get human-readable start timestamp
            start_timestamp = timestamps[0] if len(timestamps) > 0 else time.time()
            start_datetime = datetime.fromtimestamp(start_timestamp)
            start_datetime_str = start_datetime.strftime("%Y-%m-%d %H:%M:%S")
            
            with open(filename, 'w', newline='') as f:
                # Write header section with metadata
                f.write("# IMU Timed Run Data Export\n")
                f.write(f"# Start Time: {start_datetime_str}\n")
                f.write(f"# Samples: {len(self.timed_run_data)}\n")
                f.write(f"# Duration: {duration:.2f} s\n")
                f.write(f"#\n")
                f.write(f"# Configuration:\n")
                f.write(f"#   Calibration Samples: {cal_samples}\n")
                f.write(f"#   Alpha Factor: {alpha:.4f}\n")
                f.write(f"#   Sample Rate (Set): {sample_rate_set} Hz\n")
                f.write(f"#   Sample Rate (Measured): {measured_rate:.2f} Hz\n")
                f.write(f"#\n")
                f.write(f"# Statistics:\n")
                f.write(f"#   Roll:   Min={roll_stats['min']:8.3f}° Max={roll_stats['max']:8.3f}° Mean={roll_stats['mean']:8.3f}° StdDev={roll_stats['std']:8.3f}° RMS={roll_stats['rms']:8.3f}° Drift={roll_stats['drift']:8.3f}°/min\n")
                f.write(f"#   Pitch:  Min={pitch_stats['min']:8.3f}° Max={pitch_stats['max']:8.3f}° Mean={pitch_stats['mean']:8.3f}° StdDev={pitch_stats['std']:8.3f}° RMS={pitch_stats['rms']:8.3f}° Drift={pitch_stats['drift']:8.3f}°/min\n")
                f.write(f"#   Yaw:    Min={yaw_stats['min']:8.3f}° Max={yaw_stats['max']:8.3f}° Mean={yaw_stats['mean']:8.3f}° StdDev={yaw_stats['std']:8.3f}° RMS={yaw_stats['rms']:8.3f}° Drift={yaw_stats['drift']:8.3f}°/min\n")
                f.write(f"#\n")
                
                # Write data header (no timestamp column)
                f.write("Time_Relative_s,Roll_deg,Pitch_deg,Yaw_deg\n")
                
                # Write data (only relative time, no absolute timestamp)
                for i, (timestamp, roll, pitch, yaw) in enumerate(self.timed_run_data):
                    time_rel = time_relative[i]
                    f.write(f"{time_rel:.6f},{roll:.6f},{pitch:.6f},{yaw:.6f}\n")
            
            messagebox.showinfo("Export Complete", f"Data exported to:\n{filename}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export data:\n{e}")
    
    def update_loop(self):
        """Main update loop"""
        try:
            # Process queue items in batch (only if not paused)
            if not self.paused:
                processed = 0
                while not self.data_queue.empty() and processed < 100:
                    try:
                        msg_type, timestamp, line = self.data_queue.get_nowait()
                        if msg_type == "received":
                            self.process_received(timestamp, line)
                        elif msg_type == "sent":
                            self.process_sent(timestamp, line)
                        processed += 1
                    except queue.Empty:
                        break
                
                # Batch update log text
                current_time = time.time()
                if self.pending_log_lines and current_time - self.last_log_update > self.log_update_interval:
                    self.flush_log_updates()
                    self.last_log_update = current_time
                
        except Exception as e:
            self.logger.error(f"Update loop error: {e}")
        finally:
            self.root.after(50, self.update_loop)
    
    def process_received(self, timestamp, line):
        """Process incoming serial data"""
        # Store in log
        self.log_data.append(("RX", timestamp, line))
        
        # Queue text update
        time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S.%f")[:-3]
        self.pending_log_lines.append(f"[{time_str}] {line}\n")
        
        # Check for calibration completion during timed run
        if "ACK:CALIBRATE_DONE" in line and self.waiting_for_calibration:
            self.root.after(0, self.handle_calibration_done)
        
        # Check for timed run completion
        if "INFO:RUN_COMPLETE" in line:
            self.root.after(0, self.handle_run_complete)
        
        # Parse orientation (always), 3D update is gated inside the parser
        self.parse_and_update_orientation(line, timestamp)
    
    def process_sent(self, timestamp, cmd):
        """Process sent command"""
        self.log_data.append(("TX", timestamp, cmd))
        
        # Queue text updates
        time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S.%f")[:-3]
        self.pending_log_lines.append(f"[{time_str}] >> {cmd}\n")
    
    def flush_log_updates(self):
        """Batch update log text widget"""
        if not self.pending_log_lines:
            return
        
        if not self.log_text:
            self.pending_log_lines.clear()
            return
        
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, "".join(self.pending_log_lines))
        self.trim_log_widget()
        self.log_text.config(state="disabled")
        if self.auto_scroll_log.get():
            self.log_text.see(tk.END)
        self.pending_log_lines.clear()
    
    def parse_and_update_orientation(self, line, timestamp=None):
        """Parse orientation data"""
        try:
            parts = [segment.strip() for segment in line.split(",")]
            if len(parts) < 3:
                return

            roll = float(parts[0])
            pitch = float(parts[1])
            yaw = float(parts[2])
            mag_present = len(parts) >= 6
            if mag_present:
                mag_values = (float(parts[3]), float(parts[4]), float(parts[5]))
            else:
                mag_values = None

            self.roll = roll
            self.pitch = pitch
            self.yaw = yaw

            ts = timestamp or time.time()

            # Update frequency counter
            self.serial_data_times.append(ts)
            if len(self.serial_data_times) > 1:
                time_span = self.serial_data_times[-1] - self.serial_data_times[0]
                if time_span > 0:
                    self.serial_frequency = (len(self.serial_data_times) - 1) / time_span

            # Store data during timed runs (skip first 100 samples after calibration)
            if self.timed_run_active:
                self.samples_after_calibration += 1
                if self.samples_after_calibration > self.skip_calibration_samples:
                    self.timed_run_data.append((ts, self.roll, self.pitch, self.yaw))

            # Update time display for timed runs
            if self.timed_run_active and self.timed_run_start_time and hasattr(self, 'time_label') and self.time_label:
                elapsed = ts - self.timed_run_start_time
                self.timed_run_elapsed_time = elapsed
                set_duration = self.timed_run_duration
                elapsed_str = f"{int(elapsed)}s"
                set_str = f"{set_duration}s"
                self.time_label.config(
                    text=f"Set: {set_str} | Elapsed: {elapsed_str}"
                )
            elif hasattr(self, 'time_label') and self.time_label:
                self.time_label.config(text="")

            # Update frequency display
            if hasattr(self, 'freq_label') and self.freq_label:
                self.freq_label.config(text=f"{self.serial_frequency:.1f} Hz")

            # Throttle 3D updates (can be disabled via checkbox)
            current_time = time.time()
            if self.auto_update_3d.get() and current_time - self.last_3d_update >= self.min_3d_interval:
                self.update_3d_orientation()
                self.last_3d_update = current_time

            # Update values with color coding
            if hasattr(self, 'values_text') and self.values_text:
                self.values_text.config(state="normal")
                self.values_text.delete("1.0", tk.END)

                # Insert text with color tags
                self.values_text.insert("1.0", f"Roll: {self.roll:.3f}°\n", "roll")
                self.values_text.insert(tk.END, f"Pitch: {self.pitch:.3f}°\n", "pitch")
                self.values_text.insert(tk.END, f"Yaw: {self.yaw:.3f}°", "yaw")

                self.values_text.config(state="disabled")

            self.append_chart_data(ts)
            if mag_present and mag_values:
                self.auto_switch_sensor_mode("Pololu 0J8003")
                self.handle_magnetometer_sample(*mag_values)
            elif not mag_present:
                self.auto_switch_sensor_mode("MPU6050")
        except ValueError:
            pass  # Ignore parse errors silently
    
    def update_3d_orientation(self):
        """Update 3D visualization"""
        try:
            # Convert to radians
            r = math.radians(self.roll)
            p = math.radians(self.pitch)
            y = math.radians(self.yaw)
            
            # Rotation matrices
            Rx = np.array([[1, 0, 0],
                          [0, np.cos(r), -np.sin(r)],
                          [0, np.sin(r), np.cos(r)]])
            
            Ry = np.array([[np.cos(p), 0, np.sin(p)],
                          [0, 1, 0],
                          [-np.sin(p), 0, np.cos(p)]])
            
            Rz = np.array([[np.cos(y), -np.sin(y), 0],
                          [np.sin(y), np.cos(y), 0],
                          [0, 0, 1]])
            
            # Combined rotation
            R = Rz @ Ry @ Rx
            
            # Position offset
            offset = np.array([self.pos_x, self.pos_y, self.pos_z])
            
            scale = self.drone_scale.get()
            s = 0.6 * scale
            h = 0.35 * scale
            bevel = 0.08 * scale
            
            body_verts = np.array([
                # Bottom face
                [-s+bevel, -s, -h], [s-bevel, -s, -h], [s, -s+bevel, -h], [s, s-bevel, -h],
                [s-bevel, s, -h], [-s+bevel, s, -h], [-s, s-bevel, -h], [-s, -s+bevel, -h],
                # Top face
                [-s+bevel, -s, h], [s-bevel, -s, h], [s, -s+bevel, h], [s, s-bevel, h],
                [s-bevel, s, h], [-s+bevel, s, h], [-s, s-bevel, h], [-s, -s+bevel, h],
            ])
            
            rotated_body = (body_verts @ R.T) + offset
            body_faces = [
                # Bottom and top
                [rotated_body[0], rotated_body[1], rotated_body[2], rotated_body[3],
                 rotated_body[4], rotated_body[5], rotated_body[6], rotated_body[7]],
                [rotated_body[8], rotated_body[9], rotated_body[10], rotated_body[11],
                 rotated_body[12], rotated_body[13], rotated_body[14], rotated_body[15]],
                # Sides
                [rotated_body[0], rotated_body[1], rotated_body[9], rotated_body[8]],
                [rotated_body[1], rotated_body[2], rotated_body[10], rotated_body[9]],
                [rotated_body[2], rotated_body[3], rotated_body[11], rotated_body[10]],
                [rotated_body[3], rotated_body[4], rotated_body[12], rotated_body[11]],
                [rotated_body[4], rotated_body[5], rotated_body[13], rotated_body[12]],
                [rotated_body[5], rotated_body[6], rotated_body[14], rotated_body[13]],
                [rotated_body[6], rotated_body[7], rotated_body[15], rotated_body[14]],
                [rotated_body[7], rotated_body[0], rotated_body[8], rotated_body[15]],
            ]
            self.drone_body.set_verts(body_faces)
            
            # Update top marker
            marker_size = s * 0.6
            marker_verts = np.array([
                [0, -marker_size, h+0.01], [marker_size*0.866, marker_size*0.5, h+0.01],
                [-marker_size*0.866, marker_size*0.5, h+0.01]
            ])
            rotated_marker = (marker_verts @ R.T) + offset
            marker_faces = [[rotated_marker[0], rotated_marker[1], rotated_marker[2]]]
            self.top_marker.set_verts(marker_faces)
            
            # Update arms and motors
            arm_length = 2.2 * scale
            arm_width = 0.15 * scale
            arm_height = 0.1 * scale
            motor_radius = 0.3 * scale
            motor_height = 0.18 * scale
            prop_radius = 0.45 * scale
            arm_positions = [(1, 1), (-1, 1), (-1, -1), (1, -1)]
            
            for i, (dx, dy) in enumerate(arm_positions):
                start = np.array([dx * s, dy * s, 0])
                end = np.array([dx * arm_length, dy * arm_length, 0])
                
                start = (start @ R.T) + offset
                end = (end @ R.T) + offset
                
                arm_dir = end - start
                arm_dir = arm_dir / np.linalg.norm(arm_dir)
                
                perp_local = np.array([-dy, dx, 0]) * arm_width
                perp = (perp_local @ R.T)
                
                up_local = np.array([0, 0, arm_height])
                up = (up_local @ R.T)
                
                arm_verts = np.array([
                    start - perp - up, start + perp - up, start + perp + up, start - perp + up,
                    end - perp - up, end + perp - up, end + perp + up, end - perp + up
                ])
                
                arm_faces = [
                    [arm_verts[0], arm_verts[1], arm_verts[5], arm_verts[4]],
                    [arm_verts[2], arm_verts[3], arm_verts[7], arm_verts[6]],
                    [arm_verts[0], arm_verts[3], arm_verts[7], arm_verts[4]],
                    [arm_verts[1], arm_verts[2], arm_verts[6], arm_verts[5]],
                    [arm_verts[4], arm_verts[5], arm_verts[6], arm_verts[7]]
                ]
                self.arms[i].set_verts(arm_faces)
                
                # Update motor
                motor_center = end
                theta = np.linspace(0, 2*np.pi, 16)
                z_bottom = np.full(16, -motor_height/2)
                z_top = np.full(16, motor_height/2)
                x_circle = motor_radius * np.cos(theta)
                y_circle = motor_radius * np.sin(theta)
                
                motor_verts = []
                for j in range(16):
                    bottom_local = np.array([x_circle[j], y_circle[j], z_bottom[j]])
                    top_local = np.array([x_circle[j], y_circle[j], z_top[j]])
                    motor_verts.append(motor_center + (bottom_local @ R.T))
                    motor_verts.append(motor_center + (top_local @ R.T))
                
                motor_verts = np.array(motor_verts)
                motor_faces = []
                for j in range(0, 30, 2):
                    k = (j + 2) % 32
                    motor_faces.append([motor_verts[j], motor_verts[k], motor_verts[k+1], motor_verts[j+1]])
                
                self.motors[i][0].set_verts(motor_faces)
                
                # Update propeller
                prop_z_offset = motor_height/2 + 0.05
                prop_center_local = np.array([0, 0, prop_z_offset])
                prop_center_rotated = prop_center_local @ R.T
                
                prop_theta = np.linspace(0, 2*np.pi, 20)
                prop_verts = []
                for j in range(20):
                    prop_local = np.array([
                        prop_radius * np.cos(prop_theta[j]),
                        prop_radius * np.sin(prop_theta[j]),
                        prop_z_offset
                    ])
                    prop_verts.append(motor_center + (prop_local @ R.T))
                prop_verts.append(motor_center + prop_center_rotated)
                
                prop_verts = np.array(prop_verts)
                prop_faces = []
                for j in range(20):
                    k = (j + 1) % 20
                    prop_faces.append([prop_verts[20], prop_verts[j], prop_verts[k]])
                
                self.props[i].set_verts(prop_faces)
            
            # Update vectors
            self.x_vector.remove()
            self.y_vector.remove()
            self.z_vector.remove()
            
            vec_length = 1.8 * scale
            label_offset = 0.4 * scale
            x_vec = R @ np.array([vec_length, 0, 0])
            y_vec = R @ np.array([0, vec_length, 0])
            z_vec = R @ np.array([0, 0, vec_length])
            
            self.x_vector = self.ax.quiver(offset[0], offset[1], offset[2], 
                                          x_vec[0], x_vec[1], x_vec[2],
                                          color='#ef4444', arrow_length_ratio=0.15, linewidth=4)
            self.y_vector = self.ax.quiver(offset[0], offset[1], offset[2],
                                          y_vec[0], y_vec[1], y_vec[2],
                                          color='#22c55e', arrow_length_ratio=0.15, linewidth=4)
            self.z_vector = self.ax.quiver(offset[0], offset[1], offset[2],
                                          z_vec[0], z_vec[1], z_vec[2],
                                          color='#06b6d4', arrow_length_ratio=0.15, linewidth=4)
            
            # Update labels to follow vector tips
            x_label_pos = offset + x_vec * (1 + label_offset/vec_length)
            y_label_pos = offset + y_vec * (1 + label_offset/vec_length)
            z_label_pos = offset + z_vec * (1 + label_offset/vec_length)
            
            self.x_label.set_position((x_label_pos[0], x_label_pos[1]))
            self.x_label.set_3d_properties(x_label_pos[2])
            
            self.y_label.set_position((y_label_pos[0], y_label_pos[1]))
            self.y_label.set_3d_properties(y_label_pos[2])
            
            self.z_label.set_position((z_label_pos[0], z_label_pos[1]))
            self.z_label.set_3d_properties(z_label_pos[2])
            
            self.canvas.draw_idle()
            
        except Exception as e:
            self.logger.error(f"3D update error: {e}")
    
    
    def on_close(self):
        """Clean up on window close"""
        self.logger.info("Application closing")
        self.disconnect()
        self.root.destroy()
    
    def show_debug_log(self):
        """Show debug log window"""
        debug_window = tk.Toplevel(self.root)
        debug_window.title("Debug Log")
        debug_window.geometry("800x600")
        debug_window.configure(bg="#1e1e1e")
        
        frame = ttk.Frame(debug_window, padding=10)
        frame.pack(fill="both", expand=True)
        
        ttk.Label(frame, text="Debug Log (Console output):", 
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 5))
        
        text_area = scrolledtext.ScrolledText(
            frame, wrap=tk.WORD,
            background="#0d0d0d", foreground="#ffaa00",
            insertbackground="white", font=("Consolas", 9)
        )
        text_area.pack(fill="both", expand=True)
        
        # Insert logs
        text_area.insert(tk.END, self.logger.get_logs())
        text_area.config(state="disabled")
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=(10, 0))
        
        def refresh_log():
            text_area.config(state="normal")
            text_area.delete(1.0, tk.END)
            text_area.insert(tk.END, self.logger.get_logs())
            text_area.config(state="disabled")
            text_area.see(tk.END)
        
        def save_log():
            filename = f"debug_log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(self.logger.get_logs())
                messagebox.showinfo("Saved", f"Debug log saved to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save log:\n{e}")
        
        ttk.Button(btn_frame, text="Refresh", command=refresh_log).pack(side="left", padx=(0, 5))
        ttk.Button(btn_frame, text="Save Log", command=save_log).pack(side="left")
        ttk.Button(btn_frame, text="Close", command=debug_window.destroy).pack(side="right")


if __name__ == "__main__":
    root = tk.Tk()
    app = DroneIMUMonitor(root)
    root.mainloop()