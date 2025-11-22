from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List
import json
import asyncio

from . import models, schemas, database
from .ml_engine import ml_engine
from .emulator import emulator

models.Base.metadata.create_all(bind=database.engine)

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
async def transactions_page(request: Request, db: Session = Depends(database.get_db)):
    transactions = db.query(models.Transaction).join(models.User).order_by(models.Transaction.timestamp.desc()).limit(100).all()
    return templates.TemplateResponse("transactions.html", {"request": request, "transactions": transactions})

@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request, db: Session = Depends(database.get_db)):
    users = db.query(models.User).all()
    return templates.TemplateResponse("users.html", {"request": request, "users": users})

@app.get("/api/explain/{tx_id}")
def get_explanation(tx_id: int, db: Session = Depends(database.get_db)):
    tx = db.query(models.Transaction).filter(models.Transaction.id == tx_id).first()
    if not tx:
        return {"error": "Transaction not found"}
    return {"shap": json.loads(tx.shap_explanation) if tx.shap_explanation else {}}

@app.get("/api/stats", response_model=schemas.Stats)
def get_stats(db: Session = Depends(database.get_db)):
    total = db.query(models.Transaction).count()
    anomalies = db.query(models.Transaction).filter(models.Transaction.is_anomaly == True).count()
    rate = (anomalies / total) if total > 0 else 0.0
    return {"total_transactions": total, "total_anomalies": anomalies, "anomaly_rate": rate}

@app.get("/metrics", response_class=HTMLResponse)
def metrics_page(request: Request, db: Session = Depends(database.get_db)):
    # Calculate metrics based on heuristic ground truth
    # Emulator logic: Anomaly if amount > 500 (approx, since it uses uniform(500, 1000))
    # Normal if amount ~ N(100, 20)
    
    transactions = db.query(models.Transaction).all()
    
    tp = 0
    fp = 0
    fn = 0
    tn = 0
    
    for tx in transactions:
        # Use stored ground truth
        is_actual_anomaly = tx.true_label
        
        if is_actual_anomaly and tx.is_anomaly:
            tp += 1
        elif not is_actual_anomaly and tx.is_anomaly:
            fp += 1
        elif is_actual_anomaly and not tx.is_anomaly:
            fn += 1
        else:
            tn += 1
            
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    metrics = {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": precision, "recall": recall, "f1": f1,
        "total_samples": len(transactions)
    }
    
    return templates.TemplateResponse("metrics.html", {"request": request, "metrics": metrics})

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

@app.post("/api/model/select")
def select_model(model_name: str):
    success = ml_engine.set_model(model_name)
    if success:
        return {"status": "success", "current_model": model_name}
    return {"status": "error", "message": "Model not found"}

@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text() # Keep connection open
    except WebSocketDisconnect:
        manager.disconnect(websocket)
