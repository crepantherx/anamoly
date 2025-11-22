-- Create Users Table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    account_number TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    avg_transaction_amount FLOAT DEFAULT 100.0,
    risk_score FLOAT DEFAULT 0.0
);

-- Create Transactions Table
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    amount FLOAT NOT NULL,
    location TEXT NOT NULL,
    category TEXT NOT NULL,
    receiver_account TEXT,
    device_id TEXT,
    timestamp TIMESTAMP DEFAULT NOW(),
    is_anomaly BOOLEAN DEFAULT FALSE,
    true_label BOOLEAN DEFAULT FALSE,
    anomaly_score FLOAT,
    model_used TEXT,
    shap_explanation TEXT,
    model_results JSONB -- Store results from all models: {"lof": {"score": 0.1, "is_anomaly": false}, ...}
);
