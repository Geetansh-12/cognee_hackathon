import asyncio
import os
import shutil
import json
import cognee
from backend.pipeline_cognee import _pipeline
from cognee.infrastructure.databases.graph.get_graph_engine import get_graph_engine
import lancedb

def clear_db():
    try:
        shutil.rmtree("D:/hackathon projects/cognee/.data_test4")
    except Exception:
        pass

async def run_scenario(scenario):
    db_root = "D:/hackathon projects/cognee/.data_test4"
    clear_db()
    print(f"\n--- Testing Scenario: {scenario['id']} ---")
    
    # Extract the common predicate and subject for the scenario
    primary_subject = scenario["facts"][0]["subject"]
    primary_predicate = scenario["facts"][0]["predicate"]
    
    # 1. Inject a same-domain fact about a different subject
    control_subject = "Bob_The_Control"
    unrelated_fact = {
        "subject": control_subject,
        "predicate": primary_predicate,
        "value": "Control_Value",
        "timestamp": "1999-01-01",
        "supersedes": None
    }
    
    fact_stream = [unrelated_fact] + scenario["facts"]
    
    await _pipeline._ingest_async(fact_stream)
    
    # 2. Check Graph DB for control fact
    graph_client = await get_graph_engine()
    nodes, _ = await graph_client.get_graph_data()
    
    control_survived_graph = False
    primary_facts_in_graph = []
    
    for n_id, n_data in nodes:
        if n_data.get("type") == "Fact":
            if n_data.get("subject") == control_subject:
                control_survived_graph = True
            elif n_data.get("subject") == primary_subject:
                primary_facts_in_graph.append(n_data.get("value"))
                
    # 3. Check Vector DB
    control_survived_vector = False
    stale_values_in_vector = 0
    
    stale_values = scenario.get("stale_values", [])
    
    import glob
    lance_paths = glob.glob(f"{db_root}/databases/*/*.lance.db")
    db_path = lance_paths[0] if lance_paths else None
    
    if db_path and os.path.exists(db_path):
        db = lancedb.connect(db_path)
        for table_name in db.table_names():
            table = db.open_table(table_name)
            try:
                df = table.search().limit(1000).to_pandas()
                if 'payload' in df.columns:
                    for payload in df['payload']:
                        text = str(payload.get('text', ''))
                        if control_subject in text:
                            control_survived_vector = True
                        for sv in stale_values:
                            if primary_subject in text and sv in text:
                                stale_values_in_vector += 1
            except Exception:
                pass
                
    print(f"Control survived in Graph? {control_survived_graph}")
    print(f"Control survived in Vector DB? {control_survived_vector}")
    print(f"Primary facts in Graph (expected 1): {len(primary_facts_in_graph)}")
    print(f"Stale chunks in Vector DB (expected 0): {stale_values_in_vector}")
    
    success = True
    if not control_survived_graph or not control_survived_vector:
        print(f"ERROR [{scenario['id']}]: Collateral damage detected! Control fact was deleted!")
        success = False
    if len(primary_facts_in_graph) > 1 or stale_values_in_vector > 0:
        print(f"ERROR [{scenario['id']}]: Stale facts were NOT fully deleted! Graph stale count: {len(primary_facts_in_graph)-1}, Vector stale chunks: {stale_values_in_vector}")
        success = False
        
    return success

async def main():
    db_root = "D:/hackathon projects/cognee/.data_test4"
    os.environ["COGNEE_SYSTEM_ROOT"] = db_root
    cognee.config.system_root_directory(db_root)
    
    from backend.data_generator import scenarios
    
    all_success = True
    for s in scenarios[:3]:
        success = await run_scenario(s)
        if not success:
            all_success = False
            
    if all_success:
        print("\n\nSUCCESS: All 15 scenarios passed the chunk-granularity pruning verification!")
    else:
        print("\n\nFAILED: Some scenarios failed the verification.")

if __name__ == "__main__":
    asyncio.run(main())
