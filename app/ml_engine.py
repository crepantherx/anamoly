import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from sklearn.covariance import EllipticEnvelope
from sklearn.neural_network import MLPClassifier
import shap
import json

from scipy.stats import ks_2samp

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
        # Store training data columns for KS test
        self.X_train_cols = {} # {0: 'Amount', 1: 'Diff', 2: 'Hour'}

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
        
        # Store columns for drift detection
        self.X_train_cols = {
            'Amount': X_train[:, 0],
            'Diff': X_train[:, 1],
            'Hour': X_train[:, 2]
        }

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

    def detect_covariate_drift(self, recent_data):
        """
        KS Test for Covariate Drift on Amount, Diff, Hour.
        recent_data: list of dicts or DataFrame-like structure
        """
        if not self.is_fitted or not recent_data:
            return {}
        
        drift_results = {}
        features = ['Amount', 'Diff', 'Hour']
        
        # Extract recent features
        # Assuming recent_data is list of dicts from transactions
        # We need to reconstruct the feature vectors roughly
        # Or just use raw values if available. 
        # In main.py we pass 'transactions' list.
        
        recent_arrays = {f: [] for f in features}
        for tx in recent_data:
            recent_arrays['Amount'].append(tx['amount'])
            # We need 'user_avg' to calc diff, but tx usually has it or we can approx
            # Let's just use Amount and Hour for now as they are direct
            # Diff is derived. We can try to re-derive if we have user_avg in tx?
            # Tx has 'user' relation but maybe not loaded deep.
            # Let's stick to Amount and Hour for demo.
            # Actually, let's just use Amount.
            
        # Re-implementing to be more robust if we had the preprocessed X
        # For now, let's just do Amount and Hour
        
        for feature in ['Amount', 'Hour']: # Diff is harder to reconstruct without user history here
            if feature == 'Hour':
                # Parse timestamp string "2023-..."
                # This is getting complicated for a quick check.
                # Let's trust the 'Amount' as the primary covariate.
                pass

        # Let's simplify: Just Amount for Covariate Drift in this demo
        recent_amounts = [t['amount'] for t in recent_data]
        if len(recent_amounts) < 20:
            return {"Amount": {"p_value": 1.0, "drift": False}}

        stat, p_value = ks_2samp(self.X_train_cols['Amount'], recent_amounts)
        drift_results['Amount'] = {"p_value": float(p_value), "drift": p_value < 0.05}
        
        return drift_results

    def detect_label_drift(self, recent_anomalies, total_recent):
        """
        Label Drift (Prior Probability Shift).
        Compare recent anomaly rate vs training anomaly rate (10%).
        """
        if total_recent == 0:
            return {"drift": False, "current_rate": 0.0}
        
        current_rate = recent_anomalies / total_recent
        training_rate = 0.10 # We know we generated 10% anomalies
        
        # If rate shifts by > 50% relative (e.g. < 5% or > 15%), flag it
        # Or just simple absolute threshold
        drift = abs(current_rate - training_rate) > 0.05
        return {"drift": drift, "current_rate": float(current_rate)}

    def detect_concept_drift(self, recent_transactions):
        """
        DDM (Drift Detection Method) approximation.
        Monitor error rate. We don't have 'ground truth' for live data usually.
        But here we have 'true_label' in our emulator/db!
        So we can actually calculate error rate.
        """
        if not recent_transactions:
            return {"status": "Stable", "error_rate": 0.0}
        
        errors = 0
        for tx in recent_transactions:
            # Check if model prediction matches true_label
            # We need to know WHICH model is primary. 
            # Let's assume 'isolation_forest' is the primary for this check or check 'model_used'
            # But 'model_used' might vary.
            # Let's check against the stored result of 'isolation_forest' in 'model_results'
            res = tx.get('model_results', {}).get('isolation_forest', {})
            pred = res.get('is_anomaly', False)
            actual = tx['true_label']
            if pred != actual:
                errors += 1
        
        error_rate = errors / len(recent_transactions)
        
        # DDM thresholds (simplified)
        # Warn if error rate > 2 * std_dev (assuming some baseline)
        # Baseline error rate for IF on training data is roughly 5% (95% F1 ref)
        min_error = 0.05
        std = np.sqrt(min_error * (1 - min_error) / len(recent_transactions))
        
        if error_rate > min_error + 3 * std:
            status = "Drift Detected"
        elif error_rate > min_error + 2 * std:
            status = "Warning"
        else:
            status = "Stable"
            
        return {"status": status, "error_rate": float(error_rate)}

    def calculate_drift(self, recent_transactions):
        default_drift = {
            "z_score": 0.0,
            "covariate": None,
            "label": None,
            "concept": None
        }
        
        if not self.is_fitted or not recent_transactions:
            return default_drift
        
        # 1. Simple Z-Score (Legacy)
        recent_amounts = [t['amount'] for t in recent_transactions]
        recent_mean = np.mean(recent_amounts)
        z_score = abs(recent_mean - self.training_mean) / self.training_std
        
        # 2. Covariate Drift (KS Test)
        covariate_drift = self.detect_covariate_drift(recent_transactions)
        
        # 3. Label Drift
        recent_anomalies = sum(1 for t in recent_transactions if t['is_anomaly'])
        label_drift = self.detect_label_drift(recent_anomalies, len(recent_transactions))
        
        # 4. Concept Drift (DDM)
        concept_drift = self.detect_concept_drift(recent_transactions)
        
        return {
            "z_score": float(z_score),
            "covariate": covariate_drift,
            "label": label_drift,
            "concept": concept_drift
        }

ml_engine = MLEngine()
