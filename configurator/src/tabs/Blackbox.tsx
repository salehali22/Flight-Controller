import { useState } from 'react'
import { useConnectionStore } from '../store/connectionStore'

const FIELDS: [string, boolean][] = [
  ['Gyroscope',true],['Accelerometer',true],['PID Error',true],['Setpoint',true],
  ['RC Commands',true],['Motor Outputs',true],['Battery Voltage',false],
  ['Current Meter',false],['Altitude',false],['GPS',false],
]

export function Blackbox() {
  const { state, addToast } = useConnectionStore()
  const [device, setDevice] = useState('SPI Flash')
  const [rate, setRate]     = useState('500 Hz')
  const [fields, setFields] = useState(Object.fromEntries(FIELDS))

  const toggle = (f: string) => setFields(p => ({...p, [f]: !p[f]}))

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: 12, maxWidth: 640 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
        <button className="btn" onClick={() => addToast('info','Log download not available in SIM')}>Download Log</button>
        <button className="btn-pri" onClick={() => addToast('success','Blackbox config saved')} disabled={state !== 'connected'}>Save</button>
      </div>

      <div className="panel" style={{ marginBottom: 10 }}>
        <div className="panel-hd">Storage &amp; Rate</div>
        <div style={{ padding: '10px 12px', display: 'flex', gap: 12 }}>
          <div>
            <div className="lbl">Device</div>
            <select className="sel" style={{ width: 150 }} value={device} onChange={e => setDevice(e.target.value)}>
              {['Serial Port','SPI Flash','SD Card'].map(d => <option key={d}>{d}</option>)}
            </select>
          </div>
          <div>
            <div className="lbl">Logging Rate</div>
            <select className="sel" style={{ width: 100 }} value={rate} onChange={e => setRate(e.target.value)}>
              {['500 Hz','250 Hz','128 Hz','64 Hz','32 Hz'].map(r => <option key={r}>{r}</option>)}
            </select>
          </div>
        </div>
        {/* Storage usage */}
        <div style={{ padding: '0 12px 10px', display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 11, color: '#666' }}>Flash Usage</span>
          <div style={{ flex: 1, height: 4, background: '#111', border: '1px solid #2a2a2a' }}>
            <div style={{ width: '34%', height: '100%', background: '#45c98f' }} />
          </div>
          <span style={{ fontFamily: 'Fira Code, monospace', fontSize: 11, color: '#aaa' }}>34%</span>
        </div>
      </div>

      <div className="panel">
        <div className="panel-hd" style={{ display: 'flex', alignItems: 'center' }}>
          Logged Fields
          <button className="btn" style={{ marginLeft: 'auto', padding: '2px 8px', fontSize: 10 }}
            onClick={() => setFields(Object.fromEntries(FIELDS.map(([f]) => [f, true])))}>
            All
          </button>
        </div>
        <div style={{ padding: '8px 12px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
          {FIELDS.map(([f]) => (
            <label key={f} onClick={() => toggle(f)}
              style={{ display: 'flex', alignItems: 'center', gap: 7, cursor: 'pointer',
                padding: '5px 7px', border: `1px solid ${fields[f] ? '#1e6b52' : '#2a2a2a'}`,
                background: fields[f] ? '#0d1a2b' : '#181818' }}>
              <input type="checkbox" checked={fields[f]} onChange={() => {}} />
              <span style={{ fontSize: 11, color: fields[f] ? '#7fd4ae' : '#777' }}>{f}</span>
            </label>
          ))}
        </div>
      </div>
    </div>
  )
}
