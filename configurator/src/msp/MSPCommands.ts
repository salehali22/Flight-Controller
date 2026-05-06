import { mspConnection } from './MSPConnection'
import { MSP_CODES, readInt16LE, readUint16LE, readUint32LE, encodeUint16LE } from './MSPProtocol'

// ─── Info ────────────────────────────────────────────────────────────────────

export async function getApiVersion() {
  const f = await mspConnection.request(MSP_CODES.API_VERSION)
  return {
    protocolVersion: f.payload[0],
    major: f.payload[1],
    minor: f.payload[2],
  }
}

export async function getFcVariant() {
  const f = await mspConnection.request(MSP_CODES.FC_VARIANT)
  return new TextDecoder().decode(f.payload)
}

export async function getFcVersion() {
  const f = await mspConnection.request(MSP_CODES.FC_VERSION)
  return `${f.payload[0]}.${f.payload[1]}.${f.payload[2]}`
}

export async function getBoardInfo() {
  const f = await mspConnection.request(MSP_CODES.BOARD_INFO)
  const nameLen = 4
  const boardId = new TextDecoder().decode(f.payload.slice(0, nameLen))
  const hardwareRevision = readUint16LE(f.payload, nameLen)
  return { boardId, hardwareRevision }
}

// ─── Telemetry ───────────────────────────────────────────────────────────────

export interface StatusData {
  cycleTime: number
  i2cErrors: number
  sensorStatus: number
  flightModeFlags: number
  profile: number
  cpuLoad: number
  armed: boolean
}

export async function getStatus(): Promise<StatusData> {
  const f = await mspConnection.request(MSP_CODES.STATUS)
  const flags = readUint32LE(f.payload, 6)
  return {
    cycleTime: readUint16LE(f.payload, 0),
    i2cErrors: readUint16LE(f.payload, 2),
    sensorStatus: readUint16LE(f.payload, 4),
    flightModeFlags: flags,
    profile: f.payload[10] ?? 0,
    cpuLoad: readUint16LE(f.payload, 11) ?? 0,
    armed: (flags & 1) !== 0,
  }
}

export interface AttitudeData {
  roll: number   // degrees
  pitch: number  // degrees
  yaw: number    // degrees
}

export async function getAttitude(): Promise<AttitudeData> {
  const f = await mspConnection.request(MSP_CODES.ATTITUDE)
  return {
    roll: readInt16LE(f.payload, 0) / 10,
    pitch: readInt16LE(f.payload, 2) / 10,
    yaw: readInt16LE(f.payload, 4),
  }
}

export interface ImuData {
  accX: number; accY: number; accZ: number
  gyroX: number; gyroY: number; gyroZ: number
  magX: number; magY: number; magZ: number
}

export async function getRawImu(): Promise<ImuData> {
  const f = await mspConnection.request(MSP_CODES.RAW_IMU)
  return {
    accX:  readInt16LE(f.payload, 0),
    accY:  readInt16LE(f.payload, 2),
    accZ:  readInt16LE(f.payload, 4),
    gyroX: readInt16LE(f.payload, 6),
    gyroY: readInt16LE(f.payload, 8),
    gyroZ: readInt16LE(f.payload, 10),
    magX:  readInt16LE(f.payload, 12),
    magY:  readInt16LE(f.payload, 14),
    magZ:  readInt16LE(f.payload, 16),
  }
}

export async function getMotors(): Promise<number[]> {
  const f = await mspConnection.request(MSP_CODES.MOTOR)
  const motors: number[] = []
  for (let i = 0; i < 8; i++) motors.push(readUint16LE(f.payload, i * 2))
  return motors
}

export async function getRcChannels(): Promise<number[]> {
  const f = await mspConnection.request(MSP_CODES.RC)
  const channels: number[] = []
  for (let i = 0; i < f.payload.length / 2; i++) {
    channels.push(readUint16LE(f.payload, i * 2))
  }
  return channels
}

// ─── PID ─────────────────────────────────────────────────────────────────────

export interface PIDValues {
  roll:  [number, number, number]
  pitch: [number, number, number]
  yaw:   [number, number, number]
}

export async function getPID(): Promise<PIDValues> {
  const f = await mspConnection.request(MSP_CODES.PID)
  return {
    roll:  [f.payload[0], f.payload[1], f.payload[2]],
    pitch: [f.payload[3], f.payload[4], f.payload[5]],
    yaw:   [f.payload[6], f.payload[7], f.payload[8]],
  }
}

export async function setPID(pid: PIDValues): Promise<void> {
  const data = new Uint8Array([
    ...pid.roll, ...pid.pitch, ...pid.yaw,
  ])
  await mspConnection.send(MSP_CODES.SET_PID, data)
  await mspConnection.send(MSP_CODES.EEPROM_WRITE)
}

// ─── Features ────────────────────────────────────────────────────────────────

export async function getFeatureConfig(): Promise<number> {
  const f = await mspConnection.request(MSP_CODES.FEATURE_CONFIG)
  return readUint32LE(f.payload, 0)
}

export async function setFeatureConfig(mask: number): Promise<void> {
  const data = new Uint8Array([
    mask & 0xff, (mask >> 8) & 0xff, (mask >> 16) & 0xff, (mask >> 24) & 0xff,
  ])
  await mspConnection.send(MSP_CODES.SET_FEATURE_CONFIG, data)
  await mspConnection.send(MSP_CODES.EEPROM_WRITE)
}

// ─── Motor config ────────────────────────────────────────────────────────────

export async function setMotors(values: number[]): Promise<void> {
  const data = new Uint8Array(8 * 2)
  values.forEach((v, i) => {
    const [lo, hi] = encodeUint16LE(v)
    data[i * 2] = lo
    data[i * 2 + 1] = hi
  })
  await mspConnection.send(MSP_CODES.SET_MOTOR, data)
}

// ─── Serial config ───────────────────────────────────────────────────────────

export interface SerialPortConfig {
  identifier: number
  functionMask: number
  mspBaudRate: number
  gpsBaudRate: number
  telemetryBaudRate: number
  blackboxBaudRate: number
}

export async function getSerialConfig(): Promise<SerialPortConfig[]> {
  const f = await mspConnection.request(MSP_CODES.SERIAL_CONFIG)
  const ports: SerialPortConfig[] = []
  const stride = 1 + 2 + 1 + 1 + 1 + 1
  for (let i = 0; i + stride <= f.payload.length; i += stride) {
    ports.push({
      identifier: f.payload[i],
      functionMask: readUint16LE(f.payload, i + 1),
      mspBaudRate: f.payload[i + 3],
      gpsBaudRate: f.payload[i + 4],
      telemetryBaudRate: f.payload[i + 5],
      blackboxBaudRate: f.payload[i + 6],
    })
  }
  return ports
}

// ─── Calibration ─────────────────────────────────────────────────────────────

export async function calibrateAccel(): Promise<void> {
  await mspConnection.send(MSP_CODES.ACC_CALIBRATION)
}

export async function calibrateMag(): Promise<void> {
  await mspConnection.send(MSP_CODES.MAG_CALIBRATION)
}

export async function reboot(): Promise<void> {
  await mspConnection.send(MSP_CODES.REBOOT)
}

export async function saveEEPROM(): Promise<void> {
  await mspConnection.send(MSP_CODES.EEPROM_WRITE)
}

export async function resetConfig(): Promise<void> {
  await mspConnection.send(MSP_CODES.RESET_CONF)
}
