import { useState, useEffect } from 'react'
import { Plug, PlugZap, RefreshCw, ChevronDown, Wifi, WifiOff } from 'lucide-react'
import { useConnectionStore } from '../store/connectionStore'
import { useTelemetryStore } from '../store/telemetryStore'

export function TopBar() {
  const {
    state, portName, baudRate, simulateMode, fcInfo,
    setBaudRate, setSimulateMode, connect, disconnect,
    requestPort, addToast, availablePorts, refreshPorts,
  } = useConnectionStore()
  const { status } = useTelemetryStore()
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [selectedPort, setSelectedPort] = useState<SerialPort | null>(null)

  useEffect(() => { refreshPorts() }, [])

  const webSerialSupported = 'serial' in navigator

  const handleConnect = async () => {
    if (simulateMode) {
      await connect()
      return
    }
    const port = await requestPort()
    if (!port) return
    setSelectedPort(port)
    await connect(port)
  }

  const isConnected = state === 'connected'
  const isConnecting = state === 'connecting'

  return (
    <header className="h-14 bg-bg-primary/95 backdrop-blur border-b border-white/5
                       flex items-center px-4 gap-4 shrink-0 z-30">

      {/* Connection section */}
      <div className="flex items-center gap-3">
        {/* WebSerial warning */}
        {!webSerialSupported && (
          <div className="flex items-center gap-2 text-yellow-400 text-xs font-medium
                          bg-yellow-400/10 border border-yellow-400/20 px-3 py-1.5 rounded-lg">
            <WifiOff size={13} />
            WebSerial not supported — use Chrome/Edge
          </div>
        )}

        {/* Simulate toggle */}
        <label className="flex items-center gap-2 cursor-pointer select-none group">
          <div className="relative">
            <input
              type="checkbox"
              checked={simulateMode}
              onChange={(e) => {
                if (isConnected) return
                setSimulateMode(e.target.checked)
              }}
              disabled={isConnected}
              className="sr-only"
            />
            <div className={`w-8 h-4 rounded-full border transition-all duration-200
                            ${simulateMode
                              ? 'bg-cyan-500/30 border-cyan-500/50'
                              : 'bg-bg-elevated border-white/10'}`} />
            <div className={`absolute top-0.5 left-0.5 w-3 h-3 rounded-full transition-all duration-200 shadow
                            ${simulateMode ? 'translate-x-4 bg-cyan-400' : 'bg-text-muted'}`} />
          </div>
          <span className={`text-xs font-medium ${simulateMode ? 'text-cyan-400' : 'text-text-muted'}`}>
            SIM
          </span>
        </label>

        {/* Baud rate */}
        {!simulateMode && !isConnected && (
          <select
            value={baudRate}
            onChange={(e) => setBaudRate(Number(e.target.value))}
            className="select-field text-xs h-8 pr-6"
          >
            {[9600, 57600, 115200, 230400, 460800, 921600].map((b) => (
              <option key={b} value={b}>{b.toLocaleString()}</option>
            ))}
          </select>
        )}

        {/* Connect/Disconnect */}
        {!isConnected ? (
          <button
            onClick={handleConnect}
            disabled={isConnecting || (!webSerialSupported && !simulateMode)}
            className="btn-primary h-8 px-4 text-xs flex items-center gap-2"
          >
            {isConnecting ? (
              <RefreshCw size={13} className="animate-spin" />
            ) : (
              <Plug size={13} />
            )}
            {isConnecting ? 'Connecting…' : simulateMode ? 'Start Simulation' : 'Connect'}
          </button>
        ) : (
          <button
            onClick={disconnect}
            className="btn-danger h-8 px-4 text-xs flex items-center gap-2"
          >
            <PlugZap size={13} />
            Disconnect
          </button>
        )}
      </div>

      {/* Divider */}
      <div className="w-px h-6 bg-white/10" />

      {/* Connection status */}
      <div className="flex items-center gap-2">
        <div className={`glow-dot ${
          state === 'connected' ? 'bg-green-400 text-green-400' :
          state === 'connecting' ? 'bg-yellow-400 text-yellow-400' :
          state === 'error' ? 'bg-red-400 text-red-400' :
          'bg-text-muted text-text-muted'
        }`} />
        <span className="text-xs font-mono text-text-secondary">
          {state === 'connected' ? portName : state.toUpperCase()}
        </span>
      </div>

      {/* FC Info */}
      {fcInfo && (
        <>
          <div className="w-px h-6 bg-white/10" />
          <div className="flex items-center gap-3 text-xs">
            <span className="font-mono text-accent-blue font-semibold">{fcInfo.boardId}</span>
            <span className="text-text-muted">{fcInfo.fcVariant} {fcInfo.fcVersion}</span>
            <span className="text-text-muted">API {fcInfo.apiVersion}</span>
          </div>
        </>
      )}

      {/* Spacer */}
      <div className="flex-1" />

      {/* CPU + Armed status */}
      {status && (
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-xs text-text-muted">
            <span className="font-mono">CPU</span>
            <div className="w-16 h-1.5 bg-bg-elevated rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  status.cpuLoad > 80 ? 'bg-red-400' : status.cpuLoad > 50 ? 'bg-yellow-400' : 'bg-green-400'
                }`}
                style={{ width: `${Math.min(100, status.cpuLoad)}%` }}
              />
            </div>
            <span className="font-mono">{status.cpuLoad}%</span>
          </div>

          <div
            className={`flex items-center gap-2 px-3 py-1 rounded-lg text-xs font-bold tracking-wider
                        transition-all duration-300 ${
              status.armed
                ? 'bg-green-500/20 border border-green-500/40 text-green-400 shadow-glow-green'
                : 'bg-bg-elevated border border-white/10 text-text-muted'
            }`}
          >
            {status.armed ? <Wifi size={12} /> : <WifiOff size={12} />}
            {status.armed ? 'ARMED' : 'DISARMED'}
          </div>
        </div>
      )}
    </header>
  )
}
