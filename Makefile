.PHONY: help setup dev backend ui worker demo benchmark test lint build clean

help:
	@echo "QERS Makefile"
	@echo "  make setup      - Install dependencies"
	@echo "  make dev        - Start backend + UI (run in two terminals: make backend, make ui)"
	@echo "  make backend    - Start FastAPI backend (port 8000)"
	@echo "  make ui         - Start Next.js UI (port 3000)"
	@echo "  make worker     - Start Celery worker (requires Redis; set REDIS_URL)"
	@echo "  make demo       - Run MVP demo (backend + UI + example sim)"
	@echo "  make benchmark  - Run benchmark suite"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linters"
	@echo "  make build      - Docker compose build (backend + web + worker)"
	@echo "  make clean      - Clean build artifacts"

setup:
	pip install -r requirements.txt
	cd apps/web && (command -v pnpm >/dev/null 2>&1 && pnpm install || npm install)

dev:
	@echo "Run in two terminals:"
	@echo "  Terminal 1: make backend"
	@echo "  Terminal 2: make ui"
	@echo "Optional (queued sim jobs): start Redis (e.g. docker run -p 6379:6379 redis:7-alpine) then: make worker"

backend:
	PYTHONPATH=. uvicorn apps.api.main:app --reload --port 8000 --host 0.0.0.0

ui:
	cd apps/web && (command -v pnpm >/dev/null 2>&1 && pnpm dev || npm run dev)

worker:
	PYTHONPATH=. celery -A apps.jobs.celery_app worker --loglevel=info

demo:
	@echo "Starting QERS demo..."
	@echo "1. Backend will start on http://127.0.0.1:8000"
	@echo "2. UI will start on http://localhost:3000"
	@echo "3. Example robot will load automatically"
	@PYTHONPATH=. python -m qers.demo

benchmark:
	PYTHONPATH=. python -m qers.benchmarks.run_all

test:
	pytest apps/sim/tests/ apps/api/tests/ -v

lint:
	ruff check apps/ qers/
	mypy apps/ qers/

build:
	docker compose build

clean:
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf apps/web/.next
	rm -rf .pytest_cache
