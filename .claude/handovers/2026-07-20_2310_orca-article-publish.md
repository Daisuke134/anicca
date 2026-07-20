# Handover: Orca 記事 — 執筆完了、公開は STEP 2 から再開（token 切れで停止）

★2026-07-21 更新2（最新）: **note draft は既に存在する。** API 実測（23:59）:
- draft key = `nfeca7663e750`、status=draft、price=0
- 本文 11,982 字、画像 3 枚埋め込み済み（@@marker 残 0）、eyecatch 設定済み
- つまり PLAN の STEP 2+3 は完了。**残り = STEP 4（検証gate: draft screenshot + DOM assert）→ STEP 5（publish-paid --key nfeca7663e750 --price 1000 --after-chars 2445 --tags "ClaudeCode,AIエージェント,iPhone,AI開発,開発環境" --arm、NOTE_MODE=go）→ STEP 6-9（無料版/Zenn/X/カード書き戻し/メール）**
- カードは in-progress/ に戻した（queue 比較実験は中止、codex が直接 publish する）。
- 注意: 目次(TOC)挿入が済んでいるかは未確認 → STEP 4 の screenshot で確認し、無ければ insert-toc-save.py を先に。

## Codex 起動 prompt（これをそのまま `codex` に貼る）

```
codex exec -m gpt-5.6-sol --sandbox danger-full-access --skip-git-repo-check "この handover /Users/anicca/anicca-project/.claude/handovers/2026-07-20_2310_orca-article-publish.md と plan /Users/anicca/anicca-project/PLAN-orca-publish.md を読め。note draft nfeca7663e750 は作成済み（本文11,982字・画像3枚・eyecatch有、API実測済み）。STEP 4 から STEP 9 まで順に実行して記事を公開し切れ: (4)draft screenshot+DOM assert検証、TOC無ければ insert-toc-save.py (5)publish-paid.py --key nfeca7663e750 --price 1000 --after-chars 2445 --tags 'ClaudeCode,AIエージェント,iPhone,AI開発,開発環境' --arm を NOTE_MODE=go で実行し API readback で price=1000 確認 (6)make-free-version.py で無料版 (7)Zenn publish-to-zenn.sh slug=orca-iphone-ai-dev-setup、rate limit で NOT-LIVE なら bug ではない・報告して続行 (8)X Articles draft (9)カードを ~/profitable-claude/skills/article-writer/topics/in-progress/orca-phone-coding-setup.md から done/ へ mv し frontmatter に status: published と実URL を書いて commit+push、最後に AgentMail（~/.openclaw/.env の AGENTMAIL_API_KEY、inbox myclaude-clip@agentmail.to）で keiodaisuke@gmail.com へ全 live URL を送り thread read-back で検証。禁止: 検証gateの skip、rtk proxy 使用、本文の書き換え。exit code でなく API readback と file 実在で検証しろ。" < /dev/null
```

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
