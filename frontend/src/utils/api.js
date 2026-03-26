import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || '/api'
const api = axios.create({ baseURL: BASE, timeout: 30000 })

export const getHealth       = ()                    => api.get('/health')
export const getQuotes       = (tickers)             => api.get('/quotes',       { params: { tickers: tickers.join(',') } })
export const getSignals      = (tickers)             => api.get('/signals',      { params: { tickers: tickers.join(',') } })
export const getHistory      = (t, period='6mo')     => api.get(`/history/${t}`, { params: { period } })
export const getBacktest     = (t, period='2y', capital=100000) => api.get(`/backtest/${t}`, { params: { period, capital } })
export const trainModels     = (train_ticker='SPY')  => api.post('/train', { train_ticker })
export const searchTickers   = (q)                   => api.get('/search',       { params: { q } })
export const getWatchlist    = ()                    => api.get('/watchlist')
export const addTicker       = (ticker)              => api.post(`/watchlist/${ticker}`)
export const removeTicker    = (ticker)              => api.delete(`/watchlist/${ticker}`)
export const getUsers        = ()                    => api.get('/users')
export const createUser      = (data)                => api.post('/users', data)
export const deleteUser      = (id)                  => api.delete(`/users/${id}`)
export const getAlertHistory = (user_name, limit=50) => api.get('/alerts/history', { params: { user_name, limit } })
export const sendTestAlert   = (ticker, signal, confidence, price) => api.post('/alerts/send', { ticker, signal, confidence, price })
export const runAndAlert     = (tickers, min_confidence=0.65) => api.post('/alerts/run', null, { params: { tickers: tickers?.join(',') || '', min_confidence } })

export default api
