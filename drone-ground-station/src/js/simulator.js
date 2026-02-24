/**
 * simulator.js — Fake data source for drone telemetry.
 *
 * DATA SOURCE CONTRACT:
 * This module exposes one object: `DataSource`
 * It must implement:
 *   DataSource.start()           — begin emitting data
 *   DataSource.stop()            — stop emitting data
 *   DataSource.onData(callback)  — register a callback called at ~50Hz with a data object
 *   DataSource.isConnected()     — returns boolean
 *
 * The data object shape (same for real serial.js when you swap):
 * {
 *   roll: Number,       // degrees, -180 to 180
 *   pitch: Number,      // degrees, -90 to 90
 *   yaw: Number,        // degrees, 0 to 360
 *   altitude: Number,   // meters
 *   battery: Number,    // volts
 *   lat: Number,        // latitude
 *   lon: Number,        // longitude
 *   flightMode: String, // 'MANUAL' | 'AUTO' | 'RTH' | 'ACRO' | 'ANGLE'
 *   armed: Boolean,     // arm state
 *   channels: Number[], // 16 RC channel values (1000-2000 µs)
 * }
 *
 * TO SWAP WITH REAL SERIAL DATA:
 *   Replace this file with serial.js that reads from serialport package.
 *   Keep the same DataSource interface. Nothing else in the app changes.
 */

const DataSource = (() => {
  let _running = false;
  let _intervalId = null;
  let _callback = null;
  let _t = 0;

  // Persistent state for random walk and slow drift
  const state = {
    altitude: 50.0,
    altVelocity: 0.0,
    battery: 16.8,
    lat: 41.7151,
    lon: 44.8271,
    yaw: 0.0,
    channels: new Array(16).fill(1500),
    channelTargets: new Array(16).fill(1500),
    flightModes: ['MANUAL', 'ANGLE', 'AUTO', 'ACRO', 'RTH'],
    flightModeIdx: 0,
    flightModeTimer: 0,
    armed: false,
    armTimer: 0,
  };

  function generateData() {
    _t += 0.02; // 50Hz → dt = 20ms = 0.02s

    // Roll: sine wave ±30°, 3-second period
    const roll = 30 * Math.sin(_t * (2 * Math.PI / 3.0));

    // Pitch: sine wave ±20°, 4-second period, phase offset
    const pitch = 20 * Math.sin(_t * (2 * Math.PI / 4.0) + 1.2);

    // Yaw: slowly increments, wraps 0–360
    state.yaw = (state.yaw + 0.1) % 360;
    const yaw = state.yaw;

    // Altitude: random walk around 50m
    state.altVelocity += (Math.random() - 0.5) * 0.1;
    state.altVelocity *= 0.95; // damping
    state.altitude += state.altVelocity;
    state.altitude = Math.max(0, Math.min(200, state.altitude));
    // Drift back toward 50m
    state.altitude += (50 - state.altitude) * 0.001;
    const altitude = parseFloat(state.altitude.toFixed(2));

    // Battery: slowly decreasing from 16.8V
    state.battery -= 0.0001;
    state.battery = Math.max(12.0, state.battery);
    const battery = parseFloat(state.battery.toFixed(3));

    // GPS: slow drift
    state.lat += (Math.random() - 0.5) * 0.000005;
    state.lon += (Math.random() - 0.5) * 0.000005;
    const lat = parseFloat(state.lat.toFixed(6));
    const lon = parseFloat(state.lon.toFixed(6));

    // RC Channels: random walk toward new targets
    state.flightModeTimer++;
    if (state.flightModeTimer > 500) {
      // Change flight mode every ~10 seconds
      state.flightModeTimer = 0;
      state.flightModeIdx = (state.flightModeIdx + 1) % state.flightModes.length;
    }

    state.armTimer++;
    if (state.armTimer > 1000) {
      state.armTimer = 0;
      state.armed = !state.armed;
    }

    // RC channels random walk
    for (let i = 0; i < 16; i++) {
      if (Math.random() < 0.02) {
        // Occasionally pick new target
        state.channelTargets[i] = 1000 + Math.random() * 1000;
      }
      // Drift toward target
      state.channels[i] += (state.channelTargets[i] - state.channels[i]) * 0.05;
      state.channels[i] += (Math.random() - 0.5) * 5;
      state.channels[i] = Math.max(1000, Math.min(2000, state.channels[i]));
    }

    return {
      roll: parseFloat(roll.toFixed(2)),
      pitch: parseFloat(pitch.toFixed(2)),
      yaw: parseFloat(yaw.toFixed(1)),
      altitude,
      battery,
      lat,
      lon,
      flightMode: state.flightModes[state.flightModeIdx],
      armed: state.armed,
      channels: state.channels.map(c => Math.round(c)),
    };
  }

  return {
    onData(callback) {
      _callback = callback;
    },

    start() {
      if (_running) return;
      _running = true;
      console.log('[Simulator] Started at 50Hz');
      _intervalId = setInterval(() => {
        if (_callback) {
          _callback(generateData());
        }
      }, 20); // 50 Hz
    },

    stop() {
      if (!_running) return;
      _running = false;
      if (_intervalId) {
        clearInterval(_intervalId);
        _intervalId = null;
      }
      console.log('[Simulator] Stopped');
    },

    isConnected() {
      return _running;
    },

    // Reset simulator state
    reset() {
      state.altitude = 50.0;
      state.altVelocity = 0.0;
      state.battery = 16.8;
      state.lat = 41.7151;
      state.lon = 44.8271;
      state.yaw = 0.0;
      state.channels = new Array(16).fill(1500);
      state.channelTargets = new Array(16).fill(1500);
      state.flightModeIdx = 0;
      state.flightModeTimer = 0;
      state.armed = false;
      state.armTimer = 0;
      _t = 0;
    }
  };
})();
