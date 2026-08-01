# Life Manager Agent Registry 設計仕様

**日付:** 2026-08-01  
**状態:** 承認済み設計  
**正本の責務:** Life Managerに存在する「本物のエージェント」の定義、組織、ライフサイクル、実装証拠、ユーザー表示を一元管理する。

## 1. 背景

Life Managerには、現在少なくとも次の3種類の一覧がある。

- `skills/registry.json`: 22個の能力スロット
- `apps/life-manager/config/loop-adapters.json`: 6個の正規runtime adapter
- `docs/migrations/openclaw/runtime-inventory.json`: 399件のlegacy/OpenClaw/launchdジョブ

これらはエージェント名簿ではない。スキル、adapter、scheduler、worker、healthcheck、外部サービスをすべて「エージェント」と呼ぶと、利用者も実装者も、誰が判断し、誰が責任を持ち、何が本当に稼働しているかを判別できない。

本仕様では、Agent Registryを新しい単一正本として追加する。既存registryを置換せず、参照によって接続する。

## 2. 目的

1. Life Manager配下の本物のエージェントを、組織と責任で一覧化する。
2. エージェントと、スキル、ツール、ジョブ、adapter、workerを明確に分ける。
3. ローカルOSS版とcloud/Web版で同じagent definitionを使う。
4. README、詳細catalog、将来のchat/dashboardを同じ正本から生成する。
5. `live` を名乗るすべてのエージェントに、検証可能なrepo内証拠を要求する。
6. 現在の健康状態はGitへ手入力せず、runtime receiptから投影する。

## 3. 非目的

- 399件のruntime rowを399体のエージェントとして登録しない。
- `skills/registry.json`をエージェント名簿へ転用しない。
- READMEの手書き表を新しい正本にしない。
- このsliceで399件すべてのmigrationを完了しない。
- Box、OpenWiki、PixelRAGの導入は本sliceに含めない。
- Gitに秘密情報、wallet key、token、個人宛先、絶対的なローカルpathを保存しない。

## 4. エージェントの定義

### 4.1 本物のエージェント

次の条件をすべて満たすものをエージェントとする。

1. モデルが目的と現在状態を読む。
2. モデルが複数の許可された行動またはツールから次の行動を判断する。
3. 実行結果または環境の観測を受け取る。
4. 観測を使って継続、変更、停止、委譲のいずれかを再判断できる。
5. 副作用にはreceiptまたは同等の検証証拠がある。

### 4.2 エージェントではないもの

- 固定cron、launchd plist、scheduler
- healthcheck、watchdog、backup、tunnel
- 固定規則のみで選択・計算するscript
- 単一API wrapper
- レポート送信、記帳、schema validation
- モデルを1回呼ぶだけで、観測と再判断のloopを持たない生成処理
- エージェントが利用する個別skill/tool

決定的な処理は劣ったものではない。判断をエージェントへ、検証・計算・送信をtoolへ置くことで、責任境界を明確にする。

## 5. 採用アーキテクチャ

### 5.1 単一正本

```text
agents/registry.json
        │
        ├── agents/agent-registry.schema.json
        ├── scripts/validate-agent-registry.mjs
        ├── scripts/render-agent-catalog.mjs
        │       ├── README.md の生成区間
        │       └── docs/agent-catalog.md
        ├── skills/registry.json への参照
        ├── loop-adapters.json への参照
        └── runtime-inventory.json へのfamily参照
```

`agents/registry.json`だけがagent definitionの正本である。READMEとcatalogは生成物であり、直接編集しない。

### 5.2 typeとinstance

Registryはエージェントの種類と責任を定義する。同じMarketing AgentがLife Manager、Honne、Capafyなど複数productを担当しても、productごとに別のagent typeを乱造しない。

```text
Marketing Agent                  ← type
  ├── product pack: life-manager ← runtime instance/config
  ├── product pack: honne
  └── product pack: capafy
```

変動するinstance、lease、PID、last successはruntime stateで管理する。

### 5.3 lifecycle

許可する値は次の6種類だけとする。

| lifecycle | 意味 |
|---|---|
| `live` | 正規Life Manager runtimeで稼働し、証拠がある |
| `shadow` | 正規runtimeで副作用を制限して検証中 |
| `legacy_live` | legacy/OpenClaw/launchdで稼働中 |
| `dormant` | 実装済みだが現在停止中 |
| `planned` | specはあるがagent loopは未実装 |
| `deprecated` | 廃止済みまたは廃止予定 |

`live`、`shadow`、`legacy_live`、`dormant`はrepo内の実装証拠を必須とする。`planned`はspec参照を必須とする。

### 5.4 schema

各entryは最低限次を持つ。

```json
{
  "agent_id": "finance.gig",
  "display_name": "Gig Work Agent",
  "organ": "finance",
  "parent_agent_id": "finance.cfo",
  "objective": "実行可能なギグを受注・納品して収益化する",
  "lifecycle": "legacy_live",
  "deployments": ["local"],
  "decision_owner": "model",
  "skills": [],
  "tools": [],
  "loop_adapters": [],
  "runtime_families": ["gig-loop"],
  "effect_classes": ["message", "publish", "money"],
  "source_refs": [],
  "evidence_refs": []
}
```

追加規則:

- `agent_id`は安定したlowercase dotted identifierとする。
- `parent_agent_id`は同じregistry内に存在するか、rootでは`null`とする。
- 循環した親子関係を禁止する。
- 参照するskill ID、adapter ID、runtime familyは既存正本に存在しなければならない。
- repo pathは相対pathのみ許可し、存在を検証する。
- `effect_classes`は`none`、`read`、`draft`、`message`、`publish`、`money`から選ぶ。
- `money`または取消困難な副作用を持つagentは、policy/receiptの証拠参照を必須とする。

## 6. 初期組織モデル

```text
Life Manager Orchestrator
│
├── Health Organ
│   ├── Physical Health Agent
│   └── Mental Health Agent
│
├── Finance / CFO Organ
│   ├── Gig Work Agent
│   ├── Writer Agent
│   ├── Capafy Agent
│   ├── Solana Trading Agent
│   └── Polymarket Agent
│
├── Growth Organ
│   ├── Marketing Agent
│   └── Clip / Affiliate Agent
│
├── Technology / CTO Organ
│   ├── Development Agent
│   └── Mobile App Builder Agent
│
└── Opportunity Organ
    ├── Event Agent
    ├── Fundraising Agent
    └── Job Application Agent
```

これは製品の理解モデルであり、実装済みという主張ではない。各entryのlifecycleとevidenceが真実を表す。

TaskMarket、x402 Seller、Yield、UBI、Lending、Report、Spawnは初期監査でagent条件を満たさない限り、agentとして登録しない。CFOまたはOrchestratorが利用するcapability/toolとして参照する。

## 7. chatとdashboardのユーザー体験

### 7.1 状態表示

```text
User: エージェントを全部見せて

Life Manager
├── Finance
│   ├── 🟢 Gig Work      1時間前に完了
│   ├── 🟡 Capafy        次回実行待ち
│   └── 🔴 Solana Trade  receiptなし、成功扱いしない
├── Growth
│   └── 🟢 Clip          投稿URLあり
└── Health
    └── ⚪ Mental        planned
```

表示は次を結合する。

```text
Agent definition (Git)
        +
Runtime receipt / lease / ledger
        +
User権限・effect policy
        =
Chat / Dashboard projection
```

### 7.2 委譲

```text
User goal
   ↓
Life Manager Orchestrator
   ├── goal分解
   ├── agent選択
   ├── 予算・risk policy確認
   └── canonical job protocolで委譲
           ↓
      Specialist Agent
           ├── 観測
           ├── 判断
           ├── tool実行
           └── receipt作成
                   ↓
          Orchestratorが結果を統合
```

### 7.3 承認境界

| effect | 初期方針 |
|---|---|
| `read` | 自動実行可能 |
| `draft` | 自動実行可能 |
| `message` | allowlist/policyに従う |
| `publish` | product policyとrollback有無に従う |
| `money` | 金額上限、wallet policy、receiptを必須とする |

Agent Registryは承認を実行する場所ではない。承認policyの参照先を宣言し、runtimeが強制する。

### 7.4 honest status

成功表示には、effectに応じた証拠を要求する。

- 投稿: 公開URLまたはprovider receipt
- message: provider message ID
- money: transaction hash、settlement receiptまたは公式readback
- internal work: output artifact hashまたはcanonical job receipt

証拠がない場合は`running`、`unknown`、`failed`のいずれかであり、`success`にしない。

## 8. エラー処理

1. Registry/schema不正: validatorが非ゼロ終了し、生成物を更新しない。
2. 不明なskill/adapter/runtime family: fail closed。
3. evidence path不存在: fail closed。
4. runtime receipt不在: definitionは表示できるが、健康状態は`unknown`。
5. stale receipt: `stale`として表示し、直近成功とは表現しない。
6. legacy job重複: agentは1体のまま、runtime family配下に複数jobとして表示する。
7. renderer途中失敗: temporary outputを破棄し、README/catalogを部分更新しない。

## 9. テスト戦略

実装はTDDで行う。

1. schemaが正しい最小registryを受理する。
2. 重複`agent_id`を拒否する。
3. 不明なparent、循環を拒否する。
4. 不明なskill、adapter、runtime familyを拒否する。
5. lifecycleごとのevidence要件を強制する。
6. absolute pathとsecretに見えるfield/valueを拒否する。
7. rendererが同じ入力から同じ出力を生成する。
8. README marker外を変更しない。
9. generated catalogが全agentを一度ずつ含む。
10. `--check`がdriftを検出する。

## 10. 成果物と完了条件

- [x] 1. 本専用spec
- [x] 2. `agents/agent-registry.schema.json`
- [x] 3. `agents/registry.json`
- [x] 4. `scripts/validate-agent-registry.mjs`
- [x] 5. agent/capability/job分類表
- [x] 6. 証拠付き初期agent roster
- [x] 7. 399件runtime inventoryとの参照
- [x] 8. README生成区間
- [x] 9. `docs/agent-catalog.md`
- [x] 10. 既存2本の正本specから本specへの参照
- [x] 11. chat projection契約
- [ ] 12. tests、verification evidence、commit、push

完了とは、12項目すべてにrepo内の証拠があり、validator、renderer drift check、専用testsがfresh runで成功し、READMEとcatalogが同一registryから再生成できる状態をいう。

## 11. 全体残数の扱い

2026-08-01時点で、`2026-08-01-dais-life-manager-five-phase-execution-spec.md`には133件の未完了checkboxがある。本sliceの12成果物はそこに未計上であるため、開始時点の追跡可能な総残数は145件とする。

本slice完了後は12件を完了とし、既存specの133件は別sliceとして残る。Box、OpenWiki、PixelRAGは別途scope化するまでこの数へ入れない。
