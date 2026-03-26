"""
ml_engine/signal_runner.py — Orchestrates signal generation across tickers.

Usage:
    runner = SignalRunner(tickers=["AAPL","NVDA","SPY"])
    runner.train()
    signals = runner.run()
"""

import pandas as pd
from typing import List, Dict
from datetime import datetime

from data_ingestion.fetcher import MarketDataFetcher
from data_ingestion.features import FeatureEngineer
from ml_engine.models import (
    RandomForestSignal, XGBoostSignal, LSTMSignal,
    EnsembleSignal, SignalResult
)
from config.settings import get_settings
from utils.logger import log

settings = get_settings()


class SignalRunner:
    """
    End-to-end pipeline: fetch → features → predict → return signals.

    Args:
        tickers:    List of stock/ETF symbols
        use_lstm:   Include LSTM in ensemble (slower, requires TensorFlow)
        period:     Historical period for training data
    """

    DEFAULT_TICKERS = [
        "AAPL", "NVDA", "TSLA", "MSFT", "GOOGL",
        "AMZN", "META", "SPY", "QQQ", "BRK-B",
    ]

    def __init__(
        self,
        tickers: List[str] = None,
        use_lstm: bool = False,
        period: str = "2y",
    ):
        self.tickers = tickers or self.DEFAULT_TICKERS
        self.use_lstm = use_lstm
        self.period = period

        self.fetcher = MarketDataFetcher()
        self.feature_eng = FeatureEngineer()
        self.ensemble = EnsembleSignal()

        self._trained = False
        self._last_run: datetime = None
        self._signal_cache: List[SignalResult] = []

    def _prepare(self, ticker: str) -> pd.DataFrame:
        """Fetch and feature-engineer data for one ticker."""
        df = self.fetcher.get_ohlcv(ticker, period=self.period)
        if df.empty:
            log.warning(f"No data for {ticker}, skipping.")
            return pd.DataFrame()
        df = self.feature_eng.add_all_features(df)
        df = self.feature_eng.add_target_labels(df)
        df.dropna(inplace=True)
        return df

    def train(self, train_ticker: str = "SPY") -> dict:
        """Train all models on a single representative ticker (SPY by default)."""
        log.info(f"Training ensemble on {train_ticker}...")
        df = self._prepare(train_ticker)
        if df.empty:
            log.error("Training data empty. Cannot train.")
            return {}

        metrics = self.ensemble.train_all(df)
        self._trained = True
        log.info("Training complete.")
        return metrics

    def load_models(self):
        """Load previously saved models from disk."""
        self.ensemble.load_all()
        self._trained = True
        log.info("Models loaded from disk.")

    def run(self) -> List[SignalResult]:
        """Generate signals for all tickers. Returns list of SignalResult."""
        if not self._trained:
            log.warning("Models not trained. Call train() or load_models() first.")
            return []

        all_signals: List[SignalResult] = []

        for ticker in self.tickers:
            try:
                df = self._prepare(ticker)
                if df.empty or len(df) < 50:
                    continue

                # Use last 60 rows for inference (recent context)
                recent = df.tail(60)

                rf_sigs = self.ensemble.rf.predict(recent, ticker)
                xgb_sigs = self.ensemble.xgb.predict(recent, ticker)
                ens_sigs = self.ensemble.predict(recent, ticker)

                # Keep the latest signal from ensemble per ticker
                if ens_sigs:
                    all_signals.extend(ens_sigs)
                    log.info(
                        f"{ticker}: {ens_sigs[-1].signal} "
                        f"(conf={ens_sigs[-1].confidence:.2f})"
                    )

            except Exception as e:
                log.error(f"Signal run error for {ticker}: {e}")
                continue

        self._signal_cache = all_signals
        self._last_run = datetime.now()
        log.info(f"Signal run complete: {len(all_signals)} signals generated.")
        return all_signals

    def get_latest_signals(self) -> List[SignalResult]:
        """Return cached signals from last run."""
        return self._signal_cache

    def signals_to_dataframe(self, signals: List[SignalResult] = None) -> pd.DataFrame:
        """Convert signal list to a tidy DataFrame."""
        signals = signals or self._signal_cache
        if not signals:
            return pd.DataFrame()
        return pd.DataFrame([
            {
                "ticker": s.ticker,
                "signal": s.signal,
                "confidence": s.confidence,
                "model": s.model_name,
                "price": s.price,
                "timestamp": s.timestamp,
            }
            for s in signals
        ])


