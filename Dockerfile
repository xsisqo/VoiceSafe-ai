# -------- BASE --------
FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Workdir
WORKDIR /app

# Copy requirements first (cache optimization)
COPY requirements.txt .

# FIX pkg_resources error
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Render provides PORT automatically
ENV PORT=10000

# Start API
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port $PORT"]