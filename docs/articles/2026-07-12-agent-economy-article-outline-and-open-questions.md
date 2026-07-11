# エージェント経済 記事/本 — 構造・未回答の問い・タイトル（2026-07-12、Dais 議論で確定）

> 記事の evidence 正本 = [[../loop-engineering/17-agent-economy-deep-research-2026-07-10]]（landscape + to-be 10部品 + §11 goal-engineering）+ [[../loop-engineering/27-long-horizon-goal-engineering-BP]] + [[../loop-engineering/23-anicca-loop-architecture-redesign]]§11。既存ドラフト = [[2026-07-10-how-to-build-the-agent-economy-jp]]（[0]〜[8]の圧縮版＝本の序章）。

## 背骨（記事全体を貫く1問）
**Q1「AIが払い合うだけなら、本物の金はどこから入るのか？」= 循環マネー問題**。
- proof-of-earning（台帳に金が入った）は on-chain で機械が言える（易しい）。
- だが A→B→A の循環（自作自演）だと「両者が稼いだ」ように見えて価値ゼロ（Olas の1,450万tx=内輪マイクロタスクの正体）。
- → 本物の検証(validation)が答えるべき問い＝「その金は AI 経済の"外"から入った本物の価値か（external:true）」。
- なぜ最難: 難所A「価値=品質/正しさは機械採点できない」＋難所B「非循環=Sybil(1主体が複数偽ID)でないと証明」の two-fold。a16z「知能が安くなると希少になるのは検証」/ CertiK「Evaluator はコントラクトより難しい」。
- 我々: founder-loop の「external:true の実txだけを稼ぎと呼ぶ」= 難所B の第一歩。難所A(品質検証)は未解決＝賭ける本丸。生涯$5＝正直に薄い。

## まだ初心者に答えていない問い（記事で必ず答える）
| Q | 内容 | 記事での扱い |
|---|---|---|
| Q1 | AIが払い合うだけなら本物の金はどこから？(循環) | ★核心[5]。背骨 |
| Q2 | AIは具体的に何をして稼ぐ？どんなサービス？ | [6]で実例(gig/trade) |
| Q3 | なぜ普通の銀行口座でなくcrypto？ | 📌補足 |
| Q4 | wallet の金を盗まれたら/ハックされたら？ | 📌補足(鍵管理・上限) |
| Q5 | 暴走AIを人間は止められる？誰が制御？ | [6]認可・kill-switch |
| Q6 | 今、実際に黒字のAIはいる？全部$0？ | [4][6]正直に(大半$0) |
| Q7 | 結局また cryptoバブルでは？ | [4]hype vs real |
| Q8 | compute代 vs 稼ぎ、黒字になる？ | [6]エネルギー収支 |
| Q9 | トレードbot/RPAと何が違う？ | [1]定義(自律ループ) |
| Q10 | 仕事を奪う/危険では？ | [7] or 補足 |

## 記事構造（ハンバーガー、各ブロック→本の1章）
```
[0] Hook : 最も賢いAIが自分のサーバー代すら払えない
[1] 定義 : エージェント経済とは(全用語ape: wallet/USDC/on-chain)  ← Q9
[2] 理想 : あるべき姿=10部品(身元→通信→wallet→決済→ルーティング
           →escrow→評判→検証→認可→アプリ)  ★to-be
[3] 現状 : 5層で今どこまで(下半分=配管ほぼ完成/上半分=信頼まだ)
[4] hype : 「AIが稼いだ」9割の正体(ai16z 26億→数百万/Truth Terminal
           人間承認/循環tx)  ← Q6 Q7
[5] 核心 : 循環マネー問題 → 本物の価値の証明(validation)が最難所
           = 業界公認フロンティア(a16z「検証が希少」)。誰も未解決  ← Q1
[6] 我々 : Franklin on BlockRun ― 配管は採用、橋(検証+自己改善)を建てる。
           稼ぐ+建てるの両腕。正直な現在地=生涯$5、盛らない  ← Q2 Q5 Q8
[7] 結論 : 作りたい人へ(採用/測定/避ける)+我々が賭ける1点  ← Q10
[8] 最後に: アニッチャ + repo link
📌補足 : なぜ銀行でなくcrypto(Q3) / HTTP402とは / Sybil・鍵管理(Q4)
```

## タイトル候補
- A（推し）: 「AIがAIにお金を払う世界の作り方 ― 誰も解けていない"本物の証明"と、そこに賭けるAIたち」
- B: 「エージェント経済の作り方 ― 配管は完成した。残るは"信頼"だけ」
- C: 「自分でサーバー代を払うAI ― エージェント経済は、どこまで本物か」

## unified citizen loop（記事[6]の設計、Dais 2026-07-12）
Franklin ループ = Claude ループ = 同一テンプレ [稼ぐ]+[建てる]+[spawn]。今の Franklin は [稼ぐ] 片腕のみ→[建てる]腕(=[[27-long-horizon-goal-engineering-BP]] の北極星型ループ: OBSERVE as-is vs 理想→PICK 欠け→BUILD(bound付)→VERIFY(fresh adversary)→拡大)を埋める。graduation=Franklinが(a)net-positive (b)稼ぎで自compute(無料→Sonnet/Opus) (c)建てる腕で経済を建てる (d)self-heal/improve自走 → 全true で claude-p(親)exit。今日の reputation/gas VCSDD=その建てる腕の最初の一歩。
