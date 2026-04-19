import { useRef, useEffect } from 'react'
import * as THREE from 'three'
import { useTelemetryStore } from '../store/telemetryStore'

const DEG = Math.PI / 180

/** Betaflight-style preview: light floor, neutral sky */
const VIEW_BG = 0xd8d8d8
const FOG_COLOR = 0xe2e2e2

function disposeCraft(root: THREE.Object3D) {
  root.traverse((o) => {
    if (o instanceof THREE.Mesh) {
      o.geometry?.dispose()
      const mat = o.material
      if (Array.isArray(mat)) mat.forEach((m) => m.dispose())
      else mat?.dispose()
    }
    if (o instanceof THREE.Sprite) {
      const mat = o.material as THREE.SpriteMaterial
      mat.map?.dispose()
      mat.dispose()
    }
  })
}

function buildPropBlade(): THREE.Shape {
  const s = new THREE.Shape()
  s.moveTo(0.02, 0)
  s.bezierCurveTo(0.06, 0.06, 0.09, 0.14, 0.06, 0.22)
  s.lineTo(0.02, 0.24)
  s.lineTo(-0.02, 0.24)
  s.bezierCurveTo(-0.04, 0.16, -0.04, 0.06, -0.02, 0)
  s.closePath()
  return s
}

/**
 * Brushless outrunner–style motor: mounting base, stator can, gap, lathe bell, cooling slots, shaft.
 * Origin at bottom center (sits on arm); ~11 cm tall in scene units.
 */
function makeMotor(bellColor: number): THREE.Group {
  const g = new THREE.Group()
  const segs = 40

  const baseMat = new THREE.MeshStandardMaterial({ color: 0x141618, roughness: 0.55, metalness: 0.72 })
  const statorMat = new THREE.MeshStandardMaterial({ color: 0x4a4d52, roughness: 0.42, metalness: 0.78 })
  const gapMat = new THREE.MeshStandardMaterial({ color: 0x0c0e10, roughness: 0.85, metalness: 0.35 })
  const bellMat = new THREE.MeshStandardMaterial({ color: bellColor, roughness: 0.3, metalness: 0.74 })
  const slotMat = new THREE.MeshStandardMaterial({ color: 0x0a0a0c, roughness: 0.9, metalness: 0.25 })
  const shaftMat = new THREE.MeshStandardMaterial({ color: 0xd8d8dc, roughness: 0.22, metalness: 0.92 })

  // — Mounting plate (anodized black)
  const base = new THREE.Mesh(new THREE.CylinderGeometry(0.112, 0.114, 0.009, segs), baseMat)
  base.position.y = 0.0045
  g.add(base)

  // — M6 screw bosses around base (visual only)
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * Math.PI * 2 + 0.2
    const boss = new THREE.Mesh(new THREE.CylinderGeometry(0.006, 0.006, 0.0045, 6), gapMat)
    boss.position.set(Math.cos(a) * 0.096, 0.0105, Math.sin(a) * 0.096)
    g.add(boss)
  }

  // — Stator can (fixed aluminum)
  const statorH = 0.038
  const stator = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.092, statorH, segs), statorMat)
  stator.position.y = 0.009 + statorH / 2
  g.add(stator)

  const statorTop = 0.009 + statorH
  const gapY = statorTop + 0.002
  const gap = new THREE.Mesh(new THREE.TorusGeometry(0.091, 0.0022, 8, segs), gapMat)
  gap.rotation.x = Math.PI / 2
  gap.position.y = gapY
  g.add(gap)

  // — Bell: lathe profile (outrunner cup)
  const bellPts = [
    new THREE.Vector2(0.086, 0),
    new THREE.Vector2(0.093, 0.004),
    new THREE.Vector2(0.098, 0.014),
    new THREE.Vector2(0.0995, 0.026),
    new THREE.Vector2(0.099, 0.034),
    new THREE.Vector2(0.095, 0.039),
    new THREE.Vector2(0.087, 0.0415),
    new THREE.Vector2(0.076, 0.0425),
    new THREE.Vector2(0.064, 0.043),
  ]
  const bellY0 = gapY + 0.001
  const bell = new THREE.Mesh(new THREE.LatheGeometry(bellPts, segs), bellMat)
  bell.position.y = bellY0
  g.add(bell)

  const bellTop = bellY0 + 0.043
  const slotH = 0.028
  const slotR = 0.1005
  const slotMidY = bellY0 + 0.021
  for (let i = 0; i < 9; i++) {
    const a = (i / 9) * Math.PI * 2
    const slot = new THREE.Mesh(new THREE.BoxGeometry(0.0065, slotH, 0.012), slotMat)
    slot.position.set(Math.cos(a) * slotR, slotMidY, Math.sin(a) * slotR)
    slot.rotation.y = -a
    g.add(slot)
  }

  const lip = new THREE.Mesh(new THREE.TorusGeometry(0.068, 0.0032, 10, segs), statorMat)
  lip.rotation.x = Math.PI / 2
  lip.position.y = bellTop - 0.002
  g.add(lip)

  const shaftLen = 0.038
  const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.0036, 0.004, shaftLen, 12), shaftMat)
  shaft.position.y = bellTop + shaftLen / 2 - 0.004
  g.add(shaft)

  return g
}

function makeProp(color: number, blades = 2): THREE.Group {
  const hub = new THREE.Group()
  const shape = buildPropBlade()
  const geo = new THREE.ShapeGeometry(shape, 8)
  const mat = new THREE.MeshStandardMaterial({
    color,
    roughness: 0.5,
    metalness: 0.1,
    transparent: true,
    opacity: 0.82,
    side: THREE.DoubleSide,
  })
  for (let i = 0; i < blades; i++) {
    const blade = new THREE.Mesh(geo, mat)
    blade.rotation.y = (i / blades) * Math.PI * 2
    blade.rotation.x = DEG * 7
    hub.add(blade)
    const blade2 = new THREE.Mesh(geo, mat)
    blade2.rotation.y = (i / blades) * Math.PI * 2 + Math.PI
    blade2.rotation.x = DEG * 7
    blade2.scale.x = -1
    hub.add(blade2)
  }
  const disc = new THREE.Mesh(
    new THREE.CylinderGeometry(0.025, 0.025, 0.01, 12),
    new THREE.MeshStandardMaterial({ color: 0x333333, metalness: 0.8, roughness: 0.3 })
  )
  hub.add(disc)
  return hub
}

interface Motor {
  x: number
  z: number
  cw: boolean
  color: number
}

export const MIXER_MOTORS: Record<string, Motor[]> = {
  MONO: [{ x: 0, z: 0, cw: false, color: 0xff3333 }],
  BI: [
    { x: -0.8, z: 0, cw: true, color: 0xff3333 },
    { x: 0.8, z: 0, cw: false, color: 0x33cc66 },
  ],
  TRI: [
    { x: -0.75, z: 0.55, cw: true, color: 0xff3333 },
    { x: 0.75, z: 0.55, cw: false, color: 0x33cc66 },
    { x: 0, z: -0.85, cw: true, color: 0x3388ff },
  ],
  QUADX: [
    { x: 0.72, z: -0.72, cw: false, color: 0xff3333 },
    { x: 0.72, z: 0.72, cw: true, color: 0x33cc66 },
    { x: -0.72, z: -0.72, cw: true, color: 0x3388ff },
    { x: -0.72, z: 0.72, cw: false, color: 0xffcc00 },
  ],
  QUADP: [
    { x: 0, z: 0.85, cw: true, color: 0xff3333 },
    { x: 0.85, z: 0, cw: false, color: 0x33cc66 },
    { x: 0, z: -0.85, cw: false, color: 0x3388ff },
    { x: -0.85, z: 0, cw: true, color: 0xffcc00 },
  ],
  Y4: [
    { x: -0.72, z: 0.72, cw: true, color: 0xff3333 },
    { x: 0.72, z: 0.72, cw: false, color: 0x33cc66 },
    { x: -0.5, z: -0.85, cw: false, color: 0x3388ff },
    { x: 0.5, z: -0.85, cw: true, color: 0xffcc00 },
  ],
  Y6: [
    { x: -0.72, z: 0.72, cw: true, color: 0xff3333 },
    { x: 0.72, z: 0.72, cw: false, color: 0x33cc66 },
    { x: 0, z: -0.9, cw: true, color: 0x3388ff },
    { x: -0.72, z: 0.72, cw: false, color: 0xffcc00 },
    { x: 0.72, z: 0.72, cw: true, color: 0xff6600 },
    { x: 0, z: -0.9, cw: false, color: 0xaa00ff },
  ],
  HEX6: [
    { x: 0, z: 0.95, cw: false, color: 0xff3333 },
    { x: 0.82, z: 0.47, cw: true, color: 0x33cc66 },
    { x: 0.82, z: -0.47, cw: false, color: 0x3388ff },
    { x: 0, z: -0.95, cw: true, color: 0xffcc00 },
    { x: -0.82, z: -0.47, cw: false, color: 0xff6600 },
    { x: -0.82, z: 0.47, cw: true, color: 0xaa00ff },
  ],
  HEX6X: [
    { x: 0.47, z: 0.82, cw: false, color: 0xff3333 },
    { x: 0.95, z: 0, cw: true, color: 0x33cc66 },
    { x: 0.47, z: -0.82, cw: false, color: 0x3388ff },
    { x: -0.47, z: -0.82, cw: true, color: 0xffcc00 },
    { x: -0.95, z: 0, cw: false, color: 0xff6600 },
    { x: -0.47, z: 0.82, cw: true, color: 0xaa00ff },
  ],
  OCTOX: [
    { x: 0.38, z: 0.92, cw: false, color: 0xff3333 },
    { x: 0.92, z: 0.38, cw: true, color: 0x33cc66 },
    { x: 0.92, z: -0.38, cw: false, color: 0x3388ff },
    { x: 0.38, z: -0.92, cw: true, color: 0xffcc00 },
    { x: -0.38, z: -0.92, cw: false, color: 0xff6600 },
    { x: -0.92, z: -0.38, cw: true, color: 0xaa00ff },
    { x: -0.92, z: 0.38, cw: false, color: 0x00ccaa },
    { x: -0.38, z: 0.92, cw: true, color: 0xff88aa },
  ],
  OCTOFLATX: [
    { x: 0.7, z: 0.7, cw: false, color: 0xff3333 },
    { x: 1.0, z: 0, cw: true, color: 0x33cc66 },
    { x: 0.7, z: -0.7, cw: false, color: 0x3388ff },
    { x: 0, z: -1.0, cw: true, color: 0xffcc00 },
    { x: -0.7, z: -0.7, cw: false, color: 0xff6600 },
    { x: -1.0, z: 0, cw: true, color: 0xaa00ff },
    { x: -0.7, z: 0.7, cw: false, color: 0x00ccaa },
    { x: 0, z: 1.0, cw: true, color: 0xff88aa },
  ],
}

type CraftState = {
  quad: THREE.Group | null
  props: THREE.Group[]
}

function buildProceduralCraft(scene: THREE.Scene, s: CraftState, mixerType: string) {
  const quad = new THREE.Group()
  s.quad = quad
  s.props = []

  const motors = MIXER_MOTORS[mixerType] ?? MIXER_MOTORS.QUADX
  const armR = 1.2

  const bodyShape = new THREE.Shape()
  const bSides = 8,
    bR = 0.38
  for (let i = 0; i < bSides; i++) {
    const a = (i / bSides) * Math.PI * 2 - Math.PI / bSides
    if (i === 0) bodyShape.moveTo(bR * Math.cos(a), bR * Math.sin(a))
    else bodyShape.lineTo(bR * Math.cos(a), bR * Math.sin(a))
  }
  bodyShape.closePath()
  const bodyGeo = new THREE.ExtrudeGeometry(bodyShape, { depth: 0.04, bevelEnabled: false })
  const bodyMat = new THREE.MeshStandardMaterial({ color: 0x1a1a1a, roughness: 0.4, metalness: 0.6 })
  const topPlate = new THREE.Mesh(bodyGeo, bodyMat)
  topPlate.rotation.x = -Math.PI / 2
  topPlate.position.y = 0.04
  quad.add(topPlate)

  const botPlate = new THREE.Mesh(bodyGeo, bodyMat)
  botPlate.rotation.x = -Math.PI / 2
  botPlate.position.y = -0.12
  quad.add(botPlate)

  for (let i = 0; i < 4; i++) {
    const a = (i / 4) * Math.PI * 2 + Math.PI / 4
    const standoff = new THREE.Mesh(
      new THREE.CylinderGeometry(0.018, 0.018, 0.16, 6),
      new THREE.MeshStandardMaterial({ color: 0x444444, metalness: 0.9, roughness: 0.2 })
    )
    standoff.position.set(0.25 * Math.cos(a), -0.04, 0.25 * Math.sin(a))
    quad.add(standoff)
  }

  const stackMat = new THREE.MeshStandardMaterial({ color: 0x0a3a0a, roughness: 0.8, metalness: 0.1 })
  const fc = new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.025, 0.36), stackMat)
  fc.position.y = 0.085
  quad.add(fc)

  const ledMat = new THREE.MeshStandardMaterial({ color: 0x00ff44, emissive: 0x00ff44, emissiveIntensity: 2 })
  const led = new THREE.Mesh(new THREE.BoxGeometry(0.025, 0.01, 0.025), ledMat)
  led.position.set(0.12, 0.1, 0.12)
  quad.add(led)

  const camMat = new THREE.MeshStandardMaterial({ color: 0x222222, roughness: 0.5, metalness: 0.5 })
  const camMount = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.11, 0.06), camMat)
  camMount.position.set(0, 0.04, 0.28)
  quad.add(camMount)
  const lens = new THREE.Mesh(
    new THREE.CylinderGeometry(0.025, 0.025, 0.025, 12),
    new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 0.1, metalness: 0.3 })
  )
  lens.rotation.x = Math.PI / 2
  lens.position.set(0, 0.04, 0.32)
  quad.add(lens)

  const arrowMat = new THREE.MeshStandardMaterial({ color: 0x00c853, emissive: 0x00a040, emissiveIntensity: 0.5 })
  const arrow = new THREE.Mesh(new THREE.ConeGeometry(0.04, 0.1, 8), arrowMat)
  arrow.rotation.x = -Math.PI / 2
  arrow.position.set(0, 0.07, 0.45)
  quad.add(arrow)

  motors.forEach((m, idx) => {
    const angle = Math.atan2(m.x, m.z)
    const dist = Math.sqrt(m.x * m.x + m.z * m.z) * armR
    const armLen = dist + 0.05
    const armGeo = new THREE.BoxGeometry(0.055, 0.028, armLen)
    const armMat = new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 0.5, metalness: 0.6 })
    const arm = new THREE.Mesh(armGeo, armMat)
    arm.position.set(m.x * armR * 0.5, 0, m.z * armR * 0.5)
    arm.rotation.y = angle
    quad.add(arm)

    const motor = makeMotor(m.color)
    motor.position.set(m.x * armR, 0, m.z * armR)
    quad.add(motor)

    const prop = makeProp(m.color, 2)
    prop.position.set(m.x * armR, 0.15, m.z * armR)
    prop.userData.cwSpin = m.cw
    s.props.push(prop)
    quad.add(prop)

    const canvas = document.createElement('canvas')
    canvas.width = 64
    canvas.height = 32
    const ctx = canvas.getContext('2d')!
    ctx.fillStyle = '#' + m.color.toString(16).padStart(6, '0')
    ctx.font = 'bold 22px monospace'
    ctx.textAlign = 'center'
    ctx.fillText(`M${idx + 1}`, 32, 24)
    const tex = new THREE.CanvasTexture(canvas)
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true }))
    sprite.scale.set(0.35, 0.17, 1)
    sprite.position.set(m.x * armR, 0.38, m.z * armR)
    quad.add(sprite)
  })

  scene.add(quad)
}

interface Props {
  mixerType?: string
}

export function ThreeDModel({ mixerType = 'QUADX' }: Props) {
  const mountRef = useRef<HTMLDivElement>(null)
  const stateRef = useRef({
    animId: 0,
    camTheta: 0.7,
    camPhi: 0.55,
    camR: 5.5,
    mouse: { x: 0, y: 0 },
    dragging: false,
    props: [] as THREE.Group[],
    quad: null as THREE.Group | null,
    camera: null as THREE.PerspectiveCamera | null,
  })

  useEffect(() => {
    const el = mountRef.current
    if (!el) return
    const s = stateRef.current

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false })
    renderer.setSize(el.clientWidth, el.clientHeight)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setClearColor(VIEW_BG)
    renderer.shadowMap.enabled = true
    el.appendChild(renderer.domElement)

    const scene = new THREE.Scene()
    scene.fog = new THREE.FogExp2(FOG_COLOR, 0.018)

    const camera = new THREE.PerspectiveCamera(42, el.clientWidth / el.clientHeight, 0.1, 60)
    s.camera = camera

    scene.add(new THREE.AmbientLight(0xffffff, 1.35))

    const key = new THREE.DirectionalLight(0xffffff, 1.85)
    key.position.set(4, 8, 5)
    key.castShadow = true
    scene.add(key)

    const fill = new THREE.DirectionalLight(0xffffff, 0.65)
    fill.position.set(-5, 4, -4)
    scene.add(fill)

    const grid = new THREE.GridHelper(12, 24, 0xbbbbbb, 0xcccccc)
    grid.position.y = -1.4
    scene.add(grid)

    buildProceduralCraft(scene, s, mixerType)

    const updateCam = () => {
      const x = s.camR * Math.sin(s.camTheta) * Math.cos(s.camPhi)
      const y = s.camR * Math.sin(s.camPhi)
      const z = s.camR * Math.cos(s.camTheta) * Math.cos(s.camPhi)
      camera.position.set(x, y, z)
      camera.lookAt(0, 0.1, 0)
    }
    updateCam()

    const onDown = (e: MouseEvent) => {
      s.dragging = true
      s.mouse = { x: e.clientX, y: e.clientY }
    }
    const onUp = () => {
      s.dragging = false
    }
    const onMove = (e: MouseEvent) => {
      if (!s.dragging) return
      s.camTheta -= (e.clientX - s.mouse.x) * 0.006
      s.camPhi = Math.max(0.08, Math.min(1.3, s.camPhi + (e.clientY - s.mouse.y) * 0.006))
      s.mouse = { x: e.clientX, y: e.clientY }
      updateCam()
    }
    const onWheel = (e: WheelEvent) => {
      s.camR = Math.max(2.5, Math.min(10, s.camR + e.deltaY * 0.008))
      updateCam()
    }

    el.addEventListener('mousedown', onDown)
    window.addEventListener('mouseup', onUp)
    window.addEventListener('mousemove', onMove)
    el.addEventListener('wheel', onWheel, { passive: true })

    const animate = () => {
      s.animId = requestAnimationFrame(animate)
      const { attitude } = useTelemetryStore.getState()
      const root = s.quad
      if (root) {
        root.rotation.x = -attitude.pitch * DEG
        root.rotation.z = -attitude.roll * DEG
        root.rotation.y = attitude.yaw * DEG
      }
      s.props.forEach((p) => {
        const cw = p.userData.cwSpin as boolean
        p.rotation.y += cw ? 0.18 : -0.18
      })
      renderer.render(scene, camera)
    }
    animate()

    const ro = new ResizeObserver(() => {
      if (!el) return
      camera.aspect = el.clientWidth / el.clientHeight
      camera.updateProjectionMatrix()
      renderer.setSize(el.clientWidth, el.clientHeight)
    })
    ro.observe(el)

    return () => {
      cancelAnimationFrame(s.animId)
      ro.disconnect()
      el.removeEventListener('mousedown', onDown)
      window.removeEventListener('mouseup', onUp)
      window.removeEventListener('mousemove', onMove)
      el.removeEventListener('wheel', onWheel)
      if (s.quad) {
        scene.remove(s.quad)
        disposeCraft(s.quad)
        s.quad = null
      }
      s.props = []
      renderer.dispose()
      if (el.contains(renderer.domElement)) el.removeChild(renderer.domElement)
    }
  }, [mixerType])

  const resetView = () => {
    const s = stateRef.current
    s.camTheta = 0.7
    s.camPhi = 0.55
    s.camR = 5.5
    const x = s.camR * Math.sin(s.camTheta) * Math.cos(s.camPhi)
    const y = s.camR * Math.sin(s.camPhi)
    const z = s.camR * Math.cos(s.camTheta) * Math.cos(s.camPhi)
    s.camera?.position.set(x, y, z)
    s.camera?.lookAt(0, 0.1, 0)
  }

  const motors = MIXER_MOTORS[mixerType] ?? MIXER_MOTORS.QUADX

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        background: '#d8d8d8',
      }}
    >
      <div ref={mountRef} style={{ width: '100%', height: '100%', cursor: 'grab' }} />

      <div
        style={{
          position: 'absolute',
          top: 8,
          right: 8,
          background: 'rgba(255,255,255,0.92)',
          border: '1px solid #b0b0b0',
          padding: '6px 10px',
          display: 'flex',
          flexDirection: 'column',
          gap: 4,
          boxShadow: '0 1px 2px rgba(0,0,0,0.08)',
        }}
      >
        {motors.map((m, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, fontFamily: 'var(--font-mono)', color: '#333' }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#' + m.color.toString(16).padStart(6, '0') }} />
            <span style={{ color: '#444' }}>M{i + 1}</span>
            <span style={{ color: '#777', fontSize: 10 }}>{m.cw ? 'CW' : 'CCW'}</span>
          </div>
        ))}
      </div>

      <div style={{ position: 'absolute', bottom: 8, right: 8, display: 'flex', gap: 6 }}>
        <button onClick={resetView} className="btn" style={{ fontSize: 11, padding: '3px 8px' }}>
          Reset View
        </button>
      </div>

      <div
        style={{
          position: 'absolute',
          bottom: 8,
          left: 8,
          fontSize: 11,
          fontFamily: 'var(--font-mono)',
          color: '#0a6b2e',
          background: 'rgba(255,255,255,0.9)',
          padding: '3px 6px',
          border: '1px solid #aaa',
        }}
      >
        ▲ FORWARD
      </div>
    </div>
  )
}
