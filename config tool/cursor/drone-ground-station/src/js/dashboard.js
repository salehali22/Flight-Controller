/**
 * 3D attitude view - loads real GLTF/GLB models for fixed-wing, procedural for multirotors.
 */
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const MODEL_URLS = {
  fixedwing: 'https://raw.githubusercontent.com/Flightradar24/fr24-3d-models/master/models/a320.glb',
  fixedwing_alt: 'https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Models/master/2.0/CesiumMilkTruck/glTF-Binary/CesiumMilkTruck.glb'
};

const CARBON = 0x4a5568;
const BODY_DARK = 0x5a6578;
const BODY_LIGHT = 0x6b7280;
const MOTOR_SILVER = 0x9ca3af;
const PROP_BLACK = 0x374151;
const BG_COLOR = 0x0f1419;
const GRID_COLOR = 0x2d3139;

let scene, camera, renderer, controls, grid;
let vehicleGroup, propellers = [];
let currentVehicle = 'quadcopter';
let targetEuler = new THREE.Euler(0, 0, 0, 'YXZ');
let displayEuler = new THREE.Euler(0, 0, 0, 'YXZ');
let throttleNorm = 0;
let gltfLoader;

const LERP = 0.08;

function mat(color, rough = 0.5, metal = 0.5) {
  return new THREE.MeshStandardMaterial({ color, roughness: rough, metalness: metal });
}

function createPropeller() {
  const group = new THREE.Group();
  const hub = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 0.06, 8), mat(PROP_BLACK, 0.9, 0.1));
  hub.rotation.x = Math.PI / 2;
  group.add(hub);
  const blade = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.03, 0.12), mat(PROP_BLACK, 0.8, 0.15));
  blade.rotation.x = Math.PI / 2;
  group.add(blade);
  propellers.push(blade);
  return group;
}

function createBrushlessMotor() {
  const group = new THREE.Group();
  const base = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.24, 0.15, 16), mat(MOTOR_SILVER, 0.4, 0.7));
  base.rotation.x = Math.PI / 2;
  group.add(base);
  const bell = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.22, 0.12, 16), mat(MOTOR_SILVER, 0.35, 0.75));
  bell.rotation.x = Math.PI / 2;
  bell.position.z = 0.08;
  group.add(bell);
  const prop = createPropeller();
  prop.position.z = 0.2;
  group.add(prop);
  return group;
}

function createQuadcopter() {
  const group = new THREE.Group();
  const scale = 1.2;
  const body = new THREE.Mesh(new THREE.BoxGeometry(1.8 * scale, 0.5 * scale, 1.8 * scale), mat(BODY_DARK, 0.6, 0.3));
  group.add(body);
  const cameraPod = new THREE.Mesh(new THREE.SphereGeometry(0.35 * scale, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2), mat(BODY_LIGHT, 0.5, 0.4));
  cameraPod.position.y = -0.4 * scale;
  cameraPod.rotation.x = Math.PI / 2;
  group.add(cameraPod);
  const armLen = 3.5 * scale;
  const armGeo = new THREE.BoxGeometry(0.12 * scale, 0.08 * scale, armLen);
  [45, 135, 225, 315].forEach((deg, i) => {
    const a = (deg * Math.PI) / 180;
    const arm = new THREE.Mesh(armGeo, mat(CARBON, 0.5, 0.6));
    arm.position.set(Math.cos(a) * armLen / 2, 0, Math.sin(a) * armLen / 2);
    arm.rotation.y = -a;
    group.add(arm);
    const motor = createBrushlessMotor();
    motor.position.set(Math.cos(a) * armLen, 0, Math.sin(a) * armLen);
    motor.rotation.y = a;
    motor.userData.dir = i % 2 === 0 ? 1 : -1;
    const blade = motor.children[2]?.children?.[1];
    if (blade) blade.userData.dir = motor.userData.dir;
    group.add(motor);
  });
  const antenna = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.06, 0.25, 8), mat(0x60a5fa, 0.6, 0.4));
  antenna.position.y = 0.35;
  group.add(antenna);
  return group;
}

function createTricopter() {
  const group = new THREE.Group();
  const scale = 1.1;
  const body = new THREE.Mesh(new THREE.BoxGeometry(1.6 * scale, 0.45 * scale, 1.6 * scale), mat(BODY_DARK, 0.6, 0.3));
  group.add(body);
  const armLen = 3.2 * scale;
  const armGeo = new THREE.BoxGeometry(0.14 * scale, 0.07 * scale, armLen);
  [0, 2 * Math.PI / 3, 4 * Math.PI / 3].forEach((a, i) => {
    const arm = new THREE.Mesh(armGeo, mat(CARBON, 0.5, 0.6));
    arm.position.set(Math.cos(a) * armLen / 2, 0, Math.sin(a) * armLen / 2);
    arm.rotation.y = -a;
    group.add(arm);
    const motor = createBrushlessMotor();
    motor.position.set(Math.cos(a) * armLen, 0, Math.sin(a) * armLen);
    motor.rotation.y = a;
    motor.userData.dir = i === 1 ? -1 : 1;
    const blade = motor.children[2]?.children?.[1];
    if (blade) blade.userData.dir = motor.userData.dir;
    group.add(motor);
  });
  return group;
}

function createHexacopter() {
  const group = new THREE.Group();
  const scale = 1;
  const body = new THREE.Mesh(new THREE.BoxGeometry(2 * scale, 0.5 * scale, 2 * scale), mat(BODY_DARK, 0.6, 0.3));
  group.add(body);
  const armLen = 2.8 * scale;
  const armGeo = new THREE.BoxGeometry(0.1 * scale, 0.06 * scale, armLen);
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * Math.PI * 2;
    const arm = new THREE.Mesh(armGeo, mat(CARBON, 0.5, 0.6));
    arm.position.set(Math.cos(a) * armLen / 2, 0, Math.sin(a) * armLen / 2);
    arm.rotation.y = -a;
    group.add(arm);
    const motor = createBrushlessMotor();
    motor.position.set(Math.cos(a) * armLen, 0, Math.sin(a) * armLen);
    motor.rotation.y = a;
    motor.userData.dir = i % 2 === 0 ? 1 : -1;
    const blade = motor.children[2]?.children?.[1];
    if (blade) blade.userData.dir = motor.userData.dir;
    group.add(motor);
  }
  return group;
}

function loadGLTFModel(url, scale = 1, onLoad, onError) {
  if (!gltfLoader) gltfLoader = new GLTFLoader();
  gltfLoader.load(
    url,
    (gltf) => {
      const model = gltf.scene;
      model.scale.setScalar(scale);
      model.rotation.x = Math.PI / 2;
      onLoad(model);
    },
    undefined,
    (err) => {
      console.error('GLTF load failed:', url, err);
      if (onError) onError(err);
    }
  );
}

function createVehicle(type) {
  if (vehicleGroup) {
    scene.remove(vehicleGroup);
    vehicleGroup = null;
  }
  propellers = [];
  currentVehicle = type;

  if (type === 'fixedwing') {
    const placeholder = new THREE.Mesh(
      new THREE.BoxGeometry(2, 0.5, 4),
      mat(0x4a5568, 0.6, 0.4)
    );
    vehicleGroup = new THREE.Group();
    vehicleGroup.userData.loading = true;
    vehicleGroup.add(placeholder);
    scene.add(vehicleGroup);

    loadGLTFModel(
      MODEL_URLS.fixedwing,
      0.025,
      (model) => {
        if (!vehicleGroup) return;
        vehicleGroup.userData.loading = false;
        vehicleGroup.remove(placeholder);
        vehicleGroup.add(model);
      },
      () => {
        if (!vehicleGroup) return;
        vehicleGroup.remove(placeholder);
        vehicleGroup.add(createProceduralFixedWing());
        vehicleGroup.userData.loading = false;
      }
    );
    return vehicleGroup;
  }

  if (type === 'quadcopter') vehicleGroup = createQuadcopter();
  else if (type === 'tricopter') vehicleGroup = createTricopter();
  else if (type === 'hexacopter') vehicleGroup = createHexacopter();
  scene.add(vehicleGroup);
  return vehicleGroup;
}

function createProceduralFixedWing() {
  const group = new THREE.Group();
  const s = 0.8;
  const fuse = new THREE.Mesh(new THREE.CylinderGeometry(0.2 * s, 0.35 * s, 6 * s, 12), mat(BODY_LIGHT, 0.5, 0.4));
  fuse.rotation.z = Math.PI / 2;
  group.add(fuse);
  const nose = new THREE.Mesh(new THREE.ConeGeometry(0.35 * s, 0.8 * s, 12), mat(BODY_DARK, 0.5, 0.45));
  nose.rotation.z = -Math.PI / 2;
  nose.position.set(3.5 * s, 0, 0);
  group.add(nose);
  const wing = new THREE.Mesh(new THREE.BoxGeometry(5 * s, 0.25 * s, 1.5 * s), mat(0x64748b, 0.55, 0.4));
  group.add(wing);
  const hStab = new THREE.Mesh(new THREE.BoxGeometry(1.8 * s, 0.12 * s, 0.8 * s), mat(0x64748b, 0.55, 0.4));
  hStab.position.set(-2.8 * s, 0, 0);
  group.add(hStab);
  const vStab = new THREE.Mesh(new THREE.BoxGeometry(0.1 * s, 0.9 * s, 0.7 * s), mat(0x64748b, 0.55, 0.4));
  vStab.position.set(-3 * s, 0.45 * s, 0);
  group.add(vStab);
  const motor = createBrushlessMotor();
  motor.scale.set(0.5, 0.5, 0.5);
  motor.position.set(3.8 * s, 0, 0);
  motor.rotation.y = Math.PI / 2;
  motor.userData.dir = 1;
  const blade = motor.children[2]?.children?.[1];
  if (blade) blade.userData.dir = 1;
  group.add(motor);
  return group;
}

export function initDashboard(containerEl) {
  if (!containerEl) return;
  scene = new THREE.Scene();
  scene.background = new THREE.Color(BG_COLOR);
  scene.add(new THREE.AmbientLight(0xffffff, 0.8));
  const d1 = new THREE.DirectionalLight(0xffffff, 1.2);
  d1.position.set(30, 70, 40);
  scene.add(d1);
  const d2 = new THREE.DirectionalLight(0xaaccff, 0.5);
  d2.position.set(-30, 30, -20);
  scene.add(d2);
  const d3 = new THREE.DirectionalLight(0x88aadd, 0.4);
  d3.position.set(0, 30, -60);
  scene.add(d3);
  grid = new THREE.GridHelper(80, 16, GRID_COLOR, GRID_COLOR);
  scene.add(grid);
  camera = new THREE.PerspectiveCamera(50, 1, 0.1, 2000);
  camera.position.set(0, 35, 70);
  camera.lookAt(0, 0, 0);
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.domElement.style.cssText = 'display:block;width:100%;height:100%;pointer-events:auto';
  containerEl.appendChild(renderer.domElement);
  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.05;
  createVehicle('quadcopter');
  window.addEventListener('resize', onResize);
  new ResizeObserver(onResize).observe(containerEl);
  requestAnimationFrame(() => onResize());
  setTimeout(onResize, 100);
  animate();
}

function onResize() {
  const container = document.getElementById('three-container');
  if (!container || !renderer || !camera) return;
  const w = container.clientWidth;
  const h = container.clientHeight;
  renderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}

function animate() {
  requestAnimationFrame(animate);
  displayEuler.x = THREE.MathUtils.lerp(displayEuler.x, targetEuler.x, LERP);
  displayEuler.y = THREE.MathUtils.lerp(displayEuler.y, targetEuler.y, LERP);
  displayEuler.z = THREE.MathUtils.lerp(displayEuler.z, targetEuler.z, LERP);
  if (vehicleGroup) {
    vehicleGroup.rotation.order = 'YXZ';
    vehicleGroup.rotation.x = displayEuler.x;
    vehicleGroup.rotation.y = displayEuler.y;
    vehicleGroup.rotation.z = displayEuler.z;
  }
  const spinSpeed = throttleNorm * 0.35;
  propellers.forEach((prop) => {
    const dir = prop.userData?.dir ?? 1;
    if (prop.rotation) prop.rotation.z += spinSpeed * dir;
  });
  if (controls) controls.update();
  if (renderer && scene && camera) renderer.render(scene, camera);
}

export function setVehicleType(type) {
  createVehicle(type);
}

export function getVehicleSelectElement() {
  return document.getElementById('vehicle-type');
}

export function updateAttitude(rollDeg, pitchDeg, yawDeg, throttleNormValue) {
  targetEuler.x = (pitchDeg * Math.PI) / 180;
  targetEuler.y = (yawDeg * Math.PI) / 180;
  targetEuler.z = (rollDeg * Math.PI) / 180;
  throttleNorm = Math.max(0, Math.min(1, (throttleNormValue - 1000) / 1000));
}

export function updateStatusBar(roll, pitch, yaw) {
  const r = document.getElementById('status-roll');
  const p = document.getElementById('status-pitch');
  const ya = document.getElementById('status-yaw');
  if (r) r.textContent = roll.toFixed(1) + '°';
  if (p) p.textContent = pitch.toFixed(1) + '°';
  if (ya) ya.textContent = yaw.toFixed(1) + '°';
}
