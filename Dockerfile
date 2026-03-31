
# Python 3.11 Slim Image (Lightweight)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (ffmpeg for media, build-essential for compiling python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create volume for persistent data if strictly needed (though Supabase is external)
# VOLUME /app/data

# Environment variables (Defaults, can be overridden)
ENV PYTHONUNBUFFERED=1

# Command to run the bot
CMD ["python3", "main.py"]
