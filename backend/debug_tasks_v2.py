from database.db import supabase
import datetime, uuid

try:
    # 1. Get a valid workflow_id
    res_wf = supabase.table("workflows").select("id").limit(1).execute()
    if not res_wf.data:
        # Create a dummy workflow
        wf_data = {
            "title": "Debug Workflow",
            "raw_input": "debug",
            "created_at": datetime.datetime.utcnow().isoformat()
        }
        res_wf = supabase.table("workflows").insert(wf_data).execute()
    
    wf_id = res_wf.data[0]["id"]
    print(f"Using workflow_id: {wf_id}")

    task_id = str(uuid.uuid4())
    mock_task = {
        "id": task_id,
        "workflow_id": wf_id,
        "title": "Debug Task",
        "assigned_to": "Unassigned",
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
        print("SUCCESS: 'deadline' column exists.")
        print("Keys:", list(res.data[0].keys()))
        supabase.table("tasks").delete().eq("id", task_id).execute()
    except Exception as e:
        print(f"FAILED: 'deadline' column does not exist or error: {e}")
        # Try inserting with 'sla_deadline'
        if "deadline" in mock_task: del mock_task["deadline"]
        mock_task["sla_deadline"] = (datetime.datetime.utcnow() + datetime.timedelta(days=2)).isoformat()
        res = supabase.table("tasks").insert(mock_task).execute()
        print("SUCCESS: 'sla_deadline' column exists.")
        print("Keys:", list(res.data[0].keys()))
        supabase.table("tasks").delete().eq("id", task_id).execute()

except Exception as e:
    print(f"Outer Error: {e}")
