# ========================================================
# StudySphere AI - Multi-Stage Production Dockerfile
# Optimized for Cloud Deployment (AWS, GCP, Azure, DigitalOcean)
# ========================================================

# Stage 1: Build & Dependencies
FROM python:3.11-slim as builder

WORKDIR /install

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --user -r requirements.txt
RUN pip install --no-cache-dir --user gunicorn

# Stage 2: Runtime Image
FROM python:3.11-slim as runner

LABEL maintainer="StudySphere AI Team"
LABEL description="Docker-Enabled AI Chatbot for Study Material Q&A on Cloud"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/home/appuser/.local/bin:$PATH \
    IS_DOCKER=true \
    PORT=8000

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -m -s /bin/bash appuser

WORKDIR /app

COPY --from=builder /root/.local /home/appuser/.local

RUN mkdir -p /app/data/uploads /app/data/chroma_db && \
    chown -R appuser:appgroup /app /home/appuser

COPY --chown=appuser:appgroup app /app/app
COPY --chown=appuser:appgroup sample_materials /app/sample_materials
COPY --chown=appuser:appgroup run.py /app/run.py
COPY --chown=appuser:appgroup .env.example /app/.env.example

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
