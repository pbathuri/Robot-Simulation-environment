# LABLAB API - run and deploy
# Run from repo root

.PHONY: venv run docker-build docker-up docker-down test-endpoints

venv:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

run:
	PYTHONPATH=. uvicorn apps.api.main:app --host 0.0.0.0 --port $${PORT:-8000}

docker-build:
	docker compose build

docker-up:
	docker compose up --build

docker-up-d:
	docker compose up -d --build

docker-down:
	docker compose down

# Quick API checks. Default port 8000; use PORT=8001 when using docker-compose (8001:8000)
test-endpoints:
	@echo "Health:" && curl -s http://localhost:$${PORT:-8000}/health && echo ""
	@echo "RoboDK status:" && curl -s http://localhost:$${PORT:-8000}/api/robodk/status && echo ""
	@echo "Design objects:" && curl -s http://localhost:$${PORT:-8000}/api/robodk/design/objects && echo ""

# Full verification (create object, list). Use PORT=8001 for Docker.
verify:
	@bash scripts/verify-api.sh $${PORT:-8000}
