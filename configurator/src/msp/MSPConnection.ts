import { MSPParser, MSPFrame, encodeFrame } from './MSPProtocol'

interface PendingRequest {
  code: number
  resolve: (frame: MSPFrame) => void
  reject: (err: Error) => void
  timer: ReturnType<typeof setTimeout>
}

export class MSPConnection {
  private port: SerialPort | null = null
  private reader: ReadableStreamDefaultReader<Uint8Array> | null = null
  private writer: WritableStreamDefaultWriter<Uint8Array> | null = null
  private parser = new MSPParser()
  private queue: PendingRequest[] = []
  private busy = false
  private running = false
  cliMode = false

  onDisconnect?: () => void
  onCliData?: (text: string) => void

  constructor() {
    this.parser.onFrame = (frame) => this._handleFrame(frame)
  }

  async connect(port: SerialPort, baudRate = 115200): Promise<void> {
    this.port = port
    await port.open({ baudRate })
    this.writer = port.writable!.getWriter()
    this.reader = port.readable!.getReader()
    this.running = true
    this._readLoop()
  }

  async disconnect(): Promise<void> {
    this.running = false
    this.cliMode = false
    this.queue.forEach((r) => r.reject(new Error('Disconnected')))
    this.queue = []
    this.busy = false
    try { this.reader?.cancel() } catch {}
    try { this.writer?.close() } catch {}
    try { await this.port?.close() } catch {}
    this.reader = null
    this.writer = null
    this.port = null
  }

  get connected(): boolean {
    return this.port !== null && this.running
  }

  private async _readLoop() {
    const decoder = new TextDecoder()
    try {
      while (this.running && this.reader) {
        const { value, done } = await this.reader.read()
        if (done) break
        if (!value) continue

        if (this.cliMode) {
          this.onCliData?.(decoder.decode(value))
        } else {
          for (const byte of value) {
            this.parser.feed(byte)
          }
        }
      }
    } catch {
      // port disconnected
    } finally {
      if (this.running) {
        this.running = false
        this.onDisconnect?.()
      }
    }
  }

  private _handleFrame(frame: MSPFrame) {
    const req = this.queue[0]
    if (req && req.code === frame.code) {
      this.queue.shift()
      clearTimeout(req.timer)
      this.busy = false
      req.resolve(frame)
      this._processQueue()
    }
  }

  private _processQueue() {
    if (this.busy || this.queue.length === 0 || !this.connected) return
    this.busy = true
    const req = this.queue[0]
    const frame = encodeFrame(req.code)
    this.writer?.write(frame).catch(() => {})
  }

  request(code: number, timeoutMs = 1000): Promise<MSPFrame> {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        const idx = this.queue.findIndex((r) => r.code === code)
        if (idx !== -1) this.queue.splice(idx, 1)
        this.busy = false
        reject(new Error(`MSP timeout: ${code}`))
        this._processQueue()
      }, timeoutMs)

      this.queue.push({ code, resolve, reject, timer })
      if (!this.busy) this._processQueue()
    })
  }

  async send(code: number, payload?: Uint8Array): Promise<MSPFrame> {
    if (!this.connected) throw new Error('Not connected')
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        const idx = this.queue.findIndex((r) => r.code === code)
        if (idx !== -1) this.queue.splice(idx, 1)
        this.busy = false
        reject(new Error(`MSP timeout: ${code}`))
        this._processQueue()
      }, 1500)

      const entry: PendingRequest = { code, resolve, reject, timer }
      this.queue.push(entry)

      if (!this.busy) {
        this.busy = true
        const frame = encodeFrame(code, payload)
        this.writer?.write(frame).catch(() => {})
      }
    })
  }

  async sendRaw(data: Uint8Array): Promise<void> {
    await this.writer?.write(data)
  }

  async enterCLI(): Promise<void> {
    this.cliMode = true
    await this.sendRaw(new Uint8Array([0x23])) // '#'
  }

  async sendCLICommand(cmd: string): Promise<void> {
    const encoder = new TextEncoder()
    await this.sendRaw(encoder.encode(cmd + '\n'))
  }

  async exitCLI(): Promise<void> {
    await this.sendCLICommand('exit')
    this.cliMode = false
  }
}

export const mspConnection = new MSPConnection()
