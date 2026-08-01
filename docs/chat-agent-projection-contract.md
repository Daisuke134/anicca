# Life Manager chat agent projection contract

## 1. 目的

ユーザーはlaunchd、PID、plist、skill ID、adapter IDを理解しなくても、Life Managerへ自然言語で目的を伝え、担当エージェント、実行中の仕事、必要な承認、結果の証拠を一つの会話で理解できる。

この文書は画面デザインではなく、Telegram、Web chat、voice transcript、将来のdashboardが共有する意味契約である。

## 2. 投影する3つの正本

```text
agents/registry.json
役割・目的・組織・許可されたeffect・lifecycle
                    │
                    ├──────────────┐
                    ▼              ▼
canonical job/lease/receipt   user/tenant policy
実行、健康状態、結果証拠       権限、金額上限、確認要否
                    │              │
                    └──────┬───────┘
                           ▼
                    Chat projection
```

Chatはregistryだけから「現在稼働中」と推測してはいけない。`live`は製品ライフサイクルであり、直近runの成功ではない。

## 3. ユーザーから見える基本単位

### 3.1 Agent card

```text
🟢 Gig Work Agent
目的: 実行可能なギグを受注・納品して収益化
製品状態: Legacy live
現在状態: 1時間前に成功
担当中: Coconala応募候補3件
次の副作用: 応募message送信
証拠: receipt:gig-20260801-...
```

最低表示項目:

| field | source |
|---|---|
| 表示名、目的、organ | Agent Registry |
| 製品状態 | Registry `lifecycle` |
| 現在状態 | lease/receipt/ledger |
| 現在task | canonical job |
| 次のeffect | job proposalとregistry effect |
| 証拠 | provider receiptまたはcanonical receipt |

### 3.2 Organ summary

```text
┌ Finance / CFO ──────────────────────────┐
│ 🟠 Gig Work       成功・1時間前         │
│ 🟠 Capafy         次回実行待ち          │
│ 🟢 Polymarket     WAIT・損失なし         │
│ ⚪ CFO Lead       planned               │
└─────────────────────────────────────────┘
```

同じroleに複数runtime jobがあっても、最初の画面ではagent cardを1枚だけ表示する。開発者向け詳細でruntime familyと個別jobを展開する。

## 4. 会話フロー

### 4.1 目的から委譲

```text
Dais
「今月の収入を増やして」
   │
   ▼
Life Manager Orchestrator
   ├─ current financial stateを読む
   ├─ 目標、期限、policyを確認
   ├─ 必要なspecialistだけを選ぶ
   └─ canonical jobを発行
          │
          ├─ Gig Work Agent
          ├─ Writer Agent
          └─ Capafy Agent
                 │
                 ▼
             receipts
                 │
                 ▼
Life Manager
「実収入、未確定、失敗、次の手」を分けて報告
```

Orchestratorは単語一致だけで担当を決めない。目的、現在状態、制約、利用可能なagent definitionをモデルへ渡し、選択理由をjobへ残す。permission、金額、重複、idempotencyは決定的policy gateが強制する。

### 4.2 一覧要求

以下を同じintentとして扱えるようにする。

- 「エージェントを全部見せて」
- 「誰が動いてる？」
- 「収益チームの状態」
- 「いま何が止まっている？」

既定表示はorgan summary。ユーザーが「詳細」「証拠」「ジョブまで」と言った場合だけsource、receipt、runtime family、個別jobを展開する。

### 4.3 直接指名

```text
Dais: Writer AgentにLife Managerの記事を書かせて

Life Manager:
Writer Agentへ次のjobを準備しました。
・目的: 初心者向けLife Manager紹介記事
・effect: draft
・公開: まだしません
・必要な証拠: cited draft artifact
実行します。
```

存在しない名前の場合は近いskillをagentとして捏造せず、次のように返す。

```text
「TaskMarket Agent」は現在の名簿にはありません。
TaskMarketはCFO/Orchestratorが使う決定的な収益ツールです。
```

## 5. runtime healthの意味

| chat状態 | 必要条件 |
|---|---|
| `running` | 有効なleaseがあり、期限を超えていない |
| `waiting` | 次回scheduleまたは外部response待ちがreceiptにある |
| `success` | effect別の完了証拠がある |
| `failed` | terminal failure receiptがある |
| `stale` | 最終heartbeat/receiptが定義されたfreshnessを超えた |
| `unknown` | definitionはあるがruntime証拠を取得できない |
| `planned` | registry lifecycleがplanned |

`unknown`を`stopped`や`failed`へ勝手に変換しない。観測不能と失敗は異なる。

## 6. effectと確認

```text
read     ──► 自動可能
draft    ──► 自動可能
message  ──► allowlist、宛先、内容policy
publish  ──► public範囲、rollback、product policy
money    ──► owner、通貨、上限、wallet policy、receipt
```

Registryはeffectを宣言するだけで、承認済みを意味しない。実行時policyがより厳しければpolicyを優先する。

取消不能、高額、初回宛先、新規契約など、policyが確認を要求する場合の表示:

```text
確認が必要です
Agent: Gig Work Agent
Action: 有料プランへの応募
Amount: ¥5,000
Recipient/platform: Coconala
Rollback: 不可
実行 / 変更 / 中止
```

## 7. 成功証拠

| effect | 成功に必要な証拠 |
|---|---|
| `read` | source reference、取得時刻、freshness |
| `draft` | artifact path/hash |
| `message` | provider message/thread ID |
| `publish` | public URLまたはprovider publication ID |
| `money` | transaction/settlement ID、official readback、owner ledger反映 |

モデルの文章、stdout、`done:true`だけでは成功証拠にならない。

## 8. partial failure

一つのgoalを複数agentへ委譲した場合、全体を成功/失敗の一語へ潰さない。

```text
今月の収入改善

✅ Gig Work Agent
応募2件。message IDあり。

⚠️ Writer Agent
下書き完了。公開は未実行。

❌ Capafy Agent
remote status readbackに失敗。公開成功とは扱いません。

確定収入: ¥0
未確定pipeline: 2応募 + 1下書き
次: Capafy readback修復後に再確認
```

## 9. ローカル版とWeb版

会話契約とagent IDは共通にする。

```text
Local OSS                         Web / Cloud
local files/wallet/browser       tenant-scoped storage/secrets/browser
             │                              │
             └──── same Agent Registry ─────┘
                         │
                 same job/receipt schema
                         │
                  same chat semantics
```

違うのはtransport、secret provider、storage、tenant isolation、billingであり、agentの名前と責任ではない。

## 10. privacyと表示制限

- secret、private key、raw token、個人メール本文、全browser storageをchatへ表示しない。
- evidenceは安全なID、hash、URL、timestampへ縮約する。
- developer detailでも環境変数の値は表示しない。
- 他tenantのagent instance、job、receiptを絶対に結合しない。
- planned roleを「稼働中」と表示しない。

## 11. 将来のAPI境界

Chat/dashboard実装は最低限、次の読み取りinterfaceを使う。

```text
listAgentDefinitions(tenantScope)
listAgentRuntimeStates(tenantScope, agentIds)
listAgentJobs(tenantScope, agentId)
getAgentEvidence(tenantScope, receiptId)
proposeDelegation(tenantScope, userGoal)
authorizeEffect(tenantScope, proposal)
```

Agent Registryをchat codeへ複製しない。runtime healthをREADMEやGitへ書き戻さない。すべての表示はdefinition、runtime state、policyのjoinとして生成する。
