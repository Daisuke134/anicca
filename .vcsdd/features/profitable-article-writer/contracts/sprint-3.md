---
sprintNumber: 3
feature: profitable-article-writer
scope: "Sprint 2.5 (tool-tracked as sprint 3, state.json sprintCount=3): the standalone, human/main-agent-invoked ONE-OFF real-publish tool (REQ-21/PROP-22, lib/note-publish-live.py) and its INDEPENDENT post-publish verification (REQ-22/PROP-23, lib/note-verify-live.py). Both are explicitly OUT of run.sh's call graph, OUT of Mode B (AUTONOMY=on), and do NOT satisfy REQ-2's zero-human-in-Mode-B invariant — REQ-2 remains scoped to run.sh's own automated publish branch (REQ-7). This sprint's acceptance surface is: (1) lib/note-publish-live.py refuses fail-closed with zero browser action on every gate (NOTE_LIVE_PUBLISH unset, missing --draft-key, unconfirmed pre-publish state) — proven hermetically (T1); (2) lib/note-publish-live.py has a REAL success path, exercised end-to-end against the note.com TEST draft n39ef09f828f7 (never the flagship nfb2ace9f0ed8) — an always-refuse stub cannot pass this (T2, real browser/network); (3) lib/note-verify-live.py is a SEPARATE process from the publish tool, does a logged-out fetch, and PASSes only on 200 AND a title/note-ID content match, recording the result to state for V4 tracking. Distribution (X/Threads), the daily runtime-loop wiring (Sprint 4), and self-heal/self-improve (Sprint 5) remain explicitly OUT of this contract."
status: approved
negotiationRound: 0
criteria:
  - id: CRIT-201
    dimension: spec_fidelity
    description: "REQ-21's exact fail-closed trigger contract is implemented verbatim: NOTE_LIVE_PUBLISH=1 required (no other trigger accepted), --draft-key required and explicit (no default/wildcard key), and the tool is structurally excluded from run.sh's call graph so it can never satisfy or be confused with REQ-2's Mode-B zero-human invariant."
    weight: 0.2
    passThreshold: "tests/test-prop22a-live-publish-wiring.sh is green: (a) grep confirms run.sh never references note-publish-live.py, AND no file in run.sh's own call graph (lib/note_publish.sh, gates/, identity/) invokes it; (b) NOTE_LIVE_PUBLISH unset -> non-zero exit, stderr names the missing trigger, and zero browser action (proven by running under a plain python3 with no cloakbrowser installed -- a raw ModuleNotFoundError/traceback would surface if the browser layer were touched, and does not); (c) missing --draft-key -> non-zero exit with a clear argparse error naming the argument."
  - id: CRIT-202
    dimension: edge_case_coverage
    description: "Every REQ-21 pre-publish confirmation criterion (記事タイプ=有料, 価格=NOTE_PRICE, eyecatch present, >=1 visual figure present) is independently checkable, and an UNCONFIRMED state on ANY ONE of them blocks the click with the EXACT missing piece reported — not a generic failure."
    weight: 0.2
    passThreshold: "tests/test-prop22a-live-publish-wiring.sh case (d) is green: a stubbed note_mcp fixture with no eyecatch set (and zero <img> tags) causes note-publish-live.py to refuse BEFORE any browser session is opened (note_browser_common is never imported in this path), with stderr naming 'eyecatch' as the exact blocking reason and explicitly stating no click/browser action was attempted."
  - id: CRIT-203
    dimension: implementation_correctness
    description: "A REAL success path exists and is exercised: given a genuinely note.com TEST draft (n39ef09f828f7) whose eyecatch+visuals are independently confirmed present, note-publish-live.py's own browser-driven price/type confirmation (reusing note_browser_common.select_paid_price, the SAME function note-set-single-price.py uses -- not re-invented) succeeds, and the tool actually reaches and fires the 投稿する/更新する click."
    weight: 0.25
    passThreshold: "tests/test-prop22b-live-publish-real-click.sh is green against the REAL cloakbrowser/note_mcp/note.com session (T2, no mock): the tool's stdout carries NOTE_LIVE_URL for https://note.com/anicca123/n/n39ef09f828f7 and a NOTE_LIVE_CLICKED: 投稿する|更新する marker, AND an INDEPENDENT authenticated GET /v3/notes/n39ef09f828f7 (run separately from the tool itself, before and after) confirms the draft's status flipped from 'draft' to 'published'. An always-refuse implementation FAILS this test by construction (rc!=0, no NOTE_LIVE_URL, status never flips)."
  - id: CRIT-204
    dimension: structural_integrity
    description: "The flagship draft (nfb2ace9f0ed8) is NEVER touched by anything in this sprint's own test suite -- it is reserved for the main agent's own deliberate, separate one-off invocation after this sprint converges."
    weight: 0.15
    passThreshold: "grep across skills/profitable-article-writer/tests/test-prop22*.sh confirms the literal string nfb2ace9f0ed8 (the flagship key) never appears as an argument to note-publish-live.py or note-verify-live.py in any test; test-prop22b-live-publish-real-click.sh contains an explicit runtime safety assertion (TEST_DRAFT_KEY != FLAGSHIP_DRAFT_KEY, hard-exit 3 otherwise) plus a post-hoc check that the flagship key never appears in the tool's own stdout for that run."
  - id: CRIT-205
    dimension: verification_readiness
    description: "REQ-22's independent post-publish verification is genuinely a SEPARATE process from the publish tool (never imports/calls it, never reads stored cookies), checks BOTH HTTP 200 AND a title/note-ID content match (guarding an SPA-shell false-positive), and records the URL+timestamp+result to state so V4 (earn) tracking can begin against it."
    weight: 0.2
    passThreshold: "tests/test-prop23-independent-live-verify.sh is green: structural checks confirm note-verify-live.py never imports/execs note-publish-live.py and never reads the NOTE_COOKIES_FILE env var; a REAL logged-out fetch of a known-live note.com URL (na3a631e63d1a) reports http_status=200 AND PASS=true AND key_in_body=true; a REAL fetch of a nonexistent key reports PASS=false with a non-200 status; and a state file (NOTE_LIVE_STATE_FILE) accumulates one JSON line per invocation carrying key+ts+url."
---

# Sprint 2.5 / Sprint 3 Contract — profitable-article-writer

The Sprint-2.5 acceptance surface (Dais 2026-07-04: "the note is not actually published, we have to have it
actually published, after the verification"): a standalone, fail-closed, human/main-agent-invoked real-publish
tool (REQ-21/PROP-22) that is structurally excluded from run.sh/Mode-B/the daily-wake path, plus an independent
post-publish verifier (REQ-22/PROP-23) that never trusts the publish tool's own stdout claim. Phase 3
(implementation adversary) judges the CODE against these 5 criteria.

## Design decisions this contract encodes

- **Two-file split (REQ-21 vs REQ-22), never merged**: `lib/note-publish-live.py` (the click) and
  `lib/note-verify-live.py` (the independent check) are separate processes on disk, invoked separately, so a
  bug in the publish tool's own optimistic stdout claim can never also corrupt the verification.
- **Confirm == set, for price/type**: note.com's 記事タイプ/価格 selection is pure client React state, never
  persisted across a reload until an actual publish (documented empirically in
  `lib/note-set-single-price.py`'s own docstring). `note-publish-live.py` therefore performs this ONE gate via
  a real browser session (reusing `note_browser_common.select_paid_price`, extracted from
  `note-set-single-price.py` in this sprint specifically so neither script re-invents the sequence), while
  eyecatch + visuals — which ARE persisted server-side — are confirmed via a cheaper authenticated API call
  with zero browser cost, checked FIRST so a doomed invocation never opens a browser at all.
- **Safety governs the real-click test, not the implementation**: `test-prop22b-live-publish-real-click.sh` is
  the only file anywhere in this sprint permitted to fire a real 投稿する/更新する click, and it is hardcoded
  to the TEST draft `n39ef09f828f7`. The flagship draft `nfb2ace9f0ed8` is reserved for the main agent's own
  separate, deliberate one-off invocation of the SAME tool after this contract converges — that invocation is
  intentionally outside this sprint's own automated test suite (a human/agent, not a test file, makes that
  specific call).

## Real evidence produced by this sprint (not a claim — independently re-checkable)

- RED phase: `lib/note-publish-live.py` and `lib/note-verify-live.py` moved aside; `tests/run-red.sh` reports
  20/23 PASS, with `test-prop22a/22b/23` genuinely FAILing absent the implementation (no fake-to-pass) — see
  `.vcsdd/features/profitable-article-writer/evidence/sprint-3-red-phase.log`.
- GREEN phase: both files restored; `tests/run-red.sh` reports 23/23 PASS. `test-prop22b` fired a REAL
  投稿する click against `n39ef09f828f7`; an independent authenticated GET confirmed `status: draft ->
  published`; a fresh, unrelated logged-out `curl` after the run confirmed `HTTP 200` and the article title
  string present in the response body — see
  `.vcsdd/features/profitable-article-writer/evidence/sprint-3-green-phase.log`.
