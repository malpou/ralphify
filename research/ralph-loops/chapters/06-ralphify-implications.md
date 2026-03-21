# Implications for Ralphify

> This chapter distills the full body of research into actionable directions for the ralphify framework: cookbook recipes worth building, framework features to consider, and how ralphify's existing design maps to validated patterns.

## What Ralphify Already Gets Right

The research validates several core design decisions:

1. **Fresh context per iteration** — the single most validated pattern across all practitioners. Every major system resets context each cycle. Ralphify's loop-with-fresh-invocation design is correct.

2. **Commands as dynamic context** — ralphify's `{{ commands.name }}` pattern is exactly how Anthropic, Spotify, and Karpathy assemble iteration-specific context. Commands load state; the prompt guides execution.

3. **File-based state, git as backend** — no production system uses a database or custom persistence. Git commits as checkpoints with revert-on-failure is the universal pattern. Ralphify's filesystem-native design fits.

4. **Simplicity** — a ralph is just a directory with RALPH.md. Karpathy proved that 630 lines can run 700 experiments. The "simple harness, powerful results" philosophy is validated.

5. **Skills as packages** — ralphify's skill system aligns with the industry direction of installable, reusable instruction sets (Addy Osmani's "agent skills as npm packages" trend).

## Where the Gaps Are

### Verification Gates (High Priority)

Every major system has converged on verification as the critical differentiator between amateur and expert harness engineering. Ralphify has no built-in verify step — users must build verification into their prompt or commands.

**Recommendation**: Add a `verify` field to RALPH.md frontmatter — commands that run *after* the agent completes, with results determining whether to keep or revert the iteration.

```yaml
verify:
  - name: tests
    run: uv run pytest
  - name: lint
    run: uv run ruff check
```

This is the single highest-impact framework improvement. It maps directly to:
- Karpathy's keep/revert based on val_bpb
- Spotify's auto-activating verifiers + stop hooks
- The autoresearch skill's verify/guard separation

### Revert-on-Failure (High Priority)

When verification fails, automatically `git revert` to the pre-iteration state. Karpathy's autoresearch, the uditgoenka skill, and pi-autoresearch all implement this. Note: use `git revert` (safe, creates new commit) not `git reset` (destructive).

### Iteration Metrics (Medium Priority)

Track per-iteration data: duration, verification pass/fail, token cost (if available). Surface this in the CLI and in a `results.tsv`-style log. Essential for:
- Cost awareness (the $47K incidents prove unbounded loops are dangerous)
- Optimization (knowing which iterations are productive)
- The statistical confidence scoring pattern (MAD-based, from pi-autoresearch)

### Scope Constraints (Medium Priority)

A `scope` frontmatter field listing editable files/directories would prevent agent scope creep — the #1 trigger for Spotify's LLM judge vetoes. Karpathy constrains the agent to a single editable file; this is the generalized version.

```yaml
scope:
  - src/ralphify/*.py
  - tests/
```

### Parallel Ralphs (Lower Priority, High Impact)

The `manager.py` concurrent run capability exists. The missing piece: coordination patterns.
- Shared state files that multiple ralphs read/write
- A "planner" ralph that generates task-specific RALPH.md files
- Fleet-style execution across isolated worktrees (like Conductor)

This maps to Karpathy's vision: "emulate a research community" of collaborative agents.

## Cookbook Recipes Worth Building

Ranked by validated practitioner demand and alignment with ralphify's strengths:

### 1. Autoresearch Ralph (Highest Value)

Replicate Karpathy's three-primitive pattern:
- **RALPH.md prompt**: Optimization strategy with `{{ commands.metrics }}` and `{{ commands.current_code }}`
- **Commands**: `run experiment` (time-boxed), `extract metrics`, `read current code`
- **Why**: The hottest use case in the space. Directly demonstrates ralphify for ML experimentation.

### 2. Code Migration Ralph

Spotify's Honk use case:
- **RALPH.md prompt**: Migration spec with `{{ commands.test_results }}` and `{{ commands.remaining }}`
- **Commands**: `run tests`, `count files still using old pattern`
- **Why**: Batch code transformation is the most proven high-value agent use case at enterprise scale.

### 3. PRD-Driven Development Ralph

The snarktank/ralph pattern for product development:
- **RALPH.md prompt**: User stories + acceptance criteria from `{{ commands.prd }}`
- **Commands**: `read prd.json`, `run acceptance tests`, `show progress`
- **Why**: Maps the most practical product development workflow directly to a ralph.

### 4. Test Coverage Ralph

Iterative test generation with clear scalar metric:
- **RALPH.md prompt**: Coverage targets + `{{ commands.coverage }}` + `{{ commands.uncovered }}`
- **Commands**: `run coverage report`, `list uncovered functions`
- **Why**: Coverage % is as clear a scalar metric as val_bpb — great for demonstrating the optimization loop.

### 5. Security Scan Ralph

Iterative security review loop:
- **RALPH.md prompt**: Security checklist + `{{ commands.scan_results }}` + `{{ commands.open_issues }}`
- **Commands**: `run security scanner`, `list open findings`
- **Why**: Continuous security improvement with diminishing-returns stopping criterion.

### 6. Three-Phase Development Ralph

The research→plan→implement pattern (HumanLayer, Anthropic, Test Double):
- Three separate ralphs, each loading only the previous phase's output
- Research ralph → `research-output.md`; Plan ralph → `plan.md`; Implement ralph → code
- **Why**: The most validated workflow for non-trivial features. Each phase gets a clean context window.

## Prompt Engineering Lessons for RALPH.md Authors

Distilled from all chapters — the practical "how-to" for writing effective ralphs:

1. **One item per loop.** Every practitioner system limits each iteration to a single task. Batching causes drift.

2. **Commands as context loaders.** Use commands to load progress, test results, and spec files — not to do the work.

3. **Redirect verbose output.** `> run.log 2>&1` then `grep` for metrics. Never let raw test output flood context. This is the single most impactful technique for loop reliability.

4. **Instruct subagent delegation.** Tell the agent to use subagents for search/read so the main context stays clean. Limit build/test to 1 subagent (backpressure risk).

5. **Evolve the prompt, not the output.** When the agent fails, add a "sign" to RALPH.md. Every prompt improvement benefits all future iterations — the "on the loop" flywheel.

6. **Keep RALPH.md under 300 lines.** The 150-200 instruction ceiling is real. Use the prompt as a router to detailed docs, not a monolith.

7. **Show, don't tell.** Code examples beat prose 3:1 for agent instruction. Show the pattern you want.

8. **Probabilistic inside, deterministic at edges.** Commands (deterministic) evaluate; the prompt (probabilistic) generates. Tests written by humans, implementations generated by agents.

## Competitive Positioning

Ralphify sits at a validated sweet spot: simpler than full orchestration frameworks (LangGraph, CrewAI) but more structured than raw bash loops. The Karpathy autoresearch moment — 630 lines running 700 experiments — proves that "simple harness, powerful results" wins.

The key differentiator to develop: **verification as a first-class citizen.** Every major system has converged on this. Making it native to RALPH.md frontmatter would be the single highest-impact framework improvement, and no other tool in ralphify's weight class offers it.
