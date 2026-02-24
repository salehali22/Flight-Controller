/**
 * dashboard.js — 3D drone model (Three.js) + telemetry display + RC channels
 */

const Dashboard = (() => {
  // ---- Three.js state ----
  let scene, camera, renderer, droneGroup;
  let propellers = [];
  let animFrameId = null;
  let currentRoll = 0, currentPitch = 0, currentYaw = 0;
  let targetRoll = 0, targetPitch = 0, targetYaw = 0;

  // ---- RC Channel bars ----
  const RC_CHANNEL_NAMES = [
    'CH1 AIL', 'CH2 ELE', 'CH3 THR', 'CH4 RUD',
    'CH5 AUX1', 'CH6 AUX2', 'CH7 AUX3', 'CH8 AUX4',
    'CH9', 'CH10', 'CH11', 'CH12',
    'CH13', 'CH14', 'CH15', 'CH16'
  ];

  // ==========================================
  // THREE.JS SCENE SETUP
  // ==========================================

  function initThreeJS() {
    const container = document.getElementById('threejs-container');
    if (!container) return;

    const w = container.clientWidth;
    const h = container.clientHeight;

    // Scene
    scene = new THREE.Scene();
    scene.background = null; // transparent — CSS handles the background

    // Camera
    camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 1000);
    camera.position.set(0, 3, 7);
    camera.lookAt(0, 0, 0);

    // Renderer
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(w, h);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);

    // Lighting
    const ambient = new THREE.AmbientLight(0x334466, 0.8);
    scene.add(ambient);

    const keyLight = new THREE.DirectionalLight(0x00d4ff, 1.2);
    keyLight.position.set(5, 8, 5);
    keyLight.castShadow = true;
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0x446688, 0.5);
    fillLight.position.set(-5, 3, -5);
    scene.add(fillLight);

    const rimLight = new THREE.PointLight(0x00d4ff, 0.4, 20);
    rimLight.position.set(0, -3, 0);
    scene.add(rimLight);

    // Build drone model
    buildDroneModel();

    // Grid helper (subtle)
    const gridHelper = new THREE.GridHelper(14, 14, 0x1a2a4a, 0x1a2a4a);
    gridHelper.position.y = -2.5;
    scene.add(gridHelper);

    // Handle resize
    window.addEventListener('resize', onWindowResize);

    // Start render loop
    animate();
  }

  function buildDroneModel() {
    droneGroup = new THREE.Group();
    propellers = [];

    // Materials
    const bodyMat = new THREE.MeshPhongMaterial({
      color: 0x1a2840,
      emissive: 0x001122,
      specular: 0x00d4ff,
      shininess: 80,
    });

    const armMat = new THREE.MeshPhongMaterial({
      color: 0x223355,
      emissive: 0x001122,
      specular: 0x334466,
      shininess: 40,
    });

    const motorMat = new THREE.MeshPhongMaterial({
      color: 0x111122,
      emissive: 0x000011,
      specular: 0x00d4ff,
      shininess: 120,
    });

    const propMat = new THREE.MeshPhongMaterial({
      color: 0x00d4ff,
      emissive: 0x003344,
      transparent: true,
      opacity: 0.55,
      side: THREE.DoubleSide,
    });

    const accentMat = new THREE.MeshPhongMaterial({
      color: 0x00d4ff,
      emissive: 0x004466,
      specular: 0x00ffff,
      shininess: 200,
    });

    // --- Central body ---
    // Main box body
    const bodyGeo = new THREE.BoxGeometry(1.1, 0.28, 1.1);
    const body = new THREE.Mesh(bodyGeo, bodyMat);
    body.castShadow = true;
    droneGroup.add(body);

    // Top plate (thinner, slight overhang)
    const topPlateGeo = new THREE.BoxGeometry(1.2, 0.06, 1.2);
    const topPlate = new THREE.Mesh(topPlateGeo, armMat);
    topPlate.position.y = 0.17;
    droneGroup.add(topPlate);

    // Bottom plate
    const botPlateGeo = new THREE.BoxGeometry(1.2, 0.06, 1.2);
    const botPlate = new THREE.Mesh(botPlateGeo, armMat);
    botPlate.position.y = -0.17;
    droneGroup.add(botPlate);

    // Center hub accent ring
    const torusGeo = new THREE.TorusGeometry(0.22, 0.04, 8, 24);
    const torus = new THREE.Mesh(torusGeo, accentMat);
    torus.rotation.x = Math.PI / 2;
    torus.position.y = 0.18;
    droneGroup.add(torus);

    // FC indicator light (small cube on top)
    const fcLightGeo = new THREE.BoxGeometry(0.12, 0.06, 0.12);
    const fcLight = new THREE.Mesh(fcLightGeo, accentMat);
    fcLight.position.y = 0.23;
    droneGroup.add(fcLight);

    // --- Arms (4 diagonal) ---
    // Arm positions: NE, NW, SE, SW
    const armLength = 1.6;
    const armAngle = Math.PI / 4; // 45°
    const armPositions = [
      { x: 1, z: -1, rotY: armAngle },
      { x: -1, z: -1, rotY: -armAngle },
      { x: 1, z: 1, rotY: -armAngle },
      { x: -1, z: 1, rotY: armAngle },
    ];

    armPositions.forEach((pos, idx) => {
      // Arm tube
      const armGeo = new THREE.CylinderGeometry(0.055, 0.07, armLength, 8);
      const arm = new THREE.Mesh(armGeo, armMat);
      arm.rotation.z = Math.PI / 2;

      const armPivot = new THREE.Group();
      armPivot.rotation.y = pos.rotY;
      armPivot.add(arm);
      arm.position.x = armLength / 2;
      droneGroup.add(armPivot);

      // Motor mount at arm end
      const mountX = pos.x * (armLength * Math.cos(Math.PI / 4));
      const mountZ = pos.z * (armLength * Math.cos(Math.PI / 4));

      const motorMountGeo = new THREE.CylinderGeometry(0.14, 0.14, 0.12, 16);
      const motorMount = new THREE.Mesh(motorMountGeo, motorMat);
      motorMount.position.set(mountX, 0, mountZ);
      droneGroup.add(motorMount);

      // Motor bell
      const motorBellGeo = new THREE.CylinderGeometry(0.12, 0.1, 0.18, 16);
      const motorBell = new THREE.Mesh(motorBellGeo, motorMat);
      motorBell.position.set(mountX, 0.12, mountZ);
      droneGroup.add(motorBell);

      // Motor accent ring
      const motorRingGeo = new THREE.TorusGeometry(0.13, 0.015, 6, 20);
      const motorRing = new THREE.Mesh(motorRingGeo, accentMat);
      motorRing.position.set(mountX, 0.21, mountZ);
      motorRing.rotation.x = Math.PI / 2;
      droneGroup.add(motorRing);

      // Propeller disc (spinning)
      const propGroup = new THREE.Group();
      propGroup.position.set(mountX, 0.26, mountZ);

      // Two prop blades
      for (let b = 0; b < 2; b++) {
        const bladeGeo = new THREE.BoxGeometry(0.72, 0.01, 0.12);
        const blade = new THREE.Mesh(bladeGeo, propMat);
        blade.rotation.y = (b * Math.PI / 2);
        blade.rotation.z = 0.05; // slight pitch angle
        propGroup.add(blade);
      }

      // Prop hub
      const hubGeo = new THREE.CylinderGeometry(0.045, 0.045, 0.04, 12);
      const hub = new THREE.Mesh(hubGeo, motorMat);
      propGroup.add(hub);

      droneGroup.add(propGroup);
      propellers.push({ group: propGroup, dir: idx % 2 === 0 ? 1 : -1 });
    });

    // Front indicator (arrow pointing forward)
    const arrowGeo = new THREE.ConeGeometry(0.08, 0.2, 6);
    const arrow = new THREE.Mesh(arrowGeo, accentMat);
    arrow.rotation.x = Math.PI / 2;
    arrow.position.set(0, 0.02, -0.7);
    droneGroup.add(arrow);

    scene.add(droneGroup);
  }

  function animate() {
    animFrameId = requestAnimationFrame(animate);

    // Smooth interpolation for attitude
    const lerpFactor = 0.08;
    currentRoll += (targetRoll - currentRoll) * lerpFactor;
    currentPitch += (targetPitch - currentPitch) * lerpFactor;

    // Yaw: handle wrap-around properly
    let yawDiff = targetYaw - currentYaw;
    if (yawDiff > 180) yawDiff -= 360;
    if (yawDiff < -180) yawDiff += 360;
    currentYaw += yawDiff * lerpFactor;

    if (droneGroup) {
      droneGroup.rotation.x = THREE.MathUtils.degToRad(currentPitch);
      droneGroup.rotation.z = -THREE.MathUtils.degToRad(currentRoll);
      droneGroup.rotation.y = THREE.MathUtils.degToRad(currentYaw);
    }

    // Spin propellers
    const now = Date.now() * 0.001;
    propellers.forEach((p, i) => {
      p.group.rotation.y += p.dir * 0.18;
    });

    // Gentle floating animation
    if (droneGroup) {
      droneGroup.position.y = Math.sin(now * 0.7) * 0.08;
    }

    renderer.render(scene, camera);
  }

  function onWindowResize() {
    const container = document.getElementById('threejs-container');
    if (!container || !renderer || !camera) return;
    const w = container.clientWidth;
    const h = container.clientHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  }

  // ==========================================
  // RC CHANNEL BARS SETUP
  // ==========================================

  function initRCChannels() {
    const container = document.getElementById('rcChannels');
    if (!container) return;
    container.innerHTML = '';
    for (let i = 0; i < 16; i++) {
      const row = document.createElement('div');
      row.className = 'rc-channel';
      row.innerHTML = `
        <span class="rc-ch-label">${RC_CHANNEL_NAMES[i]}</span>
        <div class="rc-bar-track">
          <div class="rc-bar-fill" id="rc-fill-${i}" style="width:50%;"></div>
        </div>
        <span class="rc-ch-value" id="rc-val-${i}">1500</span>
      `;
      container.appendChild(row);
    }
  }

  // ==========================================
  // UPDATE FUNCTIONS (called each data tick)
  // ==========================================

  function updateTelemetry(data) {
    // Attitude
    targetRoll = data.roll;
    targetPitch = data.pitch;
    targetYaw = data.yaw;

    setInner('val-roll', data.roll.toFixed(1));
    setInner('val-pitch', data.pitch.toFixed(1));
    setInner('val-yaw', data.yaw.toFixed(1));
    setInner('val-altitude', data.altitude.toFixed(1));
    setInner('val-battery', data.battery.toFixed(2));
    setInner('val-gps', `${data.lat.toFixed(5)}, ${data.lon.toFixed(5)}`);
    setInner('val-mode', data.flightMode);
    setInner('attitude-text',
      `Roll: ${data.roll.toFixed(1)}°  |  Pitch: ${data.pitch.toFixed(1)}°  |  Yaw: ${data.yaw.toFixed(1)}°`
    );

    // Arm status
    const armEl = document.getElementById('val-arm');
    if (armEl) {
      armEl.textContent = data.armed ? 'ARMED' : 'DISARMED';
      armEl.className = 'telem-value arm-status ' + (data.armed ? 'armed' : 'disarmed');
    }

    // Battery color warning
    const batEl = document.getElementById('val-battery');
    if (batEl) {
      if (data.battery < 14.0) batEl.style.color = '#ff4444';
      else if (data.battery < 15.0) batEl.style.color = '#ffaa00';
      else batEl.style.color = '';
    }
  }

  function updateRCChannels(channels) {
    for (let i = 0; i < 16; i++) {
      const val = channels[i] || 1500;
      // Map 1000–2000 → 0–100%
      const pct = ((val - 1000) / 1000) * 100;
      const fillEl = document.getElementById(`rc-fill-${i}`);
      const valEl = document.getElementById(`rc-val-${i}`);
      if (fillEl) fillEl.style.width = `${pct.toFixed(1)}%`;
      if (valEl) valEl.textContent = val;
    }
  }

  function setInner(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  // ==========================================
  // PUBLIC API
  // ==========================================

  return {
    init() {
      initThreeJS();
      initRCChannels();
    },

    update(data) {
      updateTelemetry(data);
      updateRCChannels(data.channels || []);
    },

    resize: onWindowResize,

    destroy() {
      if (animFrameId) cancelAnimationFrame(animFrameId);
      window.removeEventListener('resize', onWindowResize);
    }
  };
})();
