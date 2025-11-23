from .database import supabase
import datetime

def create_user(user_data: dict):
    data = supabase.table("users").insert(user_data).execute()
    return data.data[0] if data.data else None

def get_all_users():
    data = supabase.table("users").select("*").execute()
    return data.data

def create_transaction(tx_data: dict):
    # Ensure timestamp is string for JSON serialization
    if isinstance(tx_data.get('timestamp'), datetime.datetime):
        tx_data['timestamp'] = tx_data['timestamp'].isoformat()
        
    data = supabase.table("transactions").insert(tx_data).execute()
    return data.data[0] if data.data else None

def get_recent_transactions(limit: int = 100):
    # Join with users table
    data = supabase.table("transactions").select("*, users(name)").order("timestamp", desc=True).limit(limit).execute()
    return data.data

def get_transaction_stats():
    # Efficient count query
    total_res = supabase.table("transactions").select("*", count="exact", head=True).execute()
    total = total_res.count
    
    # Count anomalies
    anomalies_res = supabase.table("transactions").select("*", count="exact", head=True).eq("is_anomaly", True).execute()
    anomalies = anomalies_res.count
    
    return total, anomalies

def get_all_transactions():
    # Warning: This hits default limit of 1000
    data = supabase.table("transactions").select("*").execute()
    return data.data

def get_transaction_by_id(tx_id: int):
    data = supabase.table("transactions").select("*").eq("id", tx_id).execute()
    return data.data[0] if data.data else None

def get_transactions_by_user(user_id: int):
    data = supabase.table("transactions").select("*").eq("user_id", user_id).order("timestamp", desc=True).execute()
    return data.data

def get_user_by_id(user_id: int):
    data = supabase.table("users").select("*").eq("id", user_id).execute()
    return data.data[0] if data.data else None

# --- Emulation State Management (Hack using dummy user) ---
EMULATOR_USER_EMAIL = "system_emulator@internal"

def get_emulation_status_from_db():
    """
    Returns True if emulation is running, False otherwise.
    Uses a dummy user's risk_score as a flag (1.0 = running, 0.0 = stopped).
    """
    data = supabase.table("users").select("risk_score").eq("email", EMULATOR_USER_EMAIL).execute()
    if data.data:
        return data.data[0]['risk_score'] == 1.0
    return False

def set_emulation_status_in_db(is_running: bool):
    """
    Sets the emulation status in the DB.
    Creates the dummy user if it doesn't exist.
    """
    status_val = 1.0 if is_running else 0.0
    
    # Check if user exists
    data = supabase.table("users").select("id").eq("email", EMULATOR_USER_EMAIL).execute()
    
    if data.data:
        # Update
        supabase.table("users").update({"risk_score": status_val}).eq("email", EMULATOR_USER_EMAIL).execute()
    else:
        # Create
        user_data = {
            "name": "System Emulator",
            "account_number": "SYS_EMULATOR",
            "email": EMULATOR_USER_EMAIL,
            "risk_score": status_val,
            "avg_transaction_amount": 0.0
        }
        supabase.table("users").insert(user_data).execute()
