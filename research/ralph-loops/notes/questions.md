# Research Questions

## Open
- [ ] How do practitioners handle non-deterministic verification (e.g., subjective quality in writing/design tasks)?
- [ ] What's the optimal iteration length for different task types (coding vs. research vs. optimization)?
- [ ] What patterns exist for gradually increasing agent autonomy as trust builds?
- [ ] How does the "agent skill" packaging ecosystem evolve — will there be a registry/marketplace?
- [ ] What's the real-world false negative rate for LLM-as-judge verification beyond Spotify's 25%?
- [ ] What's the optimal CLAUDE.md/RALPH.md length for different project types? (HumanLayer says <300 lines, but is this validated beyond their experience?)
- [ ] What statistical methods beyond MAD are practitioners using for confidence scoring in optimization loops?
- [ ] What emerging tools/frameworks are challenging the "simple harness" philosophy? Are orchestration frameworks finding their niche?

## Answered
- [x] What are the most effective patterns for keeping agents on track during long-running loops? — Fresh context resets + file-based state + verification gates. See chapters 01-02.
- [x] How do practitioners handle context window limits? — Reset context each iteration; persist state in files and git. Universal pattern across all major systems.
- [x] What error recovery strategies work best? — Git revert on verification failure (Karpathy), failure pattern runbooks (Meta REA), verifier re-runs (Spotify). See chapter 02.
- [x] What are the highest-value use cases for autonomous agents? — ML optimization (autoresearch), code migration (Spotify Honk), long-horizon feature building (Codex), ads ranking (Meta REA). See chapter 04.
- [x] How do people structure prompts for iterative agent work? — Three-phase architecture (research→plan→implement), specification docs + dynamic command outputs + progress state. See chapter 09.
- [x] What state management approaches exist? — Git + 3-4 markdown files (spec, progress, tasks, knowledge base). See chapter 01.
- [x] What novel ralph/recipe patterns could we document? — Autoresearch, migration, PRD-driven, test coverage, security scan, three-phase development. See chapter 06.
- [x] What are the main failure modes of autonomous agent loops? — Ten recurring anti-patterns: one-shotting, context poisoning, doom loops, unbounded autonomy, comprehension debt, premature completion, model-blaming, same-model judging, instruction overload, unreviewed PRs. See chapter 07.
- [x] What memory/learning mechanisms persist across loop sessions? — Self-improvement loops via lessons.md + MEMORY.md with SessionStart hooks. Verification canaries detect instruction fade. See chapter 08.
- [x] What real-world CLAUDE.md/AGENTS.md examples exist? — Freek Van der Herten (<15 lines), GitHub's 2,500+ analysis (six core areas), morphllm templates (domain-specific). See chapter 08.
- [x] How does the double-loop model map to agent workflows? — Loop 1 (exploration/vibing) then Loop 2 (refinement/review). Two ralph configurations per project: loose exploration ralph, strict refinement ralph. See chapter 09.
- [x] How do teams handle multi-agent coordination? — Parallel independence works; shared-state coordination is fragile. Filesystem coordination beats message-passing. See chapter 05.
