from database.db import supabase
import sys

def debug():
    with open("error_final_debug.txt", "w") as f:
        try:
            user_id = supabase.table('users').select('id').limit(1).execute().data[0]['id']
            wf = supabase.table('workflows').insert({'title':'debug_wf', 'created_by':user_id}).execute().data[0]
            wf_id = wf['id']
            f.write(f"Workflow ID: {wf_id}\n")
            
            # Test tasks
            f.write("\n--- Testing Tasks ---\n")
            task_test = {'workflow_id':wf_id, 'title':'test'}
            try:
                res = supabase.table('tasks').insert(task_test).execute()
                f.write(f"Task keys: {list(res.data[0].keys())}\n")
            except Exception as e:
                f.write(f"Task error: {e}\n")

            # Test logs
            f.write("\n--- Testing Logs ---\n")
            log_test = {'workflow_id':wf_id, 'decision':'test', 'confidence':0.5, 'agent':'test'}
            try:
                res = supabase.table('audit_logs').insert(log_test).execute()
                f.write(f"Log keys: {list(res.data[0].keys())}\n")
            except Exception as e:
                f.write(f"Log error: {e}\n")

            # Cleanup
            supabase.table('workflows').delete().eq('id', wf_id).execute()
        except Exception as e:
            f.write(f"OUTER ERROR: {e}\n")

if __name__ == "__main__":
    debug()
