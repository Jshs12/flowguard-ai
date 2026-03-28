from agents.graph import run_pipeline
import traceback

def test_pipeline():
    transcript = "Deploy new marketing campaign. Prepare budget allocation. Finalize vendor list."
    print("Running pipeline...")
    try:
        result = run_pipeline(transcript)
        print("Pipeline finished successfully.")
        import json
        # Remove transcript for brevity
        debug_res = {k: v for k, v in result.items() if k != 'transcript'}
        print(f"Result structure: {json.dumps(debug_res, indent=2)}")
    except Exception as e:
        print(f"PIPELINE FAILED: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_pipeline()
