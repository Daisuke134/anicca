---
created: "2026-07-23T13:05:00+09:00"
priority: 1
sources:
  - /Users/anicca/profitable-claude/skills/article-writer/state/runs/20260720-1637/article-ja.md
  - /Users/anicca/profitable-claude/skills/article-writer/state/runs/20260720-1637/article-en.md
  - /Users/anicca/profitable-claude/skills/article-writer/state/runs/20260720-1637/gates/reader-ja-attempt2.json
  - /Users/anicca/profitable-claude/skills/article-writer/state/runs/20260720-1637/gates/reader-en-attempt1.json
  - /Users/anicca/profitable-claude/skills/article-writer/state/runs/20260720-1637/gates/rubric-ja-recheck5.json
  - /Users/anicca/profitable-claude/skills/article-writer/state/runs/20260720-1637/gates/rubric-en-final.json
  - /Users/anicca/profitable-claude/skills/article-writer/state/runs/20260720-1637/gates/identity-ja-recheck2.json
  - /Users/anicca/profitable-claude/skills/article-writer/state/runs/20260720-1637/gates/identity-en.json
  - /Users/anicca/profitable-claude/skills/article-writer/state/runs/20260720-1637/gates/conscience-ja.json
  - /Users/anicca/profitable-claude/skills/article-writer/state/runs/20260720-1637/gates/conscience-en.json
  - https://addyosmani.com/blog/loop-engineering
  - https://zenn.dev/suwash/articles/loop-engineering_20260610
  - https://www.anthropic.com/institute/recursive-self-improvement
  - https://lilianweng.github.io/posts/2026-07-04-harness/
required_sources:
  - /Users/anicca/profitable-claude/skills/article-writer/state/runs/20260720-1637/article-ja.md
  - /Users/anicca/profitable-claude/skills/article-writer/state/runs/20260720-1637/article-en.md
  - /Users/anicca/profitable-claude/skills/article-writer/state/runs/20260720-1637/gates/reader-ja-attempt2.json
  - /Users/anicca/profitable-claude/skills/article-writer/state/runs/20260720-1637/gates/reader-en-attempt1.json
  - /Users/anicca/profitable-claude/skills/article-writer/state/runs/20260720-1637/gates/conscience-ja.json
  - /Users/anicca/profitable-claude/skills/article-writer/state/runs/20260720-1637/gates/conscience-en.json
angle: ループ設計とは、AIエージェントに毎回指示する代わりに、起動条件・外から検証できる停止条件・独立した判定者・失敗時の既定動作を設計すること。旧Writerで日英の読者テスト、identity、品質、conscienceを通過した未公開原稿を正本として、毎日自走させるための実践的な設計図を日英それぞれネイティブ記事として公開する。
---

# AIエージェントに毎回「次は？」と聞かれない仕組み

## Publication authorization

未公開の carry-over 原稿を、Writer Engine の現行 quality/reality gate に再投入して公開する。
旧ゲートの自己申告だけで公開済みにせず、現行Runで日英記事・独立X Post・exact8 readbackを再検証する。
