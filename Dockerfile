FROM python:3.12-slim

# Install system dependencies (ADB client, Docker CLI, curl, sudo)
RUN apt-get update && apt-get install -y --no-install-recommends \
    android-tools-adb \
    curl \
    docker.io \
    sudo \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create logs, screenshots, and data directories
RUN mkdir -p logs screenshots data

CMD ["python", "main.py"]
