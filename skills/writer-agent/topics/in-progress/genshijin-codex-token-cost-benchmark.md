---
lane: A
created: "2026-07-22T17:18:24+09:00"
priority: 0
form: article
voice: recit
sources:
  - /Users/anicca/profitable-claude/skills/article-writer/specs/genshijin-codex-benchmark-article.md
  - https://github.com/InterfaceX-co-jp/genshijin
  - https://github.com/JuliusBrussee/caveman
  - https://github.com/JuliusBrussee/caveman/blob/main/docs/HONEST-NUMBERS.md
  - https://developers.openai.com/api/docs/pricing
  - https://zenn.dev/sonicmoov/articles/8712598f532b18
angle: GenshijinをCodexで使うと本当に得かを、通常応答・単純な「簡潔に」・英語版Cavemanとの192出力比較で検証する。出力トークンだけでなく、skillが追加する入力トークン、API換算コスト、品質、読みやすさ、break-evenまで測り、日本語版と英語版を別々のネイティブ記事として公開する。
---

# Genshijin on Codex: output tokens, total cost, and quality

ユーザー指名カード。記事の主題は Genshijin plugin/skill そのもの。既存 article-writer skill へ Genshijin や Caveman を統合しない。

## 正本

最初に `sources` のローカル SPEC を全文読む。実験条件、記事構成、artifact、公開判定はすべて SPEC を正本とする。このカードと SPEC が食い違う場合は SPEC を優先する。

## 必須の調査線

- Genshijin は主役。Caveman は英語圏の原型と比較対象。
- Codex で検証するのは `npx skills` で入る core skills。Claude Code 固有 hooks/statusline/統計機能を Codex の機能として書かない。
- 既存 README の75〜80%や65%を転載して結論にしない。Codex の新規セッションで独立再測定する。
- normal / terse / caveman-full / genshijin-normal の4条件を維持する。
- JP/EN × 8 tasks × 4 conditions × 3 trials = 192 outputs。無効試行と retry も残す。
- output-only savings と input overhead 込み API-equivalent cost を別々に示す。
- Codex subscription の実請求額とは呼ばない。
- correctness、completeness、code safety、readability を blind 評価する。
- Before/After は差が最大の例を手選びせず、SPEC の median-nearest rule で選ぶ。

## 執筆線

Lane A。Dais の一人称で、なぜ気になったか、どう条件を揃えたか、数字がどう出たか、どんな仕事で ON/OFF すべきかを語る。結果が Genshijin に不利でもそのまま主結論にする。

Working titles:

- JP: `GenshijinでCodexの出力は本当に8割減るのか。入力コストまで含めて192回試す`
- EN: `Does Genshijin Actually Cut Codex Costs? 192 Runs Against Caveman and “Be Concise”`

有効件数が192未満ならタイトルを実数へ直す。JP と EN は直訳せず、それぞれの読者に自然な構成で書く。

## Publication authorization

この card の記事は、現行 article loop の全品質・安全・render gate を通過した場合に限り armed scope で公開してよい。note/ja、Zenn/ja、Substack/ja、Substack/en、X/ja、X/en は live + reality PASS まで完了する。dev.to は現行契約どおり draft-only。

