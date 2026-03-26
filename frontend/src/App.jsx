import { useState, useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import Sidebar    from './components/Sidebar'
import TickerTape from './components/TickerTape'
import Dashboard  from './pages/Dashboard'
import Signals    from './pages/Signals'
import Backtest   from './pages/Backtest'
import Alerts     from './pages/Alerts'
import Settings   from './pages/Settings'
import { getWatchlist } from './utils/api'

const DEFAULT_TICKERS = ['AAPL','NVDA','TSLA','SPY','QQQ','MSFT','GOOGL','AMZN','META']

export default function App() {
  const [watchlist, setWatchlist] = useState(DEFAULT_TICKERS)

  // Load watchlist from backend on mount
  useEffect(() => {
    getWatchlist()
      .then(r => { if (r.data?.tickers?.length) setWatchlist(r.data.tickers) })
      .catch(() => {})
  }, [])

  return (
    <div className="min-h-screen" style={{ background: '#0a0f1a' }}>
      {/* Sidebar */}
      <Sidebar watchlist={watchlist} onWatchlistChange={setWatchlist}/>

      {/* Main content area */}
      <div className="ml-56 flex flex-col min-h-screen">
        {/* Ticker tape */}
        <TickerTape tickers={watchlist}/>

        {/* Page content */}
        <main className="flex-1 p-6">
          <Routes>
            <Route path="/"         element={<Dashboard watchlist={watchlist}/>}/>
            <Route path="/signals"  element={<Signals   watchlist={watchlist} onWatchlistChange={setWatchlist}/>}/>
            <Route path="/backtest" element={<Backtest  watchlist={watchlist}/>}/>
            <Route path="/alerts"   element={<Alerts    watchlist={watchlist}/>}/>
            <Route path="/settings" element={<Settings/>}/>
          </Routes>
        </main>
      </div>
    </div>
  )
}
