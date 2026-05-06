// WebSerial API type stubs
interface SerialPortInfo {
  usbVendorId?: number
  usbProductId?: number
}

interface SerialOptions {
  baudRate: number
  dataBits?: number
  stopBits?: number
  parity?: string
  bufferSize?: number
  flowControl?: string
}

interface SerialPort extends EventTarget {
  readable: ReadableStream<Uint8Array> | null
  writable: WritableStream<Uint8Array> | null
  open(options: SerialOptions): Promise<void>
  close(): Promise<void>
  getInfo(): SerialPortInfo
}

interface Serial extends EventTarget {
  getPorts(): Promise<SerialPort[]>
  requestPort(options?: { filters?: { usbVendorId?: number; usbProductId?: number }[] }): Promise<SerialPort>
}

interface Navigator {
  serial: Serial
}

// WebUSB API type stubs
interface USBConfiguration {
  configurationValue: number
}

interface USBDevice {
  vendorId: number
  productId: number
  manufacturerName?: string
  productName?: string
  configuration: USBConfiguration | null
  open(): Promise<void>
  close(): Promise<void>
  selectConfiguration(configurationValue: number): Promise<void>
  claimInterface(interfaceNumber: number): Promise<void>
  releaseInterface(interfaceNumber: number): Promise<void>
  controlTransferIn(setup: object, length: number): Promise<USBInTransferResult>
  controlTransferOut(setup: object, data?: BufferSource): Promise<USBOutTransferResult>
}

interface USBInTransferResult {
  data?: DataView
  status: string
}

interface USBOutTransferResult {
  bytesWritten: number
  status: string
}

interface USB {
  getDevices(): Promise<USBDevice[]>
  requestDevice(options: { filters: object[] }): Promise<USBDevice>
}

interface Navigator {
  usb: USB
}
