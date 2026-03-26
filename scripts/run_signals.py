#!/usr/bin/env python3
"""
scripts/run_signals.py — Generate signals for all configured tickers.

Usage:
    python scripts/run_signals.py
    python scripts/run_signals.py --tickers AAPL NVDA SPY --alert
    python scripts/run_signals.py --output signals.csv
"""

import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import log
from ml_engine.signal_runner import SignalRunner


def parse_args():
    parser = argparse.ArgumentParser(description="Run AlphaSignal signal generation")
    parser.add_argument("--tickers", nargs="+", default=None, help="Ticker list")
    parser.add_argument("--alert", action="store_true", help="Send alerts for high-confidence signals")
    parser.add_argument("--output", default=None, help="Save signals to CSV file")
    parser.add_argument("--threshold", type=float, default=0.65, help="Confidence threshold (default: 0.65)")
    return parser.parse_args()


def main():
    args = parse_args()

    runner = SignalRunner(tickers=args.tickers)
    runner.load_models()
    signals = runner.run()

    if not signals:
        log.warning("No signals generated. Run scripts/train.py first.")
        return

    log.info("=" * 60)
    log.info(f"{'TICKER':<8} {'SIGNAL':<6} {'CONF':>6} {'PRICE':>10} {'MODEL'}")
    log.info("-" * 60)
    for s in signals:
        marker = " ◀" if s.confidence >= args.threshold else ""
        log.info(f"{s.ticker:<8} {s.signal:<6} {s.confidence*100:>5.1f}%  ${s.price:>9.2f}  {s.model_name}{marker}")
    log.info("=" * 60)

    if args.output:
        df = runner.signals_to_dataframe(signals)
        df.to_csv(args.output, index=False)
        log.info(f"Signals saved to {args.output}")

    if args.alert:
        from alerting.notifier import AlertNotifier
        notifier = AlertNotifier()
        high_conf = [s for s in signals if s.confidence >= args.threshold]
        for s in high_conf:
            notifier.send_signal_alert(s.ticker, s.signal, s.confidence, s.price)
        log.info(f"Sent {len(high_conf)} alerts.")


if __name__ == "__main__":
    main()
