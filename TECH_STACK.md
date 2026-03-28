# Technology Stack — FlowGuard AI

FlowGuard AI was built with a selection of technologies that prioritize performance, developer productivity, and state-of-the-art AI capabilities.

## Layer Breakdown

### Backend: FastAPI & Python
*   **Why**: FastAPI was chosen for its exceptional performance (using `uvicorn` and `starlette`) and its native support for asynchronous programming, which is critical for handling long-running AI agent pipelines without blocking the event loop.
*   **Benefits**: Automatic OpenAPI documentation, Pydantic type safety, and a massive ecosystem of production-grade libraries.

### Orchestration: LangGraph
*   **Why**: Unlike simple LLM chains, multi-agent systems require complex state management and cyclic flows (loops). LangGraph provides a robust framework to build "stateful" multi-agent applications.
*   **Benefits**: Built-in persistence for agent states and fine-grained control over the decision-making flow.

### Intelligence: Groq LLM (Llama 3.3 70B)
*   **Why**: Groq's LPU (Language Processing Unit) architecture offers inference speeds that are significantly faster than traditional cloud providers. Llama 3.3 70B provides GPT-4 level reasoning for extraction and assignment tasks.
*   **Benefits**: Near-instantaneous response times, strong structural reasoning (JSON output), and excellent performance for PII handling.

### Data Layer: Supabase
*   **Why**: Supabase provides "Firebase-like" speed of development with the robustness of PostgreSQL. It handles our authentication, relational data, and real-time updates through a single unified client.
*   **Benefits**: Built-in row-level security (RLS), real-time database listeners, and effortless scaling.

### Frontend: React + Vite
*   **Why**: Vite offers a lightning-fast development experience and optimized production builds. React's component-based architecture allows us to build complex dashboards (Manager vs. Employee) with reusable UI modules.
*   **Benefits**: shadcn/ui integration for premium aesthetics and robust state management for real-time task updates.

### Infrastructure: Docker & Kubernetes
*   **Why**: To ensure "it works on my machine" translates to "it works in production." Docker containerizes our 3-tier system, and Kubernetes provides the orchestration needed for auto-healing and scaling.
*   **Benefits**: Consistent environments, high availability, and easier CI/CD integration.

---

## "Why Not?" — Rejected Alternatives
*   **OpenAI (GPT-4)**: While powerful, the latency and per-token cost were less favorable for a system that processes dozens of meeting transcripts daily. Groq + Llama 3 offered comparable reasoning at a fraction of the cost and time.
*   **Firebase**: We rejected Firebase because enterprise workflows are inherently relational (Users ↔ Tasks ↔ Audits). PostgreSQL (via Supabase) provides the join support and ACID compliance needed for reliable workflow tracking.
*   **Flask**: Lacked native async support and a built-in dependency injection system, making it less suitable for a modern AI-centric backend compared to FastAPI.
*   **Vue**: While excellent, React was chosen due to the team's deep familiarity and the vast ecosystem of data-visualization libraries needed for the performance dashboard.

## AI Model Selection
We selected **Llama 3.3 70B** running on Groq specifically for:
1.  **JSON Precision**: It consistently follows the extraction schema without "hallucinating" extra text.
2.  **Latency**: In a workplace tool, users expect results in seconds, not minutes. Groq's sub-second inference is the only technology that enables this "real-time" feel.
3.  **Reasoning Depth**: Unlike smaller models (8B class), the 70B model correctly understands nuances in priority (e.g., "this should be done as soon as we finish X" vs. "this is a priority for next quarter").
