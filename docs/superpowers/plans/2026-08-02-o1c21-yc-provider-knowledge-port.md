# O1C-21 YC Provider Knowledge Port Implementation Plan

**Goal:** Move the useful field/video/progress knowledge from deprecated `apply-to-yc` into a checked-in, fail-closed successor YC provider contract without opening or submitting the live application.

**Architecture:** A JSON manifest owns immutable provider surface knowledge. A CommonJS module validates the manifest and builds a content-addressed, preview-only operation plan from agent-resolved current values and source references. Tests prove exact legacy coverage and reject stale/ambiguous/partial inputs.

**Tech Stack:** Node.js CommonJS, `node:test`, JSON configuration, existing Life Manager Application Kit/funder modules.

---

### Task 1: Lock the migrated contract with failing tests

**Files:**
- Create: `apps/life-manager/lib/yc-application-provider.test.js`
- Create: `apps/life-manager/config/yc-application-provider.json`

1. Add tests for the exact 20 main fields, four pages, video/demo uploads, six-month revenue vector, two distinct scoped question locators, page-atomic grouping, readback, and zero submits.
2. Add fail-closed tests for partial inventory, legacy/static source refs, invalid file digests, ambiguous global-text locators, wrong monthly vector length, and any submit operation.
3. Run the focused test and observe failure because the implementation does not exist.

### Task 2: Implement the deterministic provider plan

**Files:**
- Create: `apps/life-manager/lib/yc-application-provider.js`
- Modify: `apps/life-manager/package.json`

1. Validate the checked-in manifest against an exact schema and legacy inventory.
2. Validate all resolved current values and provenance without making semantic decisions.
3. Build four ordered operations with exact readback requirements and a stable SHA-256 plan digest.
4. Export only frozen results and fail on unknown/extra/missing inputs.
5. Add the focused test to the outbound suite and run focused tests green.

### Task 3: Prove the migration boundary and close O1C-21

**Files:**
- Create: `docs/evidence/funding/2026-08-02-o1c21-yc-provider-knowledge-port.json`
- Modify: `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`

1. Compare canonical inventory to deprecated `apply-to-yc` and successor `yc-w26.json` by keys and digests, without recording answer content.
2. Verify the live daily-driver endpoint is available read-only, but do not navigate to YC; live continuation belongs to O1C-22.
3. Run focused, outbound, runtime-up, and relevant full regression tests.
4. Request independent review, fix findings, rerun verification, then record evidence.
5. Check O1C-21, record 52/143 complete and 91 remaining, commit, push, and prove local/remote equality.

