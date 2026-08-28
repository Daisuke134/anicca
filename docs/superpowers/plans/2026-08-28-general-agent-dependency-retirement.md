# GA-13A Tier-2 Runner Dependency Retirement Plan

> **For agentic workers:** Use Superpowers task-by-task. Do not mutate the loaded loop before a pushed-main immutable release exists.

**Goal:** Remove the active `tier2-agent-diagnose` fallback dependency on the `profitable-claude` checkout without changing its bounded read-only diagnosis contract.

**Measured baseline:** `ai.anicca.tier2-agent-diagnose` is managed, loaded-idle, installed/event release `d9021490…`, latest natural terminal `pass`. Its repo entrypoint still defaults to `~/profitable-claude/skills/control-plane/tier2/run_diagnosis.sh`; that wrapper then calls the old checkout's agent runner. The canonical replacement is `runtime/agent-runner/agent_runner.py` in this repository.

**Files:**

- Modify: `skills/anicca-core/scripts/tier2-agent-diagnose.sh`
- Add: `skills/anicca-core/scripts/tier2-run-diagnosis.sh`
- Add: `skills/anicca-core/scripts/tier2-diagnosis.schema.json`
- Modify: the focused tier-2 contract test only

## Task 1: Repo-local diagnosis runner

- [ ] Add a failing contract that the default runner resolves inside the release and contains no `profitable-claude` path.
- [ ] Copy the working legacy wrapper and schema, changing only runner/schema resolution to the immutable release tree.
- [ ] Run tier-2 focused tests, shell syntax, agent-runner schema/evidence tests, OSS changed-path scan, and `git diff --check`.
- [ ] Push the source change without touching the loaded label or legacy checkout.
- [ ] After merge, cut a main-derived immutable release, apply only `tier2-agent-diagnose`, retain the prior plist/release as rollback, and require a natural terminal pass from the new SHA.
- [ ] Read back loaded argv, release SHA, state path, external legacy path use 0, rollback receipt, and only then close GA-13A.

## Not yet eligible

- `citizens-diff-monitor` still reads canonical `~/.hermes/state/citizens.json`; its latest terminal is `entrypoint_exit_143`. It cannot move until a replacement citizens state owner has a natural pass and rollback proof.
- Historical evidence literals and verifier deny-patterns are not runtime dependencies and are not deleted to improve counts.
