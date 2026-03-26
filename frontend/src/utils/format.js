export const fmt = {
  price:    (v) => v != null ? `$${Number(v).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})}` : '—',
  pct:      (v) => v != null ? `${Number(v)>=0?'+':''}${Number(v).toFixed(2)}%` : '—',
  conf:     (v) => v != null ? `${(Number(v)*100).toFixed(1)}%` : '—',
  vol:      (v) => v != null ? Number(v).toLocaleString() : '—',
  date:     (v) => v ? new Date(v).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'}) : '—',
  time:     (v) => v ? new Date(v).toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',second:'2-digit'}) : '—',
}

export const signalColor = (s) => ({
  BUY:  { text:'#00C896', bg:'rgba(0,200,150,0.15)', border:'rgba(0,200,150,0.3)' },
  SELL: { text:'#FF4D6A', bg:'rgba(255,77,106,0.15)', border:'rgba(255,77,106,0.3)' },
  HOLD: { text:'#F5A623', bg:'rgba(245,166,35,0.15)',  border:'rgba(245,166,35,0.3)' },
}[s] || { text:'#888', bg:'rgba(255,255,255,0.05)', border:'rgba(255,255,255,0.1)' })

export const changeColor = (v) => Number(v) > 0 ? '#00C896' : Number(v) < 0 ? '#FF4D6A' : '#F5A623'
