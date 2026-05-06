export const MSP_CODES = {
  API_VERSION: 1,
  FC_VARIANT: 2,
  FC_VERSION: 3,
  BOARD_INFO: 4,
  BUILD_INFO: 5,
  STATUS: 101,
  RAW_IMU: 102,
  MOTOR: 104,
  RC: 105,
  ATTITUDE: 108,
  ALTITUDE: 109,
  PID: 112,
  BOX: 113,
  MISC: 114,
  MOTOR_CONFIG: 131,
  SERIAL_CONFIG: 54,
  FEATURE_CONFIG: 36,
  SET_FEATURE_CONFIG: 37,
  SENSOR_CONFIG: 96,
  SET_SENSOR_CONFIG: 97,
  SENSOR_ALIGNMENT: 126,
  SET_SENSOR_ALIGNMENT: 220,
  ACC_CALIBRATION: 205,
  MAG_CALIBRATION: 206,
  SET_PID: 202,
  SET_MISC: 207,
  SET_MOTOR_CONFIG: 222,
  SET_SERIAL_CONFIG: 245,
  SET_MOTOR: 214,
  EEPROM_WRITE: 250,
  RESET_CONF: 208,
  REBOOT: 68,
} as const

export type MSPCode = (typeof MSP_CODES)[keyof typeof MSP_CODES]

export interface MSPFrame {
  code: number
  payload: Uint8Array
  error: boolean
}

export function encodeFrame(code: number, payload: Uint8Array = new Uint8Array(0)): Uint8Array {
  const len = payload.length
  const frame = new Uint8Array(6 + len)
  frame[0] = 0x24 // $
  frame[1] = 0x4d // M
  frame[2] = 0x3c // <
  frame[3] = len
  frame[4] = code
  let checksum = len ^ code
  for (let i = 0; i < len; i++) {
    frame[5 + i] = payload[i]
    checksum ^= payload[i]
  }
  frame[5 + len] = checksum
  return frame
}

export function encodeUint16LE(val: number): [number, number] {
  return [val & 0xff, (val >> 8) & 0xff]
}

export function encodeUint32LE(val: number): [number, number, number, number] {
  return [val & 0xff, (val >> 8) & 0xff, (val >> 16) & 0xff, (val >> 24) & 0xff]
}

export function readUint16LE(buf: Uint8Array, offset: number): number {
  return buf[offset] | (buf[offset + 1] << 8)
}

export function readInt16LE(buf: Uint8Array, offset: number): number {
  const val = readUint16LE(buf, offset)
  return val > 0x7fff ? val - 0x10000 : val
}

export function readUint32LE(buf: Uint8Array, offset: number): number {
  return buf[offset] | (buf[offset + 1] << 8) | (buf[offset + 2] << 16) | (buf[offset + 3] << 24)
}

export class MSPParser {
  private state: 'IDLE' | 'DOLLAR' | 'M' | 'DIRECTION' | 'LENGTH' | 'CODE' | 'PAYLOAD' | 'CHECKSUM' = 'IDLE'
  private direction = 0
  private length = 0
  private code = 0
  private payload: number[] = []
  private checksum = 0
  private error = false

  onFrame?: (frame: MSPFrame) => void

  feed(byte: number): void {
    switch (this.state) {
      case 'IDLE':
        if (byte === 0x24) this.state = 'DOLLAR'
        break
      case 'DOLLAR':
        this.state = byte === 0x4d ? 'M' : 'IDLE'
        break
      case 'M':
        if (byte === 0x3e || byte === 0x21) {
          this.direction = byte
          this.error = byte === 0x21
          this.state = 'DIRECTION'
        } else {
          this.state = 'IDLE'
        }
        break
      case 'DIRECTION':
        this.length = byte
        this.checksum = byte
        this.payload = []
        this.state = 'CODE'
        break
      case 'CODE':
        this.code = byte
        this.checksum ^= byte
        this.state = this.length > 0 ? 'PAYLOAD' : 'CHECKSUM'
        break
      case 'PAYLOAD':
        this.payload.push(byte)
        this.checksum ^= byte
        if (this.payload.length === this.length) this.state = 'CHECKSUM'
        break
      case 'CHECKSUM':
        if (byte === this.checksum) {
          this.onFrame?.({
            code: this.code,
            payload: new Uint8Array(this.payload),
            error: this.error,
          })
        }
        this.state = 'IDLE'
        break
    }
  }
}
