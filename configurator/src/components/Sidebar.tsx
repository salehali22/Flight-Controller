import { NavLink } from 'react-router-dom'
import {
  Home, Settings2, Radio, Sliders, Zap, Activity,
  Filter, ShieldAlert, HardDrive, Terminal, Cpu, Usb,
} from 'lucide-react'

const nav = [
  { to: '/setup',         icon: Home,        label: 'Setup' },
  { to: '/ports',         icon: Usb,         label: 'Ports' },
  { to: '/configuration', icon: Settings2,   label: 'Config' },
  { to: '/receiver',      icon: Radio,       label: 'Receiver' },
  { to: '/modes',         icon: Activity,    label: 'Modes' },
  { to: '/motors',        icon: Zap,         label: 'Motors' },
  { to: '/pid',           icon: Sliders,     label: 'PID Tuning' },
  { to: '/filters',       icon: Filter,      label: 'Filters' },
  { to: '/failsafe',      icon: ShieldAlert, label: 'Failsafe' },
  { to: '/blackbox',      icon: HardDrive,   label: 'Blackbox' },
  { to: '/cli',           icon: Terminal,    label: 'CLI' },
  { to: '/flasher',       icon: Cpu,         label: 'Flasher' },
]

export function Sidebar() {
  return (
    <nav className="w-[72px] hover:w-52 group/nav transition-all duration-300 ease-in-out
                    flex flex-col bg-bg-primary border-r border-white/5 shrink-0 overflow-hidden z-20">
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-white/5">
        <div className="w-8 h-8 shrink-0 rounded-lg bg-accent-blue/20 border border-accent-blue/30
                        flex items-center justify-center">
          <svg viewBox="0 0 24 24" className="w-5 h-5 text-accent-blue" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="12" cy="12" r="3" />
            <line x1="12" y1="2" x2="12" y2="6" />
            <line x1="12" y1="18" x2="12" y2="22" />
            <line x1="2" y1="12" x2="6" y2="12" />
            <line x1="18" y1="12" x2="22" y2="12" />
            <circle cx="6" cy="6" r="1.5" fill="currentColor" />
            <circle cx="18" cy="6" r="1.5" fill="currentColor" />
            <circle cx="6" cy="18" r="1.5" fill="currentColor" />
            <circle cx="18" cy="18" r="1.5" fill="currentColor" />
          </svg>
        </div>
        <div className="whitespace-nowrap opacity-0 group-hover/nav:opacity-100 transition-opacity duration-200">
          <span className="text-sm font-bold text-text-primary">FC Config</span>
          <span className="block text-[10px] text-text-muted font-mono">v1.0.0</span>
        </div>
      </div>

      {/* Nav items */}
      <div className="flex-1 py-3 flex flex-col gap-0.5">
        {nav.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 mx-2 px-3 py-2.5 rounded-lg transition-all duration-150 cursor-pointer
               group/item relative
               ${isActive
                 ? 'bg-accent-blue/15 text-accent-blue'
                 : 'text-text-muted hover:text-text-primary hover:bg-bg-elevated'
               }`
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-6 bg-accent-blue rounded-r-full shadow-glow-blue" />
                )}
                <Icon size={18} className="shrink-0" />
                <span className="text-sm font-medium whitespace-nowrap opacity-0
                                 group-hover/nav:opacity-100 transition-opacity duration-200">
                  {label}
                </span>
              </>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
