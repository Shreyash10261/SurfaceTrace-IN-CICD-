# ============================================================
# SurfaceTrace-IN — Makefile
# Development, testing, and execution shortcuts
# ============================================================

.PHONY: test lint fmt run-all collect fetch extract score export evaluate dashboard up down clean

# Python environment settings
export PYTHONPATH := src:.

# Testing & Linting
test:
	python -m pytest tests/ -v

lint:
	ruff check src/ tests/ app.py

fmt:
	ruff check --fix src/ tests/ app.py

# Pipeline Stages
run-all:
	python -m st run-all

collect:
	python -m st collect

fetch:
	python -m st fetch

extract:
	python -m st extract

score:
	python -m st score

export:
	python -m st export

evaluate:
	python -m st evaluate

# Dashboard
dashboard:
	streamlit run app.py

# Docker Compose
up:
	docker compose up --build dashboard

pipeline:
	docker compose up --build pipeline

down:
	docker compose down

clean:
	rm -rf data/*.db* output/*.csv .pytest_cache .ruff_cache
	@echo "✓ Temporary databases, outputs, and caches removed."
