---
sprintNumber: 1
feature: profitable-article-writer
scope: "Sprint 1 = the orchestration skeleton, draft-first, verified by 10 required PROP oracle tests (incl. PROP-12). Real content-gen + real note publish + real earn are Sprint 2+, explicitly OUT of this contract."
status: approved
negotiationRound: 0
criteria:
  - id: CRIT-001
    dimension: implementation_correctness
    description: "Fail-closed publish wiring: publish fires ONLY when V0 AND V0.5 both PASS. Real V0.5 (a)-(d) scoring is AGENT JUDGMENT, never hardcoded regex."
    weight: 0.18
    passThreshold: "PROP-5 test green: stubbed V0 or V0.5 FAIL -> no PUBLISHED sentinel and rc!=0; only both-PASS writes the sentinel with rc=0. AND: the non-test-mode path of gates/v05.sh delegates criteria (a)-(d) to the running agent's judgment via a documented judge_v05 request/response hook (ARTICLE_JUDGE_V05_RESPONSE) — grep confirms NO keyword/pattern grep decides (a)-(d) in that real path (criterion (e) readability stays a deterministic arithmetic computation, which is allowed)."
  - id: CRIT-002
    dimension: implementation_correctness
    description: "Mode A draft-first: stops at a note DRAFT and notifies, never publishes."
    weight: 0.13
    passThreshold: "PROP-6 test green: Mode A STATE result = DRAFT, a notify record (URL+screenshot fields) is written, and publish is never called."
  - id: CRIT-003
    dimension: edge_case_coverage
    description: "Bounded failure handling: 3-round abort with recorded failure, and no-viable-topic skip."
    weight: 0.13
    passThreshold: "PROP-15 + PROP-14 green: 3 consecutive V0/V0.5 FAILs -> STATE ABORTED + a failures.jsonl entry + zero publish; no-viable-topic/insufficient-research -> STATE SKIPPED, no article."
  - id: CRIT-004
    dimension: structural_integrity
    description: "Model-agnostic and no external execution in the article write-path."
    weight: 0.13
    passThreshold: "PROP-1 + PROP-3 green: zero provider/model/api-key literal in the skill tree (the 'sonnet' cost-tier label in lib/config.sh is allowed per REQ-12); the write-path makes no external-repo/tool execution call. PROP-1 test proven non-vacuous by an explicit negative-case assertion in tests/test-prop1-no-model-literal.sh: a synthetic draft containing 'claude-3-opus' is checked with the SAME grep and asserted to report >0 hits."
  - id: CRIT-005
    dimension: implementation_correctness
    description: "Loop model policy: sonnet tier, and the earn/verify path makes no LLM call."
    weight: 0.13
    passThreshold: "PROP-9 green: lib/config.sh declares MODEL_TIER=sonnet and a conditional RECORD_EARN_USES_LLM default of 0; the record-earn/verify sub-path makes no LLM call. The fail-closed-on-flip claim is REACHABLE and TESTED: tests/test-prop9-model-policy.sh injects RECORD_EARN_USES_LLM=1 via the environment before invoking run.sh's record_earn_only path and asserts rc!=0 and no 'RECORD_EARN_NO_LLM: true' claim; the RECORD_EARN_USES_LLM=0 default path still asserts rc=0 + the true marker."
  - id: CRIT-006
    dimension: structural_integrity
    description: "Per-install identity and zero human in the Mode-B runtime path."
    weight: 0.18
    passThreshold: "PROP-10 + PROP-2 green: all creds read from the install's own env only, a per-install accounts.json is written, no shared/Dais account literal, and the Mode-B path contains no human-gating call (Mode A's human gate is intentional and excluded)."
  - id: CRIT-007
    dimension: structural_integrity
    description: "Account-absent self-create-or-flag (PROP-12): never a loud failure/error-spew."
    weight: 0.12
    passThreshold: "PROP-12 green (tests/test-prop12-account-absent.sh): with no credential and no self-create requested, identity/accounts.sh completes rc=0, flags the rail 'unavailable' in accounts.json, and emits no error/traceback/exception text; with <RAIL>_SELF_CREATE=1 set on a rail that has NO proven self-create path (PROVEN_SELF_CREATE_RAILS), the attempt still degrades to 'unavailable' (rc=0, no crash, no loud failure); no shared/Dais account literal anywhere in identity/."
---

# Sprint 1 Contract — profitable-article-writer

The Sprint-1 acceptance surface. Each criterion is binary and pinned to a required PROP oracle test that already
runs green (Phase 2b). Phase 3 (implementation adversary) judges the CODE against these.

### CRIT-001
Fail-closed publish wiring (PROP-5). Only a both-PASS round reaches publish. Real V0.5 (a)-(d) is
AGENT-JUDGED via the judge_v05 hook, never a hardcoded regex/keyword classifier (verification-architecture.md's
purity boundary map); (e) readability stays a deterministic arithmetic computation.

### CRIT-002
Mode A draft-first (PROP-6). Draft + notify, never publish.

### CRIT-003
Bounded failure handling (PROP-15 abort+record, PROP-14 topic-skip).

### CRIT-004
Model-agnostic + no external run (PROP-1 proven non-vacuous via an explicit negative-case assertion in
tests/test-prop1-no-model-literal.sh, PROP-3).

### CRIT-005
Sonnet loop + record-earn no-LLM, fail-closed on a runtime config flip, reachable and tested (PROP-9).

### CRIT-006
Per-install identity + zero-human Mode-B path (PROP-10, PROP-2).

### CRIT-007
Account-absent self-create-or-flag, never a loud failure (PROP-12), covered by
tests/test-prop12-account-absent.sh.

## Explicitly OUT of Sprint 1
Real article content generation, real note/rail publishing over the network, and real earn/V4 — those are
Sprint 2. Distribution/reach (V2/V3) = Sprint 3. Daily loop (V5) = Sprint 4. Self-heal/self-improve = Sprint 5.
Real live judge_v05 wiring (a fresh-context adversary call scoring V0.5 (a)-(d) at runtime) is also Sprint 2 —
Sprint 1 proves the thin-script/hook interface and its fail-closed-when-unwired behavior, not a live model call.
