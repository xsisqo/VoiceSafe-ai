# ---------- BASE ----------
FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Workdir
WORKDIR /app

# Copy requirements
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy ALL project files (current folder)
COPY . .

# Render provides PORT env
ENV PORT=10000

# Start API
CMD uvicorn app:app --host 0.0.0.0 --port 10000