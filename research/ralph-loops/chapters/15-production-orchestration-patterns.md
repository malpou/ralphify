# Production Orchestration & Budget-Aware Loops (March 2026)

> The field has matured from "can agents loop?" to "how do we operate loops at scale?" This chapter covers the latest production patterns: role-based multi-agent architectures, budget-aware execution, loop fingerprint detection, and the emerging observability stack.

## Cursor's Planner-Worker-Judge Architecture

Cursor's March 2026 blog post documents the most ambitious multi-agent coding system publicly described — hundreds of concurrent agents building a web browser (1M+ lines, 1,000+ files, weeks of continuous operation).

### Architecture Evolution

Cursor iterated through three designs before finding what works:

1. **Flat coordination (failed)**: Equal-status agents self-coordinated through shared files using locks. Result: lock contention, deadlocks, agents becoming risk-averse without hierarchy.

2. **Optimistic concurrency (failed)**: State-based conflict resolution where writes fail if underlying state changed. Result: work churning, lack of accountability.

3. **Role-based pipeline (succeeded)**: Distinct roles with clear responsibilities:
   - **Planners** continuously explore codebases and create tasks. Can spawn sub-planners for recursive parallel planning.
   - **Workers** focus entirely on assigned tasks without inter-worker coordination. Push changes after completion.
   - **Judge** evaluates whether to continue the iteration cycle.

### Key Lessons

- **Model selection per role matters.** GPT-5.2 outperforms coding-specialized models (GPT-5.1-Codex) for planning. Use the best model per role, not one universal model.
- **Simplicity through removal.** An integrator role for quality control created bottlenecks; removing it improved throughput. Workers handled conflicts independently.
- **"Prompting over architecture."** A surprising amount of system behavior comes down to prompt engineering, not system design. Extensive prompt experimentation yielded better results than architectural refinements.
- **Optimal structure exists between extremes.** Too little structure → conflicts and duplicated work. Too much → fragility.

### Outstanding Challenges

Even at Cursor's scale: agents run excessively long, periodic drift requires fresh starts, and planner-worker synchronization timing remains suboptimal.

## Production Metrics That Matter

Mike Mason's January 2026 analysis provides the most grounded production data:

### Real Productivity Gains

Thoughtworks' assessment (Birgitta Boeckeler): **8-13% cycle time improvement**, not the 50% claimed by vendors.

Calculation: ~40% of time is coding × ~60% of that time AI assistance is useful × ~55% faster when useful = 8-13% net.

### Code Quality Deterioration (GitClear)

- Code churn doubled from 2021-2023
- Copy-paste code: 8.3% → 12.3%
- Refactoring dropped: 25% → under 10%
- 8-fold increase in duplicated code blocks

This is the empirical evidence for the entropy problem described in Ch12 — agent-generated codebases drift toward duplication and away from refactoring.

### Multi-File Performance Cliff

- SWE-Bench Verified (single-issue): frontier models achieve >70%
- SWE-Bench Pro (multi-file patches): drops below 25% for best models
- Enterprise legacy codebases: ~35% capability
- Files >500KB: often excluded from indexing entirely

This cliff is why the "one item per loop" rule is so critical — multi-file coordination is where agents fail.

## Budget-Aware Agent Execution

Google's BATS (Budget-Aware Test-time Scaling) framework introduces a plug-in "Budget Tracker" that surfaces real-time resource availability inside the agent's reasoning loop. The agent sees how many actions/tokens/dollars it has left and makes cost-aware decisions.

This is the formalization of what practitioners have been doing ad hoc:
- Agent Budget Guard MCP (Ch13): agents self-track spending
- Ralph TUI (Ch12): cost-per-feature tracking
- Aura Guard (Ch10): deterministic budget circuit breakers

The key insight: **budget awareness should be a continuous signal, not a hard cutoff.** Agents that can see their remaining budget make qualitatively different decisions — choosing simpler approaches, skipping optional improvements, and flagging when they're about to hit limits.

## Loop Fingerprint Detection

MatrixTrak's production pattern for detecting stuck agents:

### The Fingerprint Approach

Track the combination of last tool call + result. If this fingerprint repeats 3+ times consecutively, the agent is looping, not progressing.

```typescript
type LoopState = {
  iteration: number;
  lastFingerprint?: string;
  repeatCount: number;
};
```

### Error Classification Matrix

Map failure types to explicit actions:
- **Non-retryable** (validation, auth, policy): STOP immediately, zero retries
- **Rate limits** (429): RETRY with bounded attempts (2-3) + exponential backoff + jitter
- **Transient** (timeouts, 5xx): Limited retries, then ESCALATE
- **Safety blocks**: STOP or ESCALATE, never retry

### Essential Logging Schema

For debugging loops in production:
```
run_id, loop_iteration, last_tool, last_result_hash,
decision (stop|retry|escalate), error_class,
tool_calls_count, tokens_used
```

This is the operational complement to the circuit breaker patterns in Ch10 — those prevent cost blowups; fingerprint detection prevents behavioral loops.

## Git Worktree Isolation at Scale

Worktree-based isolation has become the standard pattern for parallel agent execution:

### Practical Ceiling

Boris Cherny's recommendation: 3-5 worktrees simultaneously. Augment Code's guide confirms: **3-4 parallel agents before coordination overhead exceeds gains**. Beyond 5-7, rate limits, merge conflicts, and review bottleneck eat the gains.

### Six Coordination Patterns (Augment Code)

1. Spec-driven task decomposition with explicit file boundaries
2. Git worktree isolation (separate working directories, shared object database)
3. Coordinator/specialist/verifier role split
4. Model routing by task type (reasoning models for architecture, fast models for iteration)
5. Layered verification gates
6. Sequential merge with rebase (each branch rebases onto latest main before merging)

### Failure Mode Taxonomy

| Failure | Detection Difficulty | Impact |
|---------|---------------------|--------|
| Merge conflicts | Low | Consumes review bandwidth |
| Duplicated implementations | Medium | Cross-branch comparison needed |
| Semantic contradictions | High | Pass compilation but fail at runtime |
| Context exhaustion | Medium | Degrades output quality |

The hardest failure (semantic contradictions) maps directly to Epsilla's "intent-failure detection" from Ch14 — code that compiles but disagrees at a behavioral level.

## Agent Observability Stack (2026)

The observability landscape for agent loops has consolidated around five platforms:

| Tool | Differentiator | Best For |
|------|---------------|----------|
| Braintrust | Eval-integrated observability | Teams doing EDD (Ch06) |
| Helicone | Proxy-based, multi-provider cost optimization | Cost-conscious loops |
| Galileo | Real-time safety checks at scale | Safety-critical agents |
| Fiddler | Compliance monitoring | Regulated industries |
| Vellum | Visual workflow + observability | Low-code agent development |

### Essential Metrics

- Response times and token usage per iteration
- Cost per request and per task
- Tool call accuracy and success rates
- Task completion rates
- Intent resolution scores (the hardest to measure)

The key gap: none of these tools are designed specifically for ralph loop observability. Ralph TUI (Ch12) comes closest but is a bespoke tool, not a platform. Ralphify could fill this gap with native iteration metrics.

## The "Engineering Discipline" Reframe

Sam Keen (Altered Craft) articulates what practitioners increasingly recognize: the ralph loop's power comes not from the bash while-loop, but from the engineering discipline it enforces:

1. **Specification-driven development**: 30+ minutes writing specs before any implementation
2. **Automated validation gates**: Tests must pass, builds must succeed, completion markers must be present
3. **Fresh context per iteration**: Filesystem persistence, not conversation accumulation

> "As AI tools become more capable, the skills that matter most may be the ones we've always had."

This echoes Van Eyck's "XP rediscovered" insight (Ch14) and Chad Fowler's "relocating rigor" thesis (Ch09). The convergence is clear: **agent loops succeed because they force engineering discipline, not despite requiring it.**

## The Meridian Experiment: 3,190 Cycles

The most extensive documented autonomous operation: Meridian ran for 30 days at 5-minute intervals (288 cycles/day), including a 110+ hour uninterrupted session.

Key findings:
- **9 specialized sub-agents** managed simultaneously
- **497 journal entries** produced (creative output correlates with sustained runtime)
- **Identity compression**: The system evolved a three-phase strategy for maintaining functional continuity across context resets, achieving it in under 100 lines
- **Operational knowledge transmits; experiential texture doesn't**: State documents carry facts but lose the "feel" of extended operation

The practical takeaway for ralph loops: agents can maintain coherence across thousands of iterations if state persistence is well-designed. But the state files must capture decisions and reasoning, not just facts — what Meridian calls the gap between "structural" and "constitutive" persistence.

## Implications for Ralphify

### Native Loop Fingerprinting

Ralphify should detect stuck loops without LLM calls. The fingerprint approach (tool+result hash) is lightweight and deterministic. Implementation: hash command outputs between iterations; if identical across 3+ iterations, warn or stop.

### Budget Signal Integration

A `budget` field in RALPH.md that surfaces remaining iterations/cost to the agent:

```yaml
max_iterations: 20
max_cost: 5.00  # USD
```

The agent sees `Iteration 7/20, estimated cost $1.43/$5.00` in its context each iteration — enabling budget-aware decision-making rather than blind execution until cutoff.

### Worktree-Native Parallel Execution

Ralphify's `manager.py` already supports concurrent runs. Adding worktree isolation would make parallel ralphs safe by default:

```bash
ralph run --parallel 3 --worktree  # 3 parallel worktrees
```

### Observability Dashboard

Per-iteration metrics surfaced in CLI output:
- Iteration count and remaining budget
- Command pass/fail status
- Estimated token usage
- Loop fingerprint status (progressing vs. stuck)

This addresses the gap no existing tool fills: ralph-loop-specific observability.
