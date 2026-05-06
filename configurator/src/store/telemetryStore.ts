import { create } from 'zustand'
import type { AttitudeData, StatusData, ImuData } from '../msp/MSPCommands'

interface TelemetryStore {
  attitude: AttitudeData
  status: StatusData | null
  imu: ImuData | null
  motors: number[]
  rcChannels: number[]
  imuHistory: { t: number; x: number; y: number; z: number }[]

  setAttitude: (a: AttitudeData) => void
  setStatus: (s: StatusData) => void
  setImu: (i: ImuData) => void
  setMotors: (m: number[]) => void
  setRcChannels: (rc: number[]) => void
}

export const useTelemetryStore = create<TelemetryStore>((set) => ({
  attitude: { roll: 0, pitch: 0, yaw: 0 },
  status: null,
  imu: null,
  motors: [0, 0, 0, 0, 0, 0, 0, 0],
  rcChannels: Array(8).fill(1500),
  imuHistory: [],

  setAttitude: (attitude) => set({ attitude }),
  setStatus: (status) => set({ status }),
  setImu: (imu) => {
    set((s) => {
      const entry = { t: Date.now(), x: imu.gyroX, y: imu.gyroY, z: imu.gyroZ }
      const history = [...s.imuHistory, entry].slice(-200)
      return { imu, imuHistory: history }
    })
  },
  setMotors: (motors) => set({ motors }),
  setRcChannels: (rcChannels) => set({ rcChannels }),
}))
