import asyncio
import random
import datetime
from faker import Faker
from . import crud
from .ml_client import ml_client

fake = Faker()

class Emulator:
    def __init__(self):
        # self.is_running is now just a local cache, source of truth is DB
        self.anomaly_probability = 0.1
        self.users_created = False

    @property
    def is_running(self):
        return crud.get_emulation_status_from_db()

    def create_initial_users(self):
        users = crud.get_all_users()
        # Filter out system user
        real_users = [u for u in users if u['email'] != crud.EMULATOR_USER_EMAIL]
        
        if real_users and len(real_users) > 0:
            self.users_created = True
            return

        print("Creating 50 synthetic users...")
        for _ in range(50):
            user_data = {
                "name": fake.name(),
                "account_number": fake.iban(),
                "email": fake.email(),
                "avg_transaction_amount": random.uniform(50, 500),
                "risk_score": 0.0
            }
            crud.create_user(user_data)
        self.users_created = True

    async def start_emulation(self, broadcast_callback):
        # Set DB status to running
        crud.set_emulation_status_in_db(True)
        print("Emulation started...")
        
        self.create_initial_users()

        while True:
            # Check DB status every loop to see if we should stop
            # This allows stopping from a different instance
            if not crud.get_emulation_status_from_db():
                print("Emulation stopped by DB flag.")
                break

            try:
                # Pick random user
                users = crud.get_all_users()
                # Filter out system user
                real_users = [u for u in users if u['email'] != crud.EMULATOR_USER_EMAIL]
                
                if not real_users:
                    break
                user = random.choice(real_users)
                
                timestamp = datetime.datetime.utcnow()
                
                # Generate data
                is_generated_anomaly = False
                if random.random() < self.anomaly_probability:
                    is_generated_anomaly = True
                    scenario = random.choice(['spike', 'foreign', 'midnight'])
                    if scenario == 'spike':
                        amount = user['avg_transaction_amount'] * random.uniform(5, 10)
                        location = "NY"
                    elif scenario == 'foreign':
                        amount = user['avg_transaction_amount'] * random.uniform(1, 2)
                        location = random.choice(["JP", "CN", "RU", "BR"])
                    else: # midnight
                        amount = user['avg_transaction_amount'] * random.uniform(1, 3)
                        location = "NY"
                else:
                    amount = random.normalvariate(user['avg_transaction_amount'], user['avg_transaction_amount'] * 0.1)
                    amount = max(1.0, amount)
                    location = random.choice(["NY", "CA", "TX", "FL"])

                category = random.choice(['Food', 'Travel', 'Electronics', 'Utilities', 'Transfer'])
                device = fake.uuid4()
                receiver = fake.iban() if category == 'Transfer' else fake.company()

                # Predict All Models - Use ML Client (async call)
                model_results, shap_json = await ml_client.predict_all(amount, user['avg_transaction_amount'], location, timestamp)
                
                # Use Isolation Forest as the "Primary" for the dashboard main view
                primary_result = model_results.get("isolation_forest", {"is_anomaly": False, "score": 0})

                # Save to DB
                tx_data = {
                    "user_id": user['id'],
                    "amount": amount,
                    "location": location,
                    "category": category,
                    "receiver_account": receiver,
                    "device_id": device,
                    "is_anomaly": primary_result['is_anomaly'],
                    "true_label": is_generated_anomaly,
                    "anomaly_score": primary_result['score'],
                    "model_used": "isolation_forest", # Primary
                    "shap_explanation": shap_json,
                    "model_results": model_results,
                    "timestamp": timestamp
                }
                
                new_tx = crud.create_transaction(tx_data)
                
                if new_tx:
                    # Broadcast via WebSocket (if connected)
                    # Note: With polling, this is less critical but good for local dev
                    data = {
                        "id": new_tx['id'],
                        "user": user['name'],
                        "amount": round(new_tx['amount'], 2),
                        "location": new_tx['location'],
                        "timestamp": new_tx['timestamp'],
                        "is_anomaly": new_tx['is_anomaly'],
                        "score": round(new_tx['anomaly_score'], 4) if new_tx['anomaly_score'] else 0,
                        "shap": shap_json
                    }
                    await broadcast_callback(data)
                
            except Exception as e:
                print(f"Error in emulation: {e}")
            
            await asyncio.sleep(random.uniform(0.5, 2.0))

    def stop_emulation(self):
        # Just update DB, the loop will catch it
        crud.set_emulation_status_in_db(False)
        print("Emulation stop signal sent to DB.")

emulator = Emulator()
