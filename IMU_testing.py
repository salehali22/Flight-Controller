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
        self.log_data = deque(maxlen=10000)  # Keep last 10k entries
        self.sent_commands = deque(maxlen=1000)
        
        # UI state
        self.auto_update_3d = tk.BooleanVar(value=True)
        self.autoscroll = tk.BooleanVar(value=True)
        self.paused = False
        self.connected = False
        
        # Export settings
        self.export_range = tk.StringVar(value="all")
        self.export_from_time = ""
        self.export_to_time = ""
        
        # IMU angles
        self.roll = 0
        self.pitch = 0
        self.yaw = 0
        
        # Drone position
        self.pos_x = 0
        self.pos_y = 0
        self.pos_z = 0
        
        # 3D update throttling (reduced for less delay)
        self.last_3d_update = 0
        self.min_3d_interval = 0.016  # ~60 FPS for smoother updates
        
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
        self.create_log_view(left)
        self.create_command_view(left)
        self.create_3d_view(right)
    
    def create_controls(self, parent):
        """Serial connection controls"""
        frame = ttk.LabelFrame(parent, text="Connection", padding=10)
        frame.pack(fill="x", pady=(0, 10))
        
        # Port selection
        port_frame = ttk.Frame(frame)
        port_frame.pack(fill="x", pady=5)
        
        ttk.Label(port_frame, text="Port:").pack(side="left", padx=(0, 5))
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(port_frame, textvariable=self.port_var, 
                                       width=12, state="readonly")
        self.port_combo.pack(side="left", padx=(0, 5))
        
        ttk.Button(port_frame, text="↻", width=3, 
                  command=self.refresh_ports).pack(side="left")
        
        # Baud rate
        baud_frame = ttk.Frame(frame)
        baud_frame.pack(fill="x", pady=5)
        
        ttk.Label(baud_frame, text="Baud:").pack(side="left", padx=(0, 5))
        self.baud_var = tk.StringVar(value="115200")
        baud_combo = ttk.Combobox(baud_frame, textvariable=self.baud_var,
                                  values=["9600", "57600", "115200", "230400"],
                                  width=12, state="readonly")
        baud_combo.pack(side="left")
        
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
        
        # Options
        opt_frame = ttk.Frame(frame)
        opt_frame.pack(fill="x", pady=5)
        
        ttk.Checkbutton(opt_frame, text="Auto-update 3D", 
                       variable=self.auto_update_3d).pack(anchor="w")
        ttk.Checkbutton(opt_frame, text="Auto-scroll", 
                       variable=self.autoscroll).pack(anchor="w")
        
        # Debug mode indicator
        if DEBUG_MODE:
            debug_label = ttk.Label(opt_frame, text="🔧 Debug Mode ON", 
                                   foreground="#ff8800", font=("Segoe UI", 8, "bold"))
            debug_label.pack(anchor="w", pady=(5, 0))
        
        # Current values
        values_frame = ttk.Frame(frame)
        values_frame.pack(fill="x", pady=10)
        
        ttk.Label(values_frame, text="Current Values:", 
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.values_label = ttk.Label(values_frame, 
                                     text="Roll: 0.0°\nPitch: 0.0°\nYaw: 0.0°",
                                     font=("Consolas", 9))
        self.values_label.pack(anchor="w", padx=(10, 0))
        
        # Action buttons
        action_frame = ttk.Frame(frame)
        action_frame.pack(fill="x", pady=5)
        
        ttk.Button(action_frame, text="Clear Log", 
                  command=self.clear_log).pack(fill="x", pady=(0, 5))
        
        ttk.Button(action_frame, text="📤 Export Data Now", 
                  command=self.export_data_now).pack(fill="x", pady=(0, 5))
        
        ttk.Button(action_frame, text="⚙ Export Settings", 
                  command=self.show_export_settings).pack(fill="x", pady=(0, 5))
        
        if DEBUG_MODE:
            ttk.Button(action_frame, text="Debug Log", 
                      command=self.show_debug_log).pack(fill="x")
        
        self.refresh_ports()
    
    def create_log_view(self, parent):
        """Data log display"""
        frame = ttk.LabelFrame(parent, text="Serial Data", padding=10)
        frame.pack(fill="both", expand=True, pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(
            frame, wrap=tk.WORD, height=20,
            background="#0d0d0d", foreground="#00ff00",
            insertbackground="white", font=("Consolas", 9)
        )
        self.log_text.pack(fill="both", expand=True)
        self.log_text.config(state="disabled")
    
    def create_command_view(self, parent):
        """Command sending interface"""
        cmd_frame = ttk.LabelFrame(parent, text="Send Command", padding=10)
        cmd_frame.pack(fill="x", pady=(0, 10))
        
        input_frame = ttk.Frame(cmd_frame)
        input_frame.pack(fill="x")
        
        self.cmd_var = tk.StringVar()
        cmd_entry = tk.Entry(input_frame, textvariable=self.cmd_var,
                            bg="#2b2b2b", fg="white", insertbackground="white",
                            font=("Consolas", 10), relief=tk.FLAT, bd=2)
        cmd_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        cmd_entry.bind("<Return>", lambda e: self.send_command())
        
        ttk.Button(input_frame, text="Send", 
                  command=self.send_command).pack(side="left")
        
        # Sent commands log
        sent_frame = ttk.LabelFrame(parent, text="Sent Commands", padding=10)
        sent_frame.pack(fill="x")
        
        self.sent_text = scrolledtext.ScrolledText(
            sent_frame, wrap=tk.WORD, height=4,
            background="#0d0d0d", foreground="#ffaa00",
            insertbackground="white", font=("Consolas", 9)
        )
        self.sent_text.pack(fill="x")
        self.sent_text.config(state="disabled")
    
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
        
        # Create matplotlib figure
        self.fig = plt.Figure(figsize=(8, 8), facecolor="#000000", dpi=80)
        self.ax = self.fig.add_subplot(111, projection="3d")
        self.ax.set_facecolor("#000000")
        
        # Set limits
        self.ax.set_xlim(-4, 4)
        self.ax.set_ylim(-4, 4)
        self.ax.set_zlim(-3, 3)
        self.ax.set_box_aspect([4, 4, 3])
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
        self.canvas = FigureCanvasTkAgg(self.fig, frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
    
    def create_drone_body(self):
        """Create quadcopter visualization"""
        # Center body - more detailed with beveled edges
        s = 0.6
        h = 0.35
        bevel = 0.08
        
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
        arm_length = 2.2
        arm_width = 0.15
        arm_height = 0.1
        motor_radius = 0.3
        motor_height = 0.18
        prop_radius = 0.45
        
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
        vec_length = 1.8
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
        self.values_label.config(text="Roll: 0.0°\nPitch: 0.0°\nYaw: 0.0°\nPos: (0.0, 0.0, 0.0)")
    
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
    
    def send_command(self):
        """Send command over serial"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to a port first")
            return
        
        cmd = self.cmd_var.get().strip()
        if not cmd:
            return
        
        try:
            self.serial_port.write((cmd + "\n").encode())
            timestamp = time.time()
            self.data_queue.put(("sent", timestamp, cmd))
            self.cmd_var.set("")
        except Exception as e:
            messagebox.showerror("Send Error", f"Failed to send:\n{e}")
    
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
        
        # Parse orientation
        if self.auto_update_3d.get():
            self.parse_and_update_orientation(line)
    
    def process_sent(self, timestamp, cmd):
        """Process sent command"""
        self.log_data.append(("TX", timestamp, cmd))
        self.sent_commands.append((timestamp, cmd))
        
        # Queue text updates
        time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S.%f")[:-3]
        self.pending_log_lines.append(f"[{time_str}] >> {cmd}\n")
        
        # Update sent commands immediately
        self.sent_text.config(state="normal")
        self.sent_text.insert(tk.END, f"[{time_str}] {cmd}\n")
        self.sent_text.config(state="disabled")
        self.sent_text.see(tk.END)
    
    def flush_log_updates(self):
        """Batch update log text widget"""
        if not self.pending_log_lines:
            return
        
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, "".join(self.pending_log_lines))
        self.log_text.config(state="disabled")
        
        if self.autoscroll.get():
            self.log_text.see(tk.END)
        
        self.pending_log_lines.clear()
    
    def parse_and_update_orientation(self, line):
        """Parse orientation data"""
        try:
            parts = line.split(",")
            if len(parts) == 3:
                self.roll = float(parts[0].strip())
                self.pitch = float(parts[1].strip())
                self.yaw = float(parts[2].strip())
                
                # Throttle 3D updates
                current_time = time.time()
                if current_time - self.last_3d_update >= self.min_3d_interval:
                    self.update_3d_orientation()
                    self.last_3d_update = current_time
                    
                self.values_label.config(
                    text=f"Roll: {self.roll:.3f}°\nPitch: {self.pitch:.3f}°\nYaw: {self.yaw:.3f}°"
                )
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
            
            # Update body with beveled edges
            s = 0.6
            h = 0.35
            bevel = 0.08
            
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
            arm_length = 2.2
            arm_width = 0.15
            arm_height = 0.1
            motor_radius = 0.3
            motor_height = 0.18
            prop_radius = 0.45
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
            
            vec_length = 1.8
            label_offset = 0.4
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
    
    def clear_log(self):
        """Clear log display and data"""
        self.log_text.config(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state="disabled")
        
        self.sent_text.config(state="normal")
        self.sent_text.delete(1.0, tk.END)
        self.sent_text.config(state="disabled")
        
        self.log_data.clear()
        self.sent_commands.clear()
        self.pending_log_lines.clear()
    
    def show_export_settings(self):
        """Show export settings dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Export Settings")
        dialog.geometry("400x320")
        dialog.configure(bg="#1e1e1e")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Main container
        main_frame = tk.Frame(dialog, bg="#1e1e1e", padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = tk.Label(main_frame, text="Configure Export Range", 
                              bg="#1e1e1e", fg="white",
                              font=("Segoe UI", 11, "bold"))
        title_label.pack(pady=(0, 15))
        
        # Options
        options_frame = tk.Frame(main_frame, bg="#1e1e1e")
        options_frame.pack(fill="x", pady=(0, 10))
        
        tk.Radiobutton(options_frame, text="All data", variable=self.export_range, 
                      value="all", bg="#1e1e1e", fg="white", 
                      selectcolor="#333", activebackground="#1e1e1e",
                      activeforeground="white", font=("Segoe UI", 10)).pack(anchor="w", pady=4)
        tk.Radiobutton(options_frame, text="Last 1 minute", variable=self.export_range, 
                      value="1min", bg="#1e1e1e", fg="white",
                      selectcolor="#333", activebackground="#1e1e1e",
                      activeforeground="white", font=("Segoe UI", 10)).pack(anchor="w", pady=4)
        tk.Radiobutton(options_frame, text="Last 5 minutes", variable=self.export_range, 
                      value="5min", bg="#1e1e1e", fg="white",
                      selectcolor="#333", activebackground="#1e1e1e",
                      activeforeground="white", font=("Segoe UI", 10)).pack(anchor="w", pady=4)
        tk.Radiobutton(options_frame, text="Last 10 minutes", variable=self.export_range, 
                      value="10min", bg="#1e1e1e", fg="white",
                      selectcolor="#333", activebackground="#1e1e1e",
                      activeforeground="white", font=("Segoe UI", 10)).pack(anchor="w", pady=4)
        tk.Radiobutton(options_frame, text="Custom time range", variable=self.export_range, 
                      value="custom", bg="#1e1e1e", fg="white",
                      selectcolor="#333", activebackground="#1e1e1e",
                      activeforeground="white", font=("Segoe UI", 10)).pack(anchor="w", pady=4)
        
        # Custom time inputs
        custom_frame = tk.Frame(main_frame, bg="#1e1e1e")
        custom_frame.pack(fill="x", pady=15)
        
        tk.Label(custom_frame, text="From (HH:MM:SS):", 
                bg="#1e1e1e", fg="white", font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w", padx=(20, 10), pady=5)
        from_entry = tk.Entry(custom_frame, width=15, bg="#2b2b2b", fg="white", 
                             insertbackground="white", relief=tk.FLAT, bd=2, font=("Consolas", 10))
        from_entry.insert(0, self.export_from_time)
        from_entry.grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(custom_frame, text="To (HH:MM:SS):", 
                bg="#1e1e1e", fg="white", font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", padx=(20, 10), pady=5)
        to_entry = tk.Entry(custom_frame, width=15, bg="#2b2b2b", fg="white", 
                           insertbackground="white", relief=tk.FLAT, bd=2, font=("Consolas", 10))
        to_entry.insert(0, self.export_to_time)
        to_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Reference times
        if self.log_data:
            first_ts = datetime.fromtimestamp(self.log_data[0][1]).strftime("%H:%M:%S")
            last_ts = datetime.fromtimestamp(self.log_data[-1][1]).strftime("%H:%M:%S")
            tk.Label(custom_frame, text=f"Available: {first_ts} - {last_ts}", 
                    bg="#1e1e1e", fg="#888",
                    font=("Consolas", 8)).grid(row=2, column=0, columnspan=2, pady=8)
        
        # Save button
        def save_settings():
            self.export_from_time = from_entry.get().strip()
            self.export_to_time = to_entry.get().strip()
            messagebox.showinfo("Settings Saved", "Export settings have been saved.\nUse 'Export Data Now' to export with these settings.")
            dialog.destroy()
        
        btn_frame = tk.Frame(main_frame, bg="#1e1e1e")
        btn_frame.pack(fill="x", pady=(10, 0))
        
        save_btn = tk.Button(btn_frame, text="Save Settings", command=save_settings,
                            bg="#22aa55", fg="white", font=("Segoe UI", 10, "bold"),
                            relief=tk.RAISED, bd=2, cursor="hand2",
                            activebackground="#33bb66", padx=25, pady=8)
        save_btn.pack(side="left", padx=(0, 10))
        
        cancel_btn = tk.Button(btn_frame, text="Cancel", command=dialog.destroy,
                              bg="#555", fg="white", font=("Segoe UI", 10),
                              relief=tk.RAISED, bd=2, cursor="hand2",
                              activebackground="#666", padx=20, pady=8)
        cancel_btn.pack(side="left")
    
    def export_data_now(self):
        """Export data using saved settings"""
        if not self.log_data:
            messagebox.showinfo("No Data", "No data to export. Connect and collect data first.")
            return
        
        range_type = self.export_range.get()
        
        if range_type == "custom":
            if not self.export_from_time or not self.export_to_time:
                result = messagebox.askyesno("Custom Range Not Set", 
                                            "Custom time range is not configured.\n\nOpen Export Settings?")
                if result:
                    self.show_export_settings()
                return
            try:
                self.export_data(range_type, self.export_from_time, self.export_to_time)
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export:\n{e}")
        else:
            self.export_data(range_type)
    
    def export_data(self, time_window, from_time=None, to_time=None):
        """Export logged data to file"""
        if not self.log_data:
            return
        
        # Create export folder
        now = datetime.now()
        folder_name = now.strftime("imu_export_%Y-%m-%d_%H-%M-%S")
        
        try:
            os.makedirs(folder_name, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to create folder:\n{e}")
            return
        
        # Filter data
        current_time = time.time()
        
        if time_window == "custom":
            today = datetime.now().date()
            from_dt = datetime.strptime(from_time, "%H:%M:%S")
            to_dt = datetime.strptime(to_time, "%H:%M:%S")
            
            from_timestamp = datetime.combine(today, from_dt.time()).timestamp()
            to_timestamp = datetime.combine(today, to_dt.time()).timestamp()
            
            filtered_data = [(t, ts, d) for t, ts, d in self.log_data 
                           if from_timestamp <= ts <= to_timestamp]
        elif time_window == "1min":
            cutoff = current_time - 60
            filtered_data = [(t, ts, d) for t, ts, d in self.log_data if ts >= cutoff]
        elif time_window == "5min":
            cutoff = current_time - 300
            filtered_data = [(t, ts, d) for t, ts, d in self.log_data if ts >= cutoff]
        elif time_window == "10min":
            cutoff = current_time - 600
            filtered_data = [(t, ts, d) for t, ts, d in self.log_data if ts >= cutoff]
        else:  # all
            filtered_data = list(self.log_data)
        
        # Create filename
        filename = os.path.join(folder_name, now.strftime("imu_log_%Y-%m-%d_%H-%M-%S.csv"))
        
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write("Type,Timestamp,Time,Data\n")
                for msg_type, ts, data in filtered_data:
                    time_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    # Escape data that might contain commas
                    data_escaped = data.replace('"', '""')
                    f.write(f'{msg_type},{ts},{time_str},"{data_escaped}"\n')
            
            rx_count = sum(1 for t, _, _ in filtered_data if t == "RX")
            tx_count = sum(1 for t, _, _ in filtered_data if t == "TX")
            
            messagebox.showinfo("Export Complete", 
                              f"Data saved to:\n{filename}\n\n"
                              f"Received: {rx_count} records\n"
                              f"Sent: {tx_count} records\n"
                              f"Total: {len(filtered_data)} records")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to save:\n{e}")
    
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