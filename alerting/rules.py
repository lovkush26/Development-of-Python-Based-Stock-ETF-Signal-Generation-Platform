"""
alerting/rules.py — Rule-based alert triggers.

Defines configurable alert rules (price thresholds, RSI levels, etc.)
and an AlertEngine that evaluates them on each data tick.
"""

from dataclasses import dataclass
from typing import Callable, Optional, List
import pandas as pd
from utils.logger import log


@dataclass
class AlertRule:
    """A single alert rule definition."""
    name: str
    description: str
    condition: Callable[[pd.Series], bool]  # Takes latest row, returns True to trigger
    message_template: str  # Use {ticker}, {value}, {threshold}
    cooldown_minutes: int = 60     # Minimum time between repeated alerts
    enabled: bool = True
    _last_triggered: Optional[str] = None

    def evaluate(self, row: pd.Series, ticker: str) -> Optional[str]:
        """Evaluate rule against a data row. Returns alert message or None."""
        if not self.enabled:
            return None
        try:
            if self.condition(row):
                msg = self.message_template.format(
                    ticker=ticker,
                    value=round(row.get("Close", 0), 2),
                    rsi=round(row.get("rsi", 0), 1),
                    volume=int(row.get("Volume", 0)),
                )
                return msg
        except Exception as e:
            log.debug(f"Rule '{self.name}' evaluation error: {e}")
        return None


class AlertEngine:
    """
    Evaluates a set of AlertRules against incoming market data.

    Usage:
        engine = AlertEngine()
        engine.add_default_rules()
        triggered = engine.evaluate(df_row, ticker="AAPL")
    """

    def __init__(self):
        self.rules: List[AlertRule] = []

    def add_rule(self, rule: AlertRule):
        self.rules.append(rule)
        log.debug(f"Added alert rule: {rule.name}")

    def add_default_rules(self):
        """Register the standard set of market alert rules."""

        # RSI overbought
        self.add_rule(AlertRule(
            name="rsi_overbought",
            description="RSI above 70 — potential reversal",
            condition=lambda row: row.get("rsi", 50) >= 70,
            message_template="⚠️ {ticker} RSI overbought ({rsi}) — watch for reversal",
        ))

        # RSI oversold
        self.add_rule(AlertRule(
            name="rsi_oversold",
            description="RSI below 30 — potential bounce",
            condition=lambda row: row.get("rsi", 50) <= 30,
            message_template="📉 {ticker} RSI oversold ({rsi}) — potential buy opportunity",
        ))

        # Price crosses 50-day SMA upward
        self.add_rule(AlertRule(
            name="price_above_sma50",
            description="Price crossed above 50-day SMA",
            condition=lambda row: (
                row.get("Close", 0) > row.get("sma_50", 0)
                and row.get("sma_cross_signal", 0) == 1
            ),
            message_template="📈 {ticker} crossed above 50-day SMA at ${value}",
        ))

        # Bollinger Band squeeze (low volatility breakout setup)
        self.add_rule(AlertRule(
            name="bb_squeeze",
            description="Bollinger Bands squeezed — breakout imminent",
            condition=lambda row: row.get("bb_width", 1) < 0.05,
            message_template="🔔 {ticker} Bollinger Band squeeze detected at ${value}",
        ))

        # Volume anomaly (2x average)
        self.add_rule(AlertRule(
            name="volume_spike",
            description="Volume 2x above 20-day average",
            condition=lambda row: (
                row.get("Volume", 0) > row.get("volume_sma_20", 1) * 2
            ),
            message_template="📊 {ticker} volume spike: {volume:,} shares (2x average)",
        ))

    def evaluate(self, row: pd.Series, ticker: str) -> List[str]:
        """
        Evaluate all active rules against one data row.
        Returns list of triggered alert messages.
        """
        messages = []
        for rule in self.rules:
            msg = rule.evaluate(row, ticker)
            if msg:
                messages.append(msg)
                log.info(f"Alert triggered [{rule.name}]: {msg}")
        return messages

    def evaluate_dataframe(self, df: pd.DataFrame, ticker: str) -> List[dict]:
        """Evaluate rules on every row of a DataFrame. Returns alert history."""
        alerts = []
        for idx, row in df.iterrows():
            msgs = self.evaluate(row, ticker)
            for msg in msgs:
                alerts.append({"date": str(idx), "ticker": ticker, "message": msg})
        return alerts

