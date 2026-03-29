"""
FlowGuard AI — JWT Authentication & RBAC
Provides password hashing, token creation, and FastAPI dependencies
for role-based access control (Manager / Employee).
"""
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from database.db import supabase


# ── Config ─────────────────────────────────────────
SECRET_KEY = "flowguard-super-secret-key-change-in-prod"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours for demo

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ── Password helpers (SHA-256 for demo; use bcrypt in production) ──
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    # 1. Try standard SHA-256 hash match
    if hashlib.sha256(plain.encode()).hexdigest() == hashed:
        return True
    
    # 2. Fallback to direct plain-text match (for manually updated DB records like '123123')
    if plain == hashed:
        return True
        
    return False


# ── Token helpers ───────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ── Simple User Model for type hints ────────────────
class User:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id")
        self.email = kwargs.get("email")
        self.role = kwargs.get("role", "employee")
        self.full_name = kwargs.get("full_name") or kwargs.get("name", "Unknown")
        self.department = kwargs.get("department")                    # ✅ NEW
        self.availability_status = kwargs.get("availability_status", "active")  # ✅ NEW
        self.performance_score = kwargs.get("performance_score", 0.5) # ✅ NEW
        self.reliability = kwargs.get("reliability", 1.0)             # ✅ NEW
        self.avg_completion_time = kwargs.get("avg_completion_time")  # ✅ NEW
        self.current_workload = kwargs.get("current_workload", 0)     # ✅ NEW

    def __repr__(self):
        return f"<User {self.email}>"


# ── Current user dependency ─────────────────────────
def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # ✅ Try Supabase, but fall back gracefully if network fails
    try:
        response = supabase.table("users").select("*").eq("email", username).execute()
        if response.data:
            return User(**response.data[0])
    except Exception as e:
        print(f"[FlowGuard] WARN: Supabase lookup failed in get_current_user: {e}")

    # ✅ Fallback: build minimal user from JWT claims only
    return User(email=username)

# ── Role checkers ───────────────────────────────────
class RoleChecker:
    """Dependency that restricts access to specified roles."""
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)):
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not permitted for this action.",
            )
        return user


allow_manager = RoleChecker(["manager"])
allow_manager_plus = RoleChecker(["head", "manager"])
allow_all = RoleChecker(["head", "manager", "employee"])
allow_head_only = RoleChecker(["head"])