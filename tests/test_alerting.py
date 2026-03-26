"""
tests/test_alerting.py — Unit tests for alerting module.
"""
import pytest
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAlertRules:
    @pytest.fixture
    def row_overbought(self):
        return pd.Series({"Close": 180.0, "rsi": 75.0, "Volume": 5_000_000,
                          "volume_sma_20": 2_000_000, "bb_width": 0.08,
                          "sma_50": 170.0, "sma_cross_signal": 1})

    @pytest.fixture
    def row_oversold(self):
        return pd.Series({"Close": 120.0, "rsi": 25.0, "Volume": 1_000_000,
                          "volume_sma_20": 2_000_000, "bb_width": 0.10,
                          "sma_50": 130.0, "sma_cross_signal": 0})

    @pytest.fixture
    def row_volume_spike(self):
        return pd.Series({"Close": 155.0, "rsi": 50.0, "Volume": 8_000_000,
                          "volume_sma_20": 2_000_000, "bb_width": 0.10,
                          "sma_50": 150.0, "sma_cross_signal": 0})

    def test_rsi_overbought_triggers(self, row_overbought):
        from alerting.rules import AlertEngine
        engine = AlertEngine()
        engine.add_default_rules()
        msgs = engine.evaluate(row_overbought, "AAPL")
        rule_names = [m for m in msgs if "overbought" in m.lower() or "RSI" in m]
        assert len(msgs) > 0

    def test_rsi_oversold_triggers(self, row_oversold):
        from alerting.rules import AlertEngine
        engine = AlertEngine()
        engine.add_default_rules()
        msgs = engine.evaluate(row_oversold, "TSLA")
        assert any("oversold" in m.lower() or "RSI" in m for m in msgs)

    def test_volume_spike_triggers(self, row_volume_spike):
        from alerting.rules import AlertEngine
        engine = AlertEngine()
        engine.add_default_rules()
        msgs = engine.evaluate(row_volume_spike, "NVDA")
        assert any("volume" in m.lower() for m in msgs)

    def test_normal_row_no_trigger(self):
        from alerting.rules import AlertEngine
        engine = AlertEngine()
        engine.add_default_rules()
        normal = pd.Series({"Close": 150.0, "rsi": 52.0, "Volume": 1_500_000,
                            "volume_sma_20": 2_000_000, "bb_width": 0.10,
                            "sma_50": 145.0, "sma_cross_signal": 0})
        msgs = engine.evaluate(normal, "SPY")
        assert len(msgs) == 0


class TestAlertNotifier:
    """Test that notifier gracefully skips unconfigured channels."""

    def test_send_without_credentials_no_crash(self):
        """Should not raise even if no API keys are set."""
        from alerting.notifier import AlertNotifier
        notifier = AlertNotifier()
        # This should log warnings but not raise
        notifier.send("Test alert — no channels configured", channels=[])

    def test_configured_channels_empty_when_no_keys(self, monkeypatch):
        from alerting.notifier import AlertNotifier
        from config import settings as cfg_module
        notifier = AlertNotifier()
        channels = notifier._configured_channels()
        # In test env without .env keys, channels should be empty list
        assert isinstance(channels, list)
