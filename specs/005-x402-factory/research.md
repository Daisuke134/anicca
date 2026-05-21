# Research: x402 Factory Skill

**Date**: 2026-02-24 | **Branch**: `005-x402-factory`

---

## Decision 1: OpenClaw スキルの実装形式

**Decision**: SKILL.md のみ（実行プロンプト方式）。skill.sh は使わない。

**Rationale**: Mac Mini の既存スキル（`x402-skill-marketer`, `trend-hunter` 等）を調査した結果、YAML frontmatter + マークダウン指示書という形式が標準。Anicca（Claude）がプロンプト指示を読んで exec/slack/fs ツールを呼び出す。skill.sh は不要。

**Source**: `ssh anicca@100.99.82.95 cat /Users/anicca/.openclaw/skills/x402-skill-marketer/SKILL.md`
**Confirmed**: 2026-02-24

---

## Decision 2: to-agents-learning.md の作成場所

**Decision**: `/Users/anicca/.openclaw/workspace/to-agents/to-agents-learning.md`

**Rationale**: Mac Mini の workspace を確認。`to-agents-learning.md` は未存在。スキル専用のワークスペースディレクトリ `to-agents/` を新規作成し、そこに配置する。（他スキルは `workspace/<skill-name>/` パターンで管理されている）

**Source**: `ssh anicca@100.99.82.95 ls /Users/anicca/.openclaw/workspace/`
**Confirmed**: 2026-02-24

---

## Decision 3: to-agents-learning.md の初期内容

**Decision**: `.cursor/plans/ios/1.6.3/2026-2-18/to-agents-learning.md` の内容を Mac Mini にコピーして初期化する。

**Rationale**: このファイルは MacBook 側のリポジトリ（`anicca-project`）に既に蓄積されている。Mac Mini への初回デプロイ時に SSH + scp で転送する。

**Source**: 既存ファイル `/Users/cbns03/Downloads/anicca-project/.cursor/plans/ios/1.6.3/2026-2-18/to-agents-learning.md`

---

## Decision 4: Railway エンドポイント追加パターン

**Decision**: `apps/api/src/routes/x402/buddhistCounsel.js` を verbatim 複製し、スキル固有のシステムプロンプトと入出力スキーマのみ変える。

**Rationale**: FR-003 の verbatim 要件。`index.js` の paymentMiddleware エントリも同パターンで追加。

**ファイル**: `apps/api/src/routes/x402/index.js`（paymentMiddleware に `POST /emotion-detector` エントリ追加）と `emotionDetector.js`（ハンドラ新規作成）。

**Key pattern（verbatim）**:
```javascript
// CORS → express.json → x402 middleware 順序
// ExactEvmScheme
// declareDiscoveryExtension
// syncFacilitatorOnStart=false（HTTPFacilitatorClient 使用）
```

**Source**: `apps/api/src/routes/x402/index.js` + `buddhistCounsel.js`（現在の本番コード）

---

## Decision 5: awal テストコマンド形式

**Decision**: `npx awal@2.0.3 x402 pay <endpoint> -X POST -d '<json>'`

**Rationale**: Step 10 で実証済み（200 OK + counsel_id 返却確認）。

**Confirmed endpoint**: `https://anicca-proxy-production.up.railway.app/api/x402/<skill_name>`

**Source**: x402-skill-marketer SKILL.md + Step 10 実行結果
**Test result**: `POST /api/x402/buddhist-counsel` → `200 OK`, tx=`0x2db3aaf4`

---

## Decision 6: clawhub publish コマンド

**Decision**: `clawhub publish` — SKILL.md のある directory で実行。

**Rationale**: Step 12（buddhist-counsel@1.0.0 公開済み）で実証。`clawhub publish` は標準コマンド。

**Source**: `.cursor/plans/ios/1.6.3/2026-2-18/x402-nudge-api-spec.md` Step 12 完了記録

---

## Decision 7: Moltbook 宣伝方法

**Decision**: `moltbook-interact` OpenClaw スキルを呼び出す（`openclaw agent --skill moltbook-interact --message "..."` または Anicca のターン内で指示）。

**Rationale**: x402-skill-marketer も moltbook-interact を参照している。新スキルの宣伝は moltbook-interact に promotion 指示を渡せばよい。

**Source**: x402-skill-marketer SKILL.md + moltbook-interact ワークスペース確認

---

## Decision 8: Cron ジョブ形式

**Decision**: `/Users/anicca/.openclaw/cron/jobs.json` に以下エントリを append。

```json
{
  "id": "to-agents-skill",
  "agentId": "anicca",
  "jobId": "to-agents-skill",
  "name": "to-agents-skill",
  "schedule": {
    "kind": "cron",
    "expr": "0 1 * * *",
    "tz": "Asia/Tokyo"
  },
  "sessionTarget": "isolated",
  "wakeMode": "now",
  "payload": {
    "kind": "agentTurn",
    "message": "Execute to-agents-skill in discover mode. Read the skill catalog from /Users/anicca/.openclaw/workspace/to-agents/to-agents-learning.md. Identify the next unbuilt skill. Send a proposal to Slack #metrics (C091G3PKHL2). Do not build anything without approval."
  },
  "delivery": {
    "mode": "none"
  },
  "enabled": true,
  "state": {}
}
```

**Source**: `ssh anicca@100.99.82.95 cat /Users/anicca/.openclaw/cron/jobs.json`（実際のフォーマット確認済み）

---

## Decision 9: Slack #metrics チャンネルID

**Decision**: `C091G3PKHL2`

**Source**: x402-skill-marketer SKILL.md + cron jobs.json 内の既存設定

---

## Resolved Unknowns Summary

| Unknown | Resolution |
|---------|-----------|
| to-agents-learning.md の場所 | `/Users/anicca/.openclaw/workspace/to-agents/to-agents-learning.md` (新規作成) |
| SKILL.md 実装形式 | YAML frontmatter + markdown（skill.sh 不要） |
| Railway パターン | buddhistCounsel.js verbatim 複製 |
| awal テストコマンド | `npx awal@2.0.3 x402 pay` （Step 10 実証済み） |
| clawhub publish | `clawhub publish` （Step 12 実証済み） |
| Moltbook 宣伝 | moltbook-interact スキル経由 |
| Cron 形式 | jobs.json append（mode: "none"） |
