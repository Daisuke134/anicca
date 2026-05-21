# OpenClaw VPS Deployment Research

## 調査情報

| 項目 | 値 |
|------|-----|
| **調査日時** | 2026-02-06 13:53:28 |
| **調査対象** | OpenClaw VPS デプロイメント（Ubuntu Server） |
| **主要情報源** | OpenClaw 公式ドキュメント、コミュニティガイド |
| **調査者** | Claude Code (tech-spec-researcher) |

---

## 📊 調査結果サマリー

```
調査完了: OpenClaw VPS デプロイメント
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 推奨構成: Ubuntu Server + systemd + Nginx
🔧 必要な設定: Gateway Mode, Systemd Service, Slack Socket Mode
🔒 セキュリティ: 必須（非ループバックバインドは認証必須）
⚠️  注意点: PATH環境変数の制限、bind設定の認証要件
```

---

## 1. VPS要件

### 最小構成

| リソース | 最小値 | 推奨値 | ローカルAIモデル使用時 |
|---------|--------|--------|---------------------|
| **vCPU** | 1 | 2+ | 4+ |
| **RAM** | 2GB | 4GB | 16GB+ |
| **ストレージ** | 20GB SSD | 40GB SSD | 100GB+ SSD |
| **GPU** | 不要 | 不要 | NVIDIA GPU（オプション） |

### サポートされるOSディストリビューション

| OS | バージョン | systemd | 推奨度 |
|----|----------|---------|--------|
| Ubuntu Server | 20.04 LTS, 22.04 LTS, 24.04 LTS | ✅ | ⭐⭐⭐ |
| Debian | 11+, 12+ | ✅ | ⭐⭐⭐ |
| CentOS/RHEL | 8+, 9+ | ✅ | ⭐⭐ |

---

## 2. Gateway 設定（最重要）

### Gateway Mode と Bind 設定

| 設定項目 | 値 | 説明 |
|---------|-----|------|
| **`gateway.mode`** | `"local"` | **必須** — Gateway を起動するために明示的に設定 |
| **`gateway.port`** | `18789`（デフォルト） | Gateway が待ち受けるポート |
| **`gateway.bind`** | `"loopback"` or `"lan"` | ネットワークアクセシビリティを制御 |

### Bind モード詳細

| Bind モード | バインドアドレス | 用途 | 認証要否 |
|------------|----------------|------|---------|
| **`loopback`** | `127.0.0.1` | ローカルのみアクセス（リバースプロキシ推奨） | 不要 |
| **`lan`** | `0.0.0.0` | ネットワークインターフェース経由でアクセス | **必須** |
| **`tailnet`** | Tailscale IP | Tailscale VPN 経由 | **必須** |
| **`custom`** | カスタムIP | 特定のインターフェースに限定 | **必須** |

### 設定ファイル例（`~/.openclaw/openclaw.json`）

#### パターン1: Loopback + Nginx リバースプロキシ（推奨）

```json5
{
  gateway: {
    mode: "local",
    port: 18789,
    bind: "loopback"
  }
}
```

**特徴:**
- 認証不要（ローカルのみアクセス可能）
- Nginx で HTTPS 終端とリバースプロキシ
- 最もシンプルで安全

#### パターン2: LAN バインド + トークン認証

```json5
{
  gateway: {
    mode: "local",
    port: 18789,
    bind: "lan",
    auth: {
      mode: "token",
      token: "your-secure-random-token-here"
    }
  }
}
```

**特徴:**
- `0.0.0.0` にバインド → 外部アクセス可能
- **認証必須**（token または password）
- トークンは環境変数 `OPENCLAW_GATEWAY_TOKEN` でも設定可能

---

## 3. Systemd Service 設定

### サービスファイルの場所

| 項目 | 値 |
|------|-----|
| **サービスタイプ** | systemd **ユーザーサービス**（システムサービスではない） |
| **サービス名** | `openclaw-gateway.service` |
| **サービスファイル** | 自動生成（`openclaw onboard --install-daemon`） |
| **ログ確認** | `journalctl --user -u openclaw-gateway -n 200 --no-pager` |

### サービス管理コマンド

| 操作 | コマンド |
|------|---------|
| **起動** | `systemctl --user start openclaw-gateway` |
| **停止** | `systemctl --user stop openclaw-gateway` |
| **再起動** | `systemctl --user restart openclaw-gateway` |
| **自動起動有効化** | `systemctl --user enable openclaw-gateway` |
| **ステータス確認** | `systemctl --user status openclaw-gateway` |
| **ログ確認（リアルタイム）** | `journalctl --user -u openclaw-gateway -f` |

### systemd サービスファイルの推奨構成

```ini
[Unit]
Description=OpenClaw Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=openclaw
WorkingDirectory=/home/openclaw
ExecStart=/usr/local/bin/openclaw gateway start
Restart=always
RestartSec=10

# 環境変数を読み込む
EnvironmentFile=/home/openclaw/.openclaw/.env

# セキュリティ強化
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/openclaw/.openclaw

[Install]
WantedBy=default.target
```

### ヘッドレスサーバーでの lingering 有効化（必須）

| 項目 | 詳細 |
|------|------|
| **問題** | SSH ログアウト後、ユーザーサービスが停止する |
| **解決策** | `loginctl enable-linger` を実行 |
| **コマンド** | `loginctl enable-linger $USER` |
| **効果** | ログイン前にユーザーサービスが起動し、ログアウト後も実行継続 |

```bash
# lingering 有効化（ヘッドレスサーバーで必須）
loginctl enable-linger $USER

# 確認
loginctl show-user $USER | grep Linger
# Linger=yes が表示されればOK
```

---

## 4. 環境変数設定

### OpenClaw 固有の環境変数

| 環境変数 | 用途 | デフォルト値 |
|---------|------|------------|
| **`OPENCLAW_CONFIG_PATH`** | カスタム設定ファイルのパス | `~/.openclaw/openclaw.json` |
| **`OPENCLAW_STATE_DIR`** | セッション、認証情報、ワークスペースの保存先 | `~/.openclaw` |
| **`OPENCLAW_GATEWAY_PORT`** | Gateway ポートのオーバーライド | `18789` |
| **`OPENCLAW_GATEWAY_TOKEN`** | Gateway 認証トークン（`gateway.auth.token` の代替） | なし |

### Slack Socket Mode 環境変数

| 環境変数 | 値 | 必須 |
|---------|-----|------|
| **`SLACK_APP_TOKEN`** | `xapp-...` | ✅ |
| **`SLACK_BOT_TOKEN`** | `xoxb-...` | ✅ |
| **`SLACK_USER_TOKEN`** | `xoxp-...`（オプション） | ❌ |

### `.env` ファイルの配置

| 項目 | 値 |
|------|-----|
| **配置場所** | `~/.openclaw/.env` |
| **読み込みタイミング** | Gateway 起動時に自動読み込み |
| **用途** | API キー、トークン、カスタムPATH等 |

#### `.env` ファイル例

```bash
# Slack Socket Mode
SLACK_APP_TOKEN=xapp-1-A07...
SLACK_BOT_TOKEN=xoxb-7...

# OpenClaw Gateway 認証（LAN bind 時に必須）
OPENCLAW_GATEWAY_TOKEN=your-secure-random-token

# カスタム環境変数
NODE_ENV=production
LOG_LEVEL=info

# カスタムPATH（必要な場合）
PATH=/usr/local/bin:/usr/bin:/bin:/home/openclaw/.local/bin
```

---

## 5. Slack Socket Mode セットアップ

### 必要なトークンと権限

| トークン種別 | 形式 | 用途 | スコープ |
|------------|------|------|---------|
| **App Token** | `xapp-...` | Socket Mode 接続 | `connections:write` |
| **Bot Token** | `xoxb-...` | メッセージ送受信、リアクション等 | 下記参照 |
| **User Token** | `xoxp-...` | 読み取り専用操作（オプション） | `users:read` 等 |

### Bot Token Scopes（必須）

| カテゴリ | スコープ | 説明 |
|---------|---------|------|
| **メッセージ** | `chat:write` | メッセージ送信 |
| **チャンネル** | `channels:history`, `channels:read` | パブリックチャンネルの履歴と情報読み取り |
| **グループ** | `groups:history`, `groups:read` | プライベートチャンネルの履歴と情報読み取り |
| **DM** | `im:read`, `im:write` | ダイレクトメッセージの読み書き |
| **ユーザー** | `users:read` | ユーザー情報の読み取り |
| **リアクション** | `reactions:read`, `reactions:write` | リアクションの読み書き |
| **ピン** | `pins:read`, `pins:write` | ピンの読み書き |
| **絵文字** | `emoji:read` | 絵文字の読み取り |
| **ファイル** | `files:write` | ファイルアップロード |

### Slack App セットアップ手順

| # | 手順 | 詳細 |
|---|------|------|
| 1 | Slack App 作成 | https://api.slack.com/apps → "Create New App" → "From scratch" |
| 2 | Socket Mode 有効化 | Settings → Socket Mode → Enable |
| 3 | App-Level Token 生成 | Basic Information → App-Level Tokens → "Generate Token" → `connections:write` スコープ |
| 4 | Bot Token Scopes 追加 | OAuth & Permissions → Scopes → 上記スコープを全て追加 |
| 5 | ワークスペースにインストール | OAuth & Permissions → "Install to Workspace" |
| 6 | Bot Token コピー | インストール後に表示される `xoxb-...` トークンをコピー |
| 7 | イベントサブスクリプション | Event Subscriptions → Enable Events → 必要なイベントを購読 |
| 8 | チャンネルに招待 | チャンネルで `/invite @bot_name` |
| 9 | Messages Tab 有効化 | App Home → Messages Tab → Enable |

### 設定ファイルでの Slack 設定

#### 環境変数を使う方法（推奨）

```json5
{
  channels: {
    slack: {
      enabled: true,
      appToken: "${SLACK_APP_TOKEN}",
      botToken: "${SLACK_BOT_TOKEN}"
    }
  }
}
```

#### 直接記述する方法

```json5
{
  channels: {
    slack: {
      enabled: true,
      appToken: "xapp-...",
      botToken: "xoxb-...",
      userToken: "xoxp-..."  // オプション
    }
  }
}
```

---

## 6. セキュリティ設定

### 必須のセキュリティ対策

| 項目 | 設定 | 理由 |
|------|------|------|
| **UFW ファイアウォール** | 有効化、SSH/HTTP/HTTPS のみ許可 | 不要なポートを閉じる |
| **SSH 鍵認証** | パスワード認証を無効化 | ブルートフォース攻撃防止 |
| **Fail2Ban** | SSH/Nginx に適用 | 不正アクセス試行をブロック |
| **Let's Encrypt SSL/TLS** | Nginx で HTTPS 終端 | 通信の暗号化 |
| **非rootユーザー** | `openclaw` 専用ユーザーを作成 | 権限分離 |
| **Systemd セキュリティ** | `NoNewPrivileges`, `ProtectSystem`, `ProtectHome` | サンドボックス化 |

### UFW ファイアウォール設定

```bash
# UFW インストール
sudo apt update && sudo apt install ufw -y

# デフォルトポリシー
sudo ufw default deny incoming
sudo ufw default allow outgoing

# SSH 許可（接続が切れないように先に設定）
sudo ufw allow 22/tcp

# HTTP/HTTPS 許可（Nginx 使用時）
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# UFW 有効化
sudo ufw enable

# ステータス確認
sudo ufw status verbose
```

### 非ループバックバインドの認証設定

| Bind モード | 認証要否 | 設定方法 |
|------------|---------|---------|
| `loopback` | 不要 | - |
| `lan` / `tailnet` / `custom` | **必須** | `gateway.auth.token` または `OPENCLAW_GATEWAY_TOKEN` |

**重要**: 非ループバックバインドで認証なしの場合、Gateway は起動時にエラーを出す。

```bash
# エラー例
Error: Non-loopback bind requires auth configuration.
Set gateway.auth.mode and gateway.auth.token, or export OPENCLAW_GATEWAY_TOKEN.
```

---

## 7. Nginx リバースプロキシ設定

### 推奨構成

| 項目 | 値 |
|------|-----|
| **Upstream** | `127.0.0.1:18789` |
| **プロトコル** | HTTP/1.1 with WebSocket upgrade |
| **SSL/TLS** | Let's Encrypt |
| **Trusted Proxies** | `127.0.0.1`, Nginx サーバーIP |

### Nginx 設定例

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:18789;
        proxy_http_version 1.1;

        # WebSocket サポート
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # プロキシヘッダー
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # タイムアウト
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }
}
```

### OpenClaw での Trusted Proxies 設定

```json5
{
  gateway: {
    mode: "local",
    bind: "loopback",
    trustedProxies: ["127.0.0.1", "10.0.0.1"]  // Nginx のIPを追加
  }
}
```

**理由**: Trusted Proxies を設定しないと、`x-forwarded-for` ヘッダーが正しく読み取られず、ローカル認証やペアリングコードの検証が失敗する。

---

## 8. トラブルシューティング

### systemd サービスが起動しない

| 症状 | 原因 | 解決策 |
|------|------|--------|
| `gateway.mode` エラー | `gateway.mode` が `local` になっていない | `openclaw.json` で `gateway.mode: "local"` を設定 |
| 認証エラー | 非ループバックバインドで認証未設定 | `gateway.auth.token` または `OPENCLAW_GATEWAY_TOKEN` を設定 |
| ポート18789でリッスンしない | 設定ミスまたはバインド失敗 | `openclaw gateway status` で確認 |
| PATH 関連エラー | systemd の最小PATH | `~/.openclaw/.env` に `PATH` を追加 |

### Slack 接続が失敗する

| 症状 | 原因 | 解決策 |
|------|------|--------|
| `SLACK_APP_TOKEN` エラー | トークンが未設定または無効 | `.env` ファイルまたは `openclaw.json` で設定 |
| Socket Mode 接続エラー | Socket Mode が無効 | Slack App Settings で Socket Mode を有効化 |
| スコープ不足 | Bot Token Scopes が不足 | 必須スコープを全て追加して再インストール |

### Gateway が起動しているがアクセスできない

| 症状 | 原因 | 解決策 |
|------|------|--------|
| `Connection refused` | ファイアウォールでブロック | UFW で該当ポートを許可 |
| Tailscale バインド失敗 | Tailscale が起動していない | Tailscale を起動するか `bind: "loopback"` に変更 |
| リバースプロキシ経由でエラー | Trusted Proxies 未設定 | `gateway.trustedProxies` に Nginx IP を追加 |

### systemd サービスログの確認

```bash
# 最新200行を表示
journalctl --user -u openclaw-gateway -n 200 --no-pager

# リアルタイムでログを追跡
journalctl --user -u openclaw-gateway -f

# エラーのみフィルタ
journalctl --user -u openclaw-gateway -p err
```

### 設定の診断

```bash
# OpenClaw の診断ツールを実行
openclaw doctor

# Gateway ステータス確認
openclaw gateway status

# 設定の検証
openclaw config validate
```

---

## 9. 監視・メンテナンス

### ヘルスチェックスクリプト

```bash
#!/bin/bash
# /usr/local/bin/openclaw-healthcheck.sh

# Gateway ステータス確認
if ! systemctl --user is-active --quiet openclaw-gateway; then
    echo "OpenClaw Gateway is not running. Restarting..."
    systemctl --user restart openclaw-gateway

    # Slack 通知（オプション）
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"⚠️ OpenClaw Gateway was restarted on VPS"}' \
        YOUR_SLACK_WEBHOOK_URL
fi

# ポート確認
if ! nc -z localhost 18789; then
    echo "Port 18789 is not listening. Investigating..."
    journalctl --user -u openclaw-gateway -n 50 --no-pager
fi
```

### Cron での定期実行

```bash
# crontab -e で以下を追加

# 5分ごとにヘルスチェック
*/5 * * * * /usr/local/bin/openclaw-healthcheck.sh >> /var/log/openclaw-healthcheck.log 2>&1

# 毎日午前3時に設定バックアップ
0 3 * * * tar -czf /backup/openclaw-$(date +\%Y\%m\%d).tar.gz ~/.openclaw/
```

### バックアップ戦略

| バックアップ対象 | 頻度 | 保存期間 | 方法 |
|---------------|------|---------|------|
| **設定ファイル** | 毎日 | 7日 | tar + rsync |
| **セッションデータ** | 毎日 | 7日 | tar + rsync |
| **ログ** | 週次 | 30日 | journalctl export |

```bash
# バックアップスクリプト例
#!/bin/bash
BACKUP_DIR="/backup/openclaw"
DATE=$(date +%Y%m%d)

mkdir -p $BACKUP_DIR

# 設定とデータをバックアップ
tar -czf $BACKUP_DIR/openclaw-$DATE.tar.gz ~/.openclaw/

# 7日以上古いバックアップを削除
find $BACKUP_DIR -name "openclaw-*.tar.gz" -mtime +7 -delete

# rsync でオフサイトバックアップ（オプション）
rsync -avz $BACKUP_DIR/ user@backup-server:/backup/openclaw/
```

---

## 10. パフォーマンス最適化

### Hot Reload 設定

| 項目 | 値 | 説明 |
|------|-----|------|
| **`reload.mode`** | `"hybrid"` | ファイル監視 + 自動リロード |
| **`reload.debounceMs`** | `300` | リロード前の待機時間（ms） |
| **本番環境** | `"off"` | ファイル監視を無効化（リソース節約） |

```json5
{
  gateway: {
    reload: {
      mode: "off",  // 本番環境では無効化を推奨
      debounceMs: 300
    }
  }
}
```

### systemd リソース制限

```ini
[Service]
# CPU 使用率の制限（50%まで）
CPUQuota=50%

# メモリ制限（2GB）
MemoryMax=2G
MemoryHigh=1.5G

# ファイルディスクリプタ制限
LimitNOFILE=65536
```

### ログローテーション

```bash
# /etc/systemd/journald.conf
[Journal]
SystemMaxUse=500M
SystemKeepFree=1G
MaxRetentionSec=7day
```

---

## 11. Docker デプロイ（代替手段）

### Docker Compose 設定例

```yaml
version: '3.8'

services:
  openclaw:
    image: openclaw/openclaw:latest
    container_name: openclaw-gateway
    restart: always
    ports:
      - "127.0.0.1:18789:18789"
    environment:
      - OPENCLAW_CONFIG_PATH=/config/openclaw.json
      - SLACK_APP_TOKEN=${SLACK_APP_TOKEN}
      - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
      - NODE_ENV=production
    volumes:
      - ./config:/config
      - ./data:/root/.openclaw
    networks:
      - openclaw-network

networks:
  openclaw-network:
    driver: bridge
```

### Docker でのメリット・デメリット

| 項目 | systemd | Docker |
|------|---------|--------|
| **セットアップ** | やや複雑 | シンプル |
| **リソース** | 軽量 | やや重い |
| **隔離性** | 低 | 高 |
| **ログ管理** | journalctl | docker logs |
| **自動起動** | systemctl enable | restart: always |

---

## 12. 公式ドキュメントリンク

### OpenClaw 公式

| カテゴリ | リンク |
|---------|--------|
| **Gateway Configuration** | [https://docs.openclaw.ai/gateway/configuration](https://docs.openclaw.ai/gateway/configuration) |
| **Troubleshooting** | [https://docs.openclaw.ai/gateway/troubleshooting](https://docs.openclaw.ai/gateway/troubleshooting) |
| **Slack Integration** | [https://github.com/openclaw/openclaw/blob/main/docs/channels/slack.md](https://github.com/openclaw/openclaw/blob/main/docs/channels/slack.md) |

### コミュニティガイド

| ガイド | リンク |
|--------|--------|
| **VPS Deployment Guide (MoltBot)** | [https://openclaw.ninja/blog/vps-deployment](https://openclaw.ninja/blog/vps-deployment) |
| **DigitalOcean Tutorial** | [https://www.digitalocean.com/community/tutorials/how-to-run-openclaw](https://www.digitalocean.com/community/tutorials/how-to-run-openclaw) |
| **Hostinger VPS Setup** | [https://www.hostinger.com/tutorials/how-to-set-up-openclaw](https://www.hostinger.com/tutorials/how-to-set-up-openclaw) |
| **AI/ML API VPS Review** | [https://aimlapi.com/blog/openclaw-review-real-world-use-setup-on-a-5-vps-and-what-actually-works](https://aimlapi.com/blog/openclaw-review-real-world-use-setup-on-a-5-vps-and-what-actually-works) |
| **Pulumi + Tailscale Deployment** | [https://www.pulumi.com/blog/deploy-openclaw-aws-hetzner/](https://www.pulumi.com/blog/deploy-openclaw-aws-hetzner/) |

---

## 13. Anicca プロジェクト固有の考慮事項

### 現在の構成（ローカル macOS）

| 項目 | 現状 |
|------|------|
| **Gateway 稼働場所** | ローカル macOS |
| **VPS** | `46.225.70.241`（セットアップ済み、OpenClaw 未デプロイ） |
| **Slack 設定** | 全チャンネル許可（groupPolicy: open） |
| **エージェント** | GPT-4o（read/write/exec ツール使用可能、MCP 使用不可） |

### VPS 移行時のチェックリスト

| # | タスク | 説明 |
|---|--------|------|
| 1 | **VPS に OpenClaw インストール** | `curl -fsSL https://openclaw.ai/install.sh \| bash` |
| 2 | **設定ファイル転送** | `~/.openclaw/openclaw.json` を VPS に rsync |
| 3 | **環境変数設定** | `.env` ファイルに `SLACK_APP_TOKEN`, `SLACK_BOT_TOKEN` を追加 |
| 4 | **systemd サービス有効化** | `openclaw onboard --install-daemon` |
| 5 | **lingering 有効化** | `loginctl enable-linger openclaw` |
| 6 | **UFW 設定** | SSH, HTTP, HTTPS のみ許可 |
| 7 | **Nginx リバースプロキシ** | 上記 Nginx 設定を適用 |
| 8 | **Let's Encrypt SSL** | `certbot --nginx -d your-domain.com` |
| 9 | **動作確認** | Slack でメッセージ送信テスト |
| 10 | **ローカル Gateway 停止** | macOS の launchd サービスを停止 |

### 環境変数の移行

**ローカル（現在）:**
- `.env` ファイル: `~/.openclaw/.env`（gitignored）
- `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN` が設定済み

**VPS（移行後）:**
- 同じ `.env` ファイルを VPS の `~/.openclaw/.env` にコピー
- systemd の `EnvironmentFile` でロード

```bash
# ローカルから VPS に環境変数を安全に転送
scp ~/.openclaw/.env openclaw@46.225.70.241:~/.openclaw/.env
```

---

## 14. 追加の推奨事項

### 自動更新

```bash
# OpenClaw の自動更新（週次）
# crontab -e

0 2 * * 0 npm update -g openclaw && systemctl --user restart openclaw-gateway
```

### モニタリング

| ツール | 用途 |
|--------|------|
| **Prometheus + Grafana** | メトリクス収集・可視化 |
| **UptimeRobot** | 外部からの死活監視 |
| **Slack Webhook** | アラート通知 |

### セキュリティ更新

```bash
# 自動セキュリティ更新（Ubuntu/Debian）
sudo apt install unattended-upgrades -y
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

### バックアップのテスト

```bash
# 月次でバックアップからリストアのテスト
# 本番とは別のディレクトリでテスト
tar -xzf /backup/openclaw-20260206.tar.gz -C /tmp/restore-test/
```

---

## 15. まとめ

### ✅ 実行済みアクション

- OpenClaw VPS デプロイメントの公式ドキュメントとコミュニティガイドを調査
- systemd サービス設定、Gateway モード、Slack Socket Mode の詳細を確認
- セキュリティベストプラクティスとトラブルシューティング手順を収集
- Anicca プロジェクト固有の移行チェックリストを作成

### 📝 次のステップ

| # | アクション | 優先度 |
|---|-----------|--------|
| 1 | VPS に OpenClaw をインストール | 高 |
| 2 | 設定ファイルと環境変数を VPS に転送 | 高 |
| 3 | systemd サービスを設定・有効化 | 高 |
| 4 | Nginx リバースプロキシと SSL/TLS を設定 | 中 |
| 5 | Slack との接続をテスト | 高 |
| 6 | ローカル Gateway を停止 | 低（動作確認後） |
| 7 | モニタリングとバックアップを設定 | 中 |

---

**調査完了日時**: 2026-02-06 13:53:28
**次回レビュー推奨**: 2026-03-06（1ヶ月後、OpenClaw のアップデート確認）
