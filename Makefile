PYTHON ?= python

.PHONY: install up down db-init sync-connectors test lint run-api

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

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .

run-api:
	$(PYTHON) -m uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
