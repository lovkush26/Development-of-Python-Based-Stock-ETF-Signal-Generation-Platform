import { signalColor } from '../utils/format'

// ── Card ──────────────────────────────────────────────────────────────────────
export function Card({ children, className = '' }) {
  return (
    <div className={`rounded-xl border border-white/10 bg-white/5 p-4 ${className}`}>
      {children}
    </div>
  )
}

// ── Signal badge ──────────────────────────────────────────────────────────────
export function SignalBadge({ signal }) {
  const c = signalColor(signal)
  return (
    <span className="font-mono text-xs font-bold px-2 py-1 rounded-md"
      style={{ color: c.text, background: c.bg, border: `1px solid ${c.border}` }}>
      {signal}
    </span>
  )
}

// ── Metric card ───────────────────────────────────────────────────────────────
export function Metric({ label, value, delta, deltaColor }) {
  const dc = deltaColor || (delta && (delta.startsWith('+') ? '#00C896' : delta.startsWith('-') ? '#FF4D6A' : '#F5A623'))
  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-4">
      <p className="text-xs text-white/50 uppercase tracking-widest mb-1 font-mono">{label}</p>
      <p className="text-2xl font-mono font-bold text-white">{value}</p>
      {delta && <p className="text-xs mt-1 font-mono" style={{ color: dc }}>{delta}</p>}
    </div>
  )
}

// ── Spinner ───────────────────────────────────────────────────────────────────
export function Spinner({ size = 16 }) {
  return (
    <div className="spinner rounded-full border-2 border-white/20 border-t-white"
      style={{ width: size, height: size, borderTopColor: '#00C896' }}/>
  )
}

// ── Live badge ────────────────────────────────────────────────────────────────
export function LiveBadge({ text = 'LIVE' }) {
  return (
    <span className="inline-flex items-center gap-1.5 font-mono text-xs px-3 py-1 rounded-full"
      style={{ background: 'rgba(0,200,150,0.12)', border: '1px solid rgba(0,200,150,0.3)', color: '#00C896' }}>
      <span className="pulse-dot w-1.5 h-1.5 rounded-full" style={{ background: '#00C896' }}/>
      {text}
    </span>
  )
}

// ── Button ────────────────────────────────────────────────────────────────────
export function Button({ children, onClick, variant = 'default', disabled, className = '', loading }) {
  const variants = {
    default:  'border border-white/20 text-white/80 hover:bg-white/10',
    primary:  'border border-green-500/40 text-green-400 hover:bg-green-500/10',
    danger:   'border border-red-500/40 text-red-400 hover:bg-red-500/10',
    ghost:    'text-white/50 hover:text-white hover:bg-white/5',
  }
  return (
    <button onClick={onClick} disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2 px-3 py-1.5 rounded-lg text-sm font-mono
        transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed
        ${variants[variant]} ${className}`}>
      {loading && <Spinner size={12}/>}
      {children}
    </button>
  )
}

// ── Table ─────────────────────────────────────────────────────────────────────
export function Table({ columns, rows, onRowClick }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/10">
            {columns.map(c => (
              <th key={c.key} className="px-3 py-2 text-left font-mono text-xs text-white/40 uppercase tracking-wider">
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}
              onClick={() => onRowClick?.(row)}
              className={`border-b border-white/5 transition-colors ${onRowClick ? 'cursor-pointer hover:bg-white/5' : ''}`}>
              {columns.map(c => (
                <td key={c.key} className="px-3 py-2.5">
                  {c.render ? c.render(row[c.key], row) : row[c.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 && (
        <div className="text-center py-8 text-white/30 font-mono text-sm">No data</div>
      )}
    </div>
  )
}

// ── Input ─────────────────────────────────────────────────────────────────────
export function Input({ value, onChange, placeholder, className = '', ...props }) {
  return (
    <input value={value} onChange={onChange} placeholder={placeholder}
      className={`w-full bg-white/5 border border-white/15 rounded-lg px-3 py-2 text-sm text-white
        placeholder-white/30 focus:outline-none focus:border-green-500/50 transition-colors ${className}`}
      {...props}/>
  )
}

// ── Select ────────────────────────────────────────────────────────────────────
export function Select({ value, onChange, options, className = '' }) {
  return (
    <select value={value} onChange={e => onChange(e.target.value)}
      className={`bg-white/5 border border-white/15 rounded-lg px-3 py-2 text-sm text-white
        focus:outline-none focus:border-green-500/50 ${className}`}>
      {options.map(o => <option key={o.value} value={o.value} className="bg-gray-900">{o.label}</option>)}
    </select>
  )
}

// ── Tabs ──────────────────────────────────────────────────────────────────────
export function Tabs({ tabs, active, onChange }) {
  return (
    <div className="flex border-b border-white/10">
      {tabs.map(t => (
        <button key={t.key} onClick={() => onChange(t.key)}
          className={`px-4 py-2.5 text-xs font-mono uppercase tracking-wider transition-colors border-b-2 -mb-px
            ${active === t.key
              ? 'text-green-400 border-green-400'
              : 'text-white/40 border-transparent hover:text-white/60'}`}>
          {t.label}
        </button>
      ))}
    </div>
  )
}

// ── Progress bar ──────────────────────────────────────────────────────────────
export function ProgressBar({ value, max, color = '#00C896' }) {
  const pct = Math.min(100, Math.round((value / max) * 100))
  return (
    <div className="w-full h-1 bg-white/10 rounded-full overflow-hidden">
      <div className="h-full rounded-full transition-all duration-300" style={{ width: `${pct}%`, background: color }}/>
    </div>
  )
}

// ── Slider ────────────────────────────────────────────────────────────────────
export function Slider({ value, min, max, step, onChange, label }) {
  return (
    <div className="flex flex-col gap-1">
      {label && <div className="flex justify-between text-xs text-white/50 font-mono">
        <span>{label}</span><span>{(value * 100).toFixed(0)}%</span>
      </div>}
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="w-full accent-green-400 cursor-pointer"/>
    </div>
  )
}
