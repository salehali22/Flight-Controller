/**
 * Data simulator - 50Hz telemetry. Replace with serial.js later for real FC.
 */
let intervalId = null;
let startTime = Date.now();

let yaw = 0;
let altitude = 50;
let battery = 16.8;
let gpsLat = 41.7151;
let gpsLon = 44.8271;
let modeOverride = null;

const MODES = ['MANUAL', 'AUTO', 'RTH'];

export function setFlightMode(mode) {
  modeOverride = MODES.includes(mode) ? mode : null;
}

export function cycleFlightMode() {
  const idx = MODES.indexOf(modeOverride || MODES[0]);
  modeOverride = MODES[(idx + 1) % MODES.length];
  return modeOverride;
}

export function startSimulation(callback) {
  if (intervalId) return;
  startTime = Date.now();
  yaw = 0;
  altitude = 50;
  battery = 16.8;
  gpsLat = 41.7151;
  gpsLon = 44.8271;

  intervalId = setInterval(() => {
    const elapsed = (Date.now() - startTime) / 1000;

    const data = {
      roll: Math.sin(elapsed * 0.5) * 30,
      pitch: Math.sin(elapsed * 0.3) * 20,
      yaw: (yaw += 0.5) % 360,
      altitude: altitude + (Math.random() - 0.5) * 0.5,
      battery: Math.max(10, battery - 0.00002),
      gps: {
        lat: gpsLat + (Math.random() - 0.5) * 0.00001,
        lon: gpsLon + (Math.random() - 0.5) * 0.00001
      },
      mode: modeOverride != null ? modeOverride : MODES[Math.floor(elapsed / 30) % 3],
      armed: Math.floor(elapsed / 20) % 2 === 0,
      rc: Array.from({ length: 16 }, () => 1000 + Math.random() * 1000),
      timestamp: Date.now()
    };

    try {
      callback(data);
    } catch (e) {
      console.error('Simulator callback error:', e);
    }
  }, 20);
}

export function stopSimulation() {
  if (intervalId) {
    clearInterval(intervalId);
    intervalId = null;
  }
}

export function isRunning() {
  return intervalId != null;
}
