# QERS FastAPI backend — run with Docker or deploy to Railway
FROM python:3.10-slim

WORKDIR /app

# System deps for pybullet/numpy (optional; minimal for API-only)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglx-mesa0 \
    libglu1-mesa \
    libx11-6 \
    libxext6 \
    libxi6 \
    libxrender1 \
    libsm6 \
    libice6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Repo root context expected when building from repo root: docker build -f apps/api/Dockerfile .
COPY apps/sim/requirements.txt requirements-sim.txt
RUN pip install --no-cache-dir -r requirements-sim.txt

COPY apps/api/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir pybullet>=3.2 robodk

COPY . .
# Ensure apps and qers are importable
ENV PYTHONPATH=/app

# Default port; Railway sets PORT
ENV PORT=8000
EXPOSE 8000

# Run uvicorn (use PORT so Railway works)
CMD uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT}
