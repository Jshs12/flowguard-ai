"""
FlowGuard AI — Autonomous Scheduler
Handles:
  - Item 9:  Auto-reassign tasks delayed past deadline
  - Item 10: Send reminder if deadline close and task not done
  - Existing: restore_returned_employees (leave auto-restore)
"""
import datetime
from database.db import supabase



# ══════════════════════════════════════════════════════
# ITEM 10 — Remind if deadline close and task not done
# Runs every hour. Flags tasks due within 24h.
# ══════════════════════════════════════════════════════
def send_deadline_reminders():
    try:
        now       = datetime.datetime.utcnow()
        in_24h    = (now + datetime.timedelta(hours=24)).isoformat()

        # Tasks not completed, deadline within 24 hours
        res = supabase.table("tasks") \
            .select("id, title, assigned_to, owner_name, sla_deadline, department") \
            .neq("status", "completed") \
            .neq("status", "cancelled") \
            .lte("sla_deadline", in_24h) \
            .gte("sla_deadline", now.isoformat()) \
            .execute()

        tasks = res.data or []

        if not tasks:
            print("[FlowGuard Scheduler] ✅ No deadline reminders needed.")
            return

        for task in tasks:
            try:
                deadline_dt  = datetime.datetime.fromisoformat(str(task["sla_deadline"])[:19])
                hours_left   = round((deadline_dt - now).total_seconds() / 3600, 1)

                # Log reminder into audit_logs so it shows in UI
                supabase.table("audit_logs").insert({
                    "workflow_id": None,
                    "agent":       "DeadlineWatcher",
                    "decision":    f"⏰ REMINDER: '{task['title']}' due in {hours_left}h",
                    "reason":      f"Task assigned to {task.get('owner_name', 'Unknown')} "
                                   f"in {task.get('department', '?')} dept is approaching deadline.",
                    "confidence":  0.95,
                    "created_at":  now.isoformat()
                }).execute()

                print(f"[FlowGuard Scheduler] ⏰ Reminder logged: "
                      f"'{task['title']}' → {task.get('owner_name')} ({hours_left}h left)")

            except Exception as e:
                print(f"[FlowGuard Scheduler] WARN: reminder log failed for {task.get('id')}: {e}")

    except Exception as e:
        print(f"[FlowGuard Scheduler] WARN: send_deadline_reminders failed: {e}")



# ══════════════════════════════════════════════════════
# ITEM 9 — Auto-reassign tasks delayed past deadline
# Runs every hour. Reassigns to best available employee.
# ══════════════════════════════════════════════════════
def auto_reassign_delayed_tasks():
    try:
        now = datetime.datetime.utcnow()

        # Tasks that are overdue and still not completed
        res = supabase.table("tasks") \
            .select("id, title, assigned_to, owner_name, department, priority, sla_deadline") \
            .neq("status", "completed") \
            .neq("status", "cancelled") \
            .lt("sla_deadline", now.isoformat()) \
            .execute()

        overdue = res.data or []

        if not overdue:
            print("[FlowGuard Scheduler] ✅ No overdue tasks to reassign.")
            return

        for task in overdue:
            try:
                dept       = (task.get("department") or "General").strip().title()
                current_id = task.get("assigned_to")

                # Find best active employee in dept — exclude current assignee
                users_res = supabase.table("users").select("*") \
                    .eq("department", dept) \
                    .eq("availability_status", "active") \
                    .execute()
                candidates = [
                    u for u in (users_res.data or [])
                    if u["id"] != current_id        # don't reassign to same person
                ]

                # Fallback: any active employee in any dept
                if not candidates:
                    fallback = supabase.table("users").select("*") \
                        .eq("availability_status", "active") \
                        .eq("role", "employee") \
                        .execute().data or []
                    candidates = [u for u in fallback if u["id"] != current_id]

                if not candidates:
                    print(f"[FlowGuard Scheduler] ⚠️ No replacement found for '{task['title']}'")
                    continue

                # Pick lowest workload + best performance score
                candidates.sort(key=lambda u: (
                    u.get("current_workload", 0),
                    -float(u.get("performance_score", 0.5) or 0.5)
                ))
                new_assignee = candidates[0]

                # Update task
                supabase.table("tasks").update({
                    "assigned_to": new_assignee["id"],
                    "owner_name":  new_assignee.get("full_name", "Reassigned"),
                    "updated_at":  now.isoformat()
                }).eq("id", task["id"]).execute()

                # Update workload counters
                supabase.table("users").update({
                    "current_workload": max(0, (new_assignee.get("current_workload", 0) or 0) + 1)
                }).eq("id", new_assignee["id"]).execute()

                if current_id:
                    old_user = supabase.table("users").select("current_workload") \
                        .eq("id", current_id).execute().data
                    if old_user:
                        supabase.table("users").update({
                            "current_workload": max(0, (old_user[0].get("current_workload", 1) or 1) - 1)
                        }).eq("id", current_id).execute()

                # Log reassignment in audit trail so it shows in UI
                supabase.table("audit_logs").insert({
                    "workflow_id": None,
                    "agent":       "AutoReassignAgent",
                    "decision":    f"🔁 AUTO-REASSIGNED: '{task['title']}'",
                    "reason":      f"Task was overdue (deadline: {task['sla_deadline'][:10]}). "
                                   f"Reassigned from {task.get('owner_name', '?')} "
                                   f"to {new_assignee.get('full_name', '?')} in {dept}.",
                    "confidence":  0.90,
                    "created_at":  now.isoformat()
                }).execute()

                print(f"[FlowGuard Scheduler] 🔁 Reassigned: '{task['title']}' "
                      f"{task.get('owner_name')} → {new_assignee.get('full_name')}")

            except Exception as e:
                print(f"[FlowGuard Scheduler] WARN: reassign failed for {task.get('id')}: {e}")

    except Exception as e:
        print(f"[FlowGuard Scheduler] WARN: auto_reassign_delayed_tasks failed: {e}")