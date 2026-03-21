# Prompt Assembly & Context Engineering

> The core craft of harness engineering is assembling the right context for each iteration. This chapter covers the concrete techniques practitioners use to build prompts, manage context windows, and steer agents mid-loop — the "how" behind the "what" of chapters 01-08.

## The Prompt Assembly Problem

In traditional software, a function's inputs are well-defined. In an agent loop, the "input" is an assembled prompt — a composition of static instructions, dynamic command outputs, progress state, and specification files. The quality of this assembly determines whether the agent makes progress or spins.

Every serious harness solves the same problem: **how to deterministically load the right context each iteration while keeping the window clean enough for the agent to reason.**

## Three-Phase Prompt Architecture

The most validated pattern, independently converged on by HumanLayer (Dex Horthy), Anthropic, and Test Double, splits work into three distinct phases, each with its own prompt and fresh context window:

### Phase 1: Research

Understand the codebase. The prompt spawns parallel subagents to search and read, producing a structured markdown artifact. Key constraint: **no suggestions, no critiques** — the only job is documenting what exists.

HumanLayer's actual production prompt uses Opus explicitly and specialized subagent types (codebase-locator, codebase-analyzer, codebase-pattern-finder). Output includes file paths with line numbers.

### Phase 2: Plan

Read the research artifact (not the raw search results — that's the key). The agent presents its understanding, asks focused questions, then outputs a phased implementation plan with success criteria per phase.

### Phase 3: Implement

Follow the plan phase by phase. Update checkboxes in the plan file as sections complete. Pause for verification after each phase. On mismatch between expected and found state: stop and ask.

**The insight**: each phase gets a fresh context window that loads only its inputs (the previous phase's artifact). This prevents context pollution and keeps utilization at 40-60%.

### Ralphify mapping

This three-phase pattern maps directly to three separate ralphs, or to a single ralph that tracks phase in a state file:

```yaml
# research-ralph/RALPH.md
agent: claude --model opus
commands:
  - name: current_state
    run: cat research-output.md 2>/dev/null || echo "No research yet"
```

```yaml
# implement-ralph/RALPH.md
agent: claude
commands:
  - name: plan
    run: cat plan.md
  - name: test_results
    run: uv run pytest --tb=short 2>&1 | tail -20
```

## Context Window Management

### The Quality Equation (Horthy)

Context quality depends on four factors, in priority order:
1. **Correctness** — wrong information in context is the worst outcome
2. **Completeness** — missing information is second worst
3. **Size** — too much noise degrades output
4. **Trajectory** — the direction of the conversation matters

Practical rule: **keep utilization at 40-60%.** Above this, quality degrades measurably. The fix is intentional compaction — writing a structured summary to a file and starting a new session that reads only that file.

### Compaction prompt pattern

```
Write everything we did so far to progress.md. Include: the end goal,
the approach we're taking, steps completed, and the current failure
we're working on. Include relevant file paths with line numbers.
```

This is directly implementable as a ralph command — `cat progress.md` at the start of each iteration gives the agent continuity without accumulated context.

### The "Don't Allocate to Primary Context" Rule (Huntley)

The primary context window should operate as a **scheduler**. All expensive operations go to subagents:
- File searching → subagent
- Test execution and result summarization → subagent
- Only 1 subagent for build/test (avoid backpressure), unlimited for file search/read

Control parallelism explicitly in the prompt:
```
You may use up to [N] parallel subagents for all operations but only
1 subagent for build/tests.
```

For ralph loops, this means RALPH.md prompts should instruct agents to delegate search/read to subagents rather than doing it in the main context.

## The Double-Loop Model

Joe Dupuis (Test Double, June 2025) articulated a two-phase model that separates product discovery from engineering quality:

### Loop 1: Exploration ("Vibing")

- Iterate only on how the software *feels* and *looks*
- Do not read the generated code — treat it as disposable
- Run multiple agents in parallel exploring different directions
- Keep scope narrow but don't constrain the solution space
- The goal is convergence on **what to build**

### Loop 2: Refinement ("Painting the Shed")

- The agent opens a draft PR; the code will be suboptimal — that's expected
- Use the "McDonald's method": imperfect output is a crystallization seed
- Review like a normal code review: close acceptable files, leave open problematic ones
- Iterate via PR feedback; each cycle shrinks the diff
- Accept "clean, not perfect" — launch new agents for remaining small issues

### Anti-patterns this model identifies

- Over-specification before exploration (waterfall-style agentic coding)
- Treating generated code as final rather than as a seed
- Blocking PRs for perfection instead of shipping incrementally

### Mapping to ralph loops

The double-loop model suggests **two ralph configurations per project**:

1. **Exploration ralph**: Loose prompt, commands gather UI state or functional output, no linting/testing commands. Run on throwaway branches.
2. **Refinement ralph**: Strict prompt referencing conventions, commands run linters/tests/type checkers. Run on the branch being merged.

The transition between loops is a human decision: "this exploration output is good enough to refine."

## Steering Injection Patterns

### The "Sign Erection" Pattern (Huntley)

When the agent produces bad behavior, don't fix the output — add a "sign" to the prompt. The metaphor: Ralph comes home bruised because he fell off the slide, so you add a sign saying "SLIDE DOWN, DON'T JUMP."

Concrete examples of signs:
- Agent assumes code isn't implemented → `Before making changes, search codebase (don't assume not implemented)`
- Agent skips tests → `After implementing functionality, run the tests for that unit`
- Agent generates duplicate implementations → Narrow scope to "one item per loop"

This is the feedback loop that improves the harness over time — every failure becomes a prompt improvement.

### "On the Loop" vs. "In the Loop" (Kief Morris, March 2026)

Three human positions relative to the agent loop:

1. **Outside the loop** (vibe coding): Human defines "what", agent handles everything
2. **In the loop**: Human inspects every artifact (bottleneck, doesn't scale)
3. **On the loop** (recommended): Human engineers the harness that controls the loop

Key distinction: "in the loop" humans fix bad output. **"On the loop" humans fix the harness that produced bad output.** This creates a flywheel — every fix improves all future iterations.

For ralphify, this means the RALPH.md file itself is the primary artifact that gets refined over time, not the code the agent produces.

### "Relocating Rigor" (Chad Fowler, January 2026)

The principle: **probabilistic inside, deterministic at the edges.**

- Generation can be flexible/probabilistic
- Evaluation must be rigid and deterministic
- Tests written by humans, implementations generated by agents
- Interfaces are real contracts, not incidental boundaries
- Failures must be loud and immediate

This validates ralphify's architecture: commands (deterministic) provide the evaluation layer, while the agent prompt (probabilistic) handles generation.

## The Context Engineering Taxonomy (Bockeler, February 2026)

Birgitta Bockeler (Thoughtworks) proposed a clear taxonomy of context loading strategies:

| Level | What | Who decides | Example |
|-------|------|-------------|---------|
| Always-loaded | General conventions | Agent software | CLAUDE.md, RALPH.md frontmatter |
| Path-scoped | Rules for specific file types | Agent software | "*.sh files use ${var} not $var" |
| Lazy-loaded | Skills, docs, reference material | LLM | Agent skills invoked on demand |
| Human-triggered | Explicit workflows | Human | Slash commands, manual commands |
| Subagent | Isolated context operations | LLM or harness | Search, analysis, review |

For ralphify, this taxonomy maps to:
- **Always-loaded**: RALPH.md prompt + command outputs
- **Path-scoped**: Future feature — scoped rules based on what files the agent touches
- **Lazy-loaded**: Skills (already supported)
- **Subagent**: Delegated via prompt instructions (agent-dependent)

## Specification-Driven Workflow (Russ Poldrack)

A practitioner workflow that demonstrates mature prompt assembly:

1. **Phase 1**: Long conversation with LLM to produce specification files — PRD, PLANNING.md, TASKS.md. One spec per concept/module, stored in a `specs/` folder.
2. **Phase 2**: Custom `/freshstart` command loads all specs into fresh context, then works through tasks incrementally.

The specs are the persistent knowledge. The conversation is disposable. This is exactly the ralph pattern: commands load specs, the prompt body guides execution.

See [Chapter 6: Implications for Ralphify](06-ralphify-implications.md) for the consolidated prompt engineering lessons derived from these patterns.
