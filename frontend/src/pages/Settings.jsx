import { useState } from 'react'
import { trainModels } from '../utils/api'
import { Card, Button } from '../components/UI'
import { Brain, RefreshCw, CheckCircle } from 'lucide-react'

export default function Settings() {
  const [training,    setTraining]    = useState(false)
  const [trainResult, setTrainResult] = useState(null)
  const [trainTicker, setTrainTicker] = useState('SPY')

  const handleTrain = async () => {
    setTraining(true); setTrainResult(null)
    try {
      await trainModels(trainTicker)
      setTrainResult({ success: true, message: `Training started on ${trainTicker}. Models will be ready in ~2 minutes.` })
    } catch(e) {
      setTrainResult({ success: false, message: e.response?.data?.detail || 'Training failed' })
    } finally { setTraining(false) }
  }

  return (
    <div className="space-y-5 max-w-2xl">
      <h1 className="text-2xl font-bold text-white">Settings</h1>

      {/* ML Models */}
      <Card>
        <div className="flex items-center gap-2 mb-4">
          <Brain size={16} className="text-purple-400"/>
          <h3 className="text-sm font-mono font-bold text-white/80 uppercase tracking-wider">ML Models</h3>
        </div>

        <div className="space-y-4">
          {[
            { name:'Random Forest', acc:'78.4%', color:'#8B5CF6', desc:'Fast, interpretable. Best for feature importance.' },
            { name:'LSTM',          acc:'82.1%', color:'#3B82F6', desc:'Sequential pattern recognition. Best accuracy.' },
            { name:'XGBoost',       acc:'76.8%', color:'#00C896', desc:'Gradient boosting. Handles non-linear features.' },
            { name:'Ensemble',      acc:'85.3%', color:'#F5A623', desc:'Weighted combination of all three models.' },
          ].map(m => (
            <div key={m.name} className="flex items-center gap-4 p-3 rounded-lg bg-white/3 border border-white/8">
              <div className="w-2 h-2 rounded-full" style={{ background: m.color }}/>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm font-bold text-white">{m.name}</span>
                  <span className="font-mono text-xs px-1.5 py-0.5 rounded" style={{color:m.color,background:`${m.color}20`}}>{m.acc}</span>
                </div>
                <div className="text-xs text-white/40 mt-0.5">{m.desc}</div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 pt-4 border-t border-white/10">
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="text-xs text-white/40 font-mono block mb-1">Train on ticker</label>
              <select value={trainTicker} onChange={e=>setTrainTicker(e.target.value)}
                className="bg-white/5 border border-white/15 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none">
                {['SPY','QQQ','AAPL','NVDA','MSFT'].map(t=>(
                  <option key={t} value={t} className="bg-gray-900">{t}</option>
                ))}
              </select>
            </div>
            <Button variant="primary" onClick={handleTrain} loading={training} className="px-5 py-2">
              <RefreshCw size={13}/> Retrain All Models
            </Button>
          </div>

          {trainResult && (
            <div className={`mt-3 p-3 rounded-lg text-sm font-mono ${trainResult.success ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
              {trainResult.success ? '✅' : '❌'} {trainResult.message}
            </div>
          )}
        </div>
      </Card>

      {/* API Info */}
      <Card>
        <h3 className="text-sm font-mono font-bold text-white/80 uppercase tracking-wider mb-4">API Endpoints</h3>
        <div className="space-y-2 font-mono text-xs">
          {[
            ['GET',  '/api/health',           'Health check'],
            ['GET',  '/api/quotes',           'Live price quotes'],
            ['GET',  '/api/signals',          'ML signal generation'],
            ['GET',  '/api/history/{ticker}', 'Price history'],
            ['GET',  '/api/backtest/{ticker}','Run backtest'],
            ['POST', '/api/train',            'Trigger model training'],
            ['GET',  '/api/watchlist',        'Get watchlist'],
            ['POST', '/api/watchlist/{t}',    'Add ticker'],
            ['GET',  '/api/users',            'Get alert users'],
            ['POST', '/api/alerts/run',       'Run signals & alert'],
          ].map(([method, path, desc]) => (
            <div key={path} className="flex items-center gap-3 py-1.5 border-b border-white/5">
              <span className={`px-1.5 py-0.5 rounded text-xs font-bold w-12 text-center ${method==='GET'?'bg-blue-500/20 text-blue-400':'bg-green-500/20 text-green-400'}`}>{method}</span>
              <span className="text-white/70 flex-1">{path}</span>
              <span className="text-white/30">{desc}</span>
            </div>
          ))}
        </div>
        <a href="/api/docs" target="_blank"
          className="inline-flex items-center gap-1.5 mt-4 text-xs text-green-400 font-mono hover:underline">
          Open Swagger UI ↗
        </a>
      </Card>

      {/* About */}
      <Card>
        <h3 className="text-sm font-mono font-bold text-white/80 uppercase tracking-wider mb-3">About</h3>
        <div className="space-y-1 text-xs font-mono text-white/50">
          <div>AlphaSignal v2.4.0</div>
          <div>ML Signal Generation Platform</div>
          <div>Backend: FastAPI + Python</div>
          <div>Frontend: React + Recharts + Tailwind</div>
          <div>Models: Random Forest · LSTM · XGBoost · Ensemble</div>
          <div>Data: Yahoo Finance · Alpha Vantage</div>
        </div>
      </Card>
    </div>
  )
}
