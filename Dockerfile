# ============================================================
# SurfaceTrace-IN — Dockerfile
# Python 3.11 slim runtime for pipeline and dashboard
# ============================================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app/src:/app"

WORKDIR /app

# Install minimal build dependencies for lxml and sqlite
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libxml2-dev \
        libxslt1-dev \
        sqlite3 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure data directory exists
RUN mkdir -p data

EXPOSE 8501

ENTRYPOINT ["python", "-m", "st"]
CMD ["run-all"]
