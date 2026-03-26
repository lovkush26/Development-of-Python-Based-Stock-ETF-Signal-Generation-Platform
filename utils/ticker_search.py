"""
utils/ticker_search.py — Search for stock tickers by name or symbol.
"""

import yfinance as yf
import requests
from typing import List, Dict
from utils.logger import log

POPULAR_TICKERS = [
    {"symbol": "AAPL",  "name": "Apple Inc"},
    {"symbol": "MSFT",  "name": "Microsoft Corporation"},
    {"symbol": "GOOGL", "name": "Alphabet Inc"},
    {"symbol": "AMZN",  "name": "Amazon.com Inc"},
    {"symbol": "NVDA",  "name": "NVIDIA Corporation"},
    {"symbol": "META",  "name": "Meta Platforms Inc"},
    {"symbol": "TSLA",  "name": "Tesla Inc"},
    {"symbol": "BRK-B", "name": "Berkshire Hathaway"},
    {"symbol": "JPM",   "name": "JPMorgan Chase"},
    {"symbol": "V",     "name": "Visa Inc"},
    {"symbol": "JNJ",   "name": "Johnson & Johnson"},
    {"symbol": "WMT",   "name": "Walmart Inc"},
    {"symbol": "XOM",   "name": "Exxon Mobil"},
    {"symbol": "MA",    "name": "Mastercard Inc"},
    {"symbol": "PG",    "name": "Procter & Gamble"},
    {"symbol": "HD",    "name": "Home Depot"},
    {"symbol": "BAC",   "name": "Bank of America"},
    {"symbol": "KO",    "name": "Coca-Cola Company"},
    {"symbol": "PEP",   "name": "PepsiCo Inc"},
    {"symbol": "COST",  "name": "Costco Wholesale"},
    {"symbol": "ADBE",  "name": "Adobe Inc"},
    {"symbol": "CRM",   "name": "Salesforce Inc"},
    {"symbol": "NFLX",  "name": "Netflix Inc"},
    {"symbol": "AMD",   "name": "Advanced Micro Devices"},
    {"symbol": "INTC",  "name": "Intel Corporation"},
    {"symbol": "ORCL",  "name": "Oracle Corporation"},
    {"symbol": "PYPL",  "name": "PayPal Holdings"},
    {"symbol": "UBER",  "name": "Uber Technologies"},
    {"symbol": "SHOP",  "name": "Shopify Inc"},
    {"symbol": "PLTR",  "name": "Palantir Technologies"},
    {"symbol": "COIN",  "name": "Coinbase Global"},
    {"symbol": "SNAP",  "name": "Snap Inc"},
    {"symbol": "SPY",   "name": "S&P 500 ETF (SPDR)"},
    {"symbol": "QQQ",   "name": "Nasdaq 100 ETF (Invesco)"},
    {"symbol": "IWM",   "name": "Russell 2000 ETF"},
    {"symbol": "DIA",   "name": "Dow Jones ETF (SPDR)"},
    {"symbol": "VTI",   "name": "Vanguard Total Market ETF"},
    {"symbol": "VOO",   "name": "Vanguard S&P 500 ETF"},
    {"symbol": "GLD",   "name": "Gold ETF (SPDR)"},
    {"symbol": "TLT",   "name": "20+ Year Treasury Bond ETF"},
    {"symbol": "ARKK",  "name": "ARK Innovation ETF"},
    {"symbol": "XLF",   "name": "Financial Select Sector ETF"},
    {"symbol": "XLK",   "name": "Technology Select Sector ETF"},
    {"symbol": "XLE",   "name": "Energy Select Sector ETF"},
]

ETF_SYMBOLS = {"SPY","QQQ","IWM","DIA","VTI","VOO","GLD","TLT","ARKK","XLF","XLK","XLE"}


def search_tickers(query: str, limit: int = 8) -> List[Dict]:
    if not query or len(query) < 1:
        return []
    query_up = query.strip().upper()
    try:
        url = "https://query1.finance.yahoo.com/v1/finance/search"
        params = {"q": query, "quotesCount": limit, "newsCount": 0, "listsCount": 0}
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, params=params, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            quotes = data.get("quotes", [])
            results = []
            for q in quotes:
                symbol = q.get("symbol", "")
                name   = q.get("longname") or q.get("shortname") or symbol
                exch   = q.get("exchDisp", "")
                qtype  = q.get("typeDisp", "")
                if symbol and qtype in ("Equity", "ETF", "Fund"):
                    results.append({"symbol": symbol, "name": name, "exchange": exch, "type": qtype})
            if results:
                return results[:limit]
    except Exception as e:
        log.debug(f"Yahoo search failed: {e}")

    results = []
    for t in POPULAR_TICKERS:
        sym  = t["symbol"].upper()
        name = t["name"].upper()
        if query_up in sym or query_up in name:
            results.append({
                "symbol": t["symbol"], "name": t["name"],
                "exchange": "NASDAQ/NYSE",
                "type": "ETF" if t["symbol"] in ETF_SYMBOLS else "Equity",
            })
    return results[:limit]


def validate_ticker(ticker: str) -> Dict:
    try:
        tkr = yf.Ticker(ticker.upper())
        info = tkr.fast_info
        price = info.last_price
        if price and price > 0:
            long_name = ticker.upper()
            try:
                long_name = tkr.info.get("longName", ticker.upper())
            except Exception:
                pass
            return {"valid": True, "name": long_name, "price": round(price, 2)}
    except Exception:
        pass
    return {"valid": False, "name": "", "price": 0}
