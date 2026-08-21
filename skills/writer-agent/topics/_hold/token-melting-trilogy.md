---
lane: A
created: "2026-07-17T14:40:00+09:00"
voice: recit
sources:
  - /Users/anicca/anicca-project/docs/loop-engineering/42-why-tokens-still-melt.md
  - /Users/anicca/anicca-project/docs/loop-engineering/43-floor-budget-the-permanent-rule.md
  - /Users/anicca/anicca-project/docs/loop-engineering/44-floor-minimization-best-practice.md
angle: 「床を掃除しても課金は溶け続けた」— 自分の仮説が5連敗した末に実測ログで突き止めた真因（課金 = 文脈サイズ×ターン数の二次関数、1セッション$77の実データ）と、二度と太らせない機械強制の作り方。
---

三幕構成で1本の長編にする（診断→処方→裏付け）:

1. **本文の柱 = 42番**: 実セッションの cache_read 推移（150k→434k/ターン）、$77 セッション、
   自分の仮説が5回連続で外れた記録（5分TTL説・OpenClaw犯人説…全部実データで棄却）。
   恥を隠さない失敗談として書く — これがこの記事のフック。
2. **後半 = 43番の床予算表**（≤25,000tok、超過時の対処順序 skill→rules→memory→CLAUDE.md、
   2026-07-13 の手術 before/after 実数字）を「実践チェックリスト」として。
3. **裏付けボックス = 44番の公式引用集**（Anthropic 公式 docs + HumanLayer/Karpathy/Chroma）。
   本文には混ぜず、脚注/参考文献ボックスに落とす。

正直に書くこと（評価で見つかった弱点、隠さない）:
- 二次関数モデルは自分の実測 derivation であり、外部検証（他環境・Anthropic 公式説明との突合）は
  まだ無い —「私の環境の実測ではこう」と明示する
- 処方 P1-P6 の効果額は計算値で、実行後の before/after 実測ではない — その旨も書く
