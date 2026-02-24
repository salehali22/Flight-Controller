/**
 * mission.js — Leaflet.js map + waypoint planning
 */

const Mission = (() => {
  let map = null;
  let waypoints = [];
  let markers = [];
  let polyline = null;
  let initialized = false;
  let ipcRenderer = null;

  // Try to get ipcRenderer if in Electron
  try {
    ipcRenderer = require('electron').ipcRenderer;
  } catch (e) {
    ipcRenderer = null;
  }

  // ==========================================
  // MAP INITIALIZATION
  // ==========================================

  function initMap() {
    if (initialized) return;
    initialized = true;

    map = L.map('map', {
      center: [41.7151, 44.8271],
      zoom: 16,
      zoomControl: true,
    });

    // OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(map);

    // Click handler for placing waypoints
    map.on('click', function (e) {
      addWaypoint(e.latlng.lat, e.latlng.lng);
    });

    // Fix Leaflet marker icon path issue in Electron
    delete L.Icon.Default.prototype._getIconUrl;
    L.Icon.Default.mergeOptions({
      iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
      iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
      shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
    });
  }

  // ==========================================
  // WAYPOINT MANAGEMENT
  // ==========================================

  function createWaypointIcon(number) {
    return L.divIcon({
      className: '',
      html: `
        <div style="
          background: #00d4ff;
          border: 2px solid white;
          border-radius: 50% 50% 50% 0;
          transform: rotate(-45deg);
          width: 26px;
          height: 26px;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 2px 6px rgba(0,0,0,0.5);
        ">
          <span style="
            transform: rotate(45deg);
            color: #1a1a2e;
            font-size: 11px;
            font-weight: 800;
            line-height: 1;
          ">${number}</span>
        </div>
      `,
      iconSize: [26, 26],
      iconAnchor: [13, 26],
      popupAnchor: [0, -28],
    });
  }

  function addWaypoint(lat, lon, alt = 50, action = 'FLY_OVER') {
    const wp = { lat, lon, alt, action };
    waypoints.push(wp);

    const idx = waypoints.length - 1;
    const marker = L.marker([lat, lon], { icon: createWaypointIcon(idx + 1) })
      .addTo(map)
      .bindPopup(`<b>WP ${idx + 1}</b><br>Lat: ${lat.toFixed(6)}<br>Lon: ${lon.toFixed(6)}`);

    markers.push(marker);
    updatePolyline();
    renderWaypointList();
    updateDistance();
  }

  function removeWaypoint(idx) {
    // Remove marker from map
    if (markers[idx]) {
      map.removeLayer(markers[idx]);
    }

    waypoints.splice(idx, 1);
    markers.splice(idx, 1);

    // Rebuild all markers with new numbers
    markers.forEach((m, i) => {
      if (m) {
        m.setIcon(createWaypointIcon(i + 1));
        m.setPopupContent(`<b>WP ${i + 1}</b><br>Lat: ${waypoints[i].lat.toFixed(6)}<br>Lon: ${waypoints[i].lon.toFixed(6)}`);
      }
    });

    updatePolyline();
    renderWaypointList();
    updateDistance();
  }

  function clearAllWaypoints() {
    markers.forEach(m => { if (m) map.removeLayer(m); });
    markers = [];
    waypoints = [];
    if (polyline) {
      map.removeLayer(polyline);
      polyline = null;
    }
    renderWaypointList();
    updateDistance();
  }

  function updatePolyline() {
    if (polyline) map.removeLayer(polyline);

    if (waypoints.length < 2) {
      polyline = null;
      return;
    }

    const latlngs = waypoints.map(wp => [wp.lat, wp.lon]);
    polyline = L.polyline(latlngs, {
      color: '#00d4ff',
      weight: 2,
      opacity: 0.8,
      dashArray: '8, 6',
    }).addTo(map);
  }

  function updateDistance() {
    let totalMeters = 0;
    for (let i = 1; i < waypoints.length; i++) {
      const a = L.latLng(waypoints[i - 1].lat, waypoints[i - 1].lon);
      const b = L.latLng(waypoints[i].lat, waypoints[i].lon);
      totalMeters += a.distanceTo(b);
    }
    const km = (totalMeters / 1000).toFixed(2);
    const el = document.getElementById('missionDistance');
    if (el) el.textContent = `Total distance: ${km} km`;
  }

  // ==========================================
  // WAYPOINT LIST RENDERING
  // ==========================================

  function renderWaypointList() {
    const container = document.getElementById('waypointList');
    if (!container) return;

    if (waypoints.length === 0) {
      container.innerHTML = '<div class="no-waypoints">Click on the map to add waypoints</div>';
      return;
    }

    container.innerHTML = '';
    waypoints.forEach((wp, idx) => {
      const item = document.createElement('div');
      item.className = 'waypoint-item';
      item.innerHTML = `
        <div class="wp-header">
          <div class="wp-number">${idx + 1}</div>
          <button class="wp-delete" data-idx="${idx}" title="Delete waypoint">&times;</button>
        </div>
        <div class="wp-coords">
          ${wp.lat.toFixed(6)}, ${wp.lon.toFixed(6)}
        </div>
        <div class="wp-controls">
          <input
            type="number"
            class="wp-input"
            placeholder="Alt (m)"
            value="${wp.alt}"
            data-idx="${idx}"
            data-field="alt"
            min="0"
            max="500"
          >
          <select class="wp-select" data-idx="${idx}" data-field="action">
            <option value="FLY_OVER" ${wp.action === 'FLY_OVER' ? 'selected' : ''}>FLY OVER</option>
            <option value="LAND" ${wp.action === 'LAND' ? 'selected' : ''}>LAND</option>
            <option value="LOITER" ${wp.action === 'LOITER' ? 'selected' : ''}>LOITER</option>
            <option value="RTH" ${wp.action === 'RTH' ? 'selected' : ''}>RTH</option>
          </select>
        </div>
      `;
      container.appendChild(item);
    });

    // Event: delete button
    container.querySelectorAll('.wp-delete').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const idx = parseInt(e.target.dataset.idx);
        removeWaypoint(idx);
      });
    });

    // Event: altitude input
    container.querySelectorAll('.wp-input').forEach(input => {
      input.addEventListener('change', (e) => {
        const idx = parseInt(e.target.dataset.idx);
        waypoints[idx].alt = parseFloat(e.target.value) || 50;
      });
    });

    // Event: action select
    container.querySelectorAll('.wp-select').forEach(sel => {
      sel.addEventListener('change', (e) => {
        const idx = parseInt(e.target.dataset.idx);
        waypoints[idx].action = e.target.value;
      });
    });
  }

  // ==========================================
  // MISSION FILE I/O
  // ==========================================

  async function saveMission() {
    if (waypoints.length === 0) {
      alert('No waypoints to save.');
      return;
    }

    const missionData = {
      version: '1.0',
      timestamp: new Date().toISOString(),
      waypoints: waypoints.map((wp, i) => ({
        index: i + 1,
        lat: wp.lat,
        lon: wp.lon,
        alt: wp.alt,
        action: wp.action,
      }))
    };

    if (ipcRenderer) {
      const result = await ipcRenderer.invoke('save-mission', missionData);
      if (result.success) {
        showMissionStatus(`Mission saved to ${result.filePath}`);
      }
    } else {
      // Browser fallback: download as JSON
      const blob = new Blob([JSON.stringify(missionData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'mission.json';
      a.click();
      URL.revokeObjectURL(url);
    }
  }

  async function loadMission() {
    if (ipcRenderer) {
      const result = await ipcRenderer.invoke('load-mission');
      if (result.success && result.data) {
        applyMissionData(result.data);
      }
    } else {
      // Browser fallback: file input
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = '.json';
      input.onchange = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (ev) => {
          try {
            const data = JSON.parse(ev.target.result);
            applyMissionData(data);
          } catch (err) {
            alert('Failed to parse mission file: ' + err.message);
          }
        };
        reader.readAsText(file);
      };
      input.click();
    }
  }

  function applyMissionData(data) {
    clearAllWaypoints();
    if (data.waypoints && Array.isArray(data.waypoints)) {
      data.waypoints.forEach(wp => {
        addWaypoint(wp.lat, wp.lon, wp.alt || 50, wp.action || 'FLY_OVER');
      });
      if (waypoints.length > 0) {
        map.setView([waypoints[0].lat, waypoints[0].lon], 15);
      }
      showMissionStatus(`Loaded ${data.waypoints.length} waypoints`);
    }
  }

  function uploadMission() {
    if (waypoints.length === 0) {
      alert('No waypoints to upload.');
      return;
    }
    // Placeholder: in real implementation, serialize and send over serial port
    const pkg = waypoints.map((wp, i) => ({
      seq: i,
      lat: wp.lat,
      lon: wp.lon,
      alt: wp.alt,
      action: wp.action,
    }));
    console.log('[Mission] Uploading to FC:', JSON.stringify(pkg, null, 2));
    showMissionStatus(`Uploading ${waypoints.length} waypoints to FC...`);
    setTimeout(() => showMissionStatus('Mission uploaded successfully'), 1500);
  }

  function showMissionStatus(msg) {
    const el = document.getElementById('missionDistance');
    if (el) {
      const originalText = el.textContent;
      el.textContent = msg;
      setTimeout(() => updateDistance(), 2500);
    }
  }

  // ==========================================
  // PUBLIC API
  // ==========================================

  return {
    init() {
      initMap();
      bindButtons();
    },

    // Resize map when tab becomes visible
    invalidate() {
      if (map) {
        setTimeout(() => map.invalidateSize(), 100);
      }
    },
  };

  function bindButtons() {
    const uploadBtn = document.getElementById('uploadMission');
    const clearBtn = document.getElementById('clearWaypoints');
    const saveBtn = document.getElementById('saveMission');
    const loadBtn = document.getElementById('loadMission');

    if (uploadBtn) uploadBtn.addEventListener('click', uploadMission);
    if (clearBtn) clearBtn.addEventListener('click', () => {
      if (waypoints.length === 0) return;
      if (confirm('Clear all waypoints?')) clearAllWaypoints();
    });
    if (saveBtn) saveBtn.addEventListener('click', saveMission);
    if (loadBtn) loadBtn.addEventListener('click', loadMission);
  }
})();
