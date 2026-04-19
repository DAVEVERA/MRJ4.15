# MRJ4.15 — Cloud Run image
# Python 3.12 slim + torch CPU + Flask via gunicorn

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080

WORKDIR /app

# System libs needed by Pillow + torch + cv2
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps (torch CPU-only via PyTorch index)
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --extra-index-url https://download.pytorch.org/whl/cpu \
        torch torchvision \
 && pip install -r requirements.txt gunicorn

# Copy app source (model file is excluded via .dockerignore)
COPY . .

EXPOSE 8080

# Single worker, multiple threads (Gemini calls are I/O-bound, ~30-60s)
CMD exec gunicorn --bind :$PORT \
        --workers 1 --threads 4 \
        --timeout 120 \
        --access-logfile - --error-logfile - \
        app:app
