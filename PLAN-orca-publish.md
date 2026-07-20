# PLAN — Orca 記事の全プラットフォーム公開（executor: codex Sol。Fable は plan と最終検証のみ）

対象記事: `docs/articles/2026-07-20-orca-phone-coding-jp.md`（執筆・slop gate 済み。**本文は 1 文字も変更禁止**）

## 実行済み（再実行するな）

- stage1 render 済み: `~/.cloak/note-work/orca-stage/`（tbl1.png, tbl2.png, note-manifest.json。tables=2, mermaids=1）
- eyecatch 生成済み: `~/.cloak/note-work/orca-assets/eyecatch.png`（1731x909、目視検証済み）
- note cookie 有効: `~/.cloak/note-work/note-cookies.json`（CDP live 抽出、current_user=anicca123 確認済み 22:44）
- タグ実測済み。使うタグ: `ClaudeCode,AIエージェント,iPhone,AI開発,開発環境`
- kroki.io は死んでいる（Error 400 実測）→ mermaid は `npx -y @mermaid-js/mermaid-cli` で local render（PNG 生成成功を実測済み）

## STEP 1: mermaid PNG render

note-manifest.json の mermaids[0] を `/tmp/orca-fig1.mmd` に書き出し、
`npx -y @mermaid-js/mermaid-cli -i /tmp/orca-fig1.mmd -o ~/.cloak/note-work/orca-stage/fig1.png -b white --scale 2`
PNG が生成されたことを `file` で確認。

## STEP 2: note draft 作成（scripts はすべて `.claude/skills/ai-entity-article-writer/scripts/` 配下、python は `~/.openclaw/skills/_shared/venv-cloak/bin/python3`）

- `note-stage2-publish.py` 相当で draft 作成: create_draft → 画像 upload（tbl1/tbl2/fig1）→ @@TBLn@@/@@FIGn@@ marker 差し替え → update_article（KEY 形式、numeric id は upload のみ）。
- 図の埋め込みは `generate_image_html(url, width=min(naturalW,460))`、表は width≈560。note は本文を ~620px に upscale するので cap 必須。
- exit code 0 でも信じるな: meta の embedded=N/M が 3/3 であること、marker が本文に残っていないことを grep で確認。
- 環境変数やスクリプトの引数仕様はスクリプト本体を読んで確認してから実行（Automaton 時代のハードコードが残っている場合は --key/--src 等の generic 経路を使う。無理なら最小 wrapper を /tmp に書く）。

## STEP 3: eyecatch + 目次

- eyecatch: `set-eyecatch-draft.py`（画像 = `~/.cloak/note-work/orca-assets/eyecatch.png`。本文には入れない）。API で `eyecatch != null` を確認。
- 自動目次: `insert-toc-save.py`（最初のセクション後、gutter [＋]→目次）。

## STEP 4: 検証 gate（必須。skip したら FAIL）

- ephemeral `launch_context(headless=True)` + note cookie で draft edit URL を開き、full-page screenshot を `~/.cloak/note-work/orca-stage/verify-*.png` に保存。
- DOM assert: 画像数 = 4（tbl2 + fig1 + eyecatch）… eyecatch は body 外なので body img = 3。`document.querySelectorAll('img')` の naturalWidth>0 を全数確認。@@TBL/@@FIG marker の残存 0。h3 = 補足のみ or 0。
- screenshot ファイルパスを agmsg で fable-main に報告（Fable が Read で目視する）。**ここで一旦停止して Fable の GO を inbox で待て。**

## STEP 5: note 公開（Fable の GO 受信後）

`note-publish/publish-paid.py --key <draft key> --price 1000 --after-chars 2445 --tags "ClaudeCode,AIエージェント,iPhone,AI開発,開発環境" --arm`
- --after-chars 2445 = [4] セットアップ実録末尾直前（実測済み。ただし publish-paid は rendered DOM の leaf-text 累積で判定するので、guard-stop run（--arm 無し）を先に 1 回走らせ FREE_ENDS_WITH が「…自動接続します。」付近 / PAID_STARTS_WITH が「実際に使った初日の所感…」付近であることを確認してから --arm）。
- NOTE_MODE=go を env に付ける（Dais 2026-07-20 無人公開許可済み）。
- 公開後 `GET https://note.com/api/v3/notes/{key}` で price=1000, is_limited 確認。結果 JSON の該当 fields を agmsg で報告。

## STEP 6: 無料版生成

`scripts/_shared/make-free-version.py --markdown-file docs/articles/2026-07-20-orca-phone-coding-jp.md --note-url <本番URL> --price 1000 --after-chars 2445 --paid-contents "初日の所感、cloud案とどちらを選ぶかの判断、おすすめできる人の整理" --summary-file /tmp/orca-summary.md --out ~/.cloak/note-work/2026-07-20-orca-free.md`
- summary-file は自分で書く: 無料部の takeaway 3-5 bullets（slop 禁止、体言止め可）。
- 出力が teaser H2 で終わっていないこと（script が guard するが確認）。

## STEP 7: Zenn 公開

`scripts/zenn-publish/publish-to-zenn.sh` を adapt → gate → render → draft → enable → ZENN_MODE=go publish の順で。
- slug: `orca-iphone-ai-dev-setup`（a-z0-9 hyphen、12-50字）
- adapt 引数: `<src=無料版でなく元記事> <slug> "ノートPCを返却しました。今日からiPhoneだけでAI開発します" 📱 "claudecode,ai,orca,iphone" "## 初日に一番よかったのは並列作業の見通しでした"`（paid-from = 有料開始見出し。そこから後ろを cut）
- no-lie gate 必須。render は preview screenshot を撮って agmsg でパス報告。
- **注意: 今日 17:08 に 1 本公開済み → 24h rate limit の可能性。publish 後 verify が NOT-LIVE でも bug ではない。その場合「rate-limited、window 明け再 trigger 要」と agmsg で報告して次の STEP へ進め。**

## STEP 8: X Articles

skill `x-article-publisher`（`~/.claude/skills/x-article-publisher/`）の `publish_md_to_x.py` で無料版 md を X Articles draft に。
- 画像: fig1.png と tbl PNG は幅 600px 未満なら engine が auto-pad する。consecutive_anchor_collision WARN が出たら transition 文を足す…のではなく Fable に報告（本文改変は Fable 判断）。
- draft 作成まで（X は draft-only 運用）。draft URL を agmsg で報告。

## STEP 9: 報告

全 URL（note 本番 / Zenn / X draft）+ 各検証結果（API fields、HTTP code、screenshot パス）を agmsg で fable-main に送信:
`~/.agents/skills/agmsg/scripts/send.sh orca-article sol-codex fable-main 'PUBLISHED <note-url> <zenn-url-or-ratelimited> <x-draft-url>'`

## 禁止

- 本文の書き換え（1 文字も）。
- 検証 gate の skip。mock/dry での「公開した」報告。
- Dais 個人 SNS への投稿。
- STEP 4 の GO 待ちの skip（note の 投稿する click だけは Fable の GO 後）。

## Block 条件

同一エラー 3 回 / 資格情報切れ → その時点の状態を agmsg で報告して停止（勝手に代替経路を発明しない）。
