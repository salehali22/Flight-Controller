import { useState, useEffect } from 'react'
import { useFCStore } from '../store/fcStore'
import { useConnectionStore } from '../store/connectionStore'
import { getPID, setPID } from '../msp/MSPCommands'
import type { PIDValues } from '../msp/MSPCommands'
import { RatesCurve } from '../components/RatesCurve'

const AXES = ['roll', 'pitch', 'yaw'] as const
type Axis = typeof AXES[number]

function NumInput({ val, onChange }: { val: number; onChange: (v: number) => void }) {
  return (
    <input
      type="number" min={0} max={250} value={val}
      onChange={e => onChange(+e.target.value)}
      className="inp" style={{ width: 56, textAlign: 'center', padding: '4px 4px' }}
    />
  )
}

export function PIDTuning() {
  const { pid, rates, setPid: storePid, setRates } = useFCStore()
  const { state, addToast } = useConnectionStore()
  const connected = state === 'connected'

  const [localPid, setLocalPid] = useState<PIDValues>({ ...pid })
  const [localRates, setLocalRates] = useState({ ...rates })
  const [profile, setProfile] = useState(1)
  const [selAxis, setSelAxis] = useState<Axis>('roll')

  useEffect(() => {
    if (!connected) return
    getPID().then(p => { setLocalPid(p); storePid(p) }).catch(() => {})
  }, [connected])

  const upPid = (ax: Axis, i: 0|1|2, v: number) =>
    setLocalPid(p => ({ ...p, [ax]: p[ax].map((x, j) => j === i ? v : x) as [number,number,number] }))

  const upRate = (ax: Axis, i: 0|1|2, v: number) =>
    setLocalRates(r => ({ ...r, [ax]: r[ax].map((x, j) => j === i ? v : x) as [number,number,number] }))

  const save = async () => {
    try { await setPID(localPid); storePid(localPid); setRates(localRates); addToast('success', 'PID saved') }
    catch { addToast('error', 'Failed to save PID') }
  }

  const [rcRate, superRate, expo] = localRates[selAxis]

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: 12 }}>
      {/* ── Header ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
        <div style={{ display: 'flex', border: '1px solid #2e2e2e', background: '#1a1a1a' }}>
          {[1,2,3].map(p => (
            <button key={p} onClick={() => setProfile(p)} className="btn"
              style={{ border: 'none', borderRight: p < 3 ? '1px solid #2e2e2e' : 'none',
                background: profile === p ? '#1e6b52' : 'transparent',
                color: profile === p ? '#fff' : '#777', padding: '4px 12px', borderRadius: 0 }}>
              Profile {p}
            </button>
          ))}
        </div>
        <div style={{ flex: 1 }} />
        <button className="btn-pri" onClick={save} disabled={!connected} style={{ padding: '4px 16px' }}>
          Save PIDs
        </button>
      </div>

      {/* ── PID table ── */}
      <div className="panel" style={{ marginBottom: 10 }}>
        <div className="panel-hd">PID Gains</div>
        <table className="tool-table">
          <thead>
            <tr>
              <th>Axis</th>
              <th>P (Proportional)</th>
              <th></th>
              <th>I (Integral)</th>
              <th></th>
              <th>D (Derivative)</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {AXES.map(ax => (
              <tr key={ax}>
                <td>
                  <span style={{ fontFamily: 'Fira Code, monospace', fontWeight: 700, textTransform: 'uppercase',
                    color: ax === 'roll' ? '#ff5555' : ax === 'pitch' ? '#55cc77' : '#5588ff' }}>
                    {ax}
                  </span>
                </td>
                {([0,1,2] as const).map(i => (
                  <>
                    <td key={`n${i}`}><NumInput val={localPid[ax][i]} onChange={v => upPid(ax, i, v)} /></td>
                    <td key={`s${i}`} style={{ paddingLeft: 0, paddingRight: 4 }}>
                      <input type="range" min={0} max={250} value={localPid[ax][i]}
                        onChange={e => upPid(ax, i, +e.target.value)}
                        style={{ width: 90 }} />
                    </td>
                  </>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── Rates ── */}
      <div className="panel">
        <div className="panel-hd" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span>RC Rates &amp; Expo</span>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 1 }}>
            {AXES.map(ax => (
              <button key={ax} onClick={() => setSelAxis(ax)} className="btn"
                style={{ border: '1px solid #333', borderRadius: 0, padding: '2px 10px', fontSize: 11,
                  textTransform: 'uppercase', fontFamily: 'Fira Code, monospace',
                  background: selAxis === ax ? '#1e6b52' : '#1a1a1a',
                  color: selAxis === ax ? '#fff' : '#777' }}>
                {ax}
              </button>
            ))}
          </div>
        </div>
        <div style={{ padding: '10px 12px', display: 'flex', gap: 20, alignItems: 'flex-start' }}>
          <div style={{ flex: 1 }}>
            {([
              ['RC Rate',    0, 0.1, 2.5, 0.01],
              ['Super Rate', 1, 0,   1.0, 0.01],
              ['Expo',       2, 0,   1.0, 0.01],
            ] as const).map(([label, idx, min, max, step]) => {
              const v = localRates[selAxis][idx as 0|1|2]
              return (
                <div key={label} style={{ marginBottom: 10 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#666', marginBottom: 4 }}>
                    <span>{label}</span>
                    <span style={{ fontFamily: 'Fira Code, monospace', color: '#ccc' }}>{v.toFixed(2)}</span>
                  </div>
                  <input type="range" min={min} max={max} step={step} value={v}
                    onChange={e => upRate(selAxis, idx as 0|1|2, +e.target.value)}
                    style={{ width: '100%' }} />
                </div>
              )
            })}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
            <RatesCurve rcRate={rcRate} superRate={superRate} expo={expo}
              color={selAxis === 'roll' ? '#ff5555' : selAxis === 'pitch' ? '#55cc77' : '#5588ff'} size={180} />
            <span style={{ fontSize: 10, color: '#555' }}>Response curve</span>
          </div>
        </div>
      </div>
    </div>
  )
}
