"""
alerting/celery_worker.py — Celery async task queue for scheduled jobs.

Tasks:
  - run_signals_task     : Generate signals for all tickers
  - retrain_models_task  : Retrain ML models on fresh data
  - send_alert_task      : Deliver an alert to all channels

Start worker:
    celery -A alerting.celery_worker worker --loglevel=info

Start beat scheduler:
    celery -A alerting.celery_worker beat --loglevel=info
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from celery import Celery
from celery.schedules import crontab
from config.settings import get_settings
from utils.logger import log

settings = get_settings()

# ── App setup ────────────────────────────────────────────────────────────────
celery_app = Celery(
    "alphasignal",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["alerting.celery_worker"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/New_York",
    enable_utc=True,
    task_track_started=True,
)

# ── Periodic schedule ─────────────────────────────────────────────────────────
celery_app.conf.beat_schedule = {
    # Run signals every 15 minutes during market hours (Mon–Fri 9:30–16:00 ET)
    "run-signals-15min": {
        "task": "alerting.celery_worker.run_signals_task",
        "schedule": crontab(minute="*/15", hour="9-16", day_of_week="1-5"),
    },
    # Retrain models nightly at 2 AM
    "retrain-nightly": {
        "task": "alerting.celery_worker.retrain_models_task",
        "schedule": crontab(hour=2, minute=0),
    },
}


# ── Tasks ────────────────────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_signals_task(self, tickers: list = None):
    """Generate ML signals and send alerts for any high-confidence signals."""
    try:
        from ml_engine.signal_runner import SignalRunner
        from alerting.notifier import AlertNotifier

        runner = SignalRunner(tickers=tickers)
        runner.load_models()
        signals = runner.run()

        notifier = AlertNotifier()
        alerted = 0
        for signal in signals:
            if signal.confidence >= settings.signal_confidence_threshold:
                notifier.send_signal_alert(
                    ticker=signal.ticker,
                    signal=signal.signal,
                    confidence=signal.confidence,
                    price=signal.price,
                )
                alerted += 1

        log.info(f"Signal task: {len(signals)} signals, {alerted} alerts sent.")
        return {"signals": len(signals), "alerts_sent": alerted}

    except Exception as exc:
        log.error(f"run_signals_task failed: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def retrain_models_task(self, train_ticker: str = "SPY"):
    """Retrain all ML models on fresh data."""
    try:
        from ml_engine.signal_runner import SignalRunner
        from alerting.notifier import AlertNotifier

        runner = SignalRunner()
        metrics = runner.train(train_ticker=train_ticker)

        notifier = AlertNotifier()
        notifier.send(
            f"✅ AlphaSignal models retrained on {train_ticker}.\n"
            f"RF CV accuracy: {metrics.get('rf', {}).get('cv_accuracy_mean', 0):.3f}\n"
            f"XGB CV accuracy: {metrics.get('xgb', {}).get('cv_accuracy_mean', 0):.3f}",
            subject="AlphaSignal: Model Retrain Complete",
        )
        return metrics

    except Exception as exc:
        log.error(f"retrain_models_task failed: {exc}")
        raise self.retry(exc=exc)


@celery_app.task
def send_alert_task(message: str, subject: str = "AlphaSignal Alert", channels: list = None):
    """Deliver an alert message (can be queued from any module)."""
    from alerting.notifier import AlertNotifier
    notifier = AlertNotifier()
    notifier.send(message, subject=subject, channels=channels)
    return {"sent": True}
