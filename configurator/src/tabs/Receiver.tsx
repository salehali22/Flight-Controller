import { useTelemetryStore } from '../store/telemetryStore'
import { useState } from 'react'

const CH_NAMES = ['Roll','Pitch','Throttle','Yaw','AUX 1','AUX 2','AUX 3','AUX 4']

export function Receiver() {
  const { rcChannels } = useTelemetryStore()
  const [chMap, setChMap] = useState('AETR')
  const [deadband, setDeadband] = useState(5)
  const [mid, setMid] = useState(50)
  const [expo, setExpo] = useState(0)

  return (
    <div style={{ height: '100%', display: 'flex', gap: 0, overflow: 'hidden' }}>
      {/* Live channels */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 12, borderRight: '1px solid #2e2e2e' }}>
        <div className="panel">
          <div className="panel-hd">Live RC Channels</div>
          <div style={{ padding: '8px 12px' }}>
            {CH_NAMES.map((name, i) => {
              const v = rcChannels[i] ?? 1500
              const pct = ((v - 1000) / 1000) * 100
              const isThrottle = name === 'Throttle'
              return (
                <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 7 }}>
                  <span style={{ fontSize: 11, color: '#777', width: 64, flexShrink: 0, fontFamily: 'Fira Code, monospace' }}>{name}</span>
                  <div style={{ flex: 1, height: 16, background: '#111', position: 'relative', border: '1px solid #2a2a2a' }}>
                    {/* Center mark */}
                    {!isThrottle && <div style={{ position: 'absolute', left: '50%', top: 0, bottom: 0, width: 1, background: '#2e2e2e' }} />}
                    {/* Bar */}
                    <div style={{
                      position: 'absolute', top: 2, bottom: 2,
                      background: '#45c98f',
                      left: isThrottle ? 2 : pct > 50 ? '50%' : `${pct}%`,
                      width: isThrottle
                        ? `${Math.max(0, pct) - 0.5}%`
                        : `${Math.abs(pct - 50)}%`,
                      transform: !isThrottle && pct < 50 ? 'none' : 'none',
                      opacity: 0.75,
                    }} />
                  </div>
                  <span style={{ fontFamily: 'Fira Code, monospace', fontSize: 11, color: '#bbb', width: 40, textAlign: 'right' }}>{v}</span>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Config */}
      <div style={{ width: 260, flexShrink: 0, overflowY: 'auto', padding: 12 }}>
        <div className="panel" style={{ marginBottom: 10 }}>
          <div className="panel-hd">Channel Map</div>
          <div style={{ padding: '8px 12px', display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {['AETR','TAER','ETAR','RETA'].map(m => (
              <button key={m} onClick={() => setChMap(m)} className="btn"
                style={{ background: chMap === m ? '#1e6b52' : '#1a1a1a', color: chMap === m ? '#fff' : '#777',
                  border: `1px solid ${chMap === m ? '#247a5c' : '#333'}`, fontFamily: 'var(--font-mono)', fontSize: 11 }}>
                {m}
              </button>
            ))}
          </div>
        </div>

        <div className="panel">
          <div className="panel-hd">Stick Settings</div>
          <div style={{ padding: '10px 12px' }}>
            {[
              { label: `Deadband: ${deadband}`, val: deadband, set: setDeadband, min: 0, max: 32, step: 1 },
              { label: `Throttle Mid: ${mid}%`, val: mid, set: setMid, min: 0, max: 100, step: 1 },
              { label: `RC Expo: ${(expo/100).toFixed(2)}`, val: expo, set: setExpo, min: 0, max: 100, step: 1 },
            ].map(({ label, val, set, min, max, step }) => (
              <div key={label} style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 11, color: '#666', marginBottom: 4, fontFamily: 'Fira Code, monospace' }}>{label}</div>
                <input type="range" min={min} max={max} step={step} value={val}
                  onChange={e => set(+e.target.value)} style={{ width: '100%' }} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
