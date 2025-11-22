from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base
import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    account_number = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    avg_transaction_amount = Column(Float, default=100.0)
    risk_score = Column(Float, default=0.0)
    
    transactions = relationship("Transaction", back_populates="user")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float, nullable=False)
    location = Column(String, nullable=False)
    category = Column(String, nullable=False) # e.g., 'Food', 'Travel', 'Electronics'
    receiver_account = Column(String, nullable=True)
    device_id = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    is_anomaly = Column(Boolean, default=False) # Model prediction
    true_label = Column(Boolean, default=False) # Ground truth (from emulator)
    anomaly_score = Column(Float, nullable=True)
    model_used = Column(String, nullable=True)
    shap_explanation = Column(Text, nullable=True) # JSON string of feature contributions
    
    user = relationship("User", back_populates="transactions")
