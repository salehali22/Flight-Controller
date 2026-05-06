import { create } from 'zustand'
import { mspConnection } from '../msp/MSPConnection'
import { SimulatedMSPConnection } from '../msp/MSPSimulator'
import { mspPoller } from '../msp/MSPPoller'
import { getApiVersion, getFcVariant, getFcVersion, getBoardInfo } from '../msp/MSPCommands'

export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error'

interface FCInfo {
  apiVersion: string
  fcVariant: string
  fcVersion: string
  boardId: string
  hardwareRevision: number
}

interface Toast {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  message: string
}

interface ConnectionStore {
  state: ConnectionState
  portName: string
  baudRate: number
  simulateMode: boolean
  simConnection: SimulatedMSPConnection | null
  fcInfo: FCInfo | null
  toasts: Toast[]
  availablePorts: SerialPortInfo[]

  setBaudRate: (b: number) => void
  setSimulateMode: (v: boolean) => void
  connect: (port?: SerialPort) => Promise<void>
  disconnect: () => Promise<void>
  refreshPorts: () => Promise<void>
  requestPort: () => Promise<SerialPort | null>
  addToast: (type: Toast['type'], message: string) => void
  removeToast: (id: string) => void
}

// Patch mspConnection to delegate to sim when active
let activeConn: any = mspConnection

export function getActiveConnection() { return activeConn }

export const useConnectionStore = create<ConnectionStore>((set, get) => ({
  state: 'disconnected',
  portName: '',
  baudRate: 115200,
  simulateMode: false,
  simConnection: null,
  fcInfo: null,
  toasts: [],
  availablePorts: [],

  setBaudRate: (b) => set({ baudRate: b }),

  setSimulateMode: (v) => set({ simulateMode: v }),

  refreshPorts: async () => {
    if (!('serial' in navigator)) return
    try {
      const ports = await (navigator as any).serial.getPorts()
      set({ availablePorts: ports.map((p: SerialPort) => p.getInfo()) })
    } catch {}
  },

  requestPort: async () => {
    if (!('serial' in navigator)) return null
    try {
      return await (navigator as any).serial.requestPort()
    } catch {
      return null
    }
  },

  connect: async (port?: SerialPort) => {
    const { simulateMode, baudRate } = get()
    set({ state: 'connecting' })

    try {
      if (simulateMode) {
        const sim = new SimulatedMSPConnection()
        activeConn = sim
        set({ simConnection: sim, state: 'connected', portName: 'SIMULATE' })
      } else {
        if (!port) throw new Error('No port selected')
        activeConn = mspConnection
        mspConnection.onDisconnect = () => {
          get().addToast('error', 'Flight controller disconnected')
          set({ state: 'disconnected', portName: '', fcInfo: null })
          mspPoller.stop()
        }
        await mspConnection.connect(port, baudRate)
        const info = port.getInfo()
        set({
          state: 'connected',
          portName: `USB VID:${info.usbVendorId?.toString(16)?.toUpperCase()} PID:${info.usbProductId?.toString(16)?.toUpperCase()}`,
        })
      }

      // Fetch FC info
      try {
        const [apiVer, variant, version, board] = await Promise.all([
          getApiVersion(),
          getFcVariant(),
          getFcVersion(),
          getBoardInfo(),
        ])
        set({
          fcInfo: {
            apiVersion: `${apiVer.major}.${apiVer.minor}`,
            fcVariant: variant,
            fcVersion: version,
            boardId: board.boardId,
            hardwareRevision: board.hardwareRevision,
          },
        })
      } catch {}

      mspPoller.start()
      get().addToast('success', 'Connected to flight controller')
    } catch (err: any) {
      set({ state: 'error' })
      get().addToast('error', err.message ?? 'Connection failed')
      setTimeout(() => set({ state: 'disconnected' }), 2000)
    }
  },

  disconnect: async () => {
    mspPoller.stop()
    const { simConnection } = get()
    if (simConnection) {
      await simConnection.disconnect()
      activeConn = mspConnection
    } else {
      await mspConnection.disconnect()
    }
    set({ state: 'disconnected', portName: '', fcInfo: null, simConnection: null })
    get().addToast('info', 'Disconnected')
  },

  addToast: (type, message) => {
    const id = Math.random().toString(36).slice(2)
    set((s) => ({ toasts: [...s.toasts, { id, type, message }] }))
    setTimeout(() => get().removeToast(id), 4000)
  },

  removeToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}))
