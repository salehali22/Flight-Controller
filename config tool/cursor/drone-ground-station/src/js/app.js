/**
 * Main controller: tab switching, RC channel DOM, simulator wiring, telemetry + 3D + charts updates.
 */
import { startSimulation, stopSimulation, isRunning, cycleFlightMode } from './simulator.js';
import { initCharts, pushTelemetry, updateCharts } from './charts.js';

let updateAttitudeFn = null;
let updateStatusBarFn = null;
let setVehicleTypeFn = null;

const SPARKLINE_SAMPLES = 100;
const sparklineBuffers = {
  roll: [], pitch: [], yaw: [], altitude: [], battery: []
};

const RC_LABELS = ['AIL', 'ELE', 'THR', 'RUD', 'AUX1', 'AUX2', 'AUX3', 'AUX4', 'AUX5', 'AUX6', 'AUX7', 'AUX8', 'AUX9', 'AUX10', 'AUX11', 'AUX12'];

function pushSpark(key, value) {
  const b = sparklineBuffers[key];
  if (!b) return;
  b.push(value);
  if (b.length > SPARKLINE_SAMPLES) b.shift();
}

function drawSparkline(canvasId, bufferKey, options = {}) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !sparklineBuffers[bufferKey]) return;
  const data = sparklineBuffers[bufferKey];
  const w = canvas.width = canvas.offsetWidth;
  const h = canvas.height = canvas.offsetHeight;
  if (!w || !h) return;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, w, h);
  if (data.length < 2) return;
  const min = options.min !== undefined ? options.min : Math.min(...data);
  const max = options.max !== undefined ? options.max : Math.max(...data);
  const range = max - min || 1;
  const pad = 2;
  ctx.strokeStyle = options.color || '#00d4ff';
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let i = 0; i < data.length; i++) {
    const x = pad + (i / (data.length - 1)) * (w - 2 * pad);
    const y = h - pad - ((data[i] - min) / range) * (h - 2 * pad);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();
}

function updateTelemetryCards(data) {
  const rollEl = document.getElementById('roll-value');
  const pitchEl = document.getElementById('pitch-value');
  const yawEl = document.getElementById('yaw-value');
  const altEl = document.getElementById('altitude-value');
  const batEl = document.getElementById('battery-value');
  const gpsLatEl = document.getElementById('gps-lat');
  const gpsLonEl = document.getElementById('gps-lon');
  const modeEl = document.getElementById('flight-mode');
  const armEl = document.getElementById('arm-status');

  if (rollEl) rollEl.textContent = data.roll.toFixed(1) + '°';
  if (pitchEl) pitchEl.textContent = data.pitch.toFixed(1) + '°';
  if (yawEl) yawEl.textContent = data.yaw.toFixed(1) + '°';
  if (altEl) altEl.textContent = data.altitude.toFixed(1) + ' m';
  if (batEl) {
    batEl.textContent = data.battery.toFixed(2) + ' V';
    batEl.classList.remove('battery-ok', 'battery-warn', 'battery-low');
    if (data.battery > 16) batEl.classList.add('battery-ok');
    else if (data.battery >= 14) batEl.classList.add('battery-warn');
    else batEl.classList.add('battery-low');
  }
  if (gpsLatEl) gpsLatEl.textContent = 'Lat: ' + data.gps.lat.toFixed(5);
  if (gpsLonEl) gpsLonEl.textContent = 'Lon: ' + data.gps.lon.toFixed(5);
  if (modeEl) modeEl.textContent = data.mode;
  if (armEl) {
    armEl.textContent = data.armed ? 'ARMED' : 'DISARMED';
    armEl.classList.toggle('armed', data.armed);
    armEl.classList.toggle('disarmed', !data.armed);
  }

  pushSpark('roll', data.roll);
  pushSpark('pitch', data.pitch);
  pushSpark('yaw', data.yaw);
  pushSpark('altitude', data.altitude);
  pushSpark('battery', data.battery);
  drawSparkline('roll-sparkline', 'roll', { min: -45, max: 45 });
  drawSparkline('pitch-sparkline', 'pitch', { min: -45, max: 45 });
  drawSparkline('yaw-sparkline', 'yaw', { min: 0, max: 360 });
  drawSparkline('altitude-sparkline', 'altitude');
  drawSparkline('battery-sparkline', 'battery', { min: 10, max: 18 });
}

function updateRCChannels(rc) {
  for (let i = 0; i < 16; i++) {
    const row = document.getElementById('rc-row-' + (i + 1));
    if (!row) continue;
    const val = rc[i] != null ? rc[i] : 1500;
    const pct = ((val - 1000) / 1000) * 100;
    const fill = row.querySelector('.rc-bar-fill');
    const valueEl = row.querySelector('.rc-value');
    if (fill) fill.style.width = pct + '%';
    if (valueEl) valueEl.textContent = Math.round(val);
  }
}

function buildRCChannels() {
  const container = document.getElementById('rc-channels');
  if (!container) return;
  container.innerHTML = '';
  for (let i = 0; i < 16; i++) {
    const label = RC_LABELS[i] || 'CH' + (i + 1);
    const div = document.createElement('div');
    div.className = 'rc-channel';
    div.id = 'rc-row-' + (i + 1);
    div.innerHTML =
      '<div class="rc-label">CH' + (i + 1) + ' ' + label + '</div>' +
      '<div class="rc-bar"><div class="rc-bar-fill" style="width: 50%"></div></div>' +
      '<div class="rc-value">1500</div>';
    container.appendChild(div);
  }
}

function setConnectionStatus(connected) {
  const el = document.getElementById('connection-status');
  if (!el) return;
  el.classList.remove('status-disconnected', 'status-connected', 'status-connecting');
  el.classList.add(connected ? 'status-connected' : 'status-disconnected');
  const text = el.querySelector('.status-text');
  if (text) text.textContent = connected ? 'CONNECTED' : 'DISCONNECTED';
}

function showError(msg) {
  const modal = document.getElementById('error-modal');
  const msgEl = document.getElementById('error-message');
  if (msgEl) msgEl.textContent = msg || 'Unknown error';
  if (modal) modal.classList.remove('hidden');
}

function hideError() {
  const modal = document.getElementById('error-modal');
  if (modal) modal.classList.add('hidden');
}

function onSimulationData(data) {
  updateTelemetryCards(data);
  pushTelemetry(data);
  if (updateAttitudeFn) updateAttitudeFn(data.roll, data.pitch, data.yaw, data.rc[2] != null ? data.rc[2] : 1500);
  if (updateStatusBarFn) updateStatusBarFn(data.roll, data.pitch, data.yaw);
  updateRCChannels(data.rc);
}

function startDataConnection() {
  hideError();
  const source = document.getElementById('data-source')?.value || 'simulator';
  if (source === 'simulator') {
    try {
      stopSimulation();
      startSimulation(onSimulationData);
      setConnectionStatus(true);
      updateConnectButton(true);
    } catch (e) {
      setConnectionStatus(false);
      updateConnectButton(false);
      showError(e && e.message ? e.message : 'Failed to start data simulator');
    }
  } else {
    stopSimulation();
    setConnectionStatus(false);
    updateConnectButton(false);
  }
}

function disconnect() {
  stopSimulation();
  setConnectionStatus(false);
  updateConnectButton(false);
}

function updateConnectButton(connected) {
  const btn = document.getElementById('connect-btn');
  if (!btn) return;
  btn.textContent = connected ? 'DISCONNECT' : 'CONNECT';
  btn.classList.toggle('btn-disconnect', connected);
  btn.classList.toggle('btn-connect', !connected);
}

function setupTabs() {
  const main = document.querySelector('.main-layout');
  const placeholders = {
    mission: document.getElementById('tab-mission'),
    pid: document.getElementById('tab-pid'),
    config: document.getElementById('tab-config')
  };
  document.querySelectorAll('.tab-button').forEach(btn => {
    btn.addEventListener('click', () => {
      const tab = btn.dataset.tab;
      document.querySelectorAll('.tab-button').forEach(b => b.classList.remove('tab-active'));
      btn.classList.add('tab-active');
      if (tab === 'dashboard') {
        if (main) main.classList.remove('hidden');
        Object.values(placeholders).forEach(el => { if (el) el.classList.add('hidden'); });
      } else {
        if (main) main.classList.add('hidden');
        Object.keys(placeholders).forEach(key => {
          const el = placeholders[key];
          if (el) el.classList.toggle('hidden', key !== tab);
        });
      }
    });
  });
}

function setupErrorModal() {
  document.getElementById('error-retry')?.addEventListener('click', () => {
    startDataConnection();
  });
  document.getElementById('error-dismiss')?.addEventListener('click', hideError);
  document.querySelector('#error-modal .modal-overlay')?.addEventListener('click', hideError);
}

function tick() {
  updateCharts();
  requestAnimationFrame(tick);
}

async function init() {
  buildRCChannels();
  setupTabs();
  setupErrorModal();
  initCharts();
  updateConnectButton(false);
  document.getElementById('connect-btn')?.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (isRunning()) disconnect();
    else startDataConnection();
  });
  tick();

  document.getElementById('flight-mode')?.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    const mode = cycleFlightMode();
    const el = document.getElementById('flight-mode');
    if (el) el.textContent = mode;
  });

  document.getElementById('data-source')?.addEventListener('change', () => {
    const portSel = document.getElementById('port-selector');
    const isSerial = document.getElementById('data-source')?.value === 'serial';
    if (portSel) portSel.classList.toggle('hidden', !isSerial);
    if (isRunning()) disconnect();
  });

  try {
    const dash = await import('./dashboard.js');
    const container = document.getElementById('three-container');
    dash.initDashboard(container);
    updateAttitudeFn = dash.updateAttitude;
    updateStatusBarFn = dash.updateStatusBar;
    setVehicleTypeFn = dash.setVehicleType;
    dash.getVehicleSelectElement()?.addEventListener('change', (e) => {
      if (setVehicleTypeFn) setVehicleTypeFn(e.target.value);
    });
  } catch (e) {
    console.error('3D dashboard failed:', e);
    const msg = document.getElementById('three-container');
    if (msg) msg.innerHTML = '<div class="three-fallback">3D view failed to load. Check console.</div>';
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
