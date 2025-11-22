import asyncio
import random
import datetime
from sqlalchemy.orm import Session
from faker import Faker
from . import models, schemas
from .database import SessionLocal
from .ml_engine import ml_engine

fake = Faker()

class Emulator:
    def __init__(self):
        self.is_running = False
        self.anomaly_probability = 0.1
        self.users_created = False

    def create_initial_users(self, db: Session):
        if db.query(models.User).count() > 0:
            self.users_created = True
            return

        print("Creating 50 synthetic users...")
        for _ in range(50):
            user = models.User(
                name=fake.name(),
                account_number=fake.iban(),
                email=fake.email(),
                avg_transaction_amount=random.uniform(50, 500)
            )
            db.add(user)
        db.commit()
        self.users_created = True

    async def start_emulation(self, broadcast_callback):
        self.is_running = True
        print("Emulation started...")
        
        db = SessionLocal()
        self.create_initial_users(db)
        db.close()

        while self.is_running:
            db = SessionLocal()
            try:
                # Pick random user
                users = db.query(models.User).all()
                if not users:
                    break
                user = random.choice(users)
                
                timestamp = datetime.datetime.utcnow()
                
                # Generate data
                is_generated_anomaly = False
                if random.random() < self.anomaly_probability:
                    is_generated_anomaly = True
                    # Anomaly Scenarios
                    scenario = random.choice(['spike', 'foreign', 'midnight'])
                    if scenario == 'spike':
                        amount = user.avg_transaction_amount * random.uniform(5, 10)
                        location = "NY"
                    elif scenario == 'foreign':
                        amount = user.avg_transaction_amount * random.uniform(1, 2)
                        location = random.choice(["JP", "CN", "RU", "BR"])
                    else: # midnight
                        amount = user.avg_transaction_amount * random.uniform(1, 3)
                        location = "NY"
                else:
                    # Normal
                    amount = random.normalvariate(user.avg_transaction_amount, user.avg_transaction_amount * 0.1)
                    amount = max(1.0, amount)
                    location = random.choice(["NY", "CA", "TX", "FL"])

                category = random.choice(['Food', 'Travel', 'Electronics', 'Utilities', 'Transfer'])
                device = fake.uuid4()
                receiver = fake.iban() if category == 'Transfer' else fake.company()

                # Predict
                is_anomaly, score, shap_json = ml_engine.predict(amount, user.avg_transaction_amount, location, timestamp)
                
                # Save to DB
                db_transaction = models.Transaction(
                    user_id=user.id,
                    amount=amount,
                    location=location,
                    category=category,
                    receiver_account=receiver,
                    device_id=device,
                    is_anomaly=is_anomaly,
                    true_label=is_generated_anomaly,
                    anomaly_score=score,
                    model_used=ml_engine.current_model_name,
                    shap_explanation=shap_json,
                    timestamp=timestamp
                )
                db.add(db_transaction)
                db.commit()
                db.refresh(db_transaction)
                
                # Broadcast via WebSocket
                data = {
                    "id": db_transaction.id,
                    "user": user.name,
                    "amount": round(db_transaction.amount, 2),
                    "location": db_transaction.location,
                    "timestamp": db_transaction.timestamp.isoformat(),
                    "is_anomaly": db_transaction.is_anomaly,
                    "score": round(db_transaction.anomaly_score, 4) if db_transaction.anomaly_score else 0,
                    "shap": shap_json
                }
                await broadcast_callback(data)
                
            except Exception as e:
                print(f"Error in emulation: {e}")
            finally:
                db.close()
            
            await asyncio.sleep(random.uniform(0.5, 2.0)) # Random interval

    def stop_emulation(self):
        self.is_running = False
        print("Emulation stopped.")

emulator = Emulator()
