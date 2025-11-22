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
        self.is_fitted = False
        self.training_data = None
        self.training_mean = 0
        self.training_std = 1

    def _preprocess(self, amount, user_avg, location, timestamp):
        diff = amount - user_avg
        hour = timestamp.hour
        is_foreign = 1 if location not in ['NY', 'CA', 'TX', 'FL'] else 0 
        return np.array([[amount, diff, hour, is_foreign]])

    def fit_initial_model(self):
        # Generate synthetic data for training
        n_samples = 1000
        X_train = np.zeros((n_samples, 4))
        
        # Normal behavior
        X_train[:, 0] = np.random.normal(100, 20, n_samples) # Amount
        X_train[:, 1] = np.random.normal(0, 10, n_samples)   # Diff
        X_train[:, 2] = np.random.randint(8, 22, n_samples)  # Hour
        X_train[:, 3] = np.random.choice([0, 1], n_samples, p=[0.9, 0.1]) 
        
        self.training_data = X_train
        self.training_mean = np.mean(X_train[:, 0]) # Track Amount mean for drift
        self.training_std = np.std(X_train[:, 0])

        for name, model in self.models.items():
            try:
                model.fit(X_train)
            except Exception as e:
                print(f"Error fitting {name}: {e}")
        
        self.is_fitted = True
        print("Models fitted.")

    def predict_all(self, amount, user_avg, location, timestamp):
        if not self.is_fitted:
            self.fit_initial_model()
        
        X = self._preprocess(amount, user_avg, location, timestamp)
        
        results = {}
        shap_json = "{}"
        
        for name, model in self.models.items():
            try:
                prediction = model.predict(X)[0]
                is_anomaly = True if prediction == -1 else False
                score = model.score_samples(X)[0]
                results[name] = {"is_anomaly": is_anomaly, "score": float(score)}
                
                # Generate SHAP only for Isolation Forest for the UI explanation
                if name == "isolation_forest":
                    try:
                        explainer = shap.TreeExplainer(model)
                        shap_values = explainer.shap_values(X)
                        vals = shap_values[0] if isinstance(shap_values, list) else shap_values
                        explanation = {
                            "Amount": float(vals[0][0]),
                            "UserAvgDiff": float(vals[0][1]),
                            "Hour": float(vals[0][2]),
                            "IsForeign": float(vals[0][3])
                        }
                        shap_json = json.dumps(explanation)
                    except:
                        pass
            except Exception as e:
                print(f"Error predicting {name}: {e}")
                results[name] = {"is_anomaly": False, "score": 0.0}

        return results, shap_json

    def calculate_drift(self, recent_amounts):
        if not self.is_fitted or not recent_amounts:
            return 0.0
        
        # Simple Drift Metric: Z-score of the recent mean vs training mean
        recent_mean = np.mean(recent_amounts)
        z_score = abs(recent_mean - self.training_mean) / self.training_std
        return float(z_score)

ml_engine = MLEngine()
