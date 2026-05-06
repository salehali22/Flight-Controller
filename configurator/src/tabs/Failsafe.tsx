import { useFCStore } from '../store/fcStore'
import { useConnectionStore } from '../store/connectionStore'

export function Failsafe() {
  const { failsafeGuardTime, failsafeProcedure, failsafeThrottle, setFailsafe } = useFCStore()
  const { state, addToast } = useConnectionStore()

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: 12, maxWidth: 560 }}>
      <div style={{ padding: '7px 10px', background: '#2b1f0d', border: '1px solid #7d5a2e', marginBottom: 10, fontSize: 11, color: '#cc9966' }}>
        ⚠ Failsafe activates on RC signal loss. Configure carefully — wrong settings can cause crashes or flyaways.
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 10 }}>
        <button className="btn-pri" onClick={() => addToast('success','Failsafe saved')} disabled={state !== 'connected'}>Save</button>
      </div>

      <div className="panel" style={{ marginBottom: 10 }}>
        <div className="panel-hd">Stage 1 — Signal Loss Detection</div>
        <div style={{ padding: '10px 12px' }}>
          <div style={{ fontSize: 11, color: '#666', marginBottom: 4 }}>
            Guard Time: <span style={{ fontFamily: 'Fira Code, monospace', color: '#ccc' }}>{failsafeGuardTime} ms</span>
            <span style={{ color: '#555', marginLeft: 8 }}>— time to wait for signal recovery before Stage 2</span>
          </div>
          <input type="range" min={100} max={1500} step={50} value={failsafeGuardTime}
            onChange={e => setFailsafe('failsafeGuardTime', +e.target.value)} style={{ width: '100%' }} />
        </div>
      </div>

      <div className="panel">
        <div className="panel-hd">Stage 2 — Failsafe Procedure</div>
        <div style={{ padding: '10px 12px' }}>
          <div style={{ display: 'flex', gap: 1, marginBottom: 12 }}>
            {[['Drop','DROP'],['Land','LAND'],['RTH','RETURN_TO_HOME']].map(([label, val]) => (
              <button key={val} onClick={() => setFailsafe('failsafeProcedure', val)} className="btn"
                style={{ flex: 1, border: '1px solid #333', borderRadius: 0,
                  background: failsafeProcedure === val ? '#1e6b52' : '#1a1a1a',
                  color: failsafeProcedure === val ? '#fff' : '#777' }}>
                {label}
              </button>
            ))}
          </div>

          {failsafeProcedure === 'DROP' && (
            <div style={{ padding: '6px 10px', background: '#2b0d0d', border: '1px solid #7d2e2e', fontSize: 11, color: '#cc6666', marginBottom: 10 }}>
              DROP: motors immediately stop. Craft falls. Use only below 30m over soft terrain.
            </div>
          )}

          {failsafeProcedure === 'LAND' && (
            <div>
              <div style={{ fontSize: 11, color: '#666', marginBottom: 4 }}>
                Landing Throttle: <span style={{ fontFamily: 'Fira Code, monospace', color: '#ccc' }}>{failsafeThrottle}</span>
              </div>
              <input type="range" min={1000} max={2000} value={failsafeThrottle}
                onChange={e => setFailsafe('failsafeThrottle', +e.target.value)} style={{ width: '100%' }} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
