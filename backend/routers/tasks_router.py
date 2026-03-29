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
# ✅ NEW (Phase 1 Items 3,4,5) — Performance Score Engine
# Efficiency = (CompletionRate * 0.5) + (SpeedScore * 0.3) + (Reliability * 0.2)
# Score delta based on days before deadline (more days = bigger reward)
# ══════════════════════════════════════════════════════
def update_performance_score(user_id: str, task: dict):
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
        supabase.table("users").update({
            "performance_score": new_score,
            "reliability":       new_rel,
        }).eq("id", user_id).execute()


        print(f"[FlowGuard] 📈 Performance updated: {user_id} "
              f"score={new_score} (delta={score_delta:+.2f}, "
              f"days_before_deadline={days_before})")


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
        import datetime

        # Mark task as completed
        result = supabase.table("tasks").update({
            "status": "completed",
        }).eq("id", task_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Task not found")

        task = result.data[0]

        # Log completion
        supabase.table("logs").insert({
            "task_id": task_id,
            "user_id": user["id"],
            "action": "task_completed",
            "message": f"Task '{task.get('title', '')}' marked complete by {user.get('full_name', 'user')}",
            "timestamp": datetime.datetime.utcnow().isoformat()
        }).execute()

        # Update performance score
        update_performance_score(user["id"], task)

        return {"message": "Task completed successfully", "task_id": task_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



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
        # Fallback to any active employee
        dept_users = supabase.table("users").select("*") \
            .eq("availability_status", "active") \
            .eq("role", "employee").execute().data or []



    if not dept_users:
        raise HTTPException(status_code=404, detail="No available employees found")



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


    # ══════════════════════════════════════════════════════
# ✅ NEW (Phase 3 Item 12) — Split Task
# Employee requests split when deadline is very close.
# Finds unoccupied dept employee and creates a sub-task.
# ══════════════════════════════════════════════════════
@router.post("/{task_id}/split")
def split_task(task_id: str, user=Depends(allow_all)):
    res = supabase.table("tasks").select("*").eq("id", task_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Task not found")


    task = res.data[0]


    # Only assigned employee or manager can split
    if user.role == "employee" and task.get("assigned_to") != user.id:
        raise HTTPException(status_code=403, detail="Not your task")


    # ✅ FIX 1: Initialize days_left = 0 BEFORE try block — prevents NameError in audit log
    days_left = 0

    # Check deadline is actually close (≤ 2 days)
    try:
        deadline_dt = datetime.datetime.fromisoformat(str(task["sla_deadline"])[:19])
        days_left   = (deadline_dt - datetime.datetime.utcnow()).days
        if days_left > 2:
            raise HTTPException(
                status_code=400,
                detail=f"Task deadline is {days_left} days away — split only allowed within 2 days"
            )
    except HTTPException:
        raise
    except Exception:
        pass  # if deadline parse fails, allow split


    dept       = (task.get("department") or "General").strip().title()
    current_id = task.get("assigned_to")


    # Find unoccupied (lowest workload) active employee in dept — not current assignee
    candidates_res = supabase.table("users").select("*") \
        .eq("department", dept) \
        .eq("availability_status", "active") \
        .execute()


    candidates = [
        u for u in (candidates_res.data or [])
        if u["id"] != current_id and u.get("current_workload", 0) == 0
    ]


    # Fallback: any active employee with lowest workload in dept
    if not candidates:
        candidates = [
            u for u in (candidates_res.data or [])
            if u["id"] != current_id
        ]


    # Final fallback: any active employee in any dept
    if not candidates:
        all_active = supabase.table("users").select("*") \
            .eq("availability_status", "active") \
            .eq("role", "employee") \
            .execute().data or []
        candidates = [u for u in all_active if u["id"] != current_id]


    if not candidates:
        raise HTTPException(status_code=404, detail="No available employee to help with split")


    candidates.sort(key=lambda u: (
        u.get("current_workload", 0),
        -float(u.get("performance_score", 0.5) or 0.5)
    ))
    helper = candidates[0]


    now        = datetime.datetime.utcnow()
    split_task = {
        "id":              str(uuid.uuid4()),
        "workflow_id":     task.get("workflow_id"),
        "title":           f"[SPLIT] {task['title']}",
        "description":     f"Split from original task due to deadline pressure. "
                           f"Help complete: {task.get('description', '')}",
        "task_type":       task.get("task_type", "general"),
        "assigned_to":     helper["id"],
        "owner_name":      helper.get("full_name", "Helper"),
        "department":      dept,
        "status":          "pending",
        "priority":        "critical",          # split tasks are always critical
        "complexity":      task.get("complexity", "medium"),
        "risk_score":      task.get("risk_score", 0.8),
        "is_delayed_risk": True,
        "sla_deadline":    task["sla_deadline"], # same deadline as parent
        "deadline":        task["sla_deadline"],
        "parent_task_id":  task_id,             # linked to original
        "created_by":      user.id,
        "created_at":      now.isoformat()
    }


    supabase.table("tasks").insert(split_task).execute()


    # Update helper workload
    supabase.table("users").update({
        "current_workload": (helper.get("current_workload", 0) or 0) + 1
    }).eq("id", helper["id"]).execute()


    # Log in audit trail
    supabase.table("audit_logs").insert({
        "workflow_id": task.get("workflow_id"),
        "agent":       "TaskSplitAgent",
        "decision":    f"✂️ TASK SPLIT: '{task['title']}'",
        "reason":      f"Deadline in {days_left}d. "   # ✅ FIX 1: now always defined
                       f"Original: {task.get('owner_name')} | "
                       f"Helper joined: {helper.get('full_name')} ({dept})",
        "confidence":  0.95,
        "created_at":  now.isoformat()
    }).execute()


    print(f"[FlowGuard] ✂️ Task split: '{task['title']}' → helper: {helper.get('full_name')}")


    return {
        "message":      "Task split successfully",
        "split_task_id": split_task["id"],
        "helper":        helper.get("full_name"),
        "department":    dept
    }




# ── GET SINGLE TASK — MUST BE LAST (catches /{task_id}) ──────────────
# ✅ FIX 2: Moved BELOW /split to avoid route conflict (was causing 404)
@router.get("/{task_id}")
def get_task(task_id: str, user=Depends(allow_all)):
    res = supabase.table("tasks").select("*").eq("id", task_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Task not found")
    return res.data[0]