# LABLAB API - backend for RoboDK integration
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application (repo root context)
COPY requirements.txt .
COPY apps/ apps/

# Expose port (Railway sets PORT; default for local)
ENV PORT=8000
EXPOSE 8000

WORKDIR /app
ENV PYTHONPATH=/app
# Shell form so PORT is expanded at runtime (Railway sets PORT)
CMD sh -c "uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"
