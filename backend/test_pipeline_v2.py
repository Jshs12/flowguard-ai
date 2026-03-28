
import os, sys
import uuid
from typing import Dict, Any

# Mock state and nodes to test logic
sys.path.append(os.path.join(os.getcwd(), "backend"))
from agents.nodes import extraction_agent, task_generation_agent, assignment_agent

def test_agents():
    print("=== Testing Agent Pipeline ===")
    
    # 1. Test Extraction Agent
    state = {
        "transcript": "We need to deploy the new auth module for the engineering team by tomorrow. It is a critical task. Also, update the marketing plan next week, medium priority.",
        "logs": []
    }
    
    print("\n--- Running Extraction Agent ---")
    state = extraction_agent(state)
    
    assert "actionitems" in state
    assert "rawextracted" in state
    assert len(state["actionitems"]) > 0
    print(f"Extraction successful: {len(state['actionitems'])} tasks found.")
    
    # 2. Test Task Generation Agent
    print("\n--- Running Task Generation Agent ---")
    state = task_generation_agent(state)
    
    assert "tasks" in state
    assert len(state["tasks"]) > 0
    
    for task in state["tasks"]:
        print(f"Task Generated: {task['title']} | Dept: {task['department']} | Prio: {task['priority']} | SLA: {task['sla_days']}")
        # Verify preservation
        assert "priority" in task
        assert "department" in task
        assert "sla_days" in task
    
    # 3. Test Assignment Agent
    print("\n--- Running Assignment Agent ---")
    # We might need to mock get_available_employees or ensure the DB has some users
    # For this test, we'll just check if it runs without crashing and logs logic
    state = assignment_agent(state)
    
    print("\n--- Final State Logs ---")
    for log in state["logs"]:
        print(f"[{log['agent_name']}] {log['action']}")

if __name__ == "__main__":
    try:
        test_agents()
        print("\n✅ All tests passed (Logic check)!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
