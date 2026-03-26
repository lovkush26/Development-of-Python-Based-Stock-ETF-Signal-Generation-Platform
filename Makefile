.PHONY: install dev test lint format train signals backtest api dashboard docker-up docker-down help

help:
	@echo "AlphaSignal — Available Commands"
	@echo "================================="
	@echo "  install      Install dependencies"
	@echo "  dev          Install dev dependencies"
	@echo "  test         Run test suite"
	@echo "  lint         Run ruff linter"
	@echo "  format       Auto-format with black"
	@echo "  train        Train ML models"
	@echo "  signals      Run signal generation"
	@echo "  backtest     Run backtest on SPY"
	@echo "  api          Start FastAPI server"
	@echo "  dashboard    Start Streamlit dashboard"
	@echo "  worker       Start Celery worker"
	@echo "  docker-up    Start all Docker services"
	@echo "  docker-down  Stop all Docker services"

install:
	pip install -r requirements.txt

dev: install
	pip install pytest pytest-asyncio pytest-cov httpx black ruff
	cp .env.example .env

test:
	pytest tests/ -v --tb=short

test-fast:
	pytest tests/ -v --tb=short -m "not slow and not integration"

lint:
	ruff check .

format:
	black .

train:
	python scripts/train.py

signals:
	python scripts/run_signals.py

backtest:
	python scripts/backtest.py

api:
	uvicorn dashboard.api:app --reload --port 8000

dashboard:
	streamlit run dashboard/app.py

worker:
	celery -A alerting.celery_worker worker --loglevel=info

beat:
	celery -A alerting.celery_worker beat --loglevel=info

seed-db:
	python scripts/seed_db.py

docker-up:
	cd docker && docker-compose up -d --build

docker-down:
	cd docker && docker-compose down

docker-logs:
	cd docker && docker-compose logs -f

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -name ".coverage" -delete
	rm -rf htmlcov/ .pytest_cache/
