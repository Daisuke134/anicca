# skill-test harness runbook — 1 skill × 1 loop × on-chain eval（正本）

用途: agent の earn skill を1つずつ「本当に稼げるか」検証する標準手順。
根拠: [[44-single-skill-agent-eval-best-practice]]（capability ablation + pass^k + fault taxonomy）。
テスト順: x402_sell（実行中 2026-07-14〜） → bounty → affiliate(clip) → affiliate(video)。
役割: 親(main session) = harness 準備・watch・修正のみ。**loop の earn には介入しない**。

## 手順

### 0. 前提（テスト対象 skill が満たすべき形）
- slot が `skills/registry.json` に live で登録済、`run.sh` が存在（entrypoint 名でなく run.sh 固定 — report 事故の教訓）
- skill は workflow 型: 判断ゼロの決定論 script + model の判断は最小の箱に隔離（doc 45）
- 収入の判定器が決定論であること（x402 なら verify-inflow の on-chain 実測。LLM-judge 禁止）

### 1. Isolation（capability ablation）
対象 instance の launchd plist に注入して再起動:
```xml
<key>ANICCA_SLOT_ALLOWLIST</key><string><skill_slot></string>
```
- alwaysAvailable slot(report/cook)は設計上残る（telemetry を殺さない）
- 実効確認: daemon.err に `[loop] slot allowlist active: <skill>` と `live skills: ...` が出ること

### 2. 観測点の設置（全部 session 外・無人）
- **正本 = ANICCA_HOME/state/ledger.jsonl**（skill の echo は daemon.err に出ない — 2026-07-14 の教訓）
- 収入 watch: `watch-inflow.sh` を instance の payTo + X402_WATCH_TAG で launchd 常駐（30分毎）
- 売上 attribution: seller の per-route sales log（`x402-sell/state/sales-<payTo>.jsonl`）

### 3. エピソード数（pass^k）
- **最低 k=4、厳密は k=8** の独立エピソードを待つ（τ-bench の実測: pass^1 が高くても pass^8 は激減し得る）
- x402_sell の1エピソード = 「wake が x402_sell を選ぶ → guard 通過 → shop open 記録」+ 収入は別軸（外部 demand 依存なので、エピソード成功 = shop 稼働、収入 = 別カウント）

### 4. 対照群
- 同構成で allowlist を空 menu 相当にした run（または skill 掲載前の期間データ）で external=0 を確認
- x402_sell は掲載前全期間 external=0 が対照として成立済

### 5. 判定
PASS = 3点セット:
1. pass^k ≥ 閾値（運用目安: k=4 で 4/4 の shop-open。収入は demand 依存なので別指標）
2. 収入判定は on-chain ground truth のみ（self-pay/colony 内は除外 — verify-inflow の wallet 集合を最新に保つ）
3. 全 FAIL エピソードが fault taxonomy 分類済:

| fault class | 例（実例 2026-07-14） | 直す場所 |
|---|---|---|
| harness/skill バグ | P1 guard が zero-capital slot を halt / report に run.sh 無し | 親が skill/harness を修正 |
| environment 起因 | free model 429 capacity / crawler 遅延 | 待つ or 供給側を変える |
| agent 判断ミス | slot 選択で earn を選ばない / args の発明 | prompt/summary を child-proof 化 |

### 6. 落とし穴
- eval leakage: テスト専用 prompt を作らない — 本番と同一 loop/prompt で回す
- metric gaming: trajectory(ledger の args)を読む — 例: model が売上ゼロでも narrate ばかり選ぶ「サボり」検知
- pass^1 で「動く」と言わない（founder の外部2件 = pass^1。複製 instance の再現待ち中）
- 観測は ledger 起点。daemon.err は brain 層のみ

## 実行中テストの現在地（2026-07-14）

| instance | skill | 段階 |
|---|---|---|
| claude-p (sonnet brain) | x402_sell | allowlist 稼働・掲載済・shop-open エピソード収集中 |
| franklin2 (GLM-4.7) | x402_sell | free 枠 429 で wake 不能（environment fault に分類、auto-retry 中） |
| franklin1 (llama) | 対照群（SOL trade 継続） | — |

## 次 skill へのテンプレ（bounty / affiliate をこの表で埋める）
1. skill を workflow 化されているか点検（doc 45 原則） → 2. allowlist 注入 → 3. 観測3点設置 →
4. k=4 エピソード → 5. 3点セット判定 → 6. fault 分類 → skill 修正 → 再走
