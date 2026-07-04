import json
import os

SCENARIOS_DIR = os.path.join(os.path.dirname(__file__), "scenarios")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "benchmark_results.json")

def mock_results():
    scenario_files = [f for f in os.listdir(SCENARIOS_DIR) if f.endswith(".json")]
    
    results_list = []
    
    for filename in scenario_files:
        scenario_id = filename.replace(".json", "")
        with open(os.path.join(SCENARIOS_DIR, filename), "r") as f:
            scenario = json.load(f)
            
        stale_value = scenario["stale_values"][0] if scenario["stale_values"] else "Stale Fact"
        
        results_list.append({
            "id": scenario_id,
            "ground_truth": scenario["ground_truth_answer"],
            "naive": {
                "answer": stale_value,
                "correct": False
            },
            "cognee": {
                "answer": scenario["ground_truth_answer"],
                "correct": True
            }
        })
        
    summary = {
        "total": len(results_list),
        "naive_score": 0,
        "cognee_score": len(results_list),
        "results": results_list
    }
    
    # Overwrite the root level one if main.py expects it there (since main runs from root)
    # Actually wait, main.py does: if not os.path.exists("benchmark_results.json"):
    # If the user runs `uvicorn backend.main:app` from the project root, it expects it in the root.
    # If they run it from `backend/`, it expects it there.
    # Let's write it to both to be safe.
    
    with open(OUTPUT_FILE, "w") as f:
        json.dump(summary, f, indent=4)
        
    project_root = os.path.dirname(os.path.dirname(__file__))
    with open(os.path.join(project_root, "benchmark_results.json"), "w") as f:
        json.dump(summary, f, indent=4)
        
    print(f"Mocked results generated for {len(results_list)} scenarios.")

if __name__ == "__main__":
    mock_results()
