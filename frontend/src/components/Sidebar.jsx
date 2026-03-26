import { NavLink } from 'react-router-dom'
import { LayoutDashboard, TrendingUp, FlaskConical, Bell, Settings } from 'lucide-react'
import { LiveBadge } from './UI'

const NAV = [
  { to: '/',          icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/signals',   icon: TrendingUp,      label: 'Signals'   },
  { to: '/backtest',  icon: FlaskConical,    label: 'Backtest'  },
  { to: '/alerts',    icon: Bell,            label: 'Alerts'    },
  { to: '/settings',  icon: Settings,        label: 'Settings'  },
]

export default function Sidebar({ watchlist, onWatchlistChange }) {
  return (
    <aside className="fixed left-0 top-0 h-screen w-56 border-r border-white/8 flex flex-col z-50"
      style={{ background: '#0d1421' }}>

      {/* Logo */}
      <div className="px-5 py-5 border-b border-white/8">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center font-mono font-bold text-sm"
            style={{ background: 'linear-gradient(135deg,#00C896,#3B82F6)', color: '#fff' }}>
            α
          </div>
          <div>
            <div className="font-mono text-sm font-bold text-white tracking-wide">AlphaSignal</div>
            <div className="text-xs text-white/40">ML Platform v2.4</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink key={to} to={to} end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150 font-mono
              ${isActive
                ? 'bg-green-500/10 text-green-400 border border-green-500/20'
                : 'text-white/50 hover:text-white/80 hover:bg-white/5'}`}>
            <Icon size={15}/>
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Bottom status */}
      <div className="px-5 py-4 border-t border-white/8 space-y-2">
        <LiveBadge text="LIVE DATA"/>
        <div className="text-xs text-white/30 font-mono">
          {new Date().toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit'})} EST
        </div>
      </div>
    </aside>
  )
}
