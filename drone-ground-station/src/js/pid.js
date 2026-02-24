/**
 * pid.js — PID tuning sliders for Roll, Pitch, and Yaw
 */

const PID = (() => {
  // Default PID values
  const DEFAULTS = {
    'roll-p':  4.5,
    'roll-i':  0.45,
    'roll-d':  0.04,
    'pitch-p': 4.5,
    'pitch-i': 0.45,
    'pitch-d': 0.04,
    'yaw-p':   3.0,
    'yaw-i':   0.30,
    'yaw-d':   0.00,
  };

  function getCurrentValues() {
    const vals = {};
    Object.keys(DEFAULTS).forEach(key => {
      const el = document.getElementById(key);
      vals[key] = el ? parseFloat(el.value) : DEFAULTS[key];
    });
    return vals;
  }

  function bindSliders() {
    Object.keys(DEFAULTS).forEach(key => {
      const slider = document.getElementById(key);
      const display = document.getElementById(`val-${key}`);
      if (!slider || !display) return;

      slider.addEventListener('input', () => {
        display.textContent = parseFloat(slider.value).toFixed(
          key.endsWith('-d') ? 3 : key.endsWith('-i') ? 2 : 1
        );
      });
    });
  }

  function sendToFC() {
    const vals = getCurrentValues();
    console.log('[PID] Sending to FC:', JSON.stringify(vals, null, 2));

    // Placeholder: serialize and send over serial port when real data source is active
    // Format for later serial.js:
    // DataSource.sendPID(vals);

    showStatus('PID values sent to FC!');
    setTimeout(() => showStatus(''), 3000);
  }

  function resetToDefault() {
    Object.keys(DEFAULTS).forEach(key => {
      const slider = document.getElementById(key);
      const display = document.getElementById(`val-${key}`);
      if (slider) slider.value = DEFAULTS[key];
      if (display) display.textContent = DEFAULTS[key].toFixed(
        key.endsWith('-d') ? 3 : key.endsWith('-i') ? 2 : 1
      );
    });
    showStatus('Reset to default values');
    setTimeout(() => showStatus(''), 2500);
  }

  function showStatus(msg) {
    const el = document.getElementById('pidStatus');
    if (el) el.textContent = msg;
  }

  function bindButtons() {
    const sendBtn = document.getElementById('sendPID');
    const resetBtn = document.getElementById('resetPID');
    if (sendBtn) sendBtn.addEventListener('click', sendToFC);
    if (resetBtn) resetBtn.addEventListener('click', resetToDefault);
  }

  return {
    init() {
      bindSliders();
      bindButtons();
    }
  };
})();
