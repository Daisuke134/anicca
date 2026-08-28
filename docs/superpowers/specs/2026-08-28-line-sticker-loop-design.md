# Life Manager LINE Animated Sticker Loop Design

## Decision

Life Manager ships one open-source, local-first loop that repeatedly creates, submits,
releases, observes, and improves LINE animated sticker sets. The first product uses a new,
AI-generated character with a recorded provenance manifest. It follows the referenced
Hoko workflow—character sheet, 60 motion ideas, video generation, APNG conversion, 24-item
selection, and submission—but official LINE Creators Market rules are the acceptance source.
The reported JPY 1.3 million result is a case-study claim, never a forecast or receipt.

The normal path has no human approval gate. The loop may pause only at an official ceremony
that cannot be completed from the existing authorized session, such as SMS, identity,
CAPTCHA, tax, or bank registration. That pause is `NEEDS_OWNER_CEREMONY`, not completion.

## Outcome

One installed launchd owner repeatedly performs:

```text
official inventory and prior sales
-> original character and 60 motion candidates
-> generated source videos
-> deterministic transparent APNG package
-> model-ranked 24-item set
-> one fenced Creators Market submission
-> official review readback
-> rejection repair or release
-> official public-store and sales readback
-> one bounded evidence-backed improvement
-> next set
```

The first loop is complete only when an official public LINE STORE product page matches the
submitted set, a durable receipt binds the public product id and artifact hashes, and a later
observe-only wake produces `duplicate_effect=0`. A ZIP, passing tests, submitted status,
process liveness, or a notification is not completion.

## Source hierarchy

1. Current official LINE pages:
   - `https://creator.line.me/en/guideline/animationsticker/`
   - `https://creator.line.me/en/review_guideline/`
   - `https://creator.line.me/en/howto/`
2. Authenticated Creators Market DOM and official LINE STORE readback.
3. The Hoko post at `https://x.com/hoko525/status/2092946088978497931` as a creative
   workflow and quality heuristic only.
4. Third-party repositories as implementation references only. Their copied facts never
   override current official pages.

The inspected official requirements currently say: 8, 16, or 24 animated stickers; APNG
files named `.png`; sticker canvas at most 320 x 270 with one dimension reaching 270;
5–20 frames; 1–4 loops totaling at most four seconds; RGB; transparent background; each
image under 1 MB; ZIP under 60 MB; main image 240 x 240 APNG; tab image 96 x 74 PNG.
These values live in one versioned policy fixture and are re-read before every submission.
The post's 300 KB and exact-duration advice remains an optional stricter optimization,
not an upload rejection rule.

## Scope

Included:

- original character definition, provenance, character sheet, and reusable visual anchors;
- model-generated 60-motion plan with universal, text-free, daily-chat intent;
- provider-neutral image and video command adapters with frozen inputs and outputs;
- green-screen removal, frame extraction, APNG encoding, optimization, and ZIP assembly;
- deterministic LINE format, alpha-hole, duplicate, variety, and provenance validation;
- a local contact-sheet/replay artifact for model visual ranking and fresh pre-submit review;
- selection and ordering of 24 stickers, with high-frequency reactions early and similar
  motions separated;
- dedicated persistent Creators Market browser profile and browser-direct submission;
- review polling, rejection reason capture, bounded repair, resubmission, release, and
  public-store readback;
- sales readback and one bounded next-set change based only on official observations;
- immutable receipts, effect fencing, restart/resume, next-wake duplicate zero, launchd,
  installer manifest, outcomes command, and OSS documentation.

Excluded from the first implementation slice:

- static, message, custom, popup, effect stickers, emoji, or themes;
- paid ads, influencer outreach, or unsupported marketplace APIs;
- a custom workflow engine, database, web dashboard, or hosted media service;
- revenue promises or synthetic sales data;
- automatic spending outside an explicit local per-set provider cap;
- replacing Life Manager's shared browser, runner, release, receipt, or notification cores.

## Architecture

The loop is a bounded Python owner under `skills/earn/line-sticker/`. Python standard library
owns state, hashes, atomic writes, ZIPs, subprocess execution, and receipts. Existing installed
media tools own video inspection and conversion. Pillow is permitted only if already installed
by the selected Life Manager media path; the implementation must not add a workflow framework.
Creative judgment stays in the configured model runner. Deterministic code never uses keyword
lists or hand scores to decide what is expressive, attractive, or marketable.

The production package contains four units:

1. `line_sticker.py`: state machine, immutable artifact manifest, official policy validation,
   effect keys, receipts, and CLI.
2. `line_sticker_media.py`: model-facing motion-plan/selection tools and deterministic bounded
   video segmentation, chroma-key, APNG conversion, package assembly, provider receipts, and
   disk/cost gates. Creative judgment remains in the configured model, not this tool.
3. `line_sticker_browser.py`: the only Creators Market mutation boundary. It attaches to one
   dedicated profile, observes official state, submits/resubmits/releases once, and reads back.
4. `line-sticker-loop.sh`: disk guard, model/media command resolution, one bounded wake, and
   structured outcome emission for launchd.

Tests use generated tiny fixtures and a fake browser adapter. They never log in, upload, submit,
release, spend, or claim a public product.

## State and identity

Each set has stable `set_id`, `character_id`, `revision`, and artifact directory. External
effects use `(account_id, set_id, revision, action)` as the effect key. State is atomically
replaced JSON; receipts are append-only JSONL. Source media and official readbacks are content
addressed. A later wake resumes the same owner.

```text
NEW
-> PLANNED
-> SOURCES_READY
-> PACKAGE_READY
-> QA_APPROVED
-> SUBMITTED
-> WAITING_REVIEW
-> REJECTED -> REPAIRING -> QA_APPROVED
-> APPROVED
-> RELEASED
-> PUBLIC_VERIFIED
-> TERMINAL_PENDING_REPLAY
-> CLOSED
```

`reconcile_unknown` follows any lost acknowledgement. No submit, resubmit, or release retry is
allowed until official readback proves whether the prior action happened. `CLOSED` is immutable.

## Creative and quality contract

- The character is original, recognizable at 96 x 74, and retains a small stable set of
  visual anchors across every motion.
- The first set contains no language-bearing text. Motion communicates a common chat intent.
- The model proposes 60 motions without prematurely discarding difficult ideas. It selects 24
  only after viewing generated motion artifacts and deterministic validator results.
- The first APNG frame is a useful store preview. Movement is legible at chat size.
- The set covers varied everyday communication and avoids materially duplicate motions.
- Transparent pixels connected to the outer background are expected. Enclosed transparent
  components inside the character are rejected unless declared intentional in the manifest.
- Every frame passes dimensions, RGB/RGBA, frame count, duration, loop, byte-size, and alpha
  checks. Main and tab images visibly correspond to the submitted set.
- A fresh model reviewer checks the exact 24 animations, metadata, rights manifest, official
  policy snapshot, and ZIP manifest before the effect fence opens.

## Provider and money contract

Image/video providers are commands described by a local private configuration. The public repo
contains interfaces and safe fixtures, never credentials. A generation quote must be read before
effect, be within the configured per-set cap, and be durably reserved by `set_id`. Unknown cost or
missing provenance fails before generation or submission.
No provider is retried after an acknowledged paid generation effect; it is reconciled first.

The first live animation route uses official Runware P-Video
(`prunaai:p-video@0`) in 720p draft mode. The official schema supports image-to-video and a maximum
duration of ten seconds; the official catalog price is USD 0.005 per second in that configuration.
The source of truth is `https://runware.ai/docs/models/prunaai-p-video` plus the official
`model pricing` readback. The production reference enters through its previously read-back Runware
media UUID. No local path, credential, or invented cost enters the provider request.

The animation adapter protocol is two-phase and identity-first. `quote` returns provider, model,
stable request id, quote token, exact Decimal cost, and expiry without generating media. The loop
binds that identity to plan/batch/character hashes, reserves cost durably, then calls `generate`
with the same identity and remaining cap. `reconcile` is the only operation allowed after unknown
acknowledgement. Provider/model/request/video hashes match across all three phases.

One atomic `convert-state.json` is the only authority for all six batch quotes, reservations,
generation/reconciliation receipts, and costs. Totals are recomputed from those batch records rather
than incremented separately. Immediately before a generate call, the batch is durably marked
`reconcile_required`; every later wake calls only `reconcile` until the provider proves either a
matching completed generation or an authoritative absent/no-effect result.

Generated source media is deleted only when the provider explicitly marks it regenerable, all ten
bound segments produced valid durable candidates, and their hashes/receipts are fsynced. Otherwise
the source remains. The loop processes one source video at a time. If a file write fails, it keeps
the last durable checkpoint, creates no external effect, and retries that same item on a later wake.
There is no fixed disk-size requirement, capacity calculator, or disk-management subsystem.

Creators Market has no assumed public submission API. The adapter uses the dedicated authenticated
browser and official pages. Credentials remain in the private credential SSOT and browser profile,
never state, prompts, Git, logs, reports, or notifications.

## Submission, review, and repair

Before submission the browser adapter records official inventory and searches for an existing
draft, review, approved item, or public product matching `set_id` and artifact hashes. It creates
or mutates exactly one matching product. It records metadata, price, regions, AI declaration,
ZIP hash, and official product id from readback.

Review polling is observe-only. On rejection, the adapter saves exact provider text and affected
asset identity. The model proposes the smallest repair grounded in that reason; deterministic QA
and fresh review run again before one fenced resubmission. Three repeated identical rejections move
to `NEEDS_POLICY_REVIEW` while sales observation and other independent sets continue.

On approval, release is automatic. Completion requires the official LINE STORE URL to load and
match product id, title, creator, item count, and released state. The following wake is forced
observe-only and must record zero duplicate external effects.

## Improvement loop

The loop records only official sales, region, distribution, and payout data exposed to the seller.
It never attributes revenue to a creative choice without evidence. After a minimum observation
window, the model may change exactly one of character concept, motion mix, ordering, title/metadata,
price, or region selection for the next set. The change, evidence, hypothesis, cost, and later
official result are bound in an experiment receipt. Lack of sales is a measured result, not failure
of the runtime and not permission to spam submissions.

## OSS and onboarding

The public integration manifest declares prerequisites, private profile location, readiness,
activation, outcomes, stop, recovery, upgrade, uninstall, money cap, official ceremonies, effect
receipts, and replay proof. A clean Mac installation opens the dedicated Creators Market profile,
asks the owner to complete only missing official registration ceremonies, verifies readiness, and
starts the launchd owner. Private state and generated artifacts are preserved on uninstall unless
the owner explicitly requests their deletion.

The package's exact provenance schema includes a `generation` object bound into
`package_sha256`: character rights evidence, character/plan/selection hashes, provider quote and
generation receipts, request ids, costs, source/segment/candidate hashes, and conversion argv
hashes. Missing or invented rights/provider evidence fails validation. A parallel mutable ledger
cannot substitute for package-bound provenance.

Character rights evidence is an explicit hashed input receipt that binds the character id and exact
character file hash. The media tool never creates or infers `original_ai_generated` rights from an
arbitrary character file.

## Acceptance gates

Code-owned gate:

- clean fixture run creates one valid 24-item package and manifest;
- malformed dimensions, frame count, playback, file size, alpha hole, duplicate asset, missing
  provenance, stale policy, failed file writes, and unknown cost prevent the external effect and
  preserve a retryable checkpoint;
- fake provider proves submit, lost-ack reconciliation, rejection repair, release, official
  readback, restart/resume, and next-wake `duplicate_effect=0`;
- installer manifest and launchd job pass existing Life Manager validators;
- no secret or private path enters tracked files or test output.

Production gate:

- the installed launchd owner—not foreground Codex—generates the real set;
- all 24 exact APNGs and metadata pass deterministic QA and fresh visual review;
- official Creators Market readback proves one submitted product;
- rejection is repaired until approved or an exact official blocker is recorded;
- the loop releases the approved product;
- official LINE STORE readback proves the public product and intended metadata;
- a later natural wake records `effect=0` and `duplicate_effect=0` for submit and release;
- official sales observation seeds one bounded next-set decision.

No narrower evidence closes the goal.

## Current measured status and remaining work

### Verified implementation state

- The package validator and durable submit/release owner are implemented and pushed on
  `feat/line-sticker-loop`. Their fresh whole-branch review is `READY` with no remaining
  Critical or Important finding.
- The validator/owner suite has 80 tests covering real FFmpeg APNG packages, official-policy
  bounds, provenance, concurrent effect fencing, lost acknowledgement, receipt crash recovery,
  public URL/product binding, and replay zero.
- The redesigned media pipeline implements model-owned 60-motion planning and 24-item selection,
  quote-before-generate cost reservation, reconcile-only unknown recovery, bounded subprocesses,
  safe motion ids, one-video-at-a-time checkpoints, APNG timing, visual-inspection readback, and
  package-bound generation provenance. A fresh parent run passes all 16 media tests, including a real
  six-batch FFmpeg package.
- The private credential SSOT contains one email-verified Runware workspace and an enabled
  `line-sticker-loop` API key. Official read-only account readback reports USD 0.05 balance and zero
  generation requests/credits. Current official CLI pricing readback identifies live
  `prunaai:p-video@0` and quotes 720p draft video at USD 0.005 per second. The adapter recomputes the
  ten-second USD 0.05 quote from that live readback before signing it; all eight adapter tests pass.
- Private set `set-001` contains one original text-free `char-001` character sheet with four views,
  six expressions, and stable color/silhouette anchors. Its exact SHA-256 is bound by a mode-600
  `original_ai_generated` rights receipt. The built-in image generator created it without Runware
  credit use; its attempted transparent background is RGB checkerboard, so it remains a character
  reference rather than a submission asset.
- A derived production reference contains one centered front-facing character on chroma green. Its
  SHA-256 and mode-600 rights receipt match, and an official Runware media receipt binds its upload.
- The active real model plan has canonical `plan_sha256`
  `b90a1682e791bb71f61fe74b9be8454e6680d4af70362dccb019dbe93bc005f4` and contains 60 unique ids,
  60 unique batch/position pairs, six batches of
  ten, and 60 distinct intents/actions. Every motion is exactly 1000 milliseconds, so every batch
  fits one ten-second source video without adaptive timing. Its canonical SHA-256 and durable plan
  receipt match. Real model execution exposed and closed two prompt/validator gaps: the top-level
  JSON schema and the source-video duration bound.
- No real Runware animation generation, Creators Market submission, review, release, public product,
  sale, payout, or bank effect has occurred.

### Money truth

Verified LINE sticker revenue is **JPY 0**. There is no Creators Market sales receipt, payout
receipt, or bank-arrival receipt. Local tests, generated fixtures, commits, and provider research
do not count as money.

### Current blockers to revenue

1. No real motion generation has run. The Runware balance is USD 0.05 and the first ten-second
   P-Video draft quote is exactly USD 0.05, leaving no balance for later batches. Any later personal
   funding must obey the money-safety boundary.
2. No authenticated LINE Creators Market browser session or dedicated profile exists, and no LINE
   credential entry is configured in the private credential SSOT.

Disk capacity is not a product requirement or revenue blocker. The fixed-threshold media gate is
removed. A forced `ENOSPC` preserves the prior checkpoint, and the same destination succeeds when
retried after the temporary failure clears.

### Atomic remaining TODO order

Each row is one action with one completion receipt. Execute from top to bottom; do not start a later
row while an earlier row is unfinished.

| ID | One action | Done evidence |
| --- | --- | --- |
| A01 — DONE | Remove the temporary fixed disk threshold; on write failure retain the current checkpoint and exit with no external effect. | Parent media 9/9 PASS; fresh review READY; forced `ENOSPC` preserves and retries the same checkpoint. |
| A02 — DONE | Run the redesigned media tests plus the full validator/owner regression and obtain fresh adversarial review. | Parent Media 13/13 + Validator 32/32 + Owner 48/48 PASS; final review has no Critical, Important, or Minor finding. |
| A03 — DONE | Connect one real animation provider account through the private credential SSOT. | Official Runware account readback binds workspace `anicca-line-sticker` and enabled key `line-sticker-loop`; current official CLI pricing binds live `prunaai:p-video@0` and USD 0.005/second for 720p draft; usage remains zero. |
| A04 — DONE | Generate one original character sheet and save its rights evidence. | The sheet SHA-256 `902222ab709ab930c7651ce8c89c3807fcf8c53f3ccd2c79e7a2b14f6ae1b3ba` and production-reference SHA-256 `7aa14830d0cba2cebf09c33cbcab5cc651f5d6cd5ae0c60dc3e357f358ab830b` each match their mode-600 rights receipts; the latter also has an official Runware media-upload receipt. |
| A05 — DONE | Ask the model for the exact 60-motion plan. | Active canonical `plan_sha256` `b90a1682e791bb71f61fe74b9be8454e6680d4af70362dccb019dbe93bc005f4` binds 60 unique one-second motions in six exact ten-second batches; its receipt and recomputed canonical hash match. |
| A06 | Generate and convert batch 1 into ten valid candidates. | Ten candidate hashes pass the LINE validator. |
| A07 | Generate and convert batch 2 into ten valid candidates. | Ten candidate hashes pass the LINE validator. |
| A08 | Generate and convert batch 3 into ten valid candidates. | Ten candidate hashes pass the LINE validator. |
| A09 | Generate and convert batch 4 into ten valid candidates. | Ten candidate hashes pass the LINE validator. |
| A10 | Generate and convert batch 5 into ten valid candidates. | Ten candidate hashes pass the LINE validator. |
| A11 | Generate and convert batch 6 into ten valid candidates. | Ten candidate hashes pass the LINE validator. |
| A12 | Ask the model to inspect all 60 candidates and select/order 24. | Selection receipt binds all 60 input hashes and 24 ordered output ids. |
| A13 | Build the real LINE package. | `main.png`, `tab.png`, 24 APNGs, provenance, and ZIP pass the validator. |
| B01 | Create or recover one dedicated authenticated Creators Market browser session. | Official account page reads back the creator identity. |
| B02 | Read the official product inventory before mutation. | Inventory receipt records whether the package already exists. |
| B03 | Upload and submit the package once. | Official Creators Market product id and submitted state read back. |
| B04 | Read the official review result on a later wake. | Exact approved or rejected state and reason are recorded. |
| B05 | If rejected, repair only the stated defect and resubmit once. | New official submitted state binds the repaired package hash. |
| B06 | When approved, release once and verify the public product. | Matching LINE STORE URL loads with the intended product id and 24 items. |
| C01 | Install one scheduled owner that runs the same next-step command. | Launchd definition and process argv read back the immutable release. |
| C02 | Run the next natural wake after release. | Submit and release both report `duplicate_effect=0`. |
| D01 | Read official sales and payout state. | Provider receipt records actual revenue or zero. |
| D02 | Change exactly one creative decision and start the next set. | Next-set plan names the evidence, hypothesis, and one changed variable. |
