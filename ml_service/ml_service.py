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

@app.on_event("startup")
async def startup_event():
    """Service startup - models will be fitted on first prediction"""
    print("🚀 ML Service starting up...")
    print("📊 Models will be fitted on first prediction request")
    print("✅ Service ready!")

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
    Models are fitted automatically on first prediction if not already fitted.
    """
    try:
        # Parse timestamp
        timestamp = datetime.fromisoformat(request.timestamp.replace('Z', '+00:00'))
        
        # Check if models need fitting (will happen on first prediction)
        if not ml_engine.is_fitted:
            print("📊 First prediction - fitting models with synthetic data...")
        
        # Get predictions from all models (auto-fits if needed)
        model_results, shap_json = ml_engine.predict_all(
            amount=request.amount,
            user_avg=request.user_avg,
            location=request.location,
            timestamp=timestamp
        )
        
        # Log prediction for debugging
        is_anomaly = model_results.get("isolation_forest", {}).get("is_anomaly", False)
        print(f"💳 Prediction: amount=${request.amount:.2f}, anomaly={is_anomaly}")
        
        return PredictionResponse(
            model_results=model_results,
            shap_explanation=shap_json
        )
    except Exception as e:
        print(f"❌ Prediction error: {str(e)}")
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

@app.get("/api/ml/debug")
async def debug_info():
    """Debug endpoint to check model status"""
    return {
        "models_fitted": ml_engine.is_fitted,
        "training_stats": {
            "mean": float(ml_engine.training_mean) if ml_engine.is_fitted else None,
            "std": float(ml_engine.training_std) if ml_engine.is_fitted else None,
        },
        "available_models": list(ml_engine.models.keys()) if ml_engine.is_fitted else [],
        "message": "Models are fitted and ready" if ml_engine.is_fitted else "Models not fitted yet - will fit on first prediction"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
