FROM python:3.11-slim

# backend/ 디렉토리가 WORKDIR이 됨 (main.py, infrastructure/ 등이 여기에 위치)
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 복사 (venv 제외)
COPY . .

# DB 볼륨 마운트 포인트
RUN mkdir -p /app/data

ENV DB_PATH=/app/data/portfolio.db
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV ROOT_PATH=/

EXPOSE $PORT

# sh -c를 JSON 배열로 명시 — 환경변수 치환 + 시그널 처리 모두 지원
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port $PORT --root-path $ROOT_PATH"]
