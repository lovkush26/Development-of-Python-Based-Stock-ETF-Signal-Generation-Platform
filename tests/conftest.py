"""
tests/conftest.py — Shared pytest fixtures and configuration.
"""
import pytest
import pandas as pd
import numpy as np
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use SQLite for tests (override DATABASE_URL)
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_alphasignal.db")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("LOG_LEVEL", "WARNING")


@pytest.fixture(scope="session")
def sample_ohlcv():
    """Synthetic OHLCV DataFrame — no network calls."""
    np.random.seed(0)
    n = 300
    price = 150 + np.cumsum(np.random.randn(n) * 0.8)
    price = np.abs(price)  # No negative prices
    return pd.DataFrame({
        "Open": price * 0.998,
        "High": price * 1.003,
        "Low": price * 0.997,
        "Close": price,
        "Volume": np.random.randint(2_000_000, 8_000_000, n),
    }, index=pd.date_range("2022-01-01", periods=n, freq="B"))


@pytest.fixture(scope="session")
def featured_df(sample_ohlcv):
    """OHLCV with all features + target labels."""
    from data_ingestion.features import FeatureEngineer
    fe = FeatureEngineer()
    df = fe.add_all_features(sample_ohlcv)
    df = fe.add_target_labels(df)
    df.dropna(inplace=True)
    return df
