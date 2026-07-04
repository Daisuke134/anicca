---
sprintNumber: 4
feature: profitable-article-writer
scope: "Sprint 4 (tool-tracked sprint 4, Dais 2026-07-04: \"then wire that in, yes, we have to\"): wire the REAL one-off publish mechanism built in Sprint 2.5/tool-sprint-3 (lib/note-publish-live.py, REQ-21/PROP-22) INTO run.sh's Mode-B branch so the daily unattended loop can publish for real — the human hand needed for the one manual publish already executed (flagship draft nfb2ace9f0ed8, already live, untouched by this sprint) is removed for all FUTURE wakes. Covers REQ-23 (PROP-24): the confirm->click sequence is extracted into a SINGLE shared function, lib/note_browser_common.confirm_and_publish(), imported unchanged by both lib/note-publish-live.py (the standalone one-off tool, unaffected in its own contract) and the new lib/note-mode-b-publish.py (run.sh's unattended Mode-B caller) — grep-verifiable single source, plus a dynamic call-count fault-injection proof that Mode A never reaches it. REQ-24 (PROP-25): the in-loop publish click is followed by an independent, separate-process verify (the SAME logic as lib/note-verify-live.py), recording SUCCESS (url+timestamp+result) or UNCONFIRMED (never silently assumed success, never blind-retried in the same wake) to STATE.md. REQ-25 (PROP-26): the effective per-wake mode is computed from a runtime-mutable \"1-in-N\" ratio config (env var or state-dir file, re-readable without redeploy), consulted instead of a raw AUTONOMY flag in isolation, with all 4 malformed-ratio cases (missing/uninitialized, N=0, negative, non-integer) failing closed to Mode A, never Mode B, never a crash. OUT of scope: distribution to reach platforms (Sprint 5), self-heal/self-improve (Sprint 7), and any change to lib/note-publish-live.py's own REQ-21 contract (it keeps its NOTE_LIVE_PUBLISH manual trigger and remains structurally excluded from run.sh's call graph)."
status: draft
negotiationRound: 0
criteria:
  - id: CRIT-401
    dimension: spec_fidelity
    description: "REQ-23's exact wiring contract holds verbatim: run.sh's Mode-B branch reaches a real publish click ONLY through the SAME shared, importable core function lib/note-publish-live.py itself imports (lib/note_browser_common.confirm_and_publish) — never a re-wrapped or reimplemented copy, and never by invoking lib/note-publish-live.py itself (which remains REQ-21's separate, human/main-agent-invoked, NOTE_LIVE_PUBLISH-gated tool, structurally excluded from run.sh's call graph)."
    weight: 0.25
    passThreshold: "tests/test-prop24a-shared-publish-click-single-source.sh is green: a code-only grep anchor for the actual 投稿する/更新する click JS statement (and its get_by_text(...).first.click(...) fallback) appears in EXACTLY ONE .py file across the whole skill tree (lib/note_browser_common.py); lib/note-publish-live.py contains no copy of it and imports confirm_and_publish instead; the new lib/note-mode-b-publish.py also imports confirm_and_publish (no copy) and is the ONLY file run.sh's Mode-B branch calls; run.sh STILL never references note-publish-live.py anywhere (grep 0 hits, REQ-21's exclusion unaffected); confirm_and_publish contains its own try/except/finally (AST-verified) — the exception-safety wrapper lives in the single shared unit, not re-wrapped per caller."
  - id: CRIT-402
    dimension: edge_case_coverage
    description: "REQ-25's ratio-derived effective-mode consultation genuinely replaces the raw AUTONOMY-only branch selection: all 4 distinct malformed-ratio cases (missing/uninitialized config, N=0, negative N, non-integer N) fail closed to Mode A — never Mode B, never a crash — and this is proven with the wake's OWN ratio-consultation code path (not merely asserted)."
    weight: 0.2
    passThreshold: "tests/test-prop26a-malformed-ratio-failclosed.sh is green: each of the 4 cases independently drives run.sh (AUTONOMY=on) and asserts rc=0 AND last_wake_result: DRAFT (Mode A) for every case; tests/test-prop26b-runtime-mutation.sh is green: mutating the SAME install's ratio config file at runtime (no redeploy) demonstrably flips wake behavior forward (Mode A -> Mode B) and backward (Mode B -> Mode A, via a malformed value) across consecutive invocations; tests/test-prop26c-1-in-N-end-to-end.sh is green: setting ratio=\"1-in-N\" (N=4) produces EXACTLY N-1 Mode-A wakes and 1 Mode-B wake over N consecutive real wakes against the same $ARTICLE_DIR, with the Mode-B wake landing on the Nth (last) invocation of the cycle."
  - id: CRIT-403
    dimension: implementation_correctness
    description: "The REAL success path is genuinely reachable and exercised THROUGH run.sh itself (not by calling the underlying tool/wrapper scripts directly), and REQ-24's independent in-loop verify correctly distinguishes a confirmed-live publish (SUCCESS) from a verify failure/inconclusive result (UNCONFIRMED, never silently treated as success, never blindly retried in the same wake)."
    weight: 0.3
    passThreshold: "tests/test-prop24c-modeB-real-success-via-runsh.sh is green against the REAL cloakbrowser/note_mcp/note.com session (T2, no mock): invoking `bash run.sh` alone (ratio=1-in-1, ARTICLE_MODEB_NOTE_KEY pointing at a confirmed-ready TEST draft, NEVER the flagship nfb2ace9f0ed8) results in STATE.md recording last_wake_result: PUBLISHED, the real publish_url, publish_verify_result: SUCCESS, and a verification timestamp, with an INDEPENDENT authenticated GET (run separately from the test's own invocation of run.sh) confirming the draft's status flipped to 'published'; tests/test-prop25a-modeB-unconfirmed-verify.sh is green: given a publish click that reports success but points at a note_key that a REAL, unmocked logged-out fetch cannot resolve, run.sh records last_wake_result: UNCONFIRMED + publish_verify_result: UNCONFIRMED (never PUBLISHED) and the shared publish function is confirmed (via its own call-count log) to have been invoked EXACTLY ONCE — no blind retry within the same wake."
  - id: CRIT-404
    dimension: structural_integrity
    description: "Mode A's branch is REQUIRED to demonstrate — via a DYNAMIC call-count assertion on the shared publish function, not merely a static artifact-absence check — that it makes ZERO calls to it under ANY branch-selection input, including deliberately-corrupted/adversarial ratio-config and wake-counter values designed to try to force a false-positive Mode-B resolution. The flagship draft (nfb2ace9f0ed8) is NEVER touched, republished, or referenced as an active target by any file added or modified in this sprint."
    weight: 0.15
    passThreshold: "tests/test-prop24b-modeA-zero-calls-fault-injection.sh is green: across 6 deliberately-corrupted branch-selection scenarios (negative ratio exploiting bash's modulo sign quirk, N=0 division-by-zero attempt, non-integer ratio, missing ratio file, a VALID ratio with AUTONOMY left off, and a corrupted non-numeric wake-counter file), a dynamically-substituted confirm_and_publish (via ARTICLE_NOTE_BROWSER_COMMON_DIR, counting real invocations to a log file) records ZERO calls across all 6 wakes, and each wake's STATE.md shows last_wake_result: DRAFT; grep across skills/profitable-article-writer/tests/*.sh confirms nfb2ace9f0ed8 appears ONLY as the hardcoded FLAGSHIP_DRAFT_KEY safety-guard literal in test-prop21b/22a/22b/24c, never as an actual --draft-key/ARTICLE_MODEB_NOTE_KEY argument or in any tool's stdout."
  - id: CRIT-405
    dimension: verification_readiness
    description: "The full VSDD RED->GREEN evidence trail is genuine (no fake-to-pass): the 9 Sprint-4 target-feature test files provably FAIL against the pre-Sprint-4 (Sprint-3-approved) implementation and provably PASS against the Sprint-4 implementation, while all pre-existing baseline tests remain green in both phases (zero regression from the refactor or from the test-suite edits required by it)."
    weight: 0.1
    passThreshold: "`.vcsdd/features/profitable-article-writer/evidence/sprint-4-red-phase.log` shows new-feature-tests: FAIL / regression-baseline: PASS with the actual bash tests/run-red.sh output (33 test files, 24 PASS / 9 FAIL, all 9 failures being the Sprint-4 target files) captured by temporarily reverting run.sh/lib/note_browser_common.py/lib/note-publish-live.py to their pre-Sprint-4 content and removing lib/note-mode-b-publish.py; `.../evidence/sprint-4-green-phase.log` shows target-feature-tests: PASS / regression-baseline: PASS with the actual bash tests/run-red.sh output (33 test files, 33 PASS / 0 FAIL) captured with the Sprint-4 implementation restored."
---

# Sprint 4 Contract — profitable-article-writer

**"Wire that in, yes, we have to."** Sprint 2.5 proved the real note.com publish-click mechanism works
(`lib/note-publish-live.py`, one human/main-agent-invoked call, `nfb2ace9f0ed8` went live). This sprint moves
that SAME mechanism inside `run.sh`'s Mode-B branch so no human/Opus ever triggers it again — REQ-23/24/25,
PROP-24/25/26.

## Design decisions this contract encodes

- **Single shared publish-click unit, not a copy.** `lib/note_browser_common.confirm_and_publish()` now owns
  the ENTIRE REQ-21 confirm→click sequence (eyecatch/visuals gate, price/type gate, the real click, the
  try/except/finally exception-safety) — extracted verbatim from `lib/note-publish-live.py`'s former `main()`
  body. Both `lib/note-publish-live.py` (REQ-21's one-off tool) and the NEW `lib/note-mode-b-publish.py`
  (REQ-23's unattended Mode-B caller) import and call it; neither re-wraps or reimplements any part of it.
  `note_browser_common.py` imports `cloakbrowser` LAZILY (inside `open_editor_ready()` only, not at module
  top level) so a draft that fails the eyecatch/visuals gate still triggers ZERO browser action even though
  the whole confirm→click sequence now lives in the same module that eventually needs a browser.
- **REQ-21's own contract is untouched.** `lib/note-publish-live.py` still requires `NOTE_LIVE_PUBLISH=1` +
  an explicit `--draft-key`, is still never invoked by `run.sh`, and is still structurally excluded from
  Mode B's call graph. The new `lib/note-mode-b-publish.py` has NO manual trigger gate — `run.sh`'s own
  ratio-derived effective-mode resolution (REQ-25) is what decides whether it fires, since requiring a
  second manual human gate there would defeat REQ-2's zero-human-in-Mode-B invariant this wiring finally
  satisfies end-to-end.
- **AUTONOMY is a master enable, the ratio decides WHICH wake.** `effective_mode` (consulted by REQ-23's
  branch selection, never a raw `AUTONOMY` read in isolation) is Mode B only when BOTH `AUTONOMY=on` AND the
  runtime-mutable ratio config (`ARTICLE_MODEB_RATIO` env or `$ARTICLE_DIR/state/mode-b-ratio` file,
  "1-in-N" or bare "N") says this specific wake (via a persistent, atomically-incremented
  `$ARTICLE_DIR/state/mode-b-wake-count`) is the Nth one in the cycle. Any malformed ratio value fails
  closed to Mode A — this is a double-gate safety design, not merely "ratio replaces AUTONOMY".
- **REQ-24's verify reuses REQ-22's SAME logic, a separate process.** `run.sh` shells out to
  `lib/note-verify-live.py` (unchanged from Sprint 2.5) after a Mode-B click, exactly as REQ-22 already
  established — never the click's own optimistic stdout claim. SUCCESS records url+timestamp+result;
  anything else records UNCONFIRMED (a distinct `last_wake_result`, not a PUBLISHED-with-a-caveat) and the
  wake makes no second attempt (no retry loop exists in this code path by construction).
- **`ARTICLE_MODEB_NOTE_KEY` mirrors `ARTICLE_NOTE_TITLE`'s role.** `run.sh` never creates/eyecatches/prices
  a draft itself for Mode B — it only clicks publish on an ALREADY-PREPARED key the caller names explicitly
  (no default/wildcard, same REQ-21 safety convention). Absent, it degrades to the unchanged Sprint-1
  placeholder, never crashing, never fabricating a URL. Draft creation for Mode B remains a later-sprint
  concern (distribution/Sprint 5 territory), consistent with REQ-23/24's own scope (wiring the ALREADY-BUILT
  mechanism, not building a new draft-prep pipeline).
- **Environmental correction, not a scope addition.** The Sprint-2.5 TEST draft `n39ef09f828f7` was found
  DELETED on note.com (external drift, unrelated to any Sprint-4 code). It was replaced with a fresh,
  equivalent, VCSDD-internal-test-only draft `ne94efe526c9a`, created via this skill's own already-proven
  `note-create-rich-draft.py`/`note-set-eyecatch.py` pipeline and independently confirmed (eyecatch + ≥1
  `<img>`) before any test touched it. `tests/test-prop21b`, `test-prop22b`, and the new `test-prop24c` were
  updated to point at it. The flagship draft `nfb2ace9f0ed8` was NEVER touched, republished, or referenced
  as an active target anywhere in this sprint.

## Real evidence produced by this sprint (not a claim — independently re-checkable)

- RED phase: `run.sh`, `lib/note_browser_common.py`, `lib/note-publish-live.py` temporarily reverted to
  their pre-Sprint-4 content, `lib/note-mode-b-publish.py` removed, all Sprint-4 test files (new + updated)
  kept in place. `tests/run-red.sh` reports 24/33 PASS, with the 9 Sprint-4 target files genuinely FAILing
  (no fake-to-pass) and all 24 baseline files unaffected — see
  `.vcsdd/features/profitable-article-writer/evidence/sprint-4-red-phase.log`.
- GREEN phase: implementation restored. `tests/run-red.sh` reports 33/33 PASS. `test-prop22b` and
  `test-prop24c` each independently fired a REAL 投稿する click against `ne94efe526c9a`; independent
  pre/post-checks (separate authenticated GET calls, outside the tool under test) confirm
  `status: draft -> published`; `test-prop24c` drove this through `run.sh` itself, with the in-loop
  independent verify recording `publish_verify_result: SUCCESS` to `STATE.md` — see
  `.vcsdd/features/profitable-article-writer/evidence/sprint-4-green-phase.log`.
