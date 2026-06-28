# Round 3 evidence notes

## article.json + article.html regenerated after source.md fixes
- Pre-R2: `missing_images: 1`, `content_images[0].exists: false` (parser fooled by title-quote syntax)
- Post-R3: regenerated against FIXED source.md (which already had the title-quote stripped + ④ split + 。。 collapsed). See `impl/article.json` + `impl/article.html` current contents.

## V1 manual paste — documented gap-closure
- Publisher's WARN-on-missing behavior is by-design (current implementation).
- Verification gate caught it; V1 was manually inserted via Playwright CDP at the
  anchor `ここに正面から取り組んだのが、Franklin です。公式 README は、自分自身をこう紹介しています`.
- Post-paste img count delta: 6 → 7 (verified in code; see `evidence/v1-retry.jpg`).
- Visual confirmation: `evidence/v1-final-region.jpg` shows V1 directly between [1] hook (ending in 「Franklin は払う。」) and [2] heading 「Franklin は『自分の財布で動く AI エージェント』」.

## H3 platform constraint
- X Articles renders `<h3>` visually flat against paragraph text. [7] sub-sections
  (今日入れてたほうが良い人 / もう少し待っていい人) work because they use **bold paragraph**
  in `source.md`, NOT actual h3. Adversary's R1 H3 finding refers to a theoretical
  problem that does not bite this article. Spec line 4b documents this platform
  constraint to prevent future regressions.

## Live draft state (post-R2)
- DRAFT URL: https://x.com/compose/articles/edit/2071129016560758784
- `Last saved 6 seconds ago` confirmed in `evidence/r2-money-maker-split.jpg` + `r2-period-fix.jpg`
- 509 words (508 + 1 newline from R2 ④ split)
- Publish button visible, NOT clicked (= NEVER published, per skill rule 8)
