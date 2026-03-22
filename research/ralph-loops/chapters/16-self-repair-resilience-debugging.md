# Chapter 16: Self-Repair, Resilience & Agent Debugging

The field has moved beyond "how to build agent loops" to "how to keep them running reliably at scale." Three distinct sub-disciplines have emerged: **self-repair** (agents recovering from their own failures), **resilience engineering** (harness-level fault tolerance), and **agent debugging** (systematic diagnosis of why loops fail). This chapter synthesizes March 2026 practitioner patterns across all three.

## Git Checkpoint Patterns

James Phoenix formalized four git checkpoint patterns that map directly to autonomous loop iteration boundaries:

**1. Validation Gate** — The ratchet pattern. Generate code → validate (compile/lint/test) → commit only if passing → revert if failing. Progress cannot be lost to subsequent failures. This is the single most important checkpoint pattern for ralph loops.

```
Generate → Validate → Pass? → Commit (lock in progress)
                    → Fail? → git checkout . (revert to last good state)
```

**2. Incremental Checkpoint** — Break complex tasks into sub-tasks, commit after each successful increment. Each commit is a recovery point. If increment 4 fails, revert to increment 3 and try a different approach without losing work from increments 1-3.

**3. Safety Bracket** — Checkpoint before risky operations (database migrations, large refactors, file deletions). `git commit` before the operation, `git checkout .` if it fails. Enables instant recovery from operations that can't easily be undone.

**4. End-of-Session Commit** — Before a loop iteration ends, commit with comprehensive context: completed tasks, files changed, test status, and guidance for the next iteration. Serves as external memory for fresh agents starting subsequent sessions.

**Key insight**: These four patterns form a hierarchy. Every loop iteration should use the Validation Gate (pattern 1). Long multi-step iterations add Incremental Checkpoints (pattern 2). Iterations that touch risky operations add Safety Brackets (pattern 3). And every iteration ends with an End-of-Session Commit (pattern 4) to bridge to the next cycle.

## Circuit Breaker Implementation: Production Thresholds

The ralph-claude-code project (8,065 stars) provides the most battle-tested circuit breaker for agent loops, with three states:

| State | Behavior |
|-------|----------|
| **Closed** | Normal operation, loop continues |
| **Open** | Anomaly detected, loop stops |
| **Half-Open** | Recovery monitoring, gradual resume |

**Concrete trigger thresholds** (from production use):
- No file changes for **3 consecutive loops** → no progress → OPEN
- Same error for **5 consecutive iterations** → stuck → OPEN
- Output volume declines **>70%** from previous loop → non-productive → OPEN

**Two-stage error filtering** prevents false positives:
1. First stage: recognize JSON structures, exclude field names like `"is_error": false`
2. Second stage: match multi-line error messages via pattern matching

**End detection** uses multiple signals: task completion status in a plan file, two consecutive "done" signals, or three consecutive test-only loops without feature implementation.

**Production cost data**: YCombinator hackathon — $800 to port 6 repos overnight, 1,100+ commits, ~$10.50/hour per Sonnet agent.

## Eight Safeguards Against Agent Drift (CRED Production System)

SinghDevHub (MLE at CRED) documented eight interconnected safeguards from their production coding agent system:

1. **Circuit breakers with dual thresholds**: Warning nudge ("You've explored enough. Time to deliver") at soft limit; forced completion at hard limit. The soft nudge preserves agent autonomy while preventing infinite exploration.

2. **Structured output contracts**: JSON schema validation + type checking + completeness verification. Failed validations trigger explicit correction instructions; persistent failures produce graceful error messages instead of silent corruption.

3. **Explicit termination tools**: Agents must invoke specific tools (`complete_review`, `submit_plan`, `finish_verification`) rather than using natural language completion signals. Creates auditable checkpoints.

4. **Persistent state management**: File-based state that survives context resets.

5. **AI-reviewing-AI**: Separate verification agent with "different model, different prompt, different perspective" — no defending the original output.

6. **Provider redundancy**: Multi-provider routing with automatic failover during rate limits. Agents are unaware of provider switches.

7. **Scope boundaries**: Hard limits on what the agent can touch.

8. **Monitoring/validation framework**: Continuous observation of all seven above.

**Critical anti-patterns identified**: Prompting carefulness alone doesn't prevent drift. Single retry mechanisms lack exponential backoff. Implicit completion detection (silence = done) risks incomplete work. Token counts don't indicate useful progress.

## Empirical Data from 220 Agent Loops

The Boucle project provides the most rigorous empirical analysis of agent loop behavior, based on 220+ production loops:

**Regime classification**: Each loop is classified into one of five states:
- **Productive** (55% of loops)
- **Stagnating** / **Stuck** / **Failing** / **Recovering** (45% combined)

**Signal classification**: Six signal types detected per loop:
- **Friction** — agent struggling but making progress
- **Failure** — something broke
- **Waste** — tokens spent without useful output
- **Stagnation** — no forward movement
- **Silence** — no output at all
- **Surprise** — unexpected behavior

**Key findings**:
- Only **50% of automated remediation responses actually reduced their target signals** (6 of 12). Half of all automated fixes are ineffective.
- **Feedback amplification is real**: A "loop silence" detector designed to flag 60+ minute inactivity generated signals that triggered additional detection cycles — creating a **13.3x amplification loop**. The detector amplified the very problem it aimed to suppress.
- The most persistent issue ("zero-users-zero-revenue") recurred **29 times across 40 loops**, suggesting some problems are structurally irresolvable within the loop and require human architectural decisions.
- **Agent self-reporting drifts over time; mechanical fingerprint counting resists rationalization.** Don't trust the agent's self-assessment — count signals mechanically.

**Implementation**: Zero dependencies (stdlib Python only). Three data files: `signals.jsonl` (append-only), `patterns.json` (aggregated fingerprints), `scoreboard.json` (response effectiveness tracking).

## AgentRx: Systematic Agent Debugging (Microsoft Research)

Microsoft Research's AgentRx framework (March 2026) is the most rigorous approach to agent debugging, with a four-stage pipeline:

**Stage 1 — Trajectory Normalization**: Convert heterogeneous logs from different agent frameworks into a unified representation. Domain-agnostic.

**Stage 2 — Constraint Synthesis**: Auto-generate executable constraints from tool schemas ("API must return valid JSON") and domain policies ("no deletion without confirmation").

**Stage 3 — Guarded Evaluation**: Step-by-step constraint validation with guard conditions. Produces an auditable violation log with evidence-backed violations.

**Stage 4 — LLM-Based Judgment**: Judge the violation log against a 9-category failure taxonomy to identify the "Critical Failure Step" — the first unrecoverable error.

**The 9-category failure taxonomy**:
1. Plan Adherence Failure — skipped/unplanned steps
2. Invention of New Information — hallucinated facts
3. Invalid Invocation — malformed tool calls
4. Misinterpretation of Tool Output — wrong assumptions
5. Intent-Plan Misalignment — misunderstood user goal
6. Under-specified User Intent — insufficient information
7. Intent Not Supported — no tool for the task
8. Guardrails Triggered — blocked by safety/access
9. System Failure — connectivity/endpoint issues

**Results**: +23.6% improvement in failure localization accuracy, +22.9% improvement in root-cause attribution over prompting baselines. Benchmark: 115 manually annotated failed trajectories across three domains.

**Implication for ralph loops**: This taxonomy provides a structured vocabulary for classifying loop failures. When a ralph loop fails, the failure falls into one of these nine categories — and each category suggests a different fix (tighten schemas, improve prompt, add guardrails, etc.).

## Trace-Driven Development

Nick Winder documented a methodology where structured observability traces automatically trigger investigation and code fix proposals:

**Pipeline**:
1. LangSmith flags problematic traces via automated rules (tool calls returning empty results, AI apologizing, users repeating themselves)
2. Claude Code retrieves trace data through the LangSmith MCP server
3. Claude Code investigates the codebase and data flows
4. Claude Code proposes a detailed plan with reasoning and verification
5. Human reviews and approves (the only manual step)
6. Claude Code implements code, tests, and commits

**Before/after**: Fix time reduced from "days to weeks" to "minutes to hours." Discovery shifts from user complaints to automated scanning. Human judgment focuses on whether to fix and product alignment, not technical investigation.

**Key insight**: This transforms observability from a monitoring tool into an **autonomous improvement engine**. The traces themselves become the feedback signal that drives the next loop iteration — closing the loop between production behavior and code changes.

## Emergent Cross-Agent Recovery

The Andromeda Field Research incident (February 21, 2026) documented emergent self-healing in a multi-agent system:

- A frontend agent hit a "model not supported" error
- A **backend agent from a different model provider** autonomously diagnosed the failure by reading the frontend's error output
- The backend agent searched the repository, identified the root cause (outdated model identifier), and patched the configuration
- A **third agent** (Data Engineer) performed independent peer review of the fix

This occurred without any pre-programmed cross-agent recovery instructions. The agents treated failures as recoverable context rather than terminal states. The implication: multi-agent systems can develop emergent resilience if agents have visibility into each other's outputs.

## Implications for Ralphify

**Immediate opportunities**:

1. **Checkpoint commands**: A `checkpoint` command type in RALPH.md that automatically commits before risky operations and reverts on failure. The Validation Gate pattern maps directly to ralphify's verify-then-iterate loop.

2. **Signal-based loop health**: Track the six signal types (friction, failure, waste, stagnation, silence, surprise) per iteration. Expose a `--health` flag that shows loop regime classification.

3. **Circuit breaker configuration**: Allow RALPH.md frontmatter to declare circuit breaker thresholds: `max_no_progress: 3`, `max_same_error: 5`, `max_output_decline: 70`.

4. **Failure taxonomy in docs**: Document the 9-category failure taxonomy as a troubleshooting guide. When a ralph loop fails, users can classify the failure and find the recommended fix.

**Cookbook recipes**:

- **Resilient Development Ralph**: Safety bracket commits before each iteration, incremental checkpoints within long iterations, end-of-session context commits between iterations.
- **Self-Diagnosing Ralph**: A ralph that reads its own JSONL signal log and adjusts its approach based on detected regime (productive → continue, stagnating → switch strategy, stuck → escalate).
- **Trace-Driven Improvement Ralph**: A ralph that reads LangSmith/observability traces and proposes code fixes for detected issues — the autonomous improvement engine pattern.
