#!/usr/bin/env python3
"""
main.py — AlphaSignal application entry point.

Usage:
    python main.py api          # Start FastAPI server
    python main.py dashboard    # Start Streamlit dashboard
    python main.py worker       # Start Celery worker
    python main.py train        # Train models and exit
    python main.py signals      # Run signals once and exit
"""
import sys
import os


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd == "api":
        import uvicorn
        uvicorn.run(
            "dashboard.api:app",
            host=os.getenv("FASTAPI_HOST", "0.0.0.0"),
            port=int(os.getenv("FASTAPI_PORT", 8000)),
            reload=os.getenv("APP_ENV", "development") == "development",
        )

    elif cmd == "dashboard":
        import subprocess
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            "dashboard/app.py",
            "--server.port", os.getenv("STREAMLIT_PORT", "8501"),
            "--server.address", "0.0.0.0",
            "--server.headless", "true",
        ])

    elif cmd == "worker":
        from alerting.celery_worker import celery_app
        celery_app.worker_main(["worker", "--loglevel=info", "--concurrency=2"])

    elif cmd == "train":
        from scripts.train import main as train_main
        sys.argv = sys.argv[1:]  # strip "train" from args
        train_main()

    elif cmd == "signals":
        from scripts.run_signals import main as signals_main
        sys.argv = sys.argv[1:]
        signals_main()

    elif cmd == "backtest":
        from scripts.backtest import main as bt_main
        sys.argv = sys.argv[1:]
        bt_main()

    elif cmd == "seed-db":
        from utils.database import init_db
        init_db()
        print("Database initialized.")

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
