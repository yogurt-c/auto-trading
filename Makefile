.PHONY: backend frontend dev install

backend:
	cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

dev:
	@trap 'kill 0' SIGINT SIGTERM; make -j2 backend frontend

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install
