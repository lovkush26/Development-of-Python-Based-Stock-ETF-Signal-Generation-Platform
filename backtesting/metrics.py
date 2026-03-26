"""
backtesting/metrics.py — Performance analytics and reporting.

Computes advanced metrics and generates HTML/CSV reports.
"""

import numpy as np
import pandas as pd
from typing import List, Dict
from backtesting.engine import BacktestResult, Trade
from utils.logger import log


class PerformanceMetrics:
    """Compute and report comprehensive strategy performance metrics."""

    @staticmethod
    def full_report(result: BacktestResult) -> Dict:
        """Generate a full performance report dict from a BacktestResult."""
        base = result.summary()

        trades = result.trades
        if not trades:
            return base

        pnls = [t.pnl for t in trades]
        pnl_pcts = [t.pnl_pct for t in trades]
        wins = [t for t in trades if t.is_win]
        losses = [t for t in trades if not t.is_win]

        avg_win = np.mean([t.pnl for t in wins]) if wins else 0
        avg_loss = np.mean([t.pnl for t in losses]) if losses else 0
        profit_factor = (
            abs(sum(t.pnl for t in wins) / sum(t.pnl for t in losses))
            if losses and sum(t.pnl for t in losses) != 0
            else float("inf")
        )

        base.update({
            "total_pnl": round(sum(pnls), 2),
            "avg_win_usd": round(avg_win, 2),
            "avg_loss_usd": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 3),
            "best_trade_pct": round(max(pnl_pcts), 2),
            "worst_trade_pct": round(min(pnl_pcts), 2),
            "consecutive_wins": PerformanceMetrics._max_consecutive(trades, win=True),
            "consecutive_losses": PerformanceMetrics._max_consecutive(trades, win=False),
        })
        return base

    @staticmethod
    def monthly_returns(equity_curve: pd.Series) -> pd.DataFrame:
        """Compute month-by-month returns from an equity curve."""
        monthly = equity_curve.resample("ME").last()
        returns = monthly.pct_change().dropna() * 100
        df = pd.DataFrame({
            "month": returns.index.strftime("%b %Y"),
            "return_pct": returns.values.round(2),
        })
        return df

    @staticmethod
    def compare_strategies(results: Dict[str, BacktestResult]) -> pd.DataFrame:
        """Side-by-side comparison table for multiple strategy results."""
        rows = []
        for name, result in results.items():
            row = result.summary()
            row["strategy"] = name
            rows.append(row)
        return pd.DataFrame(rows).set_index("strategy")

    @staticmethod
    def _max_consecutive(trades: List[Trade], win: bool) -> int:
        max_streak = current = 0
        for t in trades:
            if t.is_win == win:
                current += 1
                max_streak = max(max_streak, current)
            else:
                current = 0
        return max_streak

    @staticmethod
    def to_csv(result: BacktestResult, path: str):
        """Export trades to CSV."""
        if not result.trades:
            log.warning("No trades to export.")
            return
        df = pd.DataFrame([t.__dict__ for t in result.trades])
        df.to_csv(path, index=False)
        log.info(f"Exported {len(result.trades)} trades to {path}")

    @staticmethod
    def equity_to_csv(result: BacktestResult, path: str):
        """Export equity curve to CSV."""
        if result.equity_curve is not None:
            result.equity_curve.to_csv(path)
            log.info(f"Exported equity curve to {path}")
