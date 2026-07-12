# growth-engine — 自己改善型プロモーションskill 設計spec（2026-07-13、Dais音声確定）

## 0. 何であるか（1文）
**「製品コンテキストを渡せば、SNSアカウントを自分で作り・温め・投稿し・数字から学んで伸ばし続ける、no-human-loopの汎用プロモーションskill」**。LMマーケ(P1)はこのskillの最初の顧客にすぎない。全製品(affirmation iOS app / life-manager / anicca / Franklin / article / 将来の全プロダクト)がこれで自分を宣伝する。agent economyでもhuman builderでも使える = これ自体がOSS/売り物になる。

## 1. なぜ（Dais 2026-07-13）
- affirmation iOS app $10k MRR、life-manager $100k〜$1M MRR への鍵=マーケの機械化
- 全loopが「宣伝したい時にこのskillを呼ぶ」— 1製品のための1 loopを作らない
- 理論上アカウントは無限にスケール可能（まずIG 1垢から）

## 2. コアループ（self-improving content engine）
```
[製品コンテキスト(不変のcore message+CTA)]
        │
  ①台本生成: 痛みシーン日替わり×core固定。外部検索で「今バズってるフック形式」を採取して混ぜる
  ②動画/スライドショー生成(MoneyPrinterTurbo等)
  ③投稿(IG。専用ブラウザprofile/port、clip方式=9223/9224パターン)
  ④metrics収集(24-48h後): views/likes/saves/profile visits/link clicks/follows
  ⑤funnel jsonl記録 → Telegram日報(投稿URL+数字+次の実験)
  ⑥self-improve: 勝ち台本の要素分解(フック型/シーン/長さ/時刻)→次の台本を1変異だけ実験
  ⑦reality-verifier(埋込・report-blind): logged-outで「本当に公開されてるか」→FAILでself-fix
        └── ①へ戻る(朝夜2回)
```
- 変異は1回1変数(実験として成立させる)。判断は全てLLM(regex/if-else判定禁止=CLAUDE.md agents規約)
- アカウント自作: 既存skill `ig-account-create`(E2E実証済) + `ig-account-warmer`(7日warmup) をG2で統合

## 3. 段階(G-phases)
| G | 内容 | done |
|---|---|---|
| G0 | LM日本語IG。台本3本→Dais OK→手動動画1本→Dais OK(★loop化はOK後★) | Telegram品質OK |
| G1 | loop化: 朝夜2回投稿+④⑤⑥⑦全配線 | 3日連続で投稿URL+metricsがTelegramに届く |
| G2 | account-create+warmup統合(no-human-loopの垢量産口) | 新垢が人手ゼロでready化 |
| G3 | 多アカウント: JP垢+EN垢の2本立て(両audienceを各垢で) | EN垢も日次投稿 |
| G4 | 汎用化: 入力=製品コンテキストMDだけで任意製品に適用(affirmation appが2番目の顧客、openclawのlarry/reelclaw/honne cron群をこのskillに置換) | 2製品目が同一skillで稼働 |
| G5 | 多媒体: TikTok/YouTube/X/article への横展開 | 媒体adapter追加のみで動く |
| G6 | 全loopの標準装備化+OSS(profitable-claude harness/に収容) | どのloopも宣伝時にこれを呼ぶ |

## 4. LM編(G0)の確定パラメータ（Dais 2026-07-13）
- **言語**: まず日本語。その後EN垢を別に立てて両方運用(G3)
- **頻度**: 1日2回(朝=通勤帯、夜=就寝前)
- **Reddit**: 廃止(IGのみ→当たったら媒体拡張)
- **core message(不変)**: 「見なくていいカレンダー」— 物理予定のたびにGoogle Mapsで移動時間を調べ手入力する苦痛、常時カレンダー見張りの不安を、移動時間の自動計算・自動登録で消す(Dais本人の実痛点)
- **CTA(不変)**: aniccaai.com/life-manager

## 5. 台本3本(G0 STEP1、Daisアライン用)
**A「マップ往復」**: フック「予定を入れるたび、Googleマップ開いてない？」→ 痛み: イベント登録→マップで経路検索→「45分か…」→カレンダーに戻り出発時刻を逆算して手入力→次の予定と被って青ざめる →解決: Aniccaは予定を入れた瞬間に移動時間を自動計算、「出発」ブロックまで勝手に登録 → CTA「カレンダーは、任せるものへ」
**B「見張り疲れ」**: フック「『次なんだっけ』って、今日何回思った？」→ 痛み: 作業中もカレンダーをチラチラ、集中が切れる、見逃しの恐怖だけが残る →解決: Aniccaが「そろそろ出る時間」と先に声をかける。見るカレンダーから、教えてくるカレンダーへ → CTA
**C「ダブブの血の気」**: フック「ダブルブッキングに気づいた瞬間の、あの血の気」→ 痛み: 移動時間を入れずに連続で予定→物理的に間に合わない約束をしていた →解決: Aniccaは移動時間込みで衝突を先回り警告、リスケ案まで出す → CTA

## 6. 実装体制（Dais 2026-07-13確定）
- claude-p(私)=thinker(設計・アライン・最終verify)のみ。**コードは書かない**
- builder=Sonnet subagent(superpowers subagent-driven-development)、検証=VCSDD lean+fresh adversary(Sonnet)
- 掟5: subagent最小限。1 phase=1 builder

## 7. 記事ネタ（このプロジェクトから2本、ai-entity-article-writerのqueueへ）
1. **「AIの検証は3層ある」**: build時(vcsdd-verifier=証明・品質検査) / 出荷時(superpowers verification-before-completion=納品前動作確認) / **運用時(reality-verifier=毎日来る覆面調査員、report-blind・fresh context・実ブラウザ)**。実話フック=「3層目が無くて週予算の85%が闇で溶けた」(2026-07-12事件、doc 31の実測データ付き)
2. **「製品を渡せば勝手に伸ばすマーケ機械」**: growth-engine skillの設計と実測グロース曲線(G1完了後にデータが揃ってから)

## 8. 関連
正本TODO=00-SSOT.md §5。token掟=doc 31。競合地図=memory reference_proactive_life_manager_competitive_landscape。既存部品: ig-account-create / ig-account-warmer / MoneyPrinterTurbo(未導入) / clip式マルチprofile / gig式reality-verifier+funnel。
