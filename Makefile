PYTHON ?= python

.PHONY: install up down db-init sync-connectors validate-mte-p0 frontend-install frontend-test frontend-build test lint run-api

install:
	$(PYTHON) -m pip install -e .[dev]

up:
	docker compose up -d

down:
	docker compose down

db-init:
	$(PYTHON) scripts/init_db.py

sync-connectors:
	$(PYTHON) scripts/sync_connector_registry.py

validate-mte-p0:
	$(PYTHON) scripts/validate_mte_p0.py --reference-period 2025 --runs 3 --bootstrap-municipality --output-json

frontend-install:
	cd frontend && npm install

frontend-test:
	cd frontend && npm test

frontend-build:
	cd frontend && npm run build

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .

run-api:
	$(PYTHON) -m uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
