# Capafy 収益化プログラム — MASTER SPEC（やるべきこと全部）

- **Date**: 2026-06-04
- **Status**: PLANNING（実装未着手）
- **Branch policy**: `dev` = 唯一の作業trunk（このspecもdevに置く）
- **方法論**: SDD/TDD（各実装タスクは個別に spec→plan→TDD→verify→review→dev push）
- **関連**: `2026-06-04-capafy-monetization-design.md` / `2026-06-04-capafy-profit-playbook-BP.md` / `~/.openclaw/docs/CAPAFY_PUBLISH_PLAYBOOK.md`

---

## 0. 全体像（完全ASCII）

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  ANICCA × CAPAFY 収益化プログラム                                                ║
║                                                                                ║
║  [知識] capafy-profit-playbook-BP.md (実測232件)                                ║
║     値付けルール / 命名 / コスト式(Sonnet$3/$15・$0.12/回) / サブスクvsDownload  ║
║              │                                                                 ║
║  [道具] ★capafy-autopublish スキル★ (= 公開代行・売り物)                        ║
║     PREREQ(人): アカ作成/KYC・銀行/OTPログイン→access_token                      ║
║     ENGINE(自動): CLI(init→configure→ship→status) + camofox web(CP1/2/3)        ║
║                 + リーク防止(CLAUDE.md除外) + deep-scan + BP値付け助言            ║
║     人の最終判断: mode(サブスク/Download)+価格 のみ承認                          ║
║              │                                                                 ║
║  [知識単体] monetize-capafy スキル (壁打ち専用・公開機能なし・安価Download)       ║
║              │                                                                 ║
║  [適用先] ─┬─ jp-humanizer ✅提出(審査中)                                        ║
║            ├─ ★life-manager★ reject修正→Download/BYOK再submit (最重要)           ║
║            ├─ capafy-autopublish 自身を販売($9.99) + OSS化                       ║
║            ├─ monetize-capafy 販売                                              ║
║            └─ 全スキル: LOCAL ~/.openclaw/skills/ を Anicca cron が1run=1スキル  ║
║                        で自走公開 (GitHub Action不可・要camofox+判断)            ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

## 1. 確定事項（不変の前提）

| 項目 | 値 |
|---|---|
| Capafy手数料 | 20% + 初回$0.99認証料。Subscriptionのみ Sandbox Fee $0.07/日 |
| 2モード | Run on Capafy(サブスク)=publisher鍵hosting=API代我々持ち / Download買い切り=買い手鍵・ソース開示 |
| 鍵の出し手 | サブスク=我々 / Download=買い手。買い手が鍵出せるのはDownloadのみ |
| 収益実測232件 | TOP35全サブスク・Download最高販売2本 |
| コスト | Sonnet4.6 $3/M in・$15/M out。1 humanize≈$0.12/回(agent overhead込) |
| 安全黒字 | サブスク 週$5.99×cap8/週(4.6:1)。cap40は赤字 |
| token | `~/.openclaw/skills/capafy-publisher/config.json::access_token`(OTP不要) |
| 検索 | JSON body `{"query":...}`。`--env claude_code` |
| スキル所在 | LOCAL `~/.openclaw/skills/`（anicca-private-backupはバックアップで fetch元ではない） |

## 2. Git方針（恒久）

| branch | 役割 | ルール |
|---|---|---|
| **dev** | 唯一の作業trunk（iOS/content/Capafy 全部） | 普段はここにpush |
| main | 本番(Railway自動deploy) | dev→main のみ。直接作業禁止 |
| release/x.x.x | App Store提出専用 | mainから切る。他作業を積まない |

**現状の負債**: main↔release/1.8.7 が 455/147 分岐(iOSコード混在)。収束手順=①dev←main ②dev←release/1.8.7(conflictはdevで解決) ③dev build/test ④dev→main ⑤release作業禁止徹底。

## 3. やるべきこと全部（task list と同期）

| # | タスク | 種別 | 依存 | gate/メモ |
|---|---|---|---|---|
| T8 | Git整流: dev唯一trunk化・main↔release収束 | infra | — | 本番main更新含む。普通の必要作業として実行 |
| **T3** | **capafy-autopublish スキル作成**(公開代行・BP内蔵) | 実装 | — | spec→plan→TDD。記憶が新鮮な今が最適 |
| T7 | monetize-capafy スキル(BP単体・壁打ち・公開機能なし) | 実装 | — | 安価Download。中身はBP doc |
| T2 | life-manager reject修正→Download/BYOK再submit | 実装 | — | 最重要。reject 7項目+retry/rate上限コード強制。agent_id 4437197514 |
| T6 | capafy-autopublish を Capafy販売($9.99)+OSS化 | 公開 | T3 | autopublish使用 |
| T4 | 全スキルを Anicca cron で自走公開(LOCAL skills) | infra/公開 | T3 | gate=jp-humanizer承認+目玉3-5本実証後に全面 |
| T5 | jp-humanizer 審査承認→listing確認 | 受動 | — | 審査1-2日。**最後尾** |

## 4. life-manager の鍵（重要判断の記録）

DeepSeek等の安い鍵で「サブスク化」は **LLM部分のみ**解決。life-managerは Twilio通話料(変動・高)＋Gemini Live＋常駐polling(Capafy cloudで動くか不確実)があり、**安い鍵だけではサブスク不成立**。
→ **B-1 Download/BYOK**(買い手が自前 Twilio/Gemini/DeepSeek鍵でローカル実行・通話料も買い手持ち・privacy reject構造解消・電話core value維持) で再submit が正解。サブスク化は電話を捨てた LLM-only 簡素版(B-2)を別Agentで後日。

## 5. capafy-autopublish スキル要件（T3のspec種）

| 層 | 内容 |
|---|---|
| PREREQUISITES(人手) | Capafyアカ作成 / KYC・銀行(payout) / publisher install+OTPログイン → access_token を渡す（サブスク選択時はLLM鍵も）。login/KYC/CAPTCHAは自動化しない(HARD RULE) |
| advise | BP(232件)で「今これが売れてる→こう直せ」を壁打ち |
| build/fix | 既存スキルを売れる形にリライト / 0から生成 |
| price | BPルールで mode+価格を推奨提示 → 人が最終承認(唯一の人判断) |
| publish | CLI chain + camofox web自動化(CP1 Card/CP2 cred/deep-scan/CP3 Submit) + リーク防止(Workspace Docs deselect=CLAUDE.md除外) + logo canvas生成 |
| verify | publish-remote-status で status=1/4 確認(嘘禁止) |
| 自走 | Anicca cron が ~/.openclaw/skills/ 走査→未公開1つ→実行→台帳(_shared/capafy-published.jsonl)記録→次。1run=1スキル |

## 6. 進め方（SDD/TDD・恒久ルール）

各実装タスク(T2/T3/T7)は個別に: **brainstorming spec → writing-plans → using-git-worktrees(該当時) → TDD(RED→GREEN→REFACTOR) → verification-before-completion → code-review → finishing(dev push)**。本spec は上位master。直近 plan化対象は **T8(Git整流) → T3(autopublish)**。
</content>
