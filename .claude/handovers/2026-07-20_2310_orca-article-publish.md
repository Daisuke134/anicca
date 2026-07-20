# Handover: Orca 記事 — 執筆完了、公開は STEP 2 から再開（token 切れで停止）

★2026-07-21 更新: カードは queue/ に戻した（Dais 指示: codex 手動実行 vs 朝の article loop の比較実験のため）。
場所 = `~/profitable-claude/skills/article-writer/topics/queue/orca-phone-coding-setup.md`（commit 6900421）。
どちらの経路でも: 記事本文は執筆済み・変更禁止、この handover と PLAN-orca-publish.md STEP 2〜 が実行手順の正本。

## 完了済み（全部実測検証済み）

- リサーチ 5 項目: `docs/articles/2026-07-20-orca-phone-coding-research.md`（commit ee96355d8、一次情報 URL 付き）
- 記事本文完成: `docs/articles/2026-07-20-orca-phone-coding-jp.md`（6,614字、###=0、全角ダッシュ=0、H2 名詞句化・slop gate 済み。無料部 = 「## 初日に一番よかった…」直前まで 2,445字）
- stage1 render 済み: `~/.cloak/note-work/orca-stage/`（tbl1.png / tbl2.png / fig1.png(330x1180) / note-manifest.json）
- eyecatch: `~/.cloak/note-work/orca-assets/eyecatch.png`（1731x909、目視済み。本文に入れない）
- note cookie 有効（CDP live 抽出、current_user=anicca123）。タグ実測済み: ClaudeCode,AIエージェント,iPhone,AI開発,開発環境
- skill 修正: kroki 障害時の local mermaid-cli fallback を SKILL.md に永続化（~/.openclaw commit 8592063a。**push は remote reject — 他セッションの大容量ファイル commit(578MB tar.gz 等)が main-internal に積まれているのが原因、本タスク外。~/.openclaw を管理しているセッションが解決すべき**）

## 残り（公開 loop / 朝の claude-p article loop がやる）

実行 plan の正本 = `/Users/anicca/anicca-project/PLAN-orca-publish.md`（STEP 2 から。STEP 1 は完了済み）。
1. note draft 作成 → eyecatch → 目次 → 検証gate（screenshot + DOM assert）→ `publish-paid.py --key <draft> --price 1000 --after-chars 2445 --tags "ClaudeCode,AIエージェント,iPhone,AI開発,開発環境" --arm`（NOTE_MODE=go、Dais 2026-07-20 無人公開許可済み）→ API readback（price=1000/is_limited）
2. 無料版: make-free-version.py（--after-chars 2445）→ Zenn（slug `orca-iphone-ai-dev-setup`。**今日 17:08 に 1 本公開済み → 24h rate limit あり得る。NOT-LIVE でも bug ではない、window 明け empty commit で再 trigger**）→ X Articles draft（x-article-publisher）
3. カード書き戻し: `~/profitable-claude/skills/article-writer/topics/in-progress/orca-phone-coding-setup.md` → done/ へ mv + frontmatter に status: published + 実URL + commit/push
4. AgentMail で keiodaisuke@gmail.com へ全 live URL（`~/.openclaw/.env` の AGENTMAIL_API_KEY、inbox myclaude-clip@agentmail.to、POST /v0/inboxes/.../messages/send）→ thread read-back 検証。**メール未送 = タスク未完了**

## 既知の罠（今夜踏んだもの）

- kroki.io 死亡中 → local mermaid-cli（chrome-headless-shell install 済み、`file` で PNG 実在確認必須）
- note の on-disk Cookies sqlite は session cookie が欠ける → CDP live 抽出（TROUBLESHOOTING.md 参照)
- codex(Sol) に `rtk proxy` 経由でコマンドを打たせると失敗する → 素のコマンドで
- agmsg team `orca-article` 作成済み（fable-main / sol-codex join 済み）
