import asyncio
import os
import litellm
import cognee
from typing import List, Dict, Any
from .models import Fact

class CogneePipeline:
    def __init__(self):
        # We need an asyncio loop for Cognee API which is fully async
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
    async def _ingest_async(self, fact_stream: List[Dict[str, Any]]):
        # We need to process facts in order
        from cognee.infrastructure.databases.graph.get_graph_engine import get_graph_engine
        
        for i, fact_dict in enumerate(fact_stream):
            if i > 0:
                print(f"Pacing ingestion: sleeping for 5s to avoid free-tier API rate limits...")
                import asyncio
                await asyncio.sleep(5)
            
            # 1. Custom Deep-Pruning Layer
            if "supersedes" in fact_dict and fact_dict["supersedes"]:
                print(f"Deep-Pruning Triggered: Searching for '{fact_dict['subject']}' / '{fact_dict['predicate']}' to delete '{fact_dict['supersedes']}'")
                try:
                    graph_client = await get_graph_engine()
                    nodes, edges = await graph_client.get_graph_data()
                    
                    old_fact_node_id = None
                    # Step 1a: Find exact Node ID matching structurally
                    for n_id, n_data in nodes:
                        if n_data.get("type") == "Fact":
                            # Use robust matching: LLMs often rephrase predicates (e.g. 'lives in' -> 'location')
                            # The combination of Subject + Superseded Value is unique enough to identify the stale fact.
                            if str(n_data.get("subject")).lower() == str(fact_dict["subject"]).lower():
                                if str(n_data.get("value")).lower() == str(fact_dict["supersedes"]).lower():
                                    old_fact_node_id = n_id
                                    break
                    
                    if old_fact_node_id:
                        print(f"  -> Found stale Fact node ID: {old_fact_node_id}")
                        
                        # Step 1b: Find associated TextSummary node to get the Vector Chunk ID
                        chunk_ids_to_delete = []
                        text_summary_node_id = None
                        for src, tgt, rel, props in edges:
                            if tgt == old_fact_node_id:  # Usually extracted_from relationship
                                for n_id, n_data in nodes:
                                    if n_id == src and n_data.get("type") == "TextSummary":
                                        text_summary_node_id = n_id
                                        chunk_id = n_data.get("source_chunk_id")
                                        if chunk_id:
                                            chunk_ids_to_delete.append(chunk_id)
                                        break
                                        
                        # Step 1c: Delete from Graph Database
                        print(f"  -> Deleting Fact node from Graph...")
                        await graph_client.delete_node(old_fact_node_id)
                        if text_summary_node_id:
                            await graph_client.delete_node(text_summary_node_id)
                            
                        # Step 1c: Delete from Vector Database (LanceDB)
                        try:
                            import lancedb
                            import glob
                            db_root = os.environ.get("COGNEE_SYSTEM_ROOT", ".data")
                            lance_paths = glob.glob(f"{db_root}/databases/*/*.lance.db")
                            db_path = lance_paths[0] if lance_paths else None
                            if db_path and os.path.exists(db_path):
                                db = lancedb.connect(db_path)
                                for table_name in db.table_names():
                                    table = db.open_table(table_name)
                                    try:
                                        df = table.search().limit(1000).to_pandas()
                                        if 'payload' in df.columns:
                                            for idx, row in df.iterrows():
                                                text = str(row['payload'].get('text', ''))
                                                if fact_dict['subject'] in text and fact_dict['supersedes'] in text:
                                                    chunk_id = row['id']
                                                    print(f"  -> Deleting specific Vector Chunk ID: {chunk_id} from {table_name}")
                                                    table.delete(f"id = '{chunk_id}'")
                                    except Exception:
                                        pass
                            print("  -> Vector pruning complete.")
                        except Exception as ve:
                            import logging
                            logging.critical(f"PARTIAL DELETE FATAL ERROR: Graph pruned, but Vector delete failed: {ve}")
                            raise RuntimeError(f"Inconsistent State: Vector prune failed after graph prune. {ve}")
                except Exception as e:
                    print(f"Pruning failed: {e}")

            # 2. Ingest the new fact
            text = f"At {fact_dict['timestamp']}, {fact_dict['subject']} {fact_dict['predicate']} was {fact_dict['value']}."
            # We don't need the string "supersedes" anymore because we physically prune!
            
            await cognee.add([text])
            await cognee.cognify(graph_model=Fact)
            
        # After stream ingestion, run improve to solidify the remaining graph
        try:
            await cognee.improve()
        except Exception:
            pass
            
    def ingest(self, fact_stream: List[Dict[str, Any]]) -> None:
        self.loop.run_until_complete(self._ingest_async(fact_stream))

    async def _query_async(self, question: str) -> str:
        # cognee.search usually returns a list of results
        results = await cognee.search(question)
        
        # Format results into context
        context_parts = []
        for r in results:
            context_parts.append(str(r))
        context = "\n".join(context_parts)
        
        from tenacity import retry, stop_after_attempt, wait_exponential
        
        @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=10))
        def call_llm():
            return litellm.completion(
                model=os.getenv("LLM_MODEL", "groq/llama3-8b-8192"),
                messages=[
                    {"role": "system", "content": "You are a helpful assistant. Answer the question based ONLY on the provided context. Be concise."},
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
                ]
            )

        # Use the same LLM logic as naive
        try:
            response = call_llm()
            return response.choices[0].message.content
        except Exception as e:
            return f"Context:\n{context}\n\n(LLM Error: {e})"

    def query(self, question: str) -> str:
        return self.loop.run_until_complete(self._query_async(question))

_pipeline = CogneePipeline()

def ingest(fact_stream: List[Dict[str, Any]]) -> None:
    _pipeline.ingest(fact_stream)

def query(question: str) -> str:
    return _pipeline.query(question)
