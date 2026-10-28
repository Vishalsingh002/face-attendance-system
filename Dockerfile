# Official lightweight Python 3.10 image
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# CRUCIAL: Limits C++ compilation to 1 thread to prevent exceeding Render's 8GB RAM build limit
ENV CMAKE_BUILD_PARALLEL_LEVEL=1

WORKDIR /app

# Install system dependencies required for OpenCV and compiling dlib
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and pin setuptools < 70 (required for dlib build)
RUN pip install --no-cache-dir --upgrade pip "setuptools<70" wheel

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose default port
EXPOSE 5000

# Start Gunicorn server using dynamic $PORT passed by Render
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT:-5000} --workers 1 --threads 4 --timeout 120"]
