import asyncio
import os
import cognee
from dotenv import load_dotenv

load_dotenv()
os.environ["LLM_MODEL"] = os.environ.get("LLM_MODEL", "groq/llama-3.3-70b-versatile")
os.environ["LLM_PROVIDER"] = os.environ.get("LLM_PROVIDER", "custom")

async def debug_cognee():
    os.environ["COGNEE_SYSTEM_ROOT"] = "D:/hackathon projects/cognee/.data"
    cognee.config.system_root_directory("D:/hackathon projects/cognee/.data")
    
    # Let's see what's actually in the graph
    from cognee.infrastructure.databases.graph.get_graph_engine import get_graph_engine
    client = await get_graph_engine()
    nodes, edges = await client.get_graph_data()
    print(f"Total Nodes: {len(nodes)}")
    for n_id, data in nodes:
        if data.get("type") == "Fact" or "Alice" in str(data):
            print(f"Node {n_id}: {data}")

    print("\n--- Search Results ---")
    results = await cognee.search("Where did Alice move to in 2025?")
    for r in results:
        print(r)

if __name__ == "__main__":
    asyncio.run(debug_cognee())
