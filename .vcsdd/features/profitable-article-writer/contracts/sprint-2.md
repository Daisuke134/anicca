---
sprintNumber: 2
feature: profitable-article-writer
scope: "Sprint 2 = the REAL draft. (1) fix gates/v05.sh's readability arithmetic to recognize Japanese terminal punctuation (PROP-18), so the daily executor's actual output language can ever pass V0.5. (2) wire run.sh's generate_draft hook to the running agent's own real research+craft content via ARTICLE_REAL_DRAFT_PATH, never the Sprint-1 boilerplate template (PROP-19). (3) wire Mode-A's real note.com DRAFT publish via lib/note_publish.sh, REUSING the existing ai-entity-article-writer note-publish pipeline (never rebuilt) plus note_mcp's create_draft for genuinely-new-article creation, fail-closed at every step (PROP-20). (4) actually RUN one real wake end-to-end: a real ~2000-word JP note article on an AI-entity topic (x402), V0/V0.5 PASS (agent-judged via the judge_v05 hook), and a real note.com DRAFT created + gated + verified. Distribution/reach (V2/V3), Mode B autonomous publish, the daily runtime loop wiring (Sprint 4), and self-heal/self-improve (Sprint 5) remain explicitly OUT of this contract."
status: approved
negotiationRound: 0
criteria:
  - id: CRIT-101
    dimension: spec_fidelity
    description: "REQ-19/REQ-20 and the REQ-5(e) Japanese-punctuation edge case are traceable to a passing test."
    weight: 0.2
    passThreshold: "PROP-18/19/20 each have a named test file (tests/test-prop18-v05-jp-sentences.sh, tests/test-prop19-real-content-hook.sh, tests/test-prop20-note-publish-failclosed.sh) and all three are green."
  - id: CRIT-102
    dimension: edge_case_coverage
    description: "Japanese sentence-boundary edge case (。！？) is tested with a real discriminating fixture, not one that coincidentally passes either way."
    weight: 0.2
    passThreshold: "tests/test-prop18-v05-jp-sentences.sh's fixtures are constructed so the UNSPLIT concatenation exceeds 60 chars while each real Japanese sentence stays <=60 chars — a splitter bug and a working splitter produce OPPOSITE verdicts on the same input (not a coincidental pass)."
  - id: CRIT-103
    dimension: implementation_correctness
    description: "generate_draft's real-content hook never silently falls back to the boilerplate template when real content IS supplied, and never regresses the Sprint-1 fail-closed SKIP default when nothing is supplied."
    weight: 0.2
    passThreshold: "tests/test-prop19-real-content-hook.sh covers all three states: (a) real draft path supplied -> verbatim real content in draft.md, boilerplate marker ABSENT (b) topic set but no real draft path -> falls back to the boilerplate template (c) nothing supplied -> SKIPPED, unchanged from Sprint 1."
  - id: CRIT-104
    dimension: structural_integrity
    description: "lib/note_publish.sh reuses the existing note-publish pipeline and note_mcp's create_draft rather than rebuilding either; the wiring is fail-closed and never fabricates a URL on failure."
    weight: 0.2
    passThreshold: "grep confirms lib/note_publish.sh calls the EXISTING $NOTE_PUBLISH_SCRIPT and note_mcp.api.articles.create_draft rather than reimplementing browser automation or the note.com API client; tests/test-prop20-note-publish-failclosed.sh proves: no-integration-requested keeps the Sprint-1 placeholder verbatim, a forced failure degrades without crash or fake URL, and a forced success carries the wiring's own returned url/screenshot into notify.json."
  - id: CRIT-105
    dimension: verification_readiness
    description: "A real, non-test wake actually ran end-to-end and produced verifiable evidence (a real note.com DRAFT), not just green unit tests."
    weight: 0.2
    passThreshold: "A real article markdown file exists with real, cited content (not template text); a real note.com draft key/URL was created via note_mcp's create_draft (not injected/forced); publish-to-note.sh verify <key> was run for real and its JSON output + a screenshot file are captured as evidence for the human/verifier to review in a browser (REQ-20)."
---

# Sprint 2 Contract — profitable-article-writer

The Sprint-2 acceptance surface: fix the real-JP-content blocker in V0.5 (PROP-18), wire the real content-gen
hook (PROP-19), wire the real Mode-A note-publish path by REUSING the existing pipeline (PROP-20), and run one
real wake end-to-end for verifiable evidence. Phase 3 (implementation adversary) judges the CODE against these.

### CRIT-101 / CRIT-102
PROP-18's Japanese-punctuation fix in `gates/v05.sh` is proven with a real discriminating fixture (unsplit
concatenation > 60 chars, each real sentence <= 60 chars), not a fixture that happens to pass regardless of
the splitter's correctness.

### CRIT-103
PROP-19's `generate_draft` real-content hook is proven across all three reachable states (real content
supplied / topic-only fallback / nothing supplied), with the Sprint-1 fail-closed default provably unchanged.

### CRIT-104
PROP-20's `lib/note_publish.sh` is a THIN wrapper around the existing note-publish pipeline + note_mcp's
`create_draft` (grep-verifiable: no reimplemented browser automation or note.com API client), fail-closed at
every step, tested hermetically via its own `NOTE_PUBLISH_TEST_FORCE` seam.

### CRIT-105
Beyond green unit tests, Sprint 2 requires ONE real, non-test wake that actually produced a real note.com
draft — the artifact the human/verifier (REQ-20) reviews in a real browser.

## Explicitly OUT of Sprint 2
Mode B autonomous live publish; distribution/reach (V2/V3, Sprint 3); the daily runtime loop that fires this
wake unattended (Sprint 4); self-heal/self-improve (Sprint 5); a live (non-hook) `judge_v05` model call from
inside `run.sh` itself (the running agent still supplies `ARTICLE_JUDGE_V05_RESPONSE` externally, per the
Sprint-1 design — wiring a fresh-context adversary CALL from inside the deterministic shell script is a later
seam, not required for Sprint 2's "real draft" goal).
