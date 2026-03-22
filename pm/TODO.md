# Tasks

## Active
- [ ] dashboard-poc — Visual dashboard for ralphify (#15)

## Done
- [x] fleet-parallel-ralphs — Add `ralph fleet` command to run multiple ralphs in parallel (#1) → PR #32
- [x] merge-countdown-to-idle — Move countdown timer from PR #31 into PR #29 (idle-detection), fix live ticking → PR #29
- [x] reliable-idle-detection — Check full agent stdout for idle marker as fallback → PR #29
- [x] fix-idle-detection — Fix pm/RALPH.md typo and idle marker instruction so idle mode works
- [x] minimize-pr29-v3 — Reduce PR #29 diff by 76 lines (inlined constants, consolidated tests, trimmed docs)
- [x] delay-countdown — Replace static "Waiting" message with live countdown timer → PR #31
- [x] minimize-pr29-further — Further reduce PR #29 diff (~150 lines of dead code, redundancy, verbosity) → PR #29
- [x] minimize-pr29 — Reduce PR #29 test redundancy to shrink diff → PR #29
- [x] setup-pm-idle-config — Add idle detection config to setup-pm.md prompt → PR #30
- [x] idle-detection — State-aware idle detection with backoff and max idle duration (#28) → PR #29
- [x] minimize-pr27-tests — Further reduce test diff in PR#27 test_agent.py
- [x] ghost-agent-cleanup — Fix ghost agent processes surviving Ctrl+C (#26) → PR #27
- [x] minimize-pr27-diff — Reduce PR #27 diff size by consolidating tests
