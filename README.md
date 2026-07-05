# Cognee Hackathon Submission — ContextRot Bench + Open Source Contributions

## What We Built

### 1. ContextRot Bench — Proving Memory Hygiene Matters

Most "AI memory" demos show you adding facts. We built a benchmark 
that proves what happens when facts *change* — and quantifies 
the failure.

**The finding:** Cognee's `improve()` performs LLM-side 
reconciliation but does not physically delete stale data from 
the graph or vector store. A naive vector store and an unconfigured 
Cognee pipeline both hallucinate contradicted answers for the 
same reason: the stale facts are still there, in retrieval range.

**What we built on top:** A custom deep-pruning layer using 
Cognee's internal `get_graph_engine()` and `get_vector_engine()` 
clients to physically purge stale `Fact` nodes from both the 
Kuzu graph database and LanceDB vector store simultaneously, 
using structural subject+value matching to survive LLM predicate 
rephrasing during `cognify()`.

**Results across 15 adversarial fact-stream scenarios:**

| Pipeline | Accuracy |
|---|---|
| Naive Vector Store (LanceDB append-only) | 0% |
| Cognee + Custom Deep-Pruning Layer | 100% |

**Adversarial test (the result we're most proud of):**

> Query: "Where did Alice move to in 2025?"
> 
> Naive: "There is no information about Alice moving in 2025. 
> The context only provides multiple current locations."
>
> Cognee (pruned): "Seattle."

The naive pipeline couldn't infer the answer even with a year hint 
because the raw vector chunks lacked chronological structure. 
Cognee's graph, with stale nodes physically absent, had only one 
answer available.

**Discovery along the way:** Installing `fastembed` standalone is 
not sufficient — `cognee[fastembed]` (the plugin wrapper) is 
required. Without it, Cognee silently skips vector generation with 
no visible error, leaving an empty vector store. Documented in 
detail below.

---

### 2. Graphiti → Cognee Migration Tutorial (Submitted PR #3798)

Official tutorial for importing bi-temporal knowledge graphs from 
Graphiti into Cognee using the existing `GraphitiSource`.

- Sample dataset featuring `valid_at` / `invalid_at` temporal 
  metadata mapping to `COGXFact`
- Demonstrates how superseded (expired) facts are represented 
  during migration
- [Submitted PR #3798](https://github.com/topoteretes/cognee/pull/3798)

---

### 3. Mem0 → Cognee Migration Tutorial (Submitted PR #3847)

Official migration guide for importing Mem0 memories into Cognee's 
graph architecture.

- All three ingestion modes demonstrated: `preserve`, `re-derive`, 
  `hybrid` — with explanation of when to use each
- Explains why Mem0 memories land as `COGXMemory` rather than 
  `COGXFact` — a distinction that matters for downstream graph 
  traversal
- [Submitted PR #3847](https://github.com/topoteretes/cognee/pull/3847)

---

## Key Technical Findings

| Finding | Impact |
|---|---|
| `improve()` does LLM reconciliation, not physical deletion | Built custom dual-store pruning layer |
| `cognee[fastembed]` plugin required, not just `fastembed` | Silent failure mode now documented |
| LLM rephrases predicates during `cognify()` | Pruning uses subject+value matching, not predicate string match |
| Graph node deletion doesn't cascade to vector store | Both stores must be pruned independently |

---

## How to Run

### ContextRot Bench

```bash
git clone https://github.com/Geetansh-12/cognee_hackathon.git
cd contextrot-bench
pip install -r requirements.txt
cp .env.template .env  # add your Groq API key

# Terminal 1 — backend
python backend/main.py

# Terminal 2 — frontend  
cd frontend && npm run dev
# Open http://localhost:5173
```

The dashboard loads the frozen benchmark results (`frozen_results.json`) 
instantly — no API calls needed to see the numbers. The live 
two-panel demo makes one Groq API call per query.

### Migration Tutorials (in the Cognee repo)

```bash
uv pip install cognee
uv run python examples/tutorials/migrate_from_graphiti_tutorial.py
uv run python examples/tutorials/migrate_from_mem0_tutorial.py
```

---

## What Cognee Does Natively vs. What We Built

| Layer | Cognee Out-of-the-Box | What We Added |
|---|---|---|
| Ingestion | `add()` → `cognify()` with LLM extraction | Custom `Fact` DataPoint schema with `supersedes` field |
| Contradiction handling | `improve()` adds resolution edges | Physical deletion from Kuzu graph + LanceDB vector store |
| Predicate matching | N/A | Subject+value structural matching to survive LLM rephrasing |
| Verification | None | `verify_pruning.py` — end-to-end graph+vector pruning proof |

---

*Built for the WeMakeDevs × Cognee Hackathon. 
Blog: [Read the Blog Post on Dev.to](https://dev.to/geetansh_vikram_836d7f761/i-had-never-heard-of-cognee-then-i-spent-5-days-breaking-it-wide-open-4j0j) | Demo video: [ContextRot-Bench Demo on YouTube](https://youtu.be/FW6hriWAz40?si=oAQuVVhegkSAwJ4F)*
