"""
tests/test_backtesting.py — Unit tests for backtesting engine and metrics.
"""
import pytest
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def simple_df():
    """Minimal OHLCV + signal DataFrame for deterministic tests."""
    np.random.seed(42)
    n = 120
    price = 100 + np.cumsum(np.random.randn(n) * 0.5)
    signals = np.zeros(n, dtype=int)
    signals[10] = 1   # BUY
    signals[30] = -1  # SELL (close)
    signals[50] = 1
    signals[70] = -1
    signals[90] = 1

    return pd.DataFrame({
        "Open": price * 0.999,
        "High": price * 1.002,
        "Low": price * 0.998,
        "Close": price,
        "Volume": np.random.randint(1_000_000, 5_000_000, n),
        "signal": signals,
    }, index=pd.date_range("2023-01-01", periods=n, freq="B"))


class TestBacktestEngine:
    def test_run_returns_result(self, simple_df):
        from backtesting.engine import BacktestEngine
        engine = BacktestEngine(initial_capital=100_000)
        result = engine.run(simple_df, ticker="TEST")
        assert result is not None
        assert result.ticker == "TEST"

    def test_equity_curve_length(self, simple_df):
        from backtesting.engine import BacktestEngine
        engine = BacktestEngine()
        result = engine.run(simple_df)
        assert len(result.equity_curve) == len(simple_df)

    def test_initial_capital_preserved_no_trades(self):
        from backtesting.engine import BacktestEngine
        import pandas as pd, numpy as np
        df = pd.DataFrame({
            "Close": [100.0] * 30, "Open": [100.0] * 30,
            "High": [101.0] * 30, "Low": [99.0] * 30,
            "Volume": [1_000_000] * 30, "signal": [0] * 30,
        }, index=pd.date_range("2023-01-01", periods=30, freq="B"))
        engine = BacktestEngine(initial_capital=50_000)
        result = engine.run(df)
        assert abs(result.final_capital - 50_000) < 100

    def test_win_rate_in_valid_range(self, simple_df):
        from backtesting.engine import BacktestEngine
        engine = BacktestEngine()
        result = engine.run(simple_df)
        assert 0 <= result.win_rate <= 100

    def test_sharpe_is_finite(self, simple_df):
        from backtesting.engine import BacktestEngine
        engine = BacktestEngine()
        result = engine.run(simple_df)
        assert np.isfinite(result.sharpe_ratio)

    def test_max_drawdown_is_negative_or_zero(self, simple_df):
        from backtesting.engine import BacktestEngine
        engine = BacktestEngine()
        result = engine.run(simple_df)
        assert result.max_drawdown <= 0

    def test_summary_keys(self, simple_df):
        from backtesting.engine import BacktestEngine
        engine = BacktestEngine()
        result = engine.run(simple_df)
        summary = result.summary()
        for key in ["total_return_pct", "sharpe_ratio", "max_drawdown_pct", "win_rate_pct", "n_trades"]:
            assert key in summary


class TestPerformanceMetrics:
    def test_monthly_returns(self, simple_df):
        from backtesting.engine import BacktestEngine
        from backtesting.metrics import PerformanceMetrics
        engine = BacktestEngine()
        result = engine.run(simple_df)
        monthly = PerformanceMetrics.monthly_returns(result.equity_curve)
        assert isinstance(monthly, pd.DataFrame)
        assert "return_pct" in monthly.columns

    def test_full_report_extra_keys(self, simple_df):
        from backtesting.engine import BacktestEngine
        from backtesting.metrics import PerformanceMetrics
        engine = BacktestEngine()
        result = engine.run(simple_df)
        report = PerformanceMetrics.full_report(result)
        assert "profit_factor" in report
        assert "total_pnl" in report
