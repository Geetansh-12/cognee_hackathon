# 🚀 Cognee Open-Source Contributions (Hackathon Submission)

Welcome to our hackathon submission! For this event, we chose to make deep, high-impact contributions to **[Cognee](https://github.com/topoteretes/cognee)**, an open-source AI Memory platform that provides persistent long-term memory for AI agents using knowledge graphs and vector databases.

Instead of building a simple wrapper app, we dove into the core of the Cognee SDK to build rigorous benchmarks and critical migration pipelines that will be used by the broader developer community.

## 🌟 What We Built

### 1. Robust Pruning Engine Verification & Benchmarks
We engineered a chunk-granularity verification suite for Cognee's memory pruning system. We designed and ran 15 complex, cross-entity test scenarios (e.g., verifying that deleting a fact about Alice doesn't accidentally prune adjacent semantic facts about Bob when they share the same ingestion chunk). 
- **Impact**: We proved that Cognee's graph and vector deletion logic is non-destructive to collateral data, resulting in a frozen, highly defensible test artifact that locks in the system's reliability metrics.

### 2. Graphiti to Cognee Migration Pipeline & Tutorial (Merged/PR)
We built the official tutorial demonstrating how to import bi-temporal knowledge graphs from **Graphiti** into Cognee.
- Created a realistic sample dataset featuring temporal metadata (`valid_at` / `invalid_at`).
- Mapped Graphiti episodes and entities directly onto Cognee's `COGXFact` ontology.
- **[View the PR #3798 on the main Cognee Repo](https://github.com/topoteretes/cognee/pull/3798)**

### 3. Mem0 to Cognee Migration Pipeline & Tutorial (Merged/PR)
We developed the official migration guide for importing **Mem0** memories into Cognee's graph architecture.
- Demonstrated three distinct ingestion modes: `preserve` (direct node mapping), `re-derive` (LLM-driven re-extraction), and `hybrid`.
- Detailed how Mem0 structures uniquely map to `COGXMemory` rather than generic facts, preserving user context and episodic categories.
- **[View the PR #3847 on the main Cognee Repo](https://github.com/topoteretes/cognee/pull/3847)**

---

## 💻 How to Run Our Work

If you'd like to test our tutorial scripts locally, you can run them directly from the `examples/tutorials/` directory in this repository.

### Prerequisites
1. Ensure you have Python 3.10+ installed.
2. Clone this repository and install dependencies using `uv` or `pip`:
   ```bash
   uv pip install cognee
   ```
3. Set up your environment variables (copy `.env.template` to `.env` and add your LLM API keys).

### Running the Graphiti Migration Tutorial
```bash
uv run python examples/tutorials/migrate_from_graphiti_tutorial.py
```
This script will prune the system, load our sample Graphiti dump, cognify the data, and run semantic queries to prove the relationships were preserved.

### Running the Mem0 Migration Tutorial
```bash
uv run python examples/tutorials/migrate_from_mem0_tutorial.py
```
This script demonstrates the `preserve` ingestion mode for Mem0, mapping episodic and factual memories directly into the graph before querying them.

---

*This repository is a snapshot of our contributions during the hackathon. The original Cognee framework can be found at [topoteretes/cognee](https://github.com/topoteretes/cognee).*
