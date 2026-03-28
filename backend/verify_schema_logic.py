from database.db import supabase
import sys

def verify():
    with open("schema_verify.txt", "w") as f:
        f.write("DEBUG SCHEMA VERIFY\n")
        try:
            user_id = supabase.table('users').select('id').limit(1).execute().data[0]['id']
            wf = supabase.table('workflows').insert({'title':'schema_test', 'created_by':user_id}).execute().data[0]
            wf_id = wf['id']
            f.write(f"Workflow created: {wf_id}\n")
            
            # Test 1: Minimal insert to see NOT NULL columns
            try:
                supabase.table('audit_logs').insert({'workflow_id': wf_id}).execute()
            except Exception as e:
                f.write(f"Test 1 error (expected NOT NULL): {e}\n")
            
            # Test 2: Try 'agent'
            try:
                res = supabase.table('audit_logs').insert({'workflow_id': wf_id, 'agent': 'test', 'decision': 'test', 'confidence': 0.5}).execute()
                f.write(f"Test 2 success! columns: {res.data[0].keys()}\n")
            except Exception as e:
                f.write(f"Test 2 error ('agent'): {e}\n")

            # Cleanup
            supabase.table('workflows').delete().eq('id', wf_id).execute()
        except Exception as e:
            f.write(f"OUTER ERROR: {e}\n")

if __name__ == "__main__":
    verify()
