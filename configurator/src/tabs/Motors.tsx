import { useState, useEffect } from 'react'
import { setMotors } from '../msp/MSPCommands'
import { useConnectionStore } from '../store/connectionStore'
import { useTelemetryStore } from '../store/telemetryStore'
import { useFCStore } from '../store/fcStore'
import { MotorDiagram } from '../components/MotorDiagram'
import { MIXER_MOTORS } from '../components/ThreeDModel'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export function Motors() {
  const { state, addToast } = useConnectionStore()
  const { motors: live, imuHistory } = useTelemetryStore()
  const { mixerType } = useFCStore()
  const connected = state === 'connected'

  const motorCount = (MIXER_MOTORS[mixerType] ?? MIXER_MOTORS.QUADX).length
  const [propsOff, setPropsOff] = useState(false)
  const [testOn, setTestOn] = useState(false)
  const [vals, setVals] = useState<number[]>(Array(8).fill(1000))
  const [master, setMaster] = useState(1000)

  const setVal = async (idx: number, v: number) => {
    const next = [...vals]; next[idx] = v; setVals(next)
    if (testOn && connected) await setMotors(next).catch(() => {})
  }
  const setMaster_ = async (v: number) => {
    setMaster(v); const next = Array(8).fill(1000); for (let i = 0; i < motorCount; i++) next[i] = v; setVals(next)
    if (testOn && connected) await setMotors(next).catch(() => {})
  }
  const stopTest = () => {
    setTestOn(false); const z = Array(8).fill(1000); setVals(z); setMaster(1000)
    if (connected) setMotors(z).catch(() => {})
  }
  useEffect(() => () => { if (connected) setMotors(Array(8).fill(1000)).catch(() => {}) }, [])

  const motorColors = ['#ff3344','#44cc66','#3388ff','#ffcc00','#ff6600','#aa44ff','#00ccaa','#ff88aa']
  const displayVals = testOn ? vals : live

  const chartData = imuHistory.slice(-100).map((d, i) => ({ i, x: d.x, y: d.y, z: d.z }))

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 10 }}>
      {/* Safety warning */}
      <div style={{ padding: '8px 12px', background: '#2b0d0d', border: '1px solid #7d2e2e', display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ fontSize: 16 }}>⚠</span>
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#f44336' }}>SAFETY WARNING</div>
          <div style={{ fontSize: 11, color: '#cc8888', marginTop: 2 }}>
            Remove all propellers before using motor test. Spinning props can cause serious injury.
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 10, flex: 1, minHeight: 0 }}>
        {/* Controls */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div className="panel">
            <div className="panel-hd">Motor Test</div>
            <div style={{ padding: '10px 12px' }}>
              {/* Prop check */}
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10, cursor: 'pointer' }}>
                <input type="checkbox" checked={propsOff} onChange={e => { setPropsOff(e.target.checked); if (!e.target.checked) stopTest() }} />
                <span style={{ fontSize: 12, color: propsOff ? '#f44336' : '#777' }}>
                  ✓ I confirm propellers are removed
                </span>
              </label>

              {/* Enable/disable */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                {!testOn ? (
                  <button className="btn-success" onClick={() => setTestOn(true)} disabled={!propsOff || !connected}>
                    Enable Motor Test
                  </button>
                ) : (
                  <button className="btn-danger" onClick={stopTest}>Stop All Motors</button>
                )}
                <span style={{ fontSize: 11, color: '#555' }}>
                  {!connected ? 'Not connected' : !propsOff ? 'Check props removed first' : testOn ? 'MOTORS ACTIVE' : 'Ready to test'}
                </span>
              </div>

              {/* Master */}
              <div style={{ marginBottom: 14 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#666', marginBottom: 4 }}>
                  <span>MASTER</span>
                  <span style={{ fontFamily: 'Fira Code, monospace', color: '#ccc' }}>{master}</span>
                </div>
                <input type="range" min={1000} max={2000} value={master}
                  onChange={e => setMaster_(+e.target.value)} disabled={!testOn} style={{ width: '100%' }} />
              </div>

              {/* Per-motor sliders */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {Array.from({ length: motorCount }, (_, i) => (
                  <div key={i}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 3 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <div style={{ width: 8, height: 8, borderRadius: '50%', background: motorColors[i] }} />
                        <span style={{ fontFamily: 'Fira Code, monospace', color: '#aaa' }}>M{i + 1}</span>
                      </div>
                      <span style={{ fontFamily: 'Fira Code, monospace', color: '#ccc' }}>{vals[i]}</span>
                    </div>
                    <input type="range" min={1000} max={2000} value={vals[i]}
                      onChange={e => setVal(i, +e.target.value)} disabled={!testOn} style={{ width: '100%' }} />
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Gyro chart */}
          <div className="panel" style={{ flex: 1, minHeight: 160 }}>
            <div className="panel-hd">Gyro Vibration (live)</div>
            <div style={{ padding: '8px 0 0' }}>
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={150}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="2 4" stroke="#222" />
                    <XAxis dataKey="i" hide />
                    <YAxis stroke="#444" tick={{ fontSize: 9, fontFamily: 'Fira Code' }} width={35} />
                    <Tooltip contentStyle={{ background: '#1e1e1e', border: '1px solid #333', fontSize: 10 }} labelStyle={{ display: 'none' }} />
                    <Line dataKey="x" stroke={motorColors[0]} dot={false} strokeWidth={1} name="X" isAnimationActive={false} />
                    <Line dataKey="y" stroke={motorColors[1]} dot={false} strokeWidth={1} name="Y" isAnimationActive={false} />
                    <Line dataKey="z" stroke={motorColors[2]} dot={false} strokeWidth={1} name="Z" isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ height: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#444', fontSize: 12 }}>
                  Connect for live gyro data
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Motor diagram */}
        <div className="panel" style={{ width: 260, display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 12, gap: 8 }}>
          <div style={{ fontSize: 11, color: '#555', textTransform: 'uppercase', fontFamily: 'Fira Code, monospace', alignSelf: 'flex-start' }}>
            {mixerType} — {motorCount} motors
          </div>
          <MotorDiagram mixerType={mixerType} values={displayVals} size={230} />
          {/* Live motor values */}
          <div style={{ width: '100%', borderTop: '1px solid #2a2a2a', paddingTop: 8 }}>
            {Array.from({ length: motorCount }, (_, i) => {
              const v = displayVals[i] ?? 1000
              const pct = (v - 1000) / 10
              return (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: motorColors[i], flexShrink: 0 }} />
                  <span style={{ fontFamily: 'Fira Code, monospace', fontSize: 10, color: '#777', width: 22 }}>M{i+1}</span>
                  <div style={{ flex: 1, height: 4, background: '#1a1a1a', position: 'relative' }}>
                    <div style={{ width: `${pct}%`, height: '100%', background: motorColors[i], opacity: 0.8 }} />
                  </div>
                  <span style={{ fontFamily: 'Fira Code, monospace', fontSize: 10, color: '#aaa', width: 35, textAlign: 'right' }}>{v}</span>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
