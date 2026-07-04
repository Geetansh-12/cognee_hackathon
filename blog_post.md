# I Had Never Heard of Cognee. Then I Spent 5 Days Breaking It Wide Open.

*By Geetansh Vikram Singh | WeMakeDevs × Cognee Hackathon*

---

I want to be honest with you from the first line: when I saw "WeMakeDevs × Cognee Hackathon," I had to Google what Cognee was.

I'm a third-year CSE student at NIT Silchar. I spend most of my time grinding competitive programming problems, building Android apps, and occasionally doing something reckless like fine-tuning a 1.5B parameter RL model for a hackathon. I knew what vector stores were. I knew what knowledge graphs were. But "memory layer for AI agents"? I read the landing page three times before it clicked.

And then it *really* clicked. And I couldn't stop.

> 🎬 [Watch the 2-minute demo video here](YOUR_VIDEO_LINK_HERE)

---

## The Moment I Got Hooked

The hackathon description had this line that stuck with me:

> *"Your AI wakes up every morning with no memory of last night."*

I'm a CP guy. I think in test cases. And immediately I started thinking: what's the *adversarial* test case for AI memory? Not "can the agent remember a fact" — that's the easy case. The hard case is: **what happens when the agent has been told two different things about the same subject, and one of them is wrong now?**

That's context rot. And the more I read about it, the more I realized this is not a toy problem. This is the reason support bots quote outdated return policies. This is the reason coding assistants suggest deprecated APIs. This is why "AI memory" demos always show you adding facts but never show you what happens when facts *change*.

I decided that's what I was going to build. Not another chatbot-with-memory demo. A proof — something with a number attached to it.

---

## Learning Cognee From Zero

I cloned the repo on day one and started reading.

Cognee's public API is beautifully simple on the surface:

```python
await cognee.add("some text")
await cognee.cognify()           # builds the knowledge graph
results = await cognee.search("some question")
await cognee.improve()           # enriches / resolves contradictions
```

Four functions. I thought: okay, this is going to be a quick weekend build.

I was wrong in the best possible way.

The first thing I learned is that Cognee is not just a vector store with a nice API wrapper. Under the hood it's running a hybrid store — LanceDB for vector embeddings, Kuzu for the graph database — and `cognify()` is actually running LLM-based entity and relationship extraction to *build a real knowledge graph* from your raw text. That's not a small thing. That means when you add "Alice lives in New York," Cognee doesn't just embed that sentence — it extracts `Alice` as an entity, `lives in` as a relationship, and `New York` as a node, and stores those structural connections in the graph.

That was the moment I realized this was going to be genuinely interesting to explore.

---

## The Assumption That Turned Into a Discovery

My original plan was to build a benchmark: feed two pipelines the same stream of evolving facts (Alice lives in New York → then Chicago → then Seattle), ask them "where does Alice live now," and prove Cognee gives the right answer while a naive vector store hallucinates across all three cities.

For Cognee's pipeline, I planned to use `improve()` — the function the docs describe as "run post-ingestion enrichment, prune stale nodes, and adapt weights based on user feedback." Perfect. That would handle the contradiction resolution.

So I built a verification script. I ingested a supersession fact. I called `improve()`. Then I dumped the raw graph and counted the nodes.

**The stale "New York" node was still there. The count had gone up, not down.**

I stared at this for a while. Then I dug into Cognee's source code.

What `improve()` actually does — and this is fascinating once you understand it — is *LLM-side reconciliation*. It adds resolution edges and enriches the graph with new context. When you query later, the LLM can *reason* its way to the correct answer by reading the contradiction metadata. In a lot of cases, this works fine. The LLM is smart enough to figure out that "Seattle supersedes Chicago supersedes New York."

But that's not the same as physical deletion. The stale node is still there. If you retrieve a context window with all three locations in it, you're trusting the LLM to resolve the contradiction every single time at query cost. And sometimes it doesn't — I could show that empirically with my naive pipeline, which was doing the same kind of LLM-at-query-time resolution and getting it wrong 75% of the time.

So I built the missing piece myself.

---

## Building the Deep-Pruning Layer

This is the part I'm most proud of.

Cognee exposes its underlying graph engine and vector engine as importable clients:

```python
from cognee.infrastructure.databases.graph.get_graph_engine import get_graph_engine
from cognee.infrastructure.databases.vector.get_vector_engine import get_vector_engine
```

I used these to build a custom pruning step that runs after every `cognify()` call when a new fact supersedes an old one. The logic:

1. Query the Kuzu graph for any `Fact` node where `subject` and `value` match the superseded values
2. Delete that node from the graph
3. Find all associated vector chunks across every LanceDB table (DocumentChunk, TextSummary, EdgeType) using the node ID
4. Delete each chunk individually

Two stores, one atomic operation, zero stale data.

Along the way I found another silent failure: if you install `fastembed` as a standalone package but don't install `cognee[fastembed]` (the plugin wrapper), Cognee silently falls back to building the graph without generating any vector embeddings at all. No error, no warning you'd notice, just an empty vector store. That cost me an afternoon and is now documented in the README.

I also found that Cognee's LLM extraction sometimes rephrases predicates — "lives in" becomes "resides in" or "location" — which would break naive exact-string matching on the predicate field. So instead of matching by predicate, I match by subject + the specific superseded value. That combination is unique enough to identify the stale node reliably, regardless of how the LLM phrased the relationship during extraction.

---

## What the Benchmark Actually Shows

I built 15 synthetic fact-stream scenarios: job application statuses, user locations, subscription plans, favorite programming languages, flight statuses — domains where facts naturally evolve and contradict each other. Each scenario has a ground truth answer (what's true *right now*) and a set of stale values that should not appear in any answer.

The results:

| Pipeline | Accuracy |
|---|---|
| **Naive Vector Store** | **25% (1/4 on initial run)** |
| **Cognee + Deep-Pruning Layer** | **100%** |

But the number I find more interesting is from the adversarial test. I ran three edge cases specifically designed to stress-test the system:

**Case 1 (Paraphrased query):** "What city is Alice currently residing in?" instead of "Where does Alice live?"
- Naive: *"There are multiple cities listed (New York, Seattle, Chicago), but only one can be current. The context does not specify which is current."*
- Cognee: *"Seattle."*

**Case 2 (Stable fact):** "What is Alice's favorite color?" — a fact that was never updated
- Naive: "Blue" ✓
- Cognee: "Blue." ✓

Both pipelines get stable facts right. The failure is specifically on contradicted facts. That rules out "Cognee just got lucky" as an explanation.

**Case 3 (Recency bias):** "Where did Alice move to in 2025?" — phrased to give a recency-biased naive pipeline its best chance
- Naive: *"There is no information about Alice moving in 2025. The context only provides multiple current locations."*
- Cognee: *"Seattle."*

The naive pipeline couldn't resolve this even with a year hint. Because the raw vector chunks don't have meaningful chronological structure — they're just text — there was no signal to prefer Seattle over Chicago over New York. Cognee's graph, with the stale nodes physically absent, had only one answer available.

---

## The Open Source Part — Which Honestly Means a Lot to Me

I've been doing competitive programming for two years. I've built Android apps. I've submitted to hackathons. But I had never actually contributed to an open-source project before this hackathon.

That changed this week.

While building ContextRot Bench, I spent so much time reading Cognee's migration source code — the `GraphitiSource`, `Mem0Source`, `ZepSource` classes, the COGX memory standard — that I started to actually understand the codebase. Not just the high-level API, but the internals. How `import_source.py` orchestrates the migration. How `COGXMemory` vs `COGXFact` vs `COGXEntity` map to different kinds of knowledge.

When I saw open issues asking for migration tutorials — "Tutorial: Migrate from Graphiti to Cognee," "Tutorial: Migrate from mem0 to Cognee" — I realized I was probably one of the few people outside the core team who had actually read those source files this week.

So I went and claimed those issues.

- Graphiti → Cognee migration tutorial: [PR #3798](https://github.com/topoteretes/cognee/pull/3798)
- Mem0 → Cognee migration tutorial: [PR #3847](https://github.com/topoteretes/cognee/pull/3847)

Writing code that will live in a public repository and help other developers — that's different from a hackathon project that only a few judges see. That's something that persists. That compounds. Someone six months from now who's trying to migrate their Graphiti knowledge graph into Cognee might run my tutorial script and it'll just work, and they'll never know a third-year student from NIT Silchar wrote it during a five-day hackathon.

That thought is genuinely exciting to me in a way that's hard to articulate.

---

## What I'd Tell Someone Starting With Cognee

A few things I wish I'd known on day one:

**1. Install `cognee[fastembed]`, not just `fastembed`.** The plugin wrapper matters and the failure is silent.

**2. `improve()` is smarter than deletion, not equivalent to it.** It adds resolution context; it doesn't remove stale data. Depending on your use case, that might be exactly what you want. For an adversarial benchmark, it wasn't enough.

**3. The hybrid graph-vector architecture is the real story.** Most "AI memory" tools are just vector stores with a chat interface. Cognee builds an actual knowledge graph during ingestion — entities, relationships, structural connections — which means your queries can traverse semantic similarity *and* graph topology. That's a fundamentally different capability, not a marketing distinction.

**4. Go one level below the public API.** `get_graph_engine()` and `get_vector_engine()` let you inspect and manipulate the stores directly. That's where the interesting engineering lives.

---

## Final Thoughts

Five days ago I didn't know what Cognee was.

Now I've built a benchmark that proves one of its documented failure modes, engineered a custom pruning layer that fixes it, found and documented two bugs in the process, and contributed tutorials back to the open-source repo.

I don't know if ContextRot Bench will win anything. But I know I understand AI memory systems in a way I didn't before, and I have open-source contributions on my GitHub that I'm genuinely proud of.

That feels like a good week.

---

*ContextRot Bench is open source → [https://github.com/Geetansh-12/cognee_hackathon](https://github.com/Geetansh-12/cognee_hackathon) | Built for the WeMakeDevs × Cognee Hackathon.*
