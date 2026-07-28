# Life Manager LT（日本語）

Life Manager の目的、現状、残TODOを説明する14枚の日本語スライドです。

## 成果物

- `life-manager-lt-ja-2026-07-28.pptx` — 発表用PowerPoint
- `life-manager-lt-ja-2026-07-28.pdf` — 配布・確認用PDF
- `life-manager-lt-ja-2026-07-28-thumbnails.jpg` — 全スライドの検証用一覧
- `talk-notes.md` — 話す内容と残TODOの詳細
- `build-life-manager-lt.js` — 再生成ソース
- `html/` — PowerPointへ変換する各スライドのHTML

## 再生成

```bash
node docs/slides/life-manager-lt-2026-07-28/build-life-manager-lt.js
python .claude/skills/pptx/scripts/thumbnail.py \
  docs/slides/life-manager-lt-2026-07-28/life-manager-lt-ja-2026-07-28.pptx \
  docs/slides/life-manager-lt-2026-07-28/rendered \
  --cols 4
```

## 内容の正本

- `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`
- Codex の現行 `Life Manager` スレッド（active）のライブキュー

ローカル正本の実行カーソルと、別スレッドのライブキューは意図的に分離表示しています。
