import { useState, useEffect } from 'react'
import { getQuotes } from '../utils/api'
import { fmt, changeColor } from '../utils/format'
import { Card, Metric, Spinner } from '../components/UI'
import PriceChart from '../components/PriceChart'
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const MODEL_PERF = [
  { name: 'Ensemble',      acc: 85.3, color: '#F5A623' },
  { name: 'LSTM',          acc: 82.1, color: '#3B82F6' },
  { name: 'XGBoost',       acc: 76.8, color: '#00C896' },
  { name: 'Random Forest', acc: 78.4, color: '#8B5CF6' },
]

const FEAT_IMP = [
  { name: 'RSI',       imp: 0.24 }, { name: 'MACD',    imp: 0.19 },
  { name: 'Volume',    imp: 0.17 }, { name: 'EMA Cross',imp: 0.15 },
  { name: 'BB Width',  imp: 0.13 }, { name: 'ATR',      imp: 0.12 },
]

export default function Dashboard({ watchlist }) {
  const [quotes,  setQuotes]  = useState([])
  const [loading, setLoading] = useState(true)
  const [selected,setSelected]= useState(watchlist[0] || 'AAPL')

  const fetchQuotes = async () => {
    try {
      const res = await getQuotes(watchlist.slice(0,8))
      setQuotes(res.data || [])
    } catch {} finally { setLoading(false) }
  }

  useEffect(() => { fetchQuotes() }, [watchlist.join(',')])
  useEffect(() => { const id = setInterval(fetchQuotes, 30000); return () => clearInterval(id) }, [watchlist.join(',')])

  const selectedSignal = null // will come from signals page cache

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Market Dashboard</h1>
        <span className="text-xs text-white/30 font-mono">Auto-updates every 30s</span>
      </div>

      {/* Quote cards */}
      {loading ? (
        <div className="flex gap-3">{[1,2,3,4].map(i=>(
          <div key={i} className="flex-1 rounded-xl border border-white/10 bg-white/5 p-4 h-20 animate-pulse"/>
        ))}</div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {quotes.slice(0,8).map(q => (
            <div key={q.ticker}
              onClick={() => setSelected(q.ticker)}
              className={`rounded-xl border p-4 cursor-pointer transition-all duration-150
                ${selected===q.ticker ? 'border-green-500/40 bg-green-500/5' : 'border-white/10 bg-white/5 hover:bg-white/8'}`}>
              <div className="flex items-start justify-between mb-1">
                <span className="font-mono font-bold text-sm text-white">{q.ticker}</span>
                <span className="text-xs font-mono" style={{ color: changeColor(q.change_pct) }}>
                  {q.change_pct > 0 ? '▲' : q.change_pct < 0 ? '▼' : '▬'} {Math.abs(q.change_pct).toFixed(2)}%
                </span>
              </div>
              <div className="font-mono text-xl font-bold text-white">{fmt.price(q.price)}</div>
              <div className="text-xs text-white/30 font-mono mt-0.5">Prev: {fmt.price(q.prev_close)}</div>
            </div>
          ))}
        </div>
      )}

      {/* Main content */}
      <div className="grid grid-cols-3 gap-5">
        {/* Price chart */}
        <Card className="col-span-2">
          <PriceChart ticker={selected} signal={selectedSignal}/>
        </Card>

        {/* Right column */}
        <div className="space-y-4">
          {/* Model performance */}
          <Card>
            <h3 className="text-sm font-mono font-bold text-white/80 mb-3 uppercase tracking-wider">Model Performance</h3>
            <div className="space-y-2">
              {MODEL_PERF.map(m => (
                <div key={m.name}>
                  <div className="flex justify-between text-xs font-mono mb-1">
                    <span className="text-white/60">{m.name}</span>
                    <span style={{ color: m.color }} className="font-bold">{m.acc}%</span>
                  </div>
                  <div className="h-1.5 bg-white/8 rounded-full overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${m.acc}%`, background: m.color }}/>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Quick metrics */}
          <div className="grid grid-cols-2 gap-2">
            <Metric label="Signals"   value="24"    delta="+3 today"/>
            <Metric label="Sharpe"    value="2.31"  delta="+0.12"/>
            <Metric label="Win Rate"  value="68.4%" delta="+2.1%"/>
            <Metric label="Max DD"    value="-14.8%" deltaColor="#FF4D6A" delta="30d"/>
          </div>
        </div>
      </div>

      {/* Bottom row */}
      <div className="grid grid-cols-2 gap-5">
        {/* Volume */}
        <Card>
          <h3 className="text-sm font-mono font-bold text-white/80 mb-3 uppercase tracking-wider">Volume Analysis</h3>
          {quotes.length > 0 && (
            <ResponsiveContainer width="100%" height={150}>
              <BarChart data={quotes} margin={{top:0,right:0,bottom:0,left:0}}>
                <XAxis dataKey="ticker" tick={{ fill:'rgba(255,255,255,0.4)', fontSize:10, fontFamily:'Space Mono' }}/>
                <YAxis hide/>
                <Tooltip formatter={v=>[Number(v).toLocaleString(),'Volume']}
                  contentStyle={{ background:'#0d1421', border:'1px solid rgba(255,255,255,0.15)', borderRadius:8, fontFamily:'Space Mono', fontSize:11 }}/>
                <Bar dataKey="volume" radius={[3,3,0,0]}>
                  {quotes.map((q,i) => (
                    <Cell key={i} fill={q.change_pct >= 0 ? 'rgba(0,200,150,0.6)' : 'rgba(255,77,106,0.6)'}/>
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>

        {/* Feature importance */}
        <Card>
          <h3 className="text-sm font-mono font-bold text-white/80 mb-3 uppercase tracking-wider">Feature Importance</h3>
          <ResponsiveContainer width="100%" height={150}>
            <BarChart layout="vertical" data={FEAT_IMP} margin={{top:0,right:30,bottom:0,left:60}}>
              <XAxis type="number" tickFormatter={v=>`${(v*100).toFixed(0)}%`}
                tick={{ fill:'rgba(255,255,255,0.3)', fontSize:9, fontFamily:'Space Mono' }}/>
              <YAxis type="category" dataKey="name"
                tick={{ fill:'rgba(255,255,255,0.6)', fontSize:10, fontFamily:'Space Mono' }}/>
              <Tooltip formatter={v=>[`${(v*100).toFixed(1)}%`,'Importance']}
                contentStyle={{ background:'#0d1421', border:'1px solid rgba(255,255,255,0.15)', borderRadius:8, fontFamily:'Space Mono', fontSize:11 }}/>
              <Bar dataKey="imp" radius={[0,3,3,0]} fill="url(#feat_grad)">
                {FEAT_IMP.map((_,i) => (
                  <Cell key={i} fill={['#8B5CF6','#3B82F6','#00C896','#F5A623','#FF4D6A','#8B5CF6'][i]}/>
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* All tickers table */}
      <Card>
        <h3 className="text-sm font-mono font-bold text-white/80 mb-3 uppercase tracking-wider">All Tickers — Live Prices</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10">
                {['Ticker','Price','Change','Prev Close','Volume','Updated'].map(h => (
                  <th key={h} className="px-3 py-2 text-left font-mono text-xs text-white/40 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {quotes.map(q => (
                <tr key={q.ticker} onClick={() => setSelected(q.ticker)}
                  className="border-b border-white/5 cursor-pointer hover:bg-white/3 transition-colors">
                  <td className="px-3 py-2.5 font-mono font-bold text-white">{q.ticker}</td>
                  <td className="px-3 py-2.5 font-mono">{fmt.price(q.price)}</td>
                  <td className="px-3 py-2.5 font-mono font-bold" style={{ color: changeColor(q.change_pct) }}>
                    {fmt.pct(q.change_pct)}
                  </td>
                  <td className="px-3 py-2.5 font-mono text-white/60">{fmt.price(q.prev_close)}</td>
                  <td className="px-3 py-2.5 font-mono text-white/60">{fmt.vol(q.volume)}</td>
                  <td className="px-3 py-2.5 font-mono text-white/30 text-xs">{q.timestamp?.slice(11,19)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
