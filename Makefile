# Multi-Tenant Workflow Platform - developer shortcuts.
# Docker path: `make up` / `make down`. Local (no Docker) path: `make dev-db` + `make backend-dev`.

.PHONY: help up down build logs migrate seed test test-cov dev-db backend-dev frontend-dev

help:
	@echo "Targets:"
	@echo "  up            docker compose up --build (db + backend + frontend)"
	@echo "  down          docker compose down -v"
	@echo "  logs          docker compose logs -f"
	@echo "  migrate       alembic upgrade head (inside backend)"
	@echo "  seed          python -m app.seed (inside backend)"
	@echo "  test          pytest -q (inside backend)"
	@echo "  dev-db        start embedded PostgreSQL (no Docker/sudo) via pgserver"
	@echo "  backend-dev   run uvicorn against local SQLite"
	@echo "  frontend-dev  npm run dev"

up:
	docker compose up --build

down:
	docker compose down -v

build:
	docker compose build

logs:
	docker compose logs -f

migrate:
	cd backend && alembic upgrade head

seed:
	cd backend && python -m app.seed

test:
	cd backend && pytest -q

test-cov:
	cd backend && pytest --cov=app --cov-report=term-missing

dev-db:
	python scripts/dev_db.py

backend-dev:
	cd backend && uvicorn app.main:app --reload

frontend-dev:
	cd frontend && npm run dev
