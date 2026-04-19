import { useState, useEffect } from 'react'
import { getSerialConfig } from '../msp/MSPCommands'
import { useConnectionStore, getActiveConnection } from '../store/connectionStore'
import { MSP_CODES, encodeUint16LE } from '../msp/MSPProtocol'

const FUNCTIONS: [string, number][] = [
  ['Disabled',0],['MSP',1],['GPS',2],['Telemetry',8],
  ['RX Serial',64],['VTX',512],['ESC Sensor',1024],['Blackbox',128],
]
const BAUDS = ['Auto','9600','19200','38400','57600','115200','230400','250000']

interface Port { id: number; name: string; fnMask: number; mspBaud: number }

const DEFAULT: Port[] = Array.from({length:6}, (_,i) => ({
  id: i, name: `UART${i+1}`, fnMask: i === 0 ? 1 : 0, mspBaud: 3
}))

export function Ports() {
  const { state, addToast } = useConnectionStore()
  const [ports, setPorts] = useState<Port[]>(DEFAULT)
  const connected = state === 'connected'

  useEffect(() => {
    if (!connected) return
    getSerialConfig().then(cfg => {
      if (cfg.length) setPorts(cfg.map(p => ({ id: p.identifier, name: `UART${p.identifier+1}`, fnMask: p.functionMask, mspBaud: p.mspBaudRate })))
    }).catch(() => {})
  }, [connected])

  const upd = (id: number, k: keyof Port, v: any) =>
    setPorts(prev => prev.map(p => p.id === id ? {...p, [k]: v} : p))

  const save = async () => {
    try {
      const conn = getActiveConnection()
      const data: number[] = []
      ports.forEach(p => { data.push(p.id); data.push(...encodeUint16LE(p.fnMask)); data.push(p.mspBaud,1,0,0) })
      await conn.send(MSP_CODES.SET_SERIAL_CONFIG, new Uint8Array(data))
      await conn.send(MSP_CODES.EEPROM_WRITE)
      addToast('success', 'Port config saved')
    } catch { addToast('error', 'Save failed') }
  }

  return (
    <div style={{ padding: 12, overflowY: 'auto', height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 10 }}>
        <button className="btn-pri" onClick={save} disabled={!connected}>Save &amp; Apply</button>
      </div>
      <div className="panel">
        <table className="tool-table">
          <thead>
            <tr>
              <th>Port</th><th>Function</th><th>MSP Baud</th><th>GPS Baud</th><th>Telemetry Baud</th>
            </tr>
          </thead>
          <tbody>
            {ports.map(p => (
              <tr key={p.id}>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <div className={`led ${p.fnMask > 0 ? 'led-blue' : 'led-off'}`} style={{ width: 6, height: 6 }} />
                    <span style={{ fontFamily: 'Fira Code, monospace', fontSize: 12 }}>{p.name}</span>
                    {p.id === 0 && <span style={{ fontSize: 10, padding: '1px 5px', background: '#142218', border: '1px solid #1e6b52', color: '#7fd4ae' }}>USB</span>}
                  </div>
                </td>
                <td>
                  <select className="sel" style={{ width: 140 }} value={p.fnMask} onChange={e => upd(p.id, 'fnMask', +e.target.value)}>
                    {FUNCTIONS.map(([n,v]) => <option key={n} value={v}>{n}</option>)}
                  </select>
                </td>
                <td>
                  <select className="sel" style={{ width: 110 }} value={p.mspBaud} onChange={e => upd(p.id, 'mspBaud', +e.target.value)}>
                    {BAUDS.map((b,i) => <option key={b} value={i}>{b}</option>)}
                  </select>
                </td>
                <td><select className="sel" style={{ width: 110 }}>{BAUDS.map((b,i) => <option key={b} value={i}>{b}</option>)}</select></td>
                <td><select className="sel" style={{ width: 110 }}>{BAUDS.map((b,i) => <option key={b} value={i}>{b}</option>)}</select></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
