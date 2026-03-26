"""
data_ingestion/fetcher.py — Market data ingestion layer.

Supports:
  - Yahoo Finance  (yfinance) — free, no API key
  - Alpha Vantage  — free tier with API key
  - Polygon.io     — premium, optional

Usage:
    from data_ingestion.fetcher import MarketDataFetcher
    fetcher = MarketDataFetcher()
    df = fetcher.get_ohlcv("AAPL", period="6mo")
"""

import time
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import requests

from config.settings import get_settings
settings = get_settings()
from utils.logger import log


class MarketDataFetcher:
    """Unified market data fetcher with fallback sources."""

    def __init__(self):
        self.av_key = settings.alpha_vantage_api_key
        self.polygon_key = settings.polygon_api_key
        self._cache: Dict[str, pd.DataFrame] = {}

    # ── Primary: Yahoo Finance ───────────────────────────────────────────────

    def get_ohlcv(
        self,
        ticker: str,
        period: str = "1y",
        interval: str = "1d",
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data for a single ticker.

        Args:
            ticker:    Stock/ETF symbol e.g. "AAPL"
            period:    "1d","5d","1mo","3mo","6mo","1y","2y","5y","max"
            interval:  "1m","5m","15m","1h","1d","1wk","1mo"
            use_cache: Return cached result if available

        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume, Adj Close
        """
        cache_key = f"{ticker}_{period}_{interval}"
        if use_cache and cache_key in self._cache:
            log.debug(f"Cache hit for {ticker}")
            return self._cache[cache_key]

        try:
            log.info(f"Fetching {ticker} from Yahoo Finance [{period}/{interval}]")
            tkr = yf.Ticker(ticker)
            df = tkr.history(period=period, interval=interval)

            if df.empty:
                log.warning(f"No data returned for {ticker}")
                return pd.DataFrame()

            df = self._clean_ohlcv(df, ticker)
            self._cache[cache_key] = df
            return df

        except Exception as e:
            log.error(f"Yahoo Finance error for {ticker}: {e}")
            return pd.DataFrame()

    def get_multiple(
        self,
        tickers: List[str],
        period: str = "1y",
        interval: str = "1d",
    ) -> Dict[str, pd.DataFrame]:
        """Fetch OHLCV for multiple tickers. Returns dict of {ticker: DataFrame}."""
        results = {}
        for ticker in tickers:
            df = self.get_ohlcv(ticker, period=period, interval=interval)
            if not df.empty:
                results[ticker] = df
            time.sleep(0.25)  # Be polite to the API
        log.info(f"Fetched data for {len(results)}/{len(tickers)} tickers")
        return results

    def get_live_quote(self, ticker: str) -> Dict:
        """Get current price and basic stats."""
        try:
            tkr = yf.Ticker(ticker)
            info = tkr.fast_info
            return {
                "ticker": ticker,
                "price": round(info.last_price, 2),
                "prev_close": round(info.previous_close, 2),
                "change_pct": round(
                    (info.last_price - info.previous_close) / info.previous_close * 100, 2
                ),
                "volume": info.last_volume,
                "market_cap": info.market_cap,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            log.error(f"Live quote error for {ticker}: {e}")
            return {"ticker": ticker, "error": str(e)}

    def get_batch_quotes(self, tickers: List[str]) -> List[Dict]:
        """Get live quotes for multiple tickers efficiently."""
        quotes = []
        for ticker in tickers:
            quote = self.get_live_quote(ticker)
            quotes.append(quote)
        return quotes

    # ── Alpha Vantage (fallback / premium indicators) ───────────────────────

    def get_alpha_vantage(
        self,
        ticker: str,
        function: str = "TIME_SERIES_DAILY_ADJUSTED",
        outputsize: str = "compact",
    ) -> pd.DataFrame:
        """Fetch data from Alpha Vantage API."""
        if not self.av_key:
            log.warning("Alpha Vantage API key not set. Falling back to yfinance.")
            return self.get_ohlcv(ticker)

        url = "https://www.alphavantage.co/query"
        params = {
            "function": function,
            "symbol": ticker,
            "outputsize": outputsize,
            "apikey": self.av_key,
        }
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            # Parse TIME_SERIES_DAILY_ADJUSTED
            ts_key = [k for k in data.keys() if "Time Series" in k]
            if not ts_key:
                log.error(f"Alpha Vantage response error: {data}")
                return pd.DataFrame()

            df = pd.DataFrame(data[ts_key[0]]).T
            df.index = pd.to_datetime(df.index)
            df.sort_index(inplace=True)
            df.columns = [c.split(". ")[1].title() for c in df.columns]
            df = df.astype(float)
            return df

        except Exception as e:
            log.error(f"Alpha Vantage error for {ticker}: {e}")
            return pd.DataFrame()

    # ── Utilities ────────────────────────────────────────────────────────────

    def _clean_ohlcv(self, df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Clean and standardise OHLCV DataFrame."""
        df = df.copy()
        df.index.name = "Date"

        # Drop non-trading rows
        df.dropna(subset=["Close", "Volume"], inplace=True)
        df = df[df["Volume"] > 0]

        # Ensure correct dtypes
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df["Ticker"] = ticker
        df.sort_index(inplace=True)
        return df

    def clear_cache(self):
        self._cache.clear()
        log.info("Data cache cleared")



