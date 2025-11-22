from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class UserBase(BaseModel):
    name: str
    account_number: str
    email: str
    avg_transaction_amount: float

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    risk_score: float

    class Config:
        orm_mode = True

class TransactionBase(BaseModel):
    amount: float
    location: str
    category: str
    receiver_account: Optional[str] = None
    device_id: Optional[str] = None

class TransactionCreate(TransactionBase):
    user_id: int

class Transaction(TransactionBase):
    id: int
    user_id: int
    timestamp: datetime
    is_anomaly: bool
    anomaly_score: Optional[float] = None
    model_used: Optional[str] = None
    shap_explanation: Optional[str] = None
    
    user: Optional[User] = None

    class Config:
        orm_mode = True

class Stats(BaseModel):
    total_transactions: int
    total_anomalies: int
    anomaly_rate: float
