.PHONY: help install dev down up run test test-unit test-integration lint fmt clean

VENV      := .venv/bin
PYTHON    := $(VENV)/python
PYTEST    := $(VENV)/python -m pytest
RUFF      := $(VENV)/ruff

export IMAGE_SERVICE_AWS_ENDPOINT_URL = http://localhost:4566
export IMAGE_SERVICE_S3_BUCKET        = image-service-local
export IMAGE_SERVICE_DYNAMODB_TABLE   = images
export IMAGE_SERVICE_AWS_REGION       = ap-south-1
export IMAGE_SERVICE_ENVIRONMENT      = development
export IMAGE_SERVICE_DEBUG            = true
export AWS_ACCESS_KEY_ID              = test
export AWS_SECRET_ACCESS_KEY          = test
export AWS_DEFAULT_REGION             = ap-south-1

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies (including dev)
	uv sync

# ---------------------------------------------------------------------------
# LocalStack
# ---------------------------------------------------------------------------

up: ## Start LocalStack in the background
	docker compose up -d
	@echo "Waiting for LocalStack to be ready..."
	@until curl -sf http://localhost:4566/_localstack/health > /dev/null 2>&1; do sleep 1; done
	@echo "LocalStack is ready."

down: ## Stop LocalStack
	docker compose down

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

dev: up ## Start LocalStack + Flask dev server
	$(PYTHON) main.py

run: ## Start Flask dev server (assumes LocalStack is already running)
	$(PYTHON) main.py

# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

test: ## Run all tests (unit + integration, requires LocalStack)
	$(PYTEST) tests/

test-unit: ## Run unit tests only (no LocalStack needed)
	$(PYTEST) tests/unit/

test-integration: up ## Run integration tests (starts LocalStack if needed)
	$(PYTEST) tests/integration/

# ---------------------------------------------------------------------------
# Code quality
# ---------------------------------------------------------------------------

lint: ## Run ruff linter
	$(RUFF) check .

fmt: ## Format code with ruff
	$(RUFF) format .
	$(RUFF) check --fix .

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

clean: down ## Stop LocalStack and remove caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache
