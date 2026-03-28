"""
FlowGuard AI - Leave Router
Fully autonomous leave management with auto-restore scheduler.
"""
import datetime
from fastapi import APIRouter, Depends, HTTPException
from database.db import supabase
from auth.security import allow_all, allow_manager_plus


router = APIRouter(prefix="/api/leave", tags=["Leave"])


def restore_returned_employees():
    """Auto-called by APScheduler every hour."""
    try:
        today = datetime.datetime.utcnow().date().isoformat()
        expired = supabase.table("leave_requests") \
            .select("user_id, id, end_date") \
            .eq("status", "approved") \
            .lte("end_date", today) \
            .execute()
        if not expired.data:
            return
        for row in expired.data:
            uid = row["user_id"]
            overlap = supabase.table("leave_requests") \
                .select("id") \
                .eq("user_id", uid) \
                .eq("status", "approved") \
                .gte("end_date", today) \
                .execute()
            if not overlap.data:
                supabase.table("users").update({
                    "availability_status": "active"
                }).eq("id", uid).execute()
                supabase.table("leave_requests").update({
                    "status": "completed"
                }).eq("id", row["id"]).execute()
                print(f"[FlowGuard] Employee {uid} auto-restored to ACTIVE (leave ended {row['end_date']})")
    except Exception as e:
        print(f"[FlowGuard] WARN: restore_returned_employees failed: {e}")


@router.post("/apply")
def apply_leave(body: dict, user=Depends(allow_all)):
    start_date = body.get("start_date")
    end_date   = body.get("end_date")
    reason     = body.get("reason", "")
    if not start_date or not end_date:
        raise HTTPException(status_code=400, detail="start_date and end_date are required")
    existing = supabase.table("leave_requests") \
        .select("id") \
        .eq("user_id", user.id) \
        .eq("status", "pending") \
        .execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="You already have a pending leave request")
    leave_data = {
        "user_id":    user.id,
        "start_date": start_date,
        "end_date":   end_date,
        "reason":     reason,
        "status":     "pending",
        "created_at": datetime.datetime.utcnow().isoformat()
    }
    response = supabase.table("leave_requests").insert(leave_data).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to submit leave request")
    try:
        supabase.table("users").update({
            "availability_status": "on_leave"
        }).eq("id", user.id).execute()
        print(f"[FlowGuard] {user.email} on_leave (leave applied, pending approval)")
    except Exception as e:
        print(f"[FlowGuard] WARN: Could not update availability on apply: {e}")
    print(f"[FlowGuard] Leave request submitted by {user.email} ({start_date} to {end_date})")
    return {
        "message":  "Leave request submitted successfully. Awaiting approval.",
        "leave_id": response.data[0]["id"],
        "status":   "pending"
    }


@router.get("/my")
def my_leaves(user=Depends(allow_all)):
    response = supabase.table("leave_requests") \
        .select("*") \
        .eq("user_id", user.id) \
        .order("created_at", desc=True) \
        .execute()
    return response.data


@router.get("/all")
def all_leaves(user=Depends(allow_manager_plus)):
    # ✅ FIX: Removed FK join (users!leaverequestsuseridfkey) — FK missing in Supabase
    # Replaced with manual two-step fetch + merge to avoid PGRST200 error
    response = supabase.table("leave_requests") \
        .select("*") \
        .order("created_at", desc=True) \
        .execute()
    leaves = response.data or []
    if leaves:
        user_ids = list({l["user_id"] for l in leaves if l.get("user_id")})
        users_res = supabase.table("users") \
            .select("id, full_name, department, email, availability_status") \
            .in_("id", user_ids) \
            .execute()
        user_map = {u["id"]: u for u in (users_res.data or [])}
        for leave in leaves:
            leave["users"] = user_map.get(leave.get("user_id"), {})
    return leaves


@router.get("/pending")
def pending_leaves(user=Depends(allow_manager_plus)):
    """Only pending - for notification badge count."""
    # ✅ FIX: Removed FK join (users!leaverequestsuseridfkey) — FK missing in Supabase
    # Replaced with manual two-step fetch + merge to avoid PGRST200 error
    response = supabase.table("leave_requests") \
        .select("*") \
        .eq("status", "pending") \
        .order("created_at", desc=True) \
        .execute()
    leaves = response.data or []
    if leaves:
        user_ids = list({l["user_id"] for l in leaves if l.get("user_id")})
        users_res = supabase.table("users") \
            .select("id, full_name, department, email, availability_status") \
            .in_("id", user_ids) \
            .execute()
        user_map = {u["id"]: u for u in (users_res.data or [])}
        for leave in leaves:
            leave["users"] = user_map.get(leave.get("user_id"), {})
    return leaves


@router.put("/{leave_id}/approve")
def approve_leave(leave_id: str, user=Depends(allow_manager_plus)):
    res = supabase.table("leave_requests").select("*").eq("id", leave_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Leave request not found")
    leave = res.data[0]
    supabase.table("leave_requests").update({
        "status":      "approved",
        "reviewed_by": user.id,
        "reviewed_at": datetime.datetime.utcnow().isoformat()
    }).eq("id", leave_id).execute()
    supabase.table("users").update({
        "availability_status": "on_leave"
    }).eq("id", leave["user_id"]).execute()
    print(f"[FlowGuard] Leave APPROVED for {leave['user_id']} by {user.email}")
    return {"message": "Leave approved. Employee marked as on_leave.", "leave_id": leave_id}


@router.put("/{leave_id}/reject")
def reject_leave(leave_id: str, user=Depends(allow_manager_plus)):
    res = supabase.table("leave_requests").select("*").eq("id", leave_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Leave request not found")
    leave = res.data[0]
    supabase.table("leave_requests").update({
        "status":      "rejected",
        "reviewed_by": user.id,
        "reviewed_at": datetime.datetime.utcnow().isoformat()
    }).eq("id", leave_id).execute()
    supabase.table("users").update({
        "availability_status": "active"
    }).eq("id", leave["user_id"]).execute()
    print(f"[FlowGuard] Leave REJECTED for {leave['user_id']} by {user.email}")
    return {"message": "Leave rejected. Employee remains active.", "leave_id": leave_id}


@router.put("/{leave_id}/reopen")
def reopen_leave(leave_id: str, user=Depends(allow_manager_plus)):
    res = supabase.table("leave_requests").select("*").eq("id", leave_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Leave request not found")
    supabase.table("leave_requests").update({
        "status":      "pending",
        "reviewed_by": None,
        "reviewed_at": None
    }).eq("id", leave_id).execute()
    print(f"[FlowGuard] Leave {leave_id} reset to PENDING by {user.email}")
    return {"message": "Leave reset to pending.", "leave_id": leave_id}