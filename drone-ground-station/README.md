# Drone Ground Station

A professional desktop ground station application for the STM32H743VIT6 custom flight controller, built with Electron.js.

## Features

- **Dashboard Tab** — Live 3D drone attitude visualization (Three.js), telemetry cards, and 16-channel RC bar display
- **Mission Planner Tab** — Interactive map (Leaflet.js + OpenStreetMap), click-to-place waypoints, save/load missions
- **PID Tuning Tab** — Roll/Pitch/Yaw P, I, D sliders with live values
- **Configuration Tab** — Serial port management, FC info, arm/disarm control

---

## Prerequisites: Install Node.js

### Windows
1. Go to [https://nodejs.org](https://nodejs.org)
2. Download the **LTS** version (e.g., 20.x)
3. Run the installer — keep all defaults, make sure "Add to PATH" is checked
4. After install, open **Command Prompt** and verify:
   ```
   node --version
   npm --version
   ```
   Both should print version numbers.

### macOS
1. Go to [https://nodejs.org](https://nodejs.org)
2. Download the **LTS** version
3. Run the `.pkg` installer
4. Open **Terminal** and verify:
   ```
   node --version
   npm --version
   ```

---

## Setup & Run

### 1. Navigate to the project folder

```bash
cd drone-ground-station
```

### 2. Install dependencies

```bash
npm install
```

This installs Electron, electron-builder, and serialport. It may take 1–3 minutes on first run.

### 3. Run in development mode

```bash
npm start
```

The app will open immediately. The simulator starts automatically — no flight controller needed.

---

## Building a Distributable

### Windows (.exe installer)

```bash
npm run build:win
```

Output: `dist/Drone Ground Station Setup 1.0.0.exe`

### macOS (.dmg)

```bash
npm run build:mac
```

Output: `dist/Drone Ground Station-1.0.0.dmg`

> **Note:** Building for macOS requires running on a Mac. Building for Windows requires running on Windows or using a CI service.

---

## Project Structure

```
drone-ground-station/
├── package.json          # Dependencies and build config
├── README.md
└── src/
    ├── main.js           # Electron main process (window, IPC, file dialogs)
    ├── index.html        # Main window HTML (all 4 tabs)
    ├── css/
    │   └── style.css     # Dark theme stylesheet
    └── js/
        ├── simulator.js  # ← DATA SOURCE (swap this file for real serial later)
        ├── dashboard.js  # 3D model (Three.js) + telemetry cards + RC bars
        ├── mission.js    # Leaflet map + waypoint logic
        ├── pid.js        # PID sliders
        └── app.js        # Main controller: tabs, modals, data pipeline
```

---

## Swapping Simulator for Real Serial Data

When ready to connect to the actual flight controller:

1. Create `src/js/serial.js` that implements the same `DataSource` interface as `simulator.js`:
   - `DataSource.start()` — open serial port
   - `DataSource.stop()` — close serial port
   - `DataSource.onData(callback)` — register data handler
   - `DataSource.isConnected()` — return boolean
   - `DataSource.reset()` — optional reset

2. In `src/index.html`, replace:
   ```html
   <script src="js/simulator.js"></script>
   ```
   with:
   ```html
   <script src="js/serial.js"></script>
   ```

**Nothing else in the codebase needs to change.**

---

## Data Format

The `DataSource.onData(callback)` callback receives objects with this shape at 50 Hz:

```js
{
  roll:       Number,   // degrees, -180 to 180
  pitch:      Number,   // degrees, -90 to 90
  yaw:        Number,   // degrees, 0 to 360
  altitude:   Number,   // meters
  battery:    Number,   // volts
  lat:        Number,   // latitude
  lon:        Number,   // longitude
  flightMode: String,   // 'MANUAL' | 'AUTO' | 'RTH' | 'ANGLE' | 'ACRO'
  armed:      Boolean,
  channels:   Number[], // 16 values, each 1000–2000 µs
}
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `npm install` fails on serialport | Run `npm install --build-from-source` or install build tools: `npm install --global windows-build-tools` (Windows) |
| App opens blank white | Check DevTools console (Ctrl+Shift+I) for JS errors |
| Map doesn't load | Requires internet connection for OpenStreetMap tiles |
| 3D model not showing | Three.js loads from CDN — requires internet on first run |
