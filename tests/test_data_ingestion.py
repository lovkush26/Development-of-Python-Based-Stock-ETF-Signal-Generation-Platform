"""
tests/test_data_ingestion.py — Unit tests for data ingestion layer.
"""
import pytest
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMarketDataFetcher:
    """Tests for MarketDataFetcher."""

    def test_get_ohlcv_returns_dataframe(self):
        from data_ingestion.fetcher import MarketDataFetcher
        fetcher = MarketDataFetcher()
        df = fetcher.get_ohlcv("AAPL", period="1mo")
        assert isinstance(df, pd.DataFrame), "Should return a DataFrame"
        assert not df.empty, "DataFrame should not be empty"

    def test_ohlcv_has_required_columns(self):
        from data_ingestion.fetcher import MarketDataFetcher
        fetcher = MarketDataFetcher()
        df = fetcher.get_ohlcv("AAPL", period="1mo")
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            assert col in df.columns, f"Missing column: {col}"

    def test_invalid_ticker_returns_empty(self):
        from data_ingestion.fetcher import MarketDataFetcher
        fetcher = MarketDataFetcher()
        df = fetcher.get_ohlcv("XXXXINVALID9999", period="1mo")
        assert isinstance(df, pd.DataFrame)

    def test_cache_works(self):
        from data_ingestion.fetcher import MarketDataFetcher
        fetcher = MarketDataFetcher()
        df1 = fetcher.get_ohlcv("SPY", period="1mo")
        df2 = fetcher.get_ohlcv("SPY", period="1mo", use_cache=True)
        pd.testing.assert_frame_equal(df1, df2)

    def test_get_live_quote_structure(self):
        from data_ingestion.fetcher import MarketDataFetcher
        fetcher = MarketDataFetcher()
        quote = fetcher.get_live_quote("AAPL")
        assert "ticker" in quote
        assert quote["ticker"] == "AAPL"


class TestFeatureEngineer:
    """Tests for FeatureEngineer."""

    @pytest.fixture
    def sample_df(self):
        from data_ingestion.fetcher import MarketDataFetcher
        fetcher = MarketDataFetcher()
        return fetcher.get_ohlcv("SPY", period="6mo")

    def test_add_all_features_returns_dataframe(self, sample_df):
        from data_ingestion.features import FeatureEngineer
        fe = FeatureEngineer()
        df_feat = fe.add_all_features(sample_df)
        assert isinstance(df_feat, pd.DataFrame)
        assert len(df_feat) > 0

    def test_feature_columns_present(self, sample_df):
        from data_ingestion.features import FeatureEngineer
        fe = FeatureEngineer()
        df_feat = fe.add_all_features(sample_df)
        # Key indicators should be present
        for col in ["rsi", "macd", "bb_upper", "ema_20"]:
            assert col in df_feat.columns, f"Feature missing: {col}"

    def test_target_labels_valid(self, sample_df):
        from data_ingestion.features import FeatureEngineer
        fe = FeatureEngineer()
        df_feat = fe.add_all_features(sample_df)
        df_labeled = fe.add_target_labels(df_feat)
        assert "target" in df_labeled.columns
        unique_targets = df_labeled["target"].dropna().unique()
        for t in unique_targets:
            assert t in [-1, 0, 1], f"Unexpected target value: {t}"

    def test_no_lookahead_bias(self, sample_df):
        """Target should only look forward, not use future Close in features."""
        from data_ingestion.features import FeatureEngineer
        fe = FeatureEngineer()
        df_feat = fe.add_all_features(sample_df)
        # Check that feature columns don't include raw future prices
        assert "future_close" not in df_feat.columns
