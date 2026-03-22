# Long-Running Agent State, Memory & Operational Durability

> As agent loops extend from hours to weeks, state management becomes the primary engineering challenge. Four memory architectures compete, five compression failure modes threaten durability, and the compound failure math (85% per step → 20% for 10 steps) defines the design constraints.

## The Duration-Failure Curve

Agent performance degrades non-linearly with task duration. Doubling task duration **quadruples** the failure rate — not doubles. The "35-minute wall" marks the point where human-facing tasks start degrading measurably. For autonomous loops, this means iteration length is a critical architectural decision: shorter iterations with fresh context aren't just preferable — they're mathematically necessary.

The compound failure rate is the defining constraint:
- 85% per-step success → 20% success over 10 steps (0.85^10)
- 95% per-step success → 60% success over 10 steps (0.95^10)
- 99% per-step → 82% over 20 steps (0.99^20)

**Design implication**: Ralph loops should minimize steps per iteration. The research consensus (3-7 actions optimal, Ch04) is directly driven by this math.

## Four Competing Memory Architectures

Long-running agents need memory that persists across thousands of iterations. Four architectures have emerged:

### 1. Observational Memory (strongest for autonomous agents)

Two background LLM agents: an Observer extracts dated observations from interactions; a Reflector synthesizes insights periodically. Achieves **94.87% accuracy** on LongMemEval (GPT-5-mini), with **3-40x compression** and **4-10x token cost savings** via prompt caching. The tradeoff: background compute costs and lossy compression.

**Google's Always On Memory Agent** (open-sourced March 2026) implements this without a vector database — "just an LLM that reads, thinks, and writes structured memory" backed by SQLite. Consolidation loop runs every 30 minutes: reads unconsolidated memories, asks Gemini to detect patterns, produces synthesized summaries.

### 2. Graph Memory (Zep/Graphiti)

Temporal knowledge graphs tracking entity/relationship changes over time. **Up to 18.5% accuracy improvement** over baselines, **90% latency reduction**, up to **80% prompt token reduction**. Handles temporal reasoning natively — important for tracking "what changed since iteration 500?" The tradeoff: graph infrastructure complexity; entity extraction errors create noise.

### 3. Self-Editing Memory (MemGPT-style)

Agents manage memory explicitly via tools (`edit_memory`, `archive_memory`, `search_memory`). Working memory (in-context) + archival storage (out-of-context). The tradeoff: memory management **consumes reasoning tokens** — agents spend cycles deciding what to remember instead of doing their job.

### 4. RAG + Hybrid Retrieval

Dense vector + sparse BM25 + metadata filtering. **30-40% relevance improvement** over pure vector search. The tradeoff: no compression, forgetting, or reflection — stores everything with equal weight forever.

**Recommendation for ralph loops**: Architecture 1 (Observational) maps most naturally. A "memory ralph" that runs periodically to consolidate insights from recent iterations into a knowledge file is the ralph-native version of Google's pattern — no vector DB, just structured markdown.

## Five Memory Compression Failure Modes

As agents compress state across iterations, five distinct failure modes emerge (Indium Tech):

1. **Catastrophic Forgetting** — Compression algorithms prioritize recent signals; earlier constraints and preferences disappear without explicit deletion. The first decisions made in a long-running loop are the first to vanish.

2. **Hallucination Amplification** — Reduced contextual detail forces models to rely on internal priors, generating confident but incorrect statements about prior iterations.

3. **Context Drift** — Compressed vectors shift meaning as new data reshapes embedding space. Queries that once returned accurate results become unreliable over time.

4. **Over-Compression Bottlenecks** — Complex multi-step reasoning no longer fits after intermediate inferences were lost during compression. The "why" behind decisions disappears.

5. **Bias Creep in Embeddings** — Compression amplifies dominant patterns while marginalizing underrepresented contexts. The agent develops tunnel vision toward common patterns.

**Mitigation for ralph loops**: Fresh context per iteration already eliminates within-iteration compression risks. The danger is cross-iteration compression — when `progress.md` or `knowledge.md` grows too large and must be summarized. The safest approach: structured, append-only files with periodic consolidation by a dedicated "memory ralph" rather than within-task compression.

## Restorable Compression: Manus's Key Insight

Rather than trying to transmit understanding through compressed summaries, Manus uses **restorable compression** — preserving enough metadata (URLs, file paths, commit hashes) that the agent can re-derive context on demand.

The philosophy: **don't transmit the understanding; transmit the ability to reconstruct it.**

This has direct implications for ralph loops:
- `progress.md` should include file paths and commit references, not summaries of what changed
- Commands can re-derive current state (e.g., `git log --oneline -20`) rather than relying on stale summaries
- The ralphify command system already supports this — `{{ commands.recent_changes }}` can always pull fresh state

## The Experiential Texture Problem

The Meridian experiment (3,190 cycles, 30 days) found that operational knowledge transmits across iterations but "experiential texture" doesn't — the nuanced understanding of *why* certain approaches were tried and abandoned gets lost in state files.

**Why this matters**: An agent that reads "Approach X failed — use Approach Y" doesn't understand *why* X failed, so it can't recognize similar-but-different situations where X might actually work.

Jason Liu (jxnl.co) frames compaction as analogous to **momentum in gradient descent** — it preserves learned optimization paths, not just facts. Current compaction "doesn't always pass perfectly clear instructions to the next agent."

**The emerging mitigations**:
- **Structured decision logs**: Record not just what was decided but why, including failed alternatives
- **Restorable compression**: Keep pointers to the full context rather than summaries
- **Sub-agent exploration**: Agents that explore extensively (tens of thousands of tokens) but return condensed summaries of 1,000-2,000 tokens — a 10-20x compression that necessarily strips experiential context, but preserves actionable findings
- **Periodic fresh starts**: Cursor found that even well-designed long-running agents benefit from periodic full resets — a new agent reading the state files with fresh eyes sometimes outperforms the "experienced" one

## State File Patterns at Scale

The dominant pattern across all documented long-running systems is **markdown + JSON files in git**:

| System | State Files | Duration |
|--------|------------|----------|
| Anthropic (claude.ai rebuild) | `claude-progress.txt`, `feature_list.json` | 200+ features |
| OpenAI Codex (25-hour run) | `Prompt.md`, `Plan.md`, `Implement.md`, `Documentation.md` | 25 hours |
| Manus | `todo.md`, filesystem as externalized memory | Variable |
| Meridian | 497 journal entries, 9 sub-agent state files | 30 days |
| earezki swarm | CLAUDE.md + local files + Qdrant vector DB (5-layer) | Ongoing |

**Convergence**: Every system uses 3-5 structured files. No system uses a database for primary state. Git provides the checkpoint/revert mechanism. The 100:1 input-to-output token ratio (Manus) means state management is the primary cost driver.

## Production Failure Modes Unique to Long-Running Operation

Beyond the standard failure modes (Ch07), long-running operation introduces:

- **Lock-based coordination collapse** (Cursor): Agents held locks indefinitely, reducing hundreds of agents to 2-3 effective ones. File-based locking fails at scale.
- **Risk aversion in flat hierarchies**: Agents avoid ambitious work and churn on easy tasks to avoid failure — the agent equivalent of bikeshedding.
- **Cascading state corruption**: A corrupted memory in early steps poisons subsequent reflections, plans, and actions across the remaining workflow.
- **Memory poisoning via prompt injection**: Indirect prompt injection corrupting long-term memory creates persistent false beliefs the agent defends when questioned.
- **Drift without termination**: Agents occasionally run far too long without progress, consuming resources without producing value.

## Implications for Ralphify

1. **Ralph loops are architecturally correct for long-running work** — fresh context per iteration is the primary defense against the duration-failure curve, context drift, and memory compression failures.

2. **A "memory ralph" cookbook pattern** could implement observational memory: a periodic ralph that consolidates recent progress files, extracts patterns, and writes a `knowledge.md` for future iterations. No vector DB required — just structured markdown consolidation.

3. **Restorable compression should be a prompt engineering guideline**: RALPH.md prompts should instruct agents to write file paths and commit hashes into progress files, not summaries.

4. **The 3-7 action sweet spot per iteration** is not a preference — it's derived from compound failure math. Ralph documentation should explain *why* iterations should be small.

5. **State file templates** (progress.md, tasks.md, knowledge.md) could be part of `ralph new` — giving users a validated starting point for long-running loops.
