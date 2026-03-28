# Architecture Overview — FlowGuard AI

## System Overview
FlowGuard AI follows a robust 3-layer architecture designed for scalability, security, and agentic intelligence.

1.  **Presentation Layer**: A React-based SPA (Single Page Application) built with Vite and designed for real-time responsiveness. It provides specialized interfaces for different organizational roles.
2.  **Application Layer**: A FastAPI-based backend that handles orchestrating the LangGraph agent pipeline, authentication via JWT, and business logic execution.
3.  **Data Layer**: Powered by Supabase, providing a PostgreSQL relational database for structured data, real-time subscriptions, and secure storage for audit logs and system state.

## Agent Pipeline Deep Dive
The core logic resides in a 5-step serialized agentic flow:

```text
[Transcript Input]
        ↓
(Agent 1: Extraction) ── Uses Groq LLM to parse unstructured text into JSON "Action Items".
        ↓
(Agent 2: Task Gen)   ── Validates metadata and ensures each item has priority/complexity.
        ↓
(Agent 3: Assignment) ── Queries Supabase for active users; runs efficiency ranking engine.
        ↓
(Agent 4: Monitoring) ── Calculates SLA risk using (Current Time - Deadline) vs (User Avg Completion).
        ↓
(Agent 5: Escalation) ── Flags high-risk tasks for manager review or automatic splitting.
```

## PII Masking Flow
To ensure data privacy when using external LLMs (Groq), FlowGuard implements a zero-trust masking flow:
1.  **Identification**: Regex-based patterns detect names, emails, and sensitive identifiers in the raw transcript.
2.  **Masking**: Identifiers are replaced with placeholders (e.g., `[PERSON_1]`, `[EMAIL_1]`).
3.  **Context Retention**: A mapping dictionary is stored locally in the agent's state.
4.  **Processing**: The LLM processes the *masked* text to identify tasks.
5.  **Unmasking**: The resulting JSON tasks are unmasked using the local dictionary before being saved to the database.

## Smart Assignment Algorithm
The `Assignment Agent` uses a multi-tier decision tree to ensure the right task reaches the right person:
1.  **Filter**: Identifies employees in the target department with `availability_status = 'active'`.
2.  **Fallback**: If no department match is found, filters all active employees.
3.  **Efficiency Calculation**: Scans historical `performance_score` and `current_workload`.
4.  **Strategy**:
    *   **High Priority**: Sorts candidates primarily by `efficiency` (Performance + Speed).
    *   **Standard Priority**: Sorts candidates primarily by `workload` (Load Balance).
5.  **Execution**: Assigns `user_id` to the task and logs the "why" in the `audit_trail`.

## Performance Scoring System
Employee scores are not static; they evolve with every action:
*   **Completion Rate (50%)**: Ratio of finished vs. assigned tasks.
*   **Speed Score (30%)**: Scaled based on how many hours/days before the deadline the task was finished.
*   **Reliability (20%)**: Percentage of tasks completed without SLA breaches.
*   **Update Trigger**: Triggered automatically via `api/tasks/{id}/complete`.

## Task Splitting Logic
When the system detects a high-risk scenario (`risk > 0.7` or `deadline < 24h`), it triggers decomposition:
1.  **Triggers**: Monitoring Agent flags risk; Escalation Agent recommends split.
2.  **Decomposition**: The task is split into manageable sub-tasks (Planning, Exec, Testing).
3.  **Helper Selection**: The system looks for the least-busy active employee in the same department as a "helper".
4.  **Approval**: The helper receives a Split Request notification to join the task.

## Database Schema
*   **users**: `id, full_name, department, performance_score, current_workload`
*   **tasks**: `id, title, status, priority, risk_score, sla_deadline, assigned_to`
*   **workflows**: `id, title, raw_input, processed_at`
*   **audit_logs**: `id, task_id, agent, decision, reasoning, confidence`
*   **leave_requests**: `id, user_id, start_date, end_date, status`

## Infrastructure
*   **Docker Compose**: Orchestrates `flowguard-backend`, `flowguard-frontend`, and `flowguard-lb` (Nginx).
*   **Nginx**: Acts as a reverse proxy and load balancer, handling SSL termination and static file serving.
*   **Kubernetes**: Provides YAML definitions for deployments, services, and secrets for production-grade scaling.

## Security
*   **Auth**: JWT-based stateless authentication with secure cookie storage.
*   **RBAC**: Strict role-based decorators (`allow_manager_plus`, `allow_head`) on all REST endpoints.
*   **Integrity**: SHA-256 with salt for password hashing (via Passlib).
*   **Privacy**: PII masking ensures no sensitive enterprise data is leaked to LLM providers.
