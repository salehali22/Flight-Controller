import { useTelemetryStore } from '../store/telemetryStore'

export function StatusBar() {
  const { attitude, status } = useTelemetryStore()

  return (
    <div style={{
      height: 24, background: 'var(--sal-bg-deep)', borderTop: '1px solid var(--sal-border)',
      display: 'flex', alignItems: 'center', paddingInline: 10, gap: 16,
      flexShrink: 0, fontSize: 11, fontFamily: 'var(--font-mono)',
    }}>
      {/* Armed status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
        <div className={`led ${status?.armed ? 'led-green' : 'led-off'}`} style={{ width: 6, height: 6 }} />
        <span style={{ color: status?.armed ? '#4caf50' : '#555', fontWeight: 600, letterSpacing: '0.08em' }}>
          {status?.armed ? 'ARMED' : 'DISARMED'}
        </span>
      </div>

      <div style={{ width: 1, height: 14, background: 'var(--sal-border)' }} />

      {/* Attitude */}
      <span style={{ color: '#666' }}>
        R: <span style={{ color: '#ccc' }}>{attitude.roll.toFixed(1).padStart(6)}°</span>
        {'  '}P: <span style={{ color: '#ccc' }}>{attitude.pitch.toFixed(1).padStart(6)}°</span>
        {'  '}Y: <span style={{ color: '#ccc' }}>{attitude.yaw.toFixed(0).padStart(5)}°</span>
      </span>

      {status && (
        <>
          <div style={{ width: 1, height: 14, background: 'var(--sal-border)' }} />
          <span style={{ color: '#666' }}>
            CPU: <span style={{ color: status.cpuLoad > 70 ? '#f44336' : '#ccc' }}>{status.cpuLoad}%</span>
          </span>
          <span style={{ color: '#666' }}>
            Cycle: <span style={{ color: '#ccc' }}>{status.cycleTime}μs</span>
          </span>
          <span style={{ color: '#666' }}>
            I²C Err: <span style={{ color: status.i2cErrors > 0 ? '#f44336' : '#ccc' }}>{status.i2cErrors}</span>
          </span>
        </>
      )}

      <div style={{ flex: 1 }} />
      <span style={{ color: '#444' }}>SAL FC v1.0.0</span>
    </div>
  )
}
