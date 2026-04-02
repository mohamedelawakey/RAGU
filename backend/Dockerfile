FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies with cache mount
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    libgl1 \
    libglib2.0-0 \
    libxcb1 \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies with cache mount
COPY requirements.txt .
COPY backend/requirements.txt backend/
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --default-timeout=2000 -r requirements.txt -r backend/requirements.txt && \
    pip uninstall -y opencv-python && \
    pip install --default-timeout=2000 opencv-python-headless

# Copy project
COPY . .
