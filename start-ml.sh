#!/bin/sh
# Startup script for ML service

# Use PORT environment variable if set (Render/Heroku/etc), otherwise default to 8001
PORT=${PORT:-8001}

echo "Starting ML service on port $PORT..."

exec uvicorn ml_service.ml_service:app --host 0.0.0.0 --port $PORT
