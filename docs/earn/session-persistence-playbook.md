# ブラウザ自動化ログインセッション永続化 — 採用判定と改修方針

調査日: 2026-07-13。手法: `gh search repos/code` + `crwl <url> -o markdown`（WebSearch/firecrawl/WebFetch は使用禁止指示のため未使用）。
対象: CloakBrowser（Chromium, CDP `:9222`, profile `~/.cloak/profiles/daily-driver`）を駆動する全ループ（gig/clip/video/IG/promote 等）。

## 実測した現状（採用/不採用の前提）

- `~/anicca/skills/browser/scripts/session_vault.py`: CDP `Storage.getCookies`/`Storage.setCookies` で cookie のみを30分毎に `~/.cloak/vault/daily-driver/auth-state.json` へ dump、死んだら `restore`。Playwright storageState と同じ思想。
- `~/anicca/skills/browser/ensure_browser.sh`: Chromium 死亡を検知したら `--user-data-dir="$HOME/.cloak/profiles/daily-driver"` を**固定**して再起動 → 生存確認後に `session_vault.py restore` を自動実行。**profile 丸ごと永続化はすでにできている**（cookie vault はその上の belt-and-suspenders）。
- 全ループは `~/anicca/skills/browser/SKILL.md`（`browser-foundation`, `disable-model-invocation: true`）経由で `ensure_browser.sh` を毎パス先頭で呼ぶ規律が既にある。配線の単一ポイントは確立済み。
- ギャップ: (1) cookie だけで localStorage/IndexedDB を保存していない (2) セッション延命（keep-alive）が無い (3) 2FA/passkey 自動化が無い。

## (1) 候補リポジトリ表

| 候補 | URL | star | 最終更新 | 何を解決するか | 判定 |
|---|---|---|---|---|---|
| Playwright 公式 Authentication (storageState) | https://playwright.dev/python/docs/auth | (公式docs) | 常時更新 | 「authenticated browser state を file に保存し再利用する」正本パターン | **参照のみ・既に自前実装済み**。session_vault.py は同じ思想を CDP 直叩きで再実装している |
| Browserbase Contexts | https://docs.browserbase.com/platform/browser/core-features/contexts | (SaaS, non-repo) | 常時更新 | Context = Chromium user-data-dir 丸ごと（cookie+localStorage+IndexedDB+ServiceWorker+Web Data）を暗号化保存し複数セッションで再利用 | **不採用（概念のみ流用）**。有料クラウドSaaSで自前 CDP 運用と非互換。だが「cookie だけでなく localStorage/IndexedDB まで含めるべき」という設計は正しく、§3 の改修に採用 |
| steel-dev/steel-browser | https://github.com/steel-dev/steel-browser | 7,327 | 2026-07-13 | セルフホスト型 Browser API サンドボックス一式 | **不採用**。CDP レイヤーごと置き換える規模の話で、永続化だけを解くには過剰。今の CDP:9222+profile 運用より優位な永続化機構は提供しない |
| browser-use/browser-use | https://github.com/browser-use/browser-use | 104,491 | 2026-07-13 | LLM 駆動ブラウザ agent フレームワーク（内部で storage_state 保存/復元） | **不採用（全面採用は過剰）**。session 保存パターンは Playwright storageState と同一発想で、我々が CDP 直叩きで既に持つ実装に対する優位性なし |
| Kaliiiiiiiiii-Vinyzu/patchright(-python) | https://github.com/Kaliiiiiiiiii-Vinyzu/patchright-python | 1,421 | 2026-07-12 | 検出回避パッチ済み Playwright | **不採用（別問題）**。bot 検出回避であってセッション永続化ではない。CloakBrowser が既にこの役割を担う |
| rebrowser/rebrowser-patches | https://github.com/rebrowser/rebrowser-patches | 1,396 | 2026-07-12 | Puppeteer/Playwright の自動化検出漏洩パッチ | **不採用（別問題）**。同上 |
| ultrafunkamsterdam/undetected-chromedriver, daijro/camoufox | https://github.com/ultrafunkamsterdam/undetected-chromedriver / https://github.com/daijro/camoufox | 12,747 / 10,025 | 2026-07-13 | anti-detect browser。profile 運用は可能だが我々の CDP 常駐 daily-driver と置き換える理由がない | **不採用** |
| pyauth/pyotp | https://github.com/pyauth/pyotp | 3,322 | 2026-07-13 | Python 公式TOTP(RFC6238)/HOTP 実装。`pyotp.TOTP(secret).now()` でauthenticatorアプリと同じ6桁コードを生成 | **採用**。(c) 2FA自動化の本命。authenticator-app型2FAを持つサービス（passkey強制でもSMS依存でもないもの）はこれで人間ゼロ化できる |
| 「session keep-alive heartbeat」専用OSSプロジェクト | `gh search repos "session refresh cron cookie"` 等、複数クエリで検索 | 0件ヒット | — | 「定期的に認証済み軽量リクエストを打ってsessionを延命する」専用ライブラリは存在しない | **該当なし＝自作対象**。パターン自体はSREの定番（synthetic monitoring）であり、ライブラリ化する価値のない数行のcronジョブ |

## (2) 推奨する1つの解

**乗り換えではなく現状維持＋3点改修。** 理由:

1. session_vault.py が実装している「cookie を JSON へ dump / restore」は Playwright 公式 Authentication ガイド（storageState を file に保存し再利用する）と同一パターンであり、CDP 直叩きで正しく再実装済み（引用: playwright.dev/python/docs/auth「Your authentication routine will produce authenticated browser state and save it to a file... reuse this state and start already authenticated」）。
2. Browserbase Contexts のドキュメント（引用: docs.browserbase.com/platform/browser/core-features/contexts「A Context persists the contents of the Chromium user data directory」）が示す「本命は cookie 単体でなく user-data-dir 丸ごとの永続化」は、`ensure_browser.sh` が `--user-data-dir="$HOME/.cloak/profiles/daily-driver"` を固定して既に実現している。cookie vault はその上の保険であって主防御ではない。
3. steel-browser / browser-use / patchright 等の候補はいずれも「CDPレイヤーごと置換」「bot検出回避」という別問題を解いており、今のCDP:9222運用に対して session 永続化の面で優位性がない ＝ 乗り換えコストに見合う利得なし（車輪の再発明を避ける）。
4. 唯一の真のギャップ（cookie-onlyでlocalStorageを見ていない／keep-alive無し／2FA自動化無し）は既存OSSの「乗り換え」では埋まらず、pyotp（採用）を組み込んだ自前拡張でしか埋まらない。

## (3) session_vault.py に足す具体的改修

**a. profile 永続化の固定（すでに実装済み・現状維持を明文化）**
`ensure_browser.sh` の `--user-data-dir` 固定と `session_vault.py restore` の自動呼び出しはこのままでよい。変更不要。

**b. cookie-only を localStorage/IndexedDB 込みに拡張**
CDP `Storage.getCookies` に加えて `DOMStorage.enable` → 各 origin の `DOMStorage.getDOMStorageItems` を叩き、`auth-state.json` に `{"cookies": [...], "origins": [{"origin": ..., "localStorage": [[k,v],...]}]}` の形（Playwright storageState と同スキーマ）で保存する。多くのSPA（Google含む一部)はセッショントークンをlocalStorageに置くため、cookieだけでは (b) サーバ側無効化と紛らわしい「実は取れていた」ケースを見逃す。

**c. keep-alive サブコマンドを追加**
`session_vault.py keepalive`: アカウントごとに1本、軽量な認証必須URL（例: coconalaマイページ、IGホーム）へ CDP 経由で `Page.navigate` → タイトル/URLパターンでログイン画面へのリダイレクトを検知。ログイン中確認時は何もしない（＝サーバ側セッションを"生かす"副作用がnavigateそのもの）、ログアウト検知時は即 `restore` を試み、それでも失敗したら `totp-login` へフォールバック。既存の30分cron（`ai.anicca.session-vault`）に `dump` の直後で呼ぶ一手で全ループに効く。

**d. TOTP 自動ログイン（pyotp採用）**
新規 `session_vault.py totp-login <site>`: サイトごとに1回だけ人間がTOTPをauthenticatorアプリ型2FAで有効化し、そのシークレットを `~/.cloak/vault/daily-driver/totp-secrets.json`（`chmod 600`、cookie vaultと同ディレクトリ＝同じ機密性ポリシー）に保存。ログインフォームで2FA入力欄が出たら `pyotp.TOTP(secret).now()` を `page.fill` するだけ。SMS/passkeyではなくauthenticatorアプリ型2FAに対応しているサービス（coconala等の国内SaaS含め多くが対応）はこれで人間ゼロ化できる。
**Google/Apple は別扱い**: Google は passkey強制でTOTPが効かない、Apple IDはSMS+Bluetooth依存でブラウザ内突破は狙わない。両方とも「ブラウザログインを避けて公式APIの長期トークンに逃がす」のが正しい設計（Gmail取得は既に `gog gmail` でAPI経由、App Store操作は既に `asc` CLIでAPIキー経由——このリポジトリに既にある回避パターンをそのまま踏襲するだけで、新しい調査は不要）。

## (4) 全ブラウザループへの共通配線

配線の単一ポイントは既に存在する: `~/anicca/skills/browser/SKILL.md`（`disable-model-invocation: true`）が「毎パスの先頭で `ensure_browser.sh` を呼べ」と全ループ（gig/clip/video/IG/promote/warmup）に強制している。改修はこの1ファイル系統にだけ足せば全ループに伝播する。

1. `ensure_browser.sh` の `RECOVERED` 分岐（既存の `session_vault.py restore` 呼び出しの直後）に `session_vault.py totp-login --if-locked-out` を追加 — cookie restore だけでは復旧しない (b)(c) のケースの最終防衛線。
2. launchd cron `ai.anicca.session-vault`（30分毎）に `dump` 直後で `keepalive` を追加 — 全アカウントの (b) サーバ側無効化を先回りで検知・延命。
3. 新規ループを書く開発者向けの規律を `browser/SKILL.md` に1行追記: 「ログイン壁に当たったら止まらず `session_vault.py totp-login <site>` を呼べ。Google/Appleだけはブラウザで粘らずAPI（`gog gmail`/`asc`）に逃がせ」。

## 未実装（次アクション）

上記 b/c/d はコード未実装（本タスクは調査+方針決定のみ）。実装は別途 GLVS（`vcsdd-init`→spec→impl）で回す。

## 引用一覧

- https://playwright.dev/python/docs/auth
- https://docs.browserbase.com/platform/browser/core-features/contexts
- https://github.com/pyauth/pyotp
- https://github.com/steel-dev/steel-browser
- https://github.com/browser-use/browser-use
- https://github.com/Kaliiiiiiiiii-Vinyzu/patchright-python
- https://github.com/rebrowser/rebrowser-patches
- https://github.com/ultrafunkamsterdam/undetected-chromedriver
- https://github.com/daijro/camoufox
- `/Users/anicca/anicca/skills/browser/scripts/session_vault.py`（実測済み既存実装）
- `/Users/anicca/anicca/skills/browser/ensure_browser.sh`（実測済み既存実装）
- `/Users/anicca/anicca/skills/browser/SKILL.md`（実測済み既存配線）
