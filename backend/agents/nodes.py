"""
FlowGuard AI - Agent Node Functions
Each function represents one AI agent in the LangGraph workflow.
Used Groq LLM (Llama 3) for REAL intelligence when API key is available,
falls back to rule-based logic otherwise.
"""
import os, re, datetime, uuid, json
from typing import List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv



load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")



from database.db import supabase



# -- Try to load Groq LLM -----------------------------
_llm = None
try:
    from langchain_groq import ChatGroq
    api_key = os.getenv("GROQ_API_KEY", "")
    if api_key and api_key != "your_groq_api_key_here":
        _llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=api_key,
            temperature=0.3,
            max_tokens=2048,
        )
        print("[FlowGuard] [OK] Groq LLM loaded - agents will use real AI")
    else:
        print("[FlowGuard] [WARN] No GROQ_API_KEY - agents using rule-based fallback")
except Exception as e:
    print(f"[FlowGuard] [ERROR] Groq unavailable ({e}) - using rule-based fallback")




# -- Constants ------------------------------------------
DEPARTMENTS = {
    "marketing": "Marketing",
    "campaign": "Marketing",
    "social media": "Marketing",
    "content": "Marketing",
    "launch": "Marketing",
    "finance": "Finance",
    "budget": "Finance",
    "reconciliation": "Finance",
    "vendor": "Procurement",
    "procurement": "Procurement",
    "contract": "Procurement",
    "engineering": "Engineering",
    "deploy": "Engineering",
    "security": "Engineering",
    "audit": "Engineering",
    "api": "Engineering",
    "authentication": "Engineering",
    "server": "Engineering",
    "hr": "HR",
    "human resources": "HR",
    "onboarding": "HR",
    "handbook": "HR",
    "compliance": "HR",
    "design": "Design",
    "legal": "Legal",
    "sales": "Sales",
    "management": "Management",
    "admin": "Management",
    "operations": "Management",
}



PRIORITY_KEYWORDS = {
    "critical": ["urgent", "immediately", "asap", "critical", "emergency"],
    "high": ["important", "priority", "soon", "high priority", "must", "before"],
    "medium": ["plan", "prepare", "review", "schedule", "coordinate", "finalize"],
    "low": ["consider", "optional", "explore", "maybe", "later"],
}



PRIORITIES = {"critical": 0.9, "high": 0.7, "medium": 0.4, "low": 0.15}



# ✅ FIX 4: Normalize department names returned by LLM (e.g. "Hr" → "HR", "hr" → "HR")
_DEPT_NORMALIZE = {
    "hr": "HR",
    "human resources": "HR",
    "engineering": "Engineering",
    "marketing": "Marketing",
    "finance": "Finance",
    "procurement": "Procurement",
    "design": "Design",
    "legal": "Legal",
    "sales": "Sales",
    "management": "Management",
    "general": "General",
}


def _normalize_department(dept: str) -> str:
    """✅ FIX 4: Normalize department casing from LLM output."""
    if not dept:
        return "General"
    return _DEPT_NORMALIZE.get(dept.strip().lower(), dept.strip().title())



# ✅ FIX 3: Header/non-task line patterns to exclude
_SKIP_PATTERNS = [
    r'^meeting notes',
    r'^date[:\s]',
    r'^action items[:\s]?$',
    r'^agenda[:\s]',
    r'^attendees[:\s]',
    r'^summary[:\s]',
    r'^\d+\.',           # bare numbered lines like "1." with no task
    r'^q\d\s+(product|launch|planning)',
]



def _is_header_line(title: str) -> bool:
    """✅ FIX 3: Returns True if the line looks like a document header, not a real task."""
    t = title.strip().lower()
    return any(re.match(p, t) for p in _SKIP_PATTERNS)



# -- Helpers ------------------------------------------
def _detect_priority(sentence: str) -> str:
    s = sentence.lower()
    # ✅ FIX 1: Detect explicit "Priority: X" pattern FIRST before keyword scan
    explicit = re.search(r'priority[:\s]+(\w+)', s)
    if explicit:
        p = explicit.group(1).lower()
        if p in PRIORITIES:
            return p
    for prio, keywords in PRIORITY_KEYWORDS.items():
        if any(kw in s for kw in keywords):
            return prio
    return "medium"




def _detect_department(sentence: str) -> str:
    s = sentence.lower()
    for keyword, dept in DEPARTMENTS.items():
        if keyword in s:
            return dept
    return "General"




def _detect_complexity(sentence: str) -> str:
    s = sentence.lower()
    # ✅ FIX 1: Detect explicit "Complexity: X" pattern FIRST
    explicit = re.search(r'complexity[:\s]+(\w+)', s)
    if explicit:
        c = explicit.group(1).lower()
        if c in ["low", "medium", "high"]:
            return c
    if any(w in s for w in ["full", "complete", "entire", "comprehensive", "all", "major"]):
        return "high"
    if any(w in s for w in ["quick", "simple", "brief", "small", "minor"]):
        return "low"
    return "medium"




def _rule_based_extraction(transcript: str) -> List[Dict[str, Any]]:
    """Extract tasks from transcript using rule-based logic — no LLM needed."""
    sentences = [s.strip() for s in re.split(r'[.\n]', transcript) if len(s.strip()) > 20]
    tasks = []



    action_verbs = [
        "deploy", "prepare", "finalize", "complete", "review", "update",
        "submit", "create", "schedule", "coordinate", "conduct", "audit",
        "organize", "develop", "implement", "launch", "analyze", "send",
        "needs to", "should", "must", "will", "need to"
    ]



    for sentence in sentences:
        s_lower = sentence.lower()


        # ✅ FIX 3: Skip document header/title lines
        if _is_header_line(sentence):
            continue


        if any(verb in s_lower for verb in action_verbs):
            dept = _detect_department(sentence)
            priority = _detect_priority(sentence)
            complexity = _detect_complexity(sentence)


            # ✅ FIX 2: Parse explicit "Deadline: X days" from sentence
            deadline_match = re.search(r'deadline[:\s]+(\d+)\s*days?', s_lower)
            if deadline_match:
                sla_days = int(deadline_match.group(1))
            else:
                sla_days = 1 if priority == "critical" else 2 if priority == "high" else 5


            title = sentence.strip()
            if len(title) > 80:
                title = title[:77] + "..."



            tasks.append({
                "title": title,
                "type": dept,
                "department": dept,
                "priority": priority,
                "deadline": sla_days,   # ✅ FIX 2: use parsed sla_days
                "complexity": complexity,
            })



    return tasks




def _mask_pii(text: str) -> Dict[str, Any]:
    emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    mapping = {}
    masked_text = text



    for i, email in enumerate(list(set(emails))):
        placeholder = f"EMAIL_{i+1}"
        mapping[placeholder] = email
        masked_text = masked_text.replace(email, placeholder)



    names = re.findall(r'\b[A-Z][a-z]{2,}\b', masked_text)
    ignore_list = [
        "The", "And", "But", "For", "With", "This", "That",
        "Action", "Goal", "Task", "Meeting", "Project", "Wait",
        "Start", "End", "Phase", "General"
    ]
    names = [n for n in names if n not in ignore_list]



    for i, name in enumerate(list(set(names))):
        placeholder = f"PERSON_{i+1}"
        mapping[placeholder] = name
        masked_text = masked_text.replace(name, placeholder)



    return {"text": masked_text, "mapping": mapping}




def _unmask_pii(text: str, mapping: Dict[str, str]) -> str:
    for placeholder, real in mapping.items():
        text = text.replace(placeholder, real)
    return text




def _safe_llm_call(prompt: str) -> str:
    if _llm is None:
        return ""
    try:
        response = _llm.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        print(f"[FlowGuard] LLM call failed: {e}")
        return ""




def _parse_json_from_llm(text: str) -> Any:
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return None




def get_available_employees(department: str):
    try:
        response = supabase.table("users") \
            .select("id, name, full_name, department, performance_score, availability_status, avg_completion_time, reliability, current_workload") \
            .eq("availability_status", "active") \
            .eq("role", "employee") \
            .eq("department", department) \
            .order("performance_score", desc=True) \
            .execute()
        return response.data or []
    except Exception as e:
        print(f"[FlowGuard] [ERROR] get_available_employees failed: {e}")
        return []




# =======================================================
#  AGENT 1: Data Extraction Agent
# =======================================================
def extraction_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    print(f"[FlowGuard] [EXTRACT] Agent 1 (Extraction) starting...")
    transcript = state.get("transcript", "")
    action_items = []
    used_llm = False



    # Try LLM first
    if _llm and transcript:
        try:
            mask_res = _mask_pii(transcript)
            masked_text = mask_res["text"]
            pii_mapping = mask_res["mapping"]
            state["pii_mapping"] = pii_mapping



            prompt = """You are an AI that extracts actionable tasks from meeting transcripts.
Extract ALL action items from this transcript.



For each action item return a JSON object with:
- title: clear task name (string)
- type: work category (string)
- department: MUST be one of: Engineering, Marketing, Finance, Procurement, Design, HR, Legal, Sales, Management
- priority: one of: low, medium, high, critical
- deadline: number of days from now (integer)
- complexity: one of: low, medium, high
-sParse ACTION ITEMS from meeting notes. Format: TITLE | PRIORITY | DEADLINE | DEPARTMENT
Parse EXACTLY:
- PRIORITY → risk_score (critical=95, high=80, medium=50, low=25)
- DEADLINE → days_from_today (1 day=1, 5 days=5, next week=7)
- DEPARTMENT → auto-assign (Marketing→Marketing team, Engineering→Engineering)


Transcript:
\"\"\"
{transcript}
\"\"\"



Return ONLY a valid JSON array. No explanation, no markdown, just the array.
Example: [{{"title": "Deploy auth module", "type": "Development", "department": "Engineering", "priority": "critical", "deadline": 2, "complexity": "high"}}]
""".format(transcript=masked_text)



            raw = _safe_llm_call(prompt)
            print(f"[FlowGuard] [EXTRACT] LLM raw response: {raw[:300] if raw else 'EMPTY'}")



            if raw:
                parsed = _parse_json_from_llm(raw)
                if isinstance(parsed, list) and len(parsed) > 0:
                    for item in parsed:
                        if isinstance(item, dict):
                            for key in ["title", "type", "department"]:
                                if key in item and isinstance(item[key], str):
                                    item[key] = _unmask_pii(item[key], pii_mapping)
                            # ✅ FIX 4: Normalize department casing from LLM (e.g. "Hr" → "HR")
                            item["department"] = _normalize_department(item.get("department", "General"))
                            # ✅ FIX 1: Normalize priority casing from LLM
                            item["priority"] = str(item.get("priority", "medium")).lower()
                            if item["priority"] not in PRIORITIES:
                                item["priority"] = "medium"
                            # ✅ FIX 2: Ensure deadline is always an int
                            try:
                                item["deadline"] = int(item.get("deadline") or 2)
                            except (ValueError, TypeError):
                                item["deadline"] = 2


                    # ✅ FIX 3: Filter out header/non-task lines from LLM output
                    action_items = [
                        item for item in parsed
                        if isinstance(item, dict) and not _is_header_line(item.get("title", ""))
                    ]
                    used_llm = True
                    print(f"[FlowGuard] [EXTRACT] LLM extracted {len(action_items)} tasks")
                else:
                    print(f"[FlowGuard] [EXTRACT] LLM returned invalid/empty JSON, falling back")
        except Exception as e:
            print(f"[FlowGuard] [EXTRACT] LLM extraction failed: {e}")



    # Rule-based fallback if LLM failed or returned nothing
    if not action_items:
        print(f"[FlowGuard] [EXTRACT] Using rule-based extraction...")
        action_items = _rule_based_extraction(transcript)
        print(f"[FlowGuard] [EXTRACT] Rule-based extracted {len(action_items)} tasks")



    # Store in both for backward compatibility
    state["actionitems"] = action_items
    state["rawextracted"] = action_items
    state["action_items"] = action_items
    state["raw_extracted"] = action_items



    state["logs"].append({
        "id": str(uuid.uuid4()),
        "agent_name": "Extraction Agent",
        "action": f"Extracted {len(action_items)} tasks ({'Groq LLM + PII masking' if used_llm else 'Rule-based engine'})",
        "reason": "Analyzed meeting transcript for actionable items",
        "confidence": 0.92 if used_llm else 0.75,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    })
    return state




# =======================================================
#  AGENT 2: Task Generation Agent
# =======================================================
def task_generation_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    print(f"[FlowGuard] [TASKGEN] Agent 2 (Task Generation) starting...")



    used_key = "actionitems"
    raw_extracted = state.get("actionitems")
    if not raw_extracted:
        raw_extracted = state.get("rawextracted")
        used_key = "rawextracted"
    if not raw_extracted:
        raw_extracted = state.get("action_items")
        used_key = "action_items"



    raw_extracted = raw_extracted or []



    print(f"[FlowGuard] [TASKGEN] Using state key: '{used_key}'")
    print(f"[FlowGuard] [TASKGEN] Input task count: {len(raw_extracted)}")
    tasks = []



    for item in raw_extracted:
        parent_id = str(uuid.uuid4())
        complexity = str(item.get("complexity", "medium")).lower()
        priority = str(item.get("priority", "medium")).lower()
        if priority not in PRIORITIES:
            priority = "medium"



        deadline_raw = item.get("deadline") or item.get("sla_days") or 2
        try:
            sla_days = int(deadline_raw)
        except (ValueError, TypeError):
            sla_days = 2



        # ── FIXED: added task_type field ──────────────────────────────
        base_task = {
            "id": parent_id,
            "title": str(item.get("title", "Untitled Task")),
            "description": str(item.get("description") or f"Type: {item.get('type', 'General')}. Original Department: {item.get('department', 'General')}"),
            "priority": priority,
            "complexity": complexity,
            "department": item.get("department", "General"),
            # ADDED: preserve task_type from extraction so it's never "general" blindly
            "task_type": str(item.get("type") or item.get("task_type") or item.get("department") or "general").lower(),
            "status": "pending",
            "owner_name": "Unassigned",
            "assigned_to": None,
            "sla_days": sla_days,
        }



        if complexity == "high":
            print(f"[FlowGuard] Splitting high-complexity task: '{base_task['title']}'")
            for i, phase in enumerate(["Setup & Planning", "Core Implementation", "Validation & Testing"]):
                sub = base_task.copy()
                sub["id"] = str(uuid.uuid4())
                sub["title"] = f"Phase {i+1}: {phase} — {base_task['title']}"
                sub["parent_task_id"] = parent_id
                sub["complexity"] = "medium"
                tasks.append(sub)
            # FIXED: Do NOT append base_task if it was split into phases
        else:
            tasks.append(base_task)



    print(f"[FlowGuard] [TASKGEN] Output task count: {len(tasks)}")



    if not tasks and raw_extracted:
        print("[FlowGuard] [TASKGEN] [WARN] Forced fallback task due to empty results.")
        for item in raw_extracted:
            tasks.append({
                "id": str(uuid.uuid4()),
                "title": item.get("title", "Recovered Task"),
                "department": item.get("department", "General"),
                "task_type": str(item.get("type") or item.get("department") or "general").lower(),
                "priority": item.get("priority", "medium"),
                "status": "pending",
                "assigned_to": None,
                "owner_name": "Unassigned",
                "sla_days": 2
            })



    state["tasks"] = tasks
    state["logs"].append({
        "id": str(uuid.uuid4()),
        "agent_name": "Task Generation Agent",
        "action": f"Generated {len(tasks)} tasks (from {len(raw_extracted)} using '{used_key}')",
        "reason": "Applied complexity-based task splitting and ensured field preservation",
        "confidence": 0.95,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    })
    return state




# =======================================================
#  AGENT 3: Assignment Agent
# =======================================================
def assignment_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    print(f"[FlowGuard] [ASSIGN] Agent 3 (Assignment) starting...")
    tasks = state.get("tasks", [])
    assignments_made = 0
    unassigned = []



    try:
        users_res = supabase.table("users") \
            .select("id, name, full_name, department, performance_score, avg_completion_time, reliability, current_workload, availability_status") \
            .eq("availability_status", "active") \
            .eq("role", "employee") \
            .execute()
        active_users = users_res.data or []
        print(f"[FlowGuard] [ASSIGN] Found {len(active_users)} active employees.")
        for u in active_users:
            print(f"[FlowGuard] [ASSIGN] Employee: {u.get('name')} | Dept: {u.get('department')} | Status: {u.get('availability_status')}")
    except Exception as e:
        print(f"[FlowGuard] [ERROR] Fetching users failed: {e}")
        active_users = []



    for task in tasks:
        # ── FIXED: preserve original task department throughout ────────
        original_dept = str(task.get("department", "General")).strip()
        task_dept_lower = original_dept.lower()
        priority = task.get("priority", "medium").lower()
        sla_days = task.get("sla_days", 2)



        print(f"[FlowGuard] [ASSIGN] Task: '{task['title']}' | Priority: '{priority}' | Dept: '{original_dept}'")



        # 1. Filter by department match (case-insensitive)
        dept_users = [
            u for u in active_users
            if str(u.get("department", "")).strip().lower() == task_dept_lower
        ]



        # 2. If no dept match → fallback to any active employee
        if not dept_users:
            print(f"[FlowGuard] [ASSIGN] No dept match for '{original_dept}', falling back to all active employees.")
            candidates = active_users
        else:
            candidates = dept_users



        if not candidates:
            print(f"[FlowGuard] [ASSIGN] ❌ No employees available for '{task['title']}'")
            unassigned.append(task["title"])
            task["assigned_to"] = None
            task["owner_name"] = "Unassigned"
            continue



        # 3. Score candidates
        scored = []
        for u in candidates:
            perf = float(u.get("performance_score") or 0.5)
            avg_time = float(u.get("avg_completion_time") or 24)
            speed = max(0.0, min(1.0, 1.0 - (avg_time / 48.0)))
            rel = float(u.get("reliability") or 1.0)
            workload = int(u.get("current_workload") or 0)
            efficiency = (perf * 0.5) + (speed * 0.3) + (rel * 0.2)
            scored.append({
                "user": u,
                "efficiency": efficiency,
                "workload": workload,
                "is_dept_match": str(u.get("department", "")).strip().lower() == task_dept_lower
            })



        # 4. Ranking logic
        if priority in ["high", "critical"] or sla_days <= 1:
            print(f"[FlowGuard] [ASSIGN] Critical/Urgent: Ranking by Efficiency.")
            scored.sort(key=lambda x: (x["efficiency"], -x["workload"]), reverse=True)
        else:
            print(f"[FlowGuard] [ASSIGN] Standard: Ranking by Dept Match & Workload.")
            scored.sort(key=lambda x: (x["is_dept_match"], -x["workload"], x["efficiency"]), reverse=True)



        best = scored[0]["user"]
        task["assigned_to"] = best["id"]
        task["owner_name"] = best.get("full_name") or best.get("name") or "Unknown"



        # ── FIXED: do NOT overwrite task department with assignee's dept ──
        # Only set department if it was blank/General AND no dept match was found
        if not task.get("department") or task["department"] == "General":
            task["department"] = best.get("department", "General")
        # Otherwise keep the original task department intact
        # This means "Marketing" task stays "Marketing" even if assigned to Dave



        assignments_made += 1
        print(f"[FlowGuard] [ASSIGN] ✅ '{task['title']}' → {task['owner_name']} "
              f"(dept kept: {task['department']}, assignee dept: {best.get('department')}, "
              f"efficiency: {round(scored[0]['efficiency'], 2)})")



    if unassigned:
        state["logs"].append({
            "id": str(uuid.uuid4()),
            "agent_name": "Assignment Agent",
            "action": f"Could not assign {len(unassigned)} tasks",
            "reason": "No active employees available",
            "confidence": 1.0,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        })



    state["tasks"] = tasks
    state["logs"].append({
        "id": str(uuid.uuid4()),
        "agent_name": "Assignment Agent",
        "action": f"Assigned {assignments_made}/{len(tasks)} tasks using Ranking Engine",
        "reason": f"Ranked by Efficiency (critical) or Workload/Dept (standard)",
        "confidence": 1.0,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    })
    return state




# =======================================================
#  AGENT 4: Monitoring Agent
# =======================================================
def monitoring_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    print(f"[FlowGuard] [MONITOR] Agent 4 (Monitoring) starting...")
    tasks = state.get("tasks", [])
    risks_detected = 0



    try:
        users_res = supabase.table("users").select("id, avg_completion_time").execute()
        users_stats = {
            u["id"]: float(u.get("avg_completion_time") or 24)
            for u in (users_res.data or [])
        }
    except Exception as e:
        print(f"[FlowGuard] [WARN] Could not fetch user stats: {e}")
        users_stats = {}



    for task in tasks:
        sla_days = task.get("sla_days", 2)
        task["sla_deadline"] = (
            datetime.datetime.utcnow() + datetime.timedelta(days=sla_days)
        ).isoformat()

        # ✅ FIX 5: Get priority for risk calculation — was completely ignored before
        priority = task.get("priority", "medium")

        # ✅ FIX 5: Priority-based score table
        # critical=1.0, high=0.7, medium=0.4, low=0.15
        _PRIO_SCORE = {"critical": 1.0, "high": 0.7, "medium": 0.4, "low": 0.15}
        prio_score = _PRIO_SCORE.get(priority, 0.4)

        # ✅ FIX 5: Deadline urgency score — 14 days = zero urgency, 1 day = max urgency
        days_score = max(0.0, round(1.0 - (sla_days / 14.0), 3))

        owner_id = task.get("assigned_to")
        if owner_id and owner_id in users_stats:
            user_avg = users_stats[owner_id]
            remaining_hours = sla_days * 24
            if user_avg > remaining_hours:
                task["is_delayed_risk"] = True
                # ✅ FIX 5: Blend user delay + priority + deadline urgency
                task["risk_score"] = round(min(1.0,
                    (0.4 * 1.0) + (0.3 * prio_score) + (0.3 * days_score)
                ), 2)
                risks_detected += 1
            else:
                task["is_delayed_risk"] = False
                # ✅ FIX 5: Time risk + priority + deadline all blended
                time_risk = user_avg / max(remaining_hours, 1)
                task["risk_score"] = round(min(0.95,
                    (0.4 * time_risk) + (0.35 * prio_score) + (0.25 * days_score)
                ), 2)
        else:
            # ✅ FIX 5: No user stats — derive risk purely from priority + deadline
            # This was always 0.2 before — now it varies meaningfully
            task["is_delayed_risk"] = False
            combined = round((days_score * 0.55) + (prio_score * 0.45), 2)
            task["risk_score"] = combined
            if combined >= 0.6:
                task["is_delayed_risk"] = True
                risks_detected += 1

        print(f"[FlowGuard] [MONITOR] '{task['title']}' → "
              f"priority={priority}, sla_days={sla_days}, "
              f"risk={task['risk_score']}, delayed={task['is_delayed_risk']}")



    state["tasks"] = tasks
    state["logs"].append({
        "id": str(uuid.uuid4()),
        "agent_name": "Monitoring Agent",
        "action": f"Detected {risks_detected} tasks at risk of delay",
        "reason": "Compared avg completion time vs SLA deadline",
        "confidence": 0.88,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    })
    return state




# =======================================================
#  AGENT 5: Escalation Agent
# =======================================================
def escalation_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    print(f"[FlowGuard] [ESCALATE] Agent 5 (Escalation) starting...")
    tasks = state.get("tasks", [])
    escalation_recommendations = []



    for task in tasks:
        if task.get("status") == "escalated":
            escalation_recommendations.append({
                "task_title": task["title"],
                "recommendation": "Reassign owner or notify manager immediately",
                "risk_score": task.get("risk_score", 0.0),
            })



    total = len(tasks)
    pending = sum(1 for t in tasks if t.get("status") == "pending")
    escalated_count = sum(1 for t in tasks if t.get("status") == "escalated")
    health = (
        "critical" if escalated_count > total * 0.3
        else "warning" if escalated_count > 0
        else "healthy"
    )



    state["escalations"] = escalation_recommendations
    state["workflow_summary"] = {
        "total_tasks": total,
        "pending": pending,
        "escalated": escalated_count,
        "health": health,
    }
    state["logs"].append({
        "id": str(uuid.uuid4()),
        "agent_name": "Escalation Agent",
        "action": f"Generated {len(escalation_recommendations)} escalation recommendations",
        "reason": f"Workflow health: {health} — {escalated_count}/{total} escalated",
        "confidence": 0.90,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    })
    return state