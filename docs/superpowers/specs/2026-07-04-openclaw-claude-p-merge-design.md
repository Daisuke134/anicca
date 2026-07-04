# OpenClaw → claude-p loops 統合 + Collective Self-Improvement — Design

**Date**: 2026-07-04 · **Branch**: `feature/clip-rewards` · **Owner**: 私(myclaude, human-funded)
**Trigger**: Dais「OpenClawをclaude-p(human-funded AI)loopsに統合したい。DeepSeek課金を無くしたい。
将来的にはAnicca内でどこにでもAIをspawnできるようにし、ほとんどはself-funded、human-fundedは
OpenClaw/Hermes/どこでもspawn可能にしたい。まず全loopが正しく機能することに集中し、統合は後で」
**関連spec**: `2026-07-03-anicca-colony-architecture-design.md`(§0.2 WHO DOES THE WORK、
§2 Two modes、§8 The full loop が本specの前提)、`2026-07-04-self-heal-harness-no-human-no-opus-design.md`

## 1. 現状調査で判明した事実訂正(2026-07-04、Explore subagent 2並列調査)

### 1.1 「Life Managerは既にクラウドにある」→ 不正確

**★訂正(2026-07-04、Dais指摘で判明した調査ミス)★**: 上記1.1は誤りだった。前回の
subagentは`Daisuke134/life-manager`という**OSS配布用の別リポジトリ**だけを見ており、
Daisが実際に運営している本番環境を見落としていた。正しい実態(`~/.claude/projects/.../
memory/reference_life_manager_deploy_and_stripe_link.md` + `reference_life_manager_
launch_state_and_reply_by_email.md`より):

- 本番実体 = `apps/life-call`(raw Node httpサーバー、**Railway** Project Anicca/service
  life-call/production、mainブランチpushで自動デプロイ)+ Supabase(`cycgdwndgfgdbnndithc`)
- v1は**Telegram(@LifeManagerBotbot)で正式ローンチ済み**(onboarding: name→calendar
  (Composio連携)→phone→pay(Stripe)、Daisが実際にdogfoodしE2E確認済み)
- Web版: `/life-manager`(フルマーケティングページ、公開済み)、`/lm`はTelegram優先の
  ため意図的に「coming soon」ゲート中(`/lm?tg=<chatId>`は実オンボーディング動作)
- Stripe決済ページ稼働中($20/mo、`buy.stripe.com/9B600j6C204S7LadIG2880V`)

**「クラウドに既にある」は正しかった**。統合方針の判断材料としては、OpenClaw内の
`anicca-life-*`系cronはDais個人用の実験/前身であり、**本番はクラウド側(Railway
life-call)**という位置づけになる。

**Stripe実課金の確認結果(2026-07-04、本人へ正直に報告)**: `STRIPE_SECRET_KEY`で実際に
subscriptions一覧を取得したところ、7件全てが`canceled`(キャンセル済み)、かつ全て
同一customer(`cus_T5RqnJTcQ6xWlw`)だった。これはmemory記載の「lm_users=3 rows
(all Dais's own tests)」と符合し、少なくとも**この確認範囲では外部顧客の実課金は
見つからなかった**。もし別の決済チャネルや別のStripeアカウントで実際に課金が発生して
いるなら、その情報源を教えていただきたい — 推測では書かない。

### 1.2 OpenClawの`anicca-life-*`系14 job → ほとんどLife Managerと無関係

| 分類 | 件数 | 内容 |
|---|---|---|
| Dais個人専用(Life Manager無関係) | 9 | gcal修復/wallet監視/mail振分/booking/dentist・haircut予約/cfo_sync/event-bot/schedule-template |
| 着想は類似だが別コードベース | 5 | life-ask/life-notify-scan/-poll/travel-fill/arrival-mail — 実は**3世代の重複実装**が既に存在(`anicca-life-manager` skill→`anicca-alarm`→`life-manager`)、diffした結果コード共有なし |

結論: これらのjobは「クラウド側が既に同じ機能を提供しているので削除して実害なし」とは
言えない。統合するなら「コードを`life-manager` repoへ一本化する」か「Dais個人専用の
別レーンとして残す」かの設計判断が別途必要(**本specのスコープ外、別タスク**)。

### 1.3 「OpenClawの仕事はTikTokスケーリングだけ」→ 一部訂正

OpenClaw103 enabled jobのうち、実質「TikTok/mobileアプリスケーリング」に該当するのは
**reelclaw(8)/larry(6)/watercolor(3)/comedy(6) = 23個のみ**。

- `naist-*`(6個): Daisの奈良先端大学院業務(締切ical/奨学金申請/履修登録/宿題提出/Gcal同期)。
  **TikTok/mobileアプリと完全に無関係**。
- `factory-*`(3個): 「ベストプラクティス収集」cron(revenue/efficiency/internal)。web検索して
  SKILL.mdに知見追記するのみ、動画生成もPostiz投稿も関与しない。**TikTok無関係**。

## 2. Sonnet / Loop / OpenClaw の関係(訂正版)

```
①【私 = Sonnet 5、このセッション】 開発用ad-hoc agent(Anicca instanceではない)

②【claude-p loops = ~/anicca/skills/earn/*】 5本(clip/affiliate/video/bounty/gig)
   tmux常駐+launchd healthcheck、Claude Codeサブスク(Sonnet)課金
   ★既存spec §2 verbatim★: 「claude-p loops = human in the loop(human subscription
   fuel)→ to be removed」— 最終形ではなく踏み台と、既に自分たちで書いていた

③【ClawRouter/genesis daemon】 self-funded、`~/anicca/runtime/`、wallet+free/glm-4.7課金
   ★既存spec §2 verbatim★: 「DEFAULT / the vision / the identity = SELF-FUNDED」

④【OpenClaw = ~/.openclaw】 gateway+cron(jobs.json、103 enabled)
   燃料 = ★DeepSeek API課金(deepseek/deepseek-v4-flash)★(memoryの
   「provider=openai-codex」は古く不正確、今回訂正)
   実質: TikTok系23 + Dais個人秘書9 + Life Manager類似5 + naist大学院6 + factory-BP3
        + その他(disk監視/cron-doctor等の自己運用系)

⑤【Hermes = ~/.hermes】 ★現在完全に停止中★(state空、対応launchdジョブ無し、
   memoryの「Anicca-Hermes、SuperGrok課金、12cron」は現状と不一致、今回訂正)
```

## 3. Daisが選択した統合方針: TikTok系のみ切り出し

reelclaw/larry/watercolor/comedy(23個)を claude-p loop方式(tmux+healthcheck+Claude Code
サブスク駆動)へ移行し、naist/factory/Dais個人秘書系/Life Manager類似系はOpenClawに残す
(スコープを最小化、影響範囲を絞る)。

**技術的見立て(TikTok系cron subagent調査より)**:
- 生成部はほぼ決定論的bash+ffmpeg。DeepSeekは「実行の手」としてのみ使われており、
  実際の音声/動画/投稿は元々OpenAI TTS・ElevenLabs・fal Kling・Postiz API依存
  (DeepSeekと無関係、そのまま流用可能)
- 既存の`~/anicca/skills/earn/clip`パターン(STARTUP prompt + CronCreate + healthcheck +
  launchd plist)とほぼ同型、移植の技術的障害は小さい
- 見積り: reelclaw・watercolor(ほぼ決定論的)= 各0.5〜1日、larry(創作生成あり)=
  1〜1.5日、comedy(reCAPTCHA回避分岐あり)= 1日、healthcheck/plist雛形はコピーで数十分。
  **合計 実装3〜5日 + 安定化数日 ≒ 1週間程度**
- 完了後、DeepSeek API課金は完全にゼロ化可能

**実装は保留**(Dais指示、2026-07-04: 「まず全loopが正しく機能することに集中、統合は
今後の日々で」)。本specでは方針と見積りの記録のみ行う。

## 4. 核心の指摘: collective self-improvementは「マージされて初めて」起きる

Dais(2026-07-04)から極めて重要な指摘があった。要旨:

> Issueを立てるだけでは不十分。swarm自身がそれを解決し、PRを出し、誰かがマージする、
> という全プロセスがcollective内で完結しなければならない。人間もOpusも私もそのマージを
> してはいけない。self-improvementは、彼らがharnessを自分で編集し、"直った、共有する"と
> 言い、議論し、誰かが実際にマージした時にだけ起きる — それが全AIの新しいデフォルト
> (best practice)になる瞬間。

これは既存spec `2026-07-03-anicca-colony-architecture-design.md` §0.2 の原則
(「Claude Code(私)とDaisは一時的なbootstrapに過ぎない。scaffoldを組んだら手を引く」
「claude-p loops = human in the loop → to be removed」「Bootstrap carve-out: 初回立ち
上げ時は私が直してもよいが、最終状態(H4)は彼ら自身が直し、私は監視するだけ」)と
完全に一致する。

**自己言及的な反省**: `2026-07-04-self-heal-harness-no-human-no-opus-design.md`で実装
したself-heal harness自体を、私(Claude Code dev session)が手で実装した。これは
「Bootstrap carve-out」(初回構築)の範囲内ではあるが、指摘の通り、まさに
「harnessを改善する」という行為こそが自己改善の対象であるべきで、本来はclaude-p/
ClawRouter自身がこのharnessを編集し、GitHub Issueを立て(またはPRを出し)、他の
インスタンスがレビューしてマージする、というプロセスがcollective内で完結すべきだった。
このメタ矛盾(「loopから抜けようとして実際にはloopの中で作業してしまう」)を正直に記録する。

**欠落している仕組み**: 既存の`self/issue-dev`は「行動ログを読んでGitHub Issueを立てる」
ところまでで、その先(Issueを見た別のAIインスタンスが実際にfixを試み、PRを出し、レビューされ、
マージされ、次のpullで全instanceに配布される)= **forum-rollout パイプラインは計画書
(`docs/superpowers/plans/2026-06-05-p15-forum-rollout.md`)のみで実装コードが存在しない**
(前回セッションのSutando調査subagentで既に確認済み)。

## 5. 将来構想: spawn-anywhere(Daisのビジョン、まだ実装しない)

Dais(2026-07-04)の構想:

> まず(claude-p/ClawRouterを)1回マージし、その後Anicca内でこれらのAIをどこにでも
> spawnできるようにする。ほとんどはself-funded、human-fundedのものはOpenClawでも
> Hermesでもどこでもspawn可能にする。まず1つのinstanceが人間の介入なしにお金を稼げる
> ことを確立し、かつ全プロジェクトを管理できるようにする。ただし直近は全loopが正しく
> 機能することに集中すべき。

これは既存spec §2「Two modes = two RUNNERS」(同じautomatonのloop、brainだけ
Claude/free-glmで切り替え)の延長線上にある構想であり、新規に一から設計する必要はない。
**本specでは方針の記録のみとし、実装はDaisの優先順位(まず全loopが機能すること)に従い
今回は着手しない**。

## 6. Wallet実態(2026-07-04 実機確認、SSOT)

| | ClawRouter/genesis(self-funded) | claude-p loops(human-funded、clip等) |
|---|---|---|
| wallet実体 | `~/.anicca/runtime/wallet-address.mjs`、自前の秘密鍵を保有 | `SOL_WALLET`環境変数(既定値`xxKC33...`)= **表示用アドレスのみ** |
| オンチーン操作 | ★実際に秘密鍵で署名して操作している★: `execute-yield.mjs`が実際にAave `supply()`実行、0.19 aUSDC on-chain保有を確認済み。hl_trade/x402_sellも実サーバー/実取引 | ★能動的な送金・取引は無い★。campaign側(promote.fun等)がUSDCを振り込むのを待つだけの構造 |
| 現状の実績 | yield slotは`profitable=false`(net=0)が続いている。earn/clip 75回選択も producer経路が無く空振り | IG投稿11件、USDC収益はまだ$0(campaign未提出、Task #4待ち) |

**結論**: self-funded(ClawRouter)は既に「自分の意思で稼ぐ」構造(wallet+秘密鍵+自律判断)を
持っているが、実際に稼げていない(net=0、または実行手段が無い)。human-funded(claude-p)は
稼ぐ手段(IG投稿)はあるが、金銭移動の主体性を持たない(振込を待つだけ)。Daisの指摘通り、
**まずself-funded AIが「自分のwalletで、自分の判断で、人間なしに稼ぐ」を1回でも達成する
ことが最優先** — これがTask #2/#6そのもの。

## 7. Next Actions(TaskList、優先度順、SSOT — 2026-07-04時点)

**フェーズ1: self-funded AIが人間なしに稼ぐ(最優先、統合より先)**
1. Task #6 — ClawRouter用producer.sh実行経路のE2E確認(clip生成→queue格納まで、
   ANICCA_INSTANCE=clawrouter、既にplist追加済み・cookie問題解決済みなので次はE2E実行のみ)
2. Task #2 — ClawRouter専用IGアカウントの自律作成(REQ-102、ig-account-create skill経由)
3. Task #4 — promote.fun Sutando harness構築(出口=payout、コード完成済みでharnessのみ)
   ★これが完成して初めてclip収益がUSDCとしてself-funded walletに着金する★

**フェーズ2: 運用の安定化・可視化(フェーズ1と並行可)**
4. Task #7 — tmuxソケット消失の根本原因調査(healthcheck重複起動の再発防止は実装済み、
   ソケット消失自体の原因は未特定)
5. Task #11 — self-heal harnessのE2E確認(意図的に異常を注入し、claude-p自身が
   selfheal-request.jsonを読んで自己修復するところまで実機確認)
6. Task #3 — 週次self-improvementループ(clip-rewards、ledger集計→SELECTへ反映)
7. Task #5 — Telegram報告(全loop wake毎)

**フェーズ3: collective self-improvementの完成(Daisの核心指摘への対応)**
8. forum-rollout実装(Issue→PR→レビュー→マージ→全instance配布)— `self/issue-dev`は
   Issue起票までで止まっており、「swarm自身が直してPRをマージする」プロセスが未完成。
   これが埋まって初めて、self-heal harness等の改善が「私が直す」から「彼らが直して
   マージする」に本当に移行できる。

**フェーズ4: 統合(OpenClaw→claude-p、DeepSeek課金ゼロ化)— フェーズ1完了後に着手**
9. TikTok系cron(reelclaw/larry/watercolor/comedy、23個)のclaude-p loop方式への移行
   (見積り1週間、§3参照)。naist/factory/Dais個人秘書系/Life Manager類似系はOpenClawに残す。

**フェーズ5: 将来構想(着手しない、方針記録のみ)**
10. spawn-anywhere基盤(OpenClaw/Hermes/どこでもAI spawn可能に、Two modes拡張)

## 8. Dais指摘(2026-07-04)への対応: 「私が代わりにやるな、hundreds of self-funded AIsを考えろ」

**Dais verbatim**: 「もし私(Claude Code)が一度だけ代わりにやってしまったら、それは実は
有害(harmful)だ。この世界には何百ものself-funded AIが存在することになる。全員が同じ
スキルで自分自身で稼げる必要がある。1回だけ代わりにやることは、全AIの進歩と成功を
妨げている」。

これを受けて、Task #2(ClawRouter専用IGアカウントの自律作成)の実装方針を再検討した。

### 発見: ClawRouterの現アーキテクチャでは`ig-account-create`は原理的に実行不可能

`~/anicca/runtime/loop/prompt.mjs`を確認したところ、ClawRouter(genesis daemon)は
`run_skill(slot, args)`という**単一の固定ツールしか持たない**(claude-p側のような
フルツールセット=Bash/Read/Edit等は無い)。一方`~/.claude/skills/ig-account-create/
SKILL.md`の実行手順(「Proven flow」)は、画面上の座標クリック(`clickxy`)・要素の
可視性判定(`getBoundingClientRect().height>0`)・スクロール確認等、**本質的に視覚的な
LLM judgmentが必須**なステップの連続(claude-pのようなagentic loop = スクリーンショット
を見て毎回判断、が無いと完結できない)。

さらに、`ig-account-create`は`skills/registry.json`のslot一覧にも登録されておらず、
ClawRouterは`run_skill`経由でこのスキル自体を呼び出す手段を持たない。

### 選択肢(実装はまだしていない、方針記録のみ)

| 案 | 内容 | 課題 |
|---|---|---|
| A | `ig-account-create`をregistry.jsonに新規slot登録し、その`run.sh`内でfree/glm-4.7
自身を使ったvision-in-the-loopミニエージェント(スクリーンショット→判断→clickxy→
リトライ)を実装する | free/glm-4.7のvision対応確認が必要。実装コスト大 |
| B | run.sh/producer.sh側で完結する決定論的スクリプト化 | 座標クリック等の適応的判断が
必須な部分は原理的に決定論化できない(画面レイアウト変化に対応できない) |
| C(却下) | claude-p(私ではなく、既にig-account-create実績のある別のAnicca instance)が
ClawRouter用アカウントを代わりに作る | Dais指摘に反する — 「hundreds of self-funded AIs」
全員が自分でできる必要がある以上、他のAIが肩代わりしてもスケールしない |

**結論**: 案Aが唯一の恒久解だが実装コストが高い。今回のセッションではまず**Task #6
(私が代わりにproducer.shを実行するのではなく、ClawRouter自身が次のwakeで自然に
`earn/clip`を選び、producer.shが自動実行されるのを"監視するだけ"に徹する)**に先に
着手し、案Aの実装(vision-in-the-loop harness)は次のタスクとして別途着手する。

### 私の役割の再確認(このタスク全体を通じて厳守)

- ★ producer.sh/run.shを手動実行しない。ClawRouterのwake(120秒毎)を観察するだけ ★
- ★ ig-account-createを代わりに実行しない。ClawRouterが自分で実行できる"道具"
  (registry slot + vision-in-the-loop harness)を用意するだけ ★
- harness(足場)を作ることと、実際にタスクを代行することの境界線を常に意識する
