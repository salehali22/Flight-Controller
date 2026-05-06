/**
 * One-off bake: exports a minimal QUADX craft to public/models/craft.glb
 * Run from repo root: node scripts/bake-craft.mjs
 *
 * GLTFExporter uses FileReader (browser API); minimal polyfill for Node.
 */
if (typeof globalThis.FileReader === 'undefined') {
  globalThis.FileReader = class FileReaderPolyfill {
    constructor() {
      this.result = null
      this.onloadend = null
    }
    readAsArrayBuffer(blob) {
      blob
        .arrayBuffer()
        .then((ab) => {
          this.result = ab
          if (this.onloadend) this.onloadend()
        })
        .catch((e) => {
          console.error(e)
        })
    }
    readAsDataURL(blob) {
      blob
        .arrayBuffer()
        .then((ab) => {
          const b64 = Buffer.from(ab).toString('base64')
          this.result = `data:application/octet-stream;base64,${b64}`
          if (this.onloadend) this.onloadend()
        })
        .catch((e) => {
          console.error(e)
        })
    }
  }
}

import * as THREE from 'three'
import { GLTFExporter } from 'three/examples/jsm/exporters/GLTFExporter.js'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const outPath = path.join(__dirname, '..', 'public', 'models', 'craft.glb')

const matBody = new THREE.MeshStandardMaterial({
  color: 0x1a221e,
  roughness: 0.55,
  metalness: 0.35,
})
const matArm = new THREE.MeshStandardMaterial({
  color: 0x121812,
  roughness: 0.5,
  metalness: 0.55,
})
const matMotor = new THREE.MeshStandardMaterial({
  color: 0x2a302c,
  roughness: 0.45,
  metalness: 0.65,
})
const matProp = new THREE.MeshStandardMaterial({
  color: 0x3a4540,
  roughness: 0.35,
  metalness: 0.15,
  transparent: true,
  opacity: 0.88,
  side: THREE.DoubleSide,
})

const craft = new THREE.Group()
craft.name = 'SAL_CRAFT'

const top = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.022, 0.4), matBody)
top.position.y = 0.045
top.name = 'BODY_TOP'
craft.add(top)

const bot = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.022, 0.4), matBody)
bot.position.y = -0.045
bot.name = 'BODY_BOT'
craft.add(bot)

const armLen = 1.12
const armHalf = armLen * 0.5
const motorR = 0.72

for (let i = 0; i < 4; i++) {
  const ang = (i / 4) * Math.PI * 2 + Math.PI / 4
  const sx = Math.sin(ang)
  const cz = Math.cos(ang)

  const arm = new THREE.Mesh(new THREE.BoxGeometry(0.052, 0.026, armLen), matArm)
  arm.position.set(sx * armHalf * 0.92, 0, cz * armHalf * 0.92)
  arm.rotation.y = -ang
  arm.name = `ARM_${i}`
  craft.add(arm)

  const motor = new THREE.Mesh(
    new THREE.CylinderGeometry(0.088, 0.092, 0.072, 22),
    matMotor
  )
  motor.position.set(sx * motorR, 0.02, cz * motorR)
  motor.name = `MOTOR_${i}`
  craft.add(motor)

  const prop = new THREE.Mesh(new THREE.CircleGeometry(0.11, 24), matProp)
  prop.rotation.x = -Math.PI / 2
  prop.position.set(sx * motorR, 0.11, cz * motorR)
  prop.name = `PROP_${i}`
  craft.add(prop)
}

const forward = new THREE.Mesh(
  new THREE.ConeGeometry(0.035, 0.09, 8),
  new THREE.MeshStandardMaterial({
    color: 0x2a8f62,
    emissive: 0x1a5c40,
    emissiveIntensity: 0.35,
    roughness: 0.4,
    metalness: 0.2,
  })
)
forward.rotation.x = -Math.PI / 2
forward.position.set(0, 0.05, 0.42)
forward.name = 'FORWARD'
craft.add(forward)

const exporter = new GLTFExporter()
const buffer = await exporter.parseAsync(craft, { binary: true })
fs.mkdirSync(path.dirname(outPath), { recursive: true })
fs.writeFileSync(outPath, Buffer.from(buffer))
console.log('Wrote', outPath, '(' + fs.statSync(outPath).size + ' bytes)')
