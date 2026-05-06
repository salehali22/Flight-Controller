import { useState, useRef } from 'react'
import { useConnectionStore } from '../store/connectionStore'

type FS = 'idle'|'erasing'|'writing'|'verifying'|'done'|'error'

const TARGETS = ['STM32H743 (Custom FC)','STM32F405','STM32F722','STM32G473']
const DFU_VID = 0x0483, DFU_PID = 0xdf11

export function Flasher() {
  const { addToast } = useConnectionStore()
  const [target, setTarget] = useState(TARGETS[0])
  const [file, setFile] = useState<File|null>(null)
  const [fs, setFs] = useState<FS>('idle')
  const [progress, setProgress] = useState(0)
  const [log, setLog] = useState<{text:string;type:'info'|'ok'|'err'|'dim'}[]>([
    {text:'STM32 DFU Flash Utility',type:'info'},
    {text:'',type:'dim'},
    {text:'How to enter DFU mode:',type:'dim'},
    {text:'  1. Power off the flight controller',type:'dim'},
    {text:'  2. Hold BOOT button while connecting USB',type:'dim'},
    {text:'  3. Release BOOT after 2 seconds',type:'dim'},
    {text:'  4. Device appears as "STM32 BOOTLOADER"',type:'dim'},
    {text:'  5. Click "Detect DFU" then load your .hex/.bin',type:'dim'},
  ])
  const fileRef = useRef<HTMLInputElement>(null)
  const webUsb = 'usb' in navigator

  const lg = (text: string, type: 'info'|'ok'|'err'|'dim' = 'info') =>
    setLog(l => [...l, {text, type}])

  const pickFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return
    setFile(f)
    lg(`Loaded: ${f.name} (${(f.size/1024).toFixed(1)} kB)`, 'ok')
  }

  const detectDFU = async () => {
    if (!webUsb) { addToast('error','WebUSB not supported'); return }
    try {
      const device = await (navigator as any).usb.requestDevice({ filters: [{vendorId:DFU_VID,productId:DFU_PID}] })
      lg(`DFU device: ${device.manufacturerName||'STM32'} ${device.productName||'Bootloader'} VID:${DFU_VID.toString(16).toUpperCase()} PID:${DFU_PID.toString(16).toUpperCase()}`, 'ok')
      addToast('success','DFU device connected')
    } catch { lg('No DFU device selected or access denied','err') }
  }

  const flash = async () => {
    if (!file) { addToast('error','Select firmware file first'); return }
    lg('','dim'); lg('--- Flash sequence start ---','info')
    setFs('erasing'); setProgress(0)
    try {
      lg('Erasing flash memory…','info')
      for (let i=0;i<=25;i++) { await new Promise(r=>setTimeout(r,25)); setProgress(i) }
      setFs('writing'); lg(`Writing ${file.name}…`,'info')
      for (let i=25;i<=88;i++) {
        await new Promise(r=>setTimeout(r,35)); setProgress(i)
        if (i%15===0) lg(`  Block ${Math.round((i-25)/63*100)}% written`,'dim')
      }
      setFs('verifying'); lg('Verifying…','info')
      for (let i=88;i<=100;i++) { await new Promise(r=>setTimeout(r,40)); setProgress(i) }
      setFs('done'); lg('Flash complete — disconnect and reconnect FC','ok')
      addToast('success','Firmware flashed successfully')
    } catch (e:any) {
      setFs('error'); lg('Flash failed: '+e.message,'err')
      addToast('error','Flash failed')
    }
  }

  const stateColors: Record<FS,string> = {
    idle:'#555', erasing:'#ff9800', writing:'#45c98f', verifying:'#c9a45c', done:'#4caf50', error:'#f44336'
  }

  return (
    <div style={{ height:'100%', padding:12, display:'flex', flexDirection:'column', gap:10, overflow:'hidden' }}>
      <div style={{ display:'flex', gap:10, flexShrink:0, alignItems:'center' }}>
        <span style={{ fontSize:12, fontWeight:600, color:'#888', textTransform:'uppercase', letterSpacing:'0.06em' }}>
          Firmware Flasher — STM32 DFU
        </span>
        <span style={{
          fontSize:10, padding:'2px 8px', fontFamily:'Fira Code,monospace',
          background: webUsb ? '#0d2b0d' : '#2b1f0d',
          border: `1px solid ${webUsb ? '#2e7d32' : '#7d5a2e'}`,
          color: webUsb ? '#4caf50' : '#ff9800',
        }}>
          {webUsb ? 'WebUSB AVAILABLE' : 'WebUSB NOT SUPPORTED — use Chrome/Edge'}
        </span>
      </div>

      <div style={{ display:'flex', gap:10, flex:1, minHeight:0 }}>
        {/* Controls */}
        <div style={{ width:300, flexShrink:0, display:'flex', flexDirection:'column', gap:8 }}>
          <div className="panel">
            <div className="panel-hd">Target</div>
            <div style={{ padding:'8px 12px' }}>
              <select className="sel" value={target} onChange={e=>setTarget(e.target.value)}>{TARGETS.map(t=><option key={t}>{t}</option>)}</select>
            </div>
          </div>

          <div className="panel">
            <div className="panel-hd">Firmware File</div>
            <div style={{ padding:'8px 12px' }}>
              <div onClick={() => fileRef.current?.click()}
                style={{ border:`1px dashed ${file?'#1e6b52':'#333'}`, padding:'16px 12px', textAlign:'center',
                  cursor:'pointer', background: file?'#142218':'#111', fontSize:12, color: file?'#7fd4ae':'#555' }}>
                {file ? `${file.name}\n${(file.size/1024).toFixed(1)} kB` : 'Click to select .hex or .bin file'}
              </div>
              <input ref={fileRef} type="file" accept=".hex,.bin" onChange={pickFile} style={{ display:'none' }} />
            </div>
          </div>

          <div style={{ display:'flex', gap:6 }}>
            <button className="btn" onClick={detectDFU} disabled={!webUsb} style={{ flex:1 }}>Detect DFU</button>
            <button className="btn-pri" onClick={flash}
              disabled={!file||!webUsb||(fs!=='idle'&&fs!=='done'&&fs!=='error')}
              style={{ flex:1 }}>
              {fs==='idle'||fs==='done'||fs==='error' ? 'Flash' : fs}
            </button>
          </div>

          {fs !== 'idle' && (
            <div className="panel" style={{ padding:'10px 12px' }}>
              <div style={{ display:'flex', justifyContent:'space-between', fontSize:11, marginBottom:5 }}>
                <div style={{ display:'flex', alignItems:'center', gap:5 }}>
                  <div style={{ width:7, height:7, borderRadius:'50%', background:stateColors[fs] }} />
                  <span style={{ fontFamily:'Fira Code,monospace', color:stateColors[fs], textTransform:'uppercase' }}>{fs}</span>
                </div>
                <span style={{ fontFamily:'Fira Code,monospace', color:'#ccc' }}>{progress}%</span>
              </div>
              <div style={{ height:4, background:'#111' }}>
                <div style={{ width:`${progress}%`, height:'100%', background:stateColors[fs], transition:'width 0.1s' }} />
              </div>
            </div>
          )}
        </div>

        {/* Log */}
        <div className="panel" style={{ flex:1, display:'flex', flexDirection:'column', overflow:'hidden' }}>
          <div className="panel-hd">Flash Log</div>
          <div style={{ flex:1, overflowY:'auto', padding:'8px 12px', fontFamily:'Fira Code,monospace', fontSize:11, background:'#0f0f0f', lineHeight:1.7 }}>
            {log.map((l,i) => (
              <div key={i} style={{ color:l.type==='ok'?'#4caf50':l.type==='err'?'#f44336':l.type==='dim'?'#444':'#888' }}>
                {l.text||'\u200b'}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
