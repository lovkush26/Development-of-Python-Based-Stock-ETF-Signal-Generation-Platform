import { useState, useEffect, useCallback, useRef } from 'react'

export function useApi(apiFn, deps = [], options = {}) {
  const { interval = null, immediate = true } = options
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(immediate)
  const [error,   setError]   = useState(null)
  const timerRef = useRef(null)

  const fetch = useCallback(async (...args) => {
    setLoading(true)
    setError(null)
    try {
      const res = await apiFn(...args)
      setData(res.data)
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || 'Error')
    } finally {
      setLoading(false)
    }
  }, deps)

  useEffect(() => {
    if (immediate) fetch()
    if (interval) {
      timerRef.current = setInterval(fetch, interval)
      return () => clearInterval(timerRef.current)
    }
  }, [fetch])

  return { data, loading, error, refetch: fetch }
}

export function useInterval(callback, delay) {
  const savedCallback = useRef(callback)
  useEffect(() => { savedCallback.current = callback }, [callback])
  useEffect(() => {
    if (delay === null) return
    const id = setInterval(() => savedCallback.current(), delay)
    return () => clearInterval(id)
  }, [delay])
}
