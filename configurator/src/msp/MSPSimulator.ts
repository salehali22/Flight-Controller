import { MSP_CODES, encodeFrame, readUint16LE, MSPParser } from './MSPProtocol'

// Fake FC state for simulate mode
const state = {
  roll: 0, pitch: 0, yaw: 0,
  rollV: 0.3, pitchV: 0.2, yawV: 0.1,
  motors: [1000, 1000, 1000, 1000],
  rc: [1500, 1500, 1000, 1500, 1000, 1000, 1000, 1000],
  pid: { roll: [45, 40, 20], pitch: [45, 40, 20], yaw: [70, 45, 0] },
  features: 0b10101010,
  armed: false,
}

let simTimer: ReturnType<typeof setInterval> | null = null

function startSimPhysics() {
  if (simTimer) return
  simTimer = setInterval(() => {
    state.roll += state.rollV + (Math.random() - 0.5) * 0.1
    state.pitch += state.pitchV + (Math.random() - 0.5) * 0.1
    state.yaw += state.yawV + (Math.random() - 0.5) * 0.05
    if (Math.abs(state.roll) > 45) state.rollV *= -1
    if (Math.abs(state.pitch) > 30) state.pitchV *= -1
    if (Math.abs(state.yaw) > 180) state.yawV *= -1
  }, 20)
}

function stopSimPhysics() {
  if (simTimer) { clearInterval(simTimer); simTimer = null }
}

export function buildSimResponse(code: number, payload: Uint8Array): Uint8Array | null {
  const enc = encodeFrame
  const u16 = (n: number) => [n & 0xff, (n >> 8) & 0xff]
  const i16 = (n: number) => {
    const v = Math.round(n) & 0xffff
    return [v & 0xff, (v >> 8) & 0xff]
  }
  const u32 = (n: number) => [n & 0xff, (n >> 8) & 0xff, (n >> 16) & 0xff, (n >> 24) & 0xff]

  switch (code) {
    case MSP_CODES.API_VERSION:
      return enc(code, new Uint8Array([0, 1, 44]))
    case MSP_CODES.FC_VARIANT:
      return enc(code, new TextEncoder().encode('CUST'))
    case MSP_CODES.FC_VERSION:
      return enc(code, new Uint8Array([4, 5, 0]))
    case MSP_CODES.BOARD_INFO:
      return enc(code, new Uint8Array([...new TextEncoder().encode('H743'), 0, 1]))
    case MSP_CODES.BUILD_INFO:
      return enc(code, new TextEncoder().encode('Apr 17 2026 12:00:00'))

    case MSP_CODES.STATUS: {
      const flags = state.armed ? 1 : 0
      const data = new Uint8Array([
        ...u16(2500),   // cycleTime
        ...u16(0),      // i2cErrors
        ...u16(0b111),  // sensorStatus (gyro, acc, baro)
        ...u32(flags),  // flightModeFlags
        0,              // profile
        ...u16(15),     // cpuLoad %
      ])
      return enc(code, data)
    }

    case MSP_CODES.ATTITUDE: {
      const r = Math.round(state.roll * 10) & 0xffff
      const p = Math.round(state.pitch * 10) & 0xffff
      const y = Math.round(state.yaw) & 0xffff
      return enc(code, new Uint8Array([r & 0xff, r >> 8, p & 0xff, p >> 8, y & 0xff, y >> 8]))
    }

    case MSP_CODES.RAW_IMU: {
      const data = new Uint8Array([
        ...i16(Math.random() * 200 - 100),
        ...i16(Math.random() * 200 - 100),
        ...i16(512 + Math.random() * 100 - 50),
        ...i16(Math.random() * 60 - 30),
        ...i16(Math.random() * 60 - 30),
        ...i16(Math.random() * 60 - 30),
        0, 0, 0, 0, 0, 0,
      ])
      return enc(code, data)
    }

    case MSP_CODES.MOTOR: {
      const data = new Uint8Array(16)
      state.motors.forEach((v, i) => { data[i * 2] = v & 0xff; data[i * 2 + 1] = v >> 8 })
      return enc(code, data)
    }

    case MSP_CODES.RC: {
      const data = new Uint8Array(16)
      state.rc.forEach((v, i) => { data[i * 2] = v & 0xff; data[i * 2 + 1] = v >> 8 })
      return enc(code, data)
    }

    case MSP_CODES.PID: {
      const { roll, pitch, yaw } = state.pid
      return enc(code, new Uint8Array([...roll, ...pitch, ...yaw]))
    }

    case MSP_CODES.FEATURE_CONFIG:
      return enc(code, new Uint8Array(u32(state.features)))

    case MSP_CODES.MOTOR_CONFIG:
      return enc(code, new Uint8Array([...u16(1070), ...u16(2000), ...u16(1000)]))

    case MSP_CODES.SET_PID:
      state.pid.roll = [payload[0], payload[1], payload[2]]
      state.pid.pitch = [payload[3], payload[4], payload[5]]
      state.pid.yaw = [payload[6], payload[7], payload[8]]
      return enc(code, new Uint8Array(0))

    case MSP_CODES.SET_MOTOR: {
      for (let i = 0; i < 4; i++) state.motors[i] = readUint16LE(payload, i * 2)
      return enc(code, new Uint8Array(0))
    }

    case MSP_CODES.SET_FEATURE_CONFIG:
      state.features = payload[0] | (payload[1] << 8) | (payload[2] << 16) | (payload[3] << 24)
      return enc(code, new Uint8Array(0))

    case MSP_CODES.EEPROM_WRITE:
    case MSP_CODES.ACC_CALIBRATION:
    case MSP_CODES.MAG_CALIBRATION:
    case MSP_CODES.RESET_CONF:
      return enc(code, new Uint8Array(0))

    case MSP_CODES.REBOOT:
      return enc(code, new Uint8Array(0))

    case MSP_CODES.SERIAL_CONFIG: {
      const ports: number[] = []
      for (let i = 0; i < 6; i++) ports.push(i, 0, 0, 3, 1, 1, 1)
      return enc(code, new Uint8Array(ports))
    }

    default:
      return enc(code, new Uint8Array(0))
  }
}

export class SimulatedMSPConnection {
  private parser: MSPParser
  private queue: Array<{ code: number; resolve: (f: any) => void; reject: (e: Error) => void }> = []
  cliMode = false
  onDisconnect?: () => void
  onCliData?: (text: string) => void

  constructor() {
    this.parser = new MSPParser()
    this.parser.onFrame = (frame: any) => {
      const req = this.queue.shift()
      req?.resolve(frame)
    }
    startSimPhysics()
  }

  get connected() { return true }

  async request(code: number): Promise<any> {
    return new Promise((resolve, reject) => {
      const resp = buildSimResponse(code, new Uint8Array(0))
      if (!resp) { reject(new Error('No sim response')); return }
      this.queue.push({ code, resolve, reject })
      for (const byte of resp) this.parser.feed(byte)
    })
  }

  async send(code: number, payload = new Uint8Array(0)): Promise<any> {
    return new Promise((resolve, reject) => {
      const resp = buildSimResponse(code, payload)
      if (!resp) { reject(new Error('No sim response')); return }
      this.queue.push({ code, resolve, reject })
      for (const byte of resp) this.parser.feed(byte)
    })
  }

  async sendRaw(_data: Uint8Array) {}
  async enterCLI() { this.cliMode = true }
  async sendCLICommand(cmd: string) {
    setTimeout(() => {
      this.onCliData?.(`\r\n# ${cmd}\r\nsimulated response for: ${cmd}\r\n# `)
    }, 50)
  }
  async exitCLI() { this.cliMode = false }
  async disconnect() { stopSimPhysics() }
}
