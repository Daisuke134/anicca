# Verification Architecture (Phase 1b) — profitable-article-writer

Mode: strict. Tiers: **T0** type/lint/grep static · **T1** unit · **T2** integration/property (no-mock) · **T3** live E2E / on-chain.
`required: true` = a gate that MUST pass for convergence (strict: all financial/safety/no-human obligations).

## Purity boundary map

```
 DETERMINISTIC (code, testable in isolation)      NON-DETERMINISTIC (agent judgment, prompt-scored)
  record-earn ledger (anti-fake)                   niche/topic pick
  render/screenshot verify (V0)                    theme + buy-reason-3-lines + free/paid split
  publishers (note/zenn/substack/devto/x)          craft writing + V0.5 craft scoring
  payout routing (mode → account|wallet)           per-rail repurposing
  dedup / registry credential gating / git         ── judged by the running model, NOT hardcoded regex ──
 EXTERNAL SIDE-EFFECTS (guarded, live-verified): publish, payment receipt, account creation
```
The judgment column is the AGENT's (right-altitude prompts), never a hardcoded classifier — per building-effective-ai-agents.

## Proof obligations

| PROP | REQ | Statement (SHALL hold) | Tier | required |
|---|---|---|---|---|
| PROP-1 | REQ-1 | grep skill tree for model/provider/API-key literals → 0 matches (model-agnostic) | T0 | ✅ |
| PROP-2 | REQ-2,13 | no-human audit on the **Mode-B path**: trace/grep shows no human-gating call in Mode B (Mode A's review gate is explicitly EXCLUDED); deterministic PASS against Mode-B config | T1 | ✅ |
| PROP-3 | REQ-3 | **deterministic:** the article write-path makes NO external-repo/tool execution call (static trace). The semantic "no claim of having run" check lives in V0.5 criterion (d) (REQ-5) — a DEFINED binary check, NOT a keyword blocklist | T1 | ✅ |
| PROP-4 | REQ-4 | one wake → exactly ONE article artifact containing theme + buy-reason-3-lines + free/paid split + body | T2 | — |
| PROP-5 | REQ-5,14 | **fail-closed WIRING** (deterministic, injected-seam): `tests/test-prop5-failclosed-publish.sh` drives `gates/publish-gate.sh` via `ARTICLE_TEST_FORCE_V0`/`ARTICLE_TEST_FORCE_V05` — a documented, deterministic injection seam that stubs a FAIL from V0 OR V0.5 and asserts publish NOT called; only BOTH-PASS reaches publish. This proves the WIRING is fail-closed, not the real (non-forced) gate mechanics — those are proven separately, no-mock, by `tests/test-v0-real.sh` / `tests/test-v05-real.sh` (real heading/size/line-count check, real sentence-length arithmetic, real judge_v05 response-file parser, all invoked with the FORCE env vars unset) | T1 (wiring, injected seam) — real mechanics at T2 via test-v0-real.sh/test-v05-real.sh | ✅ |
| PROP-6 | REQ-6 | Mode A: no publish call is made; draft + notify(URL+screenshot) only. `tests/test-prop6-modeA-draft.sh` drives `run.sh` via `ARTICLE_TEST=1` + `ARTICLE_TEST_V0_RESULTS`/`ARTICLE_TEST_V05_RESULTS` — a deterministic injected-seam wiring test (T1), asserting the Mode-A branch itself never calls publish regardless of gate outcome; the gates it stubs past are covered no-mock by test-v0-real.sh/test-v05-real.sh | T1 (wiring, injected seam) | ✅ |
| PROP-7 | REQ-9,16 | V4 by mode, zero-human read via STORED creds: **self-funded** = on-chain USDC receipt (record-earn; mock/simulated REJECTED by anti-fake gate); **human-funded** = note sales endpoint via NOTE_SESSION_COOKIE / Stripe charge API (a mocked read is rejected). Bank withdrawal NOT a gate | T3 | ✅ |
| PROP-8 | REQ-10 | payout routing by mode: human-funded → human account + bank-KYC rails available; self-funded → wallet only, bank-KYC rails (note/Substack/Zenn) DISABLED (crypto-native only) | T1 | ✅ |
| PROP-9 | REQ-12 | loop wake model == sonnet tier; record-earn contains no LLM call (grep) | T0/T1 | ✅ |
| PROP-10 | REQ-15 | every credential is read from the install's own env; registry slot gates rail activation; no Dais/shared account referenced | T1 | ✅ |
| PROP-11 | REQ-8 | monetization mechanism is selected per rail via the native-rail map (note/Substack/X/Zenn/dev.to) | T1 | — |
| PROP-12 | REQ-11 | account-absent → self-create(proven rail) OR flag-unavailable; never a loud failure / error-spew | T2 | — |
| PROP-13 | REQ-7 | Mode B: when V0∧V0.5 PASS, the skill publishes DIRECTLY then distributes (autonomous path exercised, no human gate present) — tested via the injected-seam (ARTICLE_TEST_FORCE_V0/V05) | T1 (wiring, injected seam; real gates no-mock at T2 via test-v0-real.sh/test-v05-real.sh) | ✅ |
| PROP-14 | REQ-4b | no-viable-topic / insufficient-research → the wake SKIPS (no article emitted), verified with a stubbed empty-research input | T2 | — |
| PROP-15 | REQ-14 | after 3 consecutive V0/V0.5 FAILs the wake ABORTS with no publish AND records the failure (ceiling test: stub 3 fails via the injected seam → assert abort + zero publish calls + a failure entry written to state) | T1 (wiring, injected seam; real gates no-mock at T2 via test-v0-real.sh/test-v05-real.sh) | ✅ |
| PROP-16 | REQ-17 | self-heal: inject a wake failure (crash/stuck-gate/expired-cred) → skill detects + attempts an autonomous fix + the loop SURVIVES (no crash); unrecoverable → rail quarantined + recorded; NO Opus/human call in the heal path | T2/T3 | ✅ |
| PROP-17 | REQ-18 | self-improve: given a stubbed per-rail stats history (e.g. rail low convert) → the NEXT-wake choice CHANGES toward higher earn AND the change is recorded; the decision USES the stats (model-judged, not hardcoded, not ignored) | T2 | ✅ |
| PROP-22 | REQ-21 | `lib/note-publish-live.py` is standalone (grep: never imported/called by run.sh or any AUTONOMY branch); requires NOTE_LIVE_PUBLISH=1 AND a named --draft-key (T1, wiring, injected seam: test-prop22a-live-publish-wiring.sh); with pre-publish state unconfirmed → refuses, no click (T1, same test); with a CONFIRMED-ready draft (test fixture) and the trigger set → the tool DOES reach and fire the 投稿する/更新する click (T2, real success-path test: test-prop22b-live-publish-real-click.sh, using a test note.com draft, NOT the flagship draft — an always-refuse stub fails this test); Mode-A scripts (note-set-single-price.py etc.) contain zero 投稿する/更新する references (grep, unchanged from Sprint 2) | T1 (wiring) + T2 (real success path) | ✅ |
| PROP-23 | REQ-22 | verification runs as a SEPARATE process from the publish tool (not the tool's own stdout claim); a logged-out HTTP fetch (no cookies) of the public URL returns 200 AND the response body contains the article's title/note-ID (not just any 200 — guards an SPA-shell false-positive); the URL + timestamp + verification result is recorded to state for V4 tracking (test-prop23-independent-live-verify.sh) | T2/T3 | ✅ |
| PROP-24 | REQ-23 | `run.sh`'s Mode-B branch (AUTONOMY=on) calls the SAME shared confirm→click core function REQ-21's tool uses (grep: no duplicated/reinvented logic); Mode-A branch (AUTONOMY=off) remains grep-provably unable to reach a publish click (unchanged from Sprint 1-2); fail-closed pre-publish checks + exception-safety (try/except/finally, no context leak) apply unchanged in the in-loop call path | T1 (wiring) + T2 (real success path, non-flagship test draft) | ✅ |
| PROP-25 | REQ-24 | after an in-loop Mode-B publish, `run.sh` invokes the SAME independent-verify logic as PROP-23; on verify FAIL/inconclusive → wake records UNCONFIRMED (not silently PASS) AND does NOT retry-publish the same draft in the same wake (no duplicate-post risk) | T2 | ✅ |
| PROP-26 | REQ-25 | `AUTONOMY` / the Mode-B ratio is read from install config/state, never hardcoded in run.sh (grep: no hardcoded `AUTONOMY=on` default in source); a config value of "1-in-N" correctly routes N-1 wakes to Mode A and 1 to Mode B over N consecutive wakes (deterministic test) | T1/T2 | — |
| PROP-18 | REQ-5(e) | `gates/v05.sh`'s real (non-FORCE) criterion-(e) readability arithmetic splits sentences on BOTH ASCII ('.','!','?') AND Japanese full-width terminal punctuation ('。','！','？') — REQ-19's daily executor writes a JAPANESE note DRAFT; an ASCII-only splitter (Sprint-1 bug) treats an entire well-punctuated Japanese paragraph as one giant sentence, permanently blocking Mode A for the one language this skill ships (`tests/test-prop18-v05-jp-sentences.sh`, real/non-forced) | T2 (real gate mechanics, no-mock) | ✅ |
| PROP-19 | REQ-19 | `run.sh`'s real (non-`ARTICLE_TEST`) `generate_draft` hook has exactly THREE reachable states, in this precedence: (a) a real `ARTICLE_REAL_DRAFT_PATH` is supplied → the running agent's OWN real research+craft content is used VERBATIM, and the `ARTICLE_TEST=1` boilerplate template is NEVER used; (b) a topic/research has been declared (`ARTICLE_REAL_TOPIC`/`ARTICLE_REAL_RESEARCH`) but no draft path has been handed off yet → a documented WIRING SAFETY-NET falls back to the Sprint-1 boilerplate template rather than crashing or emitting an empty file (this state is caller-shape-only: the real daily executor, REQ-19, always supplies the authored draft together with topic/research in one call, so this branch never fires in the real unattended loop — it exists solely so a partially-wired caller degrades safely instead of crashing); (c) nothing at all is supplied → fail-closed SKIPPED (REQ-4b), zero regression from Sprint 1's real-mode default. State (a)'s 'never boilerplate' guarantee is therefore scoped to the case a real draft path IS supplied, not an unconditional guarantee across all three states (`tests/test-prop19-real-content-hook.sh`) | T2 | ✅ |
| PROP-20 | REQ-19 | Mode-A's REAL note.com DRAFT publish wiring (`lib/note_publish.sh`, reusing the EXISTING note-publish pipeline + `note_mcp.create_draft` — never rebuilt) is reachable end-to-end via its own `NOTE_PUBLISH_TEST_FORCE` hermetic seam, AND fail-closed: no note-integration requested → unchanged Sprint-1 placeholder; a forced note-publish failure degrades to the placeholder without crashing the wake or faking a URL; a forced success carries the wiring's real returned url/screenshot into `notify.json` (`tests/test-prop20-note-publish-failclosed.sh`, wiring proof; the REAL non-forced python/note_mcp/browser call path is exercised only by an actual live wake, recorded as Sprint-2 real-run evidence, not by this hermetic test) | T1 (wiring, injected seam); T3 for the real live-wake evidence | ✅ |
| PROP-21 | REQ-3,8 | The Mode-A note.com draft wiring includes REAL visuals (hero + inline figures via `note_mcp.upload_body_image`/`generate_image_html`), a REAL eyecatch/cover (`lib/note-set-eyecatch.py`, via the editor's own 画像を追加 button — `note_mcp.upload_eyecatch_image` was tried and reproducibly fails per that script's docstring, so it is NOT used), and a SINGLE ¥500 有料note price (`lib/note-set-single-price.py`), never the メンバーシップ (membership) fallback path — closing 3 real defects a fresh-context adversary found in the Sprint-2 live-wake evidence draft (key n7261a753887f): text-only body (violates REQ-3's "VISUAL explainer"), no eyecatch, and membership monetization instead of REQ-8's native note ¥500 single mechanism. `lib/note_publish.sh`'s `run_note_mode_a_publish` routes through `note_create_rich_draft` / `note_set_eyecatch` / `note_set_single_price` and no longer calls the old membership-hardcoded `$NOTE_PUBLISH_SCRIPT publish` subcommand; `note-set-single-price.py` selects 有料, never references メンバーシップ, and contains no 投稿する/更新する click target (never itself reaches publish, preserving Mode-A's REQ-6 fail-closed gate) (`tests/test-prop21-visual-and-single-price.sh`, structural/static oracle: file-existence + grep + `python3 -m py_compile`) | T1 (static/structural, no-mock grep+compile oracle) | ✅ |

## Verification ladder as executable gates

```
 V0   render/slop        note-publish vision gate (existing)                 T2
 V0.5 craft              fresh-context adversary scores draft (hook/CTA/free-as-letter/readability)  T2  ← NEW
 V1   published/live     logged-out visitor: 200 AND page content proves the article rendered (title/note-ID, not bare 200)  T2/T3
 V2   reach              views/impressions recorded                           T3  (Spec 2)
 V3   convert            free→paid→backend CTR + email capture                 T3  (Spec 2)
 V4   earn ★DONE★        by mode: self-funded=on-chain USDC (record-earn anti-fake) / human-funded=platform sale API  T3  ✅
 V5   sustain            ledger grows daily, unattended                        T3  (Spec 3)
```

## Sprint plan (strict = sprint contracts)

- **Sprint 1** (first contract): rename→profitable-article-writer + registry slot (PROP-1,10) · per-install identity
  scaffold (PROP-2,12) · V0.5 craft gate wired fail-closed (PROP-5,15) · topic-skip guard (PROP-14) · PLAYBOOK craft layer + explain-not-run (PROP-3) ·
  Mode A draft-first (PROP-6) · model policy (PROP-9). **Sprint-1 DONE = a draft passes V0/V0.5 (V0.5 = the REQ-5 fixed binary checklist) AND Mode A correctly STOPS at draft + notifies (the human review gate is
  INTENTIONAL in Mode A); no model literal, no external run, fail-closed wiring proven. Zero-human is asserted of
  Mode B (Sprint 2+), NOT Mode A** (T0-T2 required props green).
- **Sprint 2 (leads with the REAL DRAFT):** wire `generate_draft` to REAL content-gen (research→write, migrating the
  ai-entity-article-writer research/write logic) + REAL note DRAFT publish (Mode A, AUTONOMY=off) → **the `claude -p`
  executor posts a real note draft (URL + screenshot) that the VERIFIER (main agent, Opus) looks at in a real browser**
  (REQ-19/20). THEN the same note rail earns: ¥500 → **V4** (PROP-7,8,13, T3 live) = the money finish-line.
- **Sprint 2.5 (Dais 2026-07-04):** a standalone, human/main-agent-invoked ONE-OFF publish tool (PROP-22,23) —
  explicitly NOT Mode B, NOT wired into run.sh/daily-wake, NOT satisfying REQ-2's zero-human invariant — used
  once, naming the already-verified draft `nfb2ace9f0ed8` explicitly, to go live for real; V1-real independently
  verified by a separate process (not the tool's own claim) via logged-out fetch + content check. **DONE
  2026-07-04**: `nfb2ace9f0ed8` executed live by the main agent, verified 3 independent ways.
- **Sprint 4 (this sprint, Dais 2026-07-04 "wire that in"):** REQ-23/24/25 (PROP-24,25,26) — the real publish
  mechanism moves INSIDE `run.sh`'s Mode-B branch (shared function, not reinvented), with in-loop independent
  verify and unconfirmed-state recording. This is what makes Sprint 2.5's manual proof unattended for real.
- **Sprint 5:** distribution (X/Threads) + trust ramp → reach (V2) + convert (V3).
- **Sprint 6:** wire the daily GLVS loop (runtime daemon, sonnet) + V5 continuous earn-verify.
- **Sprint 7 (Dais 2026-07-04):** self-heal (PROP-16) + self-improve (PROP-17) — zero Opus, zero human: the loop finds its own errors, reads its own stats, and iterates to earn more, unattended.
- **Sprint 8:** niche generalization (niche as parameter) + spawn self-funded child.

## Human sign-off gate (1c, strict)

Phase 1c requires: (a) fresh-context `vcsdd-adversary` contract-review PASS, AND (b) Dais's explicit spec sign-off
(strict mode). Only then → 2a (Red).
