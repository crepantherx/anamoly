from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List
import json
import asyncio

from . import schemas, crud
from .ml_engine import ml_engine
from .emulator import emulator

app = FastAPI(title="Anomaly Detection Dashboard")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/transactions", response_class=HTMLResponse)
async def transactions_page(request: Request):
    transactions = crud.get_recent_transactions(100)
    return templates.TemplateResponse("transactions.html", {"request": request, "transactions": transactions})

@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request):
    users = crud.get_all_users()
    return templates.TemplateResponse("users.html", {"request": request, "users": users})

@app.get("/users/{user_id}", response_class=HTMLResponse)
async def user_details_page(request: Request, user_id: int):
    user = crud.get_user_by_id(user_id)
    transactions = crud.get_transactions_by_user(user_id)
    return templates.TemplateResponse("user_details.html", {"request": request, "user": user, "transactions": transactions})

@app.get("/api/explain/{tx_id}")
def get_explanation(tx_id: int):
    tx = crud.get_transaction_by_id(tx_id)
    if not tx:
        return {"error": "Transaction not found"}
    return {"shap": json.loads(tx['shap_explanation']) if tx.get('shap_explanation') else {}}

@app.get("/api/stats", response_model=schemas.Stats)
def get_stats():
    # Supabase count is a bit tricky without direct SQL or specific count query
    # For now, we fetch all (inefficient but works for demo) or use a separate count function
    # Optimization: Use Supabase count option
    # data = supabase.table("transactions").select("*", count="exact").execute()
    # total = data.count
    
    # Let's just use the crud.get_all_transactions for now as dataset is small
    txs = crud.get_all_transactions()
    total = len(txs)
    anomalies = sum(1 for t in txs if t['is_anomaly'])
    rate = (anomalies / total) if total > 0 else 0.0
    return {"total_transactions": total, "total_anomalies": anomalies, "anomaly_rate": rate}

@app.get("/metrics", response_class=HTMLResponse)
def metrics_page(request: Request):
    transactions = crud.get_all_transactions()
    
    # Calculate metrics for ALL models
    models_metrics = {}
    model_names = ["isolation_forest", "lof", "one_class_svm", "elliptic_envelope", "mlp"]
    
    for name in model_names:
        tp = fp = fn = tn = 0
        for tx in transactions:
            is_actual_anomaly = tx['true_label']
            
            # Get result for this specific model
            # model_results is stored as JSONB
            res = tx.get('model_results', {}).get(name, {})
            is_predicted_anomaly = res.get('is_anomaly', False)
            
            if is_actual_anomaly and is_predicted_anomaly:
                tp += 1
            elif not is_actual_anomaly and is_predicted_anomaly:
                fp += 1
            elif is_actual_anomaly and not is_predicted_anomaly:
                fn += 1
            else:
                tn += 1
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        models_metrics[name] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn
        }

    # Calculate Drift
    recent_amounts = [t['amount'] for t in transactions[-100:]] if transactions else []
    drift_score = ml_engine.calculate_drift(recent_amounts)

    return templates.TemplateResponse("metrics.html", {
        "request": request, 
        "metrics": models_metrics, 
        "drift": drift_score,
        "total_samples": len(transactions)
    })

@app.get("/explainability", response_class=HTMLResponse)
async def explainability_page(request: Request):
    return templates.TemplateResponse("explainability.html", {"request": request})

@app.get("/design", response_class=HTMLResponse)
async def design_page(request: Request):
    return templates.TemplateResponse("design.html", {"request": request})

@app.post("/api/emulation/start")
async def start_emulation(background_tasks: BackgroundTasks):
    if not emulator.is_running:
        background_tasks.add_task(emulator.start_emulation, manager.broadcast)
        return {"status": "started"}
    return {"status": "already running"}

@app.post("/api/emulation/stop")
def stop_emulation():
    emulator.stop_emulation()
    return {"status": "stopped"}

@app.get("/api/emulation/status")
def get_emulation_status():
    return {"status": "running" if emulator.is_running else "stopped"}

@app.post("/api/model/select")
def select_model(model_name: str):
    # With multi-model tracking, this just changes the "Primary" model for the dashboard view
    # We can update MLEngine to track "current_view_model"
    # For now, we just return success as the backend runs all anyway
    return {"status": "success", "current_model": model_name}

@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text() # Keep connection open
    except WebSocketDisconnect:
        manager.disconnect(websocket)
