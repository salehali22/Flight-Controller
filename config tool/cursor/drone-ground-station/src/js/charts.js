/**
 * Chart.js wrapper - 4 sparkline charts (roll, pitch, yaw, altitude), last 60s.
 * Expects global Chart from script tag.
 */
const MAX_POINTS = 60 * 50; // 60 sec at 50Hz
const UPDATE_INTERVAL_MS = 100;

const chartConfig = {
  type: 'line',
  data: {
    labels: [],
    datasets: [{
      data: [],
      borderColor: '#00d4ff',
      borderWidth: 2,
      fill: false,
      pointRadius: 0,
      tension: 0.1
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { enabled: false }
    },
    scales: {
      x: { display: false },
      y: { display: false }
    },
    animation: false
  }
};

const buffers = {
  roll: [],
  pitch: [],
  yaw: [],
  altitude: []
};

let chartInstances = {};
let lastUpdate = 0;

function createChart(canvasId, bufferKey) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || typeof Chart === 'undefined') return null;
  const cfg = JSON.parse(JSON.stringify(chartConfig));
  const chart = new Chart(canvas, cfg);
  chart.bufferKey = bufferKey;
  return chart;
}

export function initCharts() {
  chartInstances.roll = createChart('chart-roll', 'roll');
  chartInstances.pitch = createChart('chart-pitch', 'pitch');
  chartInstances.yaw = createChart('chart-yaw', 'yaw');
  chartInstances.altitude = createChart('chart-altitude', 'altitude');
  lastUpdate = Date.now();
}

function pushBuffer(key, value) {
  const b = buffers[key];
  b.push(value);
  if (b.length > MAX_POINTS) b.shift();
}

export function pushTelemetry(data) {
  pushBuffer('roll', data.roll);
  pushBuffer('pitch', data.pitch);
  pushBuffer('yaw', data.yaw);
  pushBuffer('altitude', data.altitude);
}

export function updateCharts() {
  const now = Date.now();
  if (now - lastUpdate < UPDATE_INTERVAL_MS) return;
  lastUpdate = now;

  const keys = ['roll', 'pitch', 'yaw', 'altitude'];
  keys.forEach(key => {
    const ch = chartInstances[key];
    if (!ch || !ch.data.datasets[0]) return;
    ch.data.datasets[0].data = buffers[key].slice();
    ch.update('none');
  });
}
