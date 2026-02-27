FROM python:3.11-slim

# ✅ ffmpeg for MP3 decoding
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render sets PORT, fallback 10000
CMD sh -c "uvicorn app:app --host 0.0.0.0 --port ${PORT:-10000}"