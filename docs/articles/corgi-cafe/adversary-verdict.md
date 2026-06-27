# Adversary Verdict — Corgi X Articles publisher (2026-06-27)

Disk-only review per HARD 0.37 (VSDD). Adversary cannot open a browser; verdict
is built from the markdown, the script, the run.log, and the rendered-draft
screenshots already on disk.

## D1 SPEC FIDELITY: PASS

The markdown matches Dais's stated instructions, and the script has no path
that could click Publish. The remaining spec gap (does the result on X match
the markdown?) is logged under D3/D5, not here.

- `docs/articles/corgi-cafe/article-jp.md:1` — H1 is the narrative title
  ("24時間営業のスタートアップカフェ「Corgi Cafe」(SF) に行ってきた"),
  NO `[0] 最初に：この記事は何か` verdict block opens the body; rule
  `MORE LESSONS (2026-06-27)` §1 in
  `~/.claude/skills/ai-entity-article-writer/SKILL.md:160-163` explicitly
  allows skipping [0] for narrative/visit pieces. ✓
- De-Englishization (rule `MORE LESSONS (2026-06-27)` §2 sweep table in
  `~/.claude/skills/ai-entity-article-writer/SKILL.md:165-181`):
  `article-jp.md:17` "26歳の Nico Laqua、共同創業者 Emily Yuan", "YC 2024卒",
  "シリーズAで $108M(評価額 $630M)"; `:19` "1階の店舗", "ボロカス" is replaced
  with "絶対やめろ" (matches the sweep mapping); `:43` "Wi-Fi 認証ページ"
  (not "captive portal"); `:55` "Y Combinator 卒は20%引き"; `:68` "厳しいダメ出し",
  "SF ベイエリア在住"; `:71` "ブランド責任者". ✓
- First-person visit voice: `article-jp.md:23,33,37,55,57,71` use 私 / 試して
  ません / 私の場合は / 個人的な印象. ✓
- Mandatory cover headline of front-of-cafe photo: `article-jp.md:3`
  `![Corgi Cafe Grand Opening](./assets/IMG_4922.jpg)` — confirmed
  rendered as cover in `verify/scroll-00.png` (banner + entrance + "9
  Claude Lane" door number visible). ✓
- QR-tablet → orange Verifying-receipt iPhone → LMGH code sequence
  preserved: `article-jp.md:25-37` (QR tablet paragraph → IMG_4926
  insertion → 電話番号 paragraph → IMG_4924 insertion → Verifying paragraph
  → IMG_4925 insertion → 4文字のコード paragraph with `LMGH`). The
  markdown source preserves the sequence; the rendered draft does NOT
  (see D5 — but that is an implementation defect, not a spec defect). ✓
  for the source.
- Ends with おすすめする人/しない人 + 出典: `article-jp.md:86-89` and
  `:91-95`. ✓
- Script NEVER publishes:
  `~/.claude/skills/x-article-publisher/scripts/publish_md_to_x.py:55`
  ("NEVER publish. The script has no publish path; HARD-banned."),
  and no `Publish` / `投稿` / `公開` button click exists anywhere in the
  file (grep returns 0 active code paths; only docstring and a single
  Preview-button regex `^Preview$|^プレビュー$` at `:526` which is anchored
  and cannot match `Publish`). ✓

## D2 EDGE CASES: FAIL

Multiple silent-failure modes are unhandled. Each will produce a draft
that "looks done" in the log but is wrong on X.

- `publish_md_to_x.py:421-425` — argparse registers ONLY `md`, `--cdp`,
  `--screenshots-dir`, `--no-cleanup-empties`, `--no-verify-render`. The
  branch at `:466` `if getattr(args, "dedup_by_title", False):` calling
  `cleanup_matching_drafts` is **dead code** — the flag `--dedup-by-title`
  is referenced in the comment at `:464-465` but never registered, so it
  is impossible to enable from the CLI. The function it would have called
  exists at `:172-190` but never runs. User-visible failure: every re-run
  silently piles up a duplicate draft with the same title (proven below).
- Re-run idempotency: `cleanup_empty_drafts` at `:192-239` only deletes
  rows whose preview text contains literal `"(Needs title)"`
  (`:197`: `page.get_by_text("(Needs title)", exact=False)`). Same-title
  duplicates from previous partial/full runs are NEVER deleted, because
  the `cleanup_matching_drafts` path is dead-coded (above). Disk evidence:
  `screenshots/01-articles-landing.png` (BEFORE cleanup) shows **two**
  pre-existing drafts (a same-title `24時間営業のスタートアップカフェ「Corgi
  Cafe」(SF) に行ってきた` and a different-title `サンフランシスコの24時間…`);
  `run.log:4` reports `cleanup: 0 empty drafts`; `screenshots/03-after-cover.png`
  shows the sidebar STILL has those same two leftover drafts plus the new
  `(Needs title)`. `verify/scroll-00.png` then shows **three** drafts in
  the sidebar (current + 2 leftovers). User-visible failure: a daily cron
  will leak N drafts per N runs forever.
- `click_first_visible(page, [...], timeout=2000)` at `:116-127` returns
  `False` if NONE of the selectors are visible in 2 s. Callers handle this
  differently:
  - `click_write` at `:241-268`: falls back to `page.goto(...articles/new)`
    when Write is unfound. Reasonable.
  - `click_edit_media_apply` at `:285-297`: only waits for the
    text=`"Edit media"`. If the cover upload silently fails (X rejects
    HEIC bytes posing as JPEG, network blip, X's UI in another locale)
    the modal never appears, the function logs and returns False **but
    the script keeps going** — title and body get pasted on top of a
    broken cover slot. Nothing aborts. User-visible failure: published
    draft with empty cover and the user only finds out at publish time.
  - The Apply button regex (`button:has-text("Apply")`,
    `div[role="button"]:has-text("Apply")`, `:has-text("適用")`) covers
    only EN+JP. X's editor in any other locale (ZH "应用", DE "Übernehmen",
    ES "Aplicar") will silently miss Apply, leaving the modal up to
    swallow every later click — exactly the scenario `HARD-LEARNED #2` in
    SKILL.md warns about as `silently hangs`.
- Upload spinner regex at `:405-407`:
  `text=/uploading|アップロード中|正在上传媒体/i` covers EN/JP/ZH only. Any
  other locale → the wait raises, the bare `except: time.sleep(3)` at
  `:409-410` runs, and a slow image (HEIC re-encoded by macOS pasteboard
  to a large JPEG) is not finished uploading when the next Cmd+V fires.
  User-visible failure: the *next* image's clipboard overwrites the
  in-flight upload buffer → an image is silently lost.
- Title selector list at `:302-306` is strictly `textarea[...]`. If X
  flips its title widget to a contenteditable (already used for the
  body), all three selectors miss, `type_title` returns False, the
  script `sys.exit("title fill failed")` at `:482`. The cover is already
  uploaded by then, leaving an orphan `(Needs title)` draft. There is no
  rollback / cleanup of the partially-built draft on failure.
- CDP attach: `:449` `p.chromium.connect_over_cdp(args.cdp)` is not
  wrapped in `try`. If the daily-driver is not on `:9222` (the user
  restarted CloakBrowser without `--remote-debugging-port`), the user
  sees a raw `playwright.sync_api.Error` traceback rather than a
  human-actionable "no CDP at <url>; start the daily-driver with
  --remote-debugging-port=9222". `browser.contexts` IS checked one line
  later (`:450-451`), so that one case is friendly; CDP-down is not.
- HEIC vs JPEG mismatch (article-specific edge that the GENERAL script
  ignores): `docs/articles/corgi-cafe/assets/` contains 16 files — 8
  `.heic` and 8 `.jpg`. The markdown points at `.jpg`. `parse_markdown.py`
  has no MIME / extension validation; if a future markdown points at
  `IMG_XXXX.heic`, X will reject the upload (X Articles does not accept
  HEIC). `insert_content_image` will paste a "broken-image" placeholder
  and the wait-for-spinner regex never fires. User-visible failure: a
  broken `❓` placeholder in the body.
- Preview button regex at `:526` is anchored EN/JP only. `run.log:44-46`
  shows the Preview attempt timed out, so the `verify-rendered.png`
  artifact promised in the docstring (`:33-35`) is NEVER produced. The
  caller is then asked by `:541` to "review screenshots, and edit/publish
  manually" — but the in-script verification gate is silently inert.
- `dismiss_overlays(page)` at `:133-140` only fires two `Escape`
  presses. Any modal that ignores Escape (X "Subscribe to Premium" promo,
  cookie banner in a fresh profile, the Edit-media modal itself) is NOT
  dismissed. `click_first_visible` then can't find Write because it's
  occluded.

## D3 IMPL CORRECTNESS: FAIL

The script's headline claim — "8/8 inserts succeeded" per `run.log` —
is correct ONLY in the sense that no exception was raised. The actual
placement is wrong for the majority of inserts (proven under D5). The
algorithm has at least these correctness defects:

- `insert_content_image` at `:342-415` clicks at the BOTTOM-RIGHT corner
  of the target block (`:386-387`
  `x: r.x + r.width - 8, y: r.y + r.height - 8`). For wrapped Japanese
  text (rule: text wraps and the last visual line ends mid-column), the
  bottom-right pixel of the bounding rect is usually past the end of the
  last text node. In Draft.js, a mouse click in the empty zone at the
  end of a block can route the SelectionState to the FOLLOWING block
  (because the click hits a sibling padding region, not the text node
  the walker matched). That is consistent with the screenshot evidence
  in D5 (IMG_4924 anchored ONE block too HIGH, IMG_4927 anchored ONE
  block too HIGH). The fix the script's comment promised at `:355` was
  "click at the END of the line", but the actual coordinate is "the
  end-of-rect" which is not the same thing for wrapped text.
- The walker at `:368-381` matches a TextNode whose `textContent`
  `.includes(text)`. After insertion of the first image, Draft.js
  re-renders the editor; if a fresh image creates an atomic block with
  its own caption text (e.g. `Provide a caption (optional)`), that
  caption is also a text node and a subsequent search whose `text` is a
  substring of any image caption would lock onto the WRONG node. Not
  triggered by this article (Japanese phrases don't overlap with that
  EN placeholder), but a future EN article saying `caption optional`
  in body text is one ambiguity away from misfire.
- `search_phrase` at `:100-113` truncates to 30 chars. For a search
  string that begins with a phrase shared by multiple paragraphs (e.g.
  "このカフェ" appears at `article-jp.md:5,79`), the walker would match
  the LAST occurrence regardless of which paragraph the user intended.
  The comment claims "30 chars = unique enough fingerprint" but never
  validates uniqueness — there is no check `if textContent.count(text)
  > 1 in editor: warn`. A silent mis-anchor is logged the same as a
  correct anchor.
- `cleanup_empty_drafts` row-scoping at `:212-218`: the primary
  selector (`ancestor::article|@role=link|@role=article`) is correctly
  row-scoped, but the fallback at `:217-218`
  `xpath=ancestor::*[1]//button` climbs to the IMMEDIATE parent and
  picks the first button under it. If X ever wraps draft rows in a
  generic `<div>` without `article`/`role`, the fallback would scan a
  large subtree and could click ANY button (including the global "More"
  sidebar item). The defense is fragile; "never the sidebar More" is
  claimed in the comment at `:194` but not enforced.
- The Preview-click block at `:524-535` invokes
  `page.get_by_role("button", name=re.compile(r"^Preview$|^プレビュー$"))`
  and on miss writes `08-final-overview.png`. There is NO real
  verification of any image's landed position. The script claims the
  caller will eyeball screenshots, but the BUILDER's own readout
  (claim: "Cover, IMG_4920, IMG_4931, IMG_4927 correct; IMG_4924,
  4925, 4926, 4928, 4930 displaced") is REFUTED by the on-disk
  screenshots (see D5) — proving the "self-verify" step is not
  effective. The verification gate documented at SKILL.md:616-625
  exists only as prose; nothing in code enforces it.
- Title selector — `:302-306` lists `textarea[name="Article Title"]`
  first; correct. ✓
- Body selector — `:322-326` lists `div[data-testid="composer"]` first
  with `div.public-DraftEditor-content` and
  `div[contenteditable="true"][role="textbox"]` as fallbacks. The third
  fallback is risky: X's Title field is *also* a `textbox`-roled
  contenteditable in some build flags, so a future regression could
  pick the title. Acceptable today; needs a comment "do not add looser
  fallbacks".
- Forward block_index order — `:501` `sorted(images,
  key=lambda x: x["block_index"])`. ✓ (matches the new `HARD-LEARNED
  #5` doc; see D4 for the contradictory other comment that still says
  REVERSE).

## D4 STRUCTURAL INTEGRITY: FAIL

Documentation has not been brought in line with the script's third
iteration; dead code remains; the script is not idempotent.

- Documentation drift inside `publish_md_to_x.py`:
  - `:28` "Insert each content image in REVERSE block_index order" —
    STALE. The code at `:501` does forward (ascending) order. The new
    inline comment at `:494-499` says forward.
  - `:52-54` `Image insert order: REVERSE block_index — earlier inserts
    shift indices of later targets, but inserting at the bottom first
    leaves earlier targets stable.` — STALE; contradicts `:494-499`
    and `:501`. The reader who trusts `DESIGN NOTES` gets the wrong
    mental model.
  - `:96-98` `strip_md` is documented as "Strip markdown markers so a
    substring search matches the rendered DOM", but
    `insert_content_image` at `:359` uses `search_phrase`, NOT
    `strip_md`. `strip_md` is now dead code outside this comment.
- Documentation drift inside `~/.claude/skills/x-article-publisher/SKILL.md`:
  - `## Step 6: Insert Content Images (Text Search Positioning)`
    (lines 261-330): the entire workflow described uses `after_text`
    with `browser_press_key: End` from the OLD Playwright-MCP era and
    declares "按 block_index 从大到小的顺序" / "反向插入示例"
    (lines 271, 324). The current canonical script is forward order.
  - `## Step 6.5: Insert Dividers` line 338 `For each divider … in
    **reverse order of block_index**` — same staleness.
  - `## Critical Rules` line 374 `**Reverse order insertion** -
    Insert images and dividers from highest to lowest block_index` —
    contradicted by the new section at lines 549-625 and by the script.
  - `## Example Flow` line 412 `For each content image, **in reverse
    order of block_index**` — same.
  - `## Step 1: Parse Markdown` block index notes at lines 172-173
    declare `after_text: Kept for reference/debugging only, NOT for
    positioning`. The new script (the section the user is now told to
    use) actively positions by `after_text` via `search_phrase`
    (`publish_md_to_x.py:359-360`). Direct contradiction inside the
    same skill file.
  - The old `## 中文 helper sections` (lines 85-145) reference
    `browser_snapshot` / `browser_wait_for` / `browser_press_key`
    primitives that the new script does not use. Two skill-doc layers
    coexist; a new reader has no way to know which is current.
- Dead code:
  - `cleanup_matching_drafts` (`:172-190`) is invoked only at
    `:466-468` behind `getattr(args, "dedup_by_title", False)`, but
    `dedup_by_title` is **never registered** in argparse (`:421-425`),
    so the function can never run and the title-dedup feature is
    fictional.
  - `strip_md` (`:96-98`) is no longer called by any image-insertion
    path; `search_phrase` (`:100-113`) replaced it. Either delete
    `strip_md` or call it where intended.
- Re-run NOT idempotent: see D2. Disk evidence:
  `screenshots/01-articles-landing.png` (2 pre-existing drafts),
  `verify/scroll-00.png` (3 drafts in sidebar after this run). Every
  invocation grows the draft list by 1.
- Nothing in the script is Corgi-specific (grep for `corgi|Corgi|IMG_`
  returns 0 hits in `publish_md_to_x.py`). The article path, image
  filenames, language, and title all flow from `args.md` →
  `parse_markdown.py`. ✓ for that one structural goal.

## D5 VERIFICATION READINESS: FAIL

Per-image-position table built from `article-jp.md` (intent) vs the
9 full-page screenshots `verify/scroll-00.png` … `verify/scroll-08.png`
(actual rendered draft):

| Image | Intended section / after-paragraph | Actually rendered between | OK/WRONG | Evidence |
|---|---|---|---|---|
| IMG_4922 (cover) | Cover slot | Cover slot | OK | `scroll-00.png` shows the front-of-cafe Grand Opening banner photo as the article cover above the title. |
| IMG_4920 (夜の窓越し) | 「やってるのは AI 保険スタートアップ」 section, AFTER "外から窓越しに見ると…corgi の立体文字。" | Between "…corgi の立体文字。" (`article-jp.md:13`) and "このカフェ、Corgi…" (`:17`) | OK | `scroll-01.png` |
| IMG_4926 (QRタブレット) | 「Wi-Fi の繋ぎ方」 section, AFTER "カウンターに オレンジの QR タブレット…これを iPhone で読み取るのが最初。" (`article-jp.md:25`) | NOT visibly placed anywhere in the WiFi section | WRONG / missing | `scroll-03.png` shows the entire WiFi body text (普通の…/カウンター…/電話番号…/「Verifying…) with NO image between any of those paragraphs. `run.log:15-18` claims the insert succeeded; the rendered draft disagrees. |
| IMG_4924 (Verifying receipt) | 「Wi-Fi の繋ぎ方」 section, AFTER "電話番号を入れると、ショートメッセージでリンクが届く。タップするとブラウザがこの画面に飛びます。" (`article-jp.md:29`) | Inserted in the **AI 保険スタートアップ** section, between "シリーズAで $108M(評価額 $630M)。" (`:17` last sentence) and "カフェは本社の1階…" (`:19`) | WRONG | `scroll-02.png` (image starts immediately under the `$108M / $630M` paragraph), `scroll-03.png` (the bottom of the same image labelled `Powered by Goby WiFi` is followed by `カフェは本社の1階…`, which is the AI section's last paragraph). |
| IMG_4925 (LMGH コード) | 「Wi-Fi の繋ぎ方」 section, AFTER "「Verifying receipt...」(レシート照合中)…数秒で次に切り替わる。" (`article-jp.md:33`) | NOT visibly placed; the next paragraph "4文字のコード(私の場合は `LMGH`)が出ます。これを Wi-Fi のログイン画面に入れると繋がる。" (`:37`) is the FIRST thing in `scroll-04.png` with no preceding image | WRONG / missing | `scroll-03.png` end → `scroll-04.png` start = continuous text, no image inserted. |
| IMG_4930 (カウンターとメニュー) | 「オレンジの椅子とノートPCの海」 section, AFTER "カウンター上にメニューが3面…Boardy という AI エージェントとのコラボらしい)。" (`article-jp.md:47`) | Between that paragraph and "席はオレンジ、机もちょっとオレンジ…" (`:51`) | OK | `scroll-04.png` (image top: ceiling) → `scroll-05.png` (image bottom: counter with menus and barista) → "席はオレンジ…" paragraph. |
| IMG_4931 (店内) | 「オレンジの椅子とノートPCの海」 section, AFTER "席はオレンジ…半分は普通のオフィスワーカー。" (`article-jp.md:51`) | NOT visibly placed; the only image between "席はオレンジ…" and "私が頼んだのは…" is the coffee photo (IMG_4927), NOT the店内 photo | WRONG / missing | `scroll-05.png` end and `scroll-06.png` start show only one image in this gap and it is the coffee-cup-on-marble shot. |
| IMG_4927 (コーヒー) | 「オレンジの椅子とノートPCの海」 section, AFTER "私が頼んだのはホットコーヒー、$7.20…" (`article-jp.md:55`) | Inserted ONE block too HIGH, between "席はオレンジ…" (`:51`) and "私が頼んだのは…" (`:55`) | WRONG | `scroll-05.png` (coffee image starts immediately under `席はオレンジ…`) → `scroll-06.png` (image bottom; `私が頼んだのは…` paragraph appears AFTER the image). |
| IMG_4928 (採用ビラ) | 「入口の採用ビラ」 section, AFTER "このカフェで一番、空気をよく表してたのは飲み物じゃなくて、入口横に置かれた **採用ビラ** でした。" (`article-jp.md:61`) | NOT visibly placed in 入口の採用ビラ section; the section goes directly from that opener to the `募集 / 給与 / …` bullets with no image in between | WRONG / missing | `scroll-06.png` shows the full opener-to-bullets block with no image; `scroll-07.png` shows the remainder of the section and the next `## 結局このカフェは何なのか` header, still with no 採用ビラ image. |

Tally (CONTENT images only; the cover slot is separate):
- 2 of 8 visibly correct (IMG_4920, IMG_4930).
- 2 of 8 visibly placed but in the WRONG paragraph (IMG_4924 dropped
  into the AI section, IMG_4927 anchored one block too high in the
  オレンジ section).
- 4 of 8 NOT visibly placed anywhere in their target section
  (IMG_4926, IMG_4925, IMG_4931, IMG_4928). They are either silently
  stacked behind one of the visible images (Draft.js can collapse
  consecutive image-atomic blocks visually when inserted into the same
  selection point) or pasted into a section that the 9 scroll captures
  did not cover. Either way the rendered draft does NOT match the
  markdown.

★ The BUILDER's self-report ("Cover, IMG_4920, IMG_4931, IMG_4927 in
correct section; IMG_4924, IMG_4925, IMG_4926, IMG_4928, IMG_4930
displaced") is REFUTED by the screenshots:
  - IMG_4930 is actually CORRECT (counter+menus image is exactly where
    `article-jp.md:49` puts it). Builder mis-called it displaced.
  - IMG_4931 is NOT visible in the correct section (店内 image is not
    seen between "席はオレンジ" and "私が頼んだのは"). Builder mis-called
    it correct.
  - IMG_4927 is in the WRONG paragraph (anchored one block too high,
    between "席はオレンジ" and "私が頼んだのは" instead of after "私が頼んだ
    のは"). Builder mis-called it correct.
The "self-verification" step is therefore non-functional: it produced a
confident readout that disagreed with the actual rendered draft on 3
of the 4 cases it judged. The verification gate documented at
`SKILL.md:616-625` is prose without enforcement and DID NOT prevent the
mis-call. ★

Overall D5: FAIL.

## OVERALL: FAIL

Most content images land in the wrong paragraph or are silently
missing; the script's own "self-verify" step contradicted the disk
screenshots; documentation in the script and SKILL.md still teaches the
abandoned reverse-order workflow; the title-dedup feature is dead
code; the cleanup is non-idempotent and verifiably leaks duplicate
drafts on every run.

Top 3 must-fix items before the next iteration:

1. **Image placement** — replace "click bottom-right pixel of the
   target block's bounding rect" (`publish_md_to_x.py:386-387`) with a
   Draft.js-native selection update: `getEditorState() →
   EditorState.forceSelection(state, SelectionState.createEmpty(blockKey).
   merge({focusOffset: block.getLength()}))` exposed through a
   `window.__forceArticlesCursorToBlockWithText__(text)` shim, then
   Cmd+V. Drop the mouse.click hack entirely. The current algorithm
   silently produced 2-of-8 correct content placements on the
   shipped run.
2. **Verification gate must be enforced in code, not prose.** After
   every `insert_content_image`, query the DOM for "is the
   most-recently-inserted figure node the DIRECT next sibling block of
   the block that contains `search_phrase(after_text)`?" If not, FAIL
   the run; do not just `time.sleep(0.5)` and move on. The current
   prose-only gate (`SKILL.md:616-625`) let the builder confidently
   misread the rendered draft.
3. **Idempotency + dead code** — either delete `--dedup-by-title`
   plumbing (`:172-190`, `:464-468`) or register the flag in argparse
   AND default it to ON for the canonical `python3 publish_md_to_x.py
   <article.md>` invocation. Concretely: every re-run with the same
   `<title>` MUST delete prior same-title drafts before creating a new
   one. Then prune the stale REVERSE-order documentation in
   `publish_md_to_x.py:28,52-54,96-98` and `SKILL.md:172-173,261-330,
   338,374,412` so the canonical doc agrees with the canonical code.
