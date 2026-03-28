from database.db import supabase
import json

tables = ["users", "workflows", "tasks", "audit_logs"]
for table in tables:
    try:
        res = supabase.table(table).select("*").limit(1).execute()
        if res.data:
            print(f"Table '{table}' keys:", list(res.data[0].keys()))
        else:
            print(f"Table '{table}' is empty")
    except Exception as e:
        print(f"Error listing table '{table}': {e}")
