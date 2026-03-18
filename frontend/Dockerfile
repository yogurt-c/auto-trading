# ── Stage 1: Build ──────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first (cache layer)
COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

# ── Stage 2: Serve ───────────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runner

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

COPY --from=builder /app/dist /usr/share/nginx/html

# SPA routing: redirect all 404s back to index.html
# nginx 공식 이미지가 시작 시 envsubst로 $PORT를 치환 후 conf.d/default.conf로 복사
COPY nginx.conf /etc/nginx/templates/default.conf.template

ENV PORT=80
ENV BACKEND_HOST=localhost:8000

EXPOSE $PORT

CMD ["nginx", "-g", "daemon off;"]
