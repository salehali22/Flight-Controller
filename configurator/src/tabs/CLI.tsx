import { useState, useRef, useEffect, useCallback } from 'react'
import { useConnectionStore } from '../store/connectionStore'
import { getActiveConnection } from '../store/connectionStore'

const QUICK = ['diff all','dump','save','defaults','version','status','get gyro_update_hz','tasks']

export function CLI() {
  const { state, addToast } = useConnectionStore()
  const [lines, setLines] = useState<string[]>(['FC Configurator CLI — type "help" for commands',''])
  const [input, setInput] = useState('')
  const [hist, setHist] = useState<string[]>([])
  const [histIdx, setHistIdx] = useState(-1)
  const [cliOn, setCLIOn] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const connected = state === 'connected'

  const append = useCallback((t: string) => setLines(p => [...p, ...t.split('\n')]), [])

  const enter = async () => {
    if (!connected) { addToast('error','Not connected'); return }
    try {
      const c = getActiveConnection()
      c.onCliData = (t: string) => append(t)
      await c.enterCLI()
      setCLIOn(true)
      append('# Entered CLI — type "exit" to return to MSP')
      setTimeout(() => inputRef.current?.focus(), 50)
    } catch (e: any) { addToast('error','CLI enter failed: ' + e.message) }
  }

  const exitCLI = async () => {
    try { await getActiveConnection().exitCLI(); setCLIOn(false); append('# CLI closed') } catch {}
  }

  const send = async (cmd: string) => {
    if (!cmd.trim() || !cliOn) return
    if (cmd === 'exit') { exitCLI(); return }
    append(`# ${cmd}`)
    setHist(h => [cmd, ...h.slice(0,49)]); setHistIdx(-1); setInput('')
    try { await getActiveConnection().sendCLICommand(cmd) }
    catch { append('Error: command failed') }
  }

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') { send(input); return }
    if (e.key === 'ArrowUp') { e.preventDefault(); const i = Math.min(histIdx+1, hist.length-1); setHistIdx(i); setInput(hist[i]??'') }
    if (e.key === 'ArrowDown') { e.preventDefault(); const i = Math.max(histIdx-1,-1); setHistIdx(i); setInput(i===-1?'':hist[i]??'') }
  }

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'auto' }) }, [lines])

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', padding: 12, gap: 8, overflow: 'hidden' }}>
      {/* Toolbar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
        {!cliOn
          ? <button className="btn-pri" onClick={enter} disabled={!connected} style={{ padding: '4px 14px' }}>Enter CLI</button>
          : <button className="btn-danger" onClick={exitCLI} style={{ padding: '4px 14px' }}>Exit CLI</button>
        }
        <button className="btn" onClick={() => setLines([])} style={{ padding: '4px 10px' }}>Clear</button>
        {cliOn && (
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', flex: 1 }}>
            {QUICK.map(q => (
              <button key={q} onClick={() => send(q)} className="btn"
                style={{ fontFamily: 'Fira Code, monospace', fontSize: 10, padding: '3px 8px' }}>
                {q}
              </button>
            ))}
          </div>
        )}
        {cliOn && (
          <span style={{ fontFamily: 'Fira Code, monospace', fontSize: 10, color: '#4caf50',
            border: '1px solid #2e7d32', padding: '2px 7px', background: '#0d2b0d', marginLeft: 'auto' }}>
            CLI ACTIVE
          </span>
        )}
      </div>

      {/* Terminal */}
      <div className="panel" style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ flex: 1, overflowY: 'auto', padding: '8px 12px',
          fontFamily: 'Fira Code, monospace', fontSize: 12, lineHeight: 1.5, background: '#0f0f0f',
          cursor: cliOn ? 'text' : 'default' }}
          onClick={() => cliOn && inputRef.current?.focus()}
        >
          {lines.map((l, i) => (
            <div key={i} style={{ color: l.startsWith('#') ? '#45c98f' : l.startsWith('Error') ? '#f44336' : '#aaa', whiteSpace: 'pre-wrap' }}>
              {l || '\u200b'}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div style={{ display: 'flex', alignItems: 'center', borderTop: '1px solid #2e2e2e',
          padding: '5px 12px', gap: 6, background: '#111' }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: '#45c98f', userSelect: 'none' }}>#</span>
          <input ref={inputRef} value={input} onChange={e => setInput(e.target.value)} onKeyDown={onKey}
            disabled={!cliOn}
            placeholder={cliOn ? 'Type command and press Enter…' : 'Click "Enter CLI" first'}
            style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none',
              fontFamily: 'Fira Code, monospace', fontSize: 12, color: '#ccc',
              cursor: cliOn ? 'text' : 'not-allowed' }}
          />
          <button onClick={() => send(input)} disabled={!cliOn || !input.trim()}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#45c98f', fontSize: 14,
              opacity: (!cliOn || !input.trim()) ? 0.3 : 1 }}>
            ↵
          </button>
        </div>
      </div>
    </div>
  )
}
