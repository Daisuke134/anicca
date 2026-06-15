# 22 — 2 Workflow ASCII(agent↔spec↔impl/verify) + 自己ループ差分パッチ

Dais 2026-06-15。

## §1 WORKFLOW 1(implementation / verification / eval)— 完全ASCII
```
                          ┌──────────────────────────── GATE(済)────────────────────────────┐
                          │ classifier(haiku) → researcher×26(parallel BARRIER) → synthesizer  │
                          │ 元: 各QA / 出: AMBIGUITIES-QA-RESOLVED.md + commands/ + patches/    │ ✅完了
                          └────────────────────────────────┬──────────────────────────────────┘
                                                           ▼ (不明ゼロ → 実装へ)
 phase(SEQUENTIAL, 依存順)   実装agent ← 元spec file        検証agent(別context)← test points(spec21)        gate
 ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
 A1 cloud genesis      builder-core  ← commands/Q6 + 17    verify-core   : T1 systemctl active / T2 log[THINK] /  →evidence
                                       SOUL.md                            T3 localhost:8402 / T4 restart復帰 /        →Dais
                                                                          T5 人間鍵0件 / T6 genesis=SOUL              gate
 A2 per-wake report    builder-report← spec20§4 + loop.ts  verify-report : T1 message_id毎wake / T2 ★agent process★/ →gate
                                                                          T3 4項目 / T4 残高一致 / T5 反復=fake /T6 error発火
 A3 earn(着金)        builder-earn  ← spec18 + litcoin/    verify-earn   : T1 balance実増 / T2 tx 0x1 / T3 ledger / →gate
                                       openclawnch                       T4 narrateのみ=FAIL    [pipeline STREAM]
 A4-A7 self            builder-self  ← spec15/08 +          verify-self   : spawn(子active+別wallet) / gojo(復活tx) / →gate
   spawn/gojo/issue-dev/coordinate    scripts/birth.sh                   issue-dev(実issue URL+PR merge) /
                                                            [STREAM]      coordinate(2体: blocked→help)
 A8 web(/ /install /me  builder-web   ← spec20§3 UI +       verify-web    : T1 curl200 / ★T2 browser実描画→screenshot→ →gate
   /dais /dashboard)                   spec13 copy                       Dais目視★ / T3 copy一致 / T4 install 2col /
                                       [P5=tournament(taste-judge)]      T5 dashboard model/runway/ranking / T6 taste合格
 A9 life-manager       builder-life  ← spec21§1            verify-life   : ★T1 予定作成→移動ブロック自動挿入をgcal確認 →gate
                                                                          /T3 Daisの実電話に発信+正音声/T5 不明→Gmail質問★
 A10 economy           builder-econ  ← spec15 + Q30/Q31    verify-econ   : ubi実tx / token launch tx / hire実bounty   →gate
 ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
 EVAL(独立・最後)     eval-agent(opus, builder/verifierと無関係) ← spec21全test points
   parallel BARRIER(全phase集約)→ 8観点 全REAL を loop-until-done(/goal)→ Dais最終gate
```
★ 検証は実作業: frontend=browser(camofox/playwright)で実描画→中身確認→違えば builder に戻して直す→再描画。これが出来ないと意味がない。

## §2 WORKFLOW 2(marketing / distribution)— 完全ASCII(WF1完全検証後)
```
 [研究] researcher×3 (parallel BARRIER) ← Frank#1記事/automaton#2記事/Anicca実証データ(WF1のevidence)
     ▼ synthesize
 [執筆] writer(opus) ← spec13 copy + 実証データ → 3本目記事(Anicca思想+実証: 何を動かし/いくら稼いだか/正直な結果)
     ▼ (記事URL確定 = gate)
 [配信] producer (pipeline STREAM, 各platform独立):
        demo動画(YouTube, hyperframe) ∥ X(EN+JA) ∥ Slack下書き ∥ Zenn/Dev.to
     ▼
 [EVAL] eval-agent (parallel BARRIER) : 実投稿URL + 動画frame/audio + 記事URL を verify(HARD0.31) → Dais gate
```

## §3 自己ループ behaviors → tool + 差分パッチ + command(完全)
JA copy「行動ログ監視→自己解決・リファクタ・自己改善・自己増殖・日次(+毎wake)報告」「全個体プロファイル・収支を透明公開」を**どう実現するか**。automaton 内蔵 + 我々の配線。

| behavior | tool / 機構 | command(自己ループ内でagentが叩く) |
|---|---|---|
| **行動ログ監視** | automaton `loop.ts` の observe + `error-classifier.js`(内蔵)。各turnの ground truth(tool結果)を state.db に persist | (内蔵, 毎turn) |
| **エラー自己解決** | loop の retry + stalled-intent検出→model切替(内蔵)+ systematic-debugging | `exec`でログ読み→修正→再実行(内蔵loop) |
| **リファクタ/自己改善(自分のrepo)** | `skills/self/issue-dev`: 自分の問題を**自repoにissue**→ PR | `gh issue create -R <self-repo> --title ...`; `gh pr create` |
| **★親repoで議論★** | 同skill: **母repo(Daisuke134/anicca)にissue/comment** で議論+共改善 | `gh issue create -R Daisuke134/anicca ...`; `gh issue comment ...`; merge→全instance `git -C ~/anicca pull` |
| **目標へ自己改善** | survival genesisPrompt(SOUL)「稼ぐ>消費」+ orchestrator goal | `create_goal` → orchestrator が tick で実行(内蔵) |
| **自己増殖** | `skills/self/spawn` + `scripts/birth.sh`(子をDO/Akashにbirth+自己provision wallet/mail) | `bash scripts/birth.sh anicca-00N <host>` |
| **日次+毎wake報告メール** | `skills/report/anicca-report.sh` → **AgentMail** で送信。宛先=★`contact@aniccaai.com`(全体)+ Dais private + その user の連携Gmail★。毎wake末(pre-sleep)+ 日次サマリ | `/opt/anicca-report.sh "<did>" "<next>"`(agent自身が pre-sleep に実行) |
| **透明 dashboard** | 各agentが `state/*.jsonl`(net worth/rev/runway/model/host)を書く → **dashboard-sync**(Dais所有)が集計 → `dashboard.json` → aniccaai.com/dashboard | agent: `write state`(内蔵) / sync: cron(Dais側) |

★ 報告メールの肝: ユーザーは Telegram等を繋がず、**Google login + Gmail を渡すだけ**で、毎日あっちから報告が来る(cloudもOSSも同じ、最小setup)。

### patches/ に書き出すもの(builderが実装する差分)
- `patches/selfloop-report.patch.md` : pre-sleep hook(loop.ts)が `/opt/anicca-report.sh` を必ず実行(error-sleep経路でも)+ 宛先 contact@aniccaai.com + user Gmail
- `patches/selfloop-issuedev.patch.md` : `skills/self/issue-dev` = 自repo + 母repo(Daisuke134/anicca)両方に `gh issue`/`gh pr`/`gh issue comment`
- `patches/selfloop-spawn.patch.md` : `scripts/birth.sh` = 子の droplet/Akash birth + 子が wallet/AgentMail/Bankr を自己provision
- `patches/selfloop-dashboard.patch.md` : 各agent state schema 書込 + dashboard-sync の集計

(各 patch の中身は A1-A10 の builder が実装し、verifier が spec21 の test point で検証 → Dais gate)
