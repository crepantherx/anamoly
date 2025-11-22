import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from sklearn.covariance import EllipticEnvelope
import shap
import json

class MLEngine:
    def __init__(self):
        self.models = {
            "isolation_forest": IsolationForest(contamination=0.1, random_state=42),
            "lof": LocalOutlierFactor(n_neighbors=20, contamination=0.1, novelty=True),
            "one_class_svm": OneClassSVM(nu=0.1, kernel="rbf", gamma=0.1),
            "elliptic_envelope": EllipticEnvelope(contamination=0.1, random_state=42)
        }
        self.current_model_name = "isolation_forest"
        self.current_model = self.models[self.current_model_name]
        self.is_fitted = False
        self.explainer = None
        self.feature_names = ["Amount", "UserAvgDiff", "Hour", "IsForeign"]

    def _preprocess(self, amount, user_avg, location, timestamp):
        # Feature Engineering
        # 1. Amount
        # 2. UserAvgDiff: amount - user_avg
        # 3. Hour: timestamp.hour
        # 4. IsForeign: 1 if location != 'US' else 0 (Simplified logic)
        
        diff = amount - user_avg
        hour = timestamp.hour
        is_foreign = 1 if location not in ['NY', 'CA', 'TX', 'FL'] else 0 # Assuming US states
        
        return np.array([[amount, diff, hour, is_foreign]])

    def fit_initial_model(self):
        # Generate synthetic data for training
        # We need 4 features now
        n_samples = 1000
        X_train = np.zeros((n_samples, 4))
        
        # Normal behavior
        X_train[:, 0] = np.random.normal(100, 20, n_samples) # Amount
        X_train[:, 1] = np.random.normal(0, 10, n_samples)   # Diff
        X_train[:, 2] = np.random.randint(8, 22, n_samples)  # Hour (daytime)
        X_train[:, 3] = np.random.choice([0, 1], n_samples, p=[0.9, 0.1]) # Mostly domestic
        
        for name, model in self.models.items():
            try:
                model.fit(X_train)
            except Exception as e:
                print(f"Error fitting {name}: {e}")
        
        self.is_fitted = True
        
        # Initialize SHAP explainer (using KernelExplainer as generic fallback)
        # Using a small background dataset for speed
        self.background_data = X_train[:50]
        # Note: TreeExplainer is faster for IsolationForest but we need generic for all.
        # For performance in this demo, we might skip full KernelExplainer if it's too slow
        # and just use a simple heuristic or TreeExplainer for IF only.
        # Let's try to use TreeExplainer if current is IF, else Kernel.
        print("Models fitted.")

    def set_model(self, model_name: str):
        if model_name in self.models:
            self.current_model_name = model_name
            self.current_model = self.models[model_name]
            return True
        return False

    def predict(self, amount, user_avg, location, timestamp):
        if not self.is_fitted:
            self.fit_initial_model()
        
        X = self._preprocess(amount, user_avg, location, timestamp)
        
        # Predict
        prediction = self.current_model.predict(X)[0]
        is_anomaly = True if prediction == -1 else False
        score = self.current_model.score_samples(X)[0]
        
        # Explain
        shap_values_json = "{}"
        try:
            # Using a simplified heuristic for speed if SHAP is too heavy for real-time loop
            # But let's try to do it properly for the requested "Explainability"
            
            if self.current_model_name == "isolation_forest":
                explainer = shap.TreeExplainer(self.current_model)
                shap_values = explainer.shap_values(X)
                # shap_values is array
                vals = shap_values[0] if isinstance(shap_values, list) else shap_values
                
                explanation = {
                    "Amount": float(vals[0][0]),
                    "UserAvgDiff": float(vals[0][1]),
                    "Hour": float(vals[0][2]),
                    "IsForeign": float(vals[0][3])
                }
                shap_values_json = json.dumps(explanation)
            else:
                # Fallback: Simple difference from mean
                # This is NOT real SHAP but prevents crashing on non-tree models for now
                # Implementing KernelExplainer in real-time loop is very slow.
                explanation = {
                    "Amount": float(amount - 100), # relative to global mean
                    "UserAvgDiff": float(amount - user_avg),
                    "Hour": float(timestamp.hour - 12),
                    "IsForeign": 100.0 if location not in ['NY', 'CA', 'TX', 'FL'] else 0.0
                }
                shap_values_json = json.dumps(explanation)

        except Exception as e:
            print(f"SHAP Error: {e}")
        
        return is_anomaly, score, shap_values_json

ml_engine = MLEngine()
