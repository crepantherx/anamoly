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

def get_all_transactions():
    data = supabase.table("transactions").select("*").execute()
    return data.data

def get_transaction_by_id(tx_id: int):
    data = supabase.table("transactions").select("*").eq("id", tx_id).execute()
    return data.data[0] if data.data else None
