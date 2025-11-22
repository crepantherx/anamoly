import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from sklearn.covariance import EllipticEnvelope
from sklearn.neural_network import MLPClassifier
import shap
import json

class MLEngine:
    def __init__(self):
        self.models = {
            "isolation_forest": IsolationForest(contamination=0.1, random_state=42),
            "lof": LocalOutlierFactor(n_neighbors=20, contamination=0.1, novelty=True),
            "one_class_svm": OneClassSVM(nu=0.1, kernel="rbf", gamma=0.1),
            "elliptic_envelope": EllipticEnvelope(contamination=0.1, random_state=42),
            "mlp": MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=500, random_state=42)
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
        y_train = np.zeros(n_samples) # 0 = Normal, 1 = Anomaly
        
        # Normal behavior (90%)
        n_normal = int(0.9 * n_samples)
        X_train[:n_normal, 0] = np.random.normal(100, 20, n_normal) # Amount
        X_train[:n_normal, 1] = np.random.normal(0, 10, n_normal)   # Diff
        X_train[:n_normal, 2] = np.random.randint(8, 22, n_normal)  # Hour
        X_train[:n_normal, 3] = np.random.choice([0, 1], n_normal, p=[0.9, 0.1]) 
        y_train[:n_normal] = 0

        # Anomalous behavior (10%) - Needed for MLP training
        n_anom = n_samples - n_normal
        X_train[n_normal:, 0] = np.random.normal(500, 100, n_anom) # High Amount
        X_train[n_normal:, 1] = np.random.normal(400, 50, n_anom)  # High Diff
        X_train[n_normal:, 2] = np.random.randint(0, 24, n_anom)   # Any Hour
        X_train[n_normal:, 3] = 1 # Mostly foreign
        y_train[n_normal:] = 1
        
        self.training_data = X_train
        self.training_mean = np.mean(X_train[:, 0]) # Track Amount mean for drift
        self.training_std = np.std(X_train[:, 0])

        for name, model in self.models.items():
            try:
                if name == "mlp":
                    model.fit(X_train, y_train)
                else:
                    model.fit(X_train) # Unsupervised models ignore y
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
                if name == "mlp":
                    # MLP predicts class 0 or 1
                    prediction = model.predict(X)[0]
                    is_anomaly = True if prediction == 1 else False
                    # Use probability of class 1 as score (negated to match others where lower is worse? No, others are: -1 is anomaly)
                    # Let's standardize: score < 0 is anomaly usually.
                    # For MLP, prob(1) > 0.5 is anomaly. 
                    # To map to "score_samples" style (higher = normal), we can use -prob(1).
                    # Or just return raw probability.
                    # Let's stick to the convention: is_anomaly boolean is key.
                    # For score, let's use -prob(anomaly) so that lower is more anomalous?
                    # Wait, IsolationForest: lower score = more anomalous.
                    # Let's use -prob(1) as score. Normal (prob 0) -> 0. Anomaly (prob 1) -> -1.
                    probs = model.predict_proba(X)[0]
                    score = -probs[1] 
                else:
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
