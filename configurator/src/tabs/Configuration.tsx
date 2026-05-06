import { useState } from 'react'
import { useFCStore } from '../store/fcStore'
import { useConnectionStore } from '../store/connectionStore'
import { setFeatureConfig } from '../msp/MSPCommands'
import { MotorDiagram } from '../components/MotorDiagram'
import { MIXER_MOTORS } from '../components/ThreeDModel'

const MIXERS = [
  'MONO','BI','TRI','QUADP','QUADX','Y4','Y6','HEX6','HEX6X','OCTOX','OCTOFLATX',
]
const ESC_PROTOCOLS = ['PWM','OneShot125','OneShot42','Multishot','DShot150','DShot300','DShot600']
const GYRO_FREQS    = ['8kHz','4kHz','2kHz','1kHz']
const ALIGNMENTS    = ['CW 0°','CW 90°','CW 180°','CW 270°']
const RX_MODES      = ['Serial (SBUS/CRSF/IBUS)','PPM','SPI/NRF24']

const FEATURES: [string, number, string][] = [
  ['MOTOR_STOP',   0x0001, 'Cut motors when disarmed'],
  ['AIRMODE',      0x4000, 'Full PID authority at zero throttle'],
  ['GPS',          0x0020, 'Enable GPS module'],
  ['TELEMETRY',    0x0400, 'Downlink telemetry data'],
  ['OSD',          0x2000, 'On-screen display'],
  ['BLACKBOX',     0x0080, 'Flight data logger'],
  ['LED_STRIP',    0x0100, 'RGB LED strip'],
  ['ANTI_GRAVITY', 0x8000, 'Anti-gravity on throttle chop'],
  ['SOFTSERIAL',   0x0008, 'Software serial ports'],
]

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="panel" style={{ marginBottom: 10 }}>
      <div className="panel-hd">{title}</div>
      <div style={{ padding: '10px 12px' }}>{children}</div>
    </div>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8, gap: 10 }}>
      <span style={{ fontSize: 12, color: '#777', width: 150, flexShrink: 0 }}>{label}</span>
      {children}
    </div>
  )
}

export function Configuration() {
  const { mixerType, escProtocol, features, setMixerType, setEscProtocol, setFeatures } = useFCStore()
  const { state, addToast } = useConnectionStore()
  const connected = state === 'connected'

  const [mixer, setMixer] = useState(mixerType)
  const [esc, setEsc] = useState(escProtocol)
  const [feats, setFeats] = useState(features)
  const [gyroFreq, setGyroFreq] = useState('8kHz')
  const [pidFreq, setPidFreq] = useState('8kHz')
  const [gyroAlign, setGyroAlign] = useState('CW 0°')
  const [accAlign, setAccAlign] = useState('CW 0°')
  const [rxMode, setRxMode] = useState(RX_MODES[0])
  const [armAngle, setArmAngle] = useState(25)

  const toggleFeat = (bit: number) => setFeats(f => f ^ bit)

  const save = async () => {
    try {
      await setFeatureConfig(feats)
      setFeatures(feats); setMixerType(mixer); setEscProtocol(esc)
      addToast('success', 'Saved — reboot recommended')
    } catch { addToast('error', 'Save failed') }
  }

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* ── Left: settings ── */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 12 }}>

        <Section title="Mixer / Craft Type">
          <Row label="Craft Type">
            <select className="sel" style={{ width: 160 }} value={mixer} onChange={e => setMixer(e.target.value)}>
              {MIXERS.map(m => <option key={m}>{m}</option>)}
            </select>
          </Row>
          <Row label="ESC Protocol">
            <select className="sel" style={{ width: 160 }} value={esc} onChange={e => setEsc(e.target.value)}>
              {ESC_PROTOCOLS.map(p => <option key={p}>{p}</option>)}
            </select>
          </Row>
        </Section>

        <Section title="Loop Rates">
          <Row label="Gyro Update">
            <select className="sel" style={{ width: 120 }} value={gyroFreq} onChange={e => setGyroFreq(e.target.value)}>
              {GYRO_FREQS.map(f => <option key={f}>{f}</option>)}
            </select>
          </Row>
          <Row label="PID Loop">
            <select className="sel" style={{ width: 120 }} value={pidFreq} onChange={e => setPidFreq(e.target.value)}>
              {GYRO_FREQS.map(f => <option key={f}>{f}</option>)}
            </select>
          </Row>
        </Section>

        <Section title="Sensor Alignment">
          <Row label="Gyro Alignment">
            <select className="sel" style={{ width: 140 }} value={gyroAlign} onChange={e => setGyroAlign(e.target.value)}>
              {ALIGNMENTS.map(a => <option key={a}>{a}</option>)}
            </select>
          </Row>
          <Row label="Acc Alignment">
            <select className="sel" style={{ width: 140 }} value={accAlign} onChange={e => setAccAlign(e.target.value)}>
              {ALIGNMENTS.map(a => <option key={a}>{a}</option>)}
            </select>
          </Row>
        </Section>

        <Section title="Receiver &amp; Arming">
          <Row label="Receiver Mode">
            <select className="sel" style={{ width: 200 }} value={rxMode} onChange={e => setRxMode(e.target.value)}>
              {RX_MODES.map(m => <option key={m}>{m}</option>)}
            </select>
          </Row>
          <Row label={`Max Arm Angle: ${armAngle}°`}>
            <input type="range" min={5} max={180} value={armAngle} onChange={e => setArmAngle(+e.target.value)}
              style={{ width: 180 }} />
          </Row>
        </Section>

        <Section title="Features">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
            {FEATURES.map(([name, bit, desc]) => {
              const on = (feats & bit) !== 0
              return (
                <label key={name} onClick={() => toggleFeat(bit)}
                  style={{
                    display: 'flex', alignItems: 'flex-start', gap: 8, cursor: 'pointer', padding: '6px 8px',
                    border: `1px solid ${on ? '#1e6b52' : '#2a2a2a'}`,
                    background: on ? '#0d1a2b' : '#181818',
                  }}
                >
                  <input type="checkbox" checked={on} onChange={() => {}} style={{ marginTop: 2 }} />
                  <div>
                    <div style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: on ? '#7fd4ae' : '#888', fontWeight: 600 }}>{name}</div>
                    <div style={{ fontSize: 10, color: '#555', marginTop: 1 }}>{desc}</div>
                  </div>
                </label>
              )
            })}
          </div>
        </Section>

        <div style={{ display: 'flex', justifyContent: 'flex-end', paddingBottom: 12 }}>
          <button className="btn-pri" onClick={save} disabled={!connected}>Save &amp; Apply</button>
        </div>
      </div>

      {/* ── Right: motor diagram ── */}
      <div style={{ width: 280, flexShrink: 0, borderLeft: '1px solid #2e2e2e', background: '#1a1a1a', display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 20, gap: 16 }}>
        <div style={{ fontSize: 11, color: '#666', fontFamily: 'Fira Code, monospace', textTransform: 'uppercase', letterSpacing: '0.08em', alignSelf: 'flex-start' }}>
          Motor Layout — {mixer}
        </div>
        <MotorDiagram mixerType={mixer} size={240} />
        <div style={{ alignSelf: 'flex-start', fontSize: 10, color: '#555' }}>
          Motor count: {(MIXER_MOTORS[mixer] ?? []).length}
        </div>
      </div>
    </div>
  )
}
