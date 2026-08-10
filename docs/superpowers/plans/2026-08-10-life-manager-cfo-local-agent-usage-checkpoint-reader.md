# CFO-2a2a.5b2a — Local Usage Checkpoint Reader Plan

Status: READY

## Goal

Read one fixed per-source checkpoint safely so the next runner can resume. A missing checkpoint is an honest first run;
a malformed or unreadable checkpoint never silently resets the cursor.

## Ponytail gate

- Modify only `apps/life-call/lib/cfo-local-agent-usage-checkpoint.js` and its existing test.
- Reuse the writer's path/schema validation and freeze helper. Add no runner, source read, launchd wiring, Telegram,
  DB, OTel, recovery loop, migration, or new state format.
- Production target +35 LOC, tests +35 LOC; total <=70 additions. Stop before 100 or a third file.

## Contract

`readLocalAgentUsageCheckpoint(stateRoot, sourceId)` uses the same fixed
`stateRoot/cfo/local-agent-usage/<source_id>.json` path. Both arguments use the writer's path-safe validation and reject
filesystem root. Missing final file returns `null`. It never scans for alternate/temp/history files.

For an existing file: require a regular file no larger than 64 KiB, mode with no group/other permission bits, one
UTF-8 JSON object followed by one LF, exact six checkpoint keys, schema/mapping/source match, exact cursor/count/
exception shapes and equations already enforced by the writer. Return a cloned deeply frozen checkpoint. Never return
the path or raw text.

Invalid arguments throw existing `invalid_state_root|invalid_batch` before filesystem access. Any existing-file stat,
read, UTF-8, JSON, schema, permission, or source mismatch throws only
`cfo_local_agent_checkpoint_invalid:read_failed`; path, errno, content, and provider data never escape.

## Task 1 — RED/GREEN and close

Extend the existing test: missing→null; writer round-trip→exact frozen isolated checkpoint; corrupt/oversize/broad-mode/
wrong-source/symlink files→fixed `read_failed`; hostile arguments→fixed pre-I/O error. Prove no temp discovery and no
mutation. Record missing-export RED, implement only reader/refactored shared validation, then run focused, CFO, full,
syntax, diff, and 2-file/70-added-LOC gates. Fresh Sol review closes 5b2a before the two-source runner 5b2b.
