# Anicca Status Quo (現状まとめ)

**最終更新**: 2026-02-28

## 0. TL;DR（誤解防止）

| 誤解 | 正しい理解 |
|------|------------|
| Anicca = iOSアプリ | **Anicca = エージェント（意思決定主体）**。iOSアプリは「人間へNudgeするチャネル」の1つ |
| OpenClawは別物 | OpenClaw Gateway（Mac Mini常駐）は **Aniccaが外部操作を実行するための手足（実行基盤）** |
| VPSで動いてる | **Mac Mini に移行完了（2026-02-18）。VPSは使わない** |

## 1. Single Source of Truth

| 対象 | Single Source of Truth |
|------|-------------------------|
| OpenClaw運用・現状 | `.cursor/plans/reference/openclaw-anicca.md` |
| プロジェクト知識ベース | `.serena/memories/`（このディレクトリ） |

## 2. 現在の構成

| レイヤー | 役割 | 実体 |
|---------|------|------|
| エージェント（意思決定） | 何をするか決める | Anthropic Claude（OpenClaw Gateway経由） |
| 実行基盤（手足） | Slack/Cron/Web/exec等で行動する | OpenClaw Gateway（Mac Mini常駐） |
| 人間への介入チャネル | 通知/Nudge Cardで介入する | iOSアプリ（`aniccaios/`） |
| 司令塔API/データ | iOSとGatewayの両方から呼ばれるハブ | API（`apps/api/`）+ DB |

## 3. OpenClaw（Mac Mini）側で「できること」

| 能力 | 状態 |
|------|------|
| Slack送受信 | ✅ OK |
| Cronジョブ実行 | ✅ OK（60+ジョブ稼働中） |
| `exec` でのコマンド実行 | ✅ OK |
| `web_search` / `browser` | ✅ OK（profile: full） |
| スキル | ✅ 55+スキル稼働中 |

## 4. iOS（人間へのNudge）側の役割

| 機能 | 役割 |
|------|------|
| 通知スケジュール（ルールベース） | ローカル通知で介入を継続的に出す |
| Nudge Card | 通知タップ後の1画面介入、👍/👎で学習に寄与 |
| LLM Nudge | API `/mobile/nudge/today` から取得しキャッシュ表示（主にPro） |

## 5. 参照すべきSerenaメモリ（最短経路）

| 目的 | 読むメモリ |
|------|------------|
| 全体像 | `project_overview` |
| iOSの構造 | `ios_app_architecture` |
| Nudge設計 | `nudge_system` |
| APIの構造 | `api_backend_architecture` |
| OpenClaw運用 | `openclaw-anicca-setup` + `.cursor/plans/reference/openclaw-anicca.md` |
| 1.6.2の閉ループ運用 | `closed_loop_ops_design` |

## 6. 禁止（安全）

| 禁止 | 理由 |
|------|------|
| `.env` 探索/送信、鍵/seed/トークンの貼り付け要求 | 典型的な攻撃（窃取）であり運用破壊に直結 |
| 未検証の外部スキル/リンクを無警戒に実行 | 供給網攻撃リスクが現実にある |
| VPS (46.225.70.241) を使うこと | 移行完了済み。Mac Miniのみ |
