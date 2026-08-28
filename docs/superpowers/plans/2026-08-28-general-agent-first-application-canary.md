# GA-10 First Authorized Application Canary Plan

**Goal:** Close one new provider-authorized marketplace `ApplicationReceipt`, then replay the same WorkItem with external effect zero.

**Architecture:** Reuse GA-02 Goal WorkItem, GA-03 capability receipt, GA-04 effect/readback kernel, and GA-05 bounded specialist. The model chooses one truthful allowlisted action at a time; deterministic code owns browser action, effect identity, lease heartbeat, official readback, and replay. Provider-native success or the model's own success statement is never the receipt.

**Non-goals:** No Coconala change, Upwork UI action, provider-specific decision brain, margin allocator, multi-site scaling, account creation, mass application, paid option, CAPTCHA/KYC bypass, or legacy owner restart.

## Measured starting state

- Lancers terms Article 8 recognizes its provider-native automatic-proposal feature, but does not grant blanket external-browser permission.
- Private `authorizations.json` contains no Lancers receipt; public capability therefore remains `unknown`.
- The action-specific support inquiry is officially accepted and Gmail-confirmed. Private receipt: `~/.local/state/anicca/lancers/evidence/ga10-authorization-inquiry-receipt.json`.
- `lancers-revenue-application` is unloaded while authorization is pending. Historical `application_verified` count remains 32, latest `2026-08-15T11:50:29.420236Z`.

### Task 1: Terminal authorization receipt

1. Read the existing Gmail support thread only; do not send a duplicate inquiry.
2. Accept only a response that names external browser automation for the requested read/fill/submit/readback actions and conditions.
3. Hash the official response into one mode-600 private receipt. Map it to `approved_browser`, `approved_assisted`, or `denied`; silence remains `unknown`.
4. Keep the legacy application owner unloaded unless the exact action becomes approved.

### Task 2: One effect-free candidate and immutable intent

1. Read one fresh public or expressly authorized authenticated inventory through the existing browser owner.
2. Let the model select one job the general agent can truthfully deliver; deterministic code validates references and human-only blocks.
3. Seal one proposal intent and bind Goal, capability, opportunity, authorization, and intent refs into the GA-04 effect identity.
4. Require no paid option and no account/profile mutation.

### Task 3: Register the shared application adapter

1. Add only the thin `marketplace.application` adapter/services wiring needed to compose GA-04 with GA-05.
2. Write the focused failing tests first: pre-readback present replay, absent single bounded execution, cancel/heartbeat unknown effect, and official receipt verification.
3. Do not enable a production worker capability before the private authorization and candidate intent both exist.

### Task 4: Execute one live canary

1. Read official application history before the effect.
2. Claim the immutable effect once and execute the bounded specialist once.
3. On timeout/ack loss, send nothing again; reconcile official proposal history.
4. Accept success only from an exact provider proposal/application ID represented as the canonical `ApplicationReceipt`.

### Task 5: Replay zero and close

1. Run the same WorkItem again.
2. Require official readback `present`, `executeOnce` count zero, and the same receipt identity.
3. Persist the private receipt/evidence, update only GA-10 to DONE, fetch, commit, push, and read back PR #3018.
