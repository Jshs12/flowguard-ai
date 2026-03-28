"""
FlowGuard AI — Audit Logs Router
Exposes the explainable AI decision trail.
"""
from fastapi import APIRouter, Depends
from database.db import supabase
from database.schemas import AuditLogOut
from auth.security import allow_manager_plus


router = APIRouter(prefix="/api/logs", tags=["Audit Logs"])


@router.get("/", response_model=list[AuditLogOut])
def list_logs(user=Depends(allow_manager_plus)):
    """Only managers can view audit logs."""
    response = supabase.table("audit_logs").select("*").order("created_at", desc=True).limit(200).execute()
    return response.data


@router.get("/workflow/{workflow_id}", response_model=list[AuditLogOut])
def logs_by_workflow(workflow_id: str, user=Depends(allow_manager_plus)):
    response = supabase.table("audit_logs").select("*").eq("workflow_id", workflow_id).order("created_at", desc=True).execute()
    return response.data