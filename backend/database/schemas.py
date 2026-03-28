"""
FlowGuard AI — Pydantic Schemas
Request / Response validation models.
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date  # ✅ added date



# ── Auth ─────────────────────────────────────────
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    full_name: str
    user_id: str



class LoginRequest(BaseModel):
    username: str
    password: str
    department: Optional[str] = None



class RegisterRequest(BaseModel):
    name: str
    full_name: Optional[str] = None          # ✅ NEW
    email: str
    password: str
    role: str
    department: Optional[str] = None



# ── Workflow ─────────────────────────────────────
class WorkflowCreate(BaseModel):
    raw_input: str
    title: Optional[str] = "Untitled Workflow"



class TaskOut(BaseModel):
    id: str
    workflow_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    department: Optional[str] = None
    assigned_to: Optional[str] = None
    owner_name: Optional[str] = None
    deadline: Optional[datetime] = None
    status: str
    priority: str
    complexity: Optional[str] = "medium"
    risk_score: Optional[float] = 0.0
    is_delayed_risk: bool = False
    sla_deadline: Optional[datetime] = None
    parent_task_id: Optional[str] = None
    split_requested: Optional[bool] = False  # ✅ NEW
    created_at: datetime


    class Config:
        from_attributes = True



class AuditLogOut(BaseModel):
    id: str
    workflow_id: Optional[str] = None
    task_id: Optional[str] = None
    agent: str
    decision: str
    confidence: float
    created_at: datetime


    class Config:
        from_attributes = True



class WorkflowOut(BaseModel):
    id: str
    title: str
    status: str
    created_at: datetime
    tasks: List[TaskOut] = []
    logs: List[AuditLogOut] = []


    class Config:
        from_attributes = True



# ── Task Update (Human-in-the-Loop) ─────────────
class TaskUpdate(BaseModel):
    assigned_to: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None



# ── Simulation ───────────────────────────────────
class SimulationRequest(BaseModel):
    task_id: str
    delay_days: int = 2



class SimulationResult(BaseModel):
    task_title: str
    original_risk: float
    simulated_risk: float
    sla_breach: bool
    impact_summary: str
    suggestion: str



# ── Auto-Assign ──────────────────────────────────
class TaskAutoAssignRequest(BaseModel):
    title: str
    task_type: str
    department: str
    deadline: Optional[datetime] = None      # ✅ made Optional (was crashing if not sent)



class TaskAutoAssignResponse(BaseModel):
    assigned_to: str
    score: float
    reason: str



# ── Leave ────────────────────────────────────────
class LeaveRequestCreate(BaseModel):
    start_date: date                         # ✅ date not datetime
    end_date: date
    reason: str = ""



class LeaveRequestOut(BaseModel):
    id: str
    user_id: str
    start_date: datetime
    end_date: datetime
    reason: str
    status: str


    class Config:
        from_attributes = True