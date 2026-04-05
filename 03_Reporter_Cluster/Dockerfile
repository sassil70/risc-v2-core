# RISC V2.0 - Cluster 3: Reporter (AI Engine with Playwright PDF Core)
FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

# The Microsoft Playwright image already has Node, Chromium, and OS dependencies installed.
# We just need to install the Python wrappers and our FastApi app.

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Source Code
COPY . .

# Expose Port
EXPOSE 8000

# Run FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
