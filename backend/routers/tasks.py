"""
FlowGuard AI - Tasks Router
"""
from fastapi import APIRouter, Depends, HTTPException
import datetime
from database.db import supabase
from database.schemas import TaskOut, TaskUpdate, TaskAutoAssignRequest, TaskAutoAssignResponse
from auth.security import allow_all, allow_manager_plus

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


def get_similar_tasks(task_type):
    return supabase.table("tasks").select("*").eq("task_type", task_type).limit(3).execute().data


@router.get("/", response_model=list[TaskOut])
def list_tasks(user=Depends(allow_all)):
    if user.role in ["head", "manager"]:
        return supabase.table("tasks").select("*").execute().data
    return supabase.table("tasks").select("*").eq("assigned_to", user.id).order("created_at", desc=True).execute().data


@router.put("/{task_id}", response_model=TaskOut)
def update_task(task_id: str, update: TaskUpdate, user=Depends(allow_manager_plus)):
    response = supabase.table("tasks").select("*").eq("id", task_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Task not found")
    task = response.data[0]
    changes = []
    if update.assigned_to and update.assigned_to != task["assigned_to"]:
        changes.append(f"assigned_to -> {update.assigned_to}")
        _increment_workload(update.assigned_to, +1)
        task["assigned_to"] = update.assigned_to
    if update.status and update.status != task["status"]:
        changes.append(f"status -> {update.status}")
        task["status"] = update.status
    if update.priority and update.priority != task["priority"]:
        changes.append(f"priority -> {update.priority}")
        task["priority"] = update.priority
    if changes:
        supabase.table("audit_logs").insert({"task_id": task_id, "agent": "Human-in-the-Loop", "decision": f"User {user.full_name} overrode: {', '.join(changes)}", "confidence": 1.0}).execute()
    supabase.table("tasks").update({"assigned_to": task["assigned_to"], "status": task.get("status"), "priority": task.get("priority")}).eq("id", task_id).execute()
    if update.status == "completed" and task.get("assigned_to"):
        _update_user_performance(task["assigned_to"])
    return task


@router.put("/{task_id}/complete")
def complete_task(task_id: str, user=Depends(allow_all)):
    res = supabase.table("tasks").select("*").eq("id", task_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Task not found")
    task = res.data[0]
    if user.role == "employee" and task.get("assigned_to") != user.id:
        raise HTTPException(status_code=403, detail="You can only complete your own tasks")
    supabase.table("tasks").update({"status": "completed"}).eq("id", task_id).execute()
    if task.get("assigned_to"):
        _update_user_performance(task["assigned_to"])
    return {"message": "Task marked as completed", "task_id": task_id}

def _increment_workload(user_id: str, delta: int):
    """Increment or decrement current_workload for a user."""
    try:
        res = supabase.table("users").select("current_workload").eq("id", user_id).execute()
        if not res.data:
            return
        current = int(res.data[0].get("current_workload") or 0)
        new_workload = max(0, current + delta)
        supabase.table("users").update({"current_workload": new_workload}).eq("id", user_id).execute()
        print(f"[FlowGuard] Workload updated for {user_id}: {current} → {new_workload}")
    except Exception as e:
        print(f"[FlowGuard] Workload update failed: {e}")

def _update_user_performance(user_id: str):
    try:
        res = supabase.table("tasks").select("*").eq("assigned_to", user_id).execute()
        tasks = res.data
        if not tasks:
            return
        completed_tasks = [t for t in tasks if t["status"] == "completed"]
        total_count = len(tasks)
        completed_count = len(completed_tasks)
        if total_count == 0:
            return
        completion_rate = completed_count / total_count
        durations = []
        before_deadline_count = 0
        bonus = 0.0
        for t in completed_tasks:
            created = datetime.datetime.fromisoformat(t["created_at"].replace("Z", "+00:00"))
            updated_raw = t.get("updated_at") or t.get("created_at")
            updated = datetime.datetime.fromisoformat(updated_raw.replace("Z", "+00:00"))
            durations.append((updated - created).total_seconds() / 3600.0)
            if t.get("sla_deadline"):
                sla = datetime.datetime.fromisoformat(t["sla_deadline"].replace("Z", "+00:00"))
                if updated <= sla:
                    before_deadline_count += 1
                    days_early = (sla - updated).total_seconds() / 86400.0
                    bonus += 0.05 if days_early >= 2 else 0.03 if days_early >= 1 else 0.01
        avg_time = sum(durations) / len(durations) if durations else 24.0
        speed_score = max(0.0, min(1.0, 1.0 - (avg_time / 48.0)))
        reliability = before_deadline_count / completed_count if completed_count > 0 else 1.0
        perf_score = min(1.0, (completion_rate * 0.5) + (speed_score * 0.3) + (reliability * 0.2) + bonus)
        supabase.table("users").update({"performance_score": round(perf_score, 2), "avg_completion_time": round(avg_time, 2), "reliability": round(reliability, 2), "current_workload": total_count - completed_count}).eq("id", user_id).execute()
        print(f"[FlowGuard] Performance updated for {user_id}: {perf_score}")
    except Exception as e:
        print(f"[FlowGuard] Performance scoring failed: {e}")


@router.post("/{task_id}/split")
def split_task(task_id: str, user=Depends(allow_all)):
    res = supabase.table("tasks").select("*").eq("id", task_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Task not found")
    task = res.data[0]
    if user.role == "employee" and task.get("assigned_to") != user.id:
        raise HTTPException(status_code=403, detail="You can only split your own tasks")
    dept = task.get("department", "General")
    dept_users = supabase.table("users").select("*").eq("department", dept).eq("availability_status", "active").execute().data
    busy_ids = {t["assigned_to"] for t in supabase.table("tasks").select("assigned_to").eq("department", dept).eq("status", "pending").execute().data if t["assigned_to"]}
    free_users = [u for u in dept_users if u["id"] not in busy_ids and u["id"] != task.get("assigned_to")]
    if not free_users:
        free_users = sorted([u for u in dept_users if u["id"] != task.get("assigned_to")], key=lambda x: x.get("current_workload", 0))
    if not free_users:
        raise HTTPException(status_code=400, detail=f"No other available employees found in {dept} department to split with")
    helper_name = helper.get("name") or helper.get("full_name") or "Unknown"
    split_obj = {
        "title": f"[SPLIT] {task['title']}",
        "description": f"Split from task {task_id}",
        "task_type": task.get("task_type", "general"),
        "department": dept,
        "assigned_to": helper["id"],
        "owner_name": helper_name,
        "status": "pending",
        "priority": task.get("priority", "high"),
        "risk_score": task.get("risk_score", 0.7),
        "sla_deadline": task.get("sla_deadline"),
        "parent_task_id": task_id,
        "workflow_id": task.get("workflow_id"),
        "created_at": datetime.datetime.utcnow().isoformat()
    }
    supabase.table("tasks").insert(split_obj).execute()
    supabase.table("tasks").update({"split_requested": True, "status": "split_pending"}).eq("id", task_id).execute()
    supabase.table("audit_logs").insert({
        "task_id": task_id,
        "agent": "Split-Agent",
        "decision": f"Split. Helper: {helper_name}",
        "confidence": 0.9
    }).execute()
    return {
        "message": "Task split successfully",
        "helper_assigned": helper_name,
        "split_task_title": split_obj["title"]
    }


@router.patch("/{task_id}/approve-split")
def approve_split(task_id: str, user=Depends(allow_all)):
    # Find the parent task
    parent = supabase.table("tasks").select("*").eq("id", task_id).execute()
    if not parent.data:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Find the linked split task (where parent_task_id = task_id)
    child = supabase.table("tasks").select("*").eq("parent_task_id", task_id).execute()
    if not child.data:
        raise HTTPException(status_code=404, detail="No split task found for this parent")
    
    # Update status to split_approved for parent
    supabase.table("tasks").update({"status": "split_approved", "split_requested": False}).eq("id", task_id).execute()
    
    # Update split task status from pending to in_progress
    supabase.table("tasks").update({"status": "in_progress"}).eq("parent_task_id", task_id).execute()
    
    # Log to audit_logs
    supabase.table("audit_logs").insert({
        "task_id": task_id,
        "agent": "Split-Approval-Agent",
        "decision": f"Split approved by employee {user.full_name or user.name}",
        "confidence": 1.0
    }).execute()
    
    return parent.data[0]


@router.get("/{task_id}/split-request")
def get_split_request(task_id: str, user=Depends(allow_all)):
    # Returns the split child task (where parent_task_id = task_id)
    res = supabase.table("tasks").select("*").eq("parent_task_id", task_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Split child task not found")
    return res.data[0]


@router.post("/auto-assign", response_model=TaskAutoAssignResponse)
def assign_task(req: TaskAutoAssignRequest, user=Depends(allow_manager_plus)):
    similar = get_similar_tasks(req.task_type)
    rag = "Similar task handled efficiently before" if similar else ""
    dept = req.department
    assigned_to_id = None
    owner_name = "Unassigned"
    best_score = 0.0
    try:
        dept_users = supabase.table("users").select("*").eq("department", dept).eq("availability_status", "active").execute().data
        if not dept_users:
            dept_users = supabase.table("users").select("*").eq("availability_status", "active").execute().data
        already = {t["assigned_to"] for t in supabase.table("tasks").select("assigned_to").eq("department", dept).eq("status", "pending").execute().data if t["assigned_to"]}
        pool = [u for u in dept_users if u["id"] not in already] or dept_users
        scored = []
        for u in pool:
            ps = u.get("performance_score", 0.5)
            at = u.get("avg_completion_time", 24.0)
            rel = u.get("reliability", 1.0)
            spd = max(0, 1 - (at / 100))
            days_left = 3
            if req.deadline:
                try:
                    dl = req.deadline if not isinstance(req.deadline, str) else datetime.datetime.fromisoformat(req.deadline)
                    days_left = max(0.0, (dl - datetime.datetime.utcnow()).total_seconds() / 86400.0)
                except Exception:
                    pass
            eff = (ps*0.7 + spd*0.2 + rel*0.1) if days_left <= 1 else (ps*0.5 + spd*0.3 + rel*0.2)
            scored.append({"id": u["id"], "name": u.get("full_name") or u.get("name", "Unknown"), "score": round(eff, 2)})
        scored.sort(key=lambda x: x["score"], reverse=True)
        if scored:
            assigned_to_id = scored[0]["id"]
            owner_name = scored[0]["name"]
            best_score = scored[0]["score"]
    except Exception as e:
        print(f"[FlowGuard] Auto-assign error: {e}")
    priority = "critical" if any(k in req.title.lower() for k in ["urgent", "asap", "critical"]) else "high" if any(k in req.title.lower() for k in ["important", "deadline"]) else "medium"
    risk_score = 0.8 if priority == "critical" else 0.6 if priority == "high" else 0.4
    supabase.table("tasks").insert({"title": req.title, "task_type": req.task_type, "department": dept, "assigned_to": assigned_to_id, "owner_name": owner_name, "deadline": req.deadline.isoformat() if req.deadline else None, "status": "pending", "priority": priority, "risk_score": risk_score, "created_at": datetime.datetime.utcnow().isoformat()}).execute()
    try:
        supabase.table("audit_logs").insert({"agent": "Assignment-Agent", "decision": f"Assigned to {owner_name}", "confidence": round(best_score, 2)}).execute()
    except Exception as e:
        print(f"Audit log error: {e}")
    return TaskAutoAssignResponse(assigned_to=owner_name, score=best_score, reason=f"Assigned by performance+dept match. {rag}")