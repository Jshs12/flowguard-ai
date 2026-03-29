"""
FlowGuard AI — Tasks Router
"""
import datetime
import uuid
from fastapi import APIRouter, Depends, HTTPException
from database.db import supabase
from auth.security import allow_all, allow_manager_plus




router = APIRouter(prefix="/api/tasks", tags=["Tasks"])




# ══════════════════════════════════════════════════════
# ── UTILS ─────────────────────────────────────────────────────────────
def safe_user_field(user, *keys):
    """Safe extraction — works for Pydantic v1, v2, custom class, or dict."""
    for key in keys:
        if isinstance(user, dict):
            val = user.get(key)
        else:
            val = getattr(user, key, None)
        if val:
            return val
    return None


def update_performance_score(user_id: str, task: dict):
    """Updates user performance metrics after task completion."""
    try:
        # ── Fetch user current stats ───────────────────
        u_res = supabase.table("users").select(
            "performance_score, reliability, current_workload"
        ).eq("id", user_id).execute()

        if not u_res.data:
            return

        u             = u_res.data[0]
        current_score = float(u.get("performance_score") or 0.5)
        current_rel   = float(u.get("reliability") or 0.5)

        # ── Fetch all tasks for completion rate ────────
        all_tasks = supabase.table("tasks").select(
            "status, sla_deadline"
        ).eq("assigned_to", user_id).execute().data or []

        total_assigned  = len(all_tasks)
        total_completed = len([t for t in all_tasks if t["status"] == "completed"])
        completion_rate = total_completed / total_assigned if total_assigned > 0 else 0.5

        # ── Speed Score: days before deadline ─────────
        deadline_str = task.get("sla_deadline") or task.get("deadline")
        days_before  = 0

        if deadline_str:
            try:
                deadline_dt = datetime.datetime.fromisoformat(str(deadline_str)[:19])
                days_before = (deadline_dt - datetime.datetime.utcnow()).days
            except Exception:
                pass

        # More days left when completed = higher reward
        if days_before >= 3:
            speed_score = 1.0
            score_delta = 0.06    # completed very early — big bonus
        elif days_before >= 1:
            speed_score = 0.75
            score_delta = 0.04    # completed with time to spare
        elif days_before == 0:
            speed_score = 0.5
            score_delta = 0.02    # completed exactly on time
        else:
            speed_score = 0.1
            score_delta = -0.03   # completed late — small penalty

        # ── Reliability: % of tasks completed on time ─
        completed_tasks = [t for t in all_tasks if t["status"] == "completed"]
        reliability     = current_rel  # keep existing if no data
        if completed_tasks:
            on_time_count = 0
            for ct in completed_tasks:
                try:
                    dl = datetime.datetime.fromisoformat(str(ct["sla_deadline"])[:19])
                    if dl >= datetime.datetime.utcnow():
                        on_time_count += 1
                except Exception:
                    pass
            reliability = on_time_count / len(completed_tasks)

        # ── Final Efficiency Score Formula ─────────────
        # Efficiency = (CompletionRate * 0.5) + (SpeedScore * 0.3) + (Reliability * 0.2)
        efficiency = (
            (completion_rate * 0.5) +
            (speed_score     * 0.3) +
            (reliability     * 0.2)
        )

        # Blend with existing score — don't hard reset
        new_score = round(min(1.0, max(0.0,
            (current_score * 0.6) + (efficiency * 0.4) + score_delta
        )), 4)

        new_rel = round(min(1.0, max(0.0,
            (current_rel * 0.7) + (reliability * 0.3)
        )), 4)

        # ── Persist updated stats ──────────────────────
        # Bug 2 fix: actually write to users
        supabase.table("users").update({
            "performance_score": new_score,
            "reliability":       new_rel,
            "avg_completion_time": 100 - (speed_score * 100) # placeholder for speed
        }).eq("id", user_id).execute()

        print(f"[FlowGuard] 📈 Performance updated: {user_id} "
              f"score={new_score} (delta={score_delta:+.2f})")

    except Exception as e:
        print(f"[FlowGuard] WARN: update_performance_score failed: {e}")
        import traceback; traceback.print_exc()




# ── GET ALL TASKS (persisted history) ────────────────────────────────
@router.get("/")
def get_tasks(user=Depends(allow_all)):
    query = supabase.table("tasks").select("*")



    if user.role == "employee":
        # Employee only sees their own assigned tasks
        query = query.eq("assigned_to", user.id)
    # manager and head see ALL tasks — no filter



    result = query.order("created_at", desc=True).execute()
    return result.data or []




# ── UPDATE TASK STATUS ────────────────────────────────────────────────
@router.put("/{task_id}")
def update_task(task_id: str, body: dict, user=Depends(allow_all)):
    res = supabase.table("tasks").select("*").eq("id", task_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Task not found")



    task = res.data[0]



    # Employee can only update their own tasks
    if user.role == "employee" and task.get("assigned_to") != user.id:
        raise HTTPException(status_code=403, detail="Not your task")



    allowed_fields = ["status", "priority", "assigned_to", "owner_name", "risk_score"]
    update_data = {k: v for k, v in body.items() if k in allowed_fields}
    update_data["updated_at"] = datetime.datetime.utcnow().isoformat()

    # ✅ NEW: Enforce department-scoped assignment
    if body.get("assigned_to"):
        assigned_to_id = body["assigned_to"]
        task_dept      = task.get("department")
        
        # Fetch assignee department
        try:
            u_res = supabase.table("users").select("department").eq("id", assigned_to_id).single().execute()
            if u_res.data:
                assignee_dept = u_res.data.get("department")
                if assignee_dept and task_dept and assignee_dept.lower() != task_dept.lower():
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot assign {task_dept} task to employee in {assignee_dept} department"
                    )
        except HTTPException: raise
        except Exception as e:
            print(f"[FlowGuard] Dept validation failed: {e}")

    supabase.table("tasks").update(update_data).eq("id", task_id).execute()



    # If completed, decrement workload
    if body.get("status") == "completed" and task.get("assigned_to"):
        try:
            u = supabase.table("users").select("current_workload") \
                .eq("id", task["assigned_to"]).execute()
            if u.data:
                current = u.data[0].get("current_workload", 1) or 1
                supabase.table("users").update({
                    "current_workload": max(0, current - 1)
                }).eq("id", task["assigned_to"]).execute()
        except Exception as e:
            print(f"[FlowGuard] WARN: workload decrement failed: {e}")


        # ✅ NEW (Phase 1 Items 3,4,5): trigger performance score update
        # Uses full scoring formula — completion rate, speed, reliability
        update_performance_score(task["assigned_to"], task)



    return {"message": "Task updated", "task_id": task_id}



# ── COMPLETE TASK ─────────────────────────────────────────────────────
@router.put("/{task_id}/complete")
async def complete_task(task_id: str, user=Depends(allow_all)):
    try:
        user_id   = safe_user_field(user, "id", "user_id")
        user_name = safe_user_field(user, "full_name", "username", "name", "user")

        # Mark task as completed
        result = supabase.table("tasks").update({
            "status": "completed",
            "updated_at": datetime.datetime.utcnow().isoformat()
        }).eq("id", task_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Task not found")

        task = result.data[0]

        # Log completion to 'audit_logs' table
        try:
            supabase.table("audit_logs").insert({
                "task_id":    task_id,
                "workflow_id": task.get("workflow_id"),
                "agent":      "Human-Interface",
                "decision":    "task_completed",
                "reason":      f"Task '{task.get('title', 'Untitled')}' marked complete by {user_name}",
                "confidence":  1.0,
                "created_at":  datetime.datetime.utcnow().isoformat()
            }).execute()
        except Exception as log_err:
            print(f"[FlowGuard] WARN: log insert failed: {log_err}")

        # Update workload
        try:
            u_res = supabase.table("users").select("current_workload").eq("id", user_id).execute()
            if u_res.data:
                curr = u_res.data[0].get("current_workload", 0) or 0
                supabase.table("users").update({"current_workload": max(0, curr - 1)}).eq("id", user_id).execute()
        except Exception:
            pass

        # Update performance score
        update_performance_score(user_id, task)

        return {"message": "Task completed successfully", "task_id": task_id}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[FlowGuard] ERROR in complete_task: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# ── PERFORMANCE DASHBOARD ──────────────────────────────────────────────
@router.get("/performance")
def get_performance(user=Depends(allow_all)):
    uid = safe_user_field(user, "id", "user_id")
    
    # Fetch user core stats
    u_res = supabase.table("users").select("*").eq("id", uid).execute()
    if not u_res.data:
        raise HTTPException(status_code=404, detail="User not found")
    user_data = u_res.data[0]
    
    # Calculate task totals
    tasks_res = supabase.table("tasks").select("status").eq("assigned_to", uid).execute()
    all_tasks = tasks_res.data or []
    
    total      = len(all_tasks)
    completed  = len([t for t in all_tasks if t["status"] == "completed"])
    active     = len([t for t in all_tasks if t["status"] in ["pending", "in_progress"]])
    
    return {
        "score":               int(float(user_data.get("performance_score", 0.5)) * 100),
        "reliability":         int(float(user_data.get("reliability", 0.5)) * 100),
        "avg_speed":           int(float(user_data.get("avg_completion_time", 0.5)) * 100),
        "tasks_completed":     completed,
        "tasks_total":         total,
        "active_tasks":        active,
        "availability_status": user_data.get("availability_status", "active")
    }


# ── AUTO-ASSIGN UNASSIGNED TASK ───────────────────────────────────────
@router.post("/auto-assign")
def auto_assign_task(body: dict, user=Depends(allow_manager_plus)):
    task_id    = body.get("task_id")
    department = body.get("department", "General")



    res = supabase.table("tasks").select("*").eq("id", task_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Task not found")



    # Find best available active employee in dept
    users_res = supabase.table("users").select("*") \
        .eq("department", department) \
        .eq("availability_status", "active") \
        .execute()
    dept_users = users_res.data or []



    if not dept_users:
        raise HTTPException(status_code=404, detail=f"No available employees found in {department} department")



    dept_users.sort(key=lambda u: (
        u.get("current_workload", 0),
        -float(u.get("performance_score", 0.5))
    ))
    best = dept_users[0]



    supabase.table("tasks").update({
        "assigned_to": best["id"],
        "owner_name":  best.get("full_name") or best.get("name", "Assigned"),
        "updated_at":  datetime.datetime.utcnow().isoformat()
    }).eq("id", task_id).execute()



    supabase.table("users").update({
        "current_workload": (best.get("current_workload", 0) or 0) + 1
    }).eq("id", best["id"]).execute()



    return {
        "message":     "Task auto-assigned",
        "assigned_to": best.get("full_name") or best.get("name"),
        "department":  department
    }


# ── SPLIT REQUEST FLOW ────────────────────────────────────────────────
@router.post("/{task_id}/split-request")
def request_split(task_id: str, body: dict, user=Depends(allow_all)):
    uid = safe_user_field(user, "id", "user_id")
    reason = body.get("reason", "Not specified")
    
    # Verify task exists and is assigned to caller
    res = supabase.table("tasks").select("*").eq("id", task_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = res.data[0]
    if user.role == "employee" and task.get("assigned_to") != uid:
        raise HTTPException(status_code=403, detail="Not your task to split")
        
    # Update task with split request
    supabase.table("tasks").update({
        "split_requested": True,
        "updated_at":     datetime.datetime.utcnow().isoformat()
    }).eq("id", task_id).execute()
    
    # Log to audit logs
    supabase.table("audit_logs").insert({
        "workflow_id": task.get("workflow_id"),
        "task_id":     task_id,
        "agent":       "Employee-Interface",
        "decision":    "split_requested",
        "reason":      reason,
        "created_at":  datetime.datetime.utcnow().isoformat()
    }).execute()
    
    return {"message": "Split request submitted"}


@router.get("/split-requests")
def get_split_requests(user=Depends(allow_manager_plus)):
    # Managers see all pending split requests
    res = supabase.table("tasks").select("*") \
        .eq("split_requested", True) \
        .neq("status", "completed") \
        .order("created_at", desc=True).execute()
    return res.data or []


@router.post("/{task_id}/approve-split")
def approve_split(task_id: str, body: dict, user=Depends(allow_manager_plus)):
    subtasks = body.get("subtasks", [])
    if not subtasks:
        raise HTTPException(status_code=400, detail="No subtasks provided")
        
    # Fetch parent task
    res = supabase.table("tasks").select("*").eq("id", task_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Parent task not found")
    parent = res.data[0]
    
    # Create child tasks
    created_count = 0
    for st in subtasks:
        child_id = str(uuid.uuid4())
        new_task = {
            "id":             child_id,
            "workflow_id":    parent.get("workflow_id"),
            "title":          st.get("title", f"Subtask for {parent['title']}"),
            "description":    f"Split from parent task: {parent['title']}",
            "assigned_to":    st.get("assigned_to", parent.get("assigned_to")),
            "owner_name":     "Assigned", # Will be updated by owner name logic if needed
            "department":     parent.get("department"),
            "status":         "pending",
            "priority":       parent.get("priority"),
            "deadline":       st.get("deadline", parent.get("sla_deadline")),
            "sla_deadline":   st.get("deadline", parent.get("sla_deadline")),
            "parent_task_id": task_id,
            "created_at":     datetime.datetime.utcnow().isoformat()
        }
        supabase.table("tasks").insert(new_task).execute()
        created_count += 1
        
        # Increment workload for child assignee
        if new_task["assigned_to"]:
            try:
                u_res = supabase.table("users").select("current_workload").eq("id", new_task["assigned_to"]).execute()
                if u_res.data:
                    curr = u_res.data[0].get("current_workload", 0) or 0
                    supabase.table("users").update({"current_workload": curr + 1}).eq("id", new_task["assigned_to"]).execute()
            except Exception: pass

    # Update parent status
    supabase.table("tasks").update({
        "status":          "split_approved",
        "split_requested": False,
        "updated_at":      datetime.datetime.utcnow().isoformat()
    }).eq("id", task_id).execute()
    
    # Log approval
    supabase.table("audit_logs").insert({
        "workflow_id": parent.get("workflow_id"),
        "task_id":     task_id,
        "agent":       "Manager-Approval",
        "decision":    "split_approved",
        "reason":      f"Split into {created_count} subtasks",
        "created_at":  datetime.datetime.utcnow().isoformat()
    }).execute()
    
    return {"message": "Split approved", "subtask_count": created_count}




# ── GET SINGLE TASK — MUST BE LAST (catches /{task_id}) ──────────────
# ✅ FIX 2: Moved BELOW /split to avoid route conflict (was causing 404)
@router.get("/{task_id}")
def get_task(task_id: str, user=Depends(allow_all)):
    res = supabase.table("tasks").select("*").eq("id", task_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Task not found")
    return res.data[0]