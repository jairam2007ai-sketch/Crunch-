# One container: builds the three websites, then runs the API that serves them.

# 1) build the buyer, seller and admin sites
FROM node:22-alpine AS web
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# 2) the FastAPI server
FROM python:3.12-slim
# The API serves the websites itself, so no cross-site (CORS) access is needed unless you add some.
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 ENV=production CORS_ORIGINS=""
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY --from=web /app/frontend/dist /app/frontend/dist
# run as an ordinary user, never root
RUN useradd --create-home --uid 10001 crunch && chown -R crunch /app
USER crunch
EXPOSE 8000
# Trust X-Forwarded-For only from the host's private network (its load balancer), so visitors
# can't fake their address to dodge rate limits. No version banner, no per-request access log.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,127.0.0.1' --no-server-header --no-access-log"]
