import { useState } from 'react'
import { getBacktest } from '../utils/api'
import { fmt, changeColor } from '../utils/format'
import { Card, Metric, Button, Select, Spinner } from '../components/UI'
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, Cell } from 'recharts'

const PERIODS  = [{ value:'1y',label:'1 Year' },{ value:'2y',label:'2 Years' },{ value:'3y',label:'3 Years' },{ value:'5y',label:'5 Years' }]

export default function Backtest({ watchlist }) {
  const [ticker,   setTicker]   = useState(watchlist[0] || 'SPY')
  const [period,   setPeriod]   = useState('2y')
  const [capital,  setCapital]  = useState(100000)
  const [result,   setResult]   = useState(null)
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState(null)

  const run = async () => {
    setLoading(true); setError(null); setResult(null)
    try {
      const res = await getBacktest(ticker, period, capital)
      setResult(res.data)
    } catch(e) {
      setError(e.response?.data?.detail || e.message)
    } finally { setLoading(false) }
  }

  // Monthly returns from equity curve
  const monthlyReturns = result?.equity_curve ? (() => {
    const monthly = {}
    result.equity_curve.forEach(p => {
      const mo = p.date.slice(0,7)
      monthly[mo] = p.value
    })
    const keys = Object.keys(monthly).sort()
    return keys.slice(1).map((k,i) => ({
      month: k,
      label: new Date(k).toLocaleDateString('en-US',{month:'short',year:'2-digit'}),
      return: +((monthly[k]/monthly[keys[i]]-1)*100).toFixed(2)
    }))
  })() : []

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-white">Strategy Backtester</h1>

      {/* Controls */}
      <Card>
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="text-xs text-white/40 font-mono uppercase tracking-wider block mb-1.5">Ticker</label>
            <select value={ticker} onChange={e=>setTicker(e.target.value)}
              className="bg-white/5 border border-white/15 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none w-32">
              {watchlist.map(t => <option key={t} value={t} className="bg-gray-900">{t}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-white/40 font-mono uppercase tracking-wider block mb-1.5">Period</label>
            <select value={period} onChange={e=>setPeriod(e.target.value)}
              className="bg-white/5 border border-white/15 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none">
              {PERIODS.map(p=><option key={p.value} value={p.value} className="bg-gray-900">{p.label}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-white/40 font-mono uppercase tracking-wider block mb-1.5">Starting Capital</label>
            <input type="number" value={capital} onChange={e=>setCapital(Number(e.target.value))}
              className="bg-white/5 border border-white/15 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none w-36"/>
          </div>
          <Button variant="primary" onClick={run} loading={loading} className="px-6 py-2">
            ▶ Run Backtest
          </Button>
        </div>
        {error && <div className="mt-3 text-sm text-red-400 font-mono bg-red-500/10 rounded-lg px-3 py-2">{error}</div>}
      </Card>

      {/* Loading */}
      {loading && (
        <Card className="flex items-center justify-center gap-3 py-8">
          <Spinner size={20}/>
          <span className="text-white/60 font-mono text-sm">Running backtest on {ticker}...</span>
        </Card>
      )}

      {/* Results */}
      {result && !loading && (
        <>
          {/* Metrics */}
          <div className="grid grid-cols-3 lg:grid-cols-6 gap-3">
            {[
              { label:'Total Return',  value: `${result.total_return_pct > 0 ? '+' : ''}${result.total_return_pct?.toFixed(1)}%`, color: result.total_return_pct >= 0 ? '#00C896' : '#FF4D6A' },
              { label:'Sharpe Ratio',  value: result.sharpe_ratio?.toFixed(2), color: result.sharpe_ratio >= 1 ? '#00C896' : '#F5A623' },
              { label:'Sortino',       value: result.sortino_ratio?.toFixed(2), color: '#8B5CF6' },
              { label:'Max Drawdown',  value: `${result.max_drawdown_pct?.toFixed(1)}%`, color: '#FF4D6A' },
              { label:'Win Rate',      value: `${result.win_rate_pct?.toFixed(1)}%`, color: '#00C896' },
              { label:'Trades',        value: result.n_trades },
            ].map(m => (
              <div key={m.label} className="rounded-xl border border-white/10 bg-white/5 p-4">
                <div className="text-xs text-white/40 font-mono uppercase tracking-wider mb-1">{m.label}</div>
                <div className="text-xl font-bold font-mono" style={{ color: m.color || '#fff' }}>{m.value}</div>
              </div>
            ))}
          </div>

          {/* Equity curve */}
          <Card>
            <h3 className="text-sm font-mono font-bold text-white/80 mb-4 uppercase tracking-wider">Equity Curve</h3>
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={result.equity_curve} margin={{top:5,right:10,bottom:5,left:10}}>
                <defs>
                  <linearGradient id="eq_grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#00C896" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="#00C896" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" tick={{fill:'rgba(255,255,255,0.3)',fontSize:10,fontFamily:'Space Mono'}}
                  tickFormatter={d=>d.slice(5)} interval="preserveStartEnd"/>
                <YAxis orientation="right" tick={{fill:'rgba(255,255,255,0.3)',fontSize:10,fontFamily:'Space Mono'}}
                  tickFormatter={v=>`$${(v/1000).toFixed(0)}k`}/>
                <ReferenceLine y={capital} stroke="rgba(255,255,255,0.15)" strokeDasharray="4 4"/>
                <Tooltip formatter={v=>[fmt.price(v),'Portfolio']}
                  contentStyle={{background:'#0d1421',border:'1px solid rgba(255,255,255,0.15)',borderRadius:8,fontFamily:'Space Mono',fontSize:11}}/>
                <Area type="monotone" dataKey="value" stroke="#00C896" strokeWidth={2}
                  fill="url(#eq_grad)" dot={false}/>
              </AreaChart>
            </ResponsiveContainer>
          </Card>

          {/* Monthly returns */}
          {monthlyReturns.length > 0 && (
            <Card>
              <h3 className="text-sm font-mono font-bold text-white/80 mb-4 uppercase tracking-wider">Monthly Returns</h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={monthlyReturns} margin={{top:5,right:10,bottom:5,left:10}}>
                  <XAxis dataKey="label" tick={{fill:'rgba(255,255,255,0.3)',fontSize:9,fontFamily:'Space Mono'}}/>
                  <YAxis tick={{fill:'rgba(255,255,255,0.3)',fontSize:10,fontFamily:'Space Mono'}}
                    tickFormatter={v=>`${v}%`} orientation="right"/>
                  <ReferenceLine y={0} stroke="rgba(255,255,255,0.2)"/>
                  <Tooltip formatter={v=>[`${v}%`,'Return']}
                    contentStyle={{background:'#0d1421',border:'1px solid rgba(255,255,255,0.15)',borderRadius:8,fontFamily:'Space Mono',fontSize:11}}/>
                  <Bar dataKey="return" radius={[3,3,0,0]}>
                    {monthlyReturns.map((d,i)=>(
                      <Cell key={i} fill={d.return>=0?'rgba(0,200,150,0.7)':'rgba(255,77,106,0.7)'}/>
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Card>
          )}
        </>
      )}

      {/* Placeholder */}
      {!result && !loading && (
        <Card className="py-12 text-center">
          <div className="text-white/20 text-4xl mb-3">📊</div>
          <div className="text-white/40 font-mono text-sm">Select a ticker and click Run Backtest</div>
        </Card>
      )}
    </div>
  )
}
