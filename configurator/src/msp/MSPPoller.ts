import { MSP_CODES, readInt16LE, readUint16LE, readUint32LE } from './MSPProtocol'
import { useTelemetryStore } from '../store/telemetryStore'
import { getActiveConnection } from '../store/connectionStore'

type PollTask = { fn: () => Promise<void>; intervalMs: number; last: number }

async function req(code: number) {
  return getActiveConnection().request(code)
}

class MSPPoller {
  private tasks: PollTask[] = []
  private rafId: number | null = null
  private running = false

  start() {
    if (this.running) return
    this.running = true
    this.tasks = [
      { fn: this._pollAttitude, intervalMs: 50,  last: 0 },
      { fn: this._pollStatus,   intervalMs: 500, last: 0 },
      { fn: this._pollImu,      intervalMs: 50,  last: 0 },
      { fn: this._pollMotors,   intervalMs: 100, last: 0 },
      { fn: this._pollRc,       intervalMs: 100, last: 0 },
    ]
    this._loop()
  }

  stop() {
    this.running = false
    if (this.rafId !== null) { cancelAnimationFrame(this.rafId); this.rafId = null }
  }

  private _loop = () => {
    if (!this.running) return
    const now = performance.now()
    for (const task of this.tasks) {
      if (now - task.last >= task.intervalMs) {
        task.last = now
        task.fn().catch(() => {})
      }
    }
    this.rafId = requestAnimationFrame(this._loop)
  }

  private _pollAttitude = async () => {
    const f = await req(MSP_CODES.ATTITUDE)
    useTelemetryStore.getState().setAttitude({
      roll:  readInt16LE(f.payload, 0) / 10,
      pitch: readInt16LE(f.payload, 2) / 10,
      yaw:   readInt16LE(f.payload, 4),
    })
  }

  private _pollStatus = async () => {
    const f = await req(MSP_CODES.STATUS)
    const flags = readUint32LE(f.payload, 6)
    useTelemetryStore.getState().setStatus({
      cycleTime: readUint16LE(f.payload, 0),
      i2cErrors: readUint16LE(f.payload, 2),
      sensorStatus: readUint16LE(f.payload, 4),
      flightModeFlags: flags,
      profile: f.payload[10] ?? 0,
      cpuLoad: readUint16LE(f.payload, 11) ?? 0,
      armed: (flags & 1) !== 0,
    })
  }

  private _pollImu = async () => {
    const f = await req(MSP_CODES.RAW_IMU)
    useTelemetryStore.getState().setImu({
      accX:  readInt16LE(f.payload, 0),
      accY:  readInt16LE(f.payload, 2),
      accZ:  readInt16LE(f.payload, 4),
      gyroX: readInt16LE(f.payload, 6),
      gyroY: readInt16LE(f.payload, 8),
      gyroZ: readInt16LE(f.payload, 10),
      magX:  readInt16LE(f.payload, 12),
      magY:  readInt16LE(f.payload, 14),
      magZ:  readInt16LE(f.payload, 16),
    })
  }

  private _pollMotors = async () => {
    const f = await req(MSP_CODES.MOTOR)
    const motors: number[] = []
    for (let i = 0; i < 8; i++) motors.push(readUint16LE(f.payload, i * 2))
    useTelemetryStore.getState().setMotors(motors)
  }

  private _pollRc = async () => {
    const f = await req(MSP_CODES.RC)
    const rc: number[] = []
    for (let i = 0; i < f.payload.length / 2; i++) rc.push(readUint16LE(f.payload, i * 2))
    useTelemetryStore.getState().setRcChannels(rc)
  }
}

export const mspPoller = new MSPPoller()
