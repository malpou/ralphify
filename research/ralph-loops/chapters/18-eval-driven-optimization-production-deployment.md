# Eval-Driven Optimization & Production Deployment

> The meta-loop — an outer agent that optimizes an inner agent's configuration via eval feedback — is now implemented by at least 5 independent systems. Meanwhile, agent loops have graduated from local laptops to CI/CD pipelines and cloud VMs, with three distinct deployment tiers emerging.

## The Meta-Loop Pattern

The concept of "a ralph that optimizes other ralphs" exists under several names but follows a universal structure:

1. **Baseline agent** executes tasks
2. **Feedback collected** (eval scores, human review, LLM-as-judge)
3. **Meta-agent** generates improved instructions from failure analysis
4. **Updated agent** deployed; loop repeats

### Implementations

**OpenAI's Self-Evolving Agents Cookbook** describes the canonical version: a metaprompt agent analyzes failures and generates improved instructions. Promotion happens when a "lenient pass threshold" (75% of graders passing) is achieved. The system maintains prompt version history and aggregate performance stats.

**Weco** (open-source predecessor: AIDE, ranked #1 on OpenAI's MLE-Bench) is the purest implementation — you provide an evaluation script, and Weco's tree-search engine proposes changes, tests them, and iterates autonomously. Founder Collective calls it: "Claude Code helps you build. Weco helps you evolve."

**Arize Phoenix PromptLearning** applied automated meta-prompting to optimize `.clinerules` / `CLAUDE.md` files specifically for coding agents. On SWE-bench Lite (300 examples, 150 train / 150 test): Claude Sonnet 4.5 saw +6% accuracy, GPT-4.1 closed the gap to Sonnet-level performance. Generated rulesets of 20-50 rules emphasizing edge case handling, root-cause diagnosis, and API contract preservation.

**IBM's AutoPDL** frames agent prompt optimization as a structured AutoML problem using successive halving to navigate the combinatorial space of prompting patterns (Zero-Shot, CoT, ReAct, ReWOO). Results: 9.21 ± 15.46 percentage point accuracy gains across 3 tasks and 7 LLMs, with gains up to 67.5pp.

**Evidently AI** implements a mistake-driven feedback loop inspired by RLHF: identify mistakes → collect error examples with context → ask LLM to improve prompt. Uses train/validation/test splits (40/40/20) with early stopping to prevent overfitting.

### Key Insight: The Meta-Loop is Domain-Agnostic

All five implementations share the same structure regardless of domain. The eval script is the only domain-specific component. For ralphify, this means a "meta-ralph" that optimizes RALPH.md files is architecturally straightforward: the inner ralph runs tasks, commands capture eval scores, and the outer ralph rewrites the inner ralph's prompt based on failure patterns.

## Eval-Driven Development (EDD) as Methodology

EDD has converged as the dominant methodology for iterating on agent configurations. The core cycle: **define correctness → measure → improve → repeat**.

### The Swiss Cheese Model (Anthropic)

Anthropic's "Demystifying Evals for AI Agents" recommends layered evaluation where each layer catches different failures:

1. **Automated evals** — deterministic checks, trajectory validation
2. **Production monitoring** — live quality scores, cost tracking
3. **A/B testing** — comparative deployment of configurations
4. **Manual transcript review** — human reading of agent sessions

Eight-step roadmap: start with 20-50 tasks from actual user failures, maintain stable isolated environments, read transcripts regularly, monitor for eval saturation (100% pass rates provide no signal).

### Evals in CI/CD

The "eval on every PR" pattern is now supported by mature tooling:

- **Promptfoo** (acquired by OpenAI, March 16, 2026): GitHub Action for before-vs-after eval on every PR. Supports Claude Agent SDK and Codex SDK. Trajectory tracing via `trajectory:step-count`. Cost and latency assertions. Used by 25%+ of Fortune 500.
- **Braintrust**: MCP server connects coding agents to eval stack. Regression gates automatically block deployments below quality thresholds. "Loop" feature generates custom evaluators from natural language.
- **LangSmith**: Full CI/CD pipeline via GitHub Actions with LangGraph orchestration. Quality-gated production releases. PR-triggered eval workflows for multi-agent systems.
- **Langfuse**: Open-source, self-hostable. Dashboard-driven (more accessible for non-engineers). Less CI/CD-native than LangSmith; better for observability.

### pass@k vs pass^k: The Reliability Gap

Phil Schmid's definitive analysis: an agent with 70% individual success rate (k=3):
- **pass@3**: ~97% (misleadingly near-certain)
- **pass^3**: 34.3% (only one-third chance of consistent success)

Paul Simmering proposes three enterprise readiness tiers based on pass^k degradation:
- **Internal tools** (ready now): 74-90% accuracy acceptable with human review
- **Customer-facing** (limited): 80% pass^1 but "drops significantly on pass^8"
- **Long-running autonomous** (not ready): agents experience "meltdowns" — "once an agent misinterprets its situation, it tends to spiral rather than self-correct"

**Promotion gates**: Changes must meet defined pass@k thresholds before moving dev → staging → production. Promptfoo recommends `--repeat 3` minimum; teams needing high reliability run k=5 or k=10.

## Production Deployment Tiers

Three distinct deployment tiers have emerged for running agent loops in production:

### Tier 1: Session-Scoped (Local)

Claude Code's `/loop` enables cron-style scheduling within a terminal session. Up to 50 concurrent tasks, 3-day auto-expiry, jitter to avoid API thundering herd. Session-scoped — tasks die when the terminal exits. Use cases: overnight PR monitoring, automated bug triage, morning summaries.

### Tier 2: CI/CD-Integrated (Durable)

**GitHub Agentic Workflows** (Technical Preview, Feb 2026): agentic workflows defined in Markdown + YAML frontmatter, compiled to GitHub Actions lock files. AI agents (Copilot, Claude Code, Codex) interpret natural-language instructions for event-triggered or scheduled jobs. Workflows are version-controlled and reviewed in PRs. Read-only permissions by default; PRs never auto-merged. GitHub calls this "Continuous AI."

**Claude Code GitHub Action** (`anthropics/claude-code-action@v1`): runs on any GitHub event — `@claude` mentions, issue assignments, PR reviews, or cron schedules. Scheduled execution uses standard cron syntax. Claude respects `CLAUDE.md`.

**Codex GitHub Action** (`openai/codex-action@v1`): installs Codex CLI, runs `codex exec` under specified permissions. OpenAI plans a future "automation cloud" where Codex Jobs run entirely in OpenAI's cloud on triggers.

### Tier 3: Cloud-Native (Isolated VMs)

**Cursor Cloud Agents**: 35% of Cursor's internal merged PRs are created by autonomous cloud agents. Each agent gets its own VM, environment, and sandbox. Up to 8 agents in parallel on a single prompt. Triggered from Slack, Linear, GitHub, or the Cursor editor. 99.9% reliability claimed.

**Codex Cloud Sandbox**: Each task runs in its own cloud sandbox, preloaded with your repository. Two-phase runtime: setup (network-enabled for dependency install) then agent phase (offline by default). Secrets available only during setup, removed before agent starts.

**Coder Tasks**: Cloud development environments where Claude Code runs from GitHub issue to pull request in isolated workspaces.

## Scheduled Agent Execution Patterns

### Production Cron Systems

**earezki's Dev|Journal** documents a production system running 23 concurrent cron jobs: SQLite with WAL mode as coordination layer, file-based locks in `/tmp/agent-locks`, logrotate with `copytruncate` for persistent logging. Example schedule: 7AM discovery → 8AM research → 9AM preparation → 11AM execution → 11PM review. Two critical failure modes: context pollution from excessive tools, and data loss without item-level commits.

**Geta Team** built a centralized shared scheduler (~200 lines of JavaScript) managing 100+ agents with hundreds of tasks on a single container. Hot config reload via file watchers (~200ms). Per-agent JSON config with cron expressions. Core principle: "One cron daemon for all agents."

### The Reliability Math Problem

A 99%-accurate step repeated 20 times yields ~82% end-to-end reliability. This is why:
- Fresh-context loops (the ralph pattern) reduce step count per iteration
- Budget-aware execution prevents compounding cost from degraded quality
- Circuit breakers catch spiraling before 20 steps accumulate

### Team Workflows

**Claude Code Agent Teams** (experimental, Feb 2026): orchestrating teams of Claude Code sessions. One lead coordinates; teammates work independently in their own context windows and can communicate directly (unlike subagents). Best for 3-5 teammates.

**AGENTS.md as cross-tool standard**: the emerging team coordination layer. A single source of truth for agent rules that works across Claude Code, Cursor, Codex, and other tools. Cursor reads both `AGENTS.md` and `CLAUDE.md` alongside `.cursor/rules`.

## Agent Observability in Production

Observability has consolidated around 5 platforms:
- **Braintrust**: eval-integrated, per-request cost, tag-based attribution, regression alerts
- **Langfuse**: open-source, self-hostable, dashboard-driven
- **Helicone**: proxy-based cost optimization, caching
- **Galileo**: real-time safety checks, agent graph tracing, per-step evaluation
- **Datadog**: enterprise integration, infrastructure-grade monitoring

Common pattern: proxy-based cost gateway (Helicone) + eval platform (Braintrust) + aggregate token alerts.

Key data points from Anthropic's 2026 Agentic Coding Trends Report:
- 95% of professional developers use AI coding tools weekly
- 75% rely on AI for at least half their work
- Rakuten: 99.9% accuracy on 12.5M-line codebase in 7 autonomous hours
- TELUS: 30% faster, 500K+ hours saved
- Zapier: 89% AI adoption, 800+ deployed agents
- Only 0-20% of tasks can be fully delegated

## Implications for Ralphify

### Eval Integration

Ralphify's command system maps directly to the eval flywheel:
- Commands capture test/eval results as dynamic context
- The prompt incorporates pass/fail signals
- A "meta-ralph" wrapping an inner ralph for prompt optimization is architecturally natural

**Concrete recipe**: a meta-ralph whose commands run the inner ralph N times, parse pass/fail results, and whose prompt instructs the agent to improve the inner RALPH.md based on failure patterns.

### Production Deployment

Ralphify ralphs are already GitHub Action-ready — they're just directories with a RALPH.md file. The path to production:
1. **Local**: `ralph run` in terminal (today)
2. **CI/CD**: GitHub Action that installs ralphify + runs `ralph run` on schedule/event
3. **Cloud**: Dockerized ralph execution in cloud sandboxes

The gap: ralphify has no native support for scheduled execution, event triggers, or multi-ralph coordination. These could be built as:
- A `ralph schedule` command (thin wrapper around cron/GitHub Actions config generation)
- Event-triggered ralphs (file watcher, webhook, GitHub event)
- A `ralph team` command for parallel execution with shared state

### Configuration as Code

GitHub's agentic workflows prove that "Markdown + YAML frontmatter → compiled to CI/CD" works. Ralphify's RALPH.md format is already this pattern. The competitive advantage: ralphify ralphs are portable across execution environments (local, CI, cloud) without format changes.
