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
EXPOSE 8001

# Run the service - Railway will set PORT env var
CMD ["sh", "-c", "uvicorn ml_service.ml_service:app --host 0.0.0.0 --port ${PORT:-8001}"]
