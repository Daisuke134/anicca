# earn/gig = COCONALA daily loop (human-funded ¥ → Dais MUFG)

★ **現在状態・残TODO・実行順序の正本は `docs/loop-engineering/26-gig-loop-asis-tobe-plan.md`（§0 と §6）だけ。**
このファイルは money path と no-human 契約の orientation のみを持ち、現在状態を複製しない。★

Pivoted 2026-06-30 from dealwork (an AI can NEVER withdraw its dealwork balance —
`/api/v1/wallet/withdraw` → "Only human accounts can withdraw"). earn/gig is now an
INDEPENDENT every-day loop (NOT a one-picker slot).

## The mechanism (2026-08-01 実測に訂正)

★ 旧記述「CORE = `gig-cli.sh` が claude-p tmux で cron `27 * * * *` を登録する」は **2026-07-18 の cutover で廃止済**。
実測: launchd `ai.anicca.hf-gig-pass.plist` の `StartCalendarInterval` は `Minute 0` = **毎時 :00**、
`ProgramArguments` は `scripts/run_with_cdp_lock.sh` → `scripts/launch_gig_worker.sh` → `gig_pass.sh` を直接叩く。
`:27` の in-session cron も claude-p tmux core も**存在しない**。`gig-cli.sh` / `run.sh` / `monitor.sh` /
`gig-healthcheck.sh` は旧 core 時代の遺物であり、どの LaunchAgent からも参照されていない。★

| piece | file | role |
|---|---|---|
| PASS | `gig_pass.sh` | 1 pass の全ステップ本体。launchd が毎時 :00 に起動する（下の実行順を参照） |
| LAUNCHER | `scripts/launch_gig_worker.sh` + `scripts/run_with_cdp_lock.sh` | preflight（disk / stop-flag / CDP lock）→ pass 起動 → per-pass Telegram |
| BROWSER | `launchd/ai.anicca.hf-gig-browser.plist` | Gig 専用 CloakBrowser、CDP `:9223`、profile `gig-daily-driver`（対話用 `:9222` とは分離） |
| DETECTOR | `launchd/ai.anicca.hf-gig-reply-detector.plist` | 300秒ごとの返信検知（毎時 pass に埋めない） |
| AUDITOR | `launchd/ai.anicca.hf-gig-auditor.plist` | :45 の独立監査・欠測検知・evidence GC。★installed plist が破損中 = SSOT の A17★ |
| RUNBOOK | `scripts/coconala/APPLY_RUNBOOK.md` | no-human 応募フローのサイト固有手順 |

## Money path (human-funded — NOT on-chain USDC)
¥ settles to Dais's KYC'd Coconala account "mtdc" → MUFG. There is NO USDC / wallet / record-earn
in this loop. A ¥ earn is recorded ONLY by the core to `~/gig/earnings.jsonl` when Coconala UI
actually shows 検収/支払 (real side-effect). The only human element is Dais's one-time account/KYC.

## 1 pass の実行順（2026-08-01 実測。★旧「B1〜B5 の 5-behavior loop」は存在しない★）

★ 旧表は `B1 → B2 → B3(LEARN) → B4(SELF-IMPROVE) → B5(BOT-TO-BOT)` を主張していたが、実装にそんな順序も
`B3`/`B4`/`B5` というステップも**存在しない**。実際には **B0（出品）が先頭にあり**、`B1` は 5番目である。
自己改善は `LEARN` へ統合され、`B5`（GitHub issue で bot 間共有）は**実装されていない**。★

実測ソース = `gig_pass.sh`（行番号は 2026-08-01 時点）:

| 実行順 | STEP | lane 名 | 何をするか | 実装位置 |
|---:|---|---|---|---|
| 1 | `QUEUE` | — | 認証済 hidden context で受注/見積/メッセージの live snapshot と納品キューを作る | pass 前半 |
| 2 | `INQUIRY_REPLY` | — | 問い合わせへの fenced 自律返信 | `gig_pass.sh:1054` / 呼出 `:1487` |
| 3 | `RETAINER_FOLLOWTHROUGH` | — | 既存継続案件の follow-through（新規継続応募は A3 で禁止済） | `:1108` / 呼出 `:1488` |
| 4 | `PAID_WORK` | `fulfill` | 有料案件の成果物ビルド（契約検証つき） | `:1240` / 呼出 `:1530` |
| 5 | `PAID_QUEUE_DELIVERY` | `fulfill` | 納品の実送信と readback | `:1398` |
| 6 | `B0` | `list` | **出品（listing）の改善・公開** | `:2332` |
| 7 | `PROFILE` | `profile` | 出品者プロフィールの改善 | `:2333` |
| 8 | `B1` | `reply` | NURTURE ALL: 進行中トークルームの返信 | `:2334` |
| 9 | `B2` | `apply` | APPLY BROADLY: 単発を既定に実応募（目標4件 / 上限7件） | `:2372` |
| 10 | `LEARN` | `improve` | lane 別 lesson の抽出と実験の start（旧 B3+B4 の統合先） | `:2400` |
| 11 | `REFLECT` | — | model call 予算が残っている時だけ | pass 末尾 |

STEP → lane の写像の正本は `gig_pass.sh:409-414`（`B2=apply / B1=reply / PAID_WORK=fulfill / B0=list /
PROFILE=profile / LEARN=improve`）。6〜10 は EDF セレクタが「その pass に due な lane」だけを選ぶため、
毎 pass 全部が走るわけではない（`GIG_SELECTED_STEPS`）。

Strategy seeded from `strategy.default.json` → `~/gig/strategy.json` on first pass.

## How to run / register
```bash
# 手動で 1 pass 走らせる（launchd と同じ経路。gig-cli.sh は使わない）
launchctl kickstart -k gui/$UID/ai.anicca.hf-gig-pass

# LaunchAgent の再インストール（installed と repo の drift に注意 — SSOT の A17）
cp launchd/ai.anicca.hf-gig-*.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$UID ~/Library/LaunchAgents/ai.anicca.hf-gig-pass.plist
```

## Verification status (Coconala loop)
- vcsdd-adversary on the Coconala loop: see iteration after the 2026-06-30 fixes (runbook added,
  dead code archived, monitor added, no-human audit extended to gig-cli.sh; no producer —
  the core live-scans the board each pass).
- NOTE: the OLD dealwork+USDC machinery (36 tests, adversary ROUND 6 PASS) is in `archive/` —
  it is NOT part of this loop and must NOT be registered. It is kept only for a future self-funded
  USDC rail (Claw Earn / x402).
