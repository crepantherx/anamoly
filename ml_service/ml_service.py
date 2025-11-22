"""
ML Service - Standalone ML prediction service
Handles all machine learning operations with heavy dependencies
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Optional
import sys
import os

# Add parent directory to path to import ml_engine
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app.ml_engine import ml_engine

app = FastAPI(title="ML Prediction Service", version="1.0.0")

# Enable CORS for web service to call this
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Vercel domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PredictionRequest(BaseModel):
    amount: float
    user_avg: float
    location: str
    timestamp: str  # ISO format string

class PredictionResponse(BaseModel):
    model_results: Dict
    shap_explanation: str

class RetrainRequest(BaseModel):
    transactions: list

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ml-prediction",
        "models_fitted": ml_engine.is_fitted
    }

@app.post("/api/ml/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """
    Predict anomaly for a transaction
    """
    try:
        # Parse timestamp
        timestamp = datetime.fromisoformat(request.timestamp.replace('Z', '+00:00'))
        
        # Get predictions from all models
        model_results, shap_json = ml_engine.predict_all(
            amount=request.amount,
            user_avg=request.user_avg,
            location=request.location,
            timestamp=timestamp
        )
        
        return PredictionResponse(
            model_results=model_results,
            shap_explanation=shap_json
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

@app.post("/api/ml/retrain")
async def retrain(request: RetrainRequest):
    """
    Retrain models using provided transaction data
    """
    try:
        result = ml_engine.retrain_from_database(request.transactions)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retraining error: {str(e)}")

@app.post("/api/ml/fit-initial")
async def fit_initial():
    """
    Fit initial synthetic model
    """
    try:
        ml_engine.fit_initial_model()
        return {"status": "success", "message": "Initial model fitted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fitting error: {str(e)}")

@app.post("/api/ml/calculate-drift")
async def calculate_drift(transactions: list):
    """
    Calculate drift metrics for recent transactions
    """
    try:
        drift_metrics = ml_engine.calculate_drift(transactions)
        return drift_metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Drift calculation error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
