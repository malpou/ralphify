# UX/UI Simplification Analysis

## Users' Jobs to Be Done

Based on the JTBD research and codebase analysis, these are the core jobs users hire ralphify to do, ranked by frequency × intensity:

1. **Ship features while I'm not coding** (J1) — Set agent running autonomously, wake up to working code. VERY HIGH frequency/intensity.
2. **Keep the agent from going off the rails** (J2) — Automatic quality gates that catch bad work. VERY HIGH frequency/intensity.
3. **Stop babysitting the agent** (J3) — Step away and let the agent work independently. HIGH frequency/intensity.
4. **Have a reliable, repeatable workflow** (J5) — Replace fragile bash scripts with structured primitives. HIGH frequency/intensity.
5. **Feel in control even when autonomous** (J6) — See what happened each iteration without reviewing every line. HIGH frequency/intensity.

These jobs map to five user-facing workflows:
- **Setup**: Go from zero to a running loop
- **Run**: Launch and configure the loop
- **Monitor**: Watch progress and understand what happened
- **Steer**: Adjust the agent's behavior while running
- **Trust**: Know the output is good via checks

---

## Current UX Audit

### Surface Area Inventory

**CLI Commands (5):**
| Command | Purpose |
|---|---|
| `ralph init` | Create ralph.toml + RALPH.md |
| `ralph run [name]` | Start the autonomous loop |
| `ralph status` | Validate setup and list primitives |
| `ralph new <type> <name>` | Scaffold a new primitive |
| `ralph ui` | Launch web dashboard |

**`ralph run` Flags (8):**
| Flag | Short | Purpose |
|---|---|---|
| `[RALPH_NAME]` | positional | Named ralph to use |
| `--prompt` | `-p` | Inline prompt text |
| `--prompt-file` | `-f` | Path to prompt file |
| `-n` | | Max iterations |
| `--stop-on-error` | `-s` | Stop if agent fails |
| `--delay` | `-d` | Seconds between iterations |
| `--log-dir` | `-l` | Directory for logs |
| `--timeout` | `-t` | Max seconds per iteration |

**Concepts Users Must Learn (10):**
1. ralph.toml (config file)
2. RALPH.md (root prompt file)
3. .ralphify/ directory (primitives home)
4. Checks (validation scripts)
5. Contexts (dynamic data injection)
6. Instructions (static reusable rules)
7. Ralphs (named prompt variants)
8. Template placeholders (`{{ contexts.name }}`, `{{ instructions }}`)
9. Frontmatter (YAML config in markdown)
10. Failure instructions (body text in CHECK.md)

**Config Files:**
- `ralph.toml` — agent command, args, default ralph
- `RALPH.md` — root prompt (or named ralph)
- `.ralphify/checks/<name>/CHECK.md` — check config + failure instruction
- `.ralphify/contexts/<name>/CONTEXT.md` — context config + static header
- `.ralphify/instructions/<name>/INSTRUCTION.md` — instruction body
- `.ralphify/ralphs/<name>/RALPH.md` — named ralph prompt

---

## Friction Log

### Job: Setup (Go from zero to running loop)

**Steps walked through:**

1. `pip install ralphify` (or `uv tool install ralphify`) — fine
2. `ralph init` — creates ralph.toml + RALPH.md
3. User must edit RALPH.md manually — the template is generic ("Your prompt content here" equivalent)
4. User must know to run `ralph new check tests` to add quality gates
5. User must understand frontmatter syntax to configure the check command
6. User must edit ralph.toml if not using Claude Code (default is `claude` with `--dangerously-skip-permissions`)
7. `ralph status` to validate — good, but optional step users might skip
8. `ralph run -n 1` to test — must know to limit iterations for first try

**Friction points identified:**

- **F1: `ralph init` creates a useless prompt** (VALIDATED). The ROOT_RALPH_TEMPLATE at `_templates.py:61-74` is a generic skeleton. It says "Add your project-specific instructions below" but gives no guidance on what those should be. The user's very first edit is staring at a mostly-empty file. Compare: `git init` creates a working repo immediately.

- **F2: No checks created by default** (VALIDATED). After `ralph init`, running `ralph run` will start an agent loop with zero quality gates. The most important differentiator of ralphify (the self-healing feedback loop) is completely absent until the user manually discovers and runs `ralph new check`. This contradicts J2 (keep the agent from going off the rails), which is the #2 job.

- **F3: `detect_project()` does nothing with its result** (VALIDATED). The detector (`detector.py:11-27`) identifies Python/Node/Rust/Go projects, prints "Detected project type: python" during init, but takes no action. It doesn't create project-appropriate checks (e.g., `pytest` for Python, `npm test` for Node), doesn't customize the ralph.toml, and doesn't tailor the RALPH.md template. The user sees information but gets no benefit from it.

- **F4: Scaffolded templates are full of HTML comments explaining the format** (VALIDATED). The CHECK_MD_TEMPLATE, CONTEXT_MD_TEMPLATE, and INSTRUCTION_MD_TEMPLATE all contain multi-line HTML comments explaining the format rather than providing useful defaults. While comments are stripped from the assembled prompt (via `_HTML_COMMENT_RE` in `_frontmatter.py`), they create noise when the user opens the file to edit it. The check template defaults to `ruff check .` which may not be installed.

- **F5: 12-step getting started guide** (VALIDATED from docs). The documented onboarding flow is 12 steps. The minimum viable loop (init → edit prompt → add check → run) is 4 steps with manual editing. Could be fewer.

### Job: Run (Launch the loop)

**Steps walked through:**

1. `ralph run` — uses ralph.toml defaults, works
2. `ralph run docs` — named ralph, works if it exists
3. `ralph run -n 3 --timeout 300 --log-dir logs` — full invocation

**Friction points identified:**

- **F6: Three ways to specify a prompt, unclear priority** (VALIDATED). Users can provide a prompt via: (a) positional `[RALPH_NAME]`, (b) `--prompt-file`/`-f`, (c) `--prompt`/`-p`, or (d) `ralph.toml`'s `ralph` field. The resolution chain in `ralphs.py:89-121` has a 4-level priority system. Using both `prompt_name` and `prompt_file` is an error (`cli.py:304-306`). This creates unnecessary cognitive load — "which one wins?" is a question users shouldn't have to answer.

- **F7: `--prompt-file` / `-f` is redundant** (VALIDATED). The `ralph.toml` already has a `ralph` field that can point to any file. Named ralphs live in `.ralphify/ralphs/`. Between the toml config and the positional argument, `--prompt-file` serves an edge case (one-off file that's not a named ralph and not the default). It adds a flag to learn and a conflict to handle (`cli.py:304-306`).

- **F8: Banner prints on every `ralph run`** (VALIDATED). The ASCII art banner (`cli.py:58-107`) prints every time the user runs `ralph run`. It's nice on first launch but wastes 8 lines of vertical space on subsequent runs. The "Star us on GitHub" line is promotional, not functional. During iteration, vertical space matters — users are scanning for check results and iteration status.

- **F9: No default for `-n` (iteration limit)** (VALIDATED). If the user omits `-n`, the loop runs infinitely until Ctrl+C. For new users, this is risky — J9 (prevent runaway costs) is a validated job. A sensible default (e.g., `-n 5` or `-n 10`) with an explicit `--infinite` flag would protect new users while allowing power users to opt in.

### Job: Monitor (Understand what happened)

**Steps walked through:**

1. During run: see iteration headers, spinner with elapsed time, check results
2. After run: summary line ("Done: 3 iteration(s) — 3 succeeded")
3. With `--log-dir`: per-iteration log files with full agent output

**Friction points identified:**

- **F10: No default log directory** (VALIDATED). Without `--log-dir`, all agent output is lost after the run. The user has to remember to add `--log-dir logs` every time. This contradicts J6 (feel in control even when autonomous) — you can't feel in control if you can't review what happened. Most users who care about quality will want logs. Should be on by default.

- **F11: Check failure output is truncated to 5,000 chars with no warning** (VALIDATED). `_output.py` truncates output to 5,000 characters. This is injected into the next iteration's prompt. If a test suite produces verbose output, the user may not realize critical failure information was cut off. There's no indicator in the CLI output that truncation occurred.

- **F12: Iteration output is minimal during run** (VALIDATED). The console emitter (`_console_emitter.py`) shows: iteration header, spinner, completion status, check pass/fail summary. It does NOT show: which prompt was used, how many contexts/instructions were resolved, prompt length, or any preview of what the agent was told. For J6 (feel in control), users would benefit from knowing what went into each iteration.

### Job: Steer (Adjust behavior while running)

**Steps walked through:**

1. Edit RALPH.md in another terminal — re-read each iteration (works!)
2. Adding/removing checks, contexts, instructions — requires restart
3. Editing check commands — requires restart

**Friction points identified:**

- **F13: Primitive config is frozen at startup — not documented in CLI** (VALIDATED). The engine discovers primitives once at startup (`engine.py:386`). New checks, contexts, or instructions added while running are invisible until restart. The docs mention this, but the CLI gives zero indication. Users who add a check and expect it to run next iteration will be confused.

- **F14: No signal when RALPH.md changes are picked up** (VALIDATED). RALPH.md is re-read each iteration (`engine.py:191`), which is great for steering. But the console shows no indication that the prompt changed. Users editing RALPH.md while running have no confirmation their edits took effect.

### Job: Trust (Know the output is good)

**Steps walked through:**

1. Checks run after each iteration
2. Failures feed back into next iteration's prompt
3. `ralph status` shows which checks are configured

**Friction points identified:**

- **F15: No guidance on WHAT checks to add** (VALIDATED). `ralph new check <name>` scaffolds an empty check. The template defaults to `ruff check .`. There's no "common checks" suggestion based on project type, no example library, and no indication of what good checks look like for the user's specific job.

- **F16: Silent context/instruction exclusion with named placeholders** (VALIDATED). From `resolver.py:43-55`: if you use `{{ contexts.git-log }}` without a `{{ contexts }}` bulk placeholder, ALL other contexts are silently dropped. There's no warning. This is documented in the docs but is a subtle, high-impact gotcha that violates the principle of least surprise.

---

## Simplification Opportunities

Ranked by: (impact on user's job) × (frequency of the job) / (effort + risk)

### Tier 1: High Impact, Low Effort

#### O1: Smart `ralph init` — auto-create project-appropriate checks
**What:** When `ralph init` detects a Python project, auto-create `.ralphify/checks/tests/CHECK.md` with `command: uv run pytest -x` (or `npm test` for Node, `cargo test` for Rust, etc.). Similarly auto-create a lint check appropriate to the ecosystem.
**Why:** Removes F2 (no checks by default) and F3 (detect_project does nothing). The core value of ralphify — self-healing feedback loops — should be active from the first run, not after manual setup.
**Job:** Setup (J1, J2, J5)
**Effort:** S — `detect_project()` already identifies the ecosystem; just need to call `_scaffold_primitive` with appropriate templates per project type.
**Risk:** Low. Generated checks might not match the user's exact setup (e.g., they use `pytest` not `uv run pytest`). Mitigate by making generated checks obviously editable and running `ralph status` to validate.

#### O2: Default log directory (`ralph_logs/`)
**What:** Always log to `ralph_logs/` unless `--no-logs` is explicitly passed. Add `ralph_logs/` to `.gitignore` guidance.
**Why:** Removes F10. Every user running loops for real needs logs for J6 (feel in control). Requiring `--log-dir` every time is a footgun for new users.
**Job:** Monitor, Trust (J6)
**Effort:** S — one default value change in `cli.py:283`.
**Risk:** Very low. Disk space is cheap. Users who don't want logs can opt out.

#### O3: Default iteration limit (e.g., 5)
**What:** Change `-n` default from unlimited to 5. Add `--no-limit` or `-n 0` for infinite mode.
**Why:** Removes F9. Protects new users from runaway costs (J9). Power users can easily opt into infinite mode.
**Job:** Run, Trust (J1, J9)
**Effort:** S — one default value change.
**Risk:** Medium. Existing users who rely on infinite loops will need to add `--no-limit`. But this is the safer default — it's far worse to accidentally run an infinite loop than to have to type `--no-limit`.

#### O4: Suppress banner on subsequent runs / add `--quiet`
**What:** Only show banner on `ralph` (no subcommand). Don't print it on `ralph run`. Or add `--quiet` flag.
**Why:** Removes F8. Saves 8+ lines of vertical space every run. Users running `ralph run` repeatedly (the core workflow) don't need the logo each time.
**Job:** Monitor (J6)
**Effort:** S — remove `_print_banner()` call from `run()` at `cli.py:293`.
**Risk:** Very low. The banner still shows on bare `ralph` command.

### Tier 2: High Impact, Medium Effort

#### O5: Remove `--prompt-file` / `-f` flag
**What:** Remove the `--prompt-file` flag entirely. Users who want a custom file put the path in `ralph.toml`'s `ralph` field.
**Why:** Removes F6 (three ways to specify prompt) and F7 (redundant flag). Simplifies the run command from 8 flags to 7. Eliminates the error case where both `prompt_name` and `--prompt-file` are used.
**Job:** Run (J1, J5)
**Effort:** S-M — remove flag from CLI, simplify `resolve_ralph_source()`, update docs.
**Risk:** Medium. Breaks any user currently using `--prompt-file`. But the toml config or named ralphs cover every use case.

#### O6: Warn on silent context/instruction exclusion
**What:** When named placeholders are used without a bulk placeholder, emit a warning listing which contexts/instructions were excluded.
**Why:** Removes F16. Prevents subtle prompt assembly bugs that undermine J2 (keep agent from going off the rails).
**Job:** Trust (J2, J6)
**Effort:** S-M — add a warning in `resolve_placeholders()` when `has_named` is true and no bulk placeholder exists and there are remaining items.
**Risk:** Low. Warnings are informational and non-breaking.

#### O7: Show prompt assembly summary per iteration
**What:** After prompt is assembled, print one line: `Prompt: 2,847 chars | Contexts: 3 | Instructions: 2 | Check failures: 1`.
**Why:** Addresses F12 and F14. Users can see at a glance what went into each iteration. If they edit RALPH.md and the char count changes, they know it took effect.
**Job:** Monitor, Steer (J6)
**Effort:** S — the data is already in `EventType.PROMPT_ASSEMBLED` event; just render it in `ConsoleEmitter`.
**Risk:** Very low. One extra line of output per iteration.

#### O8: Better `ralph init` prompt template with guided sections
**What:** Replace the generic ROOT_RALPH_TEMPLATE with a structured template that has labeled sections: Role, Task (with a pointer to a TODO.md pattern), Constraints, Process. Include a comment explaining each section.
**Why:** Addresses F1. The prompt is the most important file in the entire setup — it shouldn't be the one that gets the least guidance.
**Job:** Setup (J1, J5)
**Effort:** S — just change the template string.
**Risk:** Low. More opinionated template, but the current one is too minimal to be useful.

### Tier 3: Medium Impact, Medium Effort

#### O9: Hot-reload primitives
**What:** Re-discover checks, contexts, and instructions at the start of each iteration (not just startup).
**Why:** Addresses F13. Users can add/modify checks while the loop runs without restarting. Makes the steering experience consistent — if RALPH.md can change mid-run, why can't checks?
**Job:** Steer (J3, J6)
**Effort:** M — move `_discover_enabled_primitives()` call into the iteration loop. Note: a `consume_reload_request()` mechanism already exists in the engine (`engine.py:164-170`), so the infrastructure is partially there.
**Risk:** Medium. Discovery is filesystem I/O — adds latency per iteration. Could be mitigated by checking mtimes. Also, adding a check mid-run that fails could surprise the agent if it wasn't prompted to address that check.

#### O10: Merge "instructions" into RALPH.md / checks
**What:** Eliminate the "instructions" primitive type. Static instructions belong in RALPH.md directly. Per-check instructions are already the CHECK.md body (failure instructions). The template placeholder `{{ instructions }}` can be replaced by just writing the content in the prompt.
**Why:** Reduces concept count from 10 to 9. Instructions are the least differentiated primitive — they're just static text. Contexts have commands (dynamic), checks have commands + failure feedback. Instructions have... nothing special. They're a text include mechanism.
**Job:** Setup, Steer (all jobs, indirectly)
**Effort:** L — breaking change, requires migration path for existing users with instructions.
**Risk:** High. Some users may have built workflows around instructions as a separate concept (e.g., shared instructions across multiple ralphs). The composability argument is valid. **Consider instead**: just deprioritize instructions in docs and scaffolding, so new users don't encounter them until needed.

#### O11: Truncation indicator in CLI output
**What:** When check output or context output is truncated (>5,000 chars), show `[truncated — 12,847 chars total, showing first 5,000]` in the CLI.
**Why:** Addresses F11. Users know when they're seeing partial information and can check full logs.
**Job:** Monitor, Trust (J6)
**Effort:** S — add a return value or flag from `truncate_output()`.
**Risk:** Very low.

### Tier 4: Exploratory / Higher Risk

#### O12: `ralph init --interactive` wizard
**What:** Interactive setup that asks: What agent? (Claude/Aider/custom), What should it work on? (generates RALPH.md), What checks? (tests/lint/typecheck based on project). Falls back to current non-interactive behavior by default.
**Why:** Could reduce 12-step onboarding to 1 command. But adds complexity and interactive UX is harder to test.
**Job:** Setup (J1, J5)
**Effort:** L
**Risk:** Medium. Interactive prompts can be annoying in CI/automation. Must remain optional.

#### O13: Reduce `-p`/`--prompt` to just positional override
**What:** Instead of a separate `--prompt` flag for inline text, let `ralph run "Fix the login bug"` work as an inline prompt (detected by the string not matching any named ralph).
**Why:** More natural CLI UX. `ralph run "Fix the login bug"` vs `ralph run -p "Fix the login bug"`.
**Job:** Run (J1)
**Effort:** M — need to disambiguate between ralph names and inline prompts.
**Risk:** Medium. How do you distinguish `ralph run docs` (named ralph) from `ralph run "docs"` (inline prompt)? Could use quoting as the signal, but fragile.

---

## Principles Applied

| Principle | Where Applied |
|---|---|
| **Sensible defaults** | O1 (auto-create checks), O2 (default logs), O3 (default iteration limit) |
| **Remove before you add** | O5 (remove --prompt-file), O10 (merge instructions) |
| **Fewer concepts** | O10 (merge instructions into prompt/checks) |
| **Progressive disclosure** | O3 (safe default, opt into infinite), O4 (banner only when relevant) |
| **Convention over configuration** | O1 (detect project, create appropriate checks), O2 (default log dir) |
| **Clear feedback** | O6 (warn on silent exclusion), O7 (prompt summary), O11 (truncation indicator), O14 (change detection) |
| **Fewer steps** | O1 (init creates working setup), O8 (better template) |
| **Obvious naming** | Not a major issue — command names are clear |

---

## Open Questions

1. **How many users currently use `--prompt-file`?** If the answer is "almost none," removing it (O5) is safe. If some users depend on it, provide a migration period.

2. **What's the right default for `-n`?** Proposed: 5. But should it be 3? 10? Could also scale with project type or check count. Needs user testing.

3. **Should instructions be deprecated or just deprioritized?** O10 proposes merging them into other concepts. The composability argument (shared instructions across ralphs) is real. Alternative: keep them but don't scaffold them during init or mention them in getting-started docs.

4. **Would hot-reloading primitives (O9) confuse the agent?** If a new check appears mid-run, the agent hasn't been told about it. The failure feedback will mention it, but the agent might be confused by a check it wasn't originally instructed to satisfy.

5. **Is the banner (O4) important for brand recognition?** It uses vertical space but creates visual identity. Compromise: show it only on first run per session, or make it one line instead of six.

6. **What percentage of new users run `ralph status` before `ralph run`?** If most skip validation, the quality gates in `status` aren't providing value. Consider running status checks automatically as part of `ralph run` (emit warnings, not errors).

7. **Does `detect_project()` need to be more sophisticated?** It checks 4 manifest files. Many projects have multiple (e.g., Python + Node). Should it support multi-ecosystem projects? Or is the first-match heuristic good enough for auto-scaffolding checks?

8. **Should the `-p` inline prompt automatically set `-n 1`?** Inline prompts (`ralph run -p "quick task"`) are almost always one-off. Making them default to 1 iteration would remove a footgun without affecting named ralphs.
