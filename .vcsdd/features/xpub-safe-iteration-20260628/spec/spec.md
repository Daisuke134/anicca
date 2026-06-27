# Behavioral spec — x-article-publisher safe-iteration hardening (v2)

## Why this feature exists

During the Corgi Cafe EN translation work (2026-06-28) the engine produced 4
rounds of broken drafts and one near-publishable draft that still required the
human (Dais) to manually delete 2 duplicate images before publishing. Round 1
adversary review surfaced gaps in failure-mode enumeration, edge cases, and
verification runnability — this v2 spec addresses every top-3 must-fix from
`reviews/r1/output/spec-verdict.md` (= the round-1 verdict file Dais can read).

## Exact retro failure modes (6, verbatim from the session log)

Each mode triggered a real defect; each gets a closing change item below.

| FM | When it fired | Symptom | Root cause | Closes with |
|---|---|---|---|---|
| FM-1 | R1 publish | 5 of 7 content images landed at end of document | `insert_content_image` retry re-clicked the same (x,y) that the first try used; the first try's paste shifted the DOM, so the retry's same-coord click hit a different paragraph | Already fixed in R2 patch (retry coords are now recomputed via `page.evaluate` + `Range.getClientRects`). KEEP and add regression grep. |
| FM-2 | R1 publish | Em-dashes in EN body ("Founders Fund — the Silicon Valley") | EN stop-slop banned-list not run pre-publish | C7 + C8 (writer-skill lesson + grep gate) |
| FM-3 | R2 publish | IMG_4925 ↔ IMG_4926 swap | Two consecutive `![]()` lines share the same after_text → engine pastes 2nd image at 1st's anchor → 2nd ends up BEFORE 1st | C2 (parse_markdown WARN) + writer-skill lesson |
| FM-4 | R3 publish | IMG_4930 landed inside the WiFi section | `POST-COND WARN` ("image inserted into wrong block") was logged then returned True; no retry, no delete | C4 (WARN-retry path) + C5/C6 shared ✕-overlay helper |
| FM-5 | All 4 rounds | IMG_4926 + IMG_4928 displayed 90° rotated | Source JPGs carry EXIF orientation=6; X Articles ignores EXIF; `copy_to_clipboard.py` raw-bytes path bypasses PIL entirely | C1 (EXIF auto-rotate in compress + new `load_exif_corrected_bytes`) + C1.5 (PNG path through PIL too) |
| FM-6 | After every re-publish | Lost work / Dais frustration ("all images lost") | Default `cleanup_exact_title_duplicates` deletes any existing same-title draft on re-run, taking manual fixes with it | C3 (--no-cleanup-duplicates flag) + C5 (separate targeted-replace entry point so iteration doesn't need re-publish) |

**Adversary r1 misread**: the verdict inferred a hypothetical "FM-7 cover-dup
(cover image = first body image, gets pasted twice)". That is NOT what
happened. The 2 duplicates Dais deleted were the **rotated originals** that
my `replace-rotated-images-v2.py` failed to delete (Backspace doesn't kill
Draft.js atomic blocks), plus the **corrected versions** I pasted in. Both
fixes are already covered: the FAILURE was Backspace → C5 (✕-overlay
primitive) closes it permanently. Cover-vs-body dedup is not in scope and
not justified by the retro.

## In-scope changes (= the C-items)

| # | File | Change | Closes FM |
|---|---|---|---|
| C1 | `~/.claude/skills/x-article-publisher/scripts/copy_to_clipboard.py` | (a) `compress_image()`: prepend `img = ImageOps.exif_transpose(img)` and strip EXIF on save. (b) NEW `load_exif_corrected_bytes()`: same path for raw (no-quality) bytes. (c) macOS branch's raw-bytes early-out now calls `load_exif_corrected_bytes()` (= no path uploads EXIF-rotated pixels). Verified PIL ≥ 9.0 (system already at 10.x). | FM-5 |
| C1.5 | `~/.claude/skills/x-article-publisher/scripts/copy_to_clipboard.py` | PNG branch (`copy_image_to_clipboard_macos` line ~76-78) also routes through PIL via a `load_exif_corrected_bytes` variant that emits PNG bytes. Even though PNG EXIF orientation is rare, it exists (e.g. iOS screenshots can carry it); same primitive must apply. | FM-5 (extended) |
| C1.6 | `~/.claude/skills/x-article-publisher/scripts/copy_to_clipboard.py` | NEW `--dry-write <PATH>` flag on the `image` subcommand: instead of pushing bytes to NSPasteboard, write the post-EXIF-transpose, EXIF-stripped JPEG bytes to `<PATH>`. Makes E1 NO-MOCK runnable. | testability for FM-5 |
| C2 | `~/.claude/skills/x-article-publisher/scripts/parse_markdown.py` | After building `content_images`, scan for consecutive images sharing `after_text`. Emit stderr WARN + add `consecutive_anchor_collision: [{block_index, conflicts_with, after_text}]` to JSON. ≥3-consecutive case folds into N-1 pairwise entries (documented limitation; transitive grouping out of scope). Whitespace-only anchors are SKIPPED (not flagged). Truncation note: the detector uses the same 80-char-truncated `after_text` that downstream uses → matches downstream reality. | FM-3 |
| C3 | `~/.claude/skills/x-article-publisher/scripts/publish_md_to_x.py` | NEW `--no-cleanup-duplicates` flag (separate from existing `--no-cleanup-empties`). Defined interaction: each flag toggles its respective cleanup INDEPENDENTLY. Existing behavior unchanged when neither flag set. Both flags can be combined. Log line emitted both when cleanup runs AND when skipped (so a verifier sees the decision). | FM-6 |
| C4 | `~/.claude/skills/x-article-publisher/scripts/publish_md_to_x.py` | When `POST-COND WARN` (image inserted into wrong block), call shared helper `delete_image_block(page, img_index=-1)` to remove the wrongly-placed image, refresh `imgs_before`, fall through into the existing FAIL-retry path. | FM-4 |
| C5 | NEW `~/.claude/skills/x-article-publisher/scripts/replace_image_in_draft.py` | Args: `--draft-url <U>`, `--index N`, `--src PATH`, `--anchor "text"`, `--cdp`. Process: locate by index → `delete_image_block(page, N)` → anchor-locate → paste via `copy_to_clipboard.py image --quality 90` (= now EXIF-corrected). NEVER calls cleanup. NEVER touches non-target blocks. | iteration UX gap surfaced by FM-6 |
| C6 | NEW `~/.claude/skills/x-article-publisher/scripts/_xpub_browser.py` (or inline) | Shared helper `delete_image_block(page, img_index: int) -> bool`. Locator: `document.querySelectorAll('div[data-testid="composer"] img')[index]` (negative index allowed). Coord computation: `rect.right - 18, rect.top + 18` (= top-right ✕ overlay). Confirm dialog: click `Delete`/`Remove`/`削除` button if surfaced. Post-condition: composer-img count decreased by 1; returns True. Inline-shared between C4 and C5. | shared primitive (eliminates divergent impls) |
| C7 | `~/.claude/skills/ai-entity-article-writer/SKILL.md` | Append "MORE LESSONS — Corgi EN safe-iteration (2026-06-28)" section with lessons #41-46 covering EXIF pre-check, consecutive-images-transition rule, iteration discipline (= don't re-publish for tiny fixes), EN em-dash gate, wheel-scroll-as-verify rule, EN récit translation rules. | FM-2, FM-3, FM-6, lesson capture |
| C8 | `~/.claude/skills/x-article-publisher/SKILL.md` | Append "MORE LESSONS — safe-iteration & rotation (2026-06-28)" section with engine gaps #13-18 covering each of the changes above. | engine lesson capture |
| C9 | `~/.claude/skills/x-article-publisher/scripts/replace_image_in_draft.py` | RUNTIME GUARD: refuse `--draft-url` that doesn't start with `https://x.com/compose/articles/edit/` (= prevents stray edits on the live `/i/articles/...` URL or on a non-Anicca URL). HARD-coded reject of Dais's published article id `2070819168853622784` is excessive (= depends on memory); the URL-prefix check is sufficient. | structural safety |

## Out-of-scope (explicit decisions)

- ICC profile preservation on JPEG re-save (adversary noted). Out of scope: phone-photo color shift is invisible for body content; can revisit if Dais reports.
- `after_text` truncation to 80 chars: detector uses the SAME truncated value as downstream insert logic, so detection matches reality. Extending the cap is a separate refactor.
- Cover-vs-body dedup (adversary's hypothetical FM): NOT a real failure mode from this session; the 2 duplicates Dais deleted came from Backspace-fails (FM-5 + C5 closes it).
- `--cleanup-mode` enum (adversary suggestion to replace two booleans): two booleans are fine when each toggles a distinct, named cleanup; refactor would touch the existing `--no-cleanup-empties` callers — defer.
- Live-fire WARN→retry article (adversary asked for one). Dais explicitly said "don't post to X" in this session. Live-fire fixture is OUT OF SCOPE. The NEXT real article will exercise the WARN→retry path; record-only for now.
- Engine remains DRAFT-only. Any change that opens a publish path = STOP and revert.

## Behavioral contract (= what Done means)

| Invariant | Verification (Layer; see verify-arch.md) |
|---|---|
| C1: `compress_image()` calls `ImageOps.exif_transpose(img)` before output | L1 grep |
| C1: JPEG output has no EXIF orientation tag | L2 E1 (round-trip via --dry-write fixture) |
| C1: dimensions transposed when source had orientation=6 (also 3 and 8) | L2 E1 |
| C1.5: PNG path routes through PIL (= no early raw-bytes return for PNG) | L1 grep on `copy_image_to_clipboard_macos` |
| C1.6: `--dry-write <PATH>` writes bytes and exits 0 without touching pasteboard | L2 E1 fixture exit code |
| C2: Two `![]()` lines sharing after_text → stderr WARN + non-empty `consecutive_anchor_collision` in JSON | L2 E2 (sample.md) |
| C2: NON-consecutive images (different after_text) do NOT trigger WARN | L2 E2 negative case |
| C3: `--no-cleanup-duplicates` flag listed in `--help` | L2 E3a |
| C3: `cleanup_exact_title_duplicates(page, title)` is gated by `if not args.no_cleanup_duplicates:` | L1 grep |
| C4: WARN-retry branch calls `delete_image_block` (or inline equivalent) before fall-through to FAIL-retry | L1 grep |
| C5: `replace_image_in_draft.py --help` exits 0, lists required args | L2 E4a |
| C5: refuses non-draft URL with exit > 0 and no browser side-effect | L2 E4b (`--draft-url https://example.com/foo` → exits 1) |
| C6: `delete_image_block(...)` is defined exactly once and referenced from both C4 and C5 sites | L1 grep |
| C7+C8: both SKILL.md files grow by ≥10 lines AND existing lesson headings preserved | L2 E5 (diff) |
| C9: URL guard rejects `https://example.com/abc` | L2 E4b |

## Risk boundaries

- No regression on initial-publish path for fresh-markdown / no-consecutive-anchor articles.
- All scripts remain `python3 <script> --help`-clean.
- Only PIL/ImageOps used (already a dependency).
- All file writes to local disk; no network; no X publish; no auth.

## Stop conditions

- Round 2 adversary returns FAIL on Spec Fidelity OR Verification Readiness → re-iterate (max round 3 in lean mode, then escalate).
- E2E layer hits unexpected exception → STOP, do NOT mark Done.
- Any new path that posts to X / publishes / submits → STOP, revert immediately.

## Paths (so adversary can grep)

- NEW script: `/Users/anicca/.claude/skills/x-article-publisher/scripts/replace_image_in_draft.py`
- Patched: `/Users/anicca/.claude/skills/x-article-publisher/scripts/copy_to_clipboard.py`
- Patched: `/Users/anicca/.claude/skills/x-article-publisher/scripts/parse_markdown.py`
- Patched: `/Users/anicca/.claude/skills/x-article-publisher/scripts/publish_md_to_x.py`
- Appended: `/Users/anicca/.claude/skills/x-article-publisher/SKILL.md`
- Appended: `/Users/anicca/.claude/skills/ai-entity-article-writer/SKILL.md`
- Tests: `/Users/anicca/anicca-project/.vcsdd/features/xpub-safe-iteration-20260628/tests/`
