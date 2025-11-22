import numpy as np
from iforest import IForest
import json

class MLEngine:
    def __init__(self):
        """Lightweight ML engine using minimal dependencies"""
        self.iforest_model = None
        self.is_fitted = False
        self.training_data = None
        self.training_mean = 0
        self.training_std = 1
        self.X_train_cols = {}
        
    def _preprocess(self, amount, user_avg, location, timestamp):
        """Preprocess transaction features"""
        diff = amount - user_avg
        hour = timestamp.hour
        is_foreign = 1 if location not in ['NY', 'CA', 'TX', 'FL'] else 0 
        return np.array([[amount, diff, hour, is_foreign]])

    def fit_initial_model(self):
        """Generate synthetic data and train lightweight Isolation Forest"""
        n_samples = 1000
        X_train = np.zeros((n_samples, 4))
        
        # Normal behavior (90%)
        n_normal = int(0.9 * n_samples)
        X_train[:n_normal, 0] = np.random.normal(100, 20, n_normal)  # Amount
        X_train[:n_normal, 1] = np.random.normal(0, 10, n_normal)    # Diff
        X_train[:n_normal, 2] = np.random.randint(8, 22, n_normal)   # Hour
        X_train[:n_normal, 3] = np.random.choice([0, 1], n_normal, p=[0.9, 0.1])
        
        # Anomalous behavior (10%)
        n_anom = n_samples - n_normal
        X_train[n_normal:, 0] = np.random.normal(500, 100, n_anom)   # High Amount
        X_train[n_normal:, 1] = np.random.normal(400, 50, n_anom)    # High Diff
        X_train[n_normal:, 2] = np.random.randint(0, 24, n_anom)     # Any Hour
        X_train[n_normal:, 3] = 1  # Mostly foreign
        
        self.training_data = X_train
        self.training_mean = np.mean(X_train[:, 0])
        self.training_std = np.std(X_train[:, 0])
        
        # Store columns for drift detection
        self.X_train_cols = {
            'Amount': X_train[:, 0],
            'Diff': X_train[:, 1],
            'Hour': X_train[:, 2]
        }
        
        # Train Isolation Forest
        self.iforest_model = IForest(n_trees=100, sample_size=256)
        self.iforest_model.fit(X_train)
        
        self.is_fitted = True
        print("Lightweight model fitted.")

    def retrain_from_database(self, transactions):
        """Retrain model using real transaction data from the database"""
        if not transactions or len(transactions) < 50:
            return {"status": "error", "message": "Not enough data. Need at least 50 transactions."}
        
        X_data = []
        for tx in transactions:
            amount = tx['amount']
            diff = 0  # Simplified
            
            try:
                from datetime import datetime
                timestamp = datetime.fromisoformat(tx['timestamp'].replace('Z', '+00:00'))
                hour = timestamp.hour
            except:
                hour = 12
            
            location = tx.get('location', 'NY')
            is_foreign = 1 if location not in ['NY', 'CA', 'TX', 'FL'] else 0
            
            X_data.append([amount, diff, hour, is_foreign])
        
        X_train = np.array(X_data)
        
        # Update training stats
        self.training_data = X_train
        self.training_mean = np.mean(X_train[:, 0])
        self.training_std = np.std(X_train[:, 0])
        
        self.X_train_cols = {
            'Amount': X_train[:, 0],
            'Diff': X_train[:, 1],
            'Hour': X_train[:, 2]
        }
        
        # Retrain Isolation Forest
        self.iforest_model = IForest(n_trees=100, sample_size=256)
        self.iforest_model.fit(X_train)
        
        self.is_fitted = True
        
        anomaly_count = sum(1 for tx in transactions if tx.get('is_anomaly', False))
        
        return {
            "status": "success", 
            "message": f"Model retrained on {len(transactions)} transactions",
            "normal_count": len(transactions) - anomaly_count,
            "anomaly_count": anomaly_count
        }

    def _calculate_simple_feature_importance(self, X, is_anomaly):
        """Calculate simple feature importance based on deviation from mean"""
        feature_names = ["Amount", "UserAvgDiff", "Hour", "IsForeign"]
        importance = {}
        
        for i, name in enumerate(feature_names):
            # Calculate how much this feature deviates from training mean
            train_mean = np.mean(self.training_data[:, i])
            train_std = np.std(self.training_data[:, i])
            
            if train_std > 0:
                deviation = abs(X[0][i] - train_mean) / train_std
            else:
                deviation = 0
            
            # Higher deviation = higher importance for anomaly
            importance[name] = float(deviation) if is_anomaly else -float(deviation)
        
        return importance

    def predict_all(self, amount, user_avg, location, timestamp):
        """Predict using lightweight Isolation Forest"""
        if not self.is_fitted:
            self.fit_initial_model()
        
        X = self._preprocess(amount, user_avg, location, timestamp)
        
        results = {}
        
        # Isolation Forest prediction
        try:
            score = self.iforest_model.predict(X)[0]
            # IForest returns anomaly scores - higher is more anomalous
            # Typical threshold around 0.5
            is_anomaly = score > 0.5
            
            # Calculate simple feature importance
            explanation = self._calculate_simple_feature_importance(X, is_anomaly)
            shap_json = json.dumps(explanation)
            
            results["isolation_forest"] = {
                "is_anomaly": bool(is_anomaly), 
                "score": float(score)
            }
            
        except Exception as e:
            print(f"Error in Isolation Forest prediction: {e}")
            results["isolation_forest"] = {"is_anomaly": False, "score": 0.0}
            shap_json = "{}"
        
        # Add simple Z-score based detection as backup
        z_score = abs(amount - self.training_mean) / self.training_std if self.training_std > 0 else 0
        results["zscore"] = {
            "is_anomaly": bool(z_score > 3),  # 3 sigma threshold
            "score": float(z_score)
        }
        
        return results, shap_json

    def _ks_test_statistic(self, data1, data2):
        """Lightweight Kolmogorov-Smirnov test implementation"""
        data1 = np.sort(data1)
        data2 = np.sort(data2)
        n1 = len(data1)
        n2 = len(data2)
        
        # Combine and sort all data
        all_data = np.concatenate([data1, data2])
        all_data = np.sort(all_data)
        
        # Calculate empirical CDFs
        cdf1 = np.searchsorted(data1, all_data, side='right') / n1
        cdf2 = np.searchsorted(data2, all_data, side='right') / n2
        
        # KS statistic is max absolute difference
        ks_stat = np.max(np.abs(cdf1 - cdf2))
        
        # Approximate p-value (simplified)
        # For large samples, use asymptotic approximation
        en = np.sqrt(n1 * n2 / (n1 + n2))
        p_value = 2 * np.exp(-2 * en * en * ks_stat * ks_stat)
        
        return ks_stat, min(p_value, 1.0)

    def detect_covariate_drift(self, recent_data):
        """KS Test for Covariate Drift on Amount"""
        if not self.is_fitted or not recent_data:
            return {}
        
        recent_amounts = [t['amount'] for t in recent_data]
        if len(recent_amounts) < 20:
            return {"Amount": {"p_value": 1.0, "drift": False}}
        
        stat, p_value = self._ks_test_statistic(self.X_train_cols['Amount'], np.array(recent_amounts))
        
        return {
            "Amount": {
                "p_value": float(p_value), 
                "drift": p_value < 0.05
            }
        }

    def detect_label_drift(self, recent_anomalies, total_recent):
        """Label Drift (Prior Probability Shift)"""
        if total_recent == 0:
            return {"drift": False, "current_rate": 0.0}
        
        current_rate = recent_anomalies / total_recent
        training_rate = 0.10  # 10% anomalies in training
        
        drift = abs(current_rate - training_rate) > 0.05
        return {"drift": drift, "current_rate": float(current_rate)}

    def detect_concept_drift(self, recent_transactions):
        """DDM (Drift Detection Method) approximation"""
        if not recent_transactions:
            return {"status": "Stable", "error_rate": 0.0}
        
        errors = 0
        for tx in recent_transactions:
            # Check if model prediction matches true_label
            res = tx.get('model_results', {}).get('isolation_forest', {})
            pred = res.get('is_anomaly', False)
            actual = tx['true_label']
            if pred != actual:
                errors += 1
        
        error_rate = errors / len(recent_transactions)
        
        # Simplified DDM thresholds
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
        """Calculate all drift metrics"""
        default_drift = {
            "z_score": 0.0,
            "covariate": None,
            "label": None,
            "concept": None
        }
        
        if not self.is_fitted or not recent_transactions:
            return default_drift
        
        # 1. Simple Z-Score
        recent_amounts = [t['amount'] for t in recent_transactions]
        recent_mean = np.mean(recent_amounts)
        z_score = abs(recent_mean - self.training_mean) / self.training_std if self.training_std > 0 else 0
        
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
