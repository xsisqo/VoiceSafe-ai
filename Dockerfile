# AI/Dockerfile
FROM python:3.11-slim

# System deps (librosa/scipy + audio utils)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Workdir inside container
WORKDIR /app

# Install Python deps first (better Docker cache)
COPY AI/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the AI app code
COPY AI/ /app/

# Render sets PORT env var; we must bind to it
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]