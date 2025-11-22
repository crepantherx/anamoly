# Web Service Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt

# Copy application code
COPY app/ ./app/

# Expose port
EXPOSE 8000

# Run the web service
CMD uvicorn app.main:app --host 0.0.0.0 --port 8000
