"""
FlowGuard AI - Workflow Router
"""
import datetime
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from database.db import supabase
from database.schemas import WorkflowCreate, WorkflowOut, SimulationRequest, SimulationResult
from auth.security import get_current_user, allow_all, allow_manager_plus
from agents.graph import run_pipeline


router = APIRouter(prefix="/api/workflows", tags=["Workflows"])


# ── Smart deadline calculator ─────────────────────────────────────────
def _calculate_deadline(priority: str, complexity: str, deadline_days: int = None) -> str:
    if deadline_days and int(deadline_days) > 0:
        return (datetime.datetime.utcnow() + datetime.timedelta(days=int(deadline_days))).isoformat()

    base_days = {
        "critical": 1,
        "high":     3,
        "medium":   7,
        "low":      14,
    }.get((priority or "medium").lower(), 7)

    complexity_offset = {
        "high":   -1,
        "medium":  0,
        "low":     2,
    }.get((complexity or "medium").lower(), 0)

    total_days = max(1, base_days + complexity_offset)
    return (datetime.datetime.utcnow() + datetime.timedelta(days=total_days)).isoformat()


# ── Risk calculator ───────────────────────────────────────────────────
def compute_risk(priority: str, due_date: str = None) -> float:
    score = 0.0
    p = (priority or "medium").lower()
    if p == "critical": score += 0.6
    elif p == "high":   score += 0.4
    elif p == "medium": score += 0.2
    else:               score += 0.05

    if due_date:
        try:
            # ✅ FIX: use UTC date to match UTC deadlines
            days_left = (datetime.date.fromisoformat(str(due_date)[:10]) - datetime.datetime.utcnow().date()).days
            if days_left <= 1:   score += 0.4
            elif days_left <= 3: score += 0.25
            elif days_left <= 7: score += 0.10
        except:
            pass

    return round(min(score, 1.0), 2)


# ── Auto-assign best user with smart logic ────────────────────────────
def _resolve_assignee(
    department: str,
    workload_counter: dict,
    priority: str = "medium",
    dept_tracker: dict = None,
) -> tuple:

    if dept_tracker is None:
        dept_tracker = {}

    dept_normalized = (department or "General").strip().title()

    dept_role_map = {
        "Management":  ["head", "manager"],
        "Engineering": ["employee"],
        "Marketing":   ["employee"],
        "Hr":          ["employee"],
        "Finance":     ["employee"],
        "Procurement": ["employee"],
        "General":     ["employee"],
    }
    dept_alias_map = {
    "General": "Engineering",
    "It": "Engineering", 
    "Tech": "Engineering",
    "Human Resources": "HR",
    "Hr": "HR",
    "Procurement": "Procurement",
    "Finance": "Finance",
    "Marketing": "Marketing",
    "Sales": "Marketing",
    "Design": "Design",
    "Management": "Management",
    }
    dept_normalized = dept_alias_map.get(dept_normalized, dept_normalized)

    try:
        res = supabase.table("users").select("*") \
            .eq("department", dept_normalized) \
            .eq("availability_status", "active") \
            .execute()
        dept_users = res.data or []

        if not dept_users:
            print(f"[FlowGuard] [ASSIGN] ❌ No active employees found in department '{dept_normalized}'")
            return None, "Unassigned"

        if not dept_users:
            return None, "Unassigned"

        already_assigned = dept_tracker.get(dept_normalized, [])
        available = [u for u in dept_users if u["id"] not in already_assigned]

        if not available:
            print(f"[FlowGuard] [ROUND-ROBIN] All in '{dept_normalized}' assigned once — starting new round")
            dept_tracker[dept_normalized] = []
            already_assigned = []
            available = dept_users

        def effective_load(u):
            return (u.get("current_workload", 0) or 0) + workload_counter.get(u["id"], 0)

        priority_lower = (priority or "medium").lower()
        if priority_lower == "critical":
            available.sort(key=lambda u: (
                -float(u.get("performance_score", 0.5) or 0.5),
                effective_load(u)
            ))
            print(f"[FlowGuard] [ASSIGN] ⚡ CRITICAL task → assigning to highest performer in '{dept_normalized}'")
        else:
            available.sort(key=lambda u: (
                effective_load(u),
                -float(u.get("performance_score", 0.5) or 0.5)
            ))

        best = available[0]
        dept_tracker[dept_normalized] = already_assigned + [best["id"]]

        print(f"[FlowGuard] [ASSIGN] ✅ '{dept_normalized}' [{priority_lower}] → {best.get('full_name')} "
              f"(load: {effective_load(best)}, score: {best.get('performance_score')})")
        return best["id"], best.get("full_name") or best.get("name") or "Unassigned"

    except Exception as e:
        print(f"[FlowGuard] Assignee lookup failed: {e}")
    return None, "Unassigned"


# ── Build a clean task object ─────────────────────────────────────────
def _build_task_obj(
    t: dict,
    workflow_id: str,
    user_id: str = None,
    workload_counter: dict = None,
    dept_tracker: dict = None,
) -> dict:
    if workload_counter is None:
        workload_counter = {}
    if dept_tracker is None:
        dept_tracker = {}

    assigned_id = t.get("assigned_to")
    owner_name  = t.get("owner_name", "Unassigned")

    # ── FIXED: preserve original task department — never overwrite ────
    department  = (t.get("department") or "General").strip().title()
    priority    = (t.get("priority") or "medium").lower()
    complexity  = (t.get("complexity") or "medium").lower()

    if not assigned_id or assigned_id == "Unassigned":
        assigned_id, owner_name = _resolve_assignee(
            department, workload_counter, priority, dept_tracker
        )

    if not assigned_id:
        assigned_id = None

    parent_id = t.get("parent_task_id")
    if not parent_id or parent_id == "Unassigned":
        parent_id = None

    raw_sla      = t.get("sla_deadline") or t.get("deadline")
    raw_days     = t.get("deadline_days") or t.get("deadline")
    deadline_int = int(raw_days) if isinstance(raw_days, (int, float)) and not isinstance(raw_days, bool) else None
    deadline     = raw_sla if raw_sla and isinstance(raw_sla, str) and "T" in raw_sla \
                   else _calculate_deadline(priority, complexity, deadline_int)

    if assigned_id:
        workload_counter[assigned_id] = workload_counter.get(assigned_id, 0) + 1
        try:
            u_res = supabase.table("users").select("current_workload") \
                .eq("id", assigned_id).execute()
            if u_res.data:
                current = u_res.data[0].get("current_workload", 0) or 0
                supabase.table("users").update({"current_workload": current + 1}) \
                    .eq("id", assigned_id).execute()
                print(f"[FlowGuard] [WORKLOAD] {owner_name} → {current + 1} tasks")
        except Exception as e:
            print(f"[FlowGuard] WARN: Failed to update workload: {e}")

    risk = compute_risk(priority, deadline)

    return {
        "id":              t.get("id") or str(uuid.uuid4()),
        "workflow_id":     workflow_id,
        "title":           t.get("title", "Untitled Task"),
        "description":     t.get("description", ""),
        # ── FIXED: task_type uses type/task_type from agents, never hardcodes "general" ──
        "task_type":       str(t.get("task_type") or t.get("type") or department or "general").lower(),
        "assigned_to":     assigned_id,
        "owner_name":      owner_name,
        # ── FIXED: department stays as original task department ────────
        "department":      department,
        "status":          t.get("status", "pending"),
        "priority":        priority,
        "complexity":      complexity,
        "risk_score":      risk,
        "is_delayed_risk": risk >= 0.6,
        "sla_deadline":    deadline,
        "deadline":        deadline,
        "parent_task_id":  parent_id,
        "created_by":      user_id,
        "created_at":      datetime.datetime.utcnow().isoformat()
    }


# ── Process Meeting Transcript ────────────────────────────────────────
@router.post("/process", response_model=WorkflowOut)
def process_meeting(req: WorkflowCreate, user=Depends(allow_manager_plus)):
    try:
        print(f"[FlowGuard] Processing meeting for user: {user.email}")
        result = run_pipeline(req.raw_input)
        tasks  = result.get("tasks") or result.get("action_items") or []
        logs   = result.get("logs") or []

        print(f"🔍 PIPELINE RESULT KEYS: {list(result.keys())}")
        print(f"🔍 TASKS FROM PIPELINE: {len(tasks)}")

        if not tasks:
            print("[FlowGuard] [WARN] No tasks from pipeline. Using fallback.")
            tasks = [{
                "id":              str(uuid.uuid4()),
                "title":           "General task from meeting",
                "description":     "Fallback task — pipeline returned no tasks",
                "task_type":       "general",
                "department":      "General",
                "owner_name":      "Unassigned",
                "assigned_to":     None,
                "priority":        "medium",
                "complexity":      "medium",
                "risk_score":      0.2,
                "is_delayed_risk": False,
                "status":          "pending",
                "sla_deadline":    _calculate_deadline("medium", "medium"),
                "created_at":      datetime.datetime.utcnow().isoformat()
            }]

        wf_data = {
            "title":      req.title or "Untitled Workflow",
            "raw_input":  req.raw_input,
            "transcript": req.raw_input,
            "status":     "completed",
            "created_by": user.id,
            "created_at": datetime.datetime.utcnow().isoformat()
        }
        wf_response = supabase.table("workflows").insert(wf_data).execute()
        if not wf_response.data:
            raise HTTPException(status_code=500, detail="Workflow insert failed")

        workflow    = wf_response.data[0]
        workflow_id = workflow["id"]
        print(f"[FlowGuard] ✅ Workflow created: {workflow_id}")

        workload_counter = {}
        dept_tracker     = {}

        tasks_to_insert = []
        for t in tasks:
            task_obj = _build_task_obj(
                t, workflow_id, user.id, workload_counter, dept_tracker
            )
            print(f"➡️  '{task_obj['title']}' → {task_obj['owner_name']} "
                  f"| task_dept: {task_obj['department']} "
                  f"| task_type: {task_obj['task_type']} "
                  f"| priority: {task_obj['priority']} "
                  f"| risk: {task_obj['risk_score']}")
            try:
                supabase.table("tasks").insert(task_obj).execute()
                tasks_to_insert.append(task_obj)
            except Exception as e:
                print(f"[FlowGuard] [ERROR] Task insert failed: {e}")
                print(f"[FlowGuard] [ERROR] Task data: {task_obj}")

        print(f"[FlowGuard] ✅ Persisted {len(tasks_to_insert)}/{len(tasks)} tasks.")
        print(f"[FlowGuard] [WORKLOAD BATCH] {workload_counter}")
        print(f"[FlowGuard] [ROUND-ROBIN]   {dept_tracker}")

        logs_to_insert = []
        for log in logs:
            logs_to_insert.append({
                "id":          log.get("id") or str(uuid.uuid4()),
                "workflow_id": workflow_id,
                "agent":       log.get("agent_name", "Unknown Agent"),
                "decision":    log.get("action", ""),
                "confidence":  float(log.get("confidence") or 0.0),
                "created_at":  datetime.datetime.utcnow().isoformat()
            })

        if logs_to_insert:
            try:
                supabase.table("audit_logs").insert(logs_to_insert).execute()
                print(f"[FlowGuard] ✅ Inserted {len(logs_to_insert)} audit logs.")
            except Exception as le:
                print(f"[FlowGuard] [ERROR] Log insert failed: {le}")

        workflow["tasks"]  = tasks_to_insert
        workflow["logs"]   = logs_to_insert
        workflow["status"] = "success"
        return workflow

    except Exception as e:
        import traceback
        err_msg = f"[FlowGuard] CRITICAL ERROR: {e}\n{traceback.format_exc()}"
        print(err_msg)
        with open("error_dump.txt", "a") as f:
            f.write(f"\n--- {datetime.datetime.utcnow()} ---\n{err_msg}\n")
        raise HTTPException(status_code=500, detail=str(e))


# ── Process Media Upload ──────────────────────────────────────────────
@router.post("/process-media")
async def process_media(
    file: UploadFile = File(...),
    title: str = Form("Media Workflow"),
    user=Depends(allow_manager_plus),
):
    content = await file.read()
    mock_transcript = (
        "Deploy new marketing campaign by end of quarter. Deadline: 5 days. Priority: high.\n"
        "Prepare budget allocation for Q3. Deadline: 3 days. Priority: high.\n"
        "Finalize vendor list for procurement. Deadline: 10 days. Priority: low.\n"
        "Schedule engineering review meeting. Deadline: 7 days. Priority: medium.\n"
        "Review design mockups for new product launch. Deadline: 4 days. Priority: high."
    )

    result = run_pipeline(mock_transcript)
    tasks  = result.get("tasks") or result.get("action_items") or []

    if not tasks:
        tasks = [{
            "id":              str(uuid.uuid4()),
            "title":           f"Process Media: {file.filename}",
            "description":     "Auto-generated fallback task for media upload.",
            "task_type":       "media-processing",
            "department":      "General",
            "owner_name":      "Unassigned",
            "assigned_to":     None,
            "priority":        "medium",
            "complexity":      "medium",
            "risk_score":      0.2,
            "is_delayed_risk": False,
            "status":          "pending",
            "sla_deadline":    _calculate_deadline("medium", "medium"),
            "created_at":      datetime.datetime.utcnow().isoformat()
        }]

    wf_data = {
        "title":      title,
        "raw_input":  f"[Media Upload: {file.filename}]",
        "transcript": mock_transcript,
        "status":     "completed",
        "created_by": user.id,
        "created_at": datetime.datetime.utcnow().isoformat()
    }
    workflow    = supabase.table("workflows").insert(wf_data).execute().data[0]
    workflow_id = workflow["id"]

    supabase.table("audit_logs").insert({
        "workflow_id": workflow_id,
        "agent":       "AWS Transcribe (Mock)",
        "decision":    f"Transcribed '{file.filename}' ({len(content)} bytes)",
        "confidence":  0.95,
        "created_at":  datetime.datetime.utcnow().isoformat()
    }).execute()

    workload_counter = {}
    dept_tracker     = {}
    tasks_to_insert  = []
    for t in tasks:
        task_obj = _build_task_obj(
            t, workflow_id, user.id, workload_counter, dept_tracker
        )
        try:
            supabase.table("tasks").insert(task_obj).execute()
            tasks_to_insert.append(task_obj)
        except Exception as te:
            print(f"[FlowGuard] [ERROR] Media task insert failed: {te}")

    logs_to_insert = []
    for log in result.get("logs", []):
        logs_to_insert.append({
            "id":          log.get("id") or str(uuid.uuid4()),
            "workflow_id": workflow_id,
            "agent":       log.get("agent_name", "Unknown"),
            "decision":    log.get("action", ""),
            "confidence":  float(log.get("confidence") or 0.0),
            "created_at":  datetime.datetime.utcnow().isoformat()
        })

    if logs_to_insert:
        try:
            supabase.table("audit_logs").insert(logs_to_insert).execute()
        except Exception as le:
            print(f"[FlowGuard] [ERROR] Media log insert failed: {le}")

    return {
        "id":         workflow["id"],
        "title":      workflow["title"],
        "status":     "success",
        "transcript": mock_transcript,
        "created_at": workflow["created_at"],
        "tasks":      tasks_to_insert,
        "logs":       logs_to_insert
    }


# ── List All Workflows ────────────────────────────────────────────────
@router.get("/", response_model=list[WorkflowOut])
def list_workflows(user=Depends(allow_all)):
    query = supabase.table("workflows").select("*, tasks(*), logs:audit_logs(*)")
    if user.role not in ["head", "manager"]:
        query = query.eq("created_by", user.id)
    return query.order("created_at", desc=True).execute().data


# ── Get Single Workflow ───────────────────────────────────────────────
@router.get("/{workflow_id}", response_model=WorkflowOut)
def get_workflow(workflow_id: str, user=Depends(allow_all)):
    response = supabase.table("workflows").select("*, tasks(*), logs:audit_logs(*)") \
        .eq("id", workflow_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return response.data[0]


# ── What-If Simulation ────────────────────────────────────────────────
@router.post("/simulate", response_model=SimulationResult)
def simulate_what_if(req: SimulationRequest, user=Depends(allow_manager_plus)):
    response = supabase.table("tasks").select("*").eq("id", req.task_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Task not found")

    task           = response.data[0]
    original_risk  = task.get("risk_score", 0.5)
    simulated_risk = min(1.0, original_risk + req.delay_days * 0.15)
    sla_breach     = simulated_risk > 0.8
    impact_pct     = round((simulated_risk - original_risk) * 100, 1)
    suggestion     = (
        "Add parallel resource and escalate immediately"
        if sla_breach
        else "Monitor closely and consider reassignment"
    )

    return SimulationResult(
        task_title=task["title"],
        original_risk=round(original_risk, 2),
        simulated_risk=round(simulated_risk, 2),
        sla_breach=sla_breach,
        impact_summary=f"Risk increases by {impact_pct}% with {req.delay_days}-day delay",
        suggestion=suggestion,
    )


# ══════════════════════════════════════════════════════
# Future Prediction endpoint
# ══════════════════════════════════════════════════════
@router.get("/predict/{task_id}")
def predict_task_completion(task_id: str, user=Depends(allow_manager_plus)):
    task_res = supabase.table("tasks").select("*").eq("id", task_id).execute()
    if not task_res.data:
        raise HTTPException(status_code=404, detail="Task not found")

    task        = task_res.data[0]
    assigned_id = task.get("assigned_to")

    if not assigned_id:
        return {
            "task_id":    task_id,
            "prediction": "UNKNOWN",
            "reason":     "Task is unassigned — cannot predict",
            "risk":       "HIGH",
            "action":     "Assign task immediately"
        }

    user_res = supabase.table("users").select(
        "full_name, avg_completion_time, performance_score, reliability, current_workload"
    ).eq("id", assigned_id).execute()

    if not user_res.data:
        raise HTTPException(status_code=404, detail="Assigned user not found")

    assignee         = user_res.data[0]
    avg_time_hours   = float(assignee.get("avg_completion_time") or 24)

    remaining_hours  = 999
    try:
        deadline_dt     = datetime.datetime.fromisoformat(str(task["sla_deadline"])[:19])
        remaining_hours = max(0, (deadline_dt - datetime.datetime.utcnow()).total_seconds() / 3600)
    except Exception:
        pass

    if remaining_hours <= 0:
        prediction = "MISSED"
        risk       = "CRITICAL"
        action     = "Reassign immediately or escalate to manager"
    elif avg_time_hours > remaining_hours:
        prediction = "WILL_MISS"
        risk       = "HIGH"
        action     = "Consider splitting task or reassigning to faster employee"
    elif avg_time_hours > remaining_hours * 0.75:
        prediction = "AT_RISK"
        risk       = "MEDIUM"
        action     = "Monitor closely — send reminder to employee"
    else:
        prediction = "ON_TRACK"
        risk       = "LOW"
        action     = "No action needed"

    if risk in ("HIGH", "CRITICAL"):
        supabase.table("audit_logs").insert({
            "workflow_id": task.get("workflow_id"),
            "agent":       "PredictionAgent",
            "decision":    f"🔮 PREDICTION [{risk}]: '{task['title']}' → {prediction}",
            "reason":      f"Avg completion time: {avg_time_hours:.1f}h, "
                           f"Remaining: {remaining_hours:.1f}h. "
                           f"Assigned to: {assignee.get('full_name')}. "
                           f"Action: {action}",
            "confidence":  float(assignee.get("performance_score") or 0.5),
            "created_at":  datetime.datetime.utcnow().isoformat()
        }).execute()

    return {
        "task_id":         task_id,
        "task_title":      task["title"],
        "assignee":        assignee.get("full_name"),
        "avg_time_hours":  round(avg_time_hours, 1),
        "remaining_hours": round(remaining_hours, 1),
        "prediction":      prediction,
        "risk":            risk,
        "action":          action
    }


# ══════════════════════════════════════════════════════
# Auto-reassign tasks when employee goes on leave
# Call this whenever a leave request is APPROVED
# ══════════════════════════════════════════════════════
@router.post("/reassign-on-leave/{user_id}")
def reassign_on_leave(user_id: str, user=Depends(allow_manager_plus)):
    """
    When an employee goes on leave:
    1. Mark their availability_status = 'leave'
    2. Find all their pending/in_progress tasks
    3. Reassign each to the next best active employee in same department
    4. Log every reassignment in audit_logs
    """
    # Fetch the employee going on leave
    emp_res = supabase.table("users").select("*").eq("id", user_id).execute()
    if not emp_res.data:
        raise HTTPException(status_code=404, detail="Employee not found")

    employee = emp_res.data[0]
    emp_name = employee.get("full_name") or employee.get("name") or "Unknown"
    emp_dept = employee.get("department", "General")

    print(f"[FlowGuard] [LEAVE] Processing leave for {emp_name} ({emp_dept})")

    # Mark employee as on leave
    supabase.table("users").update({"availability_status": "leave"}) \
        .eq("id", user_id).execute()

    # Find all pending/in_progress tasks assigned to this employee
    tasks_res = supabase.table("tasks").select("*") \
        .eq("assigned_to", user_id) \
        .in_("status", ["pending", "in_progress"]) \
        .execute()

    pending_tasks = tasks_res.data or []
    print(f"[FlowGuard] [LEAVE] Found {len(pending_tasks)} tasks to reassign")

    if not pending_tasks:
        return {
            "message": f"{emp_name} marked on leave. No pending tasks to reassign.",
            "reassigned": 0,
            "employee": emp_name
        }

    # Find active employees in same department (excluding the one on leave)
    replacement_res = supabase.table("users").select("*") \
        .eq("department", emp_dept) \
        .eq("availability_status", "active") \
        .eq("role", "employee") \
        .neq("id", user_id) \
        .execute()

    replacements = replacement_res.data or []

    # Fallback: any active employee if no one in same dept
    if not replacements:
        print(f"[FlowGuard] [LEAVE] No replacements in {emp_dept}, using any active employee")
        replacement_res = supabase.table("users").select("*") \
            .eq("availability_status", "active") \
            .eq("role", "employee") \
            .neq("id", user_id) \
            .execute()
        replacements = replacement_res.data or []

    if not replacements:
        return {
            "message": f"{emp_name} marked on leave but NO active employees found to reassign tasks.",
            "reassigned": 0,
            "employee": emp_name,
            "warning": "Tasks left unassigned — no active employees available"
        }

    reassigned_count = 0
    workload_counter = {}

    for task in pending_tasks:
        # Score replacements by efficiency
        scored = []
        for u in replacements:
            perf = float(u.get("performance_score") or 0.5)
            avg_time = float(u.get("avg_completion_time") or 24)
            speed = max(0.0, min(1.0, 1.0 - (avg_time / 48.0)))
            rel = float(u.get("reliability") or 1.0)
            workload = int(u.get("current_workload") or 0) + workload_counter.get(u["id"], 0)
            efficiency = (perf * 0.5) + (speed * 0.3) + (rel * 0.2)
            scored.append({"user": u, "efficiency": efficiency, "workload": workload})

        # Pick lowest workload, tiebreak by efficiency
        scored.sort(key=lambda x: (x["workload"], -x["efficiency"]))
        best = scored[0]["user"]
        new_owner = best.get("full_name") or best.get("name") or "Unknown"

        # Update task assignment
        supabase.table("tasks").update({
            "assigned_to": best["id"],
            "owner_name":  new_owner,
            "status":      "reassigned"
        }).eq("id", task["id"]).execute()

        # Update workload counter
        workload_counter[best["id"]] = workload_counter.get(best["id"], 0) + 1
        try:
            current_wl = best.get("current_workload") or 0
            supabase.table("users").update({"current_workload": current_wl + 1}) \
                .eq("id", best["id"]).execute()
        except Exception as e:
            print(f"[FlowGuard] [LEAVE] Workload update failed: {e}")

        # Reduce workload of employee going on leave
        try:
            current_wl = employee.get("current_workload") or 0
            supabase.table("users").update({"current_workload": max(0, current_wl - 1)}) \
                .eq("id", user_id).execute()
        except Exception:
            pass

        # Log reassignment in audit trail
        supabase.table("audit_logs").insert({
            "workflow_id": task.get("workflow_id"),
            "agent":       "LeaveReassignmentAgent",
            "decision":    f"🔄 AUTO-REASSIGNED: '{task['title']}' from {emp_name} → {new_owner}",
            "confidence":  1.0,
            "created_at":  datetime.datetime.utcnow().isoformat()
        }).execute()

        print(f"[FlowGuard] [LEAVE] ✅ '{task['title']}' → {new_owner}")
        reassigned_count += 1

    return {
        "message":    f"{emp_name} marked on leave. {reassigned_count} tasks auto-reassigned.",
        "reassigned": reassigned_count,
        "employee":   emp_name,
        "department": emp_dept
    }


# ══════════════════════════════════════════════════════
# Get employees with leave status (for manager dashboard)
# Shows who is on leave so manager can see it clearly
# ══════════════════════════════════════════════════════
@router.get("/team/status")
def get_team_status(user=Depends(allow_manager_plus)):
    """Returns all employees with their availability status and task count."""
    res = supabase.table("users").select("*") \
        .eq("role", "employee") \
        .execute()

    employees = res.data or []
    result = []

    for emp in employees:
        # Count pending tasks
        task_res = supabase.table("tasks").select("id") \
            .eq("assigned_to", emp["id"]) \
            .in_("status", ["pending", "in_progress"]) \
            .execute()

        result.append({
            "id":                emp["id"],
            "name":              emp.get("full_name") or emp.get("name"),
            "department":        emp.get("department"),
            "availability":      emp.get("availability_status", "active"),
            "on_leave":          emp.get("availability_status") == "leave",
            "performance_score": emp.get("performance_score"),
            "pending_tasks":     len(task_res.data or []),
            "current_workload":  emp.get("current_workload", 0)
        })

    return result