import { useEffect, useState } from 'react'
import { getQuotes } from '../utils/api'
import { fmt, changeColor } from '../utils/format'

export default function TickerTape({ tickers }) {
  const [quotes, setQuotes] = useState([])

  const fetch = async () => {
    try {
      const res = await getQuotes(tickers.slice(0, 12))
      setQuotes(res.data || [])
    } catch {}
  }

  useEffect(() => {
    fetch()
    const id = setInterval(fetch, 30000)
    return () => clearInterval(id)
  }, [tickers.join(',')])

  if (!quotes.length) return null

  const items = [...quotes, ...quotes] // duplicate for seamless loop

  return (
    <div className="overflow-hidden border-b border-white/8 bg-white/2"
      style={{ background: 'rgba(13,20,33,0.8)' }}>
      <div className="ticker-scroll flex w-max">
        {items.map((q, i) => {
          const chg = q.change_pct
          const color = changeColor(chg)
          const arrow = chg > 0 ? '▲' : chg < 0 ? '▼' : '▬'
          return (
            <div key={i} className="inline-flex items-center gap-2 px-6 py-2 border-r border-white/5"
              style={{ fontFamily: 'Space Mono, monospace', fontSize: 11, whiteSpace: 'nowrap' }}>
              <span className="font-bold text-white">{q.ticker}</span>
              <span className="text-white/80">{fmt.price(q.price)}</span>
              <span style={{ color }}>{arrow} {Math.abs(chg).toFixed(2)}%</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
