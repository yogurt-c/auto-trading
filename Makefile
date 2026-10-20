.PHONY: android-test backend frontend dev install test test-unit test-integration lint fmt \
	research-install research-test research-lint research-fmt

backend:
	cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

dev:
	@trap 'kill 0' SIGINT SIGTERM; make -j2 backend frontend

install:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

test:
	cd backend && source venv/bin/activate && pytest

test-unit:
	cd backend && source venv/bin/activate && pytest tests/unit/

test-integration:
	cd backend && source venv/bin/activate && pytest tests/integration/

lint:
	cd backend && source venv/bin/activate && ruff check app/ tests/

fmt:
	cd backend && source venv/bin/activate && ruff format app/ tests/

research-install:
	cd research && python3.11 -m venv .venv && .venv/bin/pip install -e ../backend -e ".[dev]"

research-test:
	cd research && .venv/bin/pytest

research-lint:
	cd research && .venv/bin/ruff check src/ tests/ scripts/

research-fmt:
	cd research && .venv/bin/ruff format src/ tests/ scripts/

android-test:
	cd android && ./gradlew test
