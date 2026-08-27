# LINE Sticker Package Validator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dependency-free validator that proves a 24-item LINE animated-sticker ZIP matches the current official technical contract before any browser effect can open.

**Architecture:** One versioned JSON file is the technical-policy SSOT. One Python CLI parses PNG/APNG chunks directly, verifies exact files and hashes, calls installed `ffmpeg` only to decode RGBA pixels for enclosed-alpha-hole detection, and emits one structured JSON result. Tests generate tiny APNG fixtures with `ffmpeg`; no network, login, upload, spend, or provider mutation occurs.

**Tech Stack:** Python 3 standard library, installed FFmpeg 8+, `unittest`, JSON, PNG/APNG chunk parsing, ZIP.

**Spec:** `docs/superpowers/specs/2026-08-28-line-sticker-loop-design.md`

## Global Constraints

- Official LINE pages are the policy source; the Hoko post is a creative heuristic only.
- Animated set count is exactly 24 for the first product.
- Main image is 240 x 240 APNG; tab image is 96 x 74 PNG; stickers are APNG within 320 x 270 and one dimension equals 270.
- APNG has 5–20 frames, 1–4 plays, total duration at most 4 seconds, transparent RGB/RGBA, and each file is below 1 MB; ZIP is below 60 MB.
- Unknown, malformed, stale-policy, missing-provenance, duplicate, and enclosed-alpha-hole inputs fail closed.
- No secret, credential, private browser state, network effect, or new dependency.

---

### Task 1: Validate an exact animated-sticker package

**Files:**
- Create: `skills/earn/line-sticker/official-policy.json`
- Create: `skills/earn/line-sticker/line_sticker.py`
- Create: `skills/earn/line-sticker/tests/test_line_sticker.py`

**Interfaces:**
- Consumes: a package directory containing `main.png`, `tab.png`, `01.png` through `24.png`, `provenance.json`, and `submission.zip`.
- Produces: `validate_package(root: Path, policy_path: Path, ffmpeg: str = "ffmpeg") -> dict[str, object]` and CLI JSON with `status`, `effect`, `readback`, `package_sha256`, `files`, and `errors`.
- Produces: `parse_png(path: Path) -> dict[str, object]` with `width`, `height`, `color_type`, `animated`, `frames`, `plays`, `duration_ms`, and chunk hashes.
- Exit code: `0` only for `status=ready`; `1` for a fully parsed invalid package; `2` for CLI/configuration errors.

- [ ] **Step 1: Write the official policy SSOT**

Create `official-policy.json` with exact keys and values:

```json
{
  "version": 1,
  "source_url": "https://creator.line.me/en/guideline/animationsticker/",
  "observed_at": "2026-08-28",
  "max_policy_age_days": 30,
  "sticker_count": 24,
  "main": {"width": 240, "height": 240, "animated": true},
  "tab": {"width": 96, "height": 74, "animated": false},
  "sticker": {"max_width": 320, "max_height": 270, "required_side": 270},
  "apng": {"min_frames": 5, "max_frames": 20, "min_plays": 1, "max_plays": 4, "max_duration_ms": 4000},
  "max_file_bytes": 1000000,
  "max_zip_bytes": 60000000,
  "required_color_types": [4, 6]
}
```

- [ ] **Step 2: Write failing tests for valid files and package identity**

Tests use a helper that writes PNG chunks with valid CRCs. It writes APNG `acTL` and `fcTL`
chunks with five frames at 200 ms and one play; IDAT pixel payload may be a one-pixel zlib stream
because the parser validates chunks, while the enclosed-alpha test injects a fake `ffmpeg` command.
Create tests asserting:

```python
result = MODULE.validate_package(package, POLICY, ffmpeg=str(fake_ffmpeg))
self.assertEqual(result["status"], "ready")
self.assertEqual(result["effect"], 0)
self.assertEqual(result["readback"], 0)
self.assertEqual(len(result["files"]), 26)
self.assertRegex(result["package_sha256"], r"^[0-9a-f]{64}$")
```

The provenance fixture must bind `set_id`, `character_id`, `rights="original_ai_generated"`,
provider names, prompt hashes, and SHA-256 for every submitted PNG. `submission.zip` contains only
`main.png`, `tab.png`, and `01.png`–`24.png`, with identical bytes.

- [ ] **Step 3: Run the focused tests and confirm RED**

Run:

```bash
python3 -m unittest skills/earn/line-sticker/tests/test_line_sticker.py -v
```

Expected: import/file failure because `line_sticker.py` does not exist.

- [ ] **Step 4: Implement strict PNG/APNG parsing and package validation**

Implement PNG signature and bounded chunk parsing with `struct`, `zlib.crc32`, and EOF checks.
Reject duplicate singleton chunks, invalid CRC, missing `IHDR`/`IEND`, invalid `acTL`, inconsistent
`fcTL` frame dimensions, zero delay denominator normalized to 100, nonpositive duration, trailing
bytes, and non-RGBA/gray-alpha color types. Calculate duration from frame delays and multiply by
plays; require the result at most `max_duration_ms`.

Implement exact package membership and canonical ZIP membership, content equality, SHA-256,
provenance completeness, duplicate submitted PNG hashes, policy freshness using UTC date, file/ZIP
sizes, main/tab dimensions and animation flags, sticker canvas constraints, APNG frame/play/duration,
and safe filenames. Sort all errors and file records so repeated runs are byte-stable.

For alpha-hole inspection, run:

```python
subprocess.run(
    [ffmpeg, "-v", "error", "-i", str(path), "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgba", "-"],
    check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
)
```

Flood-fill transparent pixels (`alpha == 0`) from canvas edges. Reject any remaining transparent
component unless its `(x, y)` seed is listed for that file in `provenance.json` under
`intentional_alpha_holes`. Reject decoded byte counts other than `width * height * 4`.

The CLI accepts:

```text
line_sticker.py validate --package PATH --policy PATH [--ffmpeg PATH]
```

It prints exactly one JSON object and never prints file bytes, prompt bodies, or environment values.

- [ ] **Step 5: Add fail-closed regression cases**

Add subtests that independently mutate one fact and assert the exact error code:

```text
policy_stale
package_membership_mismatch
zip_membership_mismatch
zip_content_mismatch:01.png
provenance_missing
provenance_hash_mismatch:01.png
duplicate_asset:01.png:02.png
png_crc_invalid:01.png
animation_required:01.png
frame_count_invalid:01.png
play_count_invalid:01.png
duration_invalid:01.png
dimensions_invalid:01.png
color_type_invalid:01.png
alpha_hole_unexpected:01.png
file_too_large:01.png
zip_too_large
```

Also run validation twice and assert identical output except no time-varying field exists.

- [ ] **Step 6: Run focused verification**

Run:

```bash
python3 -m unittest skills/earn/line-sticker/tests/test_line_sticker.py -v
python3 skills/earn/line-sticker/line_sticker.py validate \
  --package skills/earn/line-sticker/tests/fixtures/valid-package \
  --policy skills/earn/line-sticker/official-policy.json
git diff --check
```

Expected: all tests pass. If the committed suite generates fixtures only in a temporary directory,
replace the second command with the test helper's documented `--keep-fixture` command; do not commit
binary media fixtures.

- [ ] **Step 7: Commit only the validator slice**

```bash
git add skills/earn/line-sticker/official-policy.json \
  skills/earn/line-sticker/line_sticker.py \
  skills/earn/line-sticker/tests/test_line_sticker.py
git commit -m "feat(line-sticker): validate animated packages"
git push
```

## Self-review result

- Spec coverage: this slice closes deterministic package QA only; generation, model selection,
  state/effect fencing, browser submission, launchd/onboarding, production release, sales readback,
  and improvement remain explicit subsequent slices under the design spec.
- Placeholder scan: no deferred instruction appears inside Task 1; every implemented validator
  behavior and expected error code is named.
- Type consistency: `validate_package` and `parse_png` names and result keys are identical across
  interfaces, tests, implementation instructions, and CLI expectations.
