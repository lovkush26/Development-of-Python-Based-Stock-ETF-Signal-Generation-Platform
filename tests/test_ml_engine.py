"""
tests/test_ml_engine.py — Unit tests for ML signal generation engine.
"""
import pytest
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="module")
def trained_df():
    """Load and prepare a small dataset for model tests."""
    from data_ingestion.fetcher import MarketDataFetcher
    from data_ingestion.features import FeatureEngineer
    fetcher = MarketDataFetcher()
    fe = FeatureEngineer()
    df = fetcher.get_ohlcv("SPY", period="1y")
    df = fe.add_all_features(df)
    df = fe.add_target_labels(df)
    df.dropna(inplace=True)
    return df


class TestSignalResult:
    def test_signal_result_fields(self):
        from ml_engine.models import SignalResult
        sr = SignalResult(
            ticker="AAPL", signal="BUY", confidence=0.85,
            model_name="RandomForest", price=185.0, timestamp="2024-01-01"
        )
        assert sr.signal in ("BUY", "SELL", "HOLD")
        assert 0.0 <= sr.confidence <= 1.0
        assert sr.ticker == "AAPL"


class TestRandomForestSignal:
    def test_train_returns_metrics(self, trained_df):
        from ml_engine.models import RandomForestSignal
        rf = RandomForestSignal(n_estimators=50)
        metrics = rf.train(trained_df)
        assert "cv_accuracy_mean" in metrics
        assert 0 < metrics["cv_accuracy_mean"] < 1

    def test_predict_returns_signals(self, trained_df):
        from ml_engine.models import RandomForestSignal
        rf = RandomForestSignal(n_estimators=50)
        rf.train(trained_df)
        signals = rf.predict(trained_df.tail(30), ticker="SPY")
        assert isinstance(signals, list)

    def test_predict_signals_valid(self, trained_df):
        from ml_engine.models import RandomForestSignal
        rf = RandomForestSignal(n_estimators=50)
        rf.train(trained_df)
        signals = rf.predict(trained_df.tail(60), ticker="SPY")
        for s in signals:
            assert s.signal in ("BUY", "SELL", "HOLD")
            assert 0.0 <= s.confidence <= 1.0

    def test_save_and_load(self, trained_df, tmp_path):
        from ml_engine.models import RandomForestSignal
        rf = RandomForestSignal(n_estimators=50)
        rf.MODEL_DIR = str(tmp_path)
        rf.train(trained_df)
        rf.save()
        rf2 = RandomForestSignal(n_estimators=50)
        rf2.MODEL_DIR = str(tmp_path)
        rf2.load()
        assert rf2._is_trained


class TestXGBoostSignal:
    def test_train_and_predict(self, trained_df):
        from ml_engine.models import XGBoostSignal
        xgb = XGBoostSignal()
        metrics = xgb.train(trained_df)
        assert "cv_accuracy_mean" in metrics
        signals = xgb.predict(trained_df.tail(30), ticker="SPY")
        assert isinstance(signals, list)


class TestSignalRunner:
    def test_runner_runs_after_training(self, trained_df):
        from ml_engine.signal_runner import SignalRunner
        runner = SignalRunner(tickers=["SPY"])
        runner.train(train_ticker="SPY")
        signals = runner.run()
        assert isinstance(signals, list)

    def test_signals_to_dataframe(self, trained_df):
        from ml_engine.signal_runner import SignalRunner
        runner = SignalRunner(tickers=["SPY"])
        runner.train(train_ticker="SPY")
        runner.run()
        df = runner.signals_to_dataframe()
        if not df.empty:
            assert "ticker" in df.columns
            assert "signal" in df.columns
