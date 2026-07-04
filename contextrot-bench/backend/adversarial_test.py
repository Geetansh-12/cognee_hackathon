import asyncio
import os
import shutil
import json
import cognee
from backend.pipeline_cognee import _pipeline
from backend.pipeline_naive import ingest as ingest_naive, query as query_naive

def clear_db():
    try:
        shutil.rmtree("D:/hackathon projects/cognee/.data_test6")
    except Exception:
        pass

async def main():
    print("\n--- Running Adversarial Tests ---")
    
    # 1. Setup the scenario
    # We will use user_location scenario, but inject a stable fact
    # and we will test paraphrasing and recency bias.
    
    scenario = {
        "id": "adversarial",
        "facts": [
            {"subject": "Alice", "predicate": "favorite color", "value": "Blue", "timestamp": "2020-01-01", "supersedes": None},
            {"subject": "Alice", "predicate": "lives in", "value": "New York", "timestamp": "2023-01-01", "supersedes": None},
            {"subject": "Alice", "predicate": "lives in", "value": "Chicago", "timestamp": "2024-06-15", "supersedes": "New York"},
            {"subject": "Alice", "predicate": "lives in", "value": "Seattle", "timestamp": "2025-09-20", "supersedes": "Chicago"}
        ]
    }
    
    print("\n[INGESTING NAIVE PIPELINE]")
    clear_db()
    ingest_naive(scenario["facts"])
    
    # Run Cognee Pipeline
    print("\n[INGESTING COGNEE PIPELINE]")
    clear_db()
    db_root = "D:/hackathon projects/cognee/.data_test6"
    os.environ["COGNEE_SYSTEM_ROOT"] = db_root
    cognee.config.system_root_directory(db_root)
    await _pipeline._ingest_async(scenario["facts"])
    
    queries = [
        {
            "name": "Case 1: Paraphrased Query",
            "q": "What city is Alice currently residing in?",
            "expected_truth": "Seattle",
            "should_naive_fail": True
        },
        {
            "name": "Case 2: Stable Fact Query",
            "q": "What is Alice's favorite color?",
            "expected_truth": "Blue",
            "should_naive_fail": False
        },
        {
            "name": "Case 3: Recency Bias (Naive might guess right by luck)",
            "q": "Where did Alice move to in 2025?",
            "expected_truth": "Seattle",
            "should_naive_fail": False  # Because the chunk literally says 2025, naive vector search will heavily favor this chunk over NY/Chicago
        }
    ]
    
    print("\n--- RUNNING QUERIES ---")
    for tc in queries:
        print(f"\n[{tc['name']}]")
        print(f"Query: {tc['q']}")
        
        # We need to run naive query synchronously
        naive_ans = query_naive(tc['q'])
        cognee_ans = await _pipeline._query_async(tc['q'])
        
        print(f"  Naive Answer:  {naive_ans}")
        print(f"  Cognee Answer: {cognee_ans}")
        
    print("\nAdversarial testing complete.")

if __name__ == "__main__":
    asyncio.run(main())
