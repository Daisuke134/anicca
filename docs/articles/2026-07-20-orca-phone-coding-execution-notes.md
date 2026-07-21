# execution-notes — Orca 記事

goal: Orca 記事を日本語・英語で note / X Articles / Zenn に公開し、実表示・課金状態・通知まで検証する。

## 公開済み

### note

- 日本語: https://note.com/anicca123/n/nfeca7663e750
  - HTTP 200。
  - API: `price=1000`, `is_limited=false`, `can_read=false`, `eyecatch=true`, `status=published`。
  - 匿名実表示 screenshot: `/Users/anicca/.cloak/note-work/verify-nfeca7663e750.png`。
  - 本文画像 4/4、目次、表、縦図、ペイウォール開始位置を DOM と目視で確認。
- English: https://note.com/anicca123/n/nae7d557ad6ff
  - HTTP 200。
  - API: `price=1000`, `is_limited=false`, `can_read=false`, `eyecatch=true`, `status=published`。
  - 匿名実表示 screenshot: `/Users/anicca/.cloak/note-work/verify-nae7d557ad6ff.png`。
  - 本文画像 4/4、目次、表、縦図、ペイウォール開始位置を DOM と目視で確認。

### X Articles

- 日本語: https://x.com/diceai0/article/2079585582758646185
  - status: https://x.com/diceai0/status/2079585582758646185
  - HTTP 200。本文画像 4、最大表示高 545px、650px 超過 0、全8章を live DOM と screenshot で確認。
- English: https://x.com/diceai0/article/2079586493526675550
  - status: https://x.com/diceai0/status/2079586493526675550
  - HTTP 200。本文画像 4、最大表示高 545px、650px 超過 0、全8章を live DOM と screenshot で確認。

## 品質・事実検証

- 未検証5項目は Orca / Anthropic / OpenAI / GitHub / Microsoft / Tailscale の公式文書と GitHub 一次情報で確認。引用と URL は `2026-07-20-orca-phone-coding-research.md` に保存。
- lane A の一人称 récit。verdict box、アニッチャ CTA、Fable/Sol、曖昧な「ターミナルはこちらが」の一文は不使用。
- 日本語の独立レビュー 41/50、英語 42/50。全角ダッシュ、命題型 H2、`###`、言語混入の各 gate は PASS。
- 無料版 gate stamp:
  - JP: `939abac7e52f50e9017b97233a9fc186`
  - EN: `363d77d13a9390cb2af56b699b15d7a7`
- Zenn ローカル render は日英とも、表1、Mermaid SVG1、broken image 0。全章 screenshot を目視確認済み。

## Zenn の現在地と再開条件

- 下書き同期 commit は remote `main` へ push 済み。日英とも draft API は `public=false` を確認。
- 日本語稿を `published:true` で push し、no-lie gate は PASS。ただし live 検証は `HTTP 403 | NOT-LIVE`。
- Zenn API の直近公開は `2026-07-21T17:10:21.742+09:00`。24時間枠の次回試行可能時刻は `2026-07-22T17:10:21.742+09:00` 以降。
- 日本語の再トリガーと live 検証後、英語はさらに次の24時間枠で公開する。英語稿は現在 `published:false`。
- 予定 URL:
  - 日本語: https://zenn.dev/anicca/articles/orca-iphone-ai-development-ja
  - English: https://zenn.dev/anicca/articles/orca-iphone-ai-development-en
- Zenn 日英 live、カードの done 移動、最終 commit/push、AgentMail 送信/read-back は未完了。完了報告・完了メールはまだ送らない。

## 生成物

- 日本語原稿: `docs/articles/2026-07-20-orca-phone-coding-jp.md`
- 英語原稿: `docs/articles/2026-07-20-orca-phone-coding-en.md`
- 無料版: `docs/articles/2026-07-20-orca-phone-coding-{jp,en}-free.md`
- research: `docs/articles/2026-07-20-orca-phone-coding-research.md`
- eyecatch: `docs/articles/assets/orca/eyecatch-{jp,en}-v2.png`
- Zenn canonical source: `~/.openclaw/workspace/zenn-articles/articles/orca-iphone-ai-development-{ja,en}.md`
