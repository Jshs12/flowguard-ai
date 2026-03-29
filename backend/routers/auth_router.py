"""
FlowGuard AI — Auth Router
Handles login, register, user management.
"""
import uuid
import datetime
from fastapi import APIRouter, HTTPException, Depends
from database.db import supabase
from database.schemas import LoginRequest, RegisterRequest, TokenResponse
from auth.security import (
    get_current_user,
    allow_all,
    allow_manager_plus,
    allow_head_only,
    hash_password,
    verify_password,
    create_access_token
)


router = APIRouter(prefix="/api/auth", tags=["Auth"])



# ── Login ─────────────────────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest):
    res = supabase.table("users").select("*").eq("email", data.username).execute()
    if not res.data:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user = res.data[0]
    if not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(data={"sub": user["email"]})

    return TokenResponse(
        access_token=token,
        role=user["role"],
        username=user["email"],
        full_name=user.get("full_name") or user.get("name", ""),
        user_id=str(user["id"]),
    )



# ══════════════════════════════════════════════════════
# ✅ NEW (Phase 3 Item 14) — Onboarding helper
# Auto-creates buddy assignment + orientation task
# when a new employee registers
# ══════════════════════════════════════════════════════
def _run_onboarding(new_user: dict):
    """
    Called right after a new employee registers.
    1. Finds a buddy (most senior active employee in same dept)
    2. Creates an orientation task assigned to them
    3. Logs both actions in audit_trail
    """
    try:
        dept    = (new_user.get("department") or "General").strip().title()
        user_id = new_user["id"]
        name    = new_user.get("full_name") or new_user.get("name", "New Employee")
        now     = datetime.datetime.utcnow().isoformat()

        # ── Step 1: Find buddy (lowest workload active employee, same dept, not self) ──
        buddy_res = supabase.table("users").select("*") \
            .eq("department", dept) \
            .eq("availability_status", "active") \
            .eq("role", "employee") \
            .execute()

        candidates = [u for u in (buddy_res.data or []) if u["id"] != user_id]

        buddy    = None
        buddy_id = None

        if candidates:
            candidates.sort(key=lambda u: (
                u.get("current_workload", 0),
                -float(u.get("performance_score", 0.5) or 0.5)
            ))
            buddy    = candidates[0]
            buddy_id = buddy["id"]
            buddy_name = buddy.get("full_name", "Team Member")

            # Log buddy assignment in audit trail
            supabase.table("audit_logs").insert({
                "workflow_id": None,
                "agent":       "OnboardingAgent",
                "decision":    f"🤝 BUDDY ASSIGNED: {name} paired with {buddy_name}",
                "reason":      f"New employee {name} joined {dept} dept. "
                               f"Buddy {buddy_name} assigned (lowest workload in dept).",
                "confidence":  1.0,
                "created_at":  now
            }).execute()

            print(f"[FlowGuard] 🤝 Onboarding: {name} → buddy: {buddy_name}")
        else:
            print(f"[FlowGuard] ⚠️ Onboarding: No buddy found in {dept} dept")

        # ── Step 2: Create orientation task assigned to new employee ──
        orientation_deadline = (
            datetime.datetime.utcnow() + datetime.timedelta(days=3)
        ).isoformat()

        orientation_task = {
            "id":              str(uuid.uuid4()),
            "workflow_id":     None,
            "title":           f"Onboarding Orientation — {name}",
            "description":     f"Complete onboarding checklist: system access, "
                               f"team intro, process walkthrough for {dept} dept.",
            "task_type":       "onboarding",
            "assigned_to":     user_id,
            "owner_name":      name,
            "department":      dept,
            "status":          "pending",
            "priority":        "high",
            "complexity":      "low",
            "risk_score":      0.2,
            "is_delayed_risk": False,
            "sla_deadline":    orientation_deadline,
            "deadline":        orientation_deadline,
            "parent_task_id":  None,
            "created_by":      user_id,
            "created_at":      now
        }

        supabase.table("tasks").insert(orientation_task).execute()

        # ── Step 3: Log orientation task creation in audit trail ──
        supabase.table("audit_logs").insert({
            "workflow_id": None,
            "agent":       "OnboardingAgent",
            "decision":    f"📋 ORIENTATION TASK CREATED for {name}",
            "reason":      f"Auto-generated 3-day onboarding task for new {dept} employee. "
                           f"Buddy: {buddy.get('full_name', 'None') if buddy else 'None'}.",
            "confidence":  1.0,
            "created_at":  now
        }).execute()

        print(f"[FlowGuard] 📋 Onboarding task created for {name} (deadline: {orientation_deadline[:10]})")

    except Exception as e:
        print(f"[FlowGuard] WARN: onboarding failed for {new_user.get('id')}: {e}")
        import traceback; traceback.print_exc()



# ── Register ──────────────────────────────────────────────────────────
@router.post("/register")
def register(data: RegisterRequest):
    existing = supabase.table("users").select("id").eq("email", data.email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = hash_password(data.password)

    new_user = {
        "id":                  str(uuid.uuid4()),
        "name":                data.name,
        "full_name":           data.full_name or data.name,
        "email":               data.email,
        "password":            hashed,
        "role":                data.role,
        "department":          data.department,
        "availability_status": "active",
        "performance_score":   0.5,
        "reliability":         0.5,
        "current_workload":    0,
    }

    supabase.table("users").insert(new_user).execute()

    # ✅ NEW: trigger onboarding only for new employees
    if data.role == "employee":
        _run_onboarding(new_user)

    return {"message": "Account created successfully"}



# ── Get Current User ──────────────────────────────────────────────────
@router.get("/me")
def me(user=Depends(get_current_user)):
    return {
        "id":         user.id,
        "email":      user.email,
        "role":       user.role,
        "full_name":  user.full_name,
        "department": user.department,
    }



# ── List All Users (HOD + Manager) ───────────────────────────────────
@router.get("/users")
def list_users(department: str = None, user=Depends(allow_manager_plus)):
    query = supabase.table("users").select(
        "id, name, full_name, email, role, department, "
        "availability_status, performance_score, reliability, current_workload"
    )
    if department:
        query = query.eq("department", department)
    res = query.execute()
    return res.data



# ── Get Users by Department ───────────────────────────────────────────
@router.get("/users/department/{department}")
def users_by_department(department: str, user=Depends(allow_manager_plus)):
    res = supabase.table("users").select(
        "id, name, full_name, email, role, department, "
        "availability_status, performance_score, reliability, current_workload"
    ).eq("department", department).execute()
    return res.data



# ── Update User Role (HOD only) ───────────────────────────────────────
@router.put("/users/{user_id}/role")
def update_role(user_id: str, payload: dict, user=Depends(allow_head_only)):
    new_role = payload.get("role")
    if new_role not in ["employee", "manager", "head"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    supabase.table("users").update({"role": new_role}).eq("id", user_id).execute()
    return {"message": f"Role updated to {new_role}"}



# ── Update Profile ────────────────────────────────────────────────────
@router.put("/update-profile")
def update_profile(payload: dict, user=Depends(get_current_user)):
    allowed     = ["full_name", "name", "department", "availability_status"]
    update_data = {k: v for k, v in payload.items() if k in allowed}
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    supabase.table("users").update(update_data).eq("id", user.id).execute()
    return {"message": "Profile updated successfully"}



# ── Change Password ───────────────────────────────────────────────────
@router.put("/change-password")
def change_password(payload: dict, user=Depends(get_current_user)):
    old_pw = payload.get("old_password")
    new_pw = payload.get("new_password")

    res = supabase.table("users").select("password").eq("id", user.id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(old_pw, res.data[0]["password"]):
        raise HTTPException(status_code=401, detail="Old password incorrect")

    hashed = hash_password(new_pw)
    supabase.table("users").update({"password": hashed}).eq("id", user.id).execute()
    return {"message": "Password changed successfully"}



# ── Delete User (HOD only) ────────────────────────────────────────────
@router.delete("/users/{user_id}")
def delete_user(user_id: str, user=Depends(allow_head_only)):
    supabase.table("users").delete().eq("id", user_id).execute()
    return {"message": "User deleted successfully"}