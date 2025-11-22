#!/bin/bash

echo "🧪 Testing Microservice Architecture..."
echo ""

# Test ML Service
echo "1️⃣  Testing ML Service..."
echo "Starting ML service in background..."

# Start ML service in background
python3 ml_service/ml_service.py > /tmp/ml_service.log 2>&1 &
ML_PID=$!

echo "ML Service PID: $ML_PID"
echo "Waiting for ML service to start..."
sleep 5

# Test health endpoint
echo "Testing /health endpoint..."
HEALTH_RESPONSE=$(curl -s http://localhost:8001/health)
echo "Response: $HEALTH_RESPONSE"

if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo "✅ ML Service health check passed"
else
    echo "❌ ML Service health check failed"
    kill $ML_PID
    exit 1
fi

# Test prediction endpoint
echo ""
echo "Testing /api/ml/predict endpoint..."
PREDICT_RESPONSE=$(curl -s -X POST http://localhost:8001/api/ml/predict \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 1000,
    "user_avg": 100,
    "location": "NY",
    "timestamp": "2024-01-01T12:00:00"
  }')

echo "Response: $PREDICT_RESPONSE"

if echo "$PREDICT_RESPONSE" | grep -q "model_results"; then
    echo "✅ ML prediction endpoint working"
else
    echo "❌ ML prediction endpoint failed"
    kill $ML_PID
    exit 1
fi

echo ""
echo "✅ All ML Service tests passed!"
echo ""
echo "🌐 ML Service is running on http://localhost:8001"
echo "   Health: http://localhost:8001/health"
echo "   API Docs: http://localhost:8001/docs"
echo ""
echo "To test web service:"
echo "  export ML_SERVICE_URL=http://localhost:8001"
echo "  uvicorn app.main:app --port 8000"
echo ""
echo "Press Ctrl+C to stop ML service..."
echo "ML Service PID: $ML_PID"

# Wait for user to stop
wait $ML_PID
