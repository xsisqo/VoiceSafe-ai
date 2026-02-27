# AI/Dockerfile
FROM python:3.11-slim

# ---- system deps (audio + build basics) ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# ---- app settings ----
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ---- install python deps first (better layer cache) ----
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ---- copy app ----
COPY . /app

# ---- Render uses $PORT ----
EXPOSE 8000

# If PORT isn't set, default to 8000
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]