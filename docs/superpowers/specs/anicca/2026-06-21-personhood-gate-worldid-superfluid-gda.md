# Personhood gate (World ID) + Superfluid GDA — design spec (task #36)

UBI must reach **unique humans**, not sybils. Today /income lets anyone enter a wallet/email and
claim — a single actor can drain the pool with N addresses. This spec adds a personhood gate
(World ID, no Orb required) and an optional continuous-distribution mechanism (Superfluid GDA).

## Problem / invariants
- **One human → at most one active UBI recipient.** Enforced by World ID's `nullifier_hash`
  (a per-app, per-action anonymous unique id) stored once; a second claim with the same nullifier is refused.
- **Privacy**: we store only the `nullifier_hash` (opaque) + the payout destination — never identity.
- **No Orb requirement**: accept `verification_level: "device"` (World App on phone) so anyone can verify;
  Orb (`orb`) is a stronger optional tier, not required. Lower friction = more reach to crypto-naive people.
- **Money-safety unchanged**: the gate sits BEFORE enqueue; it never touches the send path's
  at-most-once / at-least-once / own-funds invariants (skills/ubi).

## Parts
### 1. World ID app (self-serve signup — NOT sales-gated)
- developer.worldcoin.org → create app (Staging then Production) → get `app_id` (app_xxx) + define an
  `action` (e.g. `claim-ubi`). Self-serve via CloakBrowser daily-driver (Dais's Google login).
- Store `WORLDCOIN_APP_ID` + `WORLDCOIN_ACTION` in env (~/.openclaw/.env / apps/api env). No secret needed
  for verify (the verify endpoint is public per-app), but keep app_id in env not code.

### 2. Backend verify (apps/api) — the core, build-first + testable
- New route `apps/api/src/routes/personhood` (or under existing claim flow):
  `POST /personhood/verify` body `{ proof, merkle_root, nullifier_hash, verification_level, action, signal }`.
- Calls Worldcoin: `POST https://developer.worldcoin.org/api/v2/verify/{app_id}` with the proof bundle.
- On `success`: upsert `nullifier_hash` → if already present for this action, return `409 already_claimed`
  (the sybil refusal); else record and allow the claim to proceed to the ubi enqueue.
- Pure helpers (testable, VSDD): `buildVerifyBody`, `isDuplicateNullifier(seen, hash)`, `mapVerifyResult`.
- GATE: needs `WORLDCOIN_APP_ID` to E2E; code-ready without it (like the payout rails).

### 3. Frontend gate (apps/landing /income) — AFTER backend, WITH taste skill (HARD 0.38)
- `@worldcoin/idkit` `IDKitWidget` (app_id, action, `verification_level="device"`, `handleVerify` → POST to
  backend verify, `onSuccess` → unlock the claim form). Invoke `gpt-tasteskill` before building the UI;
  verify rendered UI in a real browser.

### 4. Superfluid GDA (optional, phase 2 — continuous distribution)
- GDA (General Distribution Agreement) = one pool, N members, stream/distribute pro-rata in one tx.
- Fits "proactive UBI" (#39): verified humans become pool members (units=1 each); anicca distributes the
  earned USDCx to the pool → every member's balance flows continuously. Replaces per-cycle batch sends for
  the on-chain cohort. Contract-side; sits alongside (not replacing) bank/email/mobile rails.
- Verify Superfluid live (SDK + GDA pool on Base) before committing — do not trust docs (VSDD).

## Build order (one-by-one, each VSDD-verified)
1. Backend `buildVerifyBody`/`isDuplicateNullifier`/`mapVerifyResult` + route + tests (code-ready, gate=app_id).
2. Self-serve World ID app signup (CloakBrowser) → app_id → E2E the backend verify.
3. Frontend IDKit widget on /income (taste skill + browser verify).
4. (Phase 2) Superfluid GDA pool for the on-chain cohort.

## Done = 4-D convergence
spec(this) ✓ → tests (verify helpers + dup-nullifier) ✓ → impl (route + widget) ✓ → adversarial gate
(sybil bypass attempts: replay proof, reused nullifier, level downgrade) all refuted ✓.
