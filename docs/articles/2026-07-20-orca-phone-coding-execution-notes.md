# execution-notes — Orca 記事（2026-07-20）

goal: 「ノートPCを返却しました。今日からiPhoneだけでAI開発します」執筆 → note(¥1000)/X Articles/Zenn 公開 → AgentMail 完了メール。

## 進捗（evidence 付き）

- 22:35 カードを queue/ → in-progress/ へ mv、commit+push 済み（profitable-claude repo、commit "chore: move orca-phone-coding-setup card to in-progress"）。
- 22:36 TaskList #1-#7 登録。
- 22:38 ★未検証5項目★ を research 2 並走で調査中（research-landscape = 競合全数+分類軸、research-tech = Tailscale-in-sandbox / Orca残量表示 / Cmux）。
- 22:40 note タグ実測（tag-counts.py）: ClaudeCode=40,468 / AIエージェント=45,234 / iPhone=49,873 / AI開発=9,286 / 開発環境=1,650 / Orca=255 / リモート開発=76 / スマホ=119,908。

- 22:50 eyecatch 生成完了（chatgpt-imagegen web backend、~/.cloak/note-work/orca-assets/eyecatch.png、1731x909、日本語テキスト「ノートPCを返却しました / iPhoneだけでAI開発」崩れ無しを Read で目視確認）。

## リスク（実測）

- Zenn: 2026-07-20 17:08 JST に `2026-07-20-set-cookiex30` を公開済み（git log 実測）。24h 1 本の rate limit に当たる可能性 → push 後 NOT-LIVE なら window 明け（明日 17:08 以降）の再 trigger（empty commit）で解決。bug ではない。
- note cookie: on-disk sqlite は `_note_session_v5` 欠落 → CDP live 抽出で 8 cookie 取得、`/api/v2/current_user` = anicca123 で有効性確認済み（22:44）。

## 決定

- タグ候補（5個以内、giant 回避）: ClaudeCode / AIエージェント / iPhone / AI開発 / 開発環境。
- 価格 ¥1,000（explainer 型、カード指定）。paywall = [4] セットアップ実録の末尾直前（--after-chars は draft 確定後に実測）。
- 図表: [3] mermaid 1枚（≤6 node 縦 chain、kroki→PNG、cap460/高さ box fit）、[2][6] 比較表 PNG（1080px 幅統一）。eyecatch = gpt-image-2（本文に入れない）。
- ## は章タイトルのみ、### 禁止（note 自動目次を短く保つ）。
