import { create } from 'zustand'
import type { PIDValues } from '../msp/MSPCommands'

interface FCStore {
  pid: PIDValues
  features: number
  escProtocol: string
  mixerType: string
  rates: {
    roll: [number, number, number]
    pitch: [number, number, number]
    yaw: [number, number, number]
  }
  failsafeGuardTime: number
  failsafeProcedure: string
  failsafeThrottle: number

  setPid: (pid: PIDValues) => void
  setFeatures: (f: number) => void
  setEscProtocol: (p: string) => void
  setMixerType: (t: string) => void
  setRates: (r: FCStore['rates']) => void
  setFailsafe: (key: string, val: any) => void
}

export const useFCStore = create<FCStore>((set) => ({
  pid: {
    roll:  [45, 40, 20],
    pitch: [45, 40, 20],
    yaw:   [70, 45, 0],
  },
  features: 0,
  escProtocol: 'DSHOT300',
  mixerType: 'QUADX',
  rates: {
    roll:  [0.7, 0.7, 0.5],
    pitch: [0.7, 0.7, 0.5],
    yaw:   [0.7, 0.7, 0.5],
  },
  failsafeGuardTime: 200,
  failsafeProcedure: 'DROP',
  failsafeThrottle: 1000,

  setPid: (pid) => set({ pid }),
  setFeatures: (features) => set({ features }),
  setEscProtocol: (escProtocol) => set({ escProtocol }),
  setMixerType: (mixerType) => set({ mixerType }),
  setRates: (rates) => set({ rates }),
  setFailsafe: (key, val) => set((s) => ({ ...s, [key]: val })),
}))
