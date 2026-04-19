import { useState } from 'react'
import { useTelemetryStore } from '../store/telemetryStore'
import { useConnectionStore } from '../store/connectionStore'

const MODES = ['ARM','ANGLE','HORIZON','ACRO','AIRMODE','BEEPER','FLIP OVER AFTER CRASH','TURTLE MODE','GPS RESCUE']

interface Cfg { modeId: number; ch: number; lo: number; hi: number }

export function Modes() {
  const { rcChannels } = useTelemetryStore()
  const { state, addToast } = useConnectionStore()
  const [cfgs, setCfgs] = useState<Cfg[]>(MODES.map((_, i) => ({ modeId: i, ch: 4, lo: 1700, hi: 2100 })))

  const upd = (i: number, p: Partial<Cfg>) => setCfgs(c => c.map((x, j) => j === i ? {...x, ...p} : x))
  const isActive = (c: Cfg) => { const v = rcChannels[c.ch] ?? 1500; return v >= c.lo && v <= c.hi }

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 10 }}>
        <button className="btn-pri" onClick={() => addToast('success','Modes saved')} disabled={state !== 'connected'}>
          Save Modes
        </button>
      </div>

      {/* AUX preview */}
      <div className="panel" style={{ marginBottom: 10 }}>
        <div className="panel-hd">AUX Channel Values</div>
        <div style={{ padding: '8px 12px', display: 'flex', gap: 12 }}>
          {[4,5,6,7].map(ch => {
            const v = rcChannels[ch] ?? 1500
            const pct = ((v - 1000) / 1000) * 100
            return (
              <div key={ch} style={{ flex: 1 }}>
                <div style={{ fontSize: 10, color: '#666', fontFamily: 'Fira Code, monospace', marginBottom: 3 }}>AUX {ch-3}: {v}</div>
                <div style={{ height: 6, background: '#111', border: '1px solid #2a2a2a' }}>
                  <div style={{ width: `${pct}%`, height: '100%', background: '#45c98f', opacity: 0.8 }} />
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <div className="panel">
        <div className="panel-hd">Mode Assignments</div>
        <table className="tool-table">
          <thead><tr><th>Mode</th><th>Status</th><th>AUX Channel</th><th>Range (1000–2000)</th></tr></thead>
          <tbody>
            {MODES.map((name, i) => {
              const c = cfgs[i]; const active = isActive(c)
              return (
                <tr key={name}>
                  <td><span style={{ fontFamily: 'Fira Code, monospace', fontSize: 11, fontWeight: 600, color: '#bbb' }}>{name}</span></td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                      <div className={`led ${active ? 'led-green' : 'led-off'}`} style={{ width: 6, height: 6 }} />
                      <span style={{ fontSize: 11, color: active ? '#4caf50' : '#555', fontFamily: 'Fira Code, monospace' }}>{active ? 'ON' : 'OFF'}</span>
                    </div>
                  </td>
                  <td>
                    <select className="sel" style={{ width: 80 }} value={c.ch} onChange={e => upd(i,{ch:+e.target.value})}>
                      {[4,5,6,7].map(ch => <option key={ch} value={ch}>AUX {ch-3}</option>)}
                    </select>
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <input type="number" min={900} max={2100} value={c.lo}
                        onChange={e => upd(i,{lo:+e.target.value})}
                        className="inp" style={{ width: 56 }} />
                      <div style={{ flex: 1, height: 8, background: '#111', position: 'relative', border: '1px solid #2a2a2a', minWidth: 100 }}>
                        <div style={{
                          position: 'absolute', top: 0, height: '100%', background: active ? '#1b5e20' : '#c9a45c', opacity: 0.7,
                          left: `${((c.lo-900)/1200)*100}%`, width: `${((c.hi-c.lo)/1200)*100}%`
                        }} />
                        {/* Current value marker */}
                        <div style={{
                          position: 'absolute', top: -2, bottom: -2, width: 2, background: '#fff', opacity: 0.5,
                          left: `${((( rcChannels[c.ch] ?? 1500)-900)/1200)*100}%`
                        }} />
                      </div>
                      <input type="number" min={900} max={2100} value={c.hi}
                        onChange={e => upd(i,{hi:+e.target.value})}
                        className="inp" style={{ width: 56 }} />
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
