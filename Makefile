.PHONY: backend frontend dev install test test-unit test-integration lint fmt

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
