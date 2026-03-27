FROM python:3.11-slim

# backend/ 디렉토리가 WORKDIR이 됨 (main.py, infrastructure/ 등이 여기에 위치)
WORKDIR /app

COPY pyproject.toml .
# 의존성 레이어 캐시를 위해 stub 패키지 생성 후 설치
RUN mkdir -p app && touch app/__init__.py && pip install --no-cache-dir .

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
