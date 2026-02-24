/**
 * app.js — Main application controller
 * Handles: tab switching, connect/disconnect modal, arm/disarm, data pipeline
 */

(function () {
  'use strict';

  // ==========================================
  // STATE
  // ==========================================
  let isConnected = false;
  let isArmed = false;
  let currentTab = 'dashboard';
  let ipcRenderer = null;

  // Try to get ipcRenderer in Electron context
  try {
    ipcRenderer = require('electron').ipcRenderer;
  } catch (e) {
    ipcRenderer = null;
  }

  // ==========================================
  // TAB SWITCHING
  // ==========================================

  function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));

    // Show selected tab
    const tabContent = document.getElementById(`tab-${tabName}`);
    if (tabContent) tabContent.classList.add('active');

    const tabBtn = document.querySelector(`.tab-btn[data-tab="${tabName}"]`);
    if (tabBtn) tabBtn.classList.add('active');

    currentTab = tabName;

    // Special per-tab actions
    if (tabName === 'mission') {
      Mission.invalidate();
    }
  }

  // ==========================================
  // CONNECTION MODAL
  // ==========================================

  function openConnectModal() {
    if (isConnected) {
      disconnect();
      return;
    }
    document.getElementById('connectModal').style.display = 'flex';
    refreshPorts('portSelect');
  }

  function closeConnectModal() {
    document.getElementById('connectModal').style.display = 'none';
  }

  async function refreshPorts(selectId) {
    const select = document.getElementById(selectId);
    if (!select) return;
    select.innerHTML = '<option value="">-- Scanning... --</option>';

    let ports = [];
    if (ipcRenderer) {
      ports = await ipcRenderer.invoke('list-ports');
    }

    select.innerHTML = '<option value="">-- Select Port --</option>';

    if (ports.length === 0) {
      const opt = document.createElement('option');
      opt.value = 'SIM';
      opt.textContent = 'Simulator (no real FC)';
      select.appendChild(opt);
    } else {
      ports.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.path;
        opt.textContent = `${p.path}${p.friendlyName ? ' — ' + p.friendlyName : ''}`;
        select.appendChild(opt);
      });
    }
  }

  function confirmConnect() {
    const useSimulator = document.getElementById('useSimulator').checked;
    const port = document.getElementById('portSelect').value;
    const baud = parseInt(document.getElementById('baudSelect').value);

    closeConnectModal();
    connect(useSimulator || !port, port, baud);
  }

  function connect(useSimulator, port, baud) {
    setConnectionState('connecting');

    if (useSimulator) {
      DataSource.reset();
      DataSource.onData(onData);
      DataSource.start();
      setConnectionState('connected');
      console.log('[App] Connected via simulator');
    } else {
      // Real serial connection placeholder
      // When serial.js is ready, call: DataSource.connect(port, baud, onData)
      console.log(`[App] Would connect to ${port} @ ${baud} baud`);
      setConnectionState('connected');
    }
  }

  function disconnect() {
    DataSource.stop();
    setConnectionState('disconnected');
    console.log('[App] Disconnected');
  }

  function setConnectionState(state) {
    const dot = document.querySelector('.status-dot');
    const statusText = document.getElementById('statusText');
    const connectBtn = document.getElementById('connectBtn');
    const cfgConnectBtn = document.getElementById('cfgConnectBtn');
    const cfgDisconnectBtn = document.getElementById('cfgDisconnectBtn');

    if (state === 'connected') {
      isConnected = true;
      dot.className = 'status-dot connected';
      statusText.textContent = 'CONNECTED';
      connectBtn.textContent = 'DISCONNECT';
      connectBtn.classList.add('connected');
      if (cfgConnectBtn) cfgConnectBtn.disabled = true;
      if (cfgDisconnectBtn) cfgDisconnectBtn.disabled = false;
    } else if (state === 'connecting') {
      dot.className = 'status-dot connecting';
      statusText.textContent = 'CONNECTING...';
    } else {
      isConnected = false;
      dot.className = 'status-dot disconnected';
      statusText.textContent = 'DISCONNECTED';
      connectBtn.textContent = 'CONNECT';
      connectBtn.classList.remove('connected');
      if (cfgConnectBtn) cfgConnectBtn.disabled = false;
      if (cfgDisconnectBtn) cfgDisconnectBtn.disabled = true;
    }
  }

  // ==========================================
  // DATA PIPELINE
  // ==========================================

  // This is the single entry point for all incoming telemetry.
  // DataSource (simulator.js or future serial.js) calls this at 50Hz.
  function onData(data) {
    // Update dashboard visuals
    Dashboard.update(data);

    // Sync arm state with config tab
    syncArmState(data.armed);
  }

  // ==========================================
  // ARM / DISARM
  // ==========================================

  function syncArmState(armed) {
    if (armed === isArmed) return;
    isArmed = armed;

    // Config tab LED + text
    const led = document.getElementById('cfgArmLed');
    const text = document.getElementById('cfgArmText');
    const btn = document.getElementById('cfgArmBtn');

    if (led) led.className = 'arm-led ' + (armed ? 'armed' : 'disarmed');
    if (text) text.textContent = armed ? 'ARMED' : 'DISARMED';
    if (btn) {
      btn.textContent = armed ? 'DISARM DRONE' : 'ARM DRONE';
      btn.className = 'btn-arm ' + (armed ? 'armed' : '');
    }
  }

  function showArmModal(wantToArm) {
    const modal = document.getElementById('armModal');
    const title = document.getElementById('armModalTitle');
    const text = document.getElementById('armModalText');
    const warning = document.getElementById('armWarning');
    const confirmBtn = document.getElementById('confirmArm');

    if (wantToArm) {
      title.textContent = 'ARM Confirmation';
      text.textContent = 'Are you sure you want to ARM the drone?';
      warning.style.display = '';
      confirmBtn.className = 'btn-danger';
      confirmBtn.textContent = 'CONFIRM ARM';
    } else {
      title.textContent = 'DISARM Confirmation';
      text.textContent = 'Are you sure you want to DISARM the drone?';
      warning.style.display = 'none';
      confirmBtn.className = 'btn-secondary';
      confirmBtn.textContent = 'CONFIRM DISARM';
    }

    modal.style.display = 'flex';

    confirmBtn.onclick = () => {
      modal.style.display = 'none';
      executeArmDisarm(wantToArm);
    };
  }

  function executeArmDisarm(arm) {
    // Placeholder: send arm/disarm command to FC via serial
    // DataSource.sendCommand(arm ? 'ARM' : 'DISARM');
    console.log(`[App] ${arm ? 'ARMING' : 'DISARMING'} drone`);
    syncArmState(arm);
  }

  // ==========================================
  // CONFIG TAB — PORT MANAGEMENT
  // ==========================================

  function initConfigTab() {
    refreshPorts('cfgPortSelect');

    const cfgRefresh = document.getElementById('cfgRefreshPorts');
    if (cfgRefresh) cfgRefresh.addEventListener('click', () => refreshPorts('cfgPortSelect'));

    const cfgConnect = document.getElementById('cfgConnectBtn');
    if (cfgConnect) {
      cfgConnect.addEventListener('click', () => {
        const port = document.getElementById('cfgPortSelect').value;
        const baud = parseInt(document.getElementById('cfgBaudSelect').value);
        connect(!port || port === '', port, baud);
      });
    }

    const cfgDisconnect = document.getElementById('cfgDisconnectBtn');
    if (cfgDisconnect) cfgDisconnect.addEventListener('click', disconnect);

    const armBtn = document.getElementById('cfgArmBtn');
    if (armBtn) {
      armBtn.addEventListener('click', () => {
        showArmModal(!isArmed);
      });
    }
  }

  // ==========================================
  // INITIALIZATION
  // ==========================================

  function init() {
    // Init all modules
    Dashboard.init();
    Mission.init();
    PID.init();
    initConfigTab();

    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        switchTab(btn.dataset.tab);
      });
    });

    // Connect button (header)
    document.getElementById('connectBtn').addEventListener('click', openConnectModal);

    // Connect modal buttons
    document.getElementById('closeModal').addEventListener('click', closeConnectModal);
    document.getElementById('cancelConnect').addEventListener('click', closeConnectModal);
    document.getElementById('confirmConnect').addEventListener('click', confirmConnect);
    document.getElementById('refreshPorts').addEventListener('click', () => refreshPorts('portSelect'));

    // Arm modal cancel
    document.getElementById('cancelArm').addEventListener('click', () => {
      document.getElementById('armModal').style.display = 'none';
    });

    // Close modals on overlay click
    document.getElementById('connectModal').addEventListener('click', (e) => {
      if (e.target === e.currentTarget) closeConnectModal();
    });
    document.getElementById('armModal').addEventListener('click', (e) => {
      if (e.target === e.currentTarget) {
        e.currentTarget.style.display = 'none';
      }
    });

    // Auto-start simulator on load
    DataSource.onData(onData);
    DataSource.start();
    setConnectionState('connected');

    console.log('[App] Drone Ground Station initialized');
  }

  // Start when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
