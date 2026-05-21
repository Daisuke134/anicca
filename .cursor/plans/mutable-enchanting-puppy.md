# Fix: OpenClaw TUI "gateway not connected" from MacBook

## Context

MacBook から `openclaw tui` を実行すると `ws://100.99.82.95:18789`（Mac Mini の Tailscale IP）に接続しようとするが、Mac Mini の gateway は `bind: "loopback"` で `127.0.0.1` のみリッスン中。Tailscale 越しの外部接続を全部拒否している。

```
MacBook TUI → ws://100.99.82.95:18789   ←── Tailscale
                        │
          Mac Mini: 127.0.0.1:18789 のみ受付
                        │
                   ❌ 接続拒否
```

## 根本原因

| 項目 | 現在値 | 必要値 |
|------|--------|--------|
| `gateway.bind` | `"loopback"` | `"tailnet"` |
| Auth | `mode: "token"` ✅ | 変更不要 |
| Port | `18789` ✅ | 変更不要 |

ソース: OpenClaw 公式ドキュメント — 有効な bind 値: `"loopback"`, `"lan"`, `"tailnet"`, `"auto"`, `"custom"`

## 修正手順（2ステップのみ）

### Step 1: `openclaw.json` の `bind` を変更

**ファイル:** `/Users/anicca/.openclaw/openclaw.json`

```json
// Before
"bind": "loopback"

// After
"bind": "tailnet"
```

> ⚠️ 注意: この変更はすでに済んでいる（セッション内で python3 で変更済み）。確認のみでOK。

### Step 2: Gateway を再起動

```bash
ssh anicca@100.99.82.95 "export PATH=/opt/homebrew/bin:/opt/homebrew/sbin:\$PATH && openclaw gateway restart"
```

## なぜ `tailnet` か

| オプション | セキュリティ | 用途 |
|-----------|------------|------|
| `loopback` | 最高 | Mac Mini ローカルのみ |
| `tailnet` | ✅ 高い | Tailscale ネットワーク内のみ（推奨） |
| `lan` | 中 | 全 LAN インターフェース（過剰） |
| `all` | 低 | 0.0.0.0（危険） |

Tailscale は VPN なので `tailnet` = Tailscale メンバーのみ接続可。Auth token も残るので二重保護。

## 検証

```bash
# MacBook から実行
openclaw tui

# 期待結果: ws://100.99.82.95:18789 に接続成功
# "gateway disconnected" エラーが消える
```

## 影響範囲

| 項目 | 影響 |
|------|------|
| Slack チャンネル | ✅ 変更なし（引き続き正常） |
| Anicca エージェント | ✅ 変更なし（引き続き正常） |
| Cron ジョブ | ✅ 変更なし |
| Mac Mini ローカルアクセス | ✅ 変更なし（tailnet は loopback も含む） |
