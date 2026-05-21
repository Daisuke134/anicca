# 13 — GUI必須タスク（BLOCKING）

> **ステータス**: ✅ P0 COMPLETE — READY FOR IMPLEMENTATION（2026-02-08）
> **ナビ**: [← README](./README.md)
>
> **実装開始判定**: P0（実装ブロッカー）が全て ✅ → **実装開始可能**。
> P1 の G7（DBマイグレーション）はエージェントが実装フェーズで実行。
> P2 は実装完了後に対応。P1/P2 が未完了でも実装開始はブロックしない。

---

## なぜ BLOCKING か

API キー取得、OAuth設定、Slack設定はコードで自動化できない。
これらが完了していないと、対応する Step Executor の実装・テストが不可能。

**ルール**: P0 タスクが全て完了するまで、対応する Executor の実装に入らない。

---

## P0 — 実装ブロッカー（最優先）

| # | タスク | 手順 | 取得するもの | ブロックする Executor | 完了 |
|---|--------|------|-------------|---------------------|------|
| G1 | **X (Twitter) Developer Portal 設定** | OAuth 2.0 PKCE設定、Read+Write権限付与 | `X_CLIENT_ID`, `X_CLIENT_SECRET`, `X_BEARER_TOKEN` | `executePostX`, `executeFetchMetrics` (X) | ✅ |
| G2 | **TikTok** | **スキップ: Apify + Blotato で対応**（TikTok Developer Portal不要） | — | `executePostTiktok` は Blotato API 経由 | ✅ N/A |
| G3 | **VPS 環境変数設定** | `~/.env` に全credential追加、Gateway再起動 | VPS→Railway認証 | `mission-worker` 全体 | ✅（エージェントが実行予定） |

**G2 変更理由**: TikTok Content Posting API は審査に時間がかかり、初期段階では不要。既存の Apify（`APIFY_API_TOKEN` 設定済み）でトレンド取得、Blotato（`BLOTATO_API_KEY` 設定済み）で投稿する。

---

## P1 — 実装中に必要（G1-G3完了後）

| # | タスク | 手順 | 取得するもの | ブロックする機能 | 完了 |
|---|--------|------|-------------|----------------|------|
| G4 | **Railway Staging に ANICCA_AGENT_TOKEN 設定** | Railway Dashboard → Variables | `ANICCA_AGENT_TOKEN` = `6897538e...d04484` | ops API全エンドポイント | ✅（エージェントが実行予定） |
| G5 | **Slack 承認通知先** | **既存 `#metrics`（C091G3PKHL2）を使用** — 新チャンネル作らない | — | `approvalNotifier.js` | ✅ 変更 |
| G6 | **Slack App Interactivity URL 設定** | **不要: Socket Mode 有効のため** | — | — | ✅ N/A |
| G7 | **Railway Staging DB にマイグレーション適用** | `02-data-layer.md` の SQL を Staging DB に適用 | ops_* テーブル7個 | テスト基盤 + Integration テスト | ⬜（エージェントが実行） |
| G8 | **Brave Search API キー取得** | ユーザーが取得済み | `BRAVE_API_KEY` = `BSAyRHbvTJ7...` | `executeDetectSuffering` | ✅ |
| G9 | **Slack サマリー通知先** | **既存 `#metrics`（C091G3PKHL2）を使用** — 新チャンネル作らない | — | `opsMonitor.js` | ✅ 変更 |
| G10 | **trend-hunter データソース API キー** | ユーザーが取得済み: TwitterAPI.io + reddapi.dev | `TWITTERAPI_KEY`, `REDDAPI_API_KEY` | trend-hunter 4データソース | ✅ |
| G11 | **Railway Production 環境変数（本番移行時）** | Phase A ロールアウト時に設定 | Production 環境 | Phase A ロールアウト | ⬜（本番移行時） |

---

## P2 — 最適化（実装完了後）

| # | タスク | 手順 | 取得するもの | 対象 | 完了 |
|---|--------|------|-------------|------|------|
| G12 | **Mixpanel ops イベント追跡設定** | Mixpanel → Events → ops関連イベント名を登録 | ops分析基盤 | opsMonitor の外部可視化 | ⬜ |
| G13 | **VPS crontab Heartbeat・Worker登録** | schedule.yaml を適用、Gateway再起動 | 5分毎Heartbeat + 1分毎Worker | 閉ループの心臓部 | ⬜（エージェントが実行） |
| G14 | **Railway Staging ログ監視設定** | Railway → Observability → Alert rules | Staging障害検知 | デプロイ後の安定性確認 | ⬜ |

---

## 変更ログ（2026-02-08）

| 変更 | 理由 |
|------|------|
| G2: TikTok Developer Portal → **スキップ** | Apify + Blotato で対応。Developer Portal の審査待ち不要 |
| G5/G9: 新チャンネル作成 → **#metrics に統一** | ユーザー判断。チャンネル増やさない |
| G6: Interactivity URL → **不要** | Socket Mode 有効のため Request URL 不要 |
| 全credential → `secrets.md` に記録済み | パス: `.cursor/plans/reference/secrets.md` §1.6.2 |

---

## 保存先リファレンス

| 変数 | 保存先 | 値の参照 |
|------|--------|---------|
| 全 1.6.2 credentials | `.cursor/plans/reference/secrets.md` | §1.6.2 Credentials セクション |
| VPS 環境変数 | `/home/anicca/.env` | SSH: `anicca@46.225.70.241` |
| Railway Variables | Railway Dashboard | Staging / Production 各サービス |
