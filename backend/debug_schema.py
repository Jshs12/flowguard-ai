from database.db import supabase
import json

def debug_table(table_name):
    print(f"\n--- Table: {table_name} ---")
    try:
        res = supabase.table(table_name).select("*").limit(1).execute()
        if res.data:
            print(f"Columns: {list(res.data[0].keys())}")
            # print(f"Sample data: {json.dumps(res.data[0], indent=2)}")
        else:
            print("No data found")
    except Exception as e:
        print(f"Error checking {table_name}: {e}")

for table in ["users", "workflows", "tasks", "audit_logs"]:
    debug_table(table)
