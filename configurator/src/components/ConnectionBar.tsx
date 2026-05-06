import { useState, useEffect } from 'react'
import { useConnectionStore } from '../store/connectionStore'

export function ConnectionBar() {
  const {
    state, baudRate, simulateMode, fcInfo,
    setBaudRate, setSimulateMode, connect, disconnect, requestPort,
  } = useConnectionStore()

  const isConnected = state === 'connected'
  const isConnecting = state === 'connecting'
  const webSerial = 'serial' in navigator

  const handleConnect = async () => {
    if (simulateMode) { await connect(); return }
    const port = await requestPort()
    if (port) await connect(port)
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1 }}>
      {/* WebSerial warning */}
      {!webSerial && (
        <span style={{ fontSize: 11, color: '#ff9800', background: '#ff980022', border: '1px solid #ff980044', padding: '2px 8px', borderRadius: 2 }}>
          WebSerial requires Chrome/Edge
        </span>
      )}

      {/* SIM toggle */}
      <label style={{ display: 'flex', alignItems: 'center', gap: 5, cursor: isConnected ? 'not-allowed' : 'pointer', opacity: isConnected ? 0.5 : 1 }}>
        <div className={`toggle-track ${simulateMode ? 'on' : ''}`} onClick={() => !isConnected && setSimulateMode(!simulateMode)}>
          <div className="toggle-knob" />
        </div>
        <span style={{ fontSize: 11, color: simulateMode ? '#c9a45c' : '#666', fontFamily: 'var(--font-mono)' }}>SIM</span>
      </label>

      {/* Baud */}
      {!isConnected && !simulateMode && (
        <select
          value={baudRate}
          onChange={e => setBaudRate(Number(e.target.value))}
          className="sel"
          style={{ width: 90 }}
        >
          {[9600,57600,115200,230400,460800,921600].map(b => (
            <option key={b} value={b}>{b}</option>
          ))}
        </select>
      )}

      {/* Connect/Disconnect */}
      {!isConnected ? (
        <button
          className="btn-pri"
          onClick={handleConnect}
          disabled={isConnecting || (!webSerial && !simulateMode)}
        >
          {isConnecting ? 'Connecting…' : simulateMode ? 'Start SIM' : 'Connect'}
        </button>
      ) : (
        <button className="btn-danger" onClick={disconnect}>Disconnect</button>
      )}

      {/* Connection status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginLeft: 4 }}>
        <div className={`led ${
          state === 'connected' ? 'led-green' :
          state === 'connecting' ? 'led-amber' :
          state === 'error' ? 'led-red' : 'led-off'
        }`} />
        <span style={{ fontFamily: 'Fira Code, monospace', fontSize: 11, color: '#888' }}>
          {state === 'connected' ? (simulateMode ? 'SIMULATION' : 'CONNECTED') :
           state === 'connecting' ? 'CONNECTING' :
           state === 'error' ? 'ERROR' : 'NOT CONNECTED'}
        </span>
      </div>

      {/* FC info */}
      {fcInfo && (
        <>
          <div style={{ width: 1, height: 18, background: '#2e2e2e' }} />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: '#45c98f' }}>
            {fcInfo.boardId}
          </span>
          <span style={{ fontFamily: 'Fira Code, monospace', fontSize: 11, color: '#666' }}>
            {fcInfo.fcVariant} {fcInfo.fcVersion} | API {fcInfo.apiVersion}
          </span>
        </>
      )}
    </div>
  )
}
