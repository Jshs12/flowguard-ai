from supabase import create_client
from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("[FlowGuard] ERROR: SUPABASE_URL or SUPABASE_SERVICE_KEY missing from .env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
print(f"[FlowGuard] ✅ Supabase connected to {SUPABASE_URL}")