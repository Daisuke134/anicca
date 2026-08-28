# GA-10 First Authorized Application Canary Plan

**Goal:** Close one new provider-authorized marketplace `ApplicationReceipt`, then replay the same WorkItem with external effect zero.

**Architecture:** Reuse GA-02 Goal WorkItem, GA-03 capability receipt, GA-04 effect/readback kernel, and GA-05 bounded specialist. The model chooses one truthful allowlisted action at a time; deterministic code owns browser action, effect identity, lease heartbeat, official readback, and replay. Provider-native success or the model's own success statement is never the receipt.

**Non-goals:** No Coconala change, Upwork UI action, provider-specific decision brain, margin allocator, multi-site scaling, account creation, mass application, paid option, CAPTCHA/KYC bypass, or legacy owner restart.

## Measured starting state

- Public capability remains `unknown`; Dais's direct instruction is the private execution authority.
- Private `authorizations.json` resolves the exact Lancers `submit_proposal` / `cloak_browser` action to `approved_browser` with evidence and receipt hashes.
- No further Lancers official inquiry, follow-up, or reply monitoring is allowed. The already-sent inquiry is left untouched.
- The legacy application owner stays unloaded; the general-agent canary owns the next effect. Historical `application_verified` count remains 32.

### Task 1: Terminal authorization receipt — DONE

1. Use Dais's direct instruction as the exact private execution authority.
2. Keep authorization mode 600 and bind provider, account, action, transport, evidence hash, receipt hash, and expiry.
3. Never contact or monitor Lancers official support for permission.
4. Keep the legacy application owner unloaded; only the general-agent canary may create the next effect.

### Task 2: One effect-free candidate and immutable intent

1. Read one fresh public or expressly authorized authenticated inventory through the existing browser owner.
2. Let the model select one job the general agent can truthfully deliver; deterministic code validates references and human-only blocks.
3. Seal one proposal intent and bind Goal, capability, opportunity, authorization, and intent refs into the GA-04 effect identity.
4. Require no paid option and no account/profile mutation.

### Task 3: Register the shared application adapter — DONE (`6c9d5d1ee`)

1. Add only the thin `marketplace.application` adapter/services wiring needed to compose GA-04 with GA-05.
2. Write the focused failing tests first: pre-readback present replay, absent single bounded execution, cancel/heartbeat unknown effect, and official receipt verification.
3. Do not enable a production worker capability before the private authorization and candidate intent both exist.

Measured result: the provider-neutral adapter composes GA-04 with an injected bounded execution service, manifest registration is portable, production worker capability remains disabled, and focused/adjacent Node tests pass 52/52.

### Task 4: Execute one live canary

1. Read official application history before the effect.
2. Claim the immutable effect once and execute the bounded specialist once.
3. On timeout/ack loss, send nothing again; reconcile official proposal history.
4. Accept success only from an exact provider proposal/application ID represented as the canonical `ApplicationReceipt`.

### Task 5: Replay zero and close

1. Run the same WorkItem again.
2. Require official readback `present`, `executeOnce` count zero, and the same receipt identity.
3. Persist the private receipt/evidence, update only GA-10 to DONE, fetch, commit, push, and read back PR #3018.
