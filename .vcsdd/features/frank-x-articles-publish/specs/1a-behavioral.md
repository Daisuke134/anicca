# Phase 1a — Behavioral Spec: Frank Article → X Articles Draft

**Feature**: frank-x-articles-publish
**Date**: 2026-06-28
**Mode**: lean (product work)
**Builder**: me (main agent)
**Adversary**: vcsdd:vcsdd-adversary (fresh-context subagent)

## Goal

Publish the Franklin article (already live on note as
`https://note.com/anicca123/n/n3ea4c7789e90`) to X Articles as a **DRAFT**
(NEVER publish — Dais clicks Publish himself).

## Source

The published note body (= the live Dais-edited version) is the canonical
source. Save it as Markdown to disk and feed that file to
`publish_md_to_x.py`. The article markdown in
`docs/articles/2026-06-15-frank-jp.md` may have older content; pull from
the API to guarantee parity with the live note article.

## Contract (in / out / edge / error / invariants)

### Inputs

- `source.md` — the Franklin article markdown (pulled from note API, body
  + 出典 final block + title)
- `cover.png` — the eyecatch we generated (`thumb.png` at
  `~/.cloak/note-work/franklin-blockrun-assets/thumb.png`); used as the
  first image in the rendered markdown so `publish_md_to_x.py` picks it up
  as cover
- All inline images already on note's CDN (`assets.st-note.com/...`) — the
  publisher must DOWNLOAD them to local paths so X can ingest them, or the
  markdown must reference local copies. Pull them locally before publish.
- CDP endpoint `http://localhost:9222` (daily-driver, already logged in to
  X Premium Plus).

### Outputs

- `draft-url.txt` containing the X Articles draft URL
  (`https://x.com/compose/articles/edit/<id>` form)
- `article.json` from `parse_markdown.py` output
- `article.html` for clipboard paste
- `screenshots/{01,01b,02,03,04,05,06,08}-*.png` from the publisher run (publisher script skips index 07 intentionally)
- `screenshots/08-final-overview.png` (= the publisher's final overview shot) PLUS supplementary wheel-NN screenshots in `evidence/` for full-article verify
- `impl/publish_log.txt` — captured stdout/stderr of the publisher run

### Edge cases

1. **Daily-driver already has an X Articles draft open in another tab** —
   the script must reuse the daily-driver CDP and find a fresh tab.
2. **Cover image is the eyecatch** — must NOT be inserted again as a body
   image. (publish_md_to_x.py treats the first image as cover automatically.)
3. **note CDN images** — `assets.st-note.com/img/<hash>.png` URLs must be
   downloaded; X cannot fetch arbitrary external URLs from a clipboard
   paste.
4. **出典 final block** — H2 "出典" with flat unordered list of 7 URLs;
   must render as native X Articles list (no conversion).
4b. **H3 renders flat on X Articles** — X's editor visually treats h3 like a slightly heavier paragraph, not a clear section header. If a sub-section needs visual punch (e.g. [7] 今日入れてたほうが良い人 / もう少し待っていい人 / 今は見送るべき人), use bold-paragraph or h2; do not rely on h3 to read as a heading. (Platform constraint, not an impl bug.)
5. **Mermaid diagrams** — rendered as PNG already (we have them on
   `~/.cloak/note-work/franklin-stage-v6/fig{1,2,3}.png` via kroki); the
   markdown must reference local copies, not Mermaid source.
6. **Table — block [6] 壊れる場所** — Dais's published note already rendered
   it as PNG (image, not markdown); we keep that pattern.
7. **Markdown image-title syntax `![](path "title")`** — `parse_markdown.py`
   regex naively treats title quotes as part of the path, leading to
   `exists=False` and a silent skip. Strip the `" ... "` from every image
   syntax in source.md before publish_md_to_x.py.
8. **Inline citation-stripping leaves double-period `。。`** — when the
   source body contains `...ほとんどです。（出典: ...）。`, naively removing the
   parens yields `ほとんどです。。`. After citation-strip, collapse `。。+` → `。`
   and `、、+` → `、`.

### Error modes

- **CDP unreachable** → fail loud, do not retry forever.
- **x.com auth missing** → fail; tell Dais to log in.
- **A body image won't upload** → publisher logs WARN and continues; verification gate MUST detect this via post-run image-count probe and trigger manual paste fix (verified in R1/R2 via Playwright CDP). Long-term: patch publisher to support \`--strict\` mode that exits non-zero on any missing image.
- **Image lands in wrong block** (per `MORE LESSONS #15`) → POST-COND retry
  via `replace_image_in_draft.py` until correct or 3 fail.
- **publisher invokes the Publish button** → MUST NOT happen; the script
  is draft-only by construction.

### Invariants

- The script NEVER calls Publish (skill design).
- The cover image (first image in markdown) becomes the X Articles cover,
  not a body image.
- All inline images are local files (not remote URLs).
- After completion, every body image renders (no broken alt placeholders).
- The 出典 block renders as an h2 + list, not raw markdown.
- The title field has the article title (NOT the body content), per
  `pitfall #1` in the skill.

## Verification gate (NO-MOCK E2E)

Per skill "Verification gate (apply to every publish)":

1. `Read` every `screenshots/{01,01b,02,03,04,05,06,08}-*.png` saved by the publisher script (no 07 — publisher script intentionally skips that index).
2. Open the draft URL in the daily-driver via CDP, take ONE more full-page
   screenshot.
3. `Read` THAT screenshot.
4. Tick each of the 8 pitfall items in the skill (title in title field, all
   body images loaded, section order, no raw markdown markers, …). If any
   tick fails, fix and rerun. Do not claim done until every tick passes.

In addition (specific to this feature):

5. Compare top-of-draft to the live note article's top: title + cover image
   should match (rendered the same way).
6. Confirm the 出典 final block contains exactly 7 URLs as live links.

## Adversarial review checklist (for vcsdd:vcsdd-adversary)

The adversary should attack:
- Did the title land in the title field, or in the body?
- Did the cover image render as a cover, or as a body image (duplicate)?
- Are ALL body images rendered, in the correct sections (not stacked)?
- Are the 7 出典 URLs present + clickable?
- Are the 補足 1/2 footnotes intact?
- Are there any leftover markdown markers (`**`, `` ` ``)?
- Are there any inline `(出典: ...)` references that should have been
  stripped (per PLAYBOOK rule 26)?
- Is the draft URL valid (`https://x.com/compose/articles/edit/<id>`)?
- Did the script invoke Publish? (Hard fail if yes.)

## Done definition (4-D convergence)

- [ ] spec ✓ (this file)
- [ ] impl ✓ (publish_md_to_x.py invocation logged with stdout/stderr)
- [ ] verification ✓ (all 8 pitfalls + 6 invariants ticked)
- [ ] adversary ✓ (PASS verdict from vcsdd:vcsdd-adversary; round 2 after fixes applied)
