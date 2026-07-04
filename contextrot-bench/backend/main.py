import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
from dotenv import load_dotenv

load_dotenv()
os.environ["LLM_MODEL"] = os.environ.get("LLM_MODEL", "groq/llama-3.3-70b-versatile")
os.environ["LLM_PROVIDER"] = os.environ.get("LLM_PROVIDER", "custom")

import cognee
cognee.config.system_root_directory("D:/hackathon projects/cognee/.data")

from backend.pipeline_naive import ingest as ingest_naive, query as query_naive
from backend.pipeline_cognee import ingest as ingest_cognee, query as query_cognee
import shutil

app = FastAPI(title="ContextRot Bench API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class IngestRequest(BaseModel):
    facts: list[dict]

class QueryRequest(BaseModel):
    question: str

def clear_db():
    try:
        shutil.rmtree("D:/hackathon projects/cognee/.data")
    except Exception:
        pass

@app.post("/api/reset")
def reset_db():
    clear_db()
    return {"status": "ok"}

@app.post("/api/ingest")
def ingest_facts(req: IngestRequest):
    try:
        # We assume the database is cleared before the first ingest
        # or we append. For the demo, we just append to whatever is there.
        ingest_naive(req.facts)
        ingest_cognee(req.facts)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query/naive")
def ask_naive(req: QueryRequest):
    try:
        answer = query_naive(req.question)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query/cognee")
def ask_cognee(req: QueryRequest):
    try:
        answer = query_cognee(req.question)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/results")
def get_results():
    if not os.path.exists("frozen_results.json"):
        return {"error": "No benchmark results found. Run verify_pruning.py first."}
    with open("frozen_results.json", "r") as f:
        return json.load(f)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
