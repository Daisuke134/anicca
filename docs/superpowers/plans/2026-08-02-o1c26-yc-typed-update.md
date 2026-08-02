# O1C-26 YC Typed Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve every O1C-25 blocker, create a truthful dedicated Life Manager demo, produce a fresh submit-ready preview, and execute each required YC typed update at most once with immediate readback while keeping application resubmission at zero.

**Architecture:** A current submitted-application provider manifest describes only observed progress/team/profile/demo routes. Agent-authored current facts and media enter a content-addressed plan builder. A durable state machine fences every remote operation before its one allowed control activation; ambiguity routes to readback and never blind retry. The existing five-scope preview is rebuilt against the resulting remote state.

**Tech Stack:** Node.js CommonJS, `node:test`, JSON/SHA-256, Playwright Core over CDP, HyperFrames, ffprobe, Git.

## Global constraints

- Exact application: Fall 2026 `0b61fe42-e383-490d-b60e-04f1ad7ec5df`, already submitted and `In review`.
- O1C-07 is the sole application-submit receipt. Planned and actual application-submit effects remain exactly zero.
- Use CloakBrowser daily-driver `http://127.0.0.1:9222`, one existing context, owned pages only, no `browser.close()`.
- User requested no human in the loop. All semantic choices and video gates are agent-approved and evidence-backed.
- Semantic truth/currentness is agent-owned. Deterministic code validates schema, hashes, chronology, state transitions, effect ceilings, and readback equality only.
- Unknown effect means no retry.
- Public evidence contains no secrets or private founder fields.

---

### Task 1: Current provider and typed-operation contract

**Files:**
- Modify: `apps/life-manager/config/yc-application-provider.json`
- Modify: `apps/life-manager/lib/yc-application-provider.js`
- Modify: `apps/life-manager/lib/yc-application-provider.test.js`
- Create: `apps/life-manager/lib/yc-typed-update.js`
- Create: `apps/life-manager/lib/yc-typed-update.test.js`
- Modify: `apps/life-manager/package.json`

- [ ] Write RED tests for the observed submitted-app route inventory, exact locators/controls, unsupported main/application-submit rejection, current source refs, and conditional operation omission.
- [ ] Write RED tests for operation SHA identity, closed plan schema, exact payload/media binding, stable canonical digest, and recursive freeze.
- [ ] Implement the minimal current provider validator and typed plan builder without semantic text classification.
- [ ] Add adversarial cases for drift, duplicates, stale sources, path traversal, private keys, extras, altered controls, and application-submit injection.
- [ ] Run focused tests and `npm run test:outbound`.

### Task 2: Durable exactly-once effect fence

**Files:**
- Modify: `apps/life-manager/lib/yc-typed-update.js`
- Modify: `apps/life-manager/lib/yc-typed-update.test.js`
- Create: `apps/life-manager/scripts/run-yc-typed-update.js`
- Create: `apps/life-manager/scripts/run-yc-typed-update.test.js`

- [ ] Write RED transition tests for `prepared -> effect_attempted -> confirmed|not_applied|unknown_effect`.
- [ ] Reject mutation without a prepared fence, second activation, payload drift, stale plan, terminal-state rewrite, and retry after ambiguity.
- [ ] Implement atomic local fence persistence and a browser executor that marks `effect_attempted` before activating the one allowed control.
- [ ] Implement exact readback per operation and privacy-minimal receipt projection.
- [ ] Prove dry-run/preview mode performs zero writes, attachments, saves, update submits, application submits, and browser closes.

### Task 3: Current facts and founder-source reconciliation

**Files:**
- Create: `docs/evidence/funding/2026-08-02-o1c26-yc-current-facts.json`
- Update external Application Kit source only with content-addressed backup if a verified correction is needed.

- [ ] Re-observe progress, team, founder profile, founder video, demo, application state, public dashboard, and current repo sources.
- [ ] Author truthful English progress/team/profile copy; current users and revenue default to observed zero unless stronger current receipts exist.
- [ ] Resolve founder source conflicts field by field; never persist private values in repo evidence.
- [ ] Decide each conditional operation with a material-difference or exact-equality receipt.
- [ ] Build the closed typed-operation plan with all pre-execution mutation effects zero.

### Task 4: Dedicated Life Manager demo

**Files:**
- Create: `videos/life-manager-yc-demo/**`
- Produce: `videos/life-manager-yc-demo/renders/video.mp4`
- Copy final content-addressed asset to Application Kit video storage after validation.

- [ ] Run HyperFrames autonomous intent/setup with `flow: automation`, `storyboard: no`, 16:9 English, 45–75 seconds, show-it-as-is.
- [ ] Capture/adopt only current real sources; record the public dashboard's actual zero-live-instance state.
- [ ] Build the storyboard, visual design, frames, audio/captions if supported, and assemble.
- [ ] Run transition verification, lint, check, snapshots, inspect the contact sheet, then render high quality.
- [ ] Validate MP4 SHA-256, bytes, duration, codecs, dimensions, and visual-truth inventory; do not upload on any failure.

### Task 5: Fresh preview and one-time execution

**Files:**
- Create: `docs/evidence/funding/2026-08-02-o1c26-yc-typed-update.json`

- [ ] Attach the exact facts, provider, and demo digests to a fresh five-scope preview.
- [ ] Require `preview_complete:true`, `submit_ready:true`, no blocker codes, prior application submit count one, planned application submits zero, and all pre-effect mutations zero.
- [ ] Persist each required operation fence in `prepared` state.
- [ ] Execute every prepared typed operation in dependency order, at most once each; on ambiguity perform readback without retry.
- [ ] Re-open every affected route and record sanitized exact readback plus final application `In review` state.
- [ ] Require actual application submissions zero and no duplicate operation identity/effect.

### Task 6: Review, verification, and closeout

**Files:**
- Modify: `docs/evidence/funding/2026-08-02-o1c26-yc-typed-update.json`
- Modify: `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`

- [ ] Commit implementation before review and record its full SHA.
- [ ] Obtain independent review; turn every Critical/Important finding into a RED regression and fix until zero remain.
- [ ] Run focused tests, outbound, runtime-up, full `npm test`, Node/JSON/digest/privacy/media/browser ownership checks, and `git diff --check`.
- [ ] Check O1C-26 only when all required typed readbacks are confirmed; record 57/143 complete and 86 remaining, then point to O1C-27.
- [ ] Commit, push, fetch, require local HEAD equals remote branch, and require a clean worktree.
