# CFO-2a2a.5b2a — Local Usage Checkpoint Reader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** READY

**Goal:** Read one fixed per-source checkpoint safely so the next local runner can resume without treating corrupt state as a first run.

**Architecture:** Extend the existing checkpoint module only. Reuse its fixed path, schema validator, and deep-freeze helper; distinguish only an absent final file (`null`) from every invalid existing file (`read_failed`).

**Tech stack:** Node.js CommonJS, `node:fs`, `node:path`, `node:test`, `node:assert/strict`; no dependency changes.

## Global constraints

- Local Mac first; no Supabase, DB, browser, Telegram, OTel, launchd, recovery loop, or new state format in this slice.
- Sol owns this plan, review, E2E, spec update, commit, and push. Luna owns production/test edits and implementation commands only.
- Modify exactly two files: `apps/life-call/lib/cfo-local-agent-usage-checkpoint.js` and `apps/life-call/lib/cfo-local-agent-usage-checkpoint.test.js`.
- Soft target: production +35 LOC and tests +35 LOC; total <=70 additions. Hard stop before 100 additions or a third file.
- Use the standard library and existing `validateBatch`, fixed-path construction, and `freeze`; add no abstraction for future readers.
- Test first: prove the missing export fails before production code changes, then add only the code needed for GREEN.
- Never emit filesystem paths, errno, raw checkpoint text, events, prompts, payloads, credentials, or provider data.

---

### Task 1: Read and validate one fixed checkpoint

**Files:**
- Modify: `apps/life-call/lib/cfo-local-agent-usage-checkpoint.js`
- Test: `apps/life-call/lib/cfo-local-agent-usage-checkpoint.test.js`

**Interfaces:**
- Consumes: the writer's fixed path `stateRoot/cfo/local-agent-usage/<source_id>.json`, exact six-key payload, `validateBatch`, and `freeze`.
- Produces: `readLocalAgentUsageCheckpoint(stateRoot, sourceId) -> frozen checkpoint | null`.
- Missing final file returns `null`; no temp, alternate, or history file is discovered.
- Invalid arguments throw `cfo_local_agent_checkpoint_invalid:invalid_state_root|invalid_batch` before filesystem access.
- Any invalid existing final file throws exactly `cfo_local_agent_checkpoint_invalid:read_failed`.

- [ ] **Step 1: Add one behavior-focused reader test and prove RED**

Import `readLocalAgentUsageCheckpoint`. In one isolated temp-root test, assert these observable contracts with literal expected values:

- missing fixed final file returns `null`, even when a matching temp-like file exists;
- writer then reader round-trip returns the exact six-key payload and the returned object plus nested objects/array are frozen;
- mutating the returned value cannot mutate a later read;
- corrupt JSON, >64 KiB, group/other permission bits, wrong source ID, and symlink final files each throw only `read_failed`;
- relative/root `stateRoot` throws `invalid_state_root`, and unsupported `sourceId` throws `invalid_batch`.

The production mutation each assertion catches is respectively: accidental file discovery, silent reset, mutable shared state, accepting malformed/oversized/insecure/misdirected state, or touching the filesystem before trust-boundary validation.

Run from `apps/life-call`:

```bash
node --test lib/cfo-local-agent-usage-checkpoint.test.js
```

Expected RED: `readLocalAgentUsageCheckpoint is not a function`; record the command and failure in the SDD report.

- [ ] **Step 2: Implement the minimum reader**

Validate `stateRoot` with the writer's existing rule and validate `sourceId` against `SOURCE_IDS` before I/O. Read only the fixed final path. A missing final path is the sole `null` case.

For an existing path, require: regular file and not symlink, size <= `64 * 1024`, no `mode & 0o077`, exact UTF-8 bytes for one JSON object followed by one LF, exact checkpoint keys `schema_version,collected_at,mapping_id,source_state,counts,coverage_exceptions`, schema version `1`, valid timestamp, matching source ID, and all writer count/exception equations. Refactor the existing validator only enough for writer and reader to share those value checks; keep the writer-only `events.length === accepted_rows` check on the write path. Never allocate placeholder events from an untrusted count.

Return a cloned deep-frozen six-key checkpoint. Catch every existing-file stat/read/decode/parse/schema/permission/source failure and convert it to only `read_failed`; do not catch the pre-I/O argument errors.

- [ ] **Step 3: Prove GREEN and regression safety**

Run from `apps/life-call`:

```bash
node --test lib/cfo-local-agent-usage-checkpoint.test.js
npm run test:cfo
npm test
node --check lib/cfo-local-agent-usage-checkpoint.js
node --check lib/cfo-local-agent-usage-checkpoint.test.js
```

Expected: all commands exit `0`, with no failures or warnings.

- [ ] **Step 4: Prove Ponytail scope**

From the repository worktree root, run:

```bash
git diff --check
git diff --name-only f73cb1a9bbb9aab50b1436347456d9a65a411686
git diff --numstat f73cb1a9bbb9aab50b1436347456d9a65a411686 -- apps/life-call/lib/cfo-local-agent-usage-checkpoint.js apps/life-call/lib/cfo-local-agent-usage-checkpoint.test.js
```

Expected: exactly the two owned files; <=70 added lines is the target and <100 is mandatory. Luna writes the SDD report and does not commit or push. Sol then performs fresh review, isolated real-shape E2E, spec update, commit, and push before 5b2b starts.
