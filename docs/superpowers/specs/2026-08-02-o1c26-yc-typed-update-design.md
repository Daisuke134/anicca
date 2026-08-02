# O1C-26 YC Typed Update Design

## Objective

Resolve the blockers recorded by O1C-25, rebuild a fresh five-scope preview, and—only when that preview says `submit_ready:true`—apply the smallest truthful set of **typed YC updates** exactly once. The already-submitted Fall 2026 application remains immutable: O1C-07 is the sole application-submit receipt and application resubmission is permanently forbidden.

## Verified starting state

- Fall 2026 application `0b61fe42-e383-490d-b60e-04f1ad7ec5df` is `In review`.
- The submitted application body still describes the old Anicca pitch and has no editable main-answer route.
- YC currently exposes separate update surfaces for progress, team, founder profile, founder video, and demo.
- O1C-25 found six blockers: stale company facts, provider-route drift, stale founder narratives, founder-source conflict, missing demo, and stale progress.
- The repository README and `agents/registry.json` are the current product sources: Life Manager is one product with local/self-hosted and cloud/Web execution surfaces, and the orchestrator delegates to a declared specialist-agent organization.
- The public landing page and dashboard still use the old Anicca framing. They are evidence of deployed public state, not a truthful visual source for the new Life Manager product story.
- A dedicated Life Manager product demo does not exist. Unrelated founder, ReelClaw, Honne, or Capafy videos may not be relabelled as the demo.
- The old provider manifest models pre-submission `main` and an obsolete progress form. It cannot drive a submitted-application update.

## Alternatives

### A. Re-edit or resubmit the original application

Rejected. There is no current edit route for the submitted 20-field body, and another application Submit would violate the historical one-submit boundary.

### B. Upload only a demo

Rejected. It would leave progress, founder narrative/source, and provider-route blockers unresolved while creating a misleading appearance of readiness.

### C. Execute a closed typed-update bundle

Selected. Preserve the original application as historical evidence; communicate current company/product facts through the official progress update, correct the current team/profile narratives only where fresh readback proves a material difference, attach a dedicated real-screen demo, and record each typed operation behind an independent exactly-once fence.

## User-visible update model

```text
submitted application (historical, immutable)
                    │
                    ├── Progress Update ─ current product / users / revenue / work / stack
                    ├── Team Update ───── current solo-founder facts, only when changed
                    ├── Founder Profile ─ verified current narrative, only when changed
                    └── Demo Update ────── dedicated Life Manager product demo
                                             │
                                             v
                                  immediate remote readback
```

The bundle is one O1C-26 business transaction, but not one ambiguous click. Each child operation has a closed type, target route, payload digest, asset digest when applicable, idempotency key, expected control, effect ceiling, and exact readback contract.

## Exactly-once semantics

An operation identity is the SHA-256 of:

`application_id + operation_type + target_route + payload_digest + asset_digest_or_none`.

For each operation:

1. A fresh preview proves the exact route, controls, source artifacts, and expected readback.
2. A durable local effect fence is written in `prepared` state before any remote mutation.
3. The remote control may be activated at most once.
4. The fence moves to `effect_attempted` before waiting for navigation or confirmation.
5. A timeout or ambiguous response is **not retried**; the agent performs readback and records `confirmed`, `not_applied`, or `unknown_effect`.
6. Only a proven `not_applied` result may create a new plan, and never under the same operation identity in O1C-26.

Application-submit effects must remain zero in every state. A second control activation, a changed payload after preparation, or an absent durable fence fails closed.

## Typed operations

| Type | Purpose | Execution rule |
|---|---|---|
| `progress_update` | Publish current product link, access guidance, product progress, founder work status, technology, users, and revenue through the current submitted-application progress surface | Required; exactly one submit attempt after full preview readiness |
| `team_update` | Correct the old cofounder/team story to the verified current team state | Conditional; omit when normalized remote values already equal the current source |
| `founder_profile_update` | Correct only verified narrative/source differences while preserving private identity fields | Conditional; omit when no source-backed material difference remains |
| `demo_update` | Upload the dedicated Life Manager demo and prove remote media readiness | Required; exactly one save/upload attempt after local media validation |

Founder-video replacement is excluded unless fresh observation finds the existing 58-second file invalid. Its current media is already present, playable, and under YC's 60-second limit.

## Current-facts bundle

Semantic content is agent-authored from current evidence. Deterministic code never decides whether prose is truthful by matching keywords.

Required source classes:

- current repository identity, README, and agent registry;
- current deploy/public-surface observations, including zero-user/zero-revenue facts when observed;
- current founder profile and Application Kit sources with conflicts explicitly resolved;
- dedicated demo source with SHA-256, bytes, duration, codecs, dimensions, and a bounded visual-truth inventory;
- O1C-07 application-submit receipt and O1C-25 preview receipt;
- fresh YC route observations and the corrected provider manifest.

The update copy must not claim users, revenue, public cloud UX, autonomous earnings, or agent health beyond current evidence. Historical on-chain settlements must be labelled historical and must not be promoted to current recurring revenue or live-user claims.

## Demo design

The demo is a 16:9, English, 45–75 second, show-it-as-is product walkthrough for YC. It uses only current, captured sources:

1. the repository's one-product/two-surfaces architecture;
2. the real local install and runtime entrypoints;
3. the generated current agent registry/catalog;
4. the real cloud service and panel code/available screen surfaces;
5. the public dashboard as it actually appears, including zero live instances when that is the current readback.

The video must visually distinguish `live`, `legacy live`, `shadow`, and `planned`. It may explain future direction, but it may not render a planned agent or absent cloud screen as already working. The HyperFrames `product-launch-video` workflow owns capture, source provenance, snapshots, lint/check, and rendering. The run is autonomous (`flow: automation`, `storyboard: no`) because the user explicitly requested no human in the loop.

## Provider manifest

Replace the obsolete four-page pre-submission model with a versioned submitted-application update manifest. The manifest contains only freshly observed routes, exact locator cardinalities, allowed file/text/choice setter mechanisms, exact activation controls, and per-field readback requirements. Unsupported main-body editing and application Submit do not appear as executable operations.

Manifest and plan validation are closed-schema and content-addressed. Any route drift, missing/duplicate control, selector cardinality change, unbound source, stale observation, or unsupported operation closes `submit_ready`.

## Preview and execution gates

The fresh O1C-26 preview must cover company facts, founder profile, founder video, demo, and progress exactly once and must bind the prepared operation bundle. `submit_ready:true` requires:

- no O1C-25 blocker remains;
- all required current sources are fresh and content-addressed;
- the demo passes local media and visual-truth checks;
- every planned typed operation has a current provider route and exact readback contract;
- conditional operations are either planned with a material-difference receipt or omitted with an equality receipt;
- all pre-execution mutation effects are zero;
- historical application submits equal exactly one and planned application submits equal zero.

If any gate is false, no remote operation runs.

## Privacy and evidence

Checked-in evidence may contain normalized non-secret update copy, route templates, digests, byte counts, media metadata, bounded value lengths, operation states, and sanitized readbacks. It must not contain cookies, tokens, headers, signed URLs, passwords, birth date, phone number, private email, raw private profile fields, or browser storage.

The browser connection uses the existing CloakBrowser daily-driver `:9222`, an owned temporary page, and never calls `browser.close()`. Each remote effect and readback is counted separately. Evidence claims exactly what was observed, not inferred backend behavior.

## Failure behavior

- No preview readiness: zero update attempts.
- Any application-submit control or effect: fail closed.
- Missing fence, payload drift, stale plan, route drift, or duplicate operation identity: fail closed.
- Ambiguous remote response: `unknown_effect`, no retry, readback only.
- Readback mismatch after a confirmed effect: record failure honestly; do not overwrite evidence or issue a second attempt.
- Video capture/render failure: no synthetic or unrelated replacement and no YC upload.

## Verification

1. Write adversarial tests before implementation for operation identity, fence transitions, duplicate-attempt rejection, unknown-effect behavior, conditional omission, manifest closure, application-submit prohibition, and readback binding.
2. Build the dedicated demo through the required HyperFrames gates and inspect the contact sheet and final MP4.
3. Re-observe all five YC scopes and construct a fresh `submit_ready:true` preview bound to exact payload/media bytes.
4. Execute only the prepared typed operations, each at most once, with immediate remote readback.
5. Run focused tests, outbound tests, runtime-up tests, full `npm test`, JSON/digest/privacy checks, browser ownership checks, and independent review.

## Self-review and approval

- The design preserves the historical submitted application and forbids resubmission.
- It resolves every O1C-25 blocker rather than hiding one behind a demo upload.
- It distinguishes deterministic safety from agent-owned semantic judgment.
- It treats zero users/revenue and stale public surfaces honestly.
- Dais requested sequential execution with no human in the loop. The agent selected and approved Alternative C on 2026-08-02 and proceeded without a human approval pause.
