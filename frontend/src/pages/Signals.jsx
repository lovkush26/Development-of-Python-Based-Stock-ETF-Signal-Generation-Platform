import { useState, useEffect } from 'react'
import { getSignals, searchTickers, addTicker, removeTicker, getWatchlist } from '../utils/api'
import { fmt, signalColor, changeColor } from '../utils/format'
import { Card, SignalBadge, Button, Input, Spinner, ProgressBar } from '../components/UI'
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { Search, Plus, X, RefreshCw } from 'lucide-react'
import PriceChart from '../components/PriceChart'

export default function Signals({ watchlist, onWatchlistChange }) {
  const [signals,    setSignals]    = useState([])
  const [loading,    setLoading]    = useState(false)
  const [filter,     setFilter]     = useState(['BUY','SELL','HOLD'])
  const [sortBy,     setSortBy]     = useState('confidence')
  const [sortAsc,    setSortAsc]    = useState(false)
  const [minConf,    setMinConf]    = useState(0.60)
  const [searchQ,    setSearchQ]    = useState('')
  const [searchRes,  setSearchRes]  = useState([])
  const [searching,  setSearching]  = useState(false)
  const [selected,   setSelected]   = useState(null)
  const [lastRun,    setLastRun]    = useState(null)
  const [progress,   setProgress]   = useState(0)
  const [progressTxt,setProgressTxt]= useState('')

  // Run signals
  const runSignals = async () => {
    if (!watchlist.length) return
    setLoading(true); setProgress(0)
    const results = []
    for (let i = 0; i < watchlist.length; i++) {
      const ticker = watchlist[i]
      setProgress(Math.round(((i+1)/watchlist.length)*100))
      setProgressTxt(`Scanning ${ticker}... (${i+1}/${watchlist.length})`)
      try {
        const res = await getSignals([ticker])
        if (res.data?.length) results.push(...res.data)
      } catch {}
    }
    setSignals(results)
    setLastRun(new Date().toLocaleTimeString())
    setLoading(false); setProgress(0); setProgressTxt('')
  }

  useEffect(() => { if (watchlist.length) runSignals() }, [])
  useEffect(() => { const id = setInterval(runSignals, 300000); return () => clearInterval(id) }, [watchlist.join(',')])

  // Search
  useEffect(() => {
    if (!searchQ.trim() || searchQ.length < 1) { setSearchRes([]); return }
    setSearching(true)
    const t = setTimeout(async () => {
      try { const r = await searchTickers(searchQ); setSearchRes(r.data?.results || []) }
      catch {} finally { setSearching(false) }
    }, 400)
    return () => clearTimeout(t)
  }, [searchQ])

  const handleAdd = async (ticker) => {
    try {
      await addTicker(ticker)
      onWatchlistChange([...watchlist, ticker])
      setSearchQ(''); setSearchRes([])
    } catch (e) { alert(e.response?.data?.detail || 'Failed to add ticker') }
  }

  const handleRemove = async (ticker) => {
    try {
      await removeTicker(ticker)
      onWatchlistChange(watchlist.filter(t => t !== ticker))
      if (selected?.ticker === ticker) setSelected(null)
    } catch {}
  }

  // Filter + sort
  const displayed = signals
    .filter(s => filter.includes(s.signal))
    .sort((a,b) => {
      const av = a[sortBy], bv = b[sortBy]
      return sortAsc ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1)
    })

  const dist = ['BUY','SELL','HOLD'].map(s => ({ name: s, value: signals.filter(x=>x.signal===s).length }))

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Signal Monitor</h1>
        <div className="flex items-center gap-2">
          {lastRun && <span className="text-xs text-white/30 font-mono">Last run: {lastRun}</span>}
          <Button variant="primary" onClick={runSignals} loading={loading} className="gap-1">
            <RefreshCw size={12}/> Run Signals
          </Button>
        </div>
      </div>

      {/* Search bar */}
      <Card>
        <div className="flex items-center gap-3 mb-3">
          <Search size={15} className="text-white/40 shrink-0"/>
          <Input value={searchQ} onChange={e=>setSearchQ(e.target.value)}
            placeholder="Search ticker by name or symbol — e.g. Apple, NVDA, S&P 500..."
            className="flex-1"/>
          {searching && <Spinner size={14}/>}
        </div>

        {searchRes.length > 0 && (
          <div className="border border-white/10 rounded-lg overflow-hidden">
            {searchRes.map(r => {
              const inWl = watchlist.includes(r.symbol)
              return (
                <div key={r.symbol} className="flex items-center gap-3 px-3 py-2.5 border-b border-white/5 last:border-0 hover:bg-white/5">
                  <span className="font-mono font-bold text-sm text-white w-16">{r.symbol}</span>
                  <span className="text-sm text-white/60 flex-1">{r.name}</span>
                  <span className="text-xs text-white/30 font-mono">{r.type}</span>
                  {inWl
                    ? <span className="text-xs text-green-400 font-mono px-2 py-0.5 rounded bg-green-500/10">✓ Added</span>
                    : <Button variant="primary" onClick={()=>handleAdd(r.symbol)} className="text-xs py-1"><Plus size={11}/>Add</Button>
                  }
                </div>
              )
            })}
          </div>
        )}

        {/* Watchlist chips */}
        <div className="flex flex-wrap gap-2 mt-3">
          {watchlist.map(t => (
            <div key={t} className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-white/15 bg-white/5">
              <span className="font-mono text-xs font-bold text-white">{t}</span>
              <button onClick={()=>handleRemove(t)} className="text-white/30 hover:text-red-400 transition-colors">
                <X size={11}/>
              </button>
            </div>
          ))}
        </div>
      </Card>

      {/* Loading progress */}
      {loading && (
        <Card>
          <div className="space-y-2">
            <div className="text-xs text-white/50 font-mono">{progressTxt}</div>
            <ProgressBar value={progress} max={100}/>
          </div>
        </Card>
      )}

      {/* Summary metrics */}
      {signals.length > 0 && (
        <div className="grid grid-cols-4 gap-3">
          {[
            { label:'Total', value: signals.length },
            { label:'BUY',   value: signals.filter(s=>s.signal==='BUY').length,  color:'#00C896' },
            { label:'SELL',  value: signals.filter(s=>s.signal==='SELL').length, color:'#FF4D6A' },
            { label:'HOLD',  value: signals.filter(s=>s.signal==='HOLD').length, color:'#F5A623' },
          ].map(m => (
            <div key={m.label} className="rounded-xl border border-white/10 bg-white/5 p-4">
              <div className="text-xs text-white/40 font-mono uppercase tracking-wider mb-1">{m.label}</div>
              <div className="text-2xl font-bold font-mono" style={{ color: m.color || '#fff' }}>{m.value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Filters + sort */}
      <Card>
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-xs text-white/40 font-mono">SIGNAL:</span>
            {['BUY','SELL','HOLD'].map(s => {
              const c = signalColor(s)
              const on = filter.includes(s)
              return (
                <button key={s} onClick={()=>setFilter(f=>on?f.filter(x=>x!==s):[...f,s])}
                  className="px-2.5 py-1 rounded-md text-xs font-mono font-bold transition-all"
                  style={on
                    ? { color:c.text, background:c.bg, border:`1px solid ${c.border}` }
                    : { color:'rgba(255,255,255,0.3)', background:'transparent', border:'1px solid rgba(255,255,255,0.1)' }}>
                  {s}
                </button>
              )
            })}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-white/40 font-mono">SORT:</span>
            <select value={sortBy} onChange={e=>setSortBy(e.target.value)}
              className="bg-white/5 border border-white/15 rounded-lg px-2 py-1 text-xs text-white font-mono focus:outline-none">
              {['confidence','ticker','rsi','change_pct','volume_ratio'].map(k=>(
                <option key={k} value={k} className="bg-gray-900">{k}</option>
              ))}
            </select>
            <button onClick={()=>setSortAsc(v=>!v)}
              className="text-xs text-white/40 hover:text-white font-mono px-2 py-1 rounded border border-white/10 hover:bg-white/5">
              {sortAsc ? '▲ ASC' : '▼ DESC'}
            </button>
          </div>
          <div className="flex items-center gap-2 ml-auto">
            <span className="text-xs text-white/40 font-mono">MIN CONF:</span>
            <input type="range" min={0.5} max={0.95} step={0.05} value={minConf}
              onChange={e=>setMinConf(Number(e.target.value))}
              className="w-24 accent-green-400"/>
            <span className="text-xs font-mono text-green-400">{(minConf*100).toFixed(0)}%</span>
          </div>
        </div>
      </Card>

      {/* Main layout */}
      <div className="grid grid-cols-3 gap-5">
        {/* Signal table */}
        <Card className="col-span-2">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10">
                  {['Ticker','Signal','Confidence','Price','Change %','RSI','MACD','BB %','Vol Ratio'].map(h=>(
                    <th key={h} className="px-3 py-2 text-left font-mono text-xs text-white/40 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {displayed.map(s => (
                  <tr key={s.ticker} onClick={()=>setSelected(s)}
                    className={`border-b border-white/5 cursor-pointer transition-colors
                      ${selected?.ticker===s.ticker ? 'bg-white/8' : 'hover:bg-white/4'}`}>
                    <td className="px-3 py-2.5 font-mono font-bold text-white">{s.ticker}</td>
                    <td className="px-3 py-2.5"><SignalBadge signal={s.signal}/></td>
                    <td className="px-3 py-2.5">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-white/10 rounded-full overflow-hidden">
                          <div className="h-full rounded-full" style={{
                            width:`${s.confidence*100}%`,
                            background: s.signal==='BUY'?'#00C896':s.signal==='SELL'?'#FF4D6A':'#F5A623'
                          }}/>
                        </div>
                        <span className="font-mono text-xs text-white/70">{fmt.conf(s.confidence)}</span>
                      </div>
                    </td>
                    <td className="px-3 py-2.5 font-mono">{fmt.price(s.price)}</td>
                    <td className="px-3 py-2.5 font-mono" style={{ color: changeColor(s.change_pct) }}>{fmt.pct(s.change_pct)}</td>
                    <td className="px-3 py-2.5 font-mono text-white/60">{s.rsi}</td>
                    <td className="px-3 py-2.5 font-mono text-white/60">{s.macd}</td>
                    <td className="px-3 py-2.5 font-mono text-white/60">{s.bb_pct}%</td>
                    <td className="px-3 py-2.5 font-mono text-white/60">{s.volume_ratio}x</td>
                  </tr>
                ))}
                {displayed.length === 0 && !loading && (
                  <tr><td colSpan={9} className="px-3 py-8 text-center text-white/30 font-mono text-sm">
                    {signals.length === 0 ? 'Click "Run Signals" to generate signals' : 'No signals match the current filters'}
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Right panel */}
        <div className="space-y-4">
          {/* Distribution */}
          <Card>
            <h3 className="text-xs font-mono uppercase text-white/50 tracking-wider mb-3">Distribution</h3>
            <ResponsiveContainer width="100%" height={140}>
              <PieChart>
                <Pie data={dist} cx="50%" cy="50%" innerRadius={35} outerRadius={60} dataKey="value" paddingAngle={3}>
                  {dist.map((d,i)=>(
                    <Cell key={i} fill={['#00C896','#FF4D6A','#F5A623'][i]} opacity={0.85}/>
                  ))}
                </Pie>
                <Tooltip contentStyle={{background:'#0d1421',border:'1px solid rgba(255,255,255,0.15)',borderRadius:8,fontFamily:'Space Mono',fontSize:11}}/>
              </PieChart>
            </ResponsiveContainer>
            <div className="flex justify-around text-xs font-mono mt-1">
              {dist.map((d,i)=>(
                <span key={d.name} style={{color:['#00C896','#FF4D6A','#F5A623'][i]}}>{d.name}: {d.value}</span>
              ))}
            </div>
          </Card>

          {/* Confidence chart */}
          {signals.length > 0 && (
            <Card>
              <h3 className="text-xs font-mono uppercase text-white/50 tracking-wider mb-3">Confidence</h3>
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={signals.slice(0,8)} margin={{top:0,right:0,bottom:0,left:0}}>
                  <XAxis dataKey="ticker" tick={{fill:'rgba(255,255,255,0.4)',fontSize:9,fontFamily:'Space Mono'}}/>
                  <YAxis hide domain={[0,1]}/>
                  <Tooltip formatter={v=>[`${(v*100).toFixed(1)}%`,'Confidence']}
                    contentStyle={{background:'#0d1421',border:'1px solid rgba(255,255,255,0.15)',borderRadius:8,fontFamily:'Space Mono',fontSize:11}}/>
                  <Bar dataKey="confidence" radius={[3,3,0,0]}>
                    {signals.slice(0,8).map((s,i)=>(
                      <Cell key={i} fill={s.signal==='BUY'?'#00C896':s.signal==='SELL'?'#FF4D6A':'#F5A623'} opacity={0.8}/>
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Card>
          )}
        </div>
      </div>

      {/* Chart for selected ticker */}
      {selected && (
        <Card>
          <PriceChart ticker={selected.ticker} signal={selected.signal}/>
        </Card>
      )}
    </div>
  )
}
