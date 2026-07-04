import os
import json
import shutil
import asyncio
from dotenv import load_dotenv

load_dotenv()
os.environ["LLM_MODEL"] = os.environ.get("LLM_MODEL", "groq/llama-3.3-70b-versatile")
os.environ["LLM_PROVIDER"] = os.environ.get("LLM_PROVIDER", "custom")

import cognee
db_root = "D:/hackathon projects/cognee/.data_benchmark"
os.environ["COGNEE_SYSTEM_ROOT"] = db_root
cognee.config.system_root_directory(db_root)

from backend.pipeline_naive import ingest as ingest_naive, query as query_naive
from backend.pipeline_cognee import ingest as ingest_cognee, query as query_cognee

SCENARIOS_DIR = os.path.join(os.path.dirname(__file__), "scenarios")

def clear_db():
    try:
        shutil.rmtree("D:/hackathon projects/cognee/.data")
    except Exception:
        pass
    try:
        shutil.rmtree("D:/hackathon projects/cognee/.venv/Lib/site-packages/cognee/.cognee_system")
    except Exception:
        pass

def evaluate_answer(answer: str, ground_truth: str, stale_values: list[str]) -> bool:
    answer_lower = answer.lower()
    
    # 1. Correct value MUST be present
    if ground_truth.lower() not in answer_lower:
        return False
        
    # 2. NO stale values can be present
    for stale in stale_values:
        if stale.lower() in answer_lower:
            return False
            
    return True

def run_benchmark():
    os.makedirs(SCENARIOS_DIR, exist_ok=True)
    scenario_files = [f for f in os.listdir(SCENARIOS_DIR) if f.endswith(".json")]
    
    results_path = os.path.join(os.path.dirname(__file__), "benchmark_results.json")
    results = {}
    
    if os.path.exists(results_path):
        try:
            with open(results_path, "r") as f:
                results = json.load(f)
            print(f"Loaded {len(results)} existing scenario results. Resuming...")
        except Exception:
            pass

    for filename in scenario_files:
        scenario_id = filename.replace(".json", "")
        if scenario_id in results:
            print(f"Skipping {scenario_id} (already evaluated)")
            continue
            
        with open(os.path.join(SCENARIOS_DIR, filename), "r") as f:
            scenario = json.load(f)
            
        print(f"\nEvaluating {scenario_id}...")
        
        # --- Run Pipeline B (Cognee) ---
        print("  -> Pipeline B (Cognee)")
        clear_db()
        cognee_error = None
        cognee_answer = ""
        
        try:
            ingest_cognee(scenario['facts'])
            cognee_answer = query_cognee(scenario['eval_question'])
        except Exception as e:
            cognee_error = str(e)
            
        answer = cognee_answer if not cognee_error else f"ERROR: {cognee_error}"
        score = evaluate_answer(answer, scenario['ground_truth_answer'], scenario['stale_values'])
        print(f"Score for {scenario_id}: {score}/1.0")
        
        results[scenario_id] = {
            "question": scenario['eval_question'],
            "expected_value": scenario['ground_truth_answer'],
            "stale_values": scenario['stale_values'],
            "system_answer": answer,
            "score": score
        }
        
        # Save checkpoint immediately
        with open(results_path, "w") as f:
            json.dump(results, f, indent=4)
            
    print("\n=== Benchmark Complete ===")
    total_score = sum(r["score"] for r in results.values())
    total_scenarios = len(results)
    if total_scenarios > 0:
        print(f"Final Score: {total_score} / {total_scenarios} ({total_score/total_scenarios*100:.1f}%)")
    
    return results

if __name__ == "__main__":
    run_benchmark()
