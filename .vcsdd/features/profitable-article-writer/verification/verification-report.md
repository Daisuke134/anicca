# Verification Report — profitable-article-writer, Sprint 1 + Sprint 2 + Sprint 3 (2.5)

Mode: strict. Phase 5 (formal hardening). Sprint 1 = the article-orchestration SKELETON, draft-first.
Sprint 2 = REAL content-gen + REAL note.com DRAFT publish (visuals, eyecatch, single-¥500 gate), REQ-19/20
(daily executor = `claude -p` sonnet, verifier = main agent). Sprint 3 (Sprint 2.5) = REQ-21/22, a standalone
one-off real-publish tool + independent post-publish verifier — explicitly excluded from run.sh/Mode-B/the
daily wake, invoked once by the main agent to make a specific already-verified draft public.

## Sprint-3 proof obligations (26/26 tests, `bash tests/run-red.sh`)

| PROP | Obligation | Proven by | Status |
|---|---|---|---|
| PROP-22 | `note-publish-live.py` unreachable from run.sh/gates/lib (structural whole-tree scan); requires NOTE_LIVE_PUBLISH=1 + explicit --draft-key; fails closed on unconfirmed price/type/eyecatch/visuals (each branch independently tested); a confirmed-ready TEST draft genuinely reaches and fires the click; browser-session exceptions are caught, cleanly reported, context always closed (no leak, no raw traceback, no double-close) | test-prop22a/b/c + test-find004 | proved (adversary hand-traced the exception-safety fix twice, independently) |
| PROP-23 | independent (separate-process) post-publish verification: 200 AND page-content match (title/note-ID), not bare 200 | test-prop23 | proved |

Regression: `note-set-single-price.py`'s original call to the extracted `select_paid_price()` re-verified live
against a real test draft (no behavior change from Sprint 2) — test-prop21b.

## Proof Obligations

Sprint-1 required proof obligations, each proven by a green oracle test (13/13, real logic; `bash tests/run-red.sh`):

| PROP | Obligation | Proven by | Status |
|---|---|---|---|
| PROP-1 | model-agnostic (no provider/model/API-key literal; sonnet tier allowed) | test-prop1 (+ negative case: `claude-3-opus` draft fails) | proved |
| PROP-2 | Mode-B path has no human-gating call | test-prop2 | proved |
| PROP-3 | no external-repo/tool execution in the write-path | test-prop3 | proved |
| PROP-5 | fail-closed publish wiring (only both-PASS publishes) | test-prop5 (injected seam) + test-v0-real/test-v05-real (real gates, no-mock) | proved |
| PROP-6 | Mode A stops at draft + notify (url+screenshot), never publishes | test-prop6 | proved |
| PROP-9 | sonnet tier; record-earn no-LLM (fail-closed on flip) | test-prop9 | proved |
| PROP-10 | per-install creds only; no shared/Dais account | test-prop10 | proved |
| PROP-12 | account-absent → self-create-eligible / flag-unavailable, never a loud failure | test-prop12 | proved |
| PROP-14 | no-viable-topic → skip (no article) | test-prop14 | proved |
| PROP-15 | 3-round abort ceiling + failure recorded (hostile-topic JSONL safe) | test-prop15 + test-json-escape-fallback | proved |

Real-gate mechanics (v0 heading/size, v05 (e) arithmetic + judge_v05 response parser) proven no-mock by `test-v0-real.sh` / `test-v05-real.sh` with the FORCE seams unset.

Sprint-2 additional proof obligations (20/20 tests total; `bash tests/run-red.sh`):

| PROP | Obligation | Proven by | Status |
|---|---|---|---|
| PROP-18 | v05 readability arithmetic handles Japanese full-width punctuation (。！？), not just ASCII, and is locale-independent (python3 `re`-based, not byte-wise `tr`) | test-prop18-v05-jp-sentences + test-find002-locale-safe-sentences | proved |
| PROP-19 | generate_draft's 3-state precedence: (a) real draft path → verbatim, never boilerplate; (b) topic/research declared, no path → documented wiring safety-net; (c) nothing → fail-closed SKIP. Missing-but-supplied path is a logged wiring error, distinct from not-supplied | test-prop19-real-content-hook + test-find003-missing-draft-path-wiring-error | proved |
| PROP-20 | Mode-A real note.com DRAFT publish wiring (reuses existing pipeline for auth/verify; new browser scripts for eyecatch/single-price, contract-approved deviation), fail-closed, never fabricates a URL, secrets redacted from error output | test-prop20-note-publish-failclosed + test-find005-secret-redaction | proved |
| PROP-21 | Real Mode-A draft contains REAL visuals (hero + ≥2 inline figures), a REAL eyecatch/cover, and a SINGLE ¥500 paid gate — VISUALLY confirmed (not just DOM-eval), never メンバーシップ | test-prop21-visual-and-single-price + independent main-agent browser verification of `single-price-panel-*.png` | proved |

## Summary

All Sprint-1 and Sprint-2 required proof obligations are proved by green, non-vacuous oracle tests, independently
re-run by the main agent (not taken on the builder's word). Adversary implementation review PASSed: Sprint 1 after
3 rounds (0 findings), Sprint 2 after 4 rounds (0 findings) — the Sprint-2 arc caught and closed a real defect class
across 4 rounds (a doc/impl mismatch on the eyecatch mechanism that recurred in 3 separate files: spec, code
comment, test comment — each closed as found, with a final full-sweep round confirming no 5th instance). No formal
proof tooling (e.g. TLA+, model checking) is applicable to this bash+python orchestration skill; correctness is
established by the oracle suite + adversarial review + main-agent browser verification (a real note.com draft was
produced and its render/paid-gate visually confirmed by the main agent, not merely claimed). Deeper formal/property
work applies at Sprint 3+ (distribution, daily loop, self-heal/self-improve) and once real on-chain/platform-sale
earn (V4) lands.
