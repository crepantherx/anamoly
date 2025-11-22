# Use Dockerfile for faster, more reliable deployments
FROM python:3.10-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements-ml.txt .
RUN pip install --no-cache-dir -r requirements-ml.txt

# Copy the ML service and app module
COPY ml_service/ ./ml_service/
COPY app/ml_engine.py ./app/

# Create __init__.py if it doesn't exist
RUN mkdir -p app && touch app/__init__.py

# Expose port
EXPOSE $PORT

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:${PORT:-8001}/health')"

# Run the service
CMD uvicorn ml_service.ml_service:app --host 0.0.0.0 --port ${PORT:-8001}
