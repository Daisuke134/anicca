# ADR: Workflows vs Agents

> **決定日**: 2026-02-06
> **ステータス**: Accepted
> **適用**: Anicca 1.6.2+、将来のエージェント開発

---

## 概要

**「Agentは魅力的だが、ほとんどのケースでWorkflowの方が正解」**

---

## 比較表

| 観点 | Workflow | Agent | 解説 |
|------|----------|-------|------|
| **予測可能性** | ✅ 高い | ❌ 低い | Agentは「何をするか分からない」リスクがある |
| **デバッグ** | ✅ 容易 | ❌ 困難 | Workflowはステップが明確、Agentはブラックボックス |
| **コスト** | ✅ 低い | ❌ 高い | Agentは自律的にLLMを呼び続ける（コスト爆発） |
| **レイテンシ** | ✅ 低い | ❌ 高い | Workflowは必要な処理だけ実行 |
| **柔軟性** | ❌ 低い | ✅ 高い | Agentは未知の状況に適応可能 |
| **メンテナンス** | ✅ 容易 | ❌ 困難 | Workflowは変更箇所が明確 |

---

## いつWorkflowを使うか

| ユースケース | 選択 | 理由 |
|-------------|------|------|
| 定期実行タスク（Cron） | Workflow | 決まった手順を繰り返す |
| SNS投稿 | Workflow | 手順が固定（生成→検証→投稿） |
| データ処理パイプライン | Workflow | 入力→変換→出力が明確 |
| API連携 | Workflow | リクエスト/レスポンスが定義済み |
| 通知送信 | Workflow | 対象→内容→送信が固定 |

---

## いつAgentを使うか

| ユースケース | 選択 | 理由 |
|-------------|------|------|
| ユーザーとの対話 | Agent | 文脈依存、予測不能な入力 |
| 探索的タスク | Agent | 何をすべきか事前に分からない |
| 複雑な推論 | Agent | 多段階の判断が必要 |
| パーソナライズ返信 | Agent | ユーザーの状況に応じて変化 |

---

## Anthropic公式ガイダンス

> **"Building Effective Agents" (2025)**
>
> 「ほとんどのアプリケーションでは、単純なワークフローで十分です。
> Agentは複雑さとコストを追加するので、本当に必要な場合のみ使用してください。」

**参照**: https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk

---

## 設計原則

### 1. Workflowファースト

- まずWorkflowで実装できないか検討
- 「Agentが必要」と証明できるまでWorkflow

### 2. Agent例外

以下の条件を**すべて**満たす場合のみAgent:
- 文脈依存性が高い
- 入力が予測不能
- 多段階推論が必須

### 3. ハイブリッドパターン

- Workflowの中で必要な部分だけAgentを使う
- 例: Workflow全体は固定、返信文生成のみAgent

---

## コスト比較（実例）

### x-poster を Workflow で実装

```
LLM呼び出し: 2回（生成 + 検証）
コスト: ~$0.01/投稿
リスク: 低い（手順が固定）
```

### x-poster を Agent で実装

```
LLM呼び出し: 5-15回（自律的に試行錯誤）
コスト: ~$0.05-0.15/投稿
リスク: 高い（無限ループ、予期しない行動）
```

---

## Anicca 1.6.2 での適用

| コンポーネント | 選択 | 理由 |
|---------------|------|------|
| x-poster | **Workflow** | hook選択→生成→検証→投稿（固定手順） |
| tiktok-poster | **Workflow** | 同上 |
| app-nudge-sender | **Workflow** | ユーザー取得→通知生成→送信（固定手順） |
| trend-hunter | **Workflow** | API検索→フィルタ→保存（固定手順） |
| suffering-detector | **Workflow** | 投稿取得→検出→通知（固定手順） |
| **返信生成** | **Agent候補** | ユーザーの苦しみに応じた返信（文脈依存） |

---

## 判断フローチャート

```
新機能の実装
    │
    ▼
手順が固定されているか？
    │
    ├─ Yes → Workflow
    │
    └─ No → 入力は予測可能か？
              │
              ├─ Yes → Workflow（分岐で対応）
              │
              └─ No → 多段階推論が必要か？
                        │
                        ├─ No → Workflow + LLM呼び出し
                        │
                        └─ Yes → Agent
```

---

## 参考文献

| 文献 | 内容 | URL |
|------|------|-----|
| Anthropic Building Effective Agents | Workflow-first推奨 | https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk |
| Anthropic Multi-Agent Research | 3-5並列推奨、コンテキスト管理 | https://www.anthropic.com/engineering/multi-agent-research-system |
| Vellum AI Agent Workflows 2026 | ハイブリッドパターン | https://www.vellum.ai |

---

## 更新履歴

| 日付 | 変更 |
|------|------|
| 2026-02-06 | 初版作成（Anicca 1.6.2 設計時） |
