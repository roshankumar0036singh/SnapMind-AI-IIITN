"""
Quick test script to verify connection to Supabase.
Run:
    python -m src.test_supabase
"""
import sys
from src.supabase_client import get_supabase_client, get_supabase_admin

def test_connection():
    print("Testing Supabase connection...")
    try:
        client = get_supabase_client()
        print(" [OK] Supabase public client initialized successfully.")
        
        admin = get_supabase_admin()
        print(" [OK] Supabase admin client initialized successfully.")
        
        # Test basic ping or table query
        res = admin.table("runemark_documents").select("doc_id").limit(1).execute()
        print(" [OK] Connected to Supabase Database successfully! Table query executed.")
        return True
    except Exception as e:
        print(f" [Notice] Client connected, but query failed (table may not be created yet): {e}")
        print("Tip: Run the SQL in `supabase_schema.sql` on your Supabase SQL Editor if tables don't exist yet.")
        return False

if __name__ == "__main__":
    test_connection()
