# Life Manager Agent Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development for every behavior change and superpowers:verification-before-completion before each commit and final handoff.

**Goal:** Add one canonical, evidence-backed registry of true Life Manager agents and generate the public README roster plus detailed catalog from it.

**Architecture:** `agents/registry.json` owns stable agent definitions. A dependency-free Node validator joins it against the existing skill registry, loop-adapter registry, and 399-row runtime inventory. A deterministic renderer writes a bounded README section and `docs/agent-catalog.md`; runtime health remains receipt-derived and outside Git.

**Tech Stack:** JSON Schema 2020-12 document, Node.js ESM, built-in `node:test`, Markdown, existing JSON registries.

## Global constraints

- Only model-directed observe/decide/act/re-observe loops are agents.
- Skills, deterministic workers, schedulers, healthchecks, adapters, and services are not promoted to agents.
- Registry paths are repository-relative and must exist.
- No secret-shaped fields, credentials, personal destinations, or absolute local paths.
- Generated docs must be deterministic and atomic.
- `live`, `shadow`, `legacy_live`, and `dormant` require implementation evidence; `planned` requires spec evidence.
- The two user-owned dirty files on `main` remain untouched; all work stays on `feat/agent-registry`.

---

### Task 1: Define validator contract

**Files:**
- Create: `test/agent-registry.test.mjs`
- Create: `agents/agent-registry.schema.json`
- Create: `scripts/validate-agent-registry.mjs`

- [ ] **Step 1: Read the good-test rules before authoring tests**
- [ ] **Step 2: Write failing tests for a valid minimal registry, duplicate IDs, unknown parents, parent cycles, lifecycle evidence, unsafe paths, and secret-shaped fields**
- [ ] **Step 3: Verify RED**

```bash
node --test test/agent-registry.test.mjs
```

Expected: FAIL because the validator module does not exist.

- [ ] **Step 4: Implement the minimal pure validator and CLI**
- [ ] **Step 5: Verify GREEN with the same command**

### Task 2: Validate cross-registry references

**Files:**
- Modify: `test/agent-registry.test.mjs`
- Modify: `scripts/validate-agent-registry.mjs`

- [ ] **Step 1: Add failing tests for unknown skill IDs, adapter IDs, runtime families, missing source/evidence paths, and invalid effect classes**
- [ ] **Step 2: Verify RED for the new cases**
- [ ] **Step 3: Implement reference loading and fail-closed validation**
- [ ] **Step 4: Verify GREEN**

The runtime family set is derived from `docs/migrations/openclaw/runtime-inventory.json.jobs[].target_adapter`; it is not copied into another hand-maintained list.

### Task 3: Build the verified initial roster

**Files:**
- Create: `agents/registry.json`
- Create: `docs/agent-classification.md`
- Modify: `docs/superpowers/specs/2026-08-01-life-manager-agent-registry-design.md`

- [ ] **Step 1: Audit each candidate against the five agent criteria**
- [ ] **Step 2: Record accepted agents with lifecycle and evidence**
- [ ] **Step 3: Record rejected capabilities/jobs with reasons so they are not repeatedly misclassified**
- [ ] **Step 4: Run the validator and fix data, never weaken validation to admit unsupported claims**

Initial candidate set: Orchestrator, CFO, Gig, Writer, Capafy, Solana Trading, Polymarket, Marketing, Clip/Affiliate, Development, Mobile App Builder, Physical Health, Mental Health, Events, Fundraising, and Job Application.

### Task 4: Define deterministic documentation rendering

**Files:**
- Modify: `test/agent-registry.test.mjs`
- Create: `scripts/render-agent-catalog.mjs`

- [ ] **Step 1: Add failing tests proving stable organ ordering, one row per agent, lifecycle labels, README marker preservation, and `--check` drift detection**
- [ ] **Step 2: Verify RED**
- [ ] **Step 3: Implement pure render functions and atomic CLI writes**
- [ ] **Step 4: Verify GREEN**

### Task 5: Generate the public roster and detailed catalog

**Files:**
- Modify: `README.md`
- Create: `docs/agent-catalog.md`
- Create: `docs/chat-agent-projection-contract.md`

- [ ] **Step 1: Add bounded README markers and generate the visual organization table**
- [ ] **Step 2: Generate the full catalog with objectives, lifecycle, deployment, effects, capabilities, runtime families, and evidence links**
- [ ] **Step 3: Document chat projection, receipt-derived health, approval boundaries, stale/unknown handling, and example conversations**
- [ ] **Step 4: Run renderer twice and prove the second run makes no diff**

### Task 6: Link existing specifications and close the 12 deliverables

**Files:**
- Modify: `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`
- Modify: `docs/superpowers/specs/2026-07-29-life-manager-finance-marketing-platform-design.md`
- Modify: `docs/superpowers/specs/2026-08-01-life-manager-agent-registry-design.md`
- Create: `docs/evidence/agent-registry/2026-08-01-agent-registry-verification.md`

- [ ] **Step 1: Add canonical cross-references without copying the roster**
- [ ] **Step 2: Check all 12 completion boxes only where repository evidence exists**
- [ ] **Step 3: Capture commands and exact pass/fail counts in verification evidence**
- [ ] **Step 4: Recalculate the remaining total: this slice 0 remaining, five-phase program 133 remaining**

### Task 7: Fresh verification, commit, and push

**Files:** all files above.

- [ ] **Step 1: Run focused tests**

```bash
node --test test/agent-registry.test.mjs
node scripts/validate-agent-registry.mjs
node scripts/render-agent-catalog.mjs --check
```

- [ ] **Step 2: Run repository-scope checks and report pre-existing baseline failures separately**

```bash
npm run test:oss
npm run verify:oss
git diff --check
```

- [ ] **Step 3: Audit every requirement in the design spec against a file, test, or command output**
- [ ] **Step 4: Commit the completed implementation**
- [ ] **Step 5: Push `feat/agent-registry` and verify the remote branch SHA**

## Completion evidence map

| Requirement | Authoritative evidence |
|---|---|
| One agent SSOT | `agents/registry.json` plus generated-file headers |
| True-agent boundary | `docs/agent-classification.md` and validator rules |
| Cross-registry integrity | focused test cases and validator fresh run |
| README discoverability | marker-bounded generated README section |
| Full visual catalog | `docs/agent-catalog.md` regenerated from registry |
| Chat UX | `docs/chat-agent-projection-contract.md` |
| Honest lifecycle/evidence | registry evidence refs and lifecycle tests |
| 399-job relation | runtime family validation against inventory |
| No drift | renderer `--check` fresh run |
| No secret/local path leakage | validator negative tests |
| 12 deliverables complete | checked design-spec list with direct evidence |
| Remote availability | `git ls-remote` SHA equals local branch SHA |
