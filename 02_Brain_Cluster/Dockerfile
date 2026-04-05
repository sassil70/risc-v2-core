# Base Image: Lightweight Python (multi-arch for local dev + Cloud Run)
FROM python:3.11-slim

# Set Working Directory
WORKDIR /app

# Install System Dependencies (PostgreSQL, Crypto, Playwright/Chromium)
RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 libatspi2.0-0 libxfixes3 \
    && rm -rf /var/lib/apt/lists/*

# Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser
RUN playwright install chromium

# Copy Application Code
COPY . .

# Health check for Cloud Run
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# Expose API Port
EXPOSE 8000

# Run Application (Cloud Run sets PORT env var)
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
