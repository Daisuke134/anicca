# Verification architecture (v2)

Addresses round-1 adversary findings: E1 now has a real `--dry-write` path,
E4 has a destructive-safety check, fixtures are enumerated below, all greps
load-bearing.

## Layers

### Layer 1 — Source grep (= static guards)

Each grep MUST return ≥1 hit and target a load-bearing line (= not a free-form
comment). Listed with the exact `grep` command:

- `grep -nE "ImageOps.exif_transpose\(img\)" ~/.claude/skills/x-article-publisher/scripts/copy_to_clipboard.py` → ≥1
- `grep -nE "def load_exif_corrected_bytes" ~/.claude/skills/x-article-publisher/scripts/copy_to_clipboard.py` → ≥1
- `grep -nE "--dry-write" ~/.claude/skills/x-article-publisher/scripts/copy_to_clipboard.py` → ≥1
- `grep -nE "consecutive_anchor_collision" ~/.claude/skills/x-article-publisher/scripts/parse_markdown.py` → ≥2 (build + key)
- `grep -nE "if not args\.no_cleanup_duplicates:" ~/.claude/skills/x-article-publisher/scripts/publish_md_to_x.py` → ≥1 (load-bearing gate)
- `grep -nE "POST-COND WARN.*DELETING via" ~/.claude/skills/x-article-publisher/scripts/publish_md_to_x.py` → ≥1 (proves WARN→delete branch exists, not just a comment)
- `python3 -m py_compile ~/.claude/skills/x-article-publisher/scripts/replace_image_in_draft.py` → exit 0
- `grep -nE "compose/articles/edit/" ~/.claude/skills/x-article-publisher/scripts/replace_image_in_draft.py` → ≥1 (URL guard)
- `grep -nc "^## " ~/.claude/skills/ai-entity-article-writer/SKILL.md` returns value > the recorded baseline `tests/baseline-ai-entity-headings.txt` (= new section appended)
- `grep -nc "^## " ~/.claude/skills/x-article-publisher/SKILL.md` returns value > the recorded baseline `tests/baseline-xpub-headings.txt`

### Layer 2 — NO-MOCK E2E (= run real scripts, real inputs, no X publish)

All fixtures live in `tests/` and are committed alongside the verify script:

- **E1 EXIF auto-rotate** — `tests/e1_exif.py`:
  - Build 3 JPGs in `/tmp` with PIL: a 300×400 image saved with EXIF orientation tags 6, 3, 8 respectively.
  - For each, run `python3 copy_to_clipboard.py image <jpg> --quality 90 --dry-write <out.jpg>`.
  - Open `<out.jpg>` → assert EXIF orientation tag is None (stripped) AND dimensions match the transposed shape (orientation=6 → 400×300; orientation=3 → 300×400 i.e. preserved-then-rotated-180; orientation=8 → 400×300).
  - Exit 0 only if all 3 pass.
- **E2 consec-anchor detection** — `tests/e2_consec.py`:
  - Positive: write `tests/sample-consec.md` with the literal payload `# T\n\n## H\n\nintro\n\n![a](a.jpg)\n\n![b](b.jpg)\n`; run `python3 parse_markdown.py tests/sample-consec.md`; assert stderr matches `/consecutive images at blocks/i` AND JSON `consecutive_anchor_collision` is non-empty.
  - Negative: write `tests/sample-spaced.md` with each image separated by a unique text paragraph; assert `consecutive_anchor_collision` IS empty AND no consecutive-WARN on stderr.
  - Exit 0 only if both pass.
- **E3 --no-cleanup-duplicates flag exists** — `tests/e3_flag.sh`:
  - `python3 publish_md_to_x.py --help 2>&1 | grep -F -- --no-cleanup-duplicates` → exit 0
- **E4 replace_image_in_draft entry-point + URL guard** — `tests/e4_replace.sh`:
  - `python3 replace_image_in_draft.py --help` → exit 0
  - `python3 replace_image_in_draft.py --draft-url https://example.com/abc --index 0 --src /tmp/none.jpg --anchor x` → exit code != 0 (= URL guard rejects)
  - No CDP connection attempted in the second case (= proven by absence of `playwright` import error → guard fires before sync_playwright).
- **E5 SKILL.md appends** — `tests/e5_skills.sh`:
  - For each SKILL.md, count `^## ` lines BEFORE this round (= `tests/baseline-*-headings.txt`) and assert AFTER count > BEFORE.
  - Assert previous lesson headings still present (= a fixed sample heading like `## MORE LESSONS — Corgi Cafe ground-truth pass (2026-06-27)` for x-article-publisher and `## MORE LESSONS (2026-06-22)` for ai-entity-article-writer must still be grep-findable).

### Layer 3 — Adversarial review (= fresh-context vcsdd:vcsdd-adversary, round 2)

Spawn after Layer 1 + 2 both pass. Adversary reviews spec v2, verify-arch v2,
and the implementation files. Output → `reviews/r2/output/spec-verdict.md` and
`reviews/r2/output/impl-verdict.md` (= two passes possible; combine if same round).

## Mapping invariant → layers (v2)

| Invariant | L1 grep | L2 E2E | L3 adversary |
|---|:-:|:-:|:-:|
| C1 EXIF auto-rotate (compress + raw path) | ✓ | E1 | ✓ |
| C1.5 PNG through PIL | ✓ | (= no PNG fixture in E1, source-only) | ✓ |
| C1.6 --dry-write | ✓ | E1 (uses the flag) | ✓ |
| C2 consec-anchor warn | ✓ | E2 +/- | ✓ |
| C3 --no-cleanup-duplicates gate | ✓ (`if not args\.no_cleanup_duplicates:`) | E3 (--help) | ✓ |
| C4 WARN→delete+retry branch | ✓ (`DELETING via`) | (= live-fire OUT OF SCOPE per spec) | ✓ |
| C5 replace_image_in_draft + URL guard | ✓ (py_compile + URL grep) | E4 +/- | ✓ |
| C6 shared delete_image_block helper | ✓ (def + ≥2 callers) | (= proven by source) | ✓ |
| C7/C8 SKILL.md appends | ✓ (heading count) | E5 | ✓ |
| C9 URL guard rejects example.com | (= subset of C5) | E4 | ✓ |

## "Done" = 4-D convergence

1. **Spec ✓** = round-2 adversary spec-review PASS on all 5 dims (or FAIL on
   non-critical dims with explicit accepted-risk reasoning).
2. **Test ✓** = `tests/verify-all.sh` exits 0 (= every L1 grep + every L2 E2E
   green, in sequence, in one run).
3. **Impl ✓** = all 7 files written, `python3 -m py_compile` clean, no
   syntax errors.
4. **Verify ✓** = round-2 adversary impl-review PASS.

Live-render verify gate (the second of HARD 0.37's TWO gates) is explicitly
DEFERRED to the next real article run — Dais said no X publish in this
session, so no live-fire fixture this round. Documented in spec §"Out of scope".

## Stop rules

- L1 fails → fix code, re-run L1 → don't proceed.
- L2 fails → fix fixture or impl, re-run; if persistent → adversary helps.
- L3 returns FAIL on a load-bearing dim → fix, write `r3/output/...` round, max
  3 rounds in lean mode.
