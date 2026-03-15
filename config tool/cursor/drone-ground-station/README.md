# Drone Ground Station

Professional telemetry and configuration tool for STM32H743VIT6 flight controller.

## Installation

1. Install Node.js 18+ from `https://nodejs.org`
2. Clone this repository
3. Run: `npm install`
4. Run: `npm start`

## Development

- `npm start` - Launch in development mode
- `npm run build` - Build distributable (.exe for Windows, .dmg for Mac)

## 3D Models

- **Fixed-Wing**: Loads real Airbus A320 GLB model from [Flightradar24/fr24-3d-models](https://github.com/Flightradar24/fr24-3d-models) (GPL-2.0). Requires internet on first load.
- **Quad/Tri/Hexacopter**: Procedural models (Three.js primitives).

## Tech Stack

- Electron.js (desktop app framework)
- Three.js (3D visualization)
- Chart.js (telemetry graphs)
- Vanilla JavaScript (no frameworks)

## Current Status

✅ Dashboard tab with simulated data  
⏳ Mission Planner tab (coming soon)  
⏳ PID Tuning tab (coming soon)  
⏳ Configuration tab (coming soon)

