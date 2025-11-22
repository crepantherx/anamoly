FROM python:3.10-slim

WORKDIR /app

# Copy ML service requirements and install
COPY requirements-ml.txt .
RUN pip install --no-cache-dir -r requirements-ml.txt

# Copy the ML service and app module
COPY ml_service/ ./ml_service/
COPY app/ml_engine.py ./app/

# Create __init__.py for app module
RUN mkdir -p app && touch app/__init__.py

# Expose port
EXPOSE 8001

# Run the ML service
CMD ["uvicorn", "ml_service.ml_service:app", "--host", "0.0.0.0", "--port", "8001"]
