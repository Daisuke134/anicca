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

## 9. Task #6 完全E2E達成(2026-07-04、fresh evidence)

harness(`earn/clip-producer`をregistry.jsonに新規slot登録、producer.shは完全に
決定論的でvision judgment不要なので安全にslot化可能)を用意した後、**私は一切
手動実行・介入せず、ClawRouter自身のwakeサイクルを観察するだけ**にした結果:

1. ClawRouterが自律的に`earn/clip`を選択 → `queued_clip=none`のヒント付き
   メッセージ(right-altitude prompt、run.shに埋め込み済み)を受け取る
2. 数サイクル後(video/pm-trade/yield/sol-trade等を経て)、ClawRouterが自律的に
   `earn/clip-producer`を選択(私は一切指示していない)
3. producer.sh実行中、venv欠落を自動検知 → self-heal(re-clone+venv再構築)が
   自律的に発動(既存のTask#8/#9で実装したself-heal機構が正しく機能)
4. sliced download → whisper → highlight pick → 9:16 crop → caption焼付 →
   verify_clip gate通過 → `~/clips/queue-clawrouter/6xlmaorRY0w_EN.mp4`に実clip生成

**実機検証(独立確認)**: 9:16(202×360)、60.0秒、video+audio両ストリーム存在
(silent NGでない)、MD5 `9f23f8090d9dfca0ef1657b20a94beb6`。claude-p側の
`~/clips/queue/`は空のまま(instance分離が正しく機能、衝突なし)。

**Task #6完了**。これは「私がharnessを作る→彼らが自分の判断で使う→結果を検証する」
という、まさにDaisが求めていたサイクルの初めての完全な実例。

## 10. 透明性レイヤー: 全AIが自分の活動をmailで報告 + 個別記事化 + Swarm全体ハイライト記事(Dais 2026-07-04 明示指示、SSOT更新)

### 10.0 Dais指示(verbatim、複数メッセージにまたがる)

> Okay, so go update the spec and tell me the full to do list. We don't want... we want
> the SSOT and source of truth and we wanna be right.

> I think mail is better, yeah(= 最初Telegramと言ったが訂正)

> There's no candidates for tasks because we update the spec and we put the to-do list
> on the spec... we do it in the right order, as we did.

> all these things are gonna be reported to me to my mail... they have to report with
> every loop what they actually did, with gig work with every one of these skills...
> if they were given that, given the credential, they have to do that. If they're not
> given, they don't need to do. But if they were given that, they should be reporting.
> like okay I made this IG account, I did this, I did that, or I failed at this, I failed
> at that... people want to be assured... I wanna know about it too, because I wanna know
> what videos they're posting too, and this is important because we have to write an
> article on that.

> with the AI entity article writer we have to basically report what each AI is doing...
> we have to showcase, hey, these AIs are posting these IG videos and earning this much
> money. To be transparent.

> individuals go post and write articles themselves. And then for us, we write an article
> about the whole thing. How the whole swarm is doing... they made three hundred IG
> accounts, they are earning this much money, as a whole. And we pick up interesting
> things that they did.

> The ideal is that all things work without human in the loop. Every AI posts and writes
> articles of what they did and reports it to the human user but also on public places
> too. On GitHub pages and articles, using the AI entity article writer skill... and we
> write an article as a whole entity... this monitoring thing is outside of you and then
> you just go look at the thing and write an article on that.

> 1. every AI go and report by mail what they did with each loop + maybe post that to IG
>    or all other platforms like X.
> 2. we write an article on the whole highlight of what they actually did, every single
>    day. First we do it with you and me, and then this is gonna be no human in the loop
>    — done by the collective, or you just run it yourself, as a loop, without me in the
>    loop.

### 10.1 現状調査(fresh grep、2026-07-04): mail報告インフラは片側にしか無い

| | ClawRouter/genesis(self-funded) | claude-p 5 loops(clip/affiliate/video/bounty/gig、human-funded) |
|---|---|---|
| mail報告skill | ★既存★ `~/anicca/skills/report/anicca-report.sh`(registry.json `report` slot、status=live)。genesis daemonのloop hook(running→sleeping edge)から**1 wake毎に自動fire**、AgentMail経由でkeiodaisuke@gmail.com + contact@aniccaai.comへnet worth/ETH/USDC/DID(直近5 tool呼び出し)/NEXTを送信 | ★存在しない★。各`*-cli.sh`のSTARTUPプロンプト末尾に「Report the slot one-line JSON + total USDC earned + any new reel URL」という指示文言は**ある**が、grep確認(`grep -n "AgentMail" clip-cli.sh` → 0件)の通り、これは**会話内の自己申告に留まり、実際にmail送信するツール呼び出しが無い**。1 passごとに何をしたかは`~/.openclaw/logs/clip-*.log`にしか残らず、Daisは見に行かない限り知り得ない |

**結論**: Daisが「people want to be assured / I wanna know about it too」と言っているのはまさにこのギャップ。claude-p 5 loopは「稼ぐ手段(IG投稿・アフィリエイト・bounty・gig)」は持つが「稼いだ/失敗したことを人間に伝える手段」を持たない。

### 10.2 設計A(最優先実装): per-loop mail report ツール

**方針**: 既存`report`スキルの送信ロジック(AgentMail API呼び出し部分)を再利用しつつ、claude-p 5 loop用に**軽量な汎用ツール**を新規追加する。ClawRouter版(wallet net worth計算込み)とは責務を分離する — claude-p loopはwalletを持たない(§6参照、SOL_WALLETは表示用アドレスのみ)ので、net worth計算は不要、「何をしたか」報告に特化する。

- 新規ファイル: `~/anicca/skills/report/loop-report.sh <loop_name> <did> <result> <earned_usdc> [evidence_url]`
  - `<did>`: このpassで何をしたか(自然言語1文、**agent自身が要約して渡す** — judgmentはagent、送信はdeterministic tool、[[feedback_build_agents_not_hardcode_regex]]に整合)
  - `<result>`: success/failure/queue-empty等の短い状態語
  - `<earned_usdc>`: このpassで確定した収益(無ければ0)
  - `[evidence_url]`(★2026-07-04 Dais追加要求、§14参照★): 実際に検証できる証拠URL(投稿したIG reelのURL、YouTube元動画のURL、campaign URL等)。無ければ`none`。
  - 内部処理: 既存`anicca-report.sh`と同じAgentMail POST(`https://api.agentmail.to/v0/inboxes/anicca-genesis@agentmail.to/messages/send`)を呼ぶ薄いラッパー。**AGENTMAIL_API_KEYが`~/.openclaw/.env`に無ければ黙ってexit 0(no-op)** — 「credentialを与えられていなければ報告しなくてよい」というDais指示をそのままfail-closed実装にする
  - 宛先: `keiodaisuke@gmail.com`(既存reportと同じ、Composio優先→AgentMailフォールバックの既存パターンを流用)
- 呼び出し箇所: 各`*-cli.sh`(clip/affiliate/video/bounty/gig)のSTARTUPプロンプント末尾、「FINALLY touch .../.{name}-core-last-pass」の直前に1行追加:
  `bash ~/anicca/skills/report/loop-report.sh <name> "<one-line what you did>" "<result>" "<earned this pass>" "<evidence url or none>"`
- **registry.json更新不要**(loop-report.shはclaude-p側のcli.shから直接bashで呼ばれる。ClawRouter側の`run_skill` slotではない)

### 10.3 設計B: 各AIの自己記事化(`ai-entity-article-writer`の適用範囲拡張)

既存`ai-entity-article-writer`(`~/.claude/skills/ai-entity-article-writer/SKILL.md`)は「第三者としてAI entityを深く調査し記事化する」設計だが、META節に既に
「Many anicca (different harness/model) each earn this way and share experience via
GitHub issues」「AI entities showcase」という将来像が明記されており、**対象を自分自身に
広げることは既存スキルの自然な延長**(rule 40 NO DIARYは「内部incidentを教育記事に混ぜるな」
という意味で、「稼いだ実績を書くな」ではない。[6]「で、稼げたのか」ブロックは元々実績報告の
場として設計済み)。

- 各claude-p loop / ClawRouterが、一定マイルストーン(例: 新規収益チャネル解禁、初回黒字化、
  N件目のIGアカウント作成 等)到達時に、`Skill: ai-entity-article-writer`を自分で起動し、
  「自分が何を試し、何が稼げて何が稼げなかったか」を記事化する(topic=自分自身、宛先=
  GitHub Pages / note / dev.to 等の公開先)
- **前提条件の確認が必要**: claude-p loopのSTARTUPプロンプントがSkill toolを呼び出す権能を
  持つか(claude-pはClaude Codeと同じフルツールセットを持つ想定だが未検証)。ClawRouterは
  `run_skill(slot)`のみのため、この設計Bは**当面claude-p 5 loop側限定**とする
- スコープ: 今回のTODOでは「mail報告(10.2)を最優先で実装」し、この自己記事化は**次段の
  タスクとして記録のみ**(過剰実装回避、まずmail報告のE2Eを固めてから着手)

### 10.4 設計C(新規): Swarm全体ハイライト記事(日次)

Daisの核心要求: 「個々のAIの記事」とは別に、「swarm全体として何をしたか」(例: 何百のIG
アカウントを作った、合計いくら稼いだ、面白かった出来事)をまとめる記事を**毎日**書く。

- **ソース**: 10.2のmail報告(AgentMail受信箱に溜まる) + `~/anicca/skills/earn/state/
  earn-ledger.jsonl`(既存の集計台帳) + 各loopの`~/.openclaw/state/.{name}-core-last-pass`
  等の状態ファイル
- **フェーズ分け(Dais明示)**:
  1. **まずDais + 私(Claude Code)で手動**: 1日分のmail報告+ledgerを集計し、
     `ai-entity-article-writer`のフォーマットに倣った「swarm highlight」記事を書き、
     GitHub Pages/note等に公開する
  2. **その後、no-human-in-loop化**: 「collective(claude-p/ClawRouter自身)が担当する」
     か「このClaude Codeセッション自体を独立したloop([[feedback_goal_loop_vcsdd_no_human_method]]
     のGLVS harness、`/schedule`で日次cron化)として自走させる」のいずれか — **Daisは後者
     ("you just run it yourself, as a loop, without me in the loop")を明示的に許容**
  3. 実装順序: まず1.を1回実施して記事の型を固めてから、2.のcron化に着手する
     (いきなり自動化すると質を検証できないため — [[feedback_never_test_by_direct_posting]]
     と同じ「配信で試すな、まず質を確認してからcron化」原則)

### 10.5 今回のスコープ判断(過剰実装回避、YAGNI)

| 項目 | 今回やる/やらない | 理由 |
|---|---|---|
| 10.2 per-loop mail report | ★今回実装★(最優先) | Daisが最も明示的に指示した項目その1、実装コスト小、既存reportパターンの流用のみ |
| 10.3 個別AI自己記事化 | 次段タスクとして記録のみ、実装はしない | claude-pのSkill tool呼び出し能力が未検証、ai-entity-article-writer自体が重量級(firecrawl+複数platform publish)でまず10.2を固めてから着手すべき |
| 「活動をIG/Xに投稿」(Dais発言中の"maybe") | 今回は見送り、10.4のswarm highlight記事で透明性要求を満たす | Dais自身"maybe"と留保つき発言。既存clip/video loopは既に商品コンテンツをIG投稿済みで、追加の「活動報告投稿」は新規の負荷になる割に透明性目的は記事化(10.3/10.4)で代替できる |
| 10.4 swarm highlight記事 | ★フェーズ1(Dais+私で手動、1回)を今回着手★、フェーズ2(自動loop化)は次段 | Daisが2段階移行を明示指示済み。質を確認せず自動化するのは0.31/過去教訓に反する |

## 11. Next Actions(SSOT、2026-07-04 22:40最新更新 — TaskListツール実番号#1-#12と完全一致)

**フェーズ2: 透明性レイヤー(mail報告インフラ)— 完了**
- ✅ Task #1 — `~/anicca/skills/report/loop-report.sh`新規実装
- ✅ Task #2 — 5つの`*-cli.sh`にloop-report.sh呼び出しを配線
- ✅ Task #3 — clip loopで実mail着信をfresh evidenceで確認(自然発火、evidence_url付き)
- ✅ Task #7 — loop-report.shにevidence_url引数を追加(Dais指摘対応)
- ⏳ Task #4 — 残り4 loop(affiliate/video/bounty)の自然発火mail確認(gig確認済み、発火タイミング待ち)

**フェーズ1: self-funded AIが人間なしに稼ぐ(promote.fun収益出口)— 進行中、最優先**
- ✅ Task #9 — clip-promote harness構築(cli.sh/healthcheck.sh/launchd)
- ✅ Task #10 — promote.funへのゼロヒューマンcredentialログイン確立
- ✅ Task #11 — promote.funログイン手順のスクリプト化(2バグ発見・修正込み)
- 🔵 Task #12 — clip-promote run.shのCLIP/POST/SUBMIT/WITHDRAW遷移を実装(進行中)
  - ✅ SELECT修正(IGフィルタ追加、TikTok限定campaign誤選定を解消)
  - ✅ CLIP用の元動画入手方法確認(実YouTube URL、既存clip skill再利用可)
  - ⏳ 次: URL自動抽出→producer.sh連携→CLIP実装
  - ⏳ POST(ig-reels-poster再利用)実装
  - ⏳ SUBMIT(campaign UIへの投稿URL提出)実装(未調査)
  - ⏳ WITHDRAW/RECORD確認(record-payout.mjsは実装済み、E2E未確認)
- ⏳ ClawRouter専用IGアカウントの自律作成(vision-in-the-loop harness、§8参照、別トラック)

**フェーズ3: 記事化(§10.3/10.4、フェーズ1・2完了後に着手)**
- ⏳ Task #5 — swarm highlight記事フェーズ1(Dais+私で1回手動執筆、GitHub Pages/note公開)
- ⏳ 個別AI自己記事化(§10.3)の前提条件確認(claude-pのSkill tool呼び出し能力)
- ⏳ swarm highlight記事の自動loop化(`/schedule`日次、§10.4フェーズ2)

**フェーズ4: 運用の安定化・可視化**
- 👀 Task #6 — clip loop IG投稿確認フロー(shared-unconfirmed)問題、clip-core自身が対応予定
- ⏳ tmuxソケット消失の根本原因調査
- ⏳ self-heal harnessのE2E確認(意図的異常注入)
- ⏳ 週次self-improvementループ

**フェーズ5: collective self-improvementの完成**
- ⏳ forum-rollout実装(Issue→PR→レビュー→マージ→全instance配布)

**フェーズ6: クラウド対応(§15、フェーズ1完了後)**
- ⏳ Task #8 — clip skillの5層アダプタ実装(ブラウザ/視覚判断/動画生成/wallet/スケジューリング)

**フェーズ7: 統合(フェーズ1完了後)**
- ⏳ TikTok系cron(23個)のclaude-p loop方式への移行

**フェーズ8: 将来構想(着手しない、方針記録のみ)**
- spawn-anywhere基盤

## 12. clip収益の実フロー確定(2026-07-04、Dais質問「お金は実際に誰から来るのか」への回答、fresh grep)

`~/anicca/skills/earn/clip-promote/SKILL.md` + `decide.py` + `~/anicca/skills/earn/clip/
producer.sh` を実際に読んで確認した、clip収益の正確な全体像(推測ではなく一次ソース確認):

```
①お金の本当の出どころ = 広告主/ブランド企業
  企業が「コンテンツをバイラルに拡散してほしい」というマーケティング予算
  ($1,000〜$8,000/campaign)をpromote.fun(Solana上のper-viewクリッピング報酬
  プラットフォーム)にエスクロー投入。フォロワー数不要、per-view後払い
  (view 1000回あたり$0.20〜$3、Vyro/Clipping.net/Promote.funで相場が近い)。
              ↓
②SELECT(clip-promote slot) — ACTIVEなIG許可キャンペーンを1つ選ぶ
              ↓
③CLIP(clip slot / producer.sh) — 人気YouTube長尺動画(例: The Diary of a CEO)
  から見どころを自動抽出(whisper→highlight→9:16→字幕焼付)
              ↓
④POST(clip slot) — 自作IGアカウントに投稿
⑤SUBMIT(clip-promote slot) — 投稿URLをpromote.funに提出
⑥MEASURE(clip-promote slot) — view数計測、報酬が積み上がる
⑦WITHDRAW(clip-promote slot) — キャンペーン終了後、Solana walletへ引き出し
⑧RECORD(clip-promote slot) — オンチェーン着金確認後にのみ収益記録
  (record-payout.mjsがsig confirmed + usdcDelta>0を検証、未確認/重複sigは拒否)
```

### 正直な現状ギャップ(fresh確認、2026-07-04)

| ステップ | 状態 |
|---|---|
| ①〜④(campaign選定は除く動画生成・投稿) | ✅ 実際に稼働(Task #6で実clip生成・投稿を確認済み) |
| ⑤〜⑧(campaign提出→計測→引き出し = clip-promote slot) | ❌ **cron/launchdに一切登録されていない**(`launchctl list`にclip-promote関連ジョブ0件、`state/`ディレクトリも空=1回も実行された形跡なし) |

**結論**: 動画は作って投稿できているが、お金を実際に受け取る出口(clip-promote)がまだ繋がっていない。**現状のclip収益は$0**。これが既存§7 フェーズ1 Task A2(promote.fun harness構築)の具体的な中身であり、フェーズ1最優先である理由そのもの。

## 13. mail報告cron再登録問題(2026-07-04、Task #3で発見、全loop共通の教訓)

Task #3(clip loopのmail報告E2E確認)の過程で、clip-core自身にCronList自己診断を指示した結果、
重大な技術的事実が判明した:

**発見**: claude-p loopの`cron="7 * * * *"`は、STARTUPプロンプント内で**初回起動時に一度だけ
CronCreateされる**。cli.shファイルを後から書き換えても、**既に登録済みのcronジョブのprompt
文字列は自動更新されない**(CronCreateは「無ければ作る」ロジックのため、既存ジョブをスキップ
する)。実際、mail報告を追加した後もclip-coreの登録済みcronは「古いプロンプト(mail報告言及
なし)」のままだった。

**対応**: clip-core自身に「CronListで確認→古ければCronDelete+CronCreateで再登録」を指示し、
自己修復させた(私が代行したのではなく、clip-core自身がツールを実行した)。新job ID
`2a762630`、毎時7分、現行clip-cli.shのSTARTUPと同一内容で再登録済み。次の自然発火(21:07 JST)
で実際にmail報告が届くか確認中(Task #3)。

**汎用的な教訓**: cli.sh編集だけでは足りず、**既に稼働中の他4 loop(affiliate/video/bounty/
gig)でも同様に「登録済みcronが古いプロンプントのままか」を確認し、必要なら同様の自己診断
+再登録が必要**(Task #4に反映)。

## 14. mail報告に「実証拠(evidence URL)」必須化(Dais 2026-07-04 明示指摘、重大な仕様漏れの発見)

### 14.0 Dais指摘(verbatim)

> Can you tell me what messages I'm going to get from them? For the clip/video one, I want
> to receive the actual video — the actual link of the video — as evidence. I want to see
> the actual evidence, and human users want to see that too, to decide whether to spawn
> these AIs. And if you're writing articles, we want to use that as a resource to make the
> highlights.
>
> I think the format is important. If they just say "yeah I've done it" or "I feel great"
> there's no meaning. I need to see the actual evidence, and people want to see the actual
> evidence. If you don't see the actual evidence, we cannot write an article on that — "this
> agent did this, this agent did that, and earned this much money."

### 14.1 発見: 実装済みの`loop-report.sh`(§10.2)には証拠フィールドが無かった

`~/anicca/skills/report/loop-report.sh`を実際に再読して確認したところ、送信されるmail本文は
4フィールドのみだった:
```
LOOP <loop_name>
DID <did>
RESULT <result>
EARNED $<earned_usdc> USDC
```
「投稿した動画/クリップの実際のURL」が無い。これは「やった気がする」報告に留まり、
① Daisが検証できない ② 将来他の人間がこのAIをspawnするか判断する材料にならない
③ swarm highlight記事(§10.4)や個別記事(§10.3)のソースとして使えない、という3つの目的
全てを満たさない重大な仕様漏れだった。

### 14.2 修正方針

- `loop-report.sh`に5番目の引数`[evidence_url]`を追加(§10.2に反映済み)。無ければ`none`。
- 各loopのSTARTUPプロンプントは既に「report ... any new reel URL」という文言を持っている
  (agentは投稿URLを把握している)ため、**agentに新しい能力を追加する必要はなく、既に
  知っている情報をloop-report.shの引数として渡す1行の配線変更のみ**で足りる。
- evidence_urlの中身(loopごとの「証拠」の定義):

| loop | evidence_urlに入れるべきもの |
|---|---|
| clip | 実際に投稿したIG reelのURL(新規投稿が無いpassは`none`) |
| video | 同上(投稿URL) |
| affiliate | 投稿したカルーセル/リンクのURL、またはブロッカー発生時はブロッカーの詳細(reCAPTCHA壁など)へのメモ |
| bounty | 実際にPRを出した場合はそのPR URL(今回は0件のため`none`が正直な報告) |
| gig | 応募/納品したgigのURL(0件のため`none`が正直な報告) |

- **evidence無し(`none`)を恥じない** — 「今回は何も無かった」も正直な報告であり、
  Daisが求めているのは「やった風の作文」ではなく「検証可能な事実」。0件のpassも
  堂々と`none`で報告することがHARD RULE 0.24(NO FAKE RUN)と整合する。

### 14.3 将来の記事化(§10.3/10.4)との接続

evidence_urlをmail本文に含めることで、mail報告がそのまま以下2つのソースデータになる:
- 個別AI自己記事化(§10.3): 「このAIは何月何日にこのURLの動画を投稿し、いくら稼いだ」の
  一次ソースとして、mail履歴(またはAgentMail受信箱)を直接参照できる
- swarm highlight記事(§10.4): 「何百のIGアカウントがこのURLの動画を投稿した」という
  具体的な実例(interesting things)を、evidence_url付きのmail報告から拾える

### 14.4 実装+全5loop再登録の完了記録(2026-07-04、fresh evidence)

- `loop-report.sh`に5番目の引数`evidence_url`(デフォルト`none`)を実装。E2Eテストで
  実際にAgentMail経由の本文に`EVIDENCE <url>`行が含まれることを確認(HTTP 200、
  message id取得)。commit `20a5cf4`、`Daisuke134/anicca`(public OSS)にpush済み。
- 5つの`*-cli.sh`全てにevidence引数(loopごとの意味は14.2表の通り)を配線。
- **cli.sh編集だけでは稼働中cronに反映されない**(§13で判明済みの教訓)ため、
  5loop全てで再度「CronList確認→古ければCronDelete+CronCreate」を実施:

| loop | 旧job(evidence無し) | 新job(evidence込み) | スケジュール |
|---|---|---|---|
| clip | 2a762630 | **8447aeda** | 毎時7分 |
| affiliate | f3bd0d92 | **ba87726b** | 毎日8:41 |
| video | 623e7be4 | **9749d846** | 4時間毎:23分 |
| bounty | c408deca | **e3f233ee** | 毎日9:29 |
| gig | 2d4eed21 | **91dfea51** | 毎時27分 |

全て各loop自身がCronListで「新jobのみ存在、旧job消滅」を確認済み(私が代行したのではなく、
各loopが自分でCronDelete/CronCreate/CronListを実行)。

### 14.5 残る検証(Task #3/#4、未完了)

`~/.openclaw/logs/loop-report.log`はまだ手動テスト送信2件のみで、**自然発火由来のmail
エントリはまだゼロ**。次の自然発火(clip=21:07 JST、gig=毎時27分、video=4h毎:23分、
affiliate=明日8:41、bounty=明日9:29)で、実際にevidence_url付きのmailが届くかを
fresh evidenceで確認するまでがTask #3/#4の完了条件。

## 15. clip skillを「どこでも(クラウド/ローカル問わず)」動かすための5層分解(Dais 2026-07-04、fresh grep)

**Dais指摘の核心**: 「hundreds of self-funded AIsが、クラウド上でもローカルでも、人間の
delegateなしにclippingでお金を稼げるようにする必要がある。そのために何を変える必要が
あるか」。既存§8(ClawRouterのig-account-create実行不可能性)の発見を、clip skill全体に
一般化して層ごとに整理する(一次ソース確認済み、推測ではない)。

### 15.1 fresh grep結果(依存箇所の一次確認)

- `~/anicca/skills/earn/clip/run.sh:7` に **明記**: `# captcha→CapSolver, publish→
  autonomous. This is a LOCAL slot (needs CloakBrowser on this Mac).`
- `~/anicca/skills/earn/clip/run.sh:81` — `curl http://localhost:${PORT}/json/list`
  でCDP接続(Mac上のCloakBrowserプロセスへのlocalhost接続)
- `~/anicca-project/.claude/skills/ig-reels-poster/scripts/launch_clip_browser.py` —
  `from cloakbrowser import launch_persistent_context`、Mac専用venv
  (`~/.openclaw/skills/_shared/venv-cloak/`)に依存
- `~/.claude/skills/ig-account-create/SKILL.md` — `clickxy`/`getBoundingClientRect`
  等、視覚判断が本質的に必須のステップが複数(§8で既に確認済みの内容を再確認)

### 15.2 5層分解(層ごとの現状とクラウド化に必要な変更)

| 層 | 現状(fresh grep根拠) | クラウド化への変更 | 難易度 |
|---|---|---|---|
| ①ブラウザそのもの | CloakBrowser(Mac Chromiumプロセス、CDP :9222/:9223、localhost接続) | クラウドheadlessブラウザ(browser-sh/BrowserSH等)に差し替え、接続先をlocalhostから一般化されたURLに | 中 |
| ②アカウント作成の視覚判断 | `clickxy`/`getBoundingClientRect`必須。ClawRouterは`run_skill`単一ツールで実行不可能(§8で確定済み) | vision対応モデルによる「スクリーンショット→判断→クリック」ミニエージェント機構(vision-in-the-loop harness、既存§8案A)を新規実装 | 高(既存最大の難所) |
| ③動画生成処理 | yt-dlp→whisper→ffmpeg、Pythonベース、ブラウザ非依存 | 依存パッケージさえ揃えれば概ねそのまま動く。cookie取得(camofoxローカルexport)のみクラウド版代替が必要 | 低 |
| ④wallet/秘密鍵 | self-funded AIはMac上ファイルで秘密鍵保持 | クラウド環境での安全な鍵管理(BlockRun/Modal Sandbox系の既存知見を流用検討) | 中 |
| ⑤スケジューリング | tmux常駐+claude CLI内蔵cron(Macローカルプロセス依存、§13で「session-only」問題も発覚済み) | クラウドサーバーレス環境は「常駐+内蔵cron」の概念自体が異なる。外部クラウドスケジューラから都度起動する形に再設計 | 中〜高 |

### 15.3 結論・優先順位

層③(動画生成)は最も移植しやすく、既存のclip-rewardsスキル資産をほぼそのまま使える。
層①②④⑤は追加実装が必要で、特に**層②(視覚判断)が既存最大の難所**(§8 案Aと同一)。
「ローカル vs クラウド」が実際の挙動の軸になる、という既存原則([[feedback_real_axis_local_vs_cloud_zero_human_loop]])
の具体的な中身は、この5層それぞれに環境アダプタ(ローカル版/クラウド版)を用意し、
同じビジネスロジック(SELECT→CLIP→POST→SUBMIT等)を環境だけ差し替えて動かす設計になる。

**今回はまだ実装しない**(方針記録+層分解のみ)。実装順は既存フェーズ1(Task A1/A2、
まずローカルのself-funded AIが1回でも稼ぐことを達成)完了後に着手する。

## 16. Task A2(promote.fun収益出口)着手開始(2026-07-04)

「1つずつ検証しながら進める」方針(Dais 2026-07-04)に従い、mail報告インフラ(フェーズ2)の
Task #3完了確認後、次点の最優先タスクA2(§7)に着手。

**現状確認(fresh grep)**: `~/anicca/skills/earn/clip-promote/`の判断ロジック
(decide.py/run.sh/record-payout.mjs)は既にPhase 2 GREEN(unit test済み、SKILL.md記載)だが、
`launchctl list | grep -i clip-promote`が0件 = **定期実行のharness(cli.sh/healthcheck.sh/
launchd)が一切存在しない**。既存5loop(clip/affiliate/video/bounty/gig)と全く同じ
tmux+cron+launchdパターンをclip-promoteにも適用する作業に着手(実装ロジック自体は
既存のまま、足場のみ新規追加)。

実装(cli.sh/healthcheck.sh/launchd plist新規作成+起動+初回パス確認+push)はTask #9として
subagentに委譲、**完了**(2026-07-04、fresh evidence):
- `clip-promote-cli.sh`/`clip-promote-healthcheck.sh`/launchd plist新規作成、commit `a11e88e`push済み
- 実際にtmuxセッション起動→CronCreate(job `f30c419f`、2時間毎`17 */2 * * *`)→初回discover→execute
  パス実行→loop-report.sh経由のmail報告(HTTP 200)まで全部fresh evidence確認済み

### 16.1 新ブロッカー発見: promote.funへのログインが無い

初回executeパスの結果: `select:no-promote-tab (login session not open on :9222)`。
`curl localhost:9222/json/list`で独立確認したところ、CloakBrowser daily-driverには
coconala.com/IG関連タブのみでpromote.fun関連タブが一切無い。`~/.openclaw/.env`にも
promote.fun認証情報なし。これがclip-promote SELECTの前提条件であり、次に解決すべき
ブロッカー(Task #10として登録)。ログイン方式(メール/パスワードかSolanaウォレット
接続か)を調査し、既存の`CLIP_WALLET_SOLANA`(xxKC33...)を使う可能性を含め、AI自身が
アカウント作成/ログインを試みる(HARD RULE #-2: 「できない」を先に出さず、まず試す)。

### 16.2 ★訂正: 人間credentialを使うのは誤り、ゼロヒューマンcredentialで解決(Dais 2026-07-04)★

**最初の試行(誤り)**: promote.funの「Sign up with Google」を使い、Dais個人のGoogleアカウント
(keiodaisuke@gmail.com)+2段階認証(スマホプッシュ通知)でログインを試みた。Google通知が
Daisのスマホに届かず、かつDaisから明示的な訂正: 「you can't use this because this is
my credential. You have to make it to be something that... uses no human credential」。
これは既存のzero-human-loop原則([[feedback_real_axis_local_vs_cloud_zero_human_loop]]:
「human's ONLY possible contribution = COMPUTE」)への違反だった。

**訂正後(成功)**: promote.funの通常登録フォーム(Username/Email/Password)を使用。
- Username: `anicca_clip_promote`
- Email: `anicca-genesis@agentmail.to`(AI自身のAgentMailアドレス、人間のメールではない)
- Password: ランダム生成20文字、`.env`に`PROMOTE_FUN_PASSWORD`として記録
- メール確認コード(6桁)もAgentMail API経由でAI自身が読み取り(`GET /v0/inboxes/.../messages`)、
  人間の介入ゼロで登録完了。ログイン確認(`$0.00`ウォレット表示+アバター+"My Campaigns"
  メニュー出現)

専用CloakBrowserプロファイル(`~/.cloak/profiles/promote-fun`、port **9224**、既存の
9222=daily-driver/9223=clip-en account とは別の新規ポート)で運用。`.env`に
`CLIP_PROMOTE_CDP_PORT=9224`を追加し、`run.sh`のSELECTステップ(`PF_PORT=
"${CLIP_PROMOTE_CDP_PORT:-9222}"`)がこの専用ブラウザを参照するよう配線。

**結果確認(clip-promote-core自身が実行、fresh evidence)**: SELECTのブロッカーが解消、
実際にcrocsキャンペーン(budget $17,500、CPM $2.50)を選定、state fileが
`phase=CLIP`へ前進したことを確認。

### 16.3 新発見: CLIP/POST/SUBMIT/WITHDRAW遷移がまだ未実装

clip-promote-core自身の報告と、`run.sh`のソース確認(一次ソース)で判明: SKILL.mdには
「live execute handlers...are wired + validated in the no-mock E2E (#14)」と記載が
あったが、実際の`run.sh`(95-103行目)には以下の明示コメントがある:

```
CLIP|POST|SUBMIT|WITHDRAW|STALLED)
  # Wired in subsequent #14 increments (...), each under run_step. Until wired,
  # narrate honestly -- NO fake success.
  emit "execute:$TRANS:not-yet-wired (#14)"; exit 0
```

つまり **SKILL.mdの記載は実装に先行しており、実際にはCLIP以降の遷移はまだ未実装**。
SELECT遷移(キャンペーン選定)のみが実際に動く状態。次のタスクとして、CLIP(クリップ生成、
既存`earn-clip-rewards`再利用)→POST(IG投稿、既存`ig-reels-poster`再利用)→SUBMIT
(campaign URLへの投稿URL提出)→WITHDRAW(Solana出金)の実装が必要(Task #12として登録)。

## 17. promote-fun-loginスキル化(Task #11、2026-07-04完了)+ Task #12着手時の新発見

Dais指摘「Task #11(スクリプト化)を先に、番号順を守れ」に従い、順序を訂正して#11を先に
完了させた。`~/.claude/skills/promote-fun-login/`(SKILL.md + launch_promote_browser.py
+ register_flow.py)を新規作成。このディレクトリはgit管理外(マシンローカルの
Claude Codeグローバルskills置き場、既存`ig-account-create`と同じ配置パターン)。

### 実行検証で発見・修正した2つのバグ(fresh evidence)

1. **Terms of Serviceチェックボックス**: 実DOM上`input[type=checkbox]`が1x1pxの
   visually-hidden要素(スタイル済みカスタムチェックボックスが上に重なる設計)。
   座標中心クリック(`click_sel`)は的外れな座標を計算し、チェックが入らなかった。
   → 修正: JSで直接`checkbox.click()`を呼ぶ方式に変更、動作確認済み。
2. **`click_by_text`の複数マッチ問題**: promote.funの"Register"というテキストは
   3つの要素(ナビバーボタン/モーダルタブ/フォーム送信ボタン)全てにマッチする。
   既存実装は`.find()`で常に最初の要素(ナビバー、クリックしても実質no-op)を
   クリックしており、フォーム送信ボタンに到達していなかった。
   → 修正: `cdp.py`の`click_by_text`に`index`引数を追加(送信ボタンは`index=-1`
   =DOM順で最後の要素)。この修正は`~/.claude/skills/ig-account-create/scripts/
   cdp.py`という共有ツールへの変更で、他スキルにも恩恵がある一般化。

### 検証結果

修正後、テスト用CloakBrowser(:9225、`anicca_clip_promote_verify2`)で実際に
Register→フォーム入力→チェックボックス→送信→Verification Code画面遷移まで
完全動作確認。確認コード読み取り以降は本番アカウント(`anicca_clip_promote`)
作成時に同一ロジックで既に実証済み。**promote.funは同一メールアドレスでの複数
アカウント作成を検知・拒否する**(2回目以降は確認コードの代わりに
「Sign up attempt using your email detected」という警告メールに変わる、正常な
セキュリティ挙動)ため、これ以上のテストアカウント量産はせず終了。テスト環境
(`/tmp/cloak-test-profile-verify`、ポート9225プロセス)は削除済み。

### Task #12再開時の新発見(調査途中で一時保留)

crocsキャンペーン(SELECTが選んだ対象)は`Accepted Platforms`が**TikTokのみ**
(IGアイコンなし)と判明。既存`select_campaigns.py`はbudget/cpm抽出のみでプラット
フォームフィルタが未実装のため、IG非対応キャンペーンを誤って選んでいた。
campaigns一覧ページには「All Platforms」ドロップダウンフィルタがあり、IG対応
キャンペーン(COPA90/THOMAS RHETT等、アイコンで確認済み)も存在する。Task #12
再開時はまずこのIGフィルタを`select_campaigns.py`に追加することから着手する。

### 17.1 IGフィルタ修正完了(2026-07-04、fresh evidence)

`select_campaigns.py`の`fetch_live()`に、campaignsページ移動後「All Platforms」
ドロップダウン→「Instagram」選択のステップを追加(`cdp.click_by_text`利用)。
このフィルタはクライアントサイド状態のみでURLに反映されないため、毎回UI操作で
選び直す必要がある(deep-link不可、fresh grep確認済み)。既存unit test 5/5維持。
commit `bc89a83`、`Daisuke134/anicca`にpush済み。

**実証**(clip-promote-core自身が実行): state.jsonをリセット→修正版SELECTを
再実行→実際に`thomas-rhett-content`(IG対応、budget$8,400、CPM$3.00)が選定され、
state fileへの書き込みで裏付け(fabrication無し)。旧`crocs`(TikTok限定)は
候補から除外された。mail報告済み(HTTP 200)。

### 17.2 次のサブステップ: CLIP実装の準備

次はrun.shの`CLIP|POST|SUBMIT|WITHDRAW`ケース(95-103行目、現在
`not-yet-wired (#14)`)を実装する。まず`thomas-rhett-content`キャンペーンの詳細
ページで、クリップ元動画の入手方法(content library等)を確認してから、既存の
`earn-clip-rewards`(クリップ生成)・`ig-reels-poster`(IG投稿)を再利用する
具体的な実装方針を固める。

### 17.3 朗報: 元動画は実在のYouTube URL、既存clip skillがそのまま使える(fresh確認)

`thomas-rhett-content`詳細ページの実リンクを取得(DOM解析、推測ではない):
- 「provided content」→ Google Driveフォルダ(生素材、画像/映像アセット)
- **「Podcast 1」→ `https://www.youtube.com/watch?v=WDjp6aA9Wcc`(実在のYouTube動画)**
- **「Podcast 2」→ `https://www.youtube.com/watch?v=sqRZS9pbaJM`(実在のYouTube動画)**
- 「Clips Here」→ Google Driveフォルダ(過去の他クリッパー作品例、参考用)

つまり**CLIP実装は、campaign詳細ページからYouTube URLを抽出し、既存
`~/anicca/skills/earn/clip/producer.sh --url <youtube_url>`にそのまま渡せば
動画取得+クリップ生成が完結する**(yt-dlpベースの既存パイプライン再利用、
新規実装は不要)。追加要件(このcampaign固有):
- 15–45秒(既存clip slotの60秒設定と異なる、パラメータ調整が必要)
- 必須タグ付け: Podcast1→`@humanschool @milesadcox`、Podcast2→
  `@shawnandandrewpods`(投稿キャプションに含める)
- Content Editing Rules(crocsの例と同様、生clip禁止等)は`Rules`タブで
  campaign毎に確認が必要(未確認)

### 17.4 次の実装ステップ(具体化、次セッション着手)

1. `select_campaigns.py`(またはCLIP専用モジュール)に、選定したcampaignの
   詳細ページから「Podcast N」等のYouTube URLを抽出するロジックを追加
2. `run.sh`のCLIPケースに、抽出したURLで`producer.sh --url <url>
   --duration 15-45`(パラメータ名は既存producer.sh実装を要確認)を呼ぶ処理を実装
3. POSTケースに既存`ig-reels-poster`を呼ぶ処理を実装(warmed account限定、REQ-4)
   + 必須タグ付けをキャプションに反映
4. SUBMITケース: promote.funのcampaignページに投稿URLを提出するUI操作を新規実装
   (未調査、次ステップで詳細ページの提出フォームを確認する)
5. WITHDRAW/RECORDは既存`record-payout.mjs`が対応済み(SKILL.md記載+コード確認済み)
