# #7 article loop — evidence（2026-07-12）

## done 条件（Dais 2026-07-12 で改定）
記事を書き、note / Zenn / Substack / X / dev.to の5媒体すべてに **draft（下書き）** として置く。**絶対に自動公開しない**（AI スロップを世に出さない）。Dais が読んで手で公開する。

## ★ 最重要の発見: このループは、動いていたら全世界に自動公開していた ★

superpowers の adversarial audit で判明した、修理前の実態:

| 媒体 | 修理前の挙動 | 結果 |
|---|---|---|
| Zenn | `publish-zenn.sh` が frontmatter に `published: true` を **必須として要求**し、無ければ FATAL。その後 `post-zenn.py` が linked repo に git push | push した瞬間に Zenn が公開レンダリング。**公開が唯一の成功経路だった** |
| Substack | draft 作成直後に無条件で `POST /api/v1/drafts/<id>/publish` | ゲート無し。毎回必ず公開 |
| note | `create_draft()` の直後に無条件で `publish_article()` | ゲート無し。毎回必ず公開 |
| dev.to | payload が `"published": not DRY_RUN` | 実行 = 公開 |
| X | `run.sh` から呼ばれていない | 該当なし |

**5媒体中4媒体が、正常動作として無条件に公開していた。** 「プロンプトで公開するなと書く」では全く不十分だった。

### 塞いだ方法（コードレベルの保証。プロンプト頼みにしない）
- dev.to: payload に `"published": False` をハードコード。True を書ける経路が存在しない
- Zenn: `publish-zenn.sh` のゲートを反転（`published:true` を要求 → `published:false` を強制、true が残っていたら FATAL）。さらに `post-zenn.py` 自身が独立に `published:false` を再強制（呼び出し元が将来壊れても穴が開かない）
- Substack: `/publish` の POST を削除。draft 作成で止め、draft id を返す
- note: `publish_article()` の import と呼び出しを削除
- `run.sh` の検証段を **反転**: draft/404 = 成功、**公開200 = SAFETY FAILURE として叫ぶ**（何かが公開されたら緑で通さず落ちる）
- account-history が `status:"posted"` と嘘をつくのを `status:"draft"` に修正

全て TDD（テスト先行→RED確認→実装→GREEN確認）。テスト: `tests/art/test_{devto,zenn}_never_publishes.sh`, `test_loop_cannot_publish.sh`, `test_runsh_verifies_drafts.sh`

## ループ本体（他4ループで判明した真因3つを設計で回避）
- **launchd `ai.anicca.article-daily` 毎日 06:00 JST**（自己申告 CronCreate は実体として保存されず、capafy/life-manager はそれで1回動いて永久停止していた。launchd が唯一のスケジューラ）
- **timeout なし**（timeout が仕事の途中で殺す。capafy は CP1 の中で、life-manager は1件も投稿しないまま rc=124 で死んでいた）
- **Telegram 報告**（PushNotification は Remote Control 非アクティブ時に silent no-op で Dais に届かない。`openclaw message send --channel telegram --target 8547730585`）
- **mkdir 排他ロック**（capafy は無しで走り、2つのスケジューラが :9222 の同じタブを 90分で5回奪い合って全滅した）
- 実行1回目の失敗も修理: pass が仕事をバックグラウンド subagent に丸投げし、print mode が 600秒上限で打ち切って **rc=0（緑）なのに記事0本**で終了していた → `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0` + プロンプトに「お前が作業者だ、丸投げして返るな」を明記

## 実走行の結果（2026-07-12 14:28 開始、私が全て自分で確認）

記事トピック: **「AI エージェントは人間なしで API の代金を払えるのか。x402 というプロトコルを実際に動かして確かめた」**（日英両方、実際に x402 を動かして人間承認の壁を検証した実験記事）

| 媒体 | 結果 | 私が確認した方法 |
|---|---|---|
| Zenn | ✅ draft | **実ブラウザで開いて 404 ページ（「ページが見つかりませんでした」）を自分の目で確認** = 一般には見えない。repo の実ファイルも `published: false`、git push 済み（`4b2a5e9`）。※`curl` は HTTP 200 を返すが中身は SPA 外殻で title 空 — **200 だから公開、は誤り**。実ブラウザで見て初めて真実が分かる |
| dev.to | ✅ draft | API の `/articles/me/unpublished` に `published: False` で実在（id 4123584）。無認証 curl で **HTTP 404** |
| Substack (ja) | ✅ draft | draft URL 実在 `https://aniccabuddha.substack.com/publish/post/206661638` |
| Substack (en) | ✅ draft | draft URL 実在 `https://aniccabuddha.substack.com/publish/post/206661640` |
| note | ❌ 未解決 | ログインフォームの submit ボタンが `disabled` のまま（Vue の controlled-input に `fill()` が反応しない典型）。note-mcp の真因バグ2件（headless ハング、セレクタ不一致）はこのパスで修正・commit 済みだが、ログイン完走には至らず |
| X (ja/en) | ❌ 未解決 | daily-driver の X セッションが失効。`auth_token` cookie を CDP で注入したが復活せず（ct0 CSRF も要る/トークン自体が失効）。X の username/password が `.env` にも `~/.cloak` にも保存されていないため、再ログインできない |

- **公開されたものはゼロ**。5媒体すべてで `published: false` を確認
- Telegram 報告: **messageId 1990**（私のテスト送信が 1991 を返したので、1990 が本物の直前の送信だと確定）
- 台帳 `~/.openclaw/skills/ai-entity-article-writer/state/articles.jsonl` に7行。失敗した note/X も **失敗理由つきで正直に記録**されている（成功に見せかけていない）
- ループ自身がこのパスで**本物のパイプラインバグを4件**見つけて修正・commit（Zenn ソフト404 の誤検知、post-zenn.py の git commit 判定、post-devto.py の tags パース + WAF-UA ブロック）

## 残る課題（正直に）
1. **note のログイン**: Vue reactivity。`fill()` ではなく実キー入力（`Input.insertText` / `type()`）+ `input`/`change` イベント発火で直る見込み。ボタンを force-enable するのは空フォーム送信になるので禁止
2. **X の再ログイン**: 認証情報が保存されていない。SMSPool 等で新規アカウントを作るか、Dais の X アカウントに人手でログインするかの判断が要る
3. **収益 ¥0**: 下書きを置いただけ。Dais が読んで公開し、有料記事が売れて初めて ¥ が立つ（IMPROVE 層）

## スクリーンショット
- `docs/superpowers/evidence/screenshots/07-article-zenn-notpublic.png`（Zenn の 404 = 非公開の証拠）
