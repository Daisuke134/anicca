# Mac Mini移行 — 進捗ステータス

**最終更新**: 2026-02-21 04:20 JST

---

## Phase 1: Daisがやる ✅ 完了
- [x] Mac Mini初期設定（アカウント: anicca）
- [x] WiFi接続: xg100n-16fdcd-3
- [x] リモートログインON
- [x] スリープ無効
- [x] Homebrewインストール

## Phase 2: CLI + State Dir ✅ ほぼ完了

### CLI (全11個)
| CLI | 状態 | バージョン |
|-----|------|-----------|
| node | ✅ | v25.6.1 |
| npm | ✅ | (node付属) |
| bun | ✅ | 1.3.9 |
| openclaw | ✅ | 2026.2.9 |
| gh | ✅ | installed |
| firecrawl | ✅ | installed |
| tailscale | ✅ | 100.99.82.95 |
| gog | ✅ | installed |
| git | ✅ | installed |
| python3 | ✅ | installed |
| brew | ✅ | installed |

### State Dir転送
| 項目 | 状態 |
|------|------|
| openclaw.json | ✅ パス修正済み (/Users/anicca/) |
| .env (156行) | ✅ |
| cron/jobs.json | ✅ |
| skills/ (34個) | ✅ |
| workspace/ | ✅ |
| agents/ (セッション履歴) | ✅ |
| memory/*.sqlite | ✅ |

### 外部設定
| 項目 | 状態 |
|------|------|
| ~/.config/moltbook/ | ❓ 未確認 |
| ~/.config/gog_client_secret.json | ❓ 未確認 |
| ~/.config/gh/ | ❓ 未確認 |

### 残りタスク
- [ ] 外部設定ファイル確認
- [ ] workspace npm install
- [ ] Playwrightブラウザインストール
- [ ] cronパッチ3件（gmail-digest, gcal-digest, lunch-music → ローカル化）
- [ ] SKILL.mdパッチ2件（gmail-digest, gcal-digest）
- [ ] TOOLS.md / MEMORY.md / IDENTITY.md更新
- [ ] **VPS Gateway停止 → Mac Mini Gateway起動**（最後にやる）

## Phase 3: 動作確認 ❌ 未着手

## 接続情報
- Mac Mini Tailscale IP: **100.99.82.95**
- Mac Mini ローカルIP: 192.168.1.12
- Mac Mini ホスト名: AniccanoMac-mini.local
- Mac Mini アカウント: anicca / Dukkha2026!
- Mac Mini WiFi: xg100n-16fdcd-3 (en1)
- Mac Mini macOS: 15.6 (Darwin 24.6.0, arm64, T8132)
