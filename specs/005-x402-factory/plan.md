# Implementation Plan: x402 Factory Skill (to-agents-skill)

**Branch**: `005-x402-factory` | **Date**: 2026-02-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-x402-factory/spec.md`

## Summary

to-agents-skill は、OpenClaw スキルとして Mac Mini 上で動作する x402 スキル量産工場。
`skill_name + description + usecase` を受け取り、buddhist-counsel パターンを型として Railway エンドポイント追加 → `awal x402 pay` テスト → SKILL.md 生成 → ClawHub 公開 → Moltbook 宣伝 → to-agents-learning.md 追記 → Slack #metrics 報告 を全自動で行う。
3モード: `produce`（実際に作る）/ `discover`（カタログから次のスキルを提案→承認待ち）/ `measure`（週次パフォーマンス計測→改善提案）。

## Technical Context

**Language/Version**: Node.js 20+ (ESM, `.mjs` または `"type":"module"`)
**Primary Dependencies**:
- OpenClaw ランタイム（exec ツール、slack ツール、fs ツール）
- `npx awal@2.0.3` — x402 テスト CLI
- `clawhub` CLI（Mac Mini 既設）— ClawHub 公開・検索
- `moltbook-interact` OpenClaw スキル — Moltbook 宣伝投稿
- `apps/api/src/routes/x402/` — Railway エンドポイント追加先（既存パターン再利用）

**Storage**: ファイルベース
- `to-agents-learning.md` → `/Users/anicca/.openclaw/workspace/to-agents/to-agents-learning.md`
- スキルカタログ → `to-agents-learning.md` 内のテーブルで管理
- 生成SKILL.md → `/Users/anicca/.openclaw/skills/<skill_name>/SKILL.md`
- Proposal記録 → `/Users/anicca/.openclaw/workspace/to-agents/proposals.json`

**Testing**: `awal x402 pay` で実エンドポイントテスト（200 OK が唯一の合格基準）
**Target Platform**: Mac Mini (`anicca-mac-mini-1`, Tailscale `100.99.82.95`)
**Project Type**: OpenClaw スキル（SKILL.md + 実行プロンプト）
**Performance Goals**: 1 スキル/run を 10分以内に完走
**Constraints**:
- `awal` 非200 → 即halt（ClawHub publish 禁止）
- ✅ 承認なしに `produce` モード実行禁止（`discover` モード時）
- ファイル全体上書き禁止（to-agents-learning.md / jobs.json は差分追記のみ）

**Scale/Scope**: 10 スキル（カタログ）× 週1ペース = 10週で全カタログ完了

## Constitution Check

プロジェクトルール（CLAUDE.md）との照合:

| ルール | 状態 | 根拠 |
|--------|------|------|
| オリジナリティ禁止 | ✅ OK | buddhist-counsel パターンを verbatim 再利用 |
| Mac Mini 反映必須 | ✅ 計画済 | SSH でインストール + Cron 追加まで実装 |
| ファイル全体上書き禁止 | ✅ 遵守 | to-agents-learning.md / jobs.json は append のみ |
| 承認ゲート | ✅ 設計済 | discover mode → Slack ✅ 必須。bypass 禁止 |
| テストなし完了禁止 | ✅ 設計済 | awal 200 OK 確認まで publish しない |

## Project Structure

### Documentation (this feature)

```text
specs/005-x402-factory/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── factory-invocation.md   # スキル呼び出し契約
│   └── endpoint-template.md    # x402 エンドポイント追加契約
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository + Mac Mini)

```text
# 1. Railway API エンドポイント追加（このリポジトリ）
apps/api/src/routes/x402/
├── index.js                  # 既存: paymentMiddleware に新スキルエントリ追加
└── <skillName>.js            # 新規: 各スキルのハンドラ（buddhist-counsel.js を型に）

# 2. OpenClaw スキル（Mac Mini にデプロイ）
/Users/anicca/.openclaw/skills/to-agents-skill/
├── SKILL.md                  # スキル定義（YAML frontmatter + 実行プロンプト）
└── templates/
    └── skill-template.md     # 生成されるSKILL.mdのテンプレート

# 3. ワークスペース（Mac Mini）
/Users/anicca/.openclaw/workspace/to-agents/
├── to-agents-learning.md     # 学びの蓄積ファイル（新規作成）
├── proposals.json            # discover mode の提案記録
└── metrics.json              # measure mode のメトリクスキャッシュ
```

**Structure Decision**: Mac Mini の OpenClaw skill として実装。Railway エンドポイントは `apps/api/src/routes/x402/` に既存パターン（buddhist-counsel）を verbatim 複製して追加する。スキル生成はAnicca（Claude）が直接ファイルを書く方式（exec ツール）。

## Complexity Tracking

| 要素 | 判断 |
|------|------|
| 外部サービス5つ（Railway, awal, clawhub, Moltbook, Slack） | 全て既設インテグレーション。新規接続なし |
| 3モード（produce/discover/measure） | 全て同一SKILL.mdに記述。分岐はプロンプト内で制御 |
