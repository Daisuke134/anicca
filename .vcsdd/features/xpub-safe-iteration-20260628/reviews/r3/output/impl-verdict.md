# Impl verdict — round 3 (lean mode final)

## Overall: PASS

## R2-fix verification

- **R2-FIX-1 URL guard: VERIFIED** — `replace_image_in_draft.py:82-83` runs the
  URL-prefix guard (`if not args.draft_url.startswith("https://x.com/compose/articles/edit/"): sys.exit(...)`)
  BEFORE `src.exists()` at `replace_image_in_draft.py:86-87`. Test
  `e4_replace.sh:15-16` now creates an existing fixture (`mktemp -t e4src.XXXXXX.jpg`
  with a JFIF magic header) and `e4_replace.sh:26` greps for the EXACT
  load-bearing string `refusing to operate on non-draft URL` (no longer
  matches a generic "missing"). If the URL guard line were deleted from
  source, this test would fail (the script would proceed to CDP-attach and
  error elsewhere with a different message). Load-bearing.

- **R2-FIX-2 delete_image_block return: VERIFIED** —
  `replace_image_in_draft.py:136-142` calls `if not delete_image_block(...):`
  and on False writes a `01-delete-FAILED.png` screenshot then `sys.exit(...)`
  with `aborting without paste so no duplicate is created` — paste path is
  unreachable on delete failure.
  `publish_md_to_x.py:492` captures `delete_ok = delete_image_block(page, img_index=-1)`
  and at `publish_md_to_x.py:493-501` `if not delete_ok:` logs the WARN and
  `return True` (= leave wrongly-placed image in place, do NOT proceed to
  paste retry → no duplicate). Matches the adversary-r2 recommendation
  verbatim. `verify-all.sh:50-56` adds load-bearing greps for both check
  sites.

- **R2-FIX-3 C7 lessons: VERIFIED** — `ai-entity-article-writer/SKILL.md:512`
  appends a new `## MORE LESSONS — xpub safe-iteration & EXIF (2026-06-28)`
  section (heading text differs slightly from spec wording but is the C7
  delivery). Lessons 45-50 (= 6 items) cover all six required concepts:
  #45 EXIF pre-check (lines 518-525), #46 consecutive-images-transition
  (526-532), #47 iteration discipline / re-publish destroys draft (533-538),
  #48 EN em-dash gate (539-542), #49 wheel-scroll-as-verify (543-548),
  #50 EN récit translation rules (549-554). Heading count: baseline 33 →
  current 35 (E5 grew-by check satisfied; pre-existing 2026-06-27 Corgi
  heading at line 429 preserved).

## Per-dimension

- **Spec Fidelity: PASS** — Every C-item in `spec/spec.md:36-48` is delivered:
  C1 EXIF transpose at `copy_to_clipboard.py:45` + EXIF strip at
  `copy_to_clipboard.py:54-57`; C1 raw-bytes path via `load_exif_corrected_bytes`
  at `copy_to_clipboard.py:60-80`; C1.5 PNG-through-PIL via `ext == '.png'`
  branch at `copy_to_clipboard.py:74-75` and macOS routing at
  `copy_to_clipboard.py:91-94`; C1.6 `--dry-write` at
  `copy_to_clipboard.py:260-264, 279-286`; C2 collision detector at
  `parse_markdown.py:352-373` (returns `consecutive_anchor_collision`
  array + stderr WARN); C3 flag at `publish_md_to_x.py:606-609` gated at
  `publish_md_to_x.py:656`; C4 WARN→delete at `publish_md_to_x.py:486-508`;
  C5 entire `replace_image_in_draft.py` (208 lines, no publish path);
  C6 shared `delete_image_block` at `_xpub_browser.py:21-69`; C7 in
  `ai-entity-article-writer/SKILL.md:512-554` (6 lessons); C8 in
  `x-article-publisher/SKILL.md:618-668` (6 lessons #13-18); C9 URL guard
  at `replace_image_in_draft.py:82-83`.

- **Edge Cases: PASS** — EXIF orientations 6, 3, 8 all covered by
  `e1_exif.py:95` (`for tag in (6, 3, 8)`) on BOTH `compress_image` path
  (`assert_dry_write`, `e1_exif.py:101`) AND `load_exif_corrected_bytes`
  path (`assert_dry_write_no_quality`, `e1_exif.py:104`). Whitespace-only
  anchors skipped at `parse_markdown.py:355-357`. URL guard
  prefix-startswith rejects `https://example.com/abc`, `https://x.com/i/articles/...`,
  and any non-`compose/articles/edit/` variant. `--no-cleanup-empties` and
  `--no-cleanup-duplicates` operate independently at `publish_md_to_x.py:652-657`.
  Delete-failure both callers HARD-fail (no silent duplicate).

- **Impl Correctness: PASS** — Control flow read end-to-end:
  `replace_image_in_draft.py:82` URL guard before any disk/network side-effect;
  `replace_image_in_draft.py:136-142` delete-fail aborts before paste;
  `publish_md_to_x.py:492-501` delete-fail aborts retry, returns True
  (image still present, just wrong spot — non-destructive); FAIL-retry at
  `publish_md_to_x.py:510-592` recomputes coords via `page.evaluate` →
  `Range.getClientRects()` at line 521-541 (= FM-1 fix preserved). No
  `Publish|publish_button|click_publish` token in either script (grep clean).
  `e2_consec.py` exercises both positive and negative cases — non-consecutive
  images do NOT trigger WARN; consecutive images DO. `--quality 0`
  falsy-check at `copy_to_clipboard.py:91, 280` accepted as risk
  (JPEG quality 0 is non-sensical input that would error in compress_image
  anyway).

- **Structural Integrity: PASS** — Engine remains DRAFT-only:
  `publish_md_to_x.py:56` comment + `replace_image_in_draft.py:34` `--publish`
  flag absent + zero grep hits for publish-button tokens. URL guard at
  `replace_image_in_draft.py:82` fires BEFORE `sync_playwright()` at line 92.
  Shared `delete_image_block` primitive (`_xpub_browser.py:21`) used by both
  call sites — no divergent re-implementation. C5's "NEVER touches non-target
  blocks" invariant now enforced via early `sys.exit` on delete failure.
  HARD 0.31 deferred-live-render is explicitly documented at
  `verify-arch.md:79-81` ("DEFERRED to next real article run, Dais said no X
  publish in this session"); honored.

- **Verification Readiness: PASS** — Every row of the spec v2 "Behavioral
  contract" table at `spec.md:60-77` is covered by a load-bearing test:
  every L1 grep in `verify-all.sh:10-61` targets a real symbol/string in
  the source (not a comment); every L2 E2E reads back a real artifact and
  asserts non-tautologically. The two adversary-r2 holes are closed:
  (a) `e4_replace.sh` URL-guard grep is now string-exact and uses an
  existing src file → URL guard line cannot be deleted without test failure;
  (b) `e1_exif.py` exercises BOTH JPEG pipeline branches. FM-1 regression
  grep added at `verify-all.sh:59-61` (`RETRY re-targeted @` is logged only
  inside the recompute branch at `publish_md_to_x.py:543`). C7-specific
  content not asserted by E5 (only heading-count growth + 2026-06-27
  preserved) — accepted because the lesson body was independently read and
  verified above (R2-FIX-3 line-cite chain).

## Residual must-fix (if any, in priority order; max 3)

None blocking. All r2 top-3 are landed and load-bearing.

## Notes

- `replace_image_in_draft.py:148-150` has a residual defensive WARN+continue
  when `delete_image_block` returned True but the caller's own
  post-count check disagrees. In practice unreachable because
  `_xpub_browser.py:67` returns True only when `after < before`, but the
  caller re-reads the count separately. Could be hardened to `sys.exit`
  for full consistency with the r2 fix, but not load-bearing since the
  primary delete-fail path already aborts at line 136-142. Accepted risk.
- `_xpub_browser.py:42` still runs `img.scrollIntoView({block: 'center'})`
  synchronously with the following `getBoundingClientRect()`. The 400ms
  `time.sleep(0.4)` at `_xpub_browser.py:52` between the move and the
  ✕-click partially mitigates, but on slow pages the scroll could still
  be in-flight when the rect is read. Accepted risk for lean-mode round-3
  (would benefit from `await new Promise(r => requestAnimationFrame(r))`
  inside the evaluate, or a re-read of the rect after `time.sleep`). Not
  blocking.
- PNG + `--quality` interaction: `publish_md_to_x.py:91-95` always passes
  `--quality 85`, which routes through `compress_image` (always emits JPEG
  bytes) → pasteboard at `copy_to_clipboard.py:105-106` labels them as
  `NSPasteboardTypePNG` based on file extension. JPEG bytes labeled as PNG
  is a pre-existing pasteboard-quirk bug NOT introduced by this round; spec
  v2 explicitly leaves it out of scope. Flag for a follow-up feature.
- E5 (`e5_skills.sh:10-15`) only asserts total `^## ` count grew + one prior
  heading preserved; it does NOT grep the C7-specific new-heading string
  or the lesson numbers. The verbatim heading from spec C7 wording
  (`MORE LESSONS — Corgi EN safe-iteration (2026-06-28)`) is NOT what
  shipped (actual heading: `MORE LESSONS — xpub safe-iteration & EXIF
  (2026-06-28)`). Acceptable because the C7 INTENT (= 6 lesson concepts
  appended) is delivered verbatim and the contract row at `spec.md:76`
  describes the test as "≥10 lines AND existing lesson headings
  preserved" (= what E5 actually does). Strengthening E5 to grep for
  the specific 2026-06-28 heading string and lesson numbers 45-50 would
  make the test load-bearing on the C7 delivery itself; defer.
- Heading-count baselines (`baseline-ai-entity-headings.txt = 33`,
  `baseline-xpub-headings.txt = 22`) vs current (`35`, `23`) confirm E5
  grew-by-1+ assertion is satisfied.
- Live-render browser verify (HARD 0.37's second gate) remains DEFERRED
  per spec out-of-scope. The NEXT real publish run is the gate that
  proves the WARN→delete-retry and EXIF rotation hold end-to-end against
  the live X Articles editor. Builder should treat the next live run as
  the final convergence proof for FM-3, FM-4, FM-5.
