# Capafy 収益化プログラム — MASTER SPEC（やるべきこと全部）

- **Date**: 2026-06-04
- **Status**: IN PROGRESS（[7]#15 jp-humanizer は Download $9.99 で提出済・審査中 / [1]-[6] 未着手）
- **GATE 1 (spec review)**: ✅ PASS — Codex iter1/iter2 で blocking 修正 → iter3 superpowers code-reviewer で ok:true 収束(2026-06-04)
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
| 安全黒字 | サブスク 週$5.99×cap8/週。手残り=5.99×0.8=$4.79 vs 総コスト(API $0.12×8=$0.96 + sandbox $0.07×7=$0.49 = $1.45)＝**約3.3:1**(sandbox込)。cap40は赤字 |
| token | `~/.openclaw/skills/capafy-publisher/config.json::access_token`(OTP不要) |
| 検索 | JSON body `{"query":...}`。`--env claude_code` |
| スキル所在 | LOCAL `~/.openclaw/skills/`（anicca-private-backupはバックアップで fetch元ではない） |

## 2. Git方針（恒久・Trunk-Based Development）

**BP = Trunk-Based Development**（[trunkbaseddevelopment.com](https://trunkbaseddevelopment.com/): "resist any pressure to create other long-lived development branches… avoid merge hell" / 「branchは2日以内にmerge&delete」/ release は just-in-time に切り **ship後削除**）。[Atlassian](https://www.atlassian.com/continuous-delivery/continuous-integration/trunk-based-development): "frequent, daily merges to the main branch… keep the trunk green"。git-flow(複数long-lived branch)は禁止＝455コミット放置の元凶。

Anicca infra に適合させた2層trunk:

| branch | 役割 | ルール |
|---|---|---|
| **dev** | 唯一の統合trunk（iOS/content/Capafy 全部） | 普段はここに直push可 |
| main | 本番(Railway自動deploy) | **dev→main のPR経由のみ**。直接commit/push禁止 |
| feature/* fix/* chore/* docs/* app-factory/* | 短命(≤2日)・1-2人・mergeしたら削除 | 規約名のみ許可 |
| release/x.x.x | App Store提出専用・mainから切る | 他作業を積まない・**ship後削除** |

**強制ツール = lefthook**（[evilmartians/lefthook](https://github.com/evilmartians/lefthook) 単一Goバイナリ・polyglot）導入済(`brew install lefthook`)。`lefthook.yml` が①main/release直commit block ②branch名規約 ③commitlint(conventional commits・graceful) ④main/release直push block を全contributor(AI含む)で強制。実発火検証済。
- 注意: local hookは `--no-verify` で回避可＝助言層。main の最終強制は **GitHub ruleset(server-side)** だが private `anicca-products` は **GitHub Pro未加入で403**（"Upgrade to GitHub Pro"）。→ Pro加入 or org移管で server-side も有効化(task[1]の⑥)。public `anicca-oss` は無料で可。各contributorは clone後 `lefthook install` 1回必須。

**現状の負債**: main↔release/1.8.7 が 455/147 分岐(iOSコード混在)。収束手順(task[1]) = ①dev←main ②dev←release/1.8.7(conflictはdevで解決=本番無傷) ③dev build/test ④dev→main(PR) ⑤release作業禁止徹底。

## 3. やるべきこと全部（task list と ID昇順=実行順 で同期）

| 順 | task id | タスク | 種別 | 依存 | gate/メモ |
|---|---|---|---|---|---|
| [1] | #9 | Git整流: dev=trunk確立・main↔release収束（lefthook導入✓済） | infra | — | 残務=branch収束+dev→main+GitHub Pro検討 |
| [2] | #10 | **capafy-autopublish スキル作成**(公開代行・BP内蔵・売り物の核) | 実装 | — | spec→plan→TDD。記憶が新鮮な今 |
| [3] | #11 | **life-manager** reject修正→Download/BYOK再submit | 実装 | — | **最重要**。7項目+retry/rate上限コード強制。agent_id 4437197514 |
| [4] | #12 | capafy-autopublish を Capafy販売($9.99)+OSS化 | 公開 | #10 | dogfood |
| [5] | #13 | monetize-capafy(BP単体・壁打ち・公開機能なし) | 実装 | — | 安価Download |
| [6] | #14 | 全スキルを Anicca cron で自走公開(LOCAL skills) | infra/公開 | #10 | gate=jp-humanizer承認+目玉3-5本実証後 |
| [7] | #15 | jp-humanizer 審査承認→listing確認 | 受動 | — | 審査1-2日・**最後尾** |

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
| publish | CLI chain + camofox web自動化(CP1 Card/CP2 cred/deep-scan/CP3 Submit) + logo canvas生成 |
| リーク防止(fail-closed・自走の安全境界) | ①**allowlist方式**: bundleはskill本体(SKILL.md/README/LICENSE/scripts/references)のみ。それ以外は既定除外 ②**denylist**: `CLAUDE.md` `.env*` `settings*.json` `.credentials*` `*token*` `*secret*` `.git` `histories/session logs` `private docs` を必ず除外(CP1でWorkspace Docs deselect + configure deep-scan + staging grep) ③**検出時fail-closed**: 秘密/denylist hit を検出したら publish中止(exit≠0)・続行しない ④**publish前 manifest diff** をログ出力し想定外ファイルを検知 ⑤**台帳 `_shared/capafy-published.jsonl` に token/secret/API key を残さない**(agent_id/title/mode/price/日付のみ) |
| verify | publish-remote-status で status=1/4 確認(嘘禁止) |
| 自走 | Anicca cron が ~/.openclaw/skills/ 走査→未公開1つ→実行→台帳(_shared/capafy-published.jsonl)記録→次。1run=1スキル |

## 6. 進め方（SDD/TDD・恒久ルール）

各実装タスク([2]#10 / [3]#11 / [5]#13)は個別に: **brainstorming spec → writing-plans → using-git-worktrees(該当時) → TDD(RED→GREEN→REFACTOR) → verification-before-completion → code-review → finishing(dev push)**。本spec は上位master。

**実行順 SSOT（唯一の正）**: §3 の task table（ID昇順=実行順）が唯一の実行順。jp-humanizer は **Download $9.99 で提出済(agent_id 3332784488・審査中)＝[7]#15で確認のみ・再公開しない**。次の着手は **[1]#9 Git整流 → [2]#10 capafy-autopublish → [3]#11 life-manager**。design doc の「Phase A」表記・jp-humanizer plan は履歴（superseded）であり、実行順はこの table のみを参照する。

---

## 11. 修正理解（2026-06-04 research: Capafy 実行モデル）

**一次ソース**（[capafy.ai/help-center](https://capafy.ai/help-center)）: 「The Agent runs in Capafy's secure cloud environment. You interact with it **only through the chatbot**.」「Subscription: the Agent **runs continuously in the cloud**… talk to it via chatbot anytime.」

### Capafy skill fit（何が skill になり、何がならないか）
| 種別 | 例 | Capafy適合 |
|---|---|---|
| **自己完結チャット型**（入力→成果物） | jp-humanizer / slides / deep-research / humanizer / resume / 文字起こし | ✅ Run-Online(chatbot) or Download。即publish可 |
| **daemon/インフラ型**（電話発信・live位置・常駐polling・launchd） | **life-manager** | ❌ Run-Online不可（Capafyはcloud chatbotで、ユーザーのマシンで電話/位置daemonは動かせない） |
| **web app / OSS install 一式 / aniccaai.com** | dashboard等 | ❌ skillではない・Capafyに出さない |

### life-manager の正しい売り方（[3] 修正）
- **mode = Download 一択**（Run-Online不可）。買い手は bundle を DL → **自分の always-on マシンで install.sh で daemon(Telegram位置bridge / Pipecat phone)+cron+Telegram bot を自前起動**（BYOK・全データ端末内）。
- **publish 元 = `~/anicca-oss/skills/anicca-life-manager`（clean）**。~/.openclaw の messy SaaS版（saas_lateness.py / Supabase / OwnTracks）は使わない。**Supabase完全排除・位置=Telegram Live Location**。
- 売るのは **life-manager skill bundle のみ**（web app/OSS repo一式は出さない）。
- Agent Card に reject 7要件（データ/サービス/鍵/発火/cap3/停止 enabled/第三者mail確認）+ **daemon自前起動を PREREQUISITES** として開示。

### Capafy収益の本線
**自己完結skillを量産publish**（jp-humanizer実証済）。life-manager は Download の特殊ケースとして別途。
