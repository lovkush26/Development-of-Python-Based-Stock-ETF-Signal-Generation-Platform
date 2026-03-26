#!/usr/bin/env python3
"""
scripts/train.py — CLI script to train all ML models.

Usage:
    python scripts/train.py
    python scripts/train.py --ticker SPY --period 3y
    python scripts/train.py --ticker SPY --period 3y --no-lstm
"""

import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import log
from ml_engine.signal_runner import SignalRunner


def parse_args():
    parser = argparse.ArgumentParser(description="Train AlphaSignal ML models")
    parser.add_argument("--ticker", default="SPY", help="Ticker to train on (default: SPY)")
    parser.add_argument("--period", default="2y", help="Historical data period (default: 2y)")
    parser.add_argument("--no-lstm", action="store_true", help="Skip LSTM training (faster)")
    return parser.parse_args()


def main():
    args = parse_args()
    log.info(f"Starting training on {args.ticker} [{args.period}]")

    runner = SignalRunner(use_lstm=not args.no_lstm)

    metrics = runner.train(train_ticker=args.ticker)

    log.info("=" * 50)
    log.info("TRAINING RESULTS")
    log.info("=" * 50)
    for model_name, m in metrics.items():
        if isinstance(m, dict):
            acc = m.get("cv_accuracy_mean", m.get("val_accuracy", 0))
            log.info(f"  {model_name.upper():12s} accuracy: {acc:.4f}")
    log.info("Models saved to ./models/saved/")
    log.info("=" * 50)


if __name__ == "__main__":
    main()
