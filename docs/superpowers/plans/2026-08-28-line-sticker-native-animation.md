# LINE Sticker Native Animation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce batch 1 as ten distinct, validator-clean animated sticker candidates without an external paid provider.

**Architecture:** One stdlib Python command implements the existing quote/generate/reconcile JSON protocol and delegates rendering to installed FFmpeg. It transforms the hashed green-screen character as a whole; it creates candidates but makes no semantic or marketability judgment.

**Tech Stack:** Python standard library, FFmpeg, existing `line_sticker_media.py` conversion and validators.

## Global Constraints

- Ponytail `full`: one provider file, one focused test file, no dependency or framework.
- Quote cost is exactly `0`; no external service, credential, network, or account state.
- Ten source segments are exactly 1000 ms and retain a solid `#00FF00` background.
- Provider/model/request/character/plan/video hashes must match across quote, generation, reconciliation, and candidate receipts.
- `regenerable` is `false`; the ten-second source remains durable.
- Transform generation never scores, labels, or selects creative quality.

---

### Task 1: Native FFmpeg provider and real batch 1

**Files:**
- Create: `skills/earn/line-sticker/native_animation.py`
- Create: `skills/earn/line-sticker/tests/test_native_animation.py`
- Modify: `docs/superpowers/specs/2026-08-28-line-sticker-loop-design.md`

**Interfaces:**
- Consumes: the existing stdin requests emitted by `line_sticker_media.convert()` for `quote`, `generate`, and `reconcile`.
- Produces: the exact provider dictionaries accepted by `_quote()`, `_generation()`, and `reconcile()`, plus `native-source-batch-<N>.mp4`.

- [ ] **Step 1: Write the failing subprocess contract test**

Create a generated 512×512 green PNG fixture. Assert that `quote` returns provider `native-ffmpeg`, model `whole-character-transforms-v1`, cost `0`, deterministic request identity, and no source file. Assert that `generate` rejects a changed character hash and otherwise returns ten ordered one-second segments, a matching video hash, `actual_cost_usd: "0"`, and `regenerable: false`. Assert that the ten segment frame hashes are not all equal. Assert that `reconcile` returns `completed` only when the deterministic source and sidecar receipt hashes match, otherwise `absent`.

- [ ] **Step 2: Run RED**

Run: `cd skills/earn/line-sticker/tests && python3 -m unittest test_native_animation`

Expected: FAIL because `native_animation.py` does not exist.

- [ ] **Step 3: Implement the minimum provider**

Use SHA-256 canonical JSON for request identity. On generate, validate exact batch motion ids, positions, 1000 ms durations, character file hash, and zero-or-greater remaining cap. Render ten one-second H.264 segments from the character with ten fixed whole-image translation/rotation rhythms, concatenate them losslessly into one ten-second MP4, hash it, and atomically save a sidecar receipt. Never branch on intent/action text. Reconcile only the deterministic local source plus sidecar hashes.

- [ ] **Step 4: Run GREEN and regression**

Run: `cd skills/earn/line-sticker/tests && python3 -m unittest test_native_animation test_line_sticker_media`

Expected: all tests PASS. Then run the real provider through `line_sticker_media.py convert --batch 1 --max-cost-usd 0` and require ten candidate JSON records with empty `validation_errors` and ten distinct candidate SHA-256 values.

- [ ] **Step 5: Fresh review, spec receipt, commit, and push**

Fresh read-only review must report no Critical or Important finding. Update A06 only after all ten exact APNGs pass the existing LINE validator. Commit production, tests, plan, and spec; push `feat/line-sticker-loop`.
