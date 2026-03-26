"""
utils/database.py — SQLAlchemy ORM models and DB session management.

Tables:
  - signals       : Generated buy/sell/hold signals with metadata
  - backtest_runs : Stored backtest results and metrics
  - alert_log     : History of sent alerts

Usage:
    from utils.database import get_db, Signal, init_db
    init_db()
    with get_db() as db:
        db.add(Signal(...))
        db.commit()
"""

from contextlib import contextmanager
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, String, Float, Integer,
    DateTime, Text, Boolean, JSON
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from config.settings import get_settings
from utils.logger import log

settings = get_settings()

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ── ORM Models ────────────────────────────────────────────────────────────────

class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), nullable=False, index=True)
    signal = Column(String(4), nullable=False)        # BUY | SELL | HOLD
    confidence = Column(Float, nullable=False)
    model_name = Column(String(50))
    price = Column(Float)
    features = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<Signal {self.ticker} {self.signal} {self.confidence:.2f}>"


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), nullable=False, index=True)
    period = Column(String(10))
    initial_capital = Column(Float)
    final_capital = Column(Float)
    total_return_pct = Column(Float)
    sharpe_ratio = Column(Float)
    sortino_ratio = Column(Float)
    max_drawdown_pct = Column(Float)
    win_rate_pct = Column(Float)
    n_trades = Column(Integer)
    metrics_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class AlertLog(Base):
    __tablename__ = "alert_log"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), index=True)
    alert_type = Column(String(50))    # signal | threshold | system
    message = Column(Text)
    channel = Column(String(20))       # slack | email | sms
    delivered = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class ModelTrainRun(Base):
    __tablename__ = "model_train_runs"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(50))
    train_ticker = Column(String(10))
    cv_accuracy_mean = Column(Float)
    cv_accuracy_std = Column(Float)
    n_samples = Column(Integer)
    n_features = Column(Integer)
    metrics_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── DB helpers ────────────────────────────────────────────────────────────────

def init_db():
    """Create all tables (safe to call multiple times)."""
    Base.metadata.create_all(bind=engine)
    log.info("Database tables created/verified.")


@contextmanager
def get_db() -> Session:
    """Context manager for a DB session with auto-commit/rollback."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def save_signal(signal) -> None:
    """Persist a SignalResult to the database."""
    from utils.database import Signal as SignalModel
    with get_db() as db:
        record = SignalModel(
            ticker=signal.ticker,
            signal=signal.signal,
            confidence=signal.confidence,
            model_name=signal.model_name,
            price=signal.price,
            features=signal.features,
        )
        db.add(record)
    log.debug(f"Saved signal: {signal.ticker} {signal.signal}")


def save_backtest(result, period: str = "unknown") -> None:
    """Persist a BacktestResult to the database."""
    summary = result.summary()
    with get_db() as db:
        record = BacktestRun(
            ticker=result.ticker,
            period=period,
            initial_capital=summary["initial_capital"],
            final_capital=summary["final_capital"],
            total_return_pct=summary["total_return_pct"],
            sharpe_ratio=summary["sharpe_ratio"],
            sortino_ratio=summary["sortino_ratio"],
            max_drawdown_pct=summary["max_drawdown_pct"],
            win_rate_pct=summary["win_rate_pct"],
            n_trades=summary["n_trades"],
            metrics_json=summary,
        )
        db.add(record)
