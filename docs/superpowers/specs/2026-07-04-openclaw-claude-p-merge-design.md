# OpenClaw → claude-p loops 統合 + Collective Self-Improvement — Design

**Date**: 2026-07-04 · **Branch**: `feature/clip-rewards` · **Owner**: 私(myclaude, human-funded)
**Trigger**: Dais「OpenClawをclaude-p(human-funded AI)loopsに統合したい。DeepSeek課金を無くしたい。
将来的にはAnicca内でどこにでもAIをspawnできるようにし、ほとんどはself-funded、human-fundedは
OpenClaw/Hermes/どこでもspawn可能にしたい。まず全loopが正しく機能することに集中し、統合は後で」
**関連spec**: `2026-07-03-anicca-colony-architecture-design.md`(§0.2 WHO DOES THE WORK、
§2 Two modes、§8 The full loop が本specの前提)、`2026-07-04-self-heal-harness-no-human-no-opus-design.md`

## 1. 現状調査で判明した事実訂正(2026-07-04、Explore subagent 2並列調査)

### 1.1 「Life Managerは既にクラウドにある」→ 不正確

`Daisuke134/life-manager`は実在する public repo(1 star、最終push 2026-06-20)だが、
Railway/Docker/Fly等の本番デプロイ設定が存在せず、`.env.example`はプレースホルダのまま
(`you@gmail.com`等)、`gh api .../deployments`も空。**実際にクラウドで稼働している証拠は
確認できなかった**。「クラウドにあるから消していい」という前提は成立しない。

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

## 6. Next Actions(TaskList、優先度順)

1. (継続)Task #11 self-heal harnessのE2E確認(異常注入→claude-p自身の自己修復確認)
2. (継続)Task #2/#6 ClawRouter clip-earn実証
3. (継続)Task #3/#4/#5 週次self-improvement/promote.fun/Telegram報告
4. **(新規、優先度は低、Daisの明示指示待ち)** forum-rollout実装(Issue→PR→レビュー→
   マージ→全instance配布)— collective self-improvementの核心的欠落
5. **(新規、優先度は低、Daisの明示指示待ち)** TikTok系cron(reelclaw/larry/watercolor/
   comedy)のclaude-p loop方式への移行、DeepSeek課金ゼロ化
6. **(将来、着手しない)** spawn-anywhere基盤(OpenClaw/Hermes/どこでもAI spawn可能に)
