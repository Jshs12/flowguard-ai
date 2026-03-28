from database.db import supabase
import uuid

def verify():
    with open("schema_final.txt", "w") as f:
        try:
            # Create a test user
            u_email = f"test_{uuid.uuid4().hex[:6]}@test.com"
            u_res = supabase.table('users').insert({
                'name': 'Test User',
                'email': u_email,
                'role': 'manager'
            }).execute()
            u_id = u_res.data[0]['id']
            f.write(f"User created: {u_id}\n")
            
            # Create a workflow
            wf_res = supabase.table('workflows').insert({
                'title': 'Test Workflow',
                'created_by': u_id
            }).execute()
            wf_id = wf_res.data[0]['id']
            f.write(f"Workflow created: {wf_id}\n")
            
            # Try a very safe task insert
            try:
                t_res = supabase.table('tasks').insert({'workflow_id': wf_id, 'title': 'Test Task', 'priority': 'medium', 'status': 'pending'}).execute()
                f.write(f"Task keys: {list(t_res.data[0].keys())}\n")
            except Exception as e:
                f.write(f"Task safe insert failed: {e}\n")
                
            # Try a very safe log insert
            try:
                l_res = supabase.table('audit_logs').insert({'workflow_id': wf_id, 'decision': 'Test Decision', 'confidence': 0.5}).execute()
                f.write(f"Log keys: {list(l_res.data[0].keys())}\n")
            except Exception as e:
                f.write(f"Log safe insert failed: {e}\n")

            # Cleanup
            supabase.table('users').delete().eq('id', u_id).execute()
            f.write("Cleanup successful\n")
        except Exception as e:
            f.write(f"FATAL ERROR: {e}\n")

if __name__ == "__main__":
    verify()
