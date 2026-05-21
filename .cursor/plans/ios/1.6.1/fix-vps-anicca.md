# VPS Anicca Gateway 修正計画

## 問題の根本原因（仮説）

> **注意：** 以下は仮説です。Step 1 の診断で証跡を採取し、確定します。

### 仮説：なぜ失敗したか

| 問題 | 仮説の原因 | 正しいアプローチ |
|------|-----------|-----------------|
| Port 18789 がバインドしない | 手動で systemd service を作成した | `openclaw gateway install --force` を使うべきだった |
| Gateway プロセスは動くがポート開かない | Service file の設定が不完全 | 公式コマンドが正しい設定を生成する |
| `openclaw cron run` が接続エラー | Gateway の管理ポートが動いていない | Gateway 自体が正しく起動していない |

### 重要な発見

**Port 18789 と Slack は分離していない。**

```
Slack Socket Mode ──┐
                    ├─→ Gateway プロセス (port 18789)
CLI コマンド ───────┘
```

- Slack Socket Mode は Gateway プロセスの **中で** 動く
- Port 18789 は Gateway の管理インターフェース
- Gateway が正しく起動しないと、Slack も動かない

**つまり：** 「Slack で Anicca に話しかける」ためには、まず Gateway を正しく起動する必要がある。

---

## 修正計画

### Step 0: VPS に接続

```bash
# 通常ユーザーで接続（root 常用は非推奨）
ssh anicca@46.225.70.241

# 必要な場合のみ sudo を使用
```

### Step 1: 診断証跡を採取（根本原因の確定）

```bash
# Gateway の詳細状態を確認
openclaw gateway status --deep --json

# ログを確認
openclaw logs --follow --lines 100

# doctor で問題を検出
openclaw doctor

# last error を確認
openclaw gateway status --deep --json | jq '.lastError'
```

この結果で根本原因を確定してから次に進む。

### Step 2: 公式コマンドでクリーンアップ

```bash
# 既存の Gateway サービスをアンインストール（公式コマンド）
openclaw gateway uninstall

# doctor で残存問題がないか確認
openclaw doctor
```

**手動 rm は最終手段としてのみ使用。公式 CLI で対応できない場合のみ：**
```bash
# 最終手段（公式コマンドで解決しない場合のみ）
rm -f ~/.config/systemd/user/openclaw-gateway.service
XDG_RUNTIME_DIR=/run/user/$(id -u) systemctl --user daemon-reload
```

### Step 3: 公式コマンドで Gateway を再インストール

```bash
# Gateway を強制再インストール（公式推奨コマンド）
openclaw gateway install --force

# サービスを起動
openclaw gateway start
```

**このコマンドが正しい理由：**
- 公式 Gateway Runbook が推奨する方法
- 正しい PATH、環境変数、ExecStart を自動設定
- `openclaw doctor` で検出される問題を回避

### Step 4: 動作確認（bind/auth 含む）

```bash
# 1. Port 18789 が開いているか
ss -tlnp | grep 18789

# 2. Gateway の詳細状態を確認（bind/auth 含む）
openclaw gateway status --deep --json

# 確認項目：
# - config path が正しいか
# - probe target が正しいか
# - last error がないか
# - bind 設定（loopback/lan）
# - auth 設定（token 有効か）

# 3. Gateway status（簡易）
openclaw gateway status

# 4. Doctor で問題がないか
openclaw doctor
```

### Step 5: Slack テスト

Gateway が正しく動いたら：

1. Slack #metrics で `@Anicca` にメンション
2. Anicca が反応するか確認
3. 反応したら、メトリクス投稿を依頼

---

## セキュリティ確認

| 項目 | 確認方法 | 期待値 |
|------|---------|--------|
| bind 設定 | `openclaw gateway status --deep --json \| jq '.bind'` | `loopback` |
| auth 設定 | `openclaw gateway status --deep --json \| jq '.auth'` | token 有効 |
| .env 権限 | `ls -la ~/.env` | `-rw-------` (600) |
| openclaw.json 権限 | `ls -la ~/.openclaw/openclaw.json` | `-rw-------` (600) |

**注意：** non-loopback bind（lan/tailnet/auto）では auth 設定が必須。

---

## なぜこれで動くか

| 修正前 | 修正後 |
|--------|--------|
| 手動で service file 作成 | `openclaw gateway install --force` が正しい設定を生成 |
| 手動 rm でクリーンアップ | `openclaw gateway uninstall` で公式フロー |
| ポート疎通確認のみ | `gateway status --deep --json` で bind/auth も検証 |
| 根本原因を断定 | 診断証跡で確定してから対処 |
| root で SSH | 通常ユーザー + 必要時のみ sudo |

---

## 再起動からやり直す必要はない

既に完了している部分は活かせる：

| タスク | 状態 | 再利用可能 |
|--------|------|-----------|
| anicca ユーザー作成 | ✅ | はい |
| lingering 有効化 | ✅ | はい |
| .env ファイル | ✅ | はい |
| openclaw.json コピー | ✅ | はい（パス修正済み） |
| OpenClaw アップグレード | ✅ | はい（2026.2.3-1） |
| ASC scripts コピー | ✅ | はい |
| .p8 キーコピー | ✅ | はい |

**やり直す部分：** Gateway サービスの再インストールのみ

---

## テストチェックリスト

| # | テスト | 期待結果 |
|---|--------|---------|
| 1 | `ss -tlnp \| grep 18789` | Port がリッスン |
| 2 | `openclaw gateway status --deep --json` | running, bind=loopback, auth=token |
| 3 | `openclaw gateway status` | "running" |
| 4 | `openclaw doctor` | Critical エラーなし |
| 5 | Slack で @Anicca | 反応あり |
| 6 | Anicca にメトリクス投稿依頼 | Slack #metrics に投稿 |
| 7 | Cron job テスト | 翌朝 5:00 JST に自動投稿 |

---

## 学んだこと

1. **公式コマンドを使う** - `openclaw gateway install/uninstall` が正解
2. **`onboard --install-daemon`** は初期セットアップ用、再インストールには `gateway install --force`
3. **Port 18789 = Gateway 全体** - Slack も CLI もここを通る
4. **`gateway status --deep`** で bind/auth も確認
5. **診断証跡を先に採取** - 仮説を確定してから対処

---

## 次のアクション

1. ユーザーに計画を説明（このファイル）
2. 承認後、Step 0-5 を実行
3. Slack テストで動作確認
4. 成功したら anicca-openclaw-spec.md を更新
