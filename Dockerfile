# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure data directory exists for volume mounting
RUN mkdir -p /app/data

# V2 Bot entry point - for production deployment (including Zeabur)
CMD ["python", "-m", "src.bot_v2"]
