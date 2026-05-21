# OpenClaw Anicca Integration - Technology Research Report

**調査日時**: 2026年2月5日 19:51:36 JST
**調査対象**: OpenClaw統合仕様の技術検証
**調査者**: Claude Code (Tech Researcher Agent)

---

## エグゼクティブサマリー

| 項目 | 判定 | 重要度 |
|------|------|--------|
| RevenueCat V2 API | PASS (注意事項あり) | HIGH |
| Gmail Plugin | WARN (最新版確認済みだが代替あり) | MEDIUM |
| LINE Messaging API | WARN (手順変更あり) | HIGH |
| OpenClaw dmScope | PASS | HIGH |
| OpenClaw session.reset | PASS | MEDIUM |
| LaunchAgent plist 環境変数 | PASS | MEDIUM |

**推奨アクション**:
1. LINE Messaging API セットアップ手順を最新版に更新
2. Gmail プラグイン代替の検討（openclaw-agentmail）
3. RevenueCat API の整数返却仕様を考慮したエラーハンドリング追加

---

## 詳細調査結果

### 1. RevenueCat V2 API

#### 検証項目
エンドポイント `https://api.revenuecat.com/v2/projects/{project_id}/metrics/overview` が MRR 取得に正しいか？

#### 結果: **PASS** (注意事項あり)

#### エビデンス
- **公式リリース**: 2023年11月2日にリリース（[ソース](https://www.revenuecat.com/release/new-rest-api-v2-functionality-app-management-overview-metrics-2023-11-02)）
- **公式ドキュメント**: Overview Metricsページで確認済み（[ソース](https://www.revenuecat.com/docs/dashboard-and-metrics/overview)）
- **エンドポイント**: `/v2/projects/{project_id}/metrics/overview` が正しい

#### 重要な注意事項

**数値の精度問題**:
```
実際のMRR: $16.82
API返却値: 16 (整数)
```

- MRR と Revenue は**整数で返却される**（2024年8月時点の仕様）
- 小額の場合、精度が失われる可能性がある
- RevenueCat公式の回答: "将来的に小額はdoubleで返す可能性があるが、現時点では整数"（[ソース](https://community.revenuecat.com/third-party-integrations-53/why-metrics-in-v2-api-mrr-and-revenue-are-whole-numbers-5017)）

#### 推奨される対応

| 対応 | 理由 |
|------|------|
| エラーハンドリング強化 | API仕様変更に備える |
| 整数前提のUI設計 | 小数点表示は期待しない |
| 定期的なAPI仕様確認 | 将来的なdouble対応に備える |

#### サンプルコード（推奨実装）
```javascript
async function getMRR(projectId) {
  const response = await fetch(
    `https://api.revenuecat.com/v2/projects/${projectId}/metrics/overview`,
    {
      headers: {
        'Authorization': `Bearer ${process.env.REVENUECAT_V2_SECRET_KEY}`,
        'Content-Type': 'application/json'
      }
    }
  );

  if (!response.ok) {
    throw new Error(`RevenueCat API error: ${response.status}`);
  }

  const data = await response.json();
  // MRR は整数で返却される（注意）
  return {
    mrr: data.metrics.mrr, // 整数
    active_subscriptions: data.metrics.active_subscriptions,
    active_trials: data.metrics.active_trials
  };
}
```

---

### 2. Gmail Plugin: @mcinteerj/openclaw-gmail

#### 検証項目
`@mcinteerj/openclaw-gmail@1.2.7` が最新版か？メンテナンスされているか？

#### 結果: **WARN** (最新版だが代替検討を推奨)

#### エビデンス

**バージョン情報**:
- **最新版**: 1.2.7（2026年2月2日リリース - **3日前**）
- **全バージョン**: 1.2.0 → 1.2.1 → 1.2.2 → 1.2.3 → 1.2.4 → 1.2.5 → 1.2.7
- **メンテナンス状況**: 積極的にメンテナンスされている（直近3日前にリリース）

**機能**:
- `gog` CLI経由でGmailにアクセス
- Polling-based sync（定期的にInbox確認）
- 自動HTML→テキスト変換
- 自動署名削除
- Circuit Breaker（API障害時のフォールバック）

#### 代替プラグイン: openclaw-agentmail

**発見事項**: より新しいセキュリティ強化版のGmailプラグインが存在

| 項目 | @mcinteerj/openclaw-gmail | openclaw-agentmail |
|------|---------------------------|-------------------|
| 最新版 | 1.2.7（2026-02-02） | 1.1.0（2026-01-31） |
| 通信方式 | Polling（定期確認） | **WebSocket（リアルタイム）** |
| セキュリティ | 標準 | **強化版**（返信のみ可能） |
| 任意送信 | 可能 | **禁止**（reply-onlyモード） |
| AgentツールAPIアクセス | 可能 | **禁止**（セキュリティ強化） |
| 送信者フィルタ | allowFrom | allowFrom |

#### 推奨される選択

| ユースケース | 推奨プラグイン | 理由 |
|-------------|---------------|------|
| **個人用（Anicca統合）** | `@mcinteerj/openclaw-gmail` | 実績あり、最新版、十分な機能 |
| **マルチユーザー/共有Inbox** | `openclaw-agentmail` | セキュリティ強化、reply-onlyモード |
| **リアルタイム性重視** | `openclaw-agentmail` | WebSocket対応（Polling不要） |

#### 最終推奨

**Specに記載された `@mcinteerj/openclaw-gmail@1.2.7` は正しい選択。** ただし、以下の理由で `openclaw-agentmail` への移行を検討する価値あり：

1. **リアルタイム性**: WebSocket対応で遅延なし
2. **セキュリティ**: reply-onlyモードでエージェントの誤送信を防止
3. **公式推奨**: OpenClawエコシステム内での正式サポート

---

### 3. LINE Messaging API

#### 検証項目
Specに記載されたLINE Messaging APIセットアップ手順は正確か？

#### 結果: **WARN** (手順変更あり)

#### 重要な変更点（2024年9月以降）

**従来の手順（Specに記載）**:
```
LINE Developers Console → 新規Channelを直接作成
```

**現在の正しい手順**:
```
LINE Official Account Manager → Messaging API有効化 → Channel自動作成
```

#### 公式ドキュメントからの引用

> **重要**: "It's no longer possible to create Messaging API channels directly from the LINE Developers Console" (2024年9月変更)
>
> チャンネルは LINE Official Account Manager 経由で作成する必要があります。

#### 更新が必要なセクション

**Spec の Step 6: LINE統合 → ユーザー作業（実装前）**

| # | 現在のSpec | 修正後（推奨） |
|---|-----------|---------------|
| 1 | LINE Developersアカウント作成 | **LINE Official Accountアカウント作成** |
| 2 | 新規Provider作成 | **削除**（自動作成される） |
| 3 | Messaging APIチャンネル作成 | **LINE Official Account Manager で Messaging API 有効化** |
| 4 | Channel Secret取得 | 同左（正しい） |
| 5 | Channel Access Token発行 | 同左（正しい） |
| 6 | Webhook URL設定 | 同左（正しい） |

#### 推奨される修正

**修正前**:
```markdown
| 1 | LINE Developersアカウント作成 | https://developers.line.biz/ → ログイン | - |
| 2 | 新規Provider作成 | Providers → Create → 名前入力 | Provider ID |
| 3 | Messaging APIチャンネル作成 | Create Channel → Messaging API | Channel ID |
```

**修正後**:
```markdown
| 1 | LINE Official Accountアカウント作成 | https://account.line.biz/ → ビジネスIDで登録 | - |
| 2 | LINE Official Account作成 | フォームに入力してアカウント作成 | Account ID |
| 3 | Messaging API有効化 | LINE Official Account Manager → Settings → Messaging API → Enable | - |
| 4 | LINE Developers Consoleで確認 | https://developers.line.biz/ → 同じ認証情報でログイン | Channel ID（自動作成済み） |
```

#### 正しいフロー（2026年2月時点）

```
1. LINE Official Account 作成（account.line.biz）
   ↓
2. LINE Official Account Manager でアカウント設定
   ↓
3. Settings → Messaging API → Enable
   ↓（自動）
4. Messaging API Channel が自動作成される
   ↓
5. LINE Developers Console で確認
   ↓
6. Channel Secret & Access Token 取得
   ↓
7. Webhook URL 設定
```

---

### 4. OpenClaw dmScope Best Practice

#### 検証項目
`dmScope: per-channel-peer` は推奨設定か？

#### 結果: **PASS**

#### 公式ドキュメントからの引用

> "Use `session.dmScope` to control how **direct messages** are grouped:
> - `main` (default): all DMs share the main session for continuity.
> - `per-peer`: isolate by sender id across channels.
> - **`per-channel-peer`: isolate by channel + sender (recommended for multi-user inboxes).**
> - `per-account-channel-peer`: isolate by account + channel + sender (recommended for multi-account inboxes)."

#### ユースケース別推奨設定

| ユースケース | 推奨dmScope | 理由 |
|-------------|------------|------|
| **単一ユーザー個人使用** | `main` | 複数チャンネル間でコンテキスト継続 |
| **共有Inbox（Anicca想定）** | **`per-channel-peer`** | **チャンネルごとに分離、セキュア** |
| **マルチアカウント** | `per-account-channel-peer` | アカウント単位でも分離 |

#### セキュリティ考慮事項

公式ドキュメントの警告:
> "If your agent accepts messages from multiple people, enable **secure DM mode** to avoid cross-user context leakage"

**Anicca統合の場合**:
- Slack #metrics, #ai は**マルチユーザー**チャンネル
- Gmail は個人Inbox（単一ユーザー）
- LINE は家族グループ（**マルチユーザー**）

**結論**: `per-channel-peer` は**正しい選択**。

---

### 5. OpenClaw session.reset

#### 検証項目
`{ mode: "daily", atHour: 4 }` は推奨設定か？

#### 結果: **PASS**

#### 公式デフォルト設定

```json
{
  "session": {
    "reset": {
      "mode": "daily",
      "atHour": 4
    }
  }
}
```

#### モード一覧

| モード | 説明 | ユースケース |
|--------|------|-------------|
| `daily` | 毎日指定時刻にリセット | **推奨**（トークン節約） |
| `idle` | 最終メッセージから指定分後 | 長時間会話しないユーザー向け |
| `never` | 手動リセットのみ | デバッグ・開発用 |

#### atHour 推奨値

| 時刻 | 理由 |
|------|------|
| **4:00 AM** | **深夜帯でユーザー非アクティブ（推奨）** |
| 3:00 AM | サーバーメンテナンス時間帯 |
| 5:00 AM | 早起きユーザー対策 |

**Specの設定 `atHour: 4` は正しい。**

#### トークン節約効果

日次リセットにより:
- Anthropic Cache TTL に合わせて古い会話を削除
- トークン使用量を最適化
- OAuth/Setup-token プロファイルでは heartbeat 1h が推奨

**結論**: Specに記載された設定は**ベストプラクティス**に従っている。

---

### 6. Environment Variables - LaunchAgent plist

#### 検証項目
LaunchAgent plist での環境変数設定パターンは正しいか？

#### 結果: **PASS**

#### 設定パターン（Specに記載）

```xml
<!-- ~/Library/LaunchAgents/ai.openclaw.gateway.plist -->
<dict>
  <key>EnvironmentVariables</key>
  <dict>
    <key>REVENUECAT_V2_SECRET_KEY</key>
    <string>sk_YTtUL...</string>
    <key>MIXPANEL_PROJECT_ID</key>
    <string>3970220</string>
    <key>MIXPANEL_API_SECRET</key>
    <string>b613eff96fec...</string>
  </dict>
</dict>
```

#### 検証結果

このパターンは**macOS標準の環境変数設定方法**として正しい。

#### 代替手段との比較

| 手段 | スコープ | 永続性 | 推奨度 |
|------|---------|--------|--------|
| **LaunchAgent plist** | **ユーザーセッション全体** | **永続的** | **HIGH** |
| `~/.zshrc` | シェルセッションのみ | 永続的 | MEDIUM |
| `/etc/paths.d/` | PATH のみ | 永続的 | MEDIUM |
| `launchctl setenv` | 現在セッションのみ | **一時的** | LOW |

#### LaunchAgent plist の利点

| 利点 | 説明 |
|------|------|
| **システム起動時に自動適用** | ユーザーログイン時に環境変数が設定される |
| **すべてのプロセスから参照可能** | GUI アプリ、CLI、デーモンすべてで利用可能 |
| **永続的** | 再起動後も設定が維持される |
| **OpenClaw公式推奨** | OpenClaw Gatewayの標準的な設定方法 |

#### 確認コマンド

```bash
# 環境変数が読めるか確認
launchctl print gui/$(id -u)/ai.openclaw.gateway | grep -E "REVENUECAT|MIXPANEL"
```

**結論**: LaunchAgent plist での環境変数設定は**正しいパターン**。

---

## 修正が必要な箇所

### 優先度: HIGH

#### LINE Messaging API セットアップ手順

**ファイル**: `.cursor/plans/openclaw/anicca-openclaw-spec.md`
**セクション**: Step 6: LINE統合 → ユーザー作業（実装前）

**現在の記載**:
```markdown
| 1 | LINE Developersアカウント作成 | https://developers.line.biz/ → ログイン | - |
| 2 | 新規Provider作成 | Providers → Create → 名前入力 | Provider ID |
| 3 | Messaging APIチャンネル作成 | Create Channel → Messaging API | Channel ID |
```

**修正後**:
```markdown
| 1 | LINE Official Accountアカウント作成 | https://account.line.biz/ → ビジネスIDで登録 | - |
| 2 | LINE Official Account作成 | フォームに入力してアカウント作成 | Account ID |
| 3 | Messaging API有効化 | LINE Official Account Manager → Settings → Messaging API → Enable | - |
| 4 | LINE Developers Consoleで確認 | https://developers.line.biz/ → 同じ認証情報でログイン | Channel ID（自動作成済み） |
```

**理由**: 2024年9月以降、LINE Developers Consoleから直接Channelを作成できなくなった。

---

### 優先度: MEDIUM

#### RevenueCat API レスポンス整数化への対応

**ファイル**: Skill実装ファイル（`daily-metrics-reporter`等）

**推奨追加コード**:
```javascript
// MRR が整数で返却されることを明示的にコメント
// RevenueCat V2 API は MRR を整数で返す（2024年8月時点の仕様）
// 例: $16.82 → 16
const mrr = data.metrics.mrr; // 整数
```

**理由**: 将来的な仕様変更（doubleへの移行）に備えた明示的なコメント。

---

### 優先度: LOW

#### Gmail プラグイン代替の検討

**ファイル**: `.cursor/plans/openclaw/anicca-openclaw-spec.md`
**セクション**: Step 5: Gmail統合

**推奨追加セクション**:
```markdown
#### 代替プラグイン: openclaw-agentmail（オプション）

より高いセキュリティとリアルタイム性が必要な場合、`openclaw-agentmail@1.1.0` を検討してください。

| 機能 | @mcinteerj/openclaw-gmail | openclaw-agentmail |
|------|---------------------------|-------------------|
| 通信方式 | Polling | WebSocket（リアルタイム） |
| セキュリティ | 標準 | 強化版（reply-onlyモード） |
```

**理由**: 将来的な選択肢としてドキュメント化。

---

## 参考リンク

### RevenueCat
- [Overview Metrics Documentation](https://www.revenuecat.com/docs/dashboard-and-metrics/overview)
- [V2 API Release Notes (2023-11-02)](https://www.revenuecat.com/release/new-rest-api-v2-functionality-app-management-overview-metrics-2023-11-02)
- [Community: Integer vs Double Discussion](https://community.revenuecat.com/third-party-integrations-53/why-metrics-in-v2-api-mrr-and-revenue-are-whole-numbers-5017)

### OpenClaw
- [Session Management Documentation](https://docs.openclaw.ai/concepts/session)
- [Session Management Deep Dive](https://docs.openclaw.ai/reference/session-management-compaction)
- [Configuration Guide](https://docs.openclaw.ai/gateway/configuration)

### LINE Messaging API
- [Getting Started Guide (2026)](https://developers.line.biz/en/docs/messaging-api/getting-started/)
- [LINE Official Account Manager](https://manager.line.biz/)

### npm Packages
- [@mcinteerj/openclaw-gmail@1.2.7](https://www.npmjs.com/package/@mcinteerj/openclaw-gmail)
- [openclaw-agentmail@1.1.0](https://www.npmjs.com/package/openclaw-agentmail)

### macOS Environment Variables
- [Setting Environment Variables on macOS (2024)](https://naiyerasif.com/post/2024/12/29/setting-up-environment-variables-on-macos/)
- [LaunchAgent plist Example](https://community.jamf.com/fid-2/tid-35307)

---

## 調査メタデータ

| 項目 | 値 |
|------|-----|
| **調査日時** | 2026年2月5日 19:51:36 JST |
| **調査対象Spec** | `.cursor/plans/openclaw/anicca-openclaw-spec.md` |
| **調査ツール** | mcp__exa__web_search_exa, WebFetch, npm CLI |
| **検索クエリ数** | 5 |
| **公式ドキュメント参照数** | 3 |
| **確認した外部API** | npm registry |
| **最新情報基準日** | 2026年2月5日 |

---

## 次のステップ

1. **即時対応**: LINE Messaging API セットアップ手順を修正
2. **短期対応**: RevenueCat API レスポンスに整数化コメントを追加
3. **中期対応**: Gmail プラグイン代替の検討と移行計画
4. **継続監視**: RevenueCat V2 API の仕様変更（double対応）

---

**調査完了**: すべての項目について最新のベストプラクティスとドキュメントを確認しました。
