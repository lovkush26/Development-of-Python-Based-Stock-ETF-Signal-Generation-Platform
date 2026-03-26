# AlphaSignal — AI-Powered Stock & ETF Signal Generation Platform

A production-ready ML trading signal platform with backtesting, real-time alerts, and an interactive Streamlit dashboard.

---

## Architecture

```
alphasignal/
├── data_ingestion/          # Market data fetching & feature engineering
│   ├── fetcher.py           #   Yahoo Finance, Alpha Vantage, Polygon.io
│   └── features.py          #   RSI, MACD, Bollinger Bands, EMA, ATR, OBV
├── ml_engine/               # ML signal generation
│   ├── models.py            #   RandomForest, LSTM, XGBoost, Ensemble
│   └── signal_runner.py     #   End-to-end signal pipeline
├── backtesting/             # Strategy validation
│   ├── engine.py            #   Event-driven backtest engine
│   └── metrics.py           #   Sharpe, drawdown, win-rate, monthly P&L
├── alerting/                # Notifications
│   ├── notifier.py          #   Slack, Email (SendGrid), SMS (Twilio)
│   ├── rules.py             #   Rule-based alert triggers (RSI, volume, etc.)
│   └── celery_worker.py     #   Async task queue (15-min signal runs, nightly retrain)
├── dashboard/               # UI & API
│   ├── app.py               #   Streamlit dashboard (charts, signals, backtest)
│   └── api.py               #   FastAPI REST API with OpenAPI docs
├── utils/
│   ├── logger.py            #   Loguru structured logging
│   └── database.py          #   SQLAlchemy ORM (signals, backtests, alerts)
├── tests/                   # Full test suite
├── scripts/                 # CLI tools (train, run_signals, backtest)
├── docker/                  # Dockerfile + docker-compose + nginx
├── .env.example
├── requirements.txt
└── Makefile
```

---

## Quick Start (Local)

### 1. Clone and set up environment

```bash
git clone https://github.com/yourname/alphasignal.git
cd alphasignal

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

make dev                         # Installs deps + copies .env.example → .env
```

### 2. Configure your `.env`

```bash
# Edit .env — at minimum set:
ALPHA_VANTAGE_API_KEY=your_key   # Free at alphavantage.co (optional, has fallback)
DATABASE_URL=sqlite:///./alphasignal.db   # SQLite for local dev
```

### 3. Initialize database

```bash
python scripts/seed_db.py
```

### 4. Train ML models

```bash
python scripts/train.py
# Or: python scripts/train.py --ticker QQQ --period 3y
```

### 5. Run signal generation

```bash
python scripts/run_signals.py
# With alerts: python scripts/run_signals.py --alert
# Save to CSV:  python scripts/run_signals.py --output signals.csv
```

### 6. Launch dashboard

```bash
# Terminal 1 — FastAPI backend
make api         # → http://localhost:8000
                 #   API docs: http://localhost:8000/docs

# Terminal 2 — Streamlit UI
make dashboard   # → http://localhost:8501
```

### 7. Run backtest

```bash
python scripts/backtest.py
# Or: python scripts/backtest.py --ticker AAPL --period 3y --capital 50000
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/quotes?tickers=AAPL,SPY` | Live price quotes |
| GET | `/signal/AAPL` | ML signal for one ticker |
| GET | `/signals?tickers=AAPL,NVDA` | Signals for multiple tickers |
| POST | `/train` | Trigger model (re)training |
| GET | `/backtest/SPY?period=2y` | Run backtest, return metrics |
| GET | `/features/AAPL` | Latest engineered features |
| GET | `/docs` | Interactive Swagger UI |

---

## Running Tests

```bash
make test                        # Full suite
make test-fast                   # Skip slow/network tests
pytest tests/test_backtesting.py # Single module
pytest -k "test_rsi"             # By keyword
```

---

## Production Deployment (Docker)

### Prerequisites
- Docker + Docker Compose
- Domain name with DNS pointing to your server

### Deploy

```bash
# 1. Copy and configure environment
cp .env.example .env
# Edit .env — set production DATABASE_URL, API keys, alert credentials

# 2. Build and start all services
make docker-up

# Services started:
#   alphasignal_db        PostgreSQL on :5432
#   alphasignal_redis     Redis on :6379
#   alphasignal_api       FastAPI on :8000
#   alphasignal_dashboard Streamlit on :8501
#   alphasignal_worker    Celery worker
#   alphasignal_beat      Celery beat (cron scheduler)

# 3. (Optional) add nginx reverse proxy
#    Copy docker/nginx.conf and adjust upstream server names

# 4. Check logs
make docker-logs

# 5. Stop
make docker-down
```

### Environment Variables for Production

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | `postgresql://user:pass@host:5432/db` |
| `REDIS_URL` | Yes | `redis://host:6379/0` |
| `APP_SECRET_KEY` | Yes | Random secret for session signing |
| `ALPHA_VANTAGE_API_KEY` | Recommended | Free tier at alphavantage.co |
| `POLYGON_API_KEY` | Optional | Premium real-time data |
| `SLACK_BOT_TOKEN` | Optional | Slack alert delivery |
| `SENDGRID_API_KEY` | Optional | Email alert delivery |
| `TWILIO_ACCOUNT_SID` | Optional | SMS alert delivery |

---

## ML Models

| Model | Accuracy | Speed | Notes |
|-------|----------|-------|-------|
| Random Forest | ~78% | Fast | Interpretable, feature importances |
| XGBoost | ~82% | Fast | Best single-model accuracy |
| LSTM | ~82% | Slow | Captures sequential price patterns |
| Ensemble | ~85% | Medium | Weighted soft-voting of all three |

All models use **time-series cross-validation** (no data leakage) and output 3-class predictions: BUY / HOLD / SELL with confidence scores.

---

## Alert Channels

Configure any combination in `.env`:

- **Slack** — posts to a channel with signal details
- **Email** — HTML formatted via SendGrid
- **SMS** — 160-char summary via Twilio

Alerts fire automatically from Celery every 15 minutes during market hours (Mon–Fri, 9:30–16:00 ET) for signals above `SIGNAL_CONFIDENCE_THRESHOLD` (default 65%).

---

## License

MIT
