"""
ML Client - HTTP client for communicating with ML Service
"""
import httpx
import os
from datetime import datetime
from typing import Dict, Tuple

class MLClient:
    def __init__(self):
        self.ml_service_url = os.getenv("ML_SERVICE_URL", "http://localhost:8001")
        self.timeout = 30.0
        
    async def predict_all(self, amount: float, user_avg: float, location: str, timestamp: datetime) -> Tuple[Dict, str]:
        """
        Call ML service to predict anomaly
        Returns: (model_results, shap_json)
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.ml_service_url}/api/ml/predict",
                    json={
                        "amount": amount,
                        "user_avg": user_avg,
                        "location": location,
                        "timestamp": timestamp.isoformat()
                    }
                )
                response.raise_for_status()
                data = response.json()
                return data["model_results"], data["shap_explanation"]
        except httpx.HTTPError as e:
            print(f"ML Service error: {e}")
            # Return default fallback response
            return {
                "isolation_forest": {"is_anomaly": False, "score": 0.0}
            }, "{}"
        except Exception as e:
            print(f"Unexpected error calling ML service: {e}")
            return {
                "isolation_forest": {"is_anomaly": False, "score": 0.0}
            }, "{}"
    
    async def retrain_from_database(self, transactions: list) -> Dict:
        """
        Call ML service to retrain models
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.ml_service_url}/api/ml/retrain",
                    json={"transactions": transactions}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"Retrain error: {e}")
            return {"status": "error", "message": str(e)}
    
    async def calculate_drift(self, recent_transactions: list) -> Dict:
        """
        Call ML service to calculate drift metrics
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ml_service_url}/api/ml/calculate-drift",
                    json=recent_transactions
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"Drift calculation error: {e}")
            return {
                "z_score": 0.0,
                "covariate": None,
                "label": None,
                "concept": None
            }
    
    async def health_check(self) -> bool:
        """
        Check if ML service is healthy
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.ml_service_url}/health")
                response.raise_for_status()
                return True
        except:
            return False

# Singleton instance
ml_client = MLClient()
