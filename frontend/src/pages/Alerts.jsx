import { useState, useEffect } from 'react'
import { getUsers, createUser, deleteUser, getAlertHistory, sendTestAlert, runAndAlert } from '../utils/api'
import { fmt, signalColor } from '../utils/format'
import { Card, Button, Input, SignalBadge, Tabs, Spinner } from '../components/UI'
import { Trash2, Plus, Send, Bell, Users, History } from 'lucide-react'

export default function Alerts({ watchlist }) {
  const [tab,       setTab]       = useState('feed')
  const [users,     setUsers]     = useState([])
  const [history,   setHistory]   = useState([])
  const [histUser,  setHistUser]  = useState('')
  const [sending,   setSending]   = useState(false)
  const [scanning,  setScanning]  = useState(false)
  const [scanRes,   setScanRes]   = useState(null)
  const [minConf,   setMinConf]   = useState(0.65)
  const [addOpen,   setAddOpen]   = useState(false)
  const [form, setForm] = useState({ name:'', phone:'', email:'', channels:['sms'], min_confidence:0.65, tickers:'' })

  const loadUsers   = async () => { try { const r = await getUsers(); setUsers(r.data?.users||[]) } catch {} }
  const loadHistory = async (u='') => { try { const r = await getAlertHistory(u||undefined,100); setHistory(r.data?.history||[]) } catch {} }

  useEffect(() => { loadUsers(); loadHistory() }, [])

  const handleAdd = async () => {
    if (!form.name) return alert('Name is required')
    try {
      await createUser({
        ...form,
        tickers: form.tickers ? form.tickers.split(',').map(t=>t.trim().toUpperCase()) : null
      })
      setForm({ name:'', phone:'', email:'', channels:['sms'], min_confidence:0.65, tickers:'' })
      setAddOpen(false)
      loadUsers()
    } catch(e) { alert(e.response?.data?.detail || 'Failed to add user') }
  }

  const handleDelete = async (id) => {
    if (!confirm('Remove this user?')) return
    try { await deleteUser(id); loadUsers() } catch {}
  }

  const handleTest = async () => {
    setSending(true)
    try { await sendTestAlert('NVDA','BUY',0.91,875.90); alert('✅ Test alert sent!'); loadHistory() }
    catch(e) { alert(e.response?.data?.detail||'Failed') }
    finally { setSending(false) }
  }

  const handleScan = async () => {
    setScanning(true); setScanRes(null)
    try {
      const r = await runAndAlert(watchlist, minConf)
      setScanRes(r.data)
      loadHistory()
    } catch(e) { alert(e.response?.data?.detail||'Scan failed') }
    finally { setScanning(false) }
  }

  const TABS = [
    { key:'feed',    label:'📋 Alert Feed' },
    { key:'send',    label:'📡 Send Alerts' },
    { key:'users',   label:'👥 Users'      },
    { key:'history', label:'📜 History'    },
  ]

  const DEMO_ALERTS = [
    { time:'2 min ago',  type:'SELL', msg:'TSLA crossed below 50-day MA',       detail:'Confidence 74% · LSTM' },
    { time:'8 min ago',  type:'BUY',  msg:'NVDA breakout above resistance $870', detail:'Confidence 91% · Ensemble' },
    { time:'15 min ago', type:'WARN', msg:'SPY RSI approaching overbought (68)', detail:'Monitor for reversal' },
    { time:'1 hr ago',   type:'INFO', msg:'Model retrain completed · LSTM v3.1', detail:'Accuracy 80.2% → 82.1%' },
    { time:'2 hr ago',   type:'BUY',  msg:'QQQ BUY signal · Momentum surge',    detail:'MACD crossover confirmed' },
  ]

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Alert System</h1>
        <div className="flex gap-2">
          <span className="text-xs font-mono px-2 py-1 rounded" style={{background:'rgba(59,130,246,0.15)',color:'#3B82F6',border:'1px solid rgba(59,130,246,0.3)'}}>EMAIL</span>
          <span className="text-xs font-mono px-2 py-1 rounded" style={{background:'rgba(139,92,246,0.15)',color:'#8B5CF6',border:'1px solid rgba(139,92,246,0.3)'}}>SLACK</span>
          <span className="text-xs font-mono px-2 py-1 rounded" style={{background:'rgba(0,200,150,0.15)',color:'#00C896',border:'1px solid rgba(0,200,150,0.3)'}}>SMS</span>
        </div>
      </div>

      <Card className="p-0 overflow-hidden">
        <Tabs tabs={TABS} active={tab} onChange={setTab}/>
        <div className="p-4">

          {/* ── Alert Feed ── */}
          {tab === 'feed' && (
            <div className="space-y-2">
              {DEMO_ALERTS.map((a,i) => {
                const colors = { BUY:'#00C896', SELL:'#FF4D6A', WARN:'#F5A623', INFO:'#3B82F6' }
                const c = colors[a.type] || '#888'
                return (
                  <div key={i} className="flex items-start gap-3 p-3 rounded-lg border-l-2"
                    style={{ borderColor: c, background:'rgba(255,255,255,0.03)' }}>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold" style={{ color: c }}>{a.type}</span>
                        <span className="text-sm text-white/80">{a.msg}</span>
                      </div>
                      <div className="text-xs text-white/40 mt-0.5">{a.detail} · {a.time}</div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* ── Send Alerts ── */}
          {tab === 'send' && (
            <div className="space-y-5">
              <div>
                <h3 className="text-sm font-mono text-white/70 mb-3 font-bold uppercase tracking-wider">🚀 Real-Time Signal Alerts</h3>
                <p className="text-xs text-white/40 mb-4">Scans all watchlist tickers right now and sends SMS/Email for every strong signal</p>

                <div className="flex items-center gap-4 mb-4">
                  <div className="flex-1">
                    <label className="text-xs text-white/40 font-mono block mb-1">Min Confidence: {(minConf*100).toFixed(0)}%</label>
                    <input type="range" min={0.5} max={0.95} step={0.05} value={minConf}
                      onChange={e=>setMinConf(Number(e.target.value))}
                      className="w-full accent-green-400"/>
                  </div>
                  <Button variant="primary" onClick={handleScan} loading={scanning} className="px-6">
                    <Send size={13}/> Run & Send Alerts
                  </Button>
                  <Button onClick={handleTest} loading={sending}>
                    <Bell size={13}/> Send Test Alert
                  </Button>
                </div>

                {scanRes && (
                  <div className="rounded-lg border border-green-500/20 bg-green-500/5 p-4">
                    <div className="flex gap-6 mb-3">
                      <div><div className="text-xs text-white/40 font-mono">SCANNED</div><div className="text-xl font-bold font-mono text-white">{scanRes.scanned}</div></div>
                      <div><div className="text-xs text-white/40 font-mono">ALERTS SENT</div><div className="text-xl font-bold font-mono text-green-400">{scanRes.alerted}</div></div>
                    </div>
                    {scanRes.alerts?.map((a,i) => (
                      <div key={i} className="flex items-center gap-3 py-2 border-t border-white/5">
                        <SignalBadge signal={a.signal}/>
                        <span className="font-mono font-bold text-white">{a.ticker}</span>
                        <span className="text-sm text-white/60">{fmt.conf(a.confidence)} confidence</span>
                        <span className="text-sm text-white/60 ml-auto">{fmt.price(a.price)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── Users ── */}
          {tab === 'users' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-white/50 font-mono">{users.length} user(s) registered</span>
                <Button variant="primary" onClick={()=>setAddOpen(v=>!v)}>
                  <Plus size={13}/> Add User
                </Button>
              </div>

              {addOpen && (
                <div className="border border-white/15 rounded-xl p-4 bg-white/3 space-y-3">
                  <h4 className="text-xs font-mono text-white/60 uppercase tracking-wider">New User</h4>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs text-white/40 font-mono block mb-1">Name *</label>
                      <Input value={form.name} onChange={e=>setForm(f=>({...f,name:e.target.value}))} placeholder="Full name"/>
                    </div>
                    <div>
                      <label className="text-xs text-white/40 font-mono block mb-1">Phone</label>
                      <Input value={form.phone} onChange={e=>setForm(f=>({...f,phone:e.target.value}))} placeholder="+919876543210"/>
                    </div>
                    <div>
                      <label className="text-xs text-white/40 font-mono block mb-1">Email</label>
                      <Input value={form.email} onChange={e=>setForm(f=>({...f,email:e.target.value}))} placeholder="user@gmail.com"/>
                    </div>
                    <div>
                      <label className="text-xs text-white/40 font-mono block mb-1">Tickers (blank = all)</label>
                      <Input value={form.tickers} onChange={e=>setForm(f=>({...f,tickers:e.target.value}))} placeholder="AAPL,NVDA,SPY"/>
                    </div>
                    <div>
                      <label className="text-xs text-white/40 font-mono block mb-1">Channels</label>
                      <div className="flex gap-2">
                        {['sms','email','slack'].map(c => (
                          <label key={c} className="flex items-center gap-1.5 cursor-pointer">
                            <input type="checkbox" checked={form.channels.includes(c)}
                              onChange={e=>setForm(f=>({...f,channels:e.target.checked?[...f.channels,c]:f.channels.filter(x=>x!==c)}))}
                              className="accent-green-400"/>
                            <span className="text-xs text-white/60 font-mono">{c}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                    <div>
                      <label className="text-xs text-white/40 font-mono block mb-1">Min Confidence: {(form.min_confidence*100).toFixed(0)}%</label>
                      <input type="range" min={0.5} max={0.95} step={0.05} value={form.min_confidence}
                        onChange={e=>setForm(f=>({...f,min_confidence:Number(e.target.value)}))}
                        className="w-full accent-green-400"/>
                    </div>
                  </div>
                  <div className="flex gap-2 pt-1">
                    <Button variant="primary" onClick={handleAdd}>✅ Add User</Button>
                    <Button onClick={()=>setAddOpen(false)}>Cancel</Button>
                  </div>
                </div>
              )}

              {users.length === 0 ? (
                <div className="text-center py-8 text-white/30 font-mono text-sm">No users yet. Add your first user above.</div>
              ) : (
                <div className="space-y-2">
                  {users.map(u => (
                    <div key={u.id} className="flex items-center gap-4 p-3 rounded-lg border border-white/8 bg-white/3 hover:bg-white/5">
                      <div className="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center text-xs font-mono font-bold text-green-400">
                        {u.name[0]?.toUpperCase()}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-bold text-white text-sm">{u.name}</div>
                        <div className="text-xs text-white/40 font-mono truncate">
                          {u.phone || '—'} · {u.email || '—'}
                        </div>
                      </div>
                      <div className="flex gap-1">
                        {u.channels?.map(c=>(
                          <span key={c} className="text-xs font-mono px-1.5 py-0.5 rounded bg-white/8 text-white/50">{c}</span>
                        ))}
                      </div>
                      <div className="text-xs font-mono text-white/40">{(u.min_confidence*100).toFixed(0)}% min</div>
                      <div className="text-xs font-mono text-white/30">{u.tickers ? u.tickers.join(',') : 'ALL'}</div>
                      <button onClick={()=>handleDelete(u.id)} className="text-white/20 hover:text-red-400 transition-colors p-1">
                        <Trash2 size={13}/>
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ── History ── */}
          {tab === 'history' && (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <select value={histUser} onChange={e=>{setHistUser(e.target.value);loadHistory(e.target.value)}}
                  className="bg-white/5 border border-white/15 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none">
                  <option value="" className="bg-gray-900">All Users</option>
                  {users.map(u=><option key={u.id} value={u.name} className="bg-gray-900">{u.name}</option>)}
                </select>
                <Button onClick={()=>loadHistory(histUser)}>Refresh</Button>
                <span className="text-xs text-white/30 font-mono">{history.length} records</span>
              </div>

              {history.length === 0 ? (
                <div className="text-center py-8 text-white/30 font-mono text-sm">No alert history yet. Send some alerts first.</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-white/10">
                        {['Sent At','User','Ticker','Signal','Confidence','Price','Channel'].map(h=>(
                          <th key={h} className="px-3 py-2 text-left font-mono text-white/40 uppercase tracking-wider">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {history.map((h,i) => (
                        <tr key={i} className="border-b border-white/5 hover:bg-white/3">
                          <td className="px-3 py-2.5 font-mono text-white/50">{h.sent_at?.slice(0,16)}</td>
                          <td className="px-3 py-2.5 font-mono text-white/70">{h.user_name}</td>
                          <td className="px-3 py-2.5 font-mono font-bold text-white">{h.ticker}</td>
                          <td className="px-3 py-2.5"><SignalBadge signal={h.signal}/></td>
                          <td className="px-3 py-2.5 font-mono text-white/60">{fmt.conf(h.confidence)}</td>
                          <td className="px-3 py-2.5 font-mono">{fmt.price(h.price)}</td>
                          <td className="px-3 py-2.5 font-mono text-white/40">{h.channel}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

        </div>
      </Card>
    </div>
  )
}
