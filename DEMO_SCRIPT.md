# Hackathon Demo Script — FlowGuard AI

## 🎬 30-Second Opening Pitch
"Good afternoon, judges. Every day, thousands of critical enterprise decisions are lost in the abyss of unstructured meeting data. Teams spend hours talking, but rely on manual, error-prone entry to turn those words into work. 

Meet **FlowGuard AI** — an autonomous multi-agent intelligence system that doesn't just record your meetings; it understands them. It extracts action items, masks sensitive data, and intelligently assigns tasks based on real-time performance metrics and workload. It’s not just project management; it’s the brain of your enterprise operations. Let’s see it in action."

---

## 🛠 Live Demo Steps

| Step | Action | Script Points |
| :--- | :--- | :--- |
| **1. Login** | Login as `manager@company.com` | "I'm entering the system as a Manager. Notice the clean, high-performance dashboard." |
| **2. Input** | Paste the 'Sample Transcript' (below) | "I'll paste the rough notes from our morning sync. No formatting needed." |
| **3. Process** | Click 'Process Meeting' | "Now, our multi-agent pipeline is firing. Agent 1 is masking PII; Agent 2 is generating tasks; Agent 3 is looking for the best assignee." |
| **4. Observe** | Show the Tasks Table | "Look here — tasks are already assigned. Note the 'Priority' and 'Risk' columns. The AI identified the Security Patch as Critical." |
| **5. Audit** | Click 'View Audit Trail' | "Transparency is key. We can see exactly why the Assignment Agent chose 'Bob' over 'Alice' based on efficiency scores." |
| **6. Sim** | Click 'What-If Simulation' | "If this task is delayed by 2 days, the system predicts a 40% increase in project risk. No more guessing." |
| **7. Employee**| Logout/Login as `employee@company.com` | "Now, switching to the employee view. I only see what's on my plate." |
| **8. Finish** | Click '✓ Complete' on a task | "As I complete this, notice the notification. My performance score is being recalibrated in real-time." |

---

## 📄 Sample Meeting Transcript
"Internal Security Sync — March 28, 2026.
Attendees: Alice (Head), Bob (Manager), Charlie (Dev), Dave (Dev).

Alice: Charlie, we need to deploy the security patch for the auth module before the 6 PM deployment today. This is critical.
Bob: Dave, can you prepare the quarterly budget report? We need it by Friday. Medium priority.
Alice: Dave, also review the legal terms for the new vendor. 
Charlie: I'll also update the API documentation next week. Low priority.
Bob: Lastly, Charlie, please finalize the AWS migration plan by tomorrow morning."

---

## ❓ Judge Q&A
1.  **Q: How do you prevent LLM hallucinations?**
    *   *A: We use a multi-agent validation loop where the Task Generation Agent verifies the output of the Extraction Agent against a strict schema.*
2.  **Q: Is the data secure?**
    *   *A: Absolutely. We implement local PII masking so sensitive names/emails never leave our secure infrastructure when calling external APIs.*
3.  **Q: What if the AI assigns a task to the wrong person?**
    *   *A: Managers have 'Human-in-the-Loop' override capability. Any manual change also retrains the AI's understanding of that user's role.*
4.  **Q: Does it support integrations like Slack or Jira?**
    *   *A: The architecture is built on a standard REST API, making it easy to pipe these autonomous tasks directly into Jira, Slack, or Trello via webhooks.*
5.  **Q: How does the performance score work?**
    *   *A: It's a weighted formula measuring completion rate, speed against SLAs, and historical reliability. It prevents burnout by avoiding overloaded employees.*
...[etc]

## 🏗 Technical Deep Dive
If judges ask about the stack:
- **Agents**: "We use LangGraph to maintain state across the 5 agents. This allows us to handle complex dependencies that linear pipelines can't."
- **Speed**: "By using Groq, we achieve inference speeds 10x faster than standard GPT-4 calls, enabling a seamless real-time experience."
- **DB**: "Supabase gives us relational integrity with real-time capabilities, ensuring the manager's dashboard updates the moment an employee finishes a task."
