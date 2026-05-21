# OpenClaw vs OpenAI Agent SDK 比較調査

## 調査メタデータ

| 項目 | 値 |
|------|-----|
| **調査日時** | 2026年2月6日 10:47 JST |
| **調査者** | Claude Opus 4.5 (tech-spec-researcher) |
| **情報源** | 公式ドキュメント、技術記事、GitHub（2026年1-2月最新情報） |
| **調査目的** | OpenClawとOpenAI Agent SDKの違いを理解し、Aniccaプロジェクトへの適用可能性を評価 |

---

## 1. OpenClawとは何か？

### 概要

| 項目 | 詳細 |
|------|------|
| **正式名称** | OpenClaw（旧名: Clawdbot → Moltbot） |
| **開発者** | Peter Steinberger（オープンソース） |
| **公式サイト** | https://openclaw.ai/ |
| **公式ドキュメント** | https://docs.openclaw.ai/ |
| **GitHubスター** | 60,000+ in 72 hours（2025年11月ローンチ直後）、現在100,000+ |
| **ライセンス** | オープンソース（無料、BYO API Key） |

### 解決する問題

**従来のAIの問題:**
- 「話すだけのAI」→ 質問に答えるだけで行動しない
- クラウド依存 → プライバシーの懸念
- 受動的 → ユーザーが指示するまで何もしない

**OpenClawの解決策:**
- **能動的（Proactive）:** 自分で判断してタスクを実行
- **ローカル実行:** ユーザーのマシン上で動作（プライバシー保護）
- **永続的メモリ:** 会話を記憶し、コンテキストを保持
- **実行能力（Hands）:** ファイル操作、シェルコマンド、ブラウザ制御が可能

### アーキテクチャ

```
┌─────────────────────────────────────────────────┐
│         ユーザー（チャットアプリ経由）               │
│  WhatsApp / Telegram / Discord / Slack / etc.   │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│               Gateway（中央ハブ）                 │
│  - 認証管理（API Key、OAuth）                     │
│  - メッセージルーティング                          │
│  - セッション管理                                 │
│  - ツールアクセス制御                              │
└───────────────────┬─────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
        ▼           ▼           ▼
   ┌────────┐  ┌────────┐  ┌────────┐
   │Agent 1 │  │Agent 2 │  │Agent N │
   │(Claude)│  │ (GPT)  │  │ (Local)│
   └────────┘  └────────┘  └────────┘
        │           │           │
        └───────────┴───────────┘
                    │
        ┌───────────┼───────────────────┐
        ▼           ▼                   ▼
   ┌────────┐  ┌────────┐        ┌────────┐
   │ Tools  │  │Skills  │        │ Memory │
   │- exec  │  │カスタム│        │markdown│
   │- browser│ │自動化  │        │ファイル│
   │- file  │  └────────┘        └────────┘
   └────────┘
```

---

## 2. 主要コンポーネント解説

### 2.1 Gateway（ゲートウェイ）

**役割:**
- チャットアプリとAIエージェントをつなぐ中央ハブ
- 複数のエージェントを一元管理
- 認証情報を安全に保管

**どこで動く:**
- ユーザーのMac/PC上でローカル実行
- または VPS / クラウドサーバー上で常時稼働
- macOSではLaunchAgentとして自動起動可能

**設定例:**
```bash
# インストール
npm install -g openclaw@latest

# オンボーディング（対話式セットアップ）
openclaw onboard --install-daemon

# Gateway起動（macOS LaunchAgent）
launchctl kickstart -k gui/$(id -u)/ai.openclaw.gateway

# 状態確認
openclaw models status
```

**認証管理:**
```bash
# Anthropic API Key登録
openclaw models auth paste-token --provider anthropic

# 環境変数で設定（デーモン用）
echo "ANTHROPIC_API_KEY=sk-ant-xxx" >> ~/.openclaw/.env
```

**詳細:** https://docs.openclaw.ai/gateway/authentication

### 2.2 Agent（エージェント）

**定義:**
- LLMインスタンス + ペルソナ + メモリ + ツールアクセス権
- 1つのGatewayに複数のエージェントを配置可能

**構成例:**
```json
{
  "agents": [
    {
      "name": "Molty",
      "model": "claude-opus-4-5",
      "persona": "あなたは親切なアシスタントです",
      "memory": "~/.openclaw/workspace/molty/",
      "tools": ["exec", "browser", "file"]
    },
    {
      "name": "CodeBot",
      "model": "gpt-4",
      "persona": "あなたはコーディング専門です",
      "memory": "~/.openclaw/workspace/codebot/",
      "tools": ["exec", "file"]
    }
  ]
}
```

**永続的メモリ:**
- Markdownファイルで保存（`~/.openclaw/workspace/`）
- 会話履歴、学習内容、ユーザー設定を記録
- 再起動してもコンテキストが保持される

### 2.3 Tools（ツール）

**Built-in Tools:**

| ツール | 用途 | 危険度 |
|--------|------|--------|
| `exec` | シェルコマンド実行 | 高（任意コード実行可能） |
| `file` | ファイル読み書き | 中 |
| `browser` | Web自動化（Playwright） | 中 |
| `web` | Web検索・スクレイピング | 低 |
| `llm_task` | サブエージェント呼び出し | 中 |
| `slack` | Slackメッセージ送信 | 低 |
| `camera` | カメラ撮影（ペアリング端末） | 中 |
| `location` | GPS位置取得 | 中 |

**アクセス制御:**
```yaml
# 最小限のツールセット
tools:
  allow: ["web", "slack"]
  deny: ["exec", "file"]

# コーディング用プロファイル
tools:
  allow: ["group:fs", "group:runtime", "exec"]
```

**詳細:** https://docs.openclaw.ai/tools

### 2.4 Skills（スキル）

**定義:**
- 再利用可能な自動化ワークフロー
- Markdownファイル（`SKILL.md`）で定義
- AIが読んで実行手順を理解する

**Skillの構造:**
```markdown
---
name: daily-report
description: 毎日のメトリクスレポートをSlackに投稿
trigger: cron
schedule: "0 6 * * *"  # 毎朝6時
---

# Daily Report Skill

## 実行手順
1. Mixpanel APIで昨日のKPIを取得
2. RevenueCat APIで課金状況を取得
3. データを整形してマークダウンレポート作成
4. Slackの #metrics チャンネルに投稿

## ツール
- `web` (API呼び出し)
- `slack` (投稿)
```

**Skill vs Tool:**

| 項目 | Tool | Skill |
|------|------|-------|
| 定義 | ハードコーディングされた機能 | Markdownで記述されたワークフロー |
| 例 | `exec`, `browser`, `file` | `daily-report`, `flight-checkin` |
| 追加方法 | コード変更が必要 | `.md`ファイルを追加するだけ |
| 実行 | LLMが直接呼び出す | LLMがMarkdownを読んで実行 |

**Skillディレクトリ:**
```
~/.openclaw/skills/
├── daily-report/
│   └── SKILL.md
├── flight-checkin/
│   └── SKILL.md
└── custom-automation/
    └── SKILL.md
```

**Skill一覧確認:**
```bash
openclaw skills list
```

**詳細:** https://docs.openclaw.ai/skills

---

## 3. OpenAI Agent SDKとは何か？

### 概要

| 項目 | 詳細 |
|------|------|
| **正式名称** | OpenAI Agent SDK（旧名: AgentKit） |
| **開発者** | OpenAI（公式） |
| **リリース日** | 2025年10月6日 |
| **ライセンス** | OpenAI API利用規約に準拠 |
| **タイプ** | コードファースト・ライブラリ |

### 解決する問題

**従来のエージェント開発の問題:**
- エージェントを作るには複雑なコーディングが必要
- ツール呼び出し、状態管理、エラー処理を全て自分で実装
- 再利用可能なコンポーネントが不足

**OpenAI Agent SDKの解決策:**
- **軽量SDK:** シンプルなPython/Node.jsライブラリ
- **ツールエコシステム:** 事前定義されたツール群
- **会話フロー管理:** マルチターン対話の自動管理
- **エラーハンドリング:** 自動リトライ、フォールバック

### アーキテクチャ

```
┌─────────────────────────────────────────────────┐
│          ユーザーアプリケーション                   │
│    (Python/Node.js/Web Frontend)                │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│         OpenAI Agent SDK（ライブラリ）            │
│  - AgentクラスでLLM呼び出しをラップ                │
│  - ツール登録・管理                               │
│  - 会話履歴管理                                   │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│           OpenAI API（クラウド）                  │
│  - GPT-4 / GPT-4o / o1                          │
│  - Function Calling                             │
│  - Structured Outputs                           │
└─────────────────────────────────────────────────┘
```

**コード例:**
```python
from openai_agent import Agent

# エージェント初期化
agent = Agent(
    model="gpt-4",
    tools=["web_search", "calculator"]
)

# ユーザーとの会話
response = agent.run("今日の天気は？")
print(response)
```

---

## 4. OpenClaw vs OpenAI Agent SDK 比較

### 4.1 アーキテクチャの違い

| 観点 | OpenClaw | OpenAI Agent SDK |
|------|----------|------------------|
| **実行場所** | ローカル or VPS（ユーザー管理） | クラウド（OpenAI管理） |
| **Gateway** | 必須（中央ハブとして機能） | 不要（ライブラリとして組み込み） |
| **デプロイ形態** | スタンドアロン・デーモン | アプリケーションに埋め込み |
| **永続性** | 24/7稼働可能（デーモン化） | アプリケーションのライフサイクルに依存 |
| **マルチエージェント** | 1つのGatewayで複数エージェント管理 | 各エージェントを独立して実装 |

**視覚的比較:**

**OpenClaw:**
```
[WhatsApp] → [Gateway] → [Agent1] → [Tools]
[Telegram] ↗            → [Agent2] → [Skills]
[Discord] ↗             → [Agent3] → [Memory]
```

**OpenAI Agent SDK:**
```
[Your App] → [SDK] → [OpenAI API]
```

### 4.2 使用目的の違い

| 用途 | OpenClaw | OpenAI Agent SDK |
|------|----------|------------------|
| **パーソナルAIアシスタント** | ◎ メインユースケース | △ 可能だが過剰 |
| **チャットボット統合** | ◎ 複数プラットフォーム対応 | ○ 1つのアプリに組み込み |
| **業務自動化（Cron）** | ◎ スケジュール機能内蔵 | △ 別途スケジューラが必要 |
| **ブラウザ自動化** | ◎ Playwright統合 | △ 自分で実装 |
| **エンタープライズAI** | △ セキュリティ懸念あり | ◎ OpenAI管理下 |
| **開発者向けSDK** | △ ライブラリとして使うには複雑 | ◎ シンプルな組み込み |

### 4.3 プライバシー・セキュリティ

| 観点 | OpenClaw | OpenAI Agent SDK |
|------|----------|------------------|
| **データの場所** | ローカル（ユーザーのマシン） | OpenAIクラウド |
| **メモリ保存** | Markdownファイル（ローカル） | OpenAI API履歴（30日間） |
| **認証情報** | `~/.openclaw/.env`（ローカル） | 環境変数 or OpenAIプロジェクト |
| **コマンド実行権限** | 危険（`exec`ツールで任意コード実行可能） | 制限的（Function Callingのみ） |
| **監査ログ** | ローカルログファイル | OpenAI Dashboard |

**OpenClawのセキュリティリスク:**
- 2026年1-2月、複数のセキュリティ研究が公開
- Skill Registryが攻撃ベクトルになる可能性
- `exec`ツールの悪用リスク（マルウェア配布）
- サプライチェーン攻撃の懸念

**参考文献:**
- https://www.tenable.com/blog/agentic-ai-security-how-to-mitigate-clawdbot-moltbot-openclaw-vulnerabilities
- https://1password.com/blog/from-magic-to-malware-how-openclaws-agent-skills-become-an-attack-surface
- https://jfrog.com/blog/giving-openclaw-the-keys-to-your-kingdom-read-this-first/

### 4.4 開発者体験

| 観点 | OpenClaw | OpenAI Agent SDK |
|------|----------|------------------|
| **学習曲線** | 急（Gateway、Agent、Skill概念） | 緩やか（Python/Node.js標準） |
| **セットアップ時間** | 10-20分（オンボーディング） | 5分（API Key設定のみ） |
| **カスタマイズ性** | 高（Skill追加が容易） | 中（Function定義が必要） |
| **デバッグ** | ローカルログで追跡可能 | OpenAI Dashboard |
| **コミュニティ** | 急成長中（Discord活発） | OpenAI公式サポート |

### 4.5 コスト構造

| 項目 | OpenClaw | OpenAI Agent SDK |
|------|----------|------------------|
| **ソフトウェア** | 無料（オープンソース） | 無料（SDK自体） |
| **LLM利用料** | BYO API Key（任意のプロバイダー） | OpenAI API料金 |
| **インフラ** | VPS代（$5-20/月）または自前マシン | 不要 |
| **選択肢** | Claude、GPT、Gemini、Local LLM | GPT-4 / GPT-4o / o1のみ |

**コスト例（月間10万トークン想定）:**

OpenClaw（Claude Opus 4.5使用）:
```
LLM: $15 入力 + $75 出力 = $90/月
VPS: $10/月（Hetzner、DigitalOcean等）
合計: $100/月
```

OpenAI Agent SDK（GPT-4o使用）:
```
LLM: $2.50 入力 + $10 出力 = $12.50/月
VPS: $0（不要）
合計: $12.50/月
```

### 4.6 スケーラビリティ

| 観点 | OpenClaw | OpenAI Agent SDK |
|------|----------|------------------|
| **同時ユーザー数** | 1人（パーソナルユース） | 無制限（アプリに依存） |
| **レート制限** | LLMプロバイダーのAPI制限 | OpenAI API制限（Tier制） |
| **マルチテナント** | 不向き（1 Gateway = 1 User想定） | 向いている（アプリで管理） |

---

## 5. 両者の協業可能性

### 5.1 併用パターン

**OpenClawとOpenAI Agent SDKは競合ではなく、補完関係になりうる。**

| パターン | 説明 |
|---------|------|
| **OpenClaw as Gateway + OpenAI SDK as Worker** | OpenClawのGatewayでメッセージをルーティングし、OpenAI Agent SDKで実装したワーカーにタスクを委譲 |
| **OpenClaw for Personal, SDK for Production** | 開発者個人はOpenClawを使い、プロダクションアプリにはOpenAI SDKを組み込む |
| **OpenClaw + MCP** | OpenClawのSkill内でMCP（Model Context Protocol）ツールを呼び出し、OpenAI SDKと連携 |

### 5.2 実装例（Anicca × OpenClaw）

**現在のAnicca構成（CLAUDE.mdより）:**
```
Gateway: macOS LaunchAgent（port 18789）
Agent: GPT-4o（read/write/exec/slack ツール、MCP不可）
Slack: #metrics, #ai チャンネルで応答
```

**改善案:**

| # | 改善項目 | 現状 | 改善後 |
|---|---------|------|--------|
| 1 | **MCP対応** | MCPツール使用不可 | OpenClaw v2.x（MCP統合済み）にアップグレード |
| 2 | **Skill管理** | 手動でSKILL.md編集 | `openclaw skills create`コマンド使用 |
| 3 | **セキュリティ** | `exec`ツール無制限 | Tools Allowlist設定（`~/.openclaw/openclaw.json`） |
| 4 | **監視** | ログファイル手動確認 | OpenClaw Dashboard（http://localhost:3333）導入 |

**セキュリティ強化設定例:**
```json
{
  "agents": [
    {
      "name": "Anicca Bot",
      "tools": {
        "allow": ["slack", "web", "llm_task"],
        "deny": ["exec", "browser"]
      }
    }
  ]
}
```

---

## 6. 推奨事項

### 6.1 Aniccaプロジェクトへの適用

| シナリオ | 推奨ツール | 理由 |
|---------|-----------|------|
| **日次メトリクスレポート** | OpenClaw（Skill） | Cron機能内蔵、Slack統合が容易 |
| **iOSアプリ内チャット** | OpenAI Agent SDK | クラウドベース、スケーラブル |
| **開発者支援ボット** | OpenClaw | ローカル実行、プライバシー保護 |

### 6.2 導入ステップ

**Phase 1: OpenClaw学習（1週間）**

| # | タスク | 期間 | ゴール |
|---|--------|------|--------|
| 1 | 公式ドキュメント読破 | 1日 | 概念理解 |
| 2 | テスト環境構築 | 1日 | ローカルでHello World |
| 3 | Slack統合テスト | 2日 | #test-openclaw チャンネルで応答 |
| 4 | Simple Skill作成 | 2日 | 手動実行で動作確認 |
| 5 | Cron Skill作成 | 1日 | 毎日6時にメトリクス投稿 |

**Phase 2: セキュリティ強化（1週間）**

| # | タスク | 期間 | ゴール |
|---|--------|------|--------|
| 1 | Tools Allowlist設定 | 1日 | `exec`を無効化 |
| 2 | Skill Review Flow確立 | 2日 | 新Skill追加前にレビュー |
| 3 | Secrets分離 | 1日 | `.env`でAPI Key管理 |
| 4 | ログ監視設定 | 1日 | 異常検知アラート |
| 5 | バックアップ自動化 | 1日 | Workspace定期バックアップ |

**Phase 3: Production化（2週間）**

| # | タスク | 期間 | ゴール |
|---|--------|------|--------|
| 1 | VPSデプロイ | 2日 | Hetzner/DigitalOceanで24/7稼働 |
| 2 | 複数Agent構成 | 3日 | Metrics Bot / Support Botを分離 |
| 3 | MCP統合 | 3日 | RevenueCat/Mixpanel MCPツール利用 |
| 4 | エラーハンドリング | 2日 | 障害時の自動復旧 |
| 5 | ドキュメント作成 | 2日 | 運用マニュアル |

---

## 7. リスク評価

### 7.1 OpenClaw導入リスク

| リスク | 発生確率 | 影響度 | 対策 |
|--------|----------|--------|------|
| **Skill Registry攻撃** | 中 | 高 | 公式Skill以外は使わない |
| **exec ツール悪用** | 低 | 致命的 | Tools Allowlistで無効化 |
| **Gateway停止** | 低 | 中 | 監視アラート + 自動再起動 |
| **メモリファイル破損** | 低 | 中 | 定期バックアップ |
| **API Key漏洩** | 低 | 高 | `.env`を`.gitignore`に追加 |

### 7.2 OpenAI Agent SDK導入リスク

| リスク | 発生確率 | 影響度 | 対策 |
|--------|----------|--------|------|
| **OpenAI API障害** | 低 | 中 | フォールバック先（Claude）を用意 |
| **レート制限** | 中 | 中 | Tier 4以上にアップグレード |
| **コスト超過** | 中 | 中 | 月次予算アラート設定 |
| **データプライバシー** | 低 | 中 | Zero Data Retention設定 |

---

## 8. 参考リンク

### 8.1 OpenClaw公式

| リンク | 説明 |
|--------|------|
| https://openclaw.ai/ | 公式サイト |
| https://docs.openclaw.ai/ | 公式ドキュメント |
| https://github.com/openclaw/openclaw | GitHubリポジトリ |
| https://discord.gg/openclaw | Discordコミュニティ |

### 8.2 OpenAI Agent SDK公式

| リンク | 説明 |
|--------|------|
| https://platform.openai.com/docs/agents | 公式ドキュメント |
| https://github.com/openai/openai-python | Python SDK |
| https://github.com/openai/openai-node | Node.js SDK |

### 8.3 比較記事（2025-2026年）

| タイトル | URL | 発行日 |
|---------|-----|--------|
| OpenAI AgentKit vs Claude Agents SDK | https://blog.getbind.co/openai-agentkit-vs-claude-agents-sdk-which-is-better/ | 2025-10-07 |
| 12 Best AI Agent Frameworks in 2026 | https://medium.com/data-science-collective/the-best-ai-agent-frameworks-for-2026-tier-list-b3a4362fac0d | 2026-01-27 |
| AI Framework Comparison 2025 | https://enhancial.substack.com/p/choosing-the-right-ai-framework-a | 2025-10-01 |

### 8.4 セキュリティ研究

| タイトル | URL | 発行日 |
|---------|-----|--------|
| Tenable: OpenClaw Vulnerabilities | https://www.tenable.com/blog/agentic-ai-security-how-to-mitigate-clawdbot-moltbot-openclaw-vulnerabilities | 2026-02-04 |
| 1Password: From Magic to Malware | https://1password.com/blog/from-magic-to-malware-how-openclaws-agent-skills-become-an-attack-surface | 2026-02-02 |
| JFrog: Giving OpenClaw The Keys | https://jfrog.com/blog/giving-openclaw-the-keys-to-your-kingdom-read-this-first/ | 2026-02-03 |
| Knostic: openclaw-shield | https://www.knostic.ai/blog/why-we-built-openclaw-shield-securing-ai-agents-from-themselves | 2026-02-05 |

---

## 9. 更新履歴

| 日付 | 更新内容 |
|------|---------|
| 2026-02-06 | 初版作成（Claude Opus 4.5） |

---

## 10. 次のアクション

| # | アクション | 担当 | 期限 |
|---|-----------|------|------|
| 1 | OpenClaw テスト環境構築 | 開発者 | 1週間以内 |
| 2 | Slack統合 PoC | 開発者 | 2週間以内 |
| 3 | セキュリティレビュー | セキュリティチーム | 1ヶ月以内 |
| 4 | 本番環境デプロイ判断 | プロダクトオーナー | 1ヶ月以内 |

---

**調査完了: 2026年2月6日 10:47 JST**
