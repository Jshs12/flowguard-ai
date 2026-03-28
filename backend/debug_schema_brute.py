from database.db import supabase
import traceback

def brute_force_schema():
    print("Fetching valid user_id...")
    user_id = supabase.table('users').select('id').limit(1).execute().data[0]['id']
    
    print("Creating temporary workflow...")
    wf = supabase.table('workflows').insert({'title':'schema_test', 'created_by':user_id}).execute().data[0]
    wf_id = wf['id']
    
    potential_columns = ['agent', 'agent_name', 'node_name', 'agent_id', 'actor']
    found_col = None
    
    for col in potential_columns:
        print(f"Testing column: '{col}'...")
        try:
            supabase.table('audit_logs').insert({
                'workflow_id': wf_id,
                col: 'test_agent',
                'decision': 'test_decision',
                'confidence': 0.5
            }).execute()
            print(f"SUCCESS! Column is '{col}'")
            found_col = col
            break
        except Exception as e:
            print(f"FAILED '{col}': {e}")
            
    # Cleanup
    print("Cleaning up...")
    supabase.table('workflows').delete().eq('id', wf_id).execute()
    
    if found_col:
        print(f"\nFINAL RESULT: The audit_logs agent column is '{found_col}'")
    else:
        print("\nFINAL RESULT: Could not find the agent column. Check for non-null constraints on other columns.")

if __name__ == "__main__":
    brute_force_schema()
