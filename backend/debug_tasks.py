from database.db import supabase
import datetime, uuid

# Mock a task insert to see if 'deadline' or 'sla_deadline' is the correct column
try:
    task_id = str(uuid.uuid4())
    mock_task = {
        "id": task_id,
        "workflow_id": None, # Assuming nullable or handled
        "title": "Debug Task",
        "assigned_to": "Unassigned", # or valid user id
        "owner_name": "Unassigned",
        "status": "pending",
        "priority": "medium",
        "risk_score": 0.5,
        "created_at": datetime.datetime.utcnow().isoformat()
    }
    
    # Try inserting with 'deadline'
    try:
        mock_task["deadline"] = (datetime.datetime.utcnow() + datetime.timedelta(days=2)).isoformat()
        res = supabase.table("tasks").insert(mock_task).execute()
        print("Success inserting with 'deadline'. Keys:", list(res.data[0].keys()))
        # Clean up
        supabase.table("tasks").delete().eq("id", task_id).execute()
    except Exception as e:
        print(f"Failed inserting with 'deadline': {e}")
        # Try inserting with 'sla_deadline'
        del mock_task["deadline"]
        mock_task["sla_deadline"] = (datetime.datetime.utcnow() + datetime.timedelta(days=2)).isoformat()
        res = supabase.table("tasks").insert(mock_task).execute()
        print("Success inserting with 'sla_deadline'. Keys:", list(res.data[0].keys()))
        # Clean up
        supabase.table("tasks").delete().eq("id", task_id).execute()

except Exception as e:
    print(f"Outer Error: {e}")
