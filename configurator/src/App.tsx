import { Routes, Route, Navigate, NavLink } from 'react-router-dom'
import { ToastContainer } from './components/Toast'
import { ConnectionBar } from './components/ConnectionBar'
import { StatusBar } from './components/StatusBar'
import { Setup } from './tabs/Setup'
import { Ports } from './tabs/Ports'
import { Configuration } from './tabs/Configuration'
import { Receiver } from './tabs/Receiver'
import { Modes } from './tabs/Modes'
import { Motors } from './tabs/Motors'
import { PIDTuning } from './tabs/PIDTuning'
import { Filters } from './tabs/Filters'
import { Failsafe } from './tabs/Failsafe'
import { Blackbox } from './tabs/Blackbox'
import { CLI } from './tabs/CLI'
import { Flasher } from './tabs/Flasher'

const TABS = [
  { to: '/setup', label: 'Setup' },
  { to: '/ports', label: 'Ports' },
  { to: '/configuration', label: 'Configuration' },
  { to: '/receiver', label: 'Receiver' },
  { to: '/modes', label: 'Modes' },
  { to: '/motors', label: 'Motors' },
  { to: '/pid', label: 'PID Tuning' },
  { to: '/filters', label: 'Filters' },
  { to: '/failsafe', label: 'Failsafe' },
  { to: '/blackbox', label: 'Blackbox' },
  { to: '/cli', label: 'CLI' },
  { to: '/flasher', label: 'Flasher' },
]

/** Left rail — green accent (SAL FC) */
const navInactive = { background: '#2b2b2b', color: '#b8b8b8' }
const navActive = { background: '#2a322e', color: '#45c98f' }

export default function App() {
  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--sal-bg)', overflow: 'hidden' }}>
      {/* Top bar — logo + connection (like BF header strip) */}
      <div
        style={{
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          padding: '0 10px',
          height: 40,
          gap: 14,
          background: '#222',
          borderBottom: '1px solid #111',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="2.5" fill="#45c98f" />
            <line x1="12" y1="3" x2="12" y2="7" stroke="#45c98f" strokeWidth="1.5" />
            <line x1="12" y1="17" x2="12" y2="21" stroke="#45c98f" strokeWidth="1.5" />
            <line x1="3" y1="12" x2="7" y2="12" stroke="#45c98f" strokeWidth="1.5" />
            <line x1="17" y1="12" x2="21" y2="12" stroke="#45c98f" strokeWidth="1.5" />
          </svg>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 700, color: '#eee', letterSpacing: '0.04em' }}>
            SAL FC
          </span>
        </div>
        <div style={{ width: 1, height: 22, background: '#444', flexShrink: 0 }} />
        <ConnectionBar />
      </div>

      {/* Body: left nav + main */}
      <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'row', overflow: 'hidden' }}>
        <nav
          style={{
            width: 200,
            flexShrink: 0,
            background: '#2b2b2b',
            borderRight: '1px solid #1a1a1a',
            display: 'flex',
            flexDirection: 'column',
            paddingTop: 4,
            overflowY: 'auto',
          }}
        >
          {TABS.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/setup'}
              style={({ isActive }) => ({
                display: 'block',
                padding: '9px 14px 9px 11px',
                fontSize: 12,
                fontWeight: isActive ? 600 : 500,
                textDecoration: 'none',
                borderLeft: isActive ? '4px solid #45c98f' : '4px solid transparent',
                ...(isActive ? navActive : navInactive),
              })}
            >
              {label}
            </NavLink>
          ))}
        </nav>

        <div style={{ flex: 1, minWidth: 0, overflow: 'hidden', background: 'var(--sal-bg)' }}>
          <Routes>
            <Route path="/" element={<Navigate to="/setup" replace />} />
            <Route path="/setup" element={<Setup />} />
            <Route path="/ports" element={<Ports />} />
            <Route path="/configuration" element={<Configuration />} />
            <Route path="/receiver" element={<Receiver />} />
            <Route path="/modes" element={<Modes />} />
            <Route path="/motors" element={<Motors />} />
            <Route path="/pid" element={<PIDTuning />} />
            <Route path="/filters" element={<Filters />} />
            <Route path="/failsafe" element={<Failsafe />} />
            <Route path="/blackbox" element={<Blackbox />} />
            <Route path="/cli" element={<CLI />} />
            <Route path="/flasher" element={<Flasher />} />
          </Routes>
        </div>
      </div>

      <StatusBar />
      <ToastContainer />
    </div>
  )
}
