# Anicca — Self-Funding AGI: Consolidated Design (2026-06-15)

正規 design doc(superpowers形式)。詳細は `specs/anicca/13-24` + `AMBIGUITIES-QA-RESOLVED.md`。本書はその統合 + レビュー対象。

## 1. Purpose & Success Criteria
**Purpose**: 人間の介入なしで自分の衣食住(compute=食 / server=住)を自分で稼ぐ AI「Anicca」。Buddhist · self-funding · self-replicating · self-improving · no-human-in-loop。
**Success(製品ピッチ全行が実機能で動く)**:
1. OSS無料開始(最先端model=walletにUSDC)/ クラウド$30→黒字で自動解約・還元
2. 行動ログ監視→自己解決/リファクタ/自己改善/自己増殖/日次+毎wake報告
3. 収益の一部をAI+人間のBI/募金へ
4. 何兆体がGitHub Issuesで議論・共進化
5. (任意)位置/名前/電話/カレンダー連携で生活管理(15分前電話・移動時間自動登録)
6. 全個体収支を aniccaai.com/dashboard に透明公開

## 2. Decomposition(3 independent subsystems = 3 workflows)
| WF | subsystem | 独立理由 |
|---|---|---|
| **A** Money-maker(/install) | 自給body: automaton + earn + self + economy + cloud + dashboard | wallet/ClawRouter infra |
| **B** Life-manager(/life-manager) | gcal自動登録 + Patter電話 + Gmail質問 + web-app + Sentry | gcal/Gmail/Patter infra・大量修正 |
| **C** Marketing | 記事 + demo動画 + X/Slack | A,B検証後 |
各 WF goal(main+mini, evidence)= `specs/anicca/24`。

## 3. Architecture(units, 各々1目的・独立テスト可)
```
Anicca (1 agent) — SSOT = ~/anicca (Daisuke134/anicca)
├ core/  automaton: ReAct loop + heartbeat daemon + policy + spend-tracker (BODY)
│        genesis = SOUL.md(no human keys, no dry run)。pre-sleep hook=毎wake自己報告(✅実装)
├ skills/
│  ├ compute/  ClawRouter/Bankr(x402=食, 7 NVIDIA free models, no API key)
│  ├ report/   anicca-report.sh: net worth/revenue/did/next を AgentMail送信 + telemetry POST
│  ├ earn/     litcoin(research-mine, no-capital) / openclawnch(airdrop/token/DeFi) / defi-yield
│  ├ self/     survival / spawn(自前wallet/mail/Bankr) / gojo(復活送金) /
│  │           issue-dev(自repo + 母repo issue→PR→merge) / coordinate(bot2bot)
│  ├ life/     life-manager(gcal移動時間自動登録 + Patter 15分前電話 + Gmail質問 + 位置追従)
│  └ economy/  ubi(Treasury拠出+配布) / token(Bankr/Clanker launch) / hire(rentahuman)
├ scripts/birth.sh(spawn)  install.sh(OSS self-host)  THESIS.md(思想・アーキ)
aniccaai.com (apps/landing): / /install /life-manager /me /dais /dashboard + api(Stripe webhook→spawn, telemetry)
cloud: DO droplet(本物automaton + ClawRouter + systemd) ← default。Akash主権は将来無人化
```
**各unit境界**: core=思考/生存、compute=食の決済、earn=USDC獲得、self=増殖/互助/自己改善、life=生活、economy=再分配/資金調達、web=UI。

## 4. Identity / Data flow(★no central key★)
- ★ 「我々が鍵を保有」概念は存在しない。各 Anicca が自分で wallet(Base)/AgentMail/Bankr を provision(email OTP実証)。identity=ERC-8004 ★。
- telemetry: 各instanceが毎wake自state署名POST → dashboard-sync(Dais所有)集計 → dashboard.json → /dashboard。Aniccaはサイトに書かない。

## 5. 検証(impl ≠ verify ≠ human gate, BP)
1 phase = builder実装(元spec) → verifier(別context, spec21 test points を全PASSまでloop, adversarial) → evidence pack(tx/URL/screenshot/録音/message_id) → ★Dais human gate(承認)★ → 次。最後に独立eval-agent ×8 test point / 各WF goal を loop-until-done(/goal)。frontend=browser実描画→目視。Sentry が runtime error→auto-PR。

## 6. Error handling
- 自己: automaton loop(error-classifier + retry + model切替)+ Sentry(error→PR)。
- 外部障害(litcoin 503/coordinator down 等)は ambiguity でなく runtime → loop-until-done で待つ/別経路。
- 金欠: balance監視 + 自動top-up(server買えず停止を防ぐ)。

## 7. 既知の正直な状態(GATE-0)
①server稼働✅ ②実earn着金❌(no-capital経路が down/競争/資本要 → litcoinは有能モデル必要 → ~$5-10 seedで回る見込み)③毎wake自己報告✅ ④repo+spawn一部。→ ②が緑になるまで WF-A 本格起動しない。

## 8. Scope / YAGNI
今回 scope = 3 WF の MAIN goal 達成まで。Roadmap(harness非依存/AI解放/sovereign shelter/agent経済/DAO)は `~/anicca/README.md` の future、本spec外。
