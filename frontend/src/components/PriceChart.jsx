import { useState, useEffect } from 'react'
import { ComposedChart, Line, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import { getHistory } from '../utils/api'
import { Spinner, Button } from './UI'

const PERIODS = ['1mo','3mo','6mo','1y','2y']

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  return (
    <div className="rounded-lg border border-white/15 p-3 text-xs font-mono"
      style={{ background: '#0d1421' }}>
      <div className="text-white/50 mb-1">{label}</div>
      <div className="text-white">O: ${d?.open}  H: ${d?.high}</div>
      <div className="text-white">L: ${d?.low}   C: ${d?.close}</div>
      <div className="text-white/50">Vol: {Number(d?.volume).toLocaleString()}</div>
    </div>
  )
}

export default function PriceChart({ ticker, signal }) {
  const [data,    setData]    = useState([])
  const [period,  setPeriod]  = useState('6mo')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!ticker) return
    setLoading(true)
    getHistory(ticker, period)
      .then(r => {
        const raw = r.data || []
        // Add EMA20 and EMA50
        let ema20 = null, ema50 = null
        const k20 = 2/(20+1), k50 = 2/(50+1)
        setData(raw.map((d,i) => {
          ema20 = ema20 === null ? d.close : d.close * k20 + ema20 * (1-k20)
          ema50 = ema50 === null ? d.close : d.close * k50 + ema50 * (1-k50)
          return { ...d, ema20: +ema20.toFixed(2), ema50: +ema50.toFixed(2) }
        }))
      })
      .catch(() => setData([]))
      .finally(() => setLoading(false))
  }, [ticker, period])

  const last  = data[data.length - 1]
  const first = data[0]
  const isUp  = last && first && last.close >= first.close

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="font-mono font-bold text-white text-lg">{ticker}</span>
          {last && (
            <span className="font-mono text-white/70 text-sm">
              ${last.close.toFixed(2)}
            </span>
          )}
          {signal && (
            <span className="font-mono text-xs px-2 py-0.5 rounded"
              style={{
                color: signal==='BUY'?'#00C896':signal==='SELL'?'#FF4D6A':'#F5A623',
                background: signal==='BUY'?'rgba(0,200,150,0.15)':signal==='SELL'?'rgba(255,77,106,0.15)':'rgba(245,166,35,0.15)',
              }}>
              {signal}
            </span>
          )}
        </div>
        <div className="flex gap-1">
          {PERIODS.map(p => (
            <button key={p} onClick={() => setPeriod(p)}
              className={`px-2 py-1 rounded text-xs font-mono transition-colors
                ${period===p ? 'text-green-400 bg-green-500/10 border border-green-500/20' : 'text-white/40 hover:text-white/60'}`}>
              {p}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48">
          <Spinner size={24}/>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={data} margin={{ top:5, right:10, bottom:5, left:10 }}>
            <XAxis dataKey="date" tick={{ fill:'rgba(255,255,255,0.3)', fontSize:9, fontFamily:'Space Mono' }}
              tickFormatter={d => d.slice(5)} interval="preserveStartEnd"/>
            <YAxis yAxisId="price" orientation="right" domain={['auto','auto']}
              tick={{ fill:'rgba(255,255,255,0.3)', fontSize:9, fontFamily:'Space Mono' }}
              tickFormatter={v => `$${v}`}/>
            <YAxis yAxisId="vol" orientation="left" hide/>
            <Tooltip content={<CustomTooltip/>}/>
            <Bar yAxisId="vol" dataKey="volume" fill={isUp?'rgba(0,200,150,0.12)':'rgba(255,77,106,0.12)'} radius={[2,2,0,0]}/>
            <Line yAxisId="price" type="monotone" dataKey="close"
              stroke={isUp?'#00C896':'#FF4D6A'} strokeWidth={1.5} dot={false}/>
            <Line yAxisId="price" type="monotone" dataKey="ema20"
              stroke="#3B82F6" strokeWidth={1} dot={false} strokeDasharray="4 4"/>
            <Line yAxisId="price" type="monotone" dataKey="ema50"
              stroke="#F5A623" strokeWidth={1} dot={false} strokeDasharray="4 4"/>
          </ComposedChart>
        </ResponsiveContainer>
      )}

      <div className="flex gap-4 mt-2 text-xs text-white/30 font-mono">
        <span><span className="text-blue-400">- -</span> EMA 20</span>
        <span><span className="text-amber-400">- -</span> EMA 50</span>
      </div>
    </div>
  )
}
