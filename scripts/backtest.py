#!/usr/bin/env python3
"""
scripts/backtest.py — Run backtests and print performance reports.

Usage:
    python scripts/backtest.py
    python scripts/backtest.py --ticker AAPL --period 3y
    python scripts/backtest.py --ticker SPY --output report.csv
"""

import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import log
from data_ingestion.fetcher import MarketDataFetcher
from data_ingestion.features import FeatureEngineer
from backtesting.engine import BacktestEngine
from backtesting.metrics import PerformanceMetrics


def parse_args():
    parser = argparse.ArgumentParser(description="Run AlphaSignal backtests")
    parser.add_argument("--ticker", default="SPY", help="Ticker to backtest (default: SPY)")
    parser.add_argument("--period", default="2y", help="Historical period (default: 2y)")
    parser.add_argument("--capital", type=float, default=100_000, help="Initial capital (default: 100000)")
    parser.add_argument("--output", default=None, help="Save trade log to CSV")
    return parser.parse_args()


def main():
    args = parse_args()

    log.info(f"Running backtest: {args.ticker} | {args.period} | ${args.capital:,.0f}")

    fetcher = MarketDataFetcher()
    fe = FeatureEngineer()
    engine = BacktestEngine(initial_capital=args.capital)

    df = fetcher.get_ohlcv(args.ticker, period=args.period)
    if df.empty:
        log.error(f"No data for {args.ticker}. Exiting.")
        sys.exit(1)

    df = fe.add_all_features(df)
    df = fe.add_target_labels(df)
    df.dropna(inplace=True)
    df["signal"] = df["target"]

    result = engine.run(df, ticker=args.ticker)
    report = PerformanceMetrics.full_report(result)
    monthly = PerformanceMetrics.monthly_returns(result.equity_curve)

    log.info("=" * 50)
    log.info(f"BACKTEST RESULTS — {args.ticker}")
    log.info("=" * 50)
    for k, v in report.items():
        if k != "ticker":
            log.info(f"  {k:<28} {v}")
    log.info("")
    log.info("Monthly Returns:")
    for _, row in monthly.iterrows():
        bar = "█" * int(abs(row["return_pct"]) / 0.5)
        sign = "+" if row["return_pct"] >= 0 else ""
        log.info(f"  {row['month']:<10} {sign}{row['return_pct']:>6.2f}%  {bar}")
    log.info("=" * 50)

    if args.output:
        PerformanceMetrics.to_csv(result, args.output)


if __name__ == "__main__":
    main()
