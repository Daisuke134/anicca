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
effect, be within the configured per-set cap, and be durably reserved by `set_id`. Unknown cost,
missing provenance, or disk below the media headroom floor fails before generation or submission.
No provider is retried after an acknowledged paid generation effect; it is reconciled first.

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

## Acceptance gates

Code-owned gate:

- clean fixture run creates one valid 24-item package and manifest;
- malformed dimensions, frame count, playback, file size, alpha hole, duplicate asset, missing
  provenance, stale policy, low disk, and unknown cost all fail closed;
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
