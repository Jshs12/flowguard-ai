"""
FlowGuard AI — Main FastAPI Application
Entry point: initializes app and mounts all routers.
"""
import datetime
import traceback

from dotenv import load_dotenv
load_dotenv()  # ✅ Load .env BEFORE everything else

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from database.db import supabase

# ── Router imports ────────────────────────────────────────────────────
from routers.auth_router  import router as auth_router
from routers.workflows    import router as workflows_router
from routers.tasks_router import router as tasks_router   # ✅ only tasks_router, removed old routers.tasks
from routers.logs         import router as logs_router
from routers.leave_router import router as leave_router, restore_returned_employees
from scheduler import send_deadline_reminders
from scheduler import auto_reassign_delayed_tasks
# After app = FastAPI() and before scheduler
from database.db import supabase

# ── Config ───────────────────────────────────────────────────────────

# Scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(restore_returned_employees, 'interval', hours=1)
scheduler.add_job(send_deadline_reminders,    "interval", hours=1)
scheduler.add_job(auto_reassign_delayed_tasks, "interval", hours=1)
scheduler.start()

# ── 1. Create app ─────────────────────────────────────────────────────
app = FastAPI(
    title="FlowGuard AI",
    description="Autonomous Enterprise Workflow Intelligence — Multi-Agent System",
    version="1.0.0",
)

# ── 2. CORS ───────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 3. Exception logging middleware ───────────────────────────────────
@app.middleware("http")
async def log_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        print(f"[CRITICAL] Unhandled Exception: {e}")
        traceback.print_exc()
        raise e

# ── 4. Routers ────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(workflows_router)
app.include_router(tasks_router)
app.include_router(logs_router)
app.include_router(leave_router)

# ── 5. Health routes ──────────────────────────────────────────────────
@app.get("/")
def root():
    return {"message": "FlowGuard AI Backend Running", "status": "online"}

@app.get("/api/health")
async def health():
    return {
        "status": "online",
        "service": "FlowGuard AI",
        "version": "1.0.0",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }

# ── 6. Entry point ────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)