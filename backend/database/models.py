"""
FlowGuard AI — SQLAlchemy Models
Defines: User, Workflow, Task, AuditLog
"""
import datetime, uuid
from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from .db import Base


def _uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    username = Column(String(80), unique=True, nullable=False, index=True)
    hashed_password = Column(String(256), nullable=False)
    full_name = Column(String(120), nullable=False)
    role = Column(SAEnum("head", "manager", "employee", name="user_role"), default="employee")
    department = Column(String(80), default="General")
    availability_status = Column(String(20), default="active")  # active | inactive
    performance_score = Column(Float, default=0.5)
    avg_completion_time = Column(Float, default=0.0)
    reliability = Column(Float, default=0.0)
    current_workload = Column(Integer, default=0)  # Added to track pending tasks count

    tasks = relationship("Task", back_populates="owner")


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(String, primary_key=True, default=_uuid)
    title = Column(String(200), default="Untitled Workflow")
    raw_input = Column(Text, nullable=False)
    transcript = Column(Text, default="")
    status = Column(String(40), default="processing")  # processing | completed | failed
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)

    tasks = relationship("Task", back_populates="workflow")
    logs = relationship("AuditLog", back_populates="workflow")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=_uuid)
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text, default="")
    owner_id = Column(String, ForeignKey("users.id"), nullable=True)
    owner_name = Column(String(120), default="Unassigned")
    department = Column(String(80), default="General")
    status = Column(String(40), default="pending")  # pending | in_progress | completed | escalated
    priority = Column(String(20), default="medium")  # low | medium | high | critical
    complexity = Column(String(20), default="medium")  # low | medium | high
    risk_score = Column(Float, default=0.0)
    is_delayed_risk = Column(Boolean, default=False)
    sla_deadline = Column(DateTime, nullable=True)
    parent_task_id = Column(String, ForeignKey("tasks.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    workflow = relationship("Workflow", back_populates="tasks")
    owner = relationship("User", back_populates="tasks")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=_uuid)
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False)
    agent_name = Column(String(100), nullable=False)
    action = Column(String(300), nullable=False)
    reason = Column(Text, default="")
    confidence = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    workflow = relationship("Workflow", back_populates="logs")


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    reason = Column(Text, default="")
    status = Column(String(20), default="pending")  # pending | approved | rejected
