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

## Verification ladder as executable gates

```
 V0   render/slop        note-publish vision gate (existing)                 T2
 V0.5 craft              fresh-context adversary scores draft (hook/CTA/free-as-letter/readability)  T2  ← NEW
 V1   published/live     logged-out visitor, URL 200                          T2
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
- **Sprint 2:** first real earn — one rail (note ¥500) reaches **V4**, autonomous publish (PROP-7,8,13, T3 live) = the money finish-line.
- **Sprint 3:** distribution (X/Threads) + trust ramp → reach (V2) + convert (V3).
- **Sprint 4:** wire the daily GLVS loop (runtime daemon, sonnet) + V5 continuous earn-verify.
- **Sprint 5 (Dais 2026-07-04):** self-heal (PROP-16) + self-improve (PROP-17) — zero Opus, zero human: the loop finds its own errors, reads its own stats, and iterates to earn more, unattended.
- **Sprint 6:** niche generalization (niche as parameter) + spawn self-funded child.

## Human sign-off gate (1c, strict)

Phase 1c requires: (a) fresh-context `vcsdd-adversary` contract-review PASS, AND (b) Dais's explicit spec sign-off
(strict mode). Only then → 2a (Red).
