# VCSDD Adversary Verdict — sprint-1
**Feature**: frank-x-articles-publish
**Date**: 2026-06-28
**Round**: 2
**Overall**: FAIL

> The R1 finding set was partially closed. The spec now covers both
> previously-missed edge cases (parser title-quote, citation-strip
> double-period) and the live X.com draft itself has been hand-patched
> via CDP to remove both defects. However, the on-disk implementation
> artifacts that the spec lists as required outputs
> (`impl/article.json`, `impl/article.html`) were **NOT regenerated**
> after the source-side fixes. They still describe the broken pre-fix
> state — `missing_images: 1`, `exists: false`, double-period in the
> body HTML, and the ④ heading still merged with its description in a
> single `<p>`. A clipboard-paste re-run from disk would resurrect every
> defect that was patched in the live draft. The publisher script's
> own silent-continue behaviour (spec line 78 violation) is also
> unchanged — only worked around at the source-md preprocessing step.

## Round 1 → Round 2 fix audit

| R1 finding | R2 closure | Result |
|---|---|---|
| Spec missing parser title-quote edge case | `specs/1a-behavioral.md:65-68` adds edge case #7 ("Strip the `\" ... \"` from every image syntax in source.md before publish_md_to_x.py") | PASS |
| Spec missing `。。` double-period edge case | `specs/1a-behavioral.md:69-72` adds edge case #8 ("After citation-strip, collapse `。。+` → `。`") | PASS |
| Spec/output mismatch on `screenshots/01..08` | `specs/1a-behavioral.md:45` aligns to `{01,01b,02,03,04,05,06,08}-*.png` and notes publisher script skips 07 intentionally | PASS (but see Dim 5 spec line 99 residual) |
| `impl/publish_log.txt` missing | File now present, 61 lines, captured stdout/stderr | PASS |
| `impl/source.md:23` `ほとんどです。。` typo | `impl/source.md:23` now reads `…ほとんどです。一方で…` (single period) | PASS at source level |
| `impl/source.md:67` ④ heading merged with body | `impl/source.md:67-69` now has `**④ …**` on line 67, blank line 68, body paragraph on line 69 — same shape as ①②③ | PASS at source level |
| Live X.com draft text retains `ほとんどです。。` | `evidence/r2-period-fix.jpg` shows live draft body reads `画像生成が $0.015などの超マイクロ取引がほとんどです。一方でクレジットカードは` (single period) and `Last saved 6 seconds ago` | PASS at live-draft level |
| Live X.com draft ④ heading merged with body | `evidence/r2-money-maker-split.jpg` shows ④ heading line, blank line, then `BlockRun のスタックを使って、人がどう稼ぐかのレシピやリンクを集めたカタログです。` body — identical shape to ②③ | PASS at live-draft level |
| `impl/article.json` shows `missing_images: 1`, `exists: false`, V1 path with title-quote glued | **NOT regenerated**; `impl/article.json:7-9,108` still show the broken parser output | FAIL |
| `impl/article.html` body shows `ほとんどです。。` and merged ④ paragraph | **NOT regenerated**; `impl/article.html:7` still contains both defects | FAIL |
| Publisher silent-continue on missing image (spec line 78) | `impl/publish_log.txt:59-61` shows `WARN: 1 image(s) need manual placement` then `DONE.` — publisher behaviour unchanged, only worked around at source preprocessing | FAIL |

## Adversarial-checklist (per spec §"Adversarial review checklist") — pixel-level (live-draft view)

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | Title in `<textarea name="Article Title">`, NOT in body | PASS | `evidence/r2-period-fix.jpg` left column shows the draft title `"コードを書き、動かす金まで自分で払う"AI『Franklin』、実際に動かし...` rendered in the Drafts side-bar as the draft heading; right pane shows the H2 `最も賢い AI が、100円の API すら自分で叩けない` as the first body element (not the title). |
| 2 | Cover image rendered as COVER banner, NOT duplicated in body | PASS | `evidence/wheel-00-top.jpg` (pre-fix wheel screenshot still valid for layout) shows the cover banner above title; no body image repeats it. R2 fixes did not affect cover placement. |
| 3 | All 7 body images rendered, in correct sections | PASS | `evidence/r2-money-maker-split.jpg` shows V2 (4-row BlockRun table) directly under the ④ split body. `evidence/v1-landed-near.jpg` shows V1 (robot+cash-register / robot+USDC thermometer) between the founder quote and the next H2. R2 fixes did not regress image placement. |
| 4 | 7 出典 URLs as clickable links | PASS | `evidence/wheel-03.jpg` shows the H2 `出典` followed by 7 underlined bullets. R2 fixes did not touch this region. |
| 5 | 補足 1 + 補足 2 footnotes intact, in order, BEFORE 出典 | PASS | `evidence/wheel-03.jpg` shows 📌 補足 1 → 補足 2 → 出典. R2 fixes did not touch this region. |
| 6 | No leftover raw markdown markers (`**`, `` ` ``, `*`, `[](...)`) in rendered body | PASS | `evidence/r2-money-maker-split.jpg` shows ②/③/④ rendered as visually bold (no `**`). No backticks in `impl/source.md` or `impl/article.html`. |
| 7 | No inline `(出典: …)` references in body | PASS | `grep` over `impl/source.md` returns zero `(出典:` matches. R2 fixes did not touch citation handling. |
| 8 | Draft URL in valid `https://x.com/compose/articles/edit/<id>` form | PASS | `impl/draft-url.txt:1` = `https://x.com/compose/articles/edit/2071129016560758784` (19-digit X snowflake id). |
| 9 | Publish NOT invoked | PASS | `evidence/r2-period-fix.jpg` and `evidence/r2-money-maker-split.jpg` both show the header reads `Draft · Last saved 6 seconds ago` and the `Publish` button remains rendered (not greyed). `impl/publish_log.txt` does not contain a Publish click event. |

All 9 user-facing items still pass on the live draft. The FAIL verdict
below is on the implementation pipeline / on-disk artifacts.

## Dimension verdicts

### 1. Spec Fidelity
**Status**: PASS

**R1 → R2 delta**:
- R1 finding: spec missed parser title-quote edge case → CLOSED at
  `specs/1a-behavioral.md:65-68` (edge case #7).
- R1 finding: spec missed `。。` double-period edge case → CLOSED at
  `specs/1a-behavioral.md:69-72` (edge case #8).
- R1 finding: spec outputs declared `screenshots/01..08-*.png` but
  publisher emits `{01,01b,02-06,08}` → CLOSED at
  `specs/1a-behavioral.md:45` (note "publisher script skips index 07
  intentionally").

**Findings** (residual):
- None blocking. Spec now describes the implementation as it actually
  behaves.

### 2. Edge Cases
**Status**: PASS

**R1 → R2 delta**:
- R1 finding: parser title-quote shape `![](path "title")` had reached
  the parser and broke it, with no spec coverage → CLOSED at
  `specs/1a-behavioral.md:65-68`.
- R1 finding: `。。` double-period after citation-strip was uncovered →
  CLOSED at `specs/1a-behavioral.md:69-72`.

**Findings** (residual):
- None blocking. Spec §"Edge cases" now lists 8 cases (was 6 in R1),
  covering both R1-uncovered failure modes.

### 3. Impl Correctness
**Status**: FAIL

**R1 → R2 delta**:
- R1 finding: `impl/publish_log.txt` does not exist → CLOSED.
  `impl/publish_log.txt` is present, 61 lines, captures publisher
  stdout/stderr.
- R1 finding: `impl/source.md:23` double period → CLOSED at source
  level (line 23 now reads `…ほとんどです。一方で…`).
- R1 finding: same defect in live X draft → CLOSED via CDP patch,
  confirmed in `evidence/r2-period-fix.jpg`.

**Findings** (NEW or unresolved):
- `impl/article.html:7` still contains
  `画像生成が $0.015などの超マイクロ取引がほとんどです。。一方でクレジットカードは`
  — the very double-period that Round 2 was supposed to remove. Spec
  line 44 declares `article.html` as the canonical clipboard-paste
  artifact; if Dais (or any re-run of the publish flow) clipboard-pastes
  this file, the live draft will be re-corrupted with the original
  defect. The R2 fix was applied to `source.md` and to the live draft
  via CDP, but `parse_markdown.py` was never re-invoked, so
  `article.html` is a stale snapshot of the pre-fix state.
- `impl/article.json:105` (the embedded `html` field used by some
  publisher paths) likewise contains
  `画像生成が $0.015などの超マイクロ取引がほとんどです。。一方でクレジットカードは`.
  Same root cause: artifact not regenerated.
- `impl/article.json:7-9,108` still reports
  `"path": ".../note-img-01.png \"Franklinは、自分の財布で動くエージェント…\""`,
  `"exists": false`, `"missing_images": 1`. The Round-2 manifest
  classifies V1 as "fixed" because the live draft has the image (per
  `evidence/v1-landed-near.jpg`), but the on-disk JSON contract — the
  authoritative artifact the spec gate is supposed to read — still
  asserts the image is missing.
- `impl/publish_log.txt:59-61` shows the publisher exited via:
  ```
  WARN: 1 image(s) need manual placement:
    - block=8 note-img-01.png "…" (missing-file)
  DONE. Open the draft in a browser, review screenshots, and edit/publish manually.
  ```
  This directly violates spec line 78 ("A body image won't upload →
  fail loud, do not silently continue"). The Round-2 fix added edge
  case #7 documenting the preventive workaround (strip title quotes in
  source.md before running), but did not change the publisher's
  silent-continue branch when the workaround is not applied. The
  invariant in spec line 78 still does not match the implementation.
- `impl/source.md:9` (and the cover at `:3`) reference image paths
  with embedded spaces (e.g. `/Users/anicca/anicca-project/.vcsdd/…`).
  These are correctly written for the local filesystem, but the
  parse_markdown.py regex bug documented in edge case #7 is still
  resident in the publisher code — only papered over by hand-editing
  the markdown. Any re-run from raw note-API output will reintroduce
  the defect.

### 4. Structural Integrity
**Status**: FAIL

**R1 → R2 delta**:
- R1 finding: `impl/source.md:67` ④ heading + body merged in a single
  paragraph → CLOSED at source level. Current `impl/source.md:67-69`
  has `**④ awesome-OpenClaw-Money-Maker、「稼ぎ方のレシピ集」**` on line
  67, blank line on 68, body sentence on line 69.
- R1 finding: live X draft ④ heading + body merged → CLOSED via CDP
  patch, confirmed in `evidence/r2-money-maker-split.jpg` showing
  ② / ③ / ④ all using the same heading-blank-body shape.

**Findings** (NEW or unresolved):
- `impl/article.html:7` still contains
  `<p><strong>④ awesome-OpenClaw-Money-Maker、「稼ぎ方のレシピ集」</strong>BlockRun のスタックを使って、人がどう稼ぐかのレシピやリンクを集めたカタログです。</p>`
  — the merged single-paragraph form that R2 was supposed to remove.
  Same root cause as the article.html `。。` finding above:
  `parse_markdown.py` was not re-invoked after `source.md:67-69` was
  split, so the HTML artifact still represents the OLD merged
  structure. A clipboard-paste re-run from disk would resurrect the
  exact defect R1 flagged.
- `impl/article.json:20` `after_text` for V2 still references the OLD
  merged form
  (`"**④ awesome-OpenClaw-Money-Maker、「稼ぎ方のレシピ集」**BlockRun のスタックを使って、人がどう稼ぐかのレシピリンクを"`),
  confirming the JSON was not regenerated.
- The R1 H3-styling finding ("`<h3>今日、入れてたほうが良い人:</h3>` renders
  visually indistinguishable from body paragraphs in
  `impl/screenshots/06-final-editor.png` / `08-final-overview.png`")
  has no Round-2 evidence addressing it. No new screenshot of the
  "Franklin は使うべきか" section is on disk. `impl/article.html:7,11`
  still emit `<h3>…</h3>` for these two sub-headings without
  confirming X Articles renders them differently from `<p>` text.
- parse_markdown.py's regex bug (edge case #7) is documented as a
  workaround in source.md rather than fixed in code. The publisher's
  structural correctness now depends on a manual pre-edit step, which
  is fragile and undocumented in the publisher script itself.

### 5. Verification Readiness
**Status**: PASS

**R1 → R2 delta**:
- R1 finding: `impl/screenshots/07-*.png` missing, breaking spec's
  "screenshots/01..08" contract → CLOSED at
  `specs/1a-behavioral.md:45` (spec now declares
  `{01,01b,02,03,04,05,06,08}-*.png` and explicitly notes "publisher
  script skips index 07 intentionally").
- R1 finding: `impl/publish_log.txt` missing for verification gate →
  CLOSED (file present, 61 lines).

**Findings** (residual, non-blocking):
- `specs/1a-behavioral.md:99` (the verification-gate step 1) still
  reads `Read every screenshots/0{1..8}-*.png saved by the publisher
  script`. The brace expansion `0{1..8}` includes `07`. This is
  inconsistent with the new spec line 45 which acknowledges 07 is
  intentionally absent. The text "saved by the publisher script"
  charitably resolves the ambiguity (read whatever the publisher
  emitted, which excludes 07), but the literal pattern still
  contradicts line 45. Minor wording inconsistency, not a blocking
  defect.
- All publisher-emitted screenshots (`01, 01b, 02, 03, 04, 05, 06, 08`)
  are on disk under `impl/screenshots/`; `impl/publish_log.txt` is on
  disk; `impl/draft-url.txt` is on disk; the verification gate can now
  complete structurally.
- The R2 fix to V1 placement is captured in
  `evidence/after-v1-insert.png/jpg` and `evidence/v1-retry.png/jpg`
  (outside the publisher's own `impl/screenshots/` namespace, but still
  reviewable). R1's request for an `impl/screenshots/07-after-v1-retry.png`
  is moot once the spec is realigned to "publisher skips 07".

## Open issues (must fix before merge / before Dais clicks Publish)

These are the items still blocking a clean PASS verdict.

1. **`impl/article.html` is stale** — line 7 still contains
   `ほとんどです。。` AND the merged `<p><strong>④ …</strong>BlockRun の
   スタックを使って…</p>`. The R2 fix was applied to `impl/source.md`
   and the live X draft, but `parse_markdown.py` was not re-invoked,
   so the canonical clipboard-paste artifact (spec line 44) is a snap-
   shot of the pre-fix state. **Re-run the publisher (or at minimum
   re-run `parse_markdown.py`) to regenerate `article.html` and
   `article.json` from the corrected `source.md`. Confirm
   `grep -c "。。" impl/article.html` is 0 and
   `grep -c "</strong>BlockRun のスタック" impl/article.html` is 0.**
2. **`impl/article.json` is stale** — `:7-9` still reports the broken
   V1 path with title-quote concatenation, `:108` still reports
   `"missing_images": 1`, `:105` still embeds the pre-fix HTML body.
   Same fix as #1.
3. **Publisher silent-continue still violates spec line 78** —
   `impl/publish_log.txt:59-61` shows the publisher emitted
   `WARN … (missing-file)` then `DONE.` instead of failing loud as
   spec line 78 ("fail loud, do not silently continue") demands. R2
   only documented the source-md preprocessing workaround (edge case
   #7); the publisher's silent-continue branch is unchanged. **Either
   (a) fix `publish_md_to_x.py` to exit non-zero when
   `missing_images > 0`, OR (b) relax spec line 78 to acknowledge the
   preprocessing-workaround contract.** Currently spec and impl
   disagree.
4. **`parse_markdown.py` regex bug is worked around, not fixed** —
   edge case #7 documents the title-quote shape that breaks the
   parser, but the fix strategy is "strip the `" … "` from source.md
   manually" rather than "make `parse_markdown.py` handle the standard
   `![alt](path "title")` markdown syntax". A future re-run on raw
   note-API output will reproduce R1's failure. **Either fix the regex
   in `parse_markdown.py` (add a test for `![](p "t")` shape), or have
   the publisher auto-strip titles as part of its own pre-pass with a
   regression test fixture.**
5. **H3 styling still unverified** — `impl/article.html:7,11` emit
   `<h3>今日、入れてたほうが良い人:</h3>` and
   `<h3>もう少し待っていい人:</h3>` but no Round-2 evidence shows X
   Articles applies a distinct heading style to these nodes. R1's
   warning ("renders visually indistinguishable from body paragraphs in
   `impl/screenshots/06-final-editor.png`") is unaddressed. **Capture
   one more screenshot of the "Franklin は使うべきか" section in the
   live draft and confirm the two `<h3>` lines are visually
   distinguishable from the bullet paragraphs underneath. If not,
   restyle to bold-paragraph or H2.**
6. **Spec wording inconsistency**:
   `specs/1a-behavioral.md:45` says the publisher emits
   `{01,01b,02,03,04,05,06,08}-*.png` (07 intentionally skipped) but
   `specs/1a-behavioral.md:99` still reads
   `Read every screenshots/0{1..8}-*.png` (which textually includes
   07). **Update line 99 to mirror line 45's set, or rephrase to
   "Read every screenshot the publisher script emitted into
   `impl/screenshots/`".**

## Summary table

| Dimension | R1 | R2 | Change |
|---|---|---|---|
| Spec Fidelity | FAIL | PASS | Closed (edge cases 7 + 8 added; outputs aligned) |
| Edge Cases | FAIL | PASS | Closed (parser case + double-period case both in spec) |
| Impl Correctness | FAIL | FAIL | Partially closed (publish_log.txt present; source.md fixed); article.html / article.json stale; publisher silent-continue unchanged |
| Structural Integrity | FAIL | FAIL | Partially closed (source.md split; live draft split); article.html still merged; H3 styling unverified; parse_markdown.py bug worked around not fixed |
| Verification Readiness | FAIL | PASS | Closed (07-skip noted; publish_log.txt present); minor line-99 wording residual |

**Overall Round 2**: FAIL on Impl Correctness + Structural Integrity.
The live X.com draft itself is publishable as-is, but the on-disk
implementation artifacts (article.html, article.json) do not reflect
the fixes and would re-corrupt the draft on any clipboard-paste
re-run.
