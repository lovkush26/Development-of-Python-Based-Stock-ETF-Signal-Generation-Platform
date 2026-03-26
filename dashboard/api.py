import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from config.settings import get_settings
from utils.logger import log

settings = get_settings()
DEFAULT_TICKERS = ["AAPL","NVDA","TSLA","MSFT","GOOGL","AMZN","META","SPY","QQQ"]

app = FastAPI(title="AlphaSignal API", version="2.4.0", docs_url="/api/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

_runner = None
_fetcher = None

def get_runner():
    global _runner
    if _runner is None:
        from ml_engine.signal_runner import SignalRunner
        _runner = SignalRunner()
        try: _runner.load_models()
        except Exception: pass
    return _runner

def get_fetcher():
    global _fetcher
    if _fetcher is None:
        from data_ingestion.fetcher import MarketDataFetcher
        _fetcher = MarketDataFetcher()
    return _fetcher

class UserCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    channels: List[str] = ["sms"]
    min_confidence: float = 0.65
    tickers: Optional[List[str]] = None

class AlertRequest(BaseModel):
    ticker: str; signal: str; confidence: float; price: float

class TrainRequest(BaseModel):
    train_ticker: str = "SPY"

@app.get("/api/health")
def health():
    return {"status":"ok","timestamp":datetime.now().isoformat(),"version":"2.4.0"}

@app.get("/api/quotes")
def get_quotes(tickers: str = Query(default=",".join(DEFAULT_TICKERS))):
    ticker_list = [t.strip().upper() for t in tickers.split(",")]
    fetcher = get_fetcher()
    quotes = fetcher.get_batch_quotes(ticker_list)
    return [q for q in quotes if "error" not in q]

@app.get("/api/signals")
def get_signals(tickers: str = Query(default=",".join(DEFAULT_TICKERS))):
    ticker_list = [t.strip().upper() for t in tickers.split(",")]
    fetcher = get_fetcher()
    from data_ingestion.features import FeatureEngineer
    fe = FeatureEngineer()
    results = []
    for ticker in ticker_list:
        try:
            q = fetcher.get_live_quote(ticker)
            price = q.get("price", 0)
            change = q.get("change_pct", 0)
            df = fetcher.get_ohlcv(ticker, period="6mo")
            if df.empty or len(df) < 60: continue
            df = fe.add_all_features(df)
            df = fe.add_target_labels(df)
            df.dropna(inplace=True)
            if df.empty: continue
            r = df.tail(1)
            rsi  = float(r["rsi"].values[0])          if "rsi"          in r.columns else 50
            macd = float(r["macd_hist"].values[0])    if "macd_hist"    in r.columns else 0
            bb   = float(r["bb_pct"].values[0])       if "bb_pct"       in r.columns else 0.5
            vol  = float(r["volume_ratio"].values[0]) if "volume_ratio" in r.columns else 1
            bs = ss = 0.0
            if rsi<=25: bs+=2.5
            elif rsi<=35: bs+=2.0
            elif rsi<=42: bs+=1.5
            elif rsi<=48: bs+=0.5
            elif rsi>=75: ss+=2.5
            elif rsi>=65: ss+=2.0
            elif rsi>=58: ss+=1.5
            elif rsi>=52: ss+=0.5
            mn = macd / 0.5
            if mn>2.0: bs+=2.5
            elif mn>0.5: bs+=2.0
            elif mn>0.0: bs+=1.0
            elif mn<-2.0: ss+=2.5
            elif mn<-0.5: ss+=2.0
            else: ss+=1.0
            if bb<0.10: bs+=2.0
            elif bb<0.20: bs+=1.5
            elif bb<0.30: bs+=1.0
            elif bb>0.90: ss+=2.0
            elif bb>0.80: ss+=1.5
            elif bb>0.70: ss+=1.0
            if change>3.0: bs+=1.5
            elif change>1.5: bs+=1.0
            elif change>0.5: bs+=0.5
            elif change<-3.0: ss+=1.5
            elif change<-1.5: ss+=1.0
            elif change<-0.5: ss+=0.5
            if vol>2.0 and change>0: bs+=1.0
            elif vol>1.3 and change>0: bs+=0.5
            elif vol>2.0 and change<0: ss+=1.0
            elif vol>1.3 and change<0: ss+=0.5
            gp = abs(bs-ss)
            if bs>ss and gp>=1.0:
                sig="BUY"; cf=min(0.95,0.60+(bs/8.5)*0.35)
            elif ss>bs and gp>=1.0:
                sig="SELL"; cf=min(0.95,0.60+(ss/8.5)*0.35)
            else:
                sig="HOLD"; cf=min(0.75,0.50+gp*0.08)
            results.append({"ticker":ticker,"signal":sig,"confidence":round(cf,3),
                "price":price,"change_pct":change,"rsi":round(rsi,1),
                "macd":round(macd,4),"bb_pct":round(bb*100,1),
                "volume_ratio":round(vol,2),"timestamp":datetime.now().isoformat()})
        except Exception as e:
            log.error(f"Signal error {ticker}: {e}")
    return results

@app.get("/api/signal/{ticker}")
def get_signal(ticker: str):
    return get_signals(tickers=ticker.upper())

@app.get("/api/history/{ticker}")
def get_history(ticker: str, period: str = "6mo"):
    fetcher = get_fetcher()
    df = fetcher.get_ohlcv(ticker.upper(), period=period)
    if df.empty:
        raise HTTPException(404, f"No data for {ticker}")
    df = df.reset_index()
    return [{"date":str(r["Date"])[:10],"open":round(float(r["Open"]),2),
             "high":round(float(r["High"]),2),"low":round(float(r["Low"]),2),
             "close":round(float(r["Close"]),2),"volume":int(r["Volume"])}
            for _,r in df.iterrows()]

@app.get("/api/backtest/{ticker}")
def run_backtest(ticker: str, period: str = "2y", capital: float = 100000):
    ticker = ticker.upper()
    try:
        from data_ingestion.fetcher import MarketDataFetcher
        from data_ingestion.features import FeatureEngineer
        from backtesting.engine import BacktestEngine
        fetcher = MarketDataFetcher()
        fe = FeatureEngineer()
        engine = BacktestEngine(initial_capital=capital)
        df = fetcher.get_ohlcv(ticker, period=period)
        if df.empty: raise HTTPException(404, f"No data for {ticker}")
        df = fe.add_all_features(df)
        df = fe.add_target_labels(df)
        df.dropna(inplace=True)
        df["signal"] = df["target"]
        result = engine.run(df, ticker=ticker)
        summary = result.summary()
        equity = [{"date":str(d)[:10],"value":round(float(v),2)}
                  for d,v in result.equity_curve.items()]
        return {**summary,"equity_curve":equity}
    except HTTPException: raise
    except Exception as e: raise HTTPException(500, str(e))

@app.post("/api/train")
def train_models(request: TrainRequest, background_tasks: BackgroundTasks):
    def _train():
        runner = get_runner()
        metrics = runner.train(train_ticker=request.train_ticker)
        log.info(f"Training done: {metrics}")
    background_tasks.add_task(_train)
    return {"message":"Training started","train_ticker":request.train_ticker}

@app.get("/api/watchlist")
def get_watchlist_route():
    from utils.ticker_store import get_watchlist as gw
    return {"tickers": gw()}

@app.post("/api/watchlist/{ticker}")
def add_ticker_route(ticker: str):
    from utils.ticker_store import add_ticker as at
    from utils.ticker_search import validate_ticker as vt
    info = vt(ticker.upper())
    if not info["valid"]:
        raise HTTPException(400, f"Invalid ticker: {ticker}")
    ok = at(ticker.upper())
    return {"success":ok,"ticker":ticker.upper(),"name":info["name"]}

@app.delete("/api/watchlist/{ticker}")
def remove_ticker_route(ticker: str):
    from utils.ticker_store import remove_ticker as rt
    rt(ticker.upper())
    return {"success":True,"ticker":ticker.upper()}

@app.get("/api/search")
def search_route(q: str = Query(default="")):
    from utils.ticker_search import search_tickers as st
    return {"results": st(q, limit=8)}

@app.get("/api/users")
def get_users():
    from utils.user_store import get_all_users
    return {"users": get_all_users()}

@app.post("/api/users")
def create_user(user: UserCreate):
    from utils.user_store import add_user
    ok = add_user(name=user.name, phone=user.phone, email=user.email,
                  channels=user.channels, min_confidence=user.min_confidence,
                  tickers=user.tickers)
    if not ok: raise HTTPException(400, f"User already exists")
    return {"success":True,"name":user.name}

@app.delete("/api/users/{user_id}")
def delete_user_route(user_id: int):
    from utils.user_store import delete_user as du
    du(user_id)
    return {"success":True}

@app.get("/api/alerts/history")
def get_alert_history(user_name: Optional[str] = None, limit: int = 50):
    from utils.user_store import get_alert_history as gah
    return {"history": gah(user_name=user_name, limit=limit)}

@app.post("/api/alerts/send")
def send_alert(req: AlertRequest):
    try:
        from alerting.notifier import AlertNotifier
        AlertNotifier().send_signal_alert(req.ticker,req.signal,req.confidence,req.price)
        return {"success":True}
    except Exception as e: raise HTTPException(500, str(e))

@app.post("/api/alerts/run")
def run_and_alert(tickers: str = Query(default=""), min_confidence: float = Query(default=0.65)):
    from utils.ticker_store import get_watchlist
    from alerting.notifier import AlertNotifier
    scan = [t.strip().upper() for t in tickers.split(",") if t.strip()] or get_watchlist()
    signals_data = get_signals(tickers=",".join(scan))
    notifier = AlertNotifier()
    alerted = []
    for s in signals_data:
        if s["signal"] != "HOLD" and s["confidence"] >= min_confidence:
            notifier.send_signal_alert(s["ticker"],s["signal"],s["confidence"],s["price"])
            alerted.append(s)
    return {"scanned":len(signals_data),"alerted":len(alerted),"alerts":alerted}
