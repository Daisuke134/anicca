# LINE Sticker Media Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn one original character reference plus model/provider command outputs into a validated, provenance-bound 24-item animated LINE sticker package.

**Architecture:** A model command makes the 60-motion plan and later selects/orders 24 candidates; deterministic Python validates those JSON contracts, invokes an animation provider command for six ten-motion videos, segments/chroma-keys/encodes each candidate with FFmpeg, assembles main/tab/ZIP/provenance, and calls the existing package validator. Creative judgment stays in the model; code owns effects, cost/disk bounds, media arithmetic, hashes, and receipts.

**Tech Stack:** Python 3 standard library, FFmpeg/FFprobe, existing `line_sticker.py`, JSON/JSONL, subprocess.

**Spec:** `docs/superpowers/specs/2026-08-28-line-sticker-loop-design.md`

## Global Constraints

- The first product has one original AI-generated character, text-free universal expressions, 60 candidates, six ten-motion source videos, and exactly 24 selected animated stickers.
- No keyword/regex/hand-score decides creativity, quality, usefulness, variety, or ordering; the configured model decides from full motion/media evidence.
- Deterministic code validates fixed schemas, timestamps, dimensions, costs, hashes, provider receipts, and official LINE package rules only.
- Every paid provider effect has one stable request id, quoted cost at or below the local per-set cap, acknowledged output hash, and no retry after unknown acknowledgement.
- Unknown cost, malformed model/provider output, missing provenance, provider mismatch, invalid candidate, or failed file write prevents the external effect and preserves the last durable checkpoint.
- Process one source video at a time and remove regenerable intermediates only after durable hashes/receipts; never delete selected outputs, provenance, state, or receipts.
- No network implementation, credential, browser mutation, launchd edit, hardcoded character copy, or income claim in this slice.

---

### Task 1: Plan, convert, select, and package 24 animations

**Files:**
- Modify: `skills/earn/line-sticker/line_sticker.py`
- Modify: `skills/earn/line-sticker/tests/test_line_sticker.py`
- Create: `skills/earn/line-sticker/creative-prompt.md`
- Create: `skills/earn/line-sticker/line_sticker_media.py`
- Create: `skills/earn/line-sticker/tests/test_line_sticker_media.py`

**Interfaces:**
- CLI `plan --character PATH --model-command JSON_ARGV --work-dir PATH --set-id ID --character-id ID`.
- CLI `convert --plan PATH --animation-command JSON_ARGV --work-dir PATH --max-cost-usd DECIMAL --ffmpeg PATH --ffprobe PATH`.
- CLI `reconcile --convert-state PATH --animation-command JSON_ARGV --batch N`.
- CLI `select --plan PATH --candidates PATH --model-command JSON_ARGV --work-dir PATH`.
- CLI `package --selection PATH --work-dir PATH --output PATH --policy PATH --ffmpeg PATH`.
- Every CLI prints one stable JSON object with `status`, `effect`, `readback`, `reason`, hashes, and output path only; no prompt body, credential, environment, or provider response body.
- There is no fixed disk threshold or capacity subsystem. Work is one source video at a time; atomic
  write failure keeps the prior checkpoint and the next wake retries the same item. Stage replay
  verifies every durable output/hash/receipt before returning effect zero.

- [ ] **Step 1: Write the right-altitude creative prompt**

Create `creative-prompt.md` with two explicit modes, `plan` and `select`. It tells the model:

- design text-free, large, legible motion for everyday global chat;
- keep the supplied character's visual anchors consistent;
- produce exactly 60 distinct candidates grouped into six coherent ten-motion videos;
- do not prematurely discard difficult ideas; generation failures are filtered later;
- in selection mode inspect every candidate path, validator result, first frame, timing, and motion preview;
- select exactly 24, put the strongest/high-frequency face first, front-load frequent reactions,
  separate visually similar motions, and explain each choice briefly;
- never invent provider success, rights, hashes, cost, or visual evidence it did not inspect.

Include three canonical examples showing good plan variety, rejection of a broken/ambiguous candidate,
and ordering that separates similar motions. Do not include keyword lists or category scores.

- [ ] **Step 2: Write RED contract tests and fake commands**

Tests create executable fake model/provider commands in `TemporaryDirectory`. The plan fake consumes
JSON on stdin and returns exactly 60 records:

```json
{
  "version": 1,
  "mode": "plan",
  "set_id": "set-1",
  "character_id": "char-1",
  "character_anchors": ["round blue ears", "white face", "short tail"],
  "motions": [{
    "motion_id": "motion-01",
    "batch": 1,
    "position": 1,
    "intent": "friendly acknowledgement",
    "action": "leans forward and gives one broad nod",
    "provider_prompt": "...",
    "duration_ms": 1200
  }]
}
```

The provider fake supports exact operations `quote`, `generate`, and `reconcile`. Quote returns
`request_id`, `quote_token`, `batch`, `provider`, `model`, `quoted_cost_usd`, `expires_at`, and
`regenerable` without creating media. Generate echoes that identity and returns acknowledgement,
video path/hash, and ten segments (`motion_id`, `start_ms`, `end_ms`). Tests first fail because
`line_sticker_media.py` is absent.

- [ ] **Step 3: Implement safe command and JSON contracts**

Parse command argv from a JSON array of nonempty strings; never use a shell. Send one bounded JSON
request on stdin, stream stdout/stderr with a hard 1 MiB cap while the process runs, start a process
group and terminate the whole group on cap/timeout, use a 10-minute timeout, require one
JSON object and exact schema/types/keys. Model plan must contain 60 unique ids, batches 1–6, positions
1–10 exactly once, exact ids `motion-01` through `motion-60`, duration 500–2000 ms, and 64-character hashes for the character bytes and prompt.
These are format/arithmetic checks, not creative judgment.

Write outputs atomically and content-address them. `plan` writes `plan.json` and `plan-receipt.json`.
Repeated identical invocation returns the existing receipt without calling the model again; conflicting
inputs fail closed.

- [ ] **Step 4: Implement provider effect fencing and one-video-at-a-time conversion**

Call side-effect-free `quote` first. It fixes provider, model, stable request id, quote token, Decimal
cost, expiry, and regenerable flag. Persist and fsync a reservation keyed by SHA-256 of set id, plan
hash, batch, provider, model, request id, quote token, and character hash. Verify cumulative reserved
cost is at or below `--max-cost-usd` before calling `generate`; send that same identity and remaining
cap to generate and require an exact echo.

Unknown acknowledgement writes `reconcile_unknown` and never calls `generate` again. CLI
`reconcile --convert-state PATH --animation-command JSON_ARGV --batch N` calls only provider operation
`reconcile` with the original request id. It accepts output only when all identities and hashes match.

Validate segments are ordered, nonoverlapping, within probed source duration, and bind the exact ten
motion ids. For each segment run FFmpeg without a shell:

```text
-ss START -t DURATION -i VIDEO
-vf chromakey=0x00FF00:0.12:0.08,fps=10,
    scale=320:270:force_original_aspect_ratio=decrease,
    pad=320:270:(ow-iw)/2:(oh-ih)/2:color=0x00000000
-plays 1 -f apng OUTPUT.png
```

Keep between 5 and 20 frames by choosing a bounded fps from duration, never by dropping the final
motion phase. Call existing `parse_png` and alpha checks for every candidate. Persist candidate SHA,
source SHA, segment, conversion argv hash, and validation errors. Remove a source video only when all
ten candidate records are durable and valid and quote/generation explicitly marked it regenerable.
Any invalid candidate retains the source.

- [ ] **Step 5: Implement model visual selection and ordering**

Build `selection-input.json` containing the 60 candidate paths, hashes, parsed APNG facts, errors,
first-frame PNG paths, contact-sheet path, motion-preview paths, and motion-plan text. Call the model
in `select` mode. Require a readback listing all 60 inspected hashes and exactly 24 unique
existing valid motion ids, exact positions 1–24, one declared cover id equal to position 1, and a
nonempty natural-language reason for each. Do not calculate or override a creative score.

Repeated identical selection input returns the existing selection receipt. A changed candidate hash
invalidates selection and requires a fresh model call.

- [ ] **Step 6: Assemble the exact official package**

Copy selected APNG bytes as `01.png`–`24.png`. Create `main.png` from the cover APNG with a transparent
240×240 canvas while preserving animation. Extract the cover first frame and create a transparent
96×74 `tab.png`. Extend the core validator's exact provenance schema with a package-bound
`generation` object. It contains original-character rights evidence, model/provider names, prompt,
character, plan and selection hashes, reserved/actual costs, quote/generation request ids, source,
segment and candidate hashes, conversion argv hashes, and exact asset hashes. Missing receipts or
rights evidence fails; no fallback provider/rights string and no sidecar ledger substitutes for it.
Create deterministic `submission.zip` containing only the 26 PNGs with fixed metadata.

Run existing `validate_package`; promote to the output directory only when `status=ready`. Promotion is
same-filesystem atomic rename and refuses an existing conflicting package. Emit raw artifact and canonical
package digests returned by the validator.

- [ ] **Step 7: Add fail-closed and replay regressions**

Cover malformed/extra model keys, 59/61/duplicate/unsafe motions, duplicate batch positions, invalid durations,
shell-like argv values remaining literal, command timeout/output overflow, quote over cap, NaN/boolean
cost, quote-before-generate call order, provider/model/request mismatch, provider unknown acknowledgement,
reconcile without generate retry, changed request/video hash, overlapping/out-of-range
segments, wrong source SHA, invalid chroma/opaque/alpha-hole candidate, 23/25/duplicate selection, selection
of invalid candidate, changed candidate after selection, identical output replay, output conflict, forced
atomic write failure with same-item resume,
source retention/deletion, package-bound provenance tamper, and stage-specific replay call counts.

Generate one real six-batch FFmpeg fixture with simple distinct green-screen motions and prove the resulting
24 package passes the existing validator. Keep fixtures temporary and bounded.

- [ ] **Step 8: Run verification and commit**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest skills/earn/line-sticker/tests/test_line_sticker_media.py -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest skills/earn/line-sticker/tests/test_line_sticker.py -v
git diff --check
git status --short
```

Expected: all media tests and existing validator/owner tests pass; only the five owned files change.

```bash
git add skills/earn/line-sticker/creative-prompt.md \
  skills/earn/line-sticker/line_sticker_media.py \
  skills/earn/line-sticker/tests/test_line_sticker_media.py \
  skills/earn/line-sticker/line_sticker.py \
  skills/earn/line-sticker/tests/test_line_sticker.py
git commit -m "feat(line-sticker): build animated media packages"
git push
```

## Self-review result

- Spec coverage: this slice closes model plan/selection contracts, provider receipts/cost fence,
  deterministic video→APNG conversion, package/provenance assembly, and replay. Real image/video provider
  network adapters, Creators Market browser, launchd/onboarding, and production publication remain later.
- Placeholder scan: every JSON shape, count, effect fence, conversion, selection, package, and command is explicit.
- Type consistency: set/character/motion/batch/request ids and artifact/package hashes are stable across all stages.
