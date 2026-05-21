# Mac Mini移行 — 進捗ステータス

**最終更新**: 2026-02-21 15:20 JST

---

## Phase 1: Daisがやる ✅ 完了
- [x] Mac Mini初期設定（アカウント: anicca / Dukkha2026!）
- [x] WiFi接続: xg100n-16fdcd-3
- [x] リモートログインON
- [x] スリープ無効
- [x] Homebrewインストール

## Phase 2: 移行作業 ✅ 完了

### CLI (11/11) ✅
- [x] node, npm, bun, openclaw, gh, firecrawl, tailscale, gog, git, python3, brew

### State Dir転送 ✅
- [x] openclaw.json, .env, cron/jobs.json, skills/, workspace/, agents/, memory/*.sqlite, devices/, identity/

### 外部設定 ✅
- [x] moltbook credentials, gog client secret, gh config

### バグ修正済み ✅
- [x] `/home/anicca` バグ → **原因: 全43cronジョブが `delivery.mode: "announce"` だった** → `"none"` に変更完了
- [x] x-poster Blotato API → **原因: `api.blotato.com` は廃止。正しいエンドポイントは `backend.blotato.com/v2`** → SKILL.md修正完了
- [x] hookpost-ttl-cleaner → **実装なし** → SKILL.md に exec ベースの実装手順を追加
- [x] autonomy-check → **launchd警告が誤検知** → SKILL.md修正（macOS SSH制限の説明追加）
- [x] Gateway自動起動 → **`.zprofile` に自動起動チェック追加。次回GUIログイン時にLaunchAgentも有効**

### VPS ✅
- [x] VPS Gateway停止済み（`systemctl --user stop openclaw-gateway`）
- [x] VPS Gateway **re-enabled**（`systemctl --user enable`）— 停止状態は維持。Mini障害時に `systemctl --user start` で即復旧可能

---

## 現在の動作状況（2026-02-21 15:20 JST）

| スキル | 状態 | 備考 |
|--------|------|------|
| suffering-detector | ✅ | severity 1.0, SAFE-T正常 |
| moltbook-interact | ✅ | 2-3リプライ/実行 |
| trend-hunter (9am) | ✅ | hooks/9am, trends/9am 生成済み |
| app-nudge-sender | ✅ | 稼働中 |
| daily-memory | ✅ | 稼働中 |
| roundtable-standup | ✅ | 稼働中 |
| app-metrics | ✅ | 稼働中 |
| app-reviews | ✅ | 稼働中 |
| larry | ✅ | 稼働中 |
| x-poster | 🔄 修正済み・テスト待ち | SKILL.md更新完了。15:23 JSTにテスト実行予定 |
| hookpost-ttl-cleaner | 🔄 修正済み・テスト待ち | SKILL.md実装完了。15:26 JSTにテスト実行予定 |
| autonomy-check | 🔄 修正済み・テスト待ち | SKILL.md修正完了。15:29 JSTにテスト実行予定 |
| trend-hunter (9pm) | 🔄 テスト待ち | 15:20 JSTにテスト実行予定 |

---

## Gateway 状態

| 項目 | 値 |
|------|-----|
| 現在のプロセス | PID 603 (nohup起動) |
| 自動起動 | `.zprofile` チェック（SSH時） + LaunchAgent（次回GUIログイン時） |
| 生死確認 | `pgrep -f "openclaw.*gateway"` |
| 再起動方法 | `nohup /opt/homebrew/bin/node /opt/homebrew/lib/node_modules/openclaw/dist/index.js gateway --port 18789 >> ~/.openclaw/logs/gateway.log 2>&1 &` |

---

## VPS 復旧手順（Mini障害時）

```bash
ssh anicca@46.225.70.241
export XDG_RUNTIME_DIR=/run/user/$(id -u)
systemctl --user start openclaw-gateway
# → Slackに繋ぎ直す
# MacBook Pro側: openclaw tui --url ws://46.225.70.241:18789
```

---

## TUI接続方法

```bash
# Mini に接続（通常）
openclaw tui

# Mini に接続（SSHトンネル経由 — "gateway not connected"エラーが出る場合）
ssh -N -L 18789:localhost:18789 anicca@100.99.82.95 &
openclaw tui --url ws://localhost:18789

# VPS に接続（Mini障害時）
openclaw tui --url ws://46.225.70.241:18789
```

---

## 残タスク

| # | タスク | 状態 | 備考 |
|---|--------|------|------|
| A | 全cron動作確認 | ⏳ 実行中 | 15:20〜15:44 JSTに9スキルのテストcron実行中 |
| B | TOOLS.md / IDENTITY.md更新 | ❌ 未完了 | TUIでAniccaに頼む |
| C | Telegramテスト | ❌ 未完了 | Slack動作確認後 |

---

## 構成図

```
ダイス（どこでも）
    ↓
MacBook Pro（手元）
    ↓ openclaw tui
Mac Mini（家）← Aniccaが動いてる（43 cronジョブ稼働）

障害時フォールバック:
MacBook Pro → VPS (46.225.70.241) ← re-enabled, 即起動可能
```

| 機能 | 場所 |
|------|------|
| gog | Mac Mini上で実行 |
| Playwright | Mac Mini上で実行 |
| cron（43ジョブ） | Mac Mini上で実行 |
| Slack/Telegram送信 | ✅ delivery.mode=none で動作中 |
| VPS | 停止中（re-enabled、即復旧可能） |

---

## 接続情報

| 項目 | 値 |
|------|-----|
| Tailscale IP | 100.99.82.95 |
| Tailscaleホスト名 | aniccanomac-mini-1 |
| ローカルIP | 192.168.1.12 |
| macOS | 15.6 (arm64, T8132) |
| アカウント | anicca / Dukkha2026! |
| Gateway token | efdd345a619e1e54f41f615325754511a165091790dba919 |
| VPS IP | 46.225.70.241 |
| VPS 状態 | 停止中（enabled、起動可能） |

---

## Blotato API（重要）

| 項目 | 値 |
|------|-----|
| 正しいBase URL | `https://backend.blotato.com/v2` |
| 廃止済み（使用禁止） | `https://api.blotato.com`（NXDOMAIN） |
| 認証ヘッダー | `blotato-api-key: <key>` |
| X投稿エンドポイント | `POST /posts` |
| ACCOUNT_ID_EN | 11852 |
| ACCOUNT_ID_JA | 29172 |
