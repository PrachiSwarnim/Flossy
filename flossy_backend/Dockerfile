FROM python:3.12-slim

WORKDIR /app
ENV PYTHONPATH=/app

# System dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App source
COPY . .

# Cloud Run configuration
ENV PORT=8080
EXPOSE 8080

# ✅ ULTRA-RESILLIENT CLOUD RUN ENTRYPOINT
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--log-level", "info"]
