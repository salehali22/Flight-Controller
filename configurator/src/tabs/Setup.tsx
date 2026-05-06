import { useState } from 'react'
import { ThreeDModel } from '../components/ThreeDModel'
import { useConnectionStore } from '../store/connectionStore'
import { useTelemetryStore } from '../store/telemetryStore'
import { useFCStore } from '../store/fcStore'
import { calibrateAccel, calibrateMag } from '../msp/MSPCommands'

const SENSOR_BITS: [string, number][] = [
  ['GYRO', 0x01], ['ACC', 0x02], ['BARO', 0x04], ['MAG', 0x08], ['GPS', 0x40], ['SONAR', 0x10],
]

export function Setup() {
  const { state, fcInfo, addToast } = useConnectionStore()
  const { attitude, status } = useTelemetryStore()
  const { mixerType } = useFCStore()
  const [calibState, setCalibState] = useState<null | 'accel' | 'mag'>(null)
  const connected = state === 'connected'

  const doCalib = async (type: 'accel' | 'mag') => {
    setCalibState(type)
    try {
      if (type === 'accel') { await calibrateAccel(); addToast('success', 'Accel calibration triggered — keep level') }
      else { await calibrateMag(); addToast('success', 'Mag calibration triggered — rotate FC') }
    } catch { addToast('error', 'Calibration failed') }
    setTimeout(() => setCalibState(null), type === 'accel' ? 5000 : 30000)
  }

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* ── 3D Model ── */}
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', borderRight: '1px solid #2e2e2e' }}>
        <div style={{ padding: '6px 10px', background: '#1a1a1a', borderBottom: '1px solid #2e2e2e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 11, fontWeight: 600, color: '#888', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            3D Attitude — {mixerType}
          </span>
          <div style={{ display: 'flex', gap: 12, fontFamily: 'Fira Code, monospace', fontSize: 11 }}>
            <span style={{ color: '#555' }}>R: <span style={{ color: '#eee' }}>{attitude.roll.toFixed(1)}°</span></span>
            <span style={{ color: '#555' }}>P: <span style={{ color: '#eee' }}>{attitude.pitch.toFixed(1)}°</span></span>
            <span style={{ color: '#555' }}>Y: <span style={{ color: '#eee' }}>{attitude.yaw.toFixed(0)}°</span></span>
          </div>
        </div>
        <div style={{ flex: 1, minHeight: 0 }}>
          <ThreeDModel mixerType={mixerType} />
        </div>
      </div>

      {/* ── Right panel ── */}
      <div style={{ width: 260, flexShrink: 0, overflowY: 'auto', background: '#1e1e1e' }}>

        {/* Armed status */}
        <div style={{
          padding: '10px 12px', borderBottom: '1px solid #2e2e2e',
          background: status?.armed ? '#0d2b0d' : '#1e1e1e',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div className={`led ${status?.armed ? 'led-green' : 'led-off'}`} />
            <span style={{
              fontFamily: 'Fira Code, monospace', fontSize: 14, fontWeight: 700,
              letterSpacing: '0.1em', color: status?.armed ? '#4caf50' : '#555',
            }}>
              {status?.armed ? 'ARMED' : 'DISARMED'}
            </span>
          </div>
        </div>

        {/* Sensors */}
        <div style={{ padding: '8px 12px', borderBottom: '1px solid #2e2e2e' }}>
          <div className="panel-hd" style={{ marginInline: -12, marginTop: -8, marginBottom: 8, paddingInline: 12 }}>Sensors</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 4 }}>
            {SENSOR_BITS.map(([name, bit]) => {
              const ok = status ? (status.sensorStatus & bit) !== 0 : false
              return (
                <div key={name} style={{
                  padding: '4px 0', textAlign: 'center',
                  border: `1px solid ${ok ? '#2e7d32' : '#2a2a2a'}`,
                  background: ok ? '#0d1a0d' : '#111',
                }}>
                  <div className={`led ${ok ? 'led-green' : 'led-off'}`} style={{ margin: '0 auto 2px' }} />
                  <div style={{ fontSize: 10, fontFamily: 'Fira Code, monospace', color: ok ? '#4caf50' : '#444' }}>{name}</div>
                </div>
              )
            })}
          </div>
        </div>

        {/* FC Info */}
        {fcInfo && (
          <div style={{ padding: '8px 12px', borderBottom: '1px solid #2e2e2e' }}>
            <div className="panel-hd" style={{ marginInline: -12, marginTop: -8, marginBottom: 8, paddingInline: 12 }}>FC Info</div>
            {[
              ['Board',    fcInfo.boardId],
              ['Firmware', `${fcInfo.fcVariant} ${fcInfo.fcVersion}`],
              ['API',      fcInfo.apiVersion],
              ['HW Rev',   String(fcInfo.hardwareRevision)],
            ].map(([k, v]) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: 12 }}>
                <span style={{ color: '#666' }}>{k}</span>
                <span style={{ fontFamily: 'Fira Code, monospace', color: '#ccc' }}>{v}</span>
              </div>
            ))}
          </div>
        )}

        {/* System */}
        {status && (
          <div style={{ padding: '8px 12px', borderBottom: '1px solid #2e2e2e' }}>
            <div className="panel-hd" style={{ marginInline: -12, marginTop: -8, marginBottom: 8, paddingInline: 12 }}>System</div>
            <div style={{ marginBottom: 6 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 3 }}>
                <span style={{ color: '#666' }}>CPU Load</span>
                <span style={{ fontFamily: 'Fira Code, monospace', color: status.cpuLoad > 70 ? '#f44336' : '#ccc' }}>{status.cpuLoad}%</span>
              </div>
              <div style={{ height: 3, background: '#222' }}>
                <div style={{
                  height: '100%', width: `${status.cpuLoad}%`,
                  background: status.cpuLoad > 70 ? '#f44336' : '#45c98f',
                  transition: 'width 0.5s',
                }} />
              </div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: '#666' }}>Cycle Time</span>
              <span style={{ fontFamily: 'Fira Code, monospace', color: '#ccc' }}>{status.cycleTime}μs</span>
            </div>
          </div>
        )}

        {/* Calibration */}
        <div style={{ padding: '8px 12px', borderBottom: '1px solid #2e2e2e' }}>
          <div className="panel-hd" style={{ marginInline: -12, marginTop: -8, marginBottom: 8, paddingInline: 12 }}>Calibration</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <button className="btn" onClick={() => doCalib('accel')} disabled={!connected || !!calibState}>
              {calibState === 'accel' ? '⟳ Calibrating…' : 'Calibrate Accelerometer'}
            </button>
            <button className="btn" onClick={() => doCalib('mag')} disabled={!connected || !!calibState}>
              {calibState === 'mag' ? '⟳ Calibrating…' : 'Calibrate Magnetometer'}
            </button>
          </div>
          {calibState && (
            <div style={{ marginTop: 6, fontSize: 11, color: '#ff9800', fontFamily: 'Fira Code, monospace' }}>
              {calibState === 'accel' ? '⚠ Keep FC flat and still…' : '⚠ Rotate FC in all orientations…'}
            </div>
          )}
        </div>

        {!connected && (
          <div style={{ padding: 12, fontSize: 12, color: '#555', textAlign: 'center' }}>
            Connect to FC to see live data
          </div>
        )}
      </div>
    </div>
  )
}
