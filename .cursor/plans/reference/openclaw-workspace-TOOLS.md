# TOOLS.md (OpenClaw workspace template)

このファイルは OpenClaw のエージェントワークスペース直下に置くことを想定しています:

- `~/.openclaw/workspace/TOOLS.md` (VPS)

OpenClaw はセッション開始時に `AGENTS.md` / `SOUL.md` / `TOOLS.md` などをエージェント文脈へ注入します。

## Web / Browser ツール

この環境では Web 検索とWeb取得が利用できます（利用不能と断定しない）。

- `web_search`: Web検索（Brave Search API など）
- `web_fetch`: HTTP fetch + readable extraction（JSは実行しない）
- `browser`: JS-heavy sites / ログインが必要なサイト向け（ブラウザ自動化）

運用ルール:

- 「株価」「最新」「公式ドキュメント」「URLが必要」などは、まず `web_search` で一次情報（公式ドキュメント/API）を特定し、URL付きで返す。
- ツールが失敗した場合のみ、実際のエラー内容を短く報告し、次善策を提示する（推測で「使えない」と言わない）。

