# Opportunity Scout Evidence Collector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collect one replayable, read-only public-evidence snapshot from every Order 5A.1 market without creating an account, reserving work, submitting, signing, or paying.

**Architecture:** Add one dependency-free Node tool under `skills/agent-economy/`. It performs only public GET requests plus the documented read-only Olas GraphQL POSTs, writes each raw response under the instance state root, and emits a compact manifest containing request provenance, HTTP status, byte count, SHA-256, evidence path, and the model-owned evaluation fields. It never ranks, classifies, or selects an opportunity.

**Tech Stack:** Node.js built-ins (`fetch`, `node:crypto`, `node:fs/promises`, `node:path`, `node:url`) and `node:test`.

## Global Constraints

- Work only in `/Users/anicca/Projects/life-manager-main/.worktrees/agent-economy-implementation` and push only `feat/agent-economy-implementation`.
- Order 5A.1 is read-only: no account, credential, application, report, claim, signature, payment, reservation, or broadcast.
- No human-provided credential or authorization header enters a request.
- Deterministic code collects and hashes evidence; the Life Manager model owns market judgment.
- One failed source remains an explicit failed source record and never erases successful source evidence.
- Raw response data stays outside releases in the per-instance state root; stdout and the manifest contain no secret.

---

### Task 1: Public market evidence collector

**Files:**
- Create: `skills/agent-economy/opportunity-scout.mjs`
- Create: `skills/agent-economy/opportunity-scout.test.mjs`
- Modify: `docs/superpowers/specs/2026-08-21-agent-economy-design.md`

**Interfaces:**
- Produces: `collectOpportunityEvidence({ fetchImpl, observedAt }) -> Promise<{ schema_version, record_type, observed_at, mode, evaluation_fields, sources }>`.
- Produces: `writeOpportunityEvidence({ snapshot, bodies, stateDir }) -> Promise<{ manifestPath, snapshot }>` for the CLI only.
- Each source record contains `source`, `method`, `url`, optional `request_body_sha256`, `ok`, `http_status`, `content_type`, `content_bytes`, `content_sha256`, and later `evidence_path`.
- CLI writes `$ANICCA_HOME/skills/agent-economy/state/opportunity-scout/<UTC-safe-observed-at>/manifest.json` plus one raw response file per source.

- [x] **Step 1: Write the failing test**

Add tests that inject a fake `fetchImpl`, then assert:

```js
assert.deepEqual(new Set(calls.map((call) => call.method)), new Set(['GET', 'POST']));
assert.equal(calls.some((call) => call.headers.authorization || call.headers.cookie), false);
assert.equal(snapshot.mode, 'read_only');
assert.deepEqual(snapshot.evaluation_fields, [
  'scope', 'funding', 'recent_payout', 'competition', 'signup_identity',
  'payout_rail', 'deadline', 'expected_compute', 'official_receipt',
]);
assert.equal(snapshot.sources.every((source) => /^[a-f0-9]{64}$/.test(source.content_sha256)), true);
```

Also make one source return HTTP 503 and prove the collector returns both the explicit failed record and every successful record. Verify every Olas POST body contains only `global`, `meches`, `_meta`, and request/delivery fields and contains no mutation. Verify the writer stores raw bodies and a manifest whose `evidence_path` files hash back to `content_sha256`.

- [x] **Step 2: Run the focused test and observe RED**

Run:

```bash
node --test skills/agent-economy/opportunity-scout.test.mjs
```

Expected: FAIL because `opportunity-scout.mjs` does not exist.

- [x] **Step 3: Implement the smallest collector**

Implement fixed transport descriptors only for:

- Agent Bounties Base claimable feed;
- Immunefi bounty directory;
- uGig gigs and bounties JSON APIs;
- Code4rena audits;
- Sherlock contests;
- Cantina competitions;
- Olas Gnosis, Base, Polygon, and Optimism marketplace subgraphs.

Use `Promise.allSettled`, never send credentials, preserve non-2xx bodies as evidence, SHA-256 the exact response bytes, and use atomic temporary-file rename for the manifest. Do not parse quality, infer category, rank markets, select work, or add a dependency.

- [x] **Step 4: Run the focused test and observe GREEN**

Run:

```bash
node --test skills/agent-economy/opportunity-scout.test.mjs
```

Expected: PASS.

- [x] **Step 5: Run one live read-only collection**

Run with an isolated temporary state root:

```bash
SCOUT_STATE_DIR="$(mktemp -d)/opportunity-scout" \
  node skills/agent-economy/opportunity-scout.mjs
```

Expected: exit 0 when at least one source succeeds; output names the manifest and contains no account/application/report/claim/payment effect. Independently hash every raw file and compare it with the manifest.

- [x] **Step 6: Update the canonical spec with measured state**

Keep 5A.1 active. Record the collector, exact source success/failure count, manifest hash, and the next atomic action: model-owned normalization from the raw evidence. Do not mark 5A.1 complete until all required evaluation fields have evidence-backed values or explicit unknown reasons.

- [x] **Step 7: Run relevant regression tests**

Run:

```bash
node --test skills/agent-economy/opportunity-scout.test.mjs test/agent-economy-skill.test.mjs
npm run test:agent-economy
```

Expected: all pass.

- [x] **Step 8: Review, commit, and push**

Fresh read-only review checks no effect path, no credential inheritance, exact hashing, partial-source preservation, and model-owned judgment. Then commit and push to `origin/feat/agent-economy-implementation`.
