import { useState } from 'react'
import { useConnectionStore } from '../store/connectionStore'

function Toggle({ on, set }: { on: boolean; set: (v: boolean) => void }) {
  return (
    <div className={`toggle-track ${on ? 'on' : ''}`} onClick={() => set(!on)} style={{ cursor: 'pointer' }}>
      <div className="toggle-knob" />
    </div>
  )
}

function Slider({ label, val, set, min, max }: { label: string; val: number; set: (v: number) => void; min: number; max: number }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#666', marginBottom: 4 }}>
        <span>{label}</span>
        <span style={{ fontFamily: 'Fira Code, monospace', color: '#ccc' }}>{val} Hz</span>
      </div>
      <input type="range" min={min} max={max} value={val} onChange={e => set(+e.target.value)} style={{ width: '100%' }} />
    </div>
  )
}

export function Filters() {
  const { state, addToast } = useConnectionStore()
  const [gyroType, setGyroType]     = useState('BiQuad')
  const [gyroFreq, setGyroFreq]     = useState(200)
  const [dtermType, setDtermType]   = useState('PT1')
  const [dtermFreq, setDtermFreq]   = useState(100)
  const [rpm, setRpm]               = useState(false)
  const [rpmH, setRpmH]             = useState(3)
  const [dynNotch, setDynNotch]     = useState(true)
  const [dynMin, setDynMin]         = useState(100)
  const [dynMax, setDynMax]         = useState(600)
  const [dynCount, setDynCount]     = useState(3)
  const TYPES = ['PT1','BiQuad','PT2','PT3']

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: 12, maxWidth: 640 }}>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 10 }}>
        <button className="btn-pri" onClick={() => addToast('success','Filters saved')} disabled={state !== 'connected'}>Save</button>
      </div>

      {[
        { title: 'Gyro Low-Pass Filter', type: gyroType, setType: setGyroType, freq: gyroFreq, setFreq: setGyroFreq },
        { title: 'D-Term Low-Pass Filter', type: dtermType, setType: setDtermType, freq: dtermFreq, setFreq: setDtermFreq },
      ].map(({ title, type, setType, freq, setFreq }) => (
        <div className="panel" style={{ marginBottom: 10 }} key={title}>
          <div className="panel-hd">{title}</div>
          <div style={{ padding: '10px 12px', display: 'flex', gap: 16, alignItems: 'flex-end' }}>
            <div>
              <div className="lbl">Type</div>
              <select className="sel" style={{ width: 100 }} value={type} onChange={e => setType(e.target.value)}>
                {TYPES.map(t => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div style={{ flex: 1 }}>
              <Slider label="Cutoff Frequency" val={freq} set={setFreq} min={30} max={500} />
            </div>
          </div>
        </div>
      ))}

      <div className="panel" style={{ marginBottom: 10 }}>
        <div className="panel-hd" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          RPM Filter (requires DSHOT + bidirectional)
          <div style={{ marginLeft: 'auto' }}><Toggle on={rpm} set={setRpm} /></div>
        </div>
        {rpm && (
          <div style={{ padding: '10px 12px' }}>
            <div style={{ fontSize: 11, color: '#666', marginBottom: 4 }}>Harmonics: <span style={{ fontFamily: 'Fira Code, monospace', color: '#ccc' }}>{rpmH}</span></div>
            <input type="range" min={1} max={5} value={rpmH} onChange={e => setRpmH(+e.target.value)} style={{ width: '100%' }} />
          </div>
        )}
      </div>

      <div className="panel">
        <div className="panel-hd" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          Dynamic Notch Filter
          <div style={{ marginLeft: 'auto' }}><Toggle on={dynNotch} set={setDynNotch} /></div>
        </div>
        {dynNotch && (
          <div style={{ padding: '10px 12px' }}>
            <Slider label="Min Frequency" val={dynMin} set={setDynMin} min={50} max={300} />
            <Slider label="Max Frequency" val={dynMax} set={setDynMax} min={200} max={1000} />
            <div style={{ fontSize: 11, color: '#666', marginBottom: 4 }}>Notch Count: <span style={{ fontFamily: 'Fira Code, monospace', color: '#ccc' }}>{dynCount}</span></div>
            <input type="range" min={1} max={5} value={dynCount} onChange={e => setDynCount(+e.target.value)} style={{ width: '100%' }} />
          </div>
        )}
      </div>
    </div>
  )
}
