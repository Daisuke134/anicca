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
| PROP-3 | REQ-3 | **deterministic:** the article write-path makes NO external-repo/tool execution call (static trace). The semantic "no claim of having run" check is delegated to the V0.5 judgment gate (adversary), NOT a keyword blocklist (paraphrase-proof) | T1 | ✅ |
| PROP-4 | REQ-4 | one wake → exactly ONE article artifact containing theme + buy-reason-3-lines + free/paid split + body | T2 | — |
| PROP-5 | REQ-5,14 | **fail-closed WIRING** (deterministic, independent of V0.5's internal rubric): inject a stubbed FAIL from V0 OR V0.5 → assert publish is NOT called; only BOTH-PASS reaches publish. Repeatable regardless of craft-score judgment | T2 | ✅ |
| PROP-6 | REQ-6 | Mode A: no publish call is made; draft + notify(URL+screenshot) only | T2 | ✅ |
| PROP-7 | REQ-9,16 | V4 by mode, zero-human-verifiable: **self-funded** = on-chain USDC receipt via record-earn (fake/mock/simulated REJECTED by anti-fake gate); **human-funded** = platform sale-event confirmed via API/dashboard. Bank withdrawal is NOT a gate | T3 | ✅ |
| PROP-8 | REQ-10 | payout routing by mode: human-funded → human account + bank-KYC rails available; self-funded → wallet only, bank-KYC rails (note/Substack/Zenn) DISABLED (crypto-native only) | T1 | ✅ |
| PROP-9 | REQ-12 | loop wake model == sonnet tier; record-earn contains no LLM call (grep) | T0/T1 | ✅ |
| PROP-10 | REQ-15 | every credential is read from the install's own env; registry slot gates rail activation; no Dais/shared account referenced | T1 | ✅ |
| PROP-11 | REQ-8 | monetization mechanism is selected per rail via the native-rail map (note/Substack/X/Zenn/dev.to) | T1 | — |
| PROP-12 | REQ-11 | account-absent → self-create(proven rail) OR flag-unavailable; never a loud failure / error-spew | T2 | — |
| PROP-13 | REQ-7 | Mode B: when V0∧V0.5 PASS, the skill publishes DIRECTLY then distributes (autonomous path exercised, no human gate present) | T2 | ✅ |
| PROP-14 | REQ-4b | no-viable-topic / insufficient-research → the wake SKIPS (no article emitted), verified with a stubbed empty-research input | T2 | — |

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
  scaffold (PROP-2,12) · V0.5 craft gate wired fail-closed (PROP-5) · PLAYBOOK craft layer + explain-not-run (PROP-3) ·
  Mode A draft-first (PROP-6) · model policy (PROP-9). **Sprint-1 DONE = a draft passes V0/V0.5 AND Mode A correctly STOPS at draft + notifies (the human review gate is
  INTENTIONAL in Mode A); no model literal, no external run, fail-closed wiring proven. Zero-human is asserted of
  Mode B (Sprint 2+), NOT Mode A** (T0-T2 required props green).
- **Sprint 2:** first real earn — one rail (note ¥500) reaches **V4** (PROP-7,8, T3 live) = the money finish-line.
- Later sprints: distribution/reach (V2/V3), daily loop (V5), niche generalization.

## Human sign-off gate (1c, strict)

Phase 1c requires: (a) fresh-context `vcsdd-adversary` contract-review PASS, AND (b) Dais's explicit spec sign-off
(strict mode). Only then → 2a (Red).
