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

# Copy startup script
COPY start-ml.sh ./
RUN chmod +x start-ml.sh

# Expose port
EXPOSE 8001

# Run the service
CMD ["./start-ml.sh"]
