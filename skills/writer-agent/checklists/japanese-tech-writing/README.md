# japanese-tech-writing

日本語の技術文書・書籍原稿の文章規範を定める Claude Skill。

## 出典（Attribution）

このスキルは [k16shikano](https://gist.github.com/k16shikano) 氏が公開している GitHub Gist
[`SKILL.md`](https://gist.github.com/k16shikano/fd287c3133457c4fd8f5601d34aa817d)（2026-07-17 時点で
Star 1,547 / Fork 92）を、attribution 付きでそのまま vendor したものです。`SKILL.md` の内容は
2026-07-17 に取得した gist の revision をそのまま使用しています（本 repo 側での改変なし）。

gist ページ自体には明示的なライセンス表記がありません。本 repo では
`docs/superpowers/specs/2026-07-14-article-earn-loop-ssot.md` §7.4/§7.6（#57）の決定に基づき、
出典を明記した上でそのまま参照利用しています。再配布・改変を行う場合は、まず原作者（k16shikano
氏）に確認してください。

## このスキルの役割（stop-ai-slop-jp との使い分け）

`deslop-gate.sh` は `--doc-type` フラグでこのスキルと `stop-ai-slop-jp` を切り替えます
（spec §7.4 で見つかった2つの矛盾——二人称の扱い、述語強度——が「文書種別」によって生じるため）。

- `--doc-type note`（既定）: `stop-ai-slop-jp` を使用。note 体験記・パーソナルな一人称の文章向け。
- `--doc-type tech`: この `japanese-tech-writing`（k16 gist）を使用。技術解説・書籍原稿寄りの、
  よりフォーマルな技術文書向け。

英語記事（`--lang en`）では `stop-slop` のみが使われ、このスキルは対象外です（k16 gist は
日本語文章規範のため）。
