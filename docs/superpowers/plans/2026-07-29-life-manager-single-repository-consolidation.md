# Life Manager Single Repository Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development for each behavior change and superpowers:verification-before-completion before claiming any task complete.

**Goal:** Make `Daisuke134/life-manager` the only writable Life Manager source of truth, preserve and classify every `life-manager-v0` behavior, and archive the legacy repository without breaking a live loop.

**Architecture:** Repository ID `1248111245` owns all product code, specs, deployment configuration, schedulers, and evidence. Repository ID `1273052304` is a bounded import source only. Migration is behavior-first: inventory each legacy file, map it to a canonical owner, prove import/supersession/retirement, block new legacy references, then archive.

**Tech Stack:** Git/GitHub API, Node.js and Python tests already present in both repositories, macOS launchd inventory, Railway configuration, Markdown evidence manifests.

**Global constraints:**

- Never delete either repository or rewrite its history.
- Never copy secrets, `.env` values, local state, or user identifiers into Git.
- Preserve unrelated dirty worktrees and commits.
- Do not change a live scheduler target until its replacement passes a real receipt/equivalence check.
- All new files and status updates are committed only to `Daisuke134/life-manager`.

---

### Task 1: Freeze repository identities and write-target guard

**Files:**
- Create: `scripts/check-life-manager-repository-ssot.sh`
- Create: `docs/migrations/life-manager-v0/repository-baseline.json`
- Test: `scripts/check-life-manager-repository-ssot.sh`

- [ ] Record both immutable GitHub repository IDs, remotes, default branches, archive state, and head SHAs.
- [ ] Write a failing guard fixture containing `life-manager-v0` as a CI/deploy/runtime target.
- [ ] Implement the guard so historical migration evidence is allowed but runtime, CI, deploy, scheduler, and current-spec references fail.
- [ ] Run the guard and store the real output in the migration evidence directory.

### Task 2: Build the v0 file and behavior disposition manifest

**Files:**
- Create: `docs/migrations/life-manager-v0/file-disposition.json`
- Create: `docs/migrations/life-manager-v0/behavior-map.md`
- Test: existing tests under the legacy `ask/`, `call/`, `locate/`, `notify/`, `travel/`, and planner suites

- [ ] Enumerate all 35 tracked v0 files by blob SHA and mark each `import`, `superseded`, or `retire`.
- [ ] Map the 31 path-unique files to canonical packages/services and named behavior tests.
- [ ] Run the legacy test suites as a behavioral baseline and preserve results.
- [ ] Reject any disposition without a canonical owner, rationale, and verification command.

### Task 3: Import retained behavior into canonical owners

**Files:**
- Modify: canonical owners under `apps/life-manager/`, `adapters/`, `runtime/`, `services/`, or `skills/`
- Test: colocated canonical tests for planner, call, travel, ask, locate, and notify behavior

- [ ] Add a failing canonical test for each retained behavior not already covered.
- [ ] Import or adapt the minimum code needed without absolute paths or OpenClaw scheduler calls.
- [ ] Prove superseded behaviors with existing canonical tests and exact replacement paths.
- [ ] Prove retired behaviors are unreachable from all scheduler and deployment entrypoints.

### Task 4: Reconcile live execution and deployment references

**Files:**
- Modify: canonical launchd migration manifests and deployment configuration
- Create: `docs/migrations/life-manager-v0/reference-audit.json`

- [ ] Inventory GitHub Actions, Railway configuration, launchd commands, service boot files, and documentation entrypoints.
- [ ] Verify no live command currently targets the v0 remote or its misleading local clone.
- [ ] Replace checkout-name coupling with installed release/data-root configuration before renaming local paths.
- [ ] Trigger each changed retained loop through its real scheduler and capture non-dry receipts.

### Task 5: Normalize local checkout naming

**Files:**
- Modify: local clone/worktree metadata only after Task 4 passes
- Update: `docs/migrations/life-manager-v0/reference-audit.json`

- [ ] Quarantine or rename the local v0 clone so `/Users/operator/Projects/life-manager` cannot be mistaken for the canonical repo.
- [ ] Normalize the canonical checkout name only after every absolute-path reference is removed or safely migrated.
- [ ] Verify remotes by repository ID after the rename; directory names alone are not proof.
- [ ] Re-run all scheduler, service, and dependency guards.

### Task 6: Archive `life-manager-v0`

**Files:**
- Modify: legacy repository README and description before archival
- Create: `docs/migrations/life-manager-v0/final-equivalence-report.md`

- [ ] Update the legacy README and repository description with the canonical successor link and read-only status.
- [ ] Close or transfer actionable v0 issues and pull requests.
- [ ] Run the complete disposition, behavior, reference, CI, deploy, and live-receipt verification suite.
- [ ] Archive repository ID `1273052304` through GitHub and verify `archived=true`.
- [ ] Verify repository ID `1248111245` remains writable and is the only current Life Manager target.

### Task 7: Continue the platform migration from the canonical spec

**Files:**
- Modify: `docs/superpowers/specs/2026-07-29-life-manager-finance-marketing-platform-design.md`

- [ ] Mark Order 0 complete only after Tasks 1–6 have real evidence.
- [ ] Continue Orders 1–38 without creating another Life Manager repository or duplicate program spec.
- [ ] Keep remaining TODO status in the canonical spec and executable detail in canonical plans.
