# Harness Evolution & Entropy Management

> Harnesses are temporary scaffolding, not permanent architecture. The best harnesses are designed to be "rippable" — built so that complexity can be removed as models improve. Meanwhile, agent-generated codebases accumulate entropy that requires active management through periodic cleanup agents.

## The Rippable Harness Principle

LangChain coined the term: "Build your harness to be rippable — you should be able to remove 'smart' logic when the model gets smart enough to not need it." But in early 2026, the evidence has moved from principle to practice.

### Who's Actually Ripping Layers

**Vercel** removed 80% of their agent's tools and got *better* results. Fewer tools meant fewer steps, fewer tokens, faster responses, and higher success rates. This is harness improvement through subtraction — the opposite of the instinct to add capabilities.

**Manus** refactored their harness five times in six months. Each refactor simplified rather than complexified. The rapid model improvement cycle (new frontier model every 2-3 months) means harness logic has a short shelf life.

**LangChain** re-architected their research agent three times in one year. Each iteration removed hand-coded reasoning patterns that newer models handled natively.

### The Build-to-Delete Framework

Phil Schmid (Hugging Face) frames this as "Build to Delete" — a design philosophy for agent harnesses:

**Permanent layers** (keep across model generations):
- Context engineering (documentation, repository structure loading)
- Architectural constraints (dependency rules, linting, CI)
- State persistence (git, progress files)
- Safety boundaries (permission scoping, cost limits)

**Temporary layers** (expect to remove as models improve):
- Reasoning optimization middleware (ReasoningSandwich)
- Loop detection and course-correction prompts
- Planning decomposition scaffolding
- Tool selection guidance / routing logic

**The test**: Before adding any middleware layer, ask: "Will I want to remove this when the next model ships?" If yes, ensure it's modular and isolated. If you over-engineer the control flow, the next model update will break your system.

### The Bitter Lesson Applied to Harnesses

Schmid invokes Sutton's Bitter Lesson: hand-coded complexity becomes obsolete rapidly. Capabilities that required complex, hand-coded pipelines in 2024 are now handled by a single context-window prompt in 2026. The trajectory is clear — and harness engineers who bet against model improvement lose.

The implication: **invest in robust atomic tools rather than elaborate control flows.** Let models handle planning directly. The harness provides constraints and context, not orchestration logic.

## Entropy Management: The Third Pillar

OpenAI's harness engineering framework identifies three pillars: **context engineering**, **architectural constraints**, and **entropy management**. The first two are well-understood. The third — entropy management — is the newest and least documented.

### The Problem

Over time, agent-generated codebases accumulate entropy:
- Documentation drifts from reality
- Naming conventions diverge across modules
- Dead code accumulates
- Agents replicate existing patterns — even suboptimal ones — creating compounding drift
- "AI slop" (low-quality, boilerplate-heavy generated code) builds up

OpenAI's Codex team (1M+ lines, zero hand-written) initially spent **every Friday manually cleaning up AI slop.** This doesn't scale.

### Garbage Collection Agents

The solution: **periodic cleanup agents** that run on schedule (daily, weekly, or event-triggered):

1. **Documentation consistency agents** — scan for doc/code divergence
2. **Constraint violation scanners** — verify architectural rules are followed
3. **Pattern enforcement agents** — ensure naming conventions, file structure, code style
4. **Dependency auditors** — flag unused or outdated dependencies
5. **Quality grade agents** — assign per-module quality scores, open targeted refactoring PRs

This is the "garbage collection" metaphor: just as runtime GC prevents memory leaks, harness GC prevents technical debt accumulation. Human taste is captured once in constraints and enforcement rules, then applied continuously on every line of code.

### The Entropy Ralph

For ralphify, this maps directly to a **cleanup ralph** — a ralph that runs on a schedule (daily, weekly) scanning for codebase drift:

```yaml
agent: claude -p
commands:
  - name: violations
    run: ./scripts/check-constraints.sh
  - name: quality_scores
    run: ./scripts/quality-grade.sh
```

The prompt instructs the agent to fix constraint violations, update stale documentation, and remove dead code. Each iteration addresses the highest-priority drift. This is the operational complement to the "development ralph" — one builds, the other maintains.

## Completion Promise Gating

A significant pattern that has emerged and been formalized in 2026: **machine-verifiable exit markers** that replace subjective LLM judgment about task completion.

### The Problem with Self-Assessment

The ReAct paradigm relies on the LLM's self-assessment to determine completion. But LLM self-assessment is unreliable — agents exit when they *subjectively think* they're done, not when they've *objectively met* completion criteria. This is the fundamental architectural weakness that the ralph loop pattern solves.

### How Completion Promises Work

1. The prompt includes a specific marker (e.g., `<promise>COMPLETE</promise>`) that the agent should output *only* when objectively verifiable criteria are met
2. A Stop Hook intercepts the agent's exit attempt
3. If the marker isn't present in the output, the exit is blocked (exit code 2) and the original prompt is re-injected
4. The agent confronts its previous work in the filesystem/git, analyzes why the task remains incomplete, and tries again

This creates a **forced verification loop**: external systems (file state, test results, git diffs) serve as distributed memory, and the completion promise serves as the gating function.

### Completion Promises vs. Command Verification

Ralphify's `commands` field already provides a natural mechanism for external verification. The completion promise pattern is complementary — it handles the case where the agent *thinks* it's done but hasn't actually produced the desired outcome. The combination:

1. **Commands** verify the *state* (tests pass, coverage improved, no lint errors)
2. **Completion promises** verify the *intent* (the agent believes all items are addressed)
3. **Max iterations** provide the hard safety ceiling

## The Observability Gap

Ralph TUI (Verdent) represents the first dedicated dashboard for agent loop observability, tracking three metrics:

1. **Task completion rate** — 60% baseline, 90%+ is excellent
2. **Stuck detection latency** — target: under 5 minutes to detect a stuck loop
3. **Cost per feature** — $1.50 target vs. $5.00+ typical

Key patterns:
- **Visual loop detection**: if the agent edits the same file 4+ times without passing the test, it's stuck. The dashboard makes this immediately visible.
- **Session state persistence**: writing session data to disk (`.ralph-tui/session.json`) enables crash recovery and cross-session continuity.
- **Model tiering**: cheaper models (Haiku) for routine tasks, premium models (Opus) for complex logic. Cost optimization within the loop.

This is an area where ralphify could differentiate — surfacing per-iteration metrics (duration, command results, iteration count, estimated cost) in CLI output addresses the #1 operational pain point.

## Evolutionary Software: Level 9

Geoffrey Huntley (ralph loop inventor) is pushing toward what he calls "Level 9" — fully evolutionary software:

- **Level 8** (Gas Town / current state): orchestration of multiple autonomous agents, spinning plates
- **Level 9** (Loom / target): autonomous loops that evolve products and optimize automatically for revenue

In Huntley's implementation:
- Agents push directly to master (no branches, no code review)
- Deployment in under 30 seconds
- Self-repairing feedback loops: if something breaks in production, feedback feeds back into the active session and it self-repairs
- Full sudo access on bare metal NixOS machines with carefully engineered constraints

This is extreme but directionally correct. The progression: manual coding → AI-assisted coding → autonomous loops → evolutionary software. Ralphify sits at the "autonomous loops" level, with the architecture to support movement toward evolutionary software as trust and verification mature.

### Three Operational Modes

Huntley identifies three modes for autonomous loops:

1. **Forward mode** — autonomous building (standard ralph loop)
2. **Reverse mode** — clean room development (agent deconstructs/rebuilds for quality)
3. **Loop mindset** — cyclical improvement and automation (the ralph as a continuous process, not a one-time execution)

The "loop mindset" is the key shift: treating software development as an iterative, continuous process rather than sequential building. The ralph isn't a tool you run once — it's a process you tune and operate indefinitely.

## Trajectory Data as Competitive Advantage

Phil Schmid argues that competitive advantage comes not from prompts or harness logic, but from **trajectory data** — the record of every agent interaction, failure, and recovery:

> "Every time your agent fails to follow an instruction late in a workflow" provides training material for iteration.

This reframes agent failures as **data collection**. The organizations that capture the richest trajectory data will build the best harnesses over time, creating a flywheel:

1. Run agent loops → collect trajectory data
2. Analyze failures → identify harness gaps
3. Add constraints or context → improve success rate
4. Repeat

For ralphify, this suggests that **iteration logging** (what the agent tried, what passed/failed, how many iterations) is not just an observability feature — it's the raw material for harness improvement.

## Implications for Ralphify

Moved to [Chapter 6](06-ralphify-implications.md) — see sections on "Where the Gaps Are" and "Competitive Positioning."
