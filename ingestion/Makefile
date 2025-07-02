.PHONY: install test lint format clean run

install:
	pip install -e .[dev]

test:
	pytest

lint:
	flake8 ingestion/ tests/
	mypy ingestion/

format:
	black ingestion/ tests/
	isort ingestion/ tests/

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run:
	python -m ingestion.main

dev-setup:
	pip install -e .[dev]
	pre-commit install 