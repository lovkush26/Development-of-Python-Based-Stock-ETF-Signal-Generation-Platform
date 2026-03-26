"""
backtesting/engine.py — Strategy backtesting on historical data.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Optional

from utils.logger import log


@dataclass
class Trade:
    ticker: str
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    signal: str
    quantity: int
    pnl: float
    pnl_pct: float
    is_win: bool


@dataclass
class BacktestResult:
    ticker: str
    trades: List[Trade] = field(default_factory=list)
    equity_curve: pd.Series = None
    initial_capital: float = 100_000.0
    final_capital: float = 0.0

    @property
    def total_return_pct(self) -> float:
        if self.initial_capital == 0:
            return 0.0
        return (self.final_capital - self.initial_capital) / self.initial_capital * 100

    @property
    def win_rate(self) -> float:
        if not self.trades:
            return 0.0
        return sum(1 for t in self.trades if t.is_win) / len(self.trades) * 100

    @property
    def max_drawdown(self) -> float:
        if self.equity_curve is None or self.equity_curve.empty:
            return 0.0
        roll_max = self.equity_curve.cummax()
        drawdown = (self.equity_curve - roll_max) / roll_max
        return float(drawdown.min() * 100)

    @property
    def sharpe_ratio(self) -> float:
        if self.equity_curve is None or len(self.equity_curve) < 2:
            return 0.0
        daily_returns = self.equity_curve.pct_change().dropna()
        if daily_returns.std() == 0:
            return 0.0
        return float(daily_returns.mean() / daily_returns.std() * np.sqrt(252))

    @property
    def sortino_ratio(self) -> float:
        if self.equity_curve is None or len(self.equity_curve) < 2:
            return 0.0
        daily_returns = self.equity_curve.pct_change().dropna()
        downside = daily_returns[daily_returns < 0]
        if len(downside) == 0 or downside.std() == 0:
            return 0.0
        return float(daily_returns.mean() / downside.std() * np.sqrt(252))

    def summary(self) -> dict:
        return {
            "ticker": self.ticker,
            "initial_capital": round(self.initial_capital, 2),
            "final_capital": round(self.final_capital, 2),
            "total_return_pct": round(self.total_return_pct, 2),
            "n_trades": len(self.trades),
            "win_rate_pct": round(self.win_rate, 2),
            "max_drawdown_pct": round(self.max_drawdown, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 3),
            "sortino_ratio": round(self.sortino_ratio, 3),
            "avg_trade_pnl_pct": round(
                np.mean([t.pnl_pct for t in self.trades]) if self.trades else 0, 2
            ),
        }


class BacktestEngine:
    def __init__(
        self,
        initial_capital: float = 100_000.0,
        position_size: float = 0.10,
        commission: float = 0.001,
        slippage: float = 0.0005,
    ):
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.commission = commission
        self.slippage = slippage

    def run(self, df, ticker="STOCK", signal_col="signal"):
        if signal_col not in df.columns:
            log.error(f"Column '{signal_col}' not found")
            return BacktestResult(ticker=ticker, initial_capital=self.initial_capital)

        capital = self.initial_capital
        equity_values = []
        trades = []
        position = 0
        entry_price = 0.0
        entry_cost = 0.0
        entry_date = None

        for idx, row in df.iterrows():
            price = float(row["Close"])
            signal = int(row.get(signal_col, 0))

            if position > 0 and signal in (-1, 1):
                exit_price = price * (1 - self.slippage)
                proceeds = position * exit_price * (1 - self.commission)
                pnl = proceeds - entry_cost
                capital += proceeds
                trades.append(Trade(
                    ticker=ticker, entry_date=str(entry_date), exit_date=str(idx),
                    entry_price=round(entry_price, 4), exit_price=round(exit_price, 4),
                    signal="BUY", quantity=position, pnl=round(pnl, 2),
                    pnl_pct=round(pnl / entry_cost * 100, 2) if entry_cost > 0 else 0.0,
                    is_win=pnl > 0,
                ))
                position = 0
                entry_cost = 0.0

            if signal == 1 and position == 0 and capital > 0:
                trade_value = capital * self.position_size
                ep = price * (1 + self.slippage)
                shares = int(trade_value / ep)
                if shares > 0:
                    cost = shares * ep * (1 + self.commission)
                    if cost <= capital:
                        capital -= cost
                        position = shares
                        entry_price = ep
                        entry_cost = cost
                        entry_date = idx

            equity_values.append(capital + position * price)

        if position > 0 and equity_values:
            last_price = float(df["Close"].iloc[-1])
            proceeds = position * last_price * (1 - self.commission)
            capital += proceeds
            equity_values[-1] = capital

        result = BacktestResult(
            ticker=ticker,
            trades=trades,
            equity_curve=pd.Series(equity_values, index=df.index),
            initial_capital=self.initial_capital,
            final_capital=equity_values[-1] if equity_values else self.initial_capital,
        )
        log.info(f"Backtest {ticker}: return={result.total_return_pct:.1f}% trades={len(trades)}")
        return result

    def run_multiple(self, datasets):
        return {ticker: self.run(df, ticker=ticker) for ticker, df in datasets.items()}