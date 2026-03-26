"""
data_ingestion/features.py — Technical indicator feature engineering.

Computes RSI, MACD, Bollinger Bands, EMA crosses, ATR, OBV, and more.
All features are added as columns to the input DataFrame.
"""

import pandas as pd
import numpy as np
from typing import Optional
from utils.logger import log


class FeatureEngineer:
    """
    Adds technical indicator features to OHLCV DataFrames.

    Usage:
        fe = FeatureEngineer()
        df_with_features = fe.add_all_features(df)
        df_with_labels   = fe.add_target_labels(df_with_features)
    """

    FEATURE_COLUMNS = [
        # Price-derived
        "returns_1d", "returns_5d", "returns_10d",
        "log_return",
        # Momentum
        "rsi", "rsi_14",
        "macd", "macd_signal", "macd_hist",
        "stoch_k", "stoch_d",
        "williams_r",
        # Trend
        "ema_9", "ema_20", "ema_50", "ema_200",
        "sma_20", "sma_50",
        "ema_cross_9_20", "ema_cross_20_50",
        "sma_cross_signal",
        "price_vs_ema20", "price_vs_sma50",
        "adx",
        # Volatility
        "bb_upper", "bb_lower", "bb_mid", "bb_width", "bb_pct",
        "atr", "atr_pct",
        "daily_range_pct",
        "volatility_20d",
        # Volume
        "volume_sma_20", "volume_ratio",
        "obv", "obv_ma",
        "cmf",
        # Pattern helpers
        "higher_high", "lower_low",
    ]

    @property
    def feature_columns(self):
        return self.FEATURE_COLUMNS

    def add_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add all technical indicators and return enriched DataFrame."""
        df = df.copy()
        try:
            df = self._add_price_features(df)
            df = self._add_momentum(df)
            df = self._add_trend(df)
            df = self._add_volatility(df)
            df = self._add_volume_features(df)
            df = self._add_pattern_features(df)
        except Exception as e:
            log.error(f"Feature engineering error: {e}")
        return df

    def add_target_labels(
        self, df: pd.DataFrame, lookahead: int = 5, threshold: float = 0.02
    ) -> pd.DataFrame:
        """
        Add target labels for supervised learning.

        Labels:
          +1 (BUY)  — price rises > threshold over next `lookahead` days
          -1 (SELL) — price falls > threshold
           0 (HOLD) — otherwise

        Args:
            lookahead:  Days to look ahead for return calculation
            threshold:  Minimum return magnitude to label as BUY/SELL
        """
        df = df.copy()
        future_return = df["Close"].shift(-lookahead) / df["Close"] - 1
        df["target"] = 0
        df.loc[future_return > threshold, "target"] = 1
        df.loc[future_return < -threshold, "target"] = -1
        return df

    # ── Private feature builders ──────────────────────────────────────────────

    def _add_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df["returns_1d"] = df["Close"].pct_change(1)
        df["returns_5d"] = df["Close"].pct_change(5)
        df["returns_10d"] = df["Close"].pct_change(10)
        df["log_return"] = np.log(df["Close"] / df["Close"].shift(1))
        return df

    def _add_momentum(self, df: pd.DataFrame) -> pd.DataFrame:
        # RSI
        delta = df["Close"].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        df["rsi"] = 100 - (100 / (1 + rs))
        df["rsi_14"] = df["rsi"]  # alias

        # MACD
        ema12 = df["Close"].ewm(span=12, adjust=False).mean()
        ema26 = df["Close"].ewm(span=26, adjust=False).mean()
        df["macd"] = ema12 - ema26
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]

        # Stochastic
        low14 = df["Low"].rolling(14).min()
        high14 = df["High"].rolling(14).max()
        denom = (high14 - low14).replace(0, np.nan)
        df["stoch_k"] = 100 * (df["Close"] - low14) / denom
        df["stoch_d"] = df["stoch_k"].rolling(3).mean()

        # Williams %R
        df["williams_r"] = -100 * (high14 - df["Close"]) / denom

        return df

    def _add_trend(self, df: pd.DataFrame) -> pd.DataFrame:
        # EMAs / SMAs
        for span in [9, 20, 50, 200]:
            df[f"ema_{span}"] = df["Close"].ewm(span=span, adjust=False).mean()
        for window in [20, 50]:
            df[f"sma_{window}"] = df["Close"].rolling(window).mean()

        # EMA cross signals
        df["ema_cross_9_20"] = (df["ema_9"] > df["ema_20"]).astype(int)
        df["ema_cross_20_50"] = (df["ema_20"] > df["ema_50"]).astype(int)
        df["sma_cross_signal"] = (
            (df["sma_20"] > df["sma_50"]) & (df["sma_20"].shift(1) <= df["sma_50"].shift(1))
        ).astype(int)

        # Price relative to MAs
        df["price_vs_ema20"] = (df["Close"] - df["ema_20"]) / df["ema_20"]
        df["price_vs_sma50"] = (df["Close"] - df["sma_50"]) / df["sma_50"]

        # ADX
        tr = pd.concat([
            df["High"] - df["Low"],
            (df["High"] - df["Close"].shift()).abs(),
            (df["Low"] - df["Close"].shift()).abs(),
        ], axis=1).max(axis=1)
        df["adx"] = tr.rolling(14).mean()  # simplified ATR-based proxy

        return df

    def _add_volatility(self, df: pd.DataFrame) -> pd.DataFrame:
        # Bollinger Bands
        df["bb_mid"] = df["Close"].rolling(20).mean()
        bb_std = df["Close"].rolling(20).std()
        df["bb_upper"] = df["bb_mid"] + 2 * bb_std
        df["bb_lower"] = df["bb_mid"] - 2 * bb_std
        band_width = (df["bb_upper"] - df["bb_lower"]).replace(0, np.nan)
        df["bb_width"] = band_width / df["bb_mid"]
        df["bb_pct"] = (df["Close"] - df["bb_lower"]) / band_width

        # ATR
        tr = pd.concat([
            df["High"] - df["Low"],
            (df["High"] - df["Close"].shift()).abs(),
            (df["Low"] - df["Close"].shift()).abs(),
        ], axis=1).max(axis=1)
        df["atr"] = tr.ewm(span=14, adjust=False).mean()
        df["atr_pct"] = df["atr"] / df["Close"]

        # Daily range
        df["daily_range_pct"] = (df["High"] - df["Low"]) / df["Close"]

        # Rolling volatility
        df["volatility_20d"] = df["returns_1d"].rolling(20).std()

        return df

    def _add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df["volume_sma_20"] = df["Volume"].rolling(20).mean()
        df["volume_ratio"] = df["Volume"] / df["volume_sma_20"].replace(0, np.nan)

        # OBV
        obv = (np.sign(df["Close"].diff()) * df["Volume"]).fillna(0).cumsum()
        df["obv"] = obv
        df["obv_ma"] = obv.rolling(20).mean()

        # Chaikin Money Flow
        mf_multiplier = (
            (2 * df["Close"] - df["Low"] - df["High"]) /
            (df["High"] - df["Low"]).replace(0, np.nan)
        )
        mf_volume = mf_multiplier * df["Volume"]
        df["cmf"] = mf_volume.rolling(20).sum() / df["Volume"].rolling(20).sum().replace(0, np.nan)

        return df

    def _add_pattern_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df["higher_high"] = (df["High"] > df["High"].shift(1)).astype(int)
        df["lower_low"] = (df["Low"] < df["Low"].shift(1)).astype(int)
        return df
