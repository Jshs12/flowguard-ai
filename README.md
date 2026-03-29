# ⚡ FLOWGUARD AI: Autonomous Workflow Intelligence
### *Bridge the gap between meeting talk and enterprise execution.*

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Framework-green?logo=fastapi)
![React](https://img.shields.io/badge/React-Frontend-blue?logo=react)
![Docker](https://img.shields.io/badge/Docker-Containerization-blue?logo=docker)
![Supabase](https://img.shields.io/badge/Supabase-Database-green?logo=supabase)

---

## 📖 What is FlowGuard AI?
FlowGuard AI is a multi-agent autonomous system that transforms unstructured meeting transcripts into structured, actionable, and tracked enterprise workflows. 

It doesn't just record meetings—it **reasons** through them. It identifies tasks, masks sensitive PII data, intelligently assigns them to the best-suited employees based on performance metrics, and proactively monitors SLAs to prevent project delays.

---

## 🚀 How to Deploy (Local PC)

### Prerequisites
- **Docker & Docker Compose** installed.
- **Node.js** (for frontend development, optional if using Docker).
- **Python 3.10+** (for backend development, optional if using Docker).
- **Supabase Account** (to host your database).
- **Groq API Key** (for lightning-fast LLM inference).

### Step 1: Environment Setup
Create a `.env` file in the root directory:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
GROQ_API_KEY=gsk_your_key_here
JWT_SECRET=your_random_secret_string
```

### Step 2: Launch the System
Run the following command in your terminal:
```bash
docker-compose up -d --build
```
This will start:
- **Backend API**: `http://localhost:8001`
- **Frontend UI**: `http://localhost:5173`
- **Nginx Load Balancer**: `http://localhost:8080` (Standard gateway)

---

## 🎮 How to Use the Application

### 1. Management Flow (Manager/HOD)
- **Login**: Use a manager account (e.g., `manager@company.com`).
- **Input Metadata**: Enter meeting title and department.
- **Process Transcript**: Paste a meeting transcript into the text area and click **"Process Meeting"**.
- **Agent Pipeline**: Watch as the AI agents extract tasks, calculate risk scores, and assign them to employees.
- **Dashboard**: View the progress of all tasks, check audit logs for AI decisions, and use the "What-If" simulator to predict delays.

### 2. Employee Flow
- **Login**: Use an employee account (e.g., `employee1@company.com`).
- **Task Board**: View tasks specifically assigned to you by the AI.
- **Execution**: Move tasks to "In Progress" or "Completed".
- **Split Task**: If a task is too complex, click **"✂ Split"** to request AI-assisted decomposition and helper assignment.
- **Performance**: Track your efficiency score, completion rate, and speed metrics.

---

## 🧪 How to Test

### Backend API Testing
You can test the endpoints using any REST client or the built-in FastAPI docs at `http://localhost:8001/docs`.
- **Health Check**: `GET /api/health`
- **Process Workflow**: `POST /api/workflows/process` (requires valid transcript)

### Automated Test Scripts
We have included several verification scripts in the `backend/` folder:
```bash
# Test the multi-agent pipeline logic
python backend/test_pipeline_v2.py

# Verify database schema and relationships
python backend/verify_schema_logic.py
```

---

## 🎬 Demo Script

Meeting Notes - Q3 Product Launch Planning
Date: March 28, 2026

Action Items:

1. Launch new marketing campaign for Q3 product release.
   Assigned to: Marketing team. Deadline: 5 days. Priority: high.

2. Submit Q3 budget report to finance department.
   Deadline: 3 days. Priority: high. Complexity: medium.

3. Conduct engineering review meeting for backend infrastructure.
   Assigned to: Engineering. Deadline: 7 days. Priority: medium.

4. Review and finalize vendor contracts for procurement.
   Deadline: 10 days. Priority: low. Complexity: low.

5. Prepare HR onboarding documents for new hires joining next week.
   Assigned to: HR department. Deadline: 2 days. Priority: critical.

6. Design UI mockups for new dashboard feature.
   Assigned to: Engineering. Deadline: 4 days. Priority: high. Complexity: high.

7. Conduct security audit on all active APIs.
   Assigned to: Engineering. Deadline: 14 days. Priority: medium. Complexity: high.

8. Send weekly performance report to management.
   Assigned to: Management. Deadline: 1 day. Priority: high. Complexity: low.


---
# DEMO ACCOUNTS

Email : manager@company.com
Password : manager123
Email : hod@company.com
Password : hod123
Email : employee@company.com
Password : employee123
   


---

## 🛠 Tech Stack
| Tier | Technology | Choice Rationale |
| :--- | :--- | :--- |
| **Logic** | **LangGraph** | Cycle-based agentic state management. |
| **Model** | **Llama 3.3 70B** | Fast, high-reasoning, open-source model. |
| **API** | **FastAPI** | High-performance, async, type-safe Python. |
| **UI** | **React + Vite** | Blazing fast frontend builds and reactivity. |
| **DB** | **Supabase** | Real-time PostgreSQL with built-in auth. |
| **Infra** | **Docker/K8s** | Reproducible environments and scaling. |

---

## 📂 Project Structure
- `backend/`: FastAPI server, LangGraph agents, and database routers.
- `frontend/`: React application with role-based dashboard components.
- `k8s/`: Kubernetes deployment manifests for production scaling.
- `nginx-lb.conf`: Configuration for the Nginx reverse proxy/load balancer.

---

## 🏆 Hackathon Details
- **Project Name**: FlowGuard AI
- **Track**: Track 2 — Autonomous Enterprise Workflows
- **Target**: ET Gen AI Hackathon 2026
