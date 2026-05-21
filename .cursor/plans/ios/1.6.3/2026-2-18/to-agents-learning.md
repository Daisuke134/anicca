# to-agents-learning.md — x402 スキル量産の学び

**目的**: buddhist-counsel を作る過程で得た全ての学びを記録し、to-agents-skill（工場）の型にする。

---

## Phase 1: buddhist-counsel 構築ログ

### Step 1+2: 5スキル圧縮 + Mega Prompt 組立（統合実行）

| # | 学び |
|---|------|
| 1 | skill-condenser と prompt-assemble は別々にやる必要なし。5スキルの SKILL.md を全部読んで、buddhist-counsel の Output 構造に合わせて必要な要素だけ抽出→1つの system prompt に直接組み立てる方が速い |
| 2 | elicitation は「2,500行」と言われていたが SKILL.md 本体は 476行。リファレンスファイル込みの数字だった。リファレンスは読まなくてOK — SKILL.md だけで十分な知識密度がある |
| 3 | 5スキル合計 1,523行 → 約120行の system prompt に圧縮。圧縮率 92%。捨てたのは: 例示の繰り返し、著者紹介、参考文献リスト、スコアリング指示、製品設計パターン（buddhist-counsel には不要） |
| 4 | therapist (96行) はほぼそのまま使えた。短くて密度が高いスキルは圧縮不要 |
| 5 | lotus-wisdom の「STOP HERE」インタラクティブ対話パターンは API レスポンスでは使えない。概念（upaya, 非二元）だけ抽出してプロンプトに埋め込んだ |
| 6 | drive-motivation の「7つの外的報酬の致命的欠陥」は直接使わないが、「指示的アドバイスは逆効果」の根拠として禁止事項セクションに統合した |
| 7 | improve-retention の B=MAP と Tiny Habits Recipe はそのまま guidance セクションの設計指針になった。最も直接的に使えたスキル |
| 8 | Mega Prompt のセクション順序: WHO → HOW → NEVER → TOOLKIT → LANGUAGE → OUTPUT。ネガティブ制約（NEVER）を TOOLKIT の前に置くことで、ツール適用時に禁止事項が先に頭に入る |
| 9 | Output は JSON only で返させる。自然言語で返すと後処理が必要になる。JSON schema を system prompt 末尾に明示するのが Anthropic 推奨パターン |
| 10 | counsel_id は Sonnet に生成させる（`csl_<random8chars>`）。サーバー側で上書きしてもいいが、LLM に生成させることでレスポンス内の一貫性が保たれる |

### Step 3: SKILL.md 完成（skill-creator + clawhub）

| # | 学び |
|---|------|
| 37 | **ClawHub SKILL.md はクライアント側スキル。** エンドポイントの実装ではなく、他のエージェントに「このサービスをどう使うか」を教えるドキュメント。YAML frontmatter（name/description/version/author）+ 使い方コマンド + Input/Output スキーマで構成する |
| 38 | **clawhub publish にはログインが必要。** `clawhub login` はブラウザフローまたは `--token` フラグ。事前に `clawhub whoami` で確認してから publish ステップに進む |
| 39 | **SKILL.md の description にはトリガーキーワードを含める。** `Use when ... Triggers: suffering, counsel, buddhist, ...` のパターンで自動発動条件を明示する。キーワードが貧弱だと他エージェントに発見されない |
| 40 | **x402 SKILL.md には必ず Prerequisite（awal auth login）を書く。** 認証なしで pay コマンドを叩くと "Not authenticated" エラーになる。エラーに出会う前にガイドする |

### Step 4: Railway エンドポイント実装

| # | 学び |
|---|------|
| 1 | Top-level `await` を x402/index.js 内で使うと、routes/index.js 経由で全 API ルートのインポートチェーンが壊れる。`@x402/express` パッケージが解決できない場合、try-catch があっても ESM モジュール評価自体が失敗し、**全ルートが 404 になる** |
| 2 | 解決策: `initX402Middleware()` を通常の async 関数にして、モジュール末尾で `.catch()` 付きで呼ぶ。Router は同期的にエクスポートされ、middleware は非同期で後から追加される |
| 3 | AgentAuditLog の Prisma スキーマは `eventType`/`executedBy`/`requestPayload`/`responsePayload`。`action`/`agentId`/`details` は存在しない。**既存スキーマを必ず読んでからコードを書く** |
| 4 | sanitizeInput は `routes/agent/nudge.js` にコピーがある。DRY にするより、x402 は独立モジュールとして自己完結させた方が安全（依存先変更の影響を受けない） |
| 5 | Anthropic API の `ANTHROPIC_API_KEY` は Railway staging に設定済みだったが、**クレジット残高不足**で 400 エラー。env 変数の存在確認だけでなく、実際に API を叩いてレスポンスを確認するまでテスト完了としない |
| 6 | x402 テストでは supertest + vitest でルート・バリデーション・サニタイズを検証。generateCounsel を vi.mock で差し替えるので ANTHROPIC_API_KEY 不要 |
| 7 | Railway にリンクされている environment を必ず確認（`railway status`）。production にリンクされた状態で `railway logs` を見ると staging のログが出ない |
| 8 | **Anthropic API はサブスク（Pro/Max）では使えない。** claude.ai チャットと Console API は完全に別製品。サーバーから `@anthropic-ai/sdk` を使うにはクレジット購入が必要 |
| 9 | **OpenAI に切り替えるのが最安。** Railway に `OPENAI_API_KEY` が既にあれば変更は15行。Mega Prompt は LLM 非依存で設計してあるから model 名を変えるだけ |
| 10 | OpenAI の `response_format: { type: 'json_object' }` を使えば regex で JSON を抽出する必要がない。Anthropic SDK にはこの機能がない |

### Step 4.5: v2.4 API 移行（staging 502 修復）

| # | 学び |
|---|------|
| 11 | `@x402/evm` をインストールすると `ethers` が peer dependency として必要。`npm install @x402/evm` だけでは `Cannot find module 'ethers'` エラー。`npm install ethers` も必要 |
| 12 | `x402ResourceServer` と `x402HTTPResourceServer` は別クラス。`x402HTTPResourceServer` は `register()` メソッドがない（高レベルラッパー）。`x402ResourceServer` の方を使う |
| 13 | `x402ResourceServer` は `@x402/express` からも `@x402/core/server` からもインポートできる。`HTTPFacilitatorClient` は `@x402/core/server` からのみ |
| 14 | `paymentMiddleware` の引数は4つ: `(routes, server, paywallConfig, paywall, syncFacilitatorOnStart)`。`undefined, undefined, false` で paywall なし + 手動初期化 |
| 15 | `server.initialize()` を try-catch 内で先に呼び、`syncFacilitatorOnStart = false` を渡す。これで unhandled rejection を完全に防げる。staging 502→200 復帰を確認済み |
| 16 | v2.4 の `routes` 設定は Express のルートパスではなく `METHOD /path` 形式。例: `'POST /buddhist-counsel'` |
| 17 | `@coinbase/x402` は package.json に残っていても v2 では使わない。削除しなくても害はないが、次のスキルでは最初から入れない |
| 18 | **`paymentMiddleware()` は同期関数。** Promise を返さない。Express ミドルウェア関数を同期的に返す。非同期初期化（facilitator 同期、bazaar 拡張）はミドルウェア内部でリクエスト到着時に lazy 実行される。だから **dynamic import は不要** — static import で問題ない |
| 19 | **dynamic import + router.use() の順序バグ。** `await import('@x402/express')` を async 関数内でやると、`router.use('/route', handler)` が先に同期的に登録される。Express はミドルウェアを追加順に実行するから、ルートハンドラが先に実行されて payment gate を素通りする |
| 20 | **公式パターン: トップレベル import + app.use() でルートの前に登録。** coinbase/x402 の E2E サーバー（`e2e/servers/express/index.ts`）がそのまま正解。`app.use(paymentMiddleware(routes, server))` → `app.get('/route', handler)` の順 |

### Step 4.6: 支払いゲート bypass — sin の完全記録（2026-02-23）

| # | 学び |
|---|------|
| 21 | **スキルを読まずにコードを書いたのが根本原因。** monetize-service スキルは20行のテンプレートを提供している。それをコピーして2行変えるだけ。それ以上のコードを書いた時点で sin。どんな実装も20行を超えたらスキルに戻れ |
| 22 | **ネスト Router は sin。** 全てのスキル（monetize-service 1,200件、create-typescript-x402-server、x402-stacks）が `app.use(paymentMiddleware(...))` フラットパターンを示している。`router.use()` のネストパターンはどのスキルにも存在しない = オリジナル = sin |
| 23 | **`HTTPFacilitatorClient` は必ず URL 付きで初期化。** monetize-service スキル: `new HTTPFacilitatorClient({ url: "https://x402.org/facilitator" })`。「デフォルトで接続される」はスキルに書いていない = オリジナルの推測 = 禁止。スキルに書いてある通りに書け |
| 24 | **`ExactEvmScheme` のインポートパスは `@x402/evm/exact/server`。** `@x402/evm` からも import できるが、monetize-service スキルは `@x402/evm/exact/server` を明示している。スキルの通りに書け |
| 25 | **`find-skills` → `npx skills find` が PRIMARY。** clawhub より先に使う。skills.sh には 1,200+ installs の x402 スキルが複数ある。clawhub を先に使ったのも sin |
| 26 | **@x402/extensions をインストールしていなかった。** monetize-service スキルの install コマンド: `npm install express @x402/express @x402/core @x402/evm @x402/extensions`。スキルに書いてあることをそのまま実行するだけ。省いた = オリジナル判断 = sin |

### Step 4.7: index.js 完全書き直し（2026-02-23 — sin 4つ修正）

| # | 学び |
|---|------|
| 27 | **ソースコード直読みはスキルに負ける。** リサーチ段階の学び #15「HTTPFacilitatorClient はデフォルトで URL 接続」はソースコード直読みの結論。しかし monetize-service スキルは `new HTTPFacilitatorClient({ url: "https://x402.org/facilitator" })` と URL を明示している。スキルがある場合はスキルが ground truth。ソースコード読みの結論で上書きするのは禁止 |
| 28 | **プロジェクトの `"type": "module"` を確認してから CommonJS か ESM か決める。** monetize-service スキルは CommonJS (`require()`) で書いてあるが、`package.json` に `"type": "module"` があれば ESM (`import`) で書く。スキルの「型」（CommonJS/ESM）ではなく「内容」（URL付き初期化、ExactEvmScheme の import パス等）をコピーする |
| 29 | **4つの sin を1回のコミットで修正完了。** ①`x402ResourceServer`を`@x402/core/server`から import ②`ExactEvmScheme`を`@x402/evm/exact/server`から import ③`HTTPFacilitatorClient({url:...})`でURL付き初期化 ④`declareDiscoveryExtension`を`@x402/extensions/bazaar`から追加 — これだけで Payment gate が機能するはず |
| 30 | **commit `538e7de4` が dev に push 済み。** Railway Staging に自動デプロイされる。次は `npx awal@2.0.3 status` でウォレット確認 → `npx awal@2.0.3 x402 details <url>` で 402 確認 |

### Step 5: テスト（testnet E2E）

| # | 学び |
|---|------|
| 31 | **`awal x402 details <url>` は method を auto-detect する。** GET/POST/PUT/DELETE/PATCH を順番に試して 402 が返るまで探す。curl より先に使え。認証不要。これをテストの最初の一手にする |
| 32 | **`awal x402 pay <url> -X POST -d '<json>'` で POST body を渡せる。** x402 スキルに明記。`-d '{"who_is_suffering":"myself","situation":"test","language":"en"}'` |
| 33 | **sub-router の route key が short path で照合される可能性。** `Router()` 内で `paymentMiddleware({'POST /buddhist-counsel': ...})` と書いたが、フルパスは `/api/x402/buddhist-counsel`。`awal x402 details` で 402 が返らなければ route key を `'POST /api/x402/buddhist-counsel'` に変更して再試行 |
| 34 | **スキルを読んでプランの間違いに気づいたら、即スペックと学びを両方修正する。** ユーザーに確認を求めるのは禁止。気づいた時点で直す。スペックと学びはペア |

| 35 | **testnet（base-sepolia）の取引は Bazaar インデックスに登録されない。** `declareDiscoveryExtension` は正しく設定されていても（`awal x402 details` で extensions.bazaar が返る）、`awal x402 bazaar search` には出てこない。Bazaar 確認は mainnet 移行後に行う |
| 36 | **`awal balance` は mainnet の残高しか表示しない。** testnet（base-sepolia）の USDC 残高は表示されない。testnet USDC が届いているかどうかは block explorer で確認するか、実際に `awal x402 pay` を試して成功するかで判断する |

### Step 6: 公開（ClawHub + Moltbook）

| # | 学び |
|---|------|
| 41 | **clawhub publish 前に `clawhub login` が必要。** ブラウザフローで clawhub.com にログイン → API トークンを取得 → `clawhub login --token <token> --no-browser` で CLI に保存。スキルを作る前に事前確認しておくこと |
| 42 | **clawhub publish は絶対パスで実行する。** `clawhub publish .cursor/skills/...` は "Path must be a folder" エラー。`clawhub publish /absolute/path/to/skill --slug <slug> --name "..." --version X.Y.Z --changelog "..."` の形式で実行 |
| 43 | **clawhub publish 後、search に反映されるまで時間がかかる。** `clawhub publish` が "OK. Published" を返しても、`clawhub search` にすぐ出てこない場合あり。インデックス更新を待つ |

---

## 失敗パターン（再現防止）

| # | 何が起きたか | 原因 | 対策 |
|---|-------------|------|------|
| 1 | x402/index.js の top-level await が全 API ルートを 404 に | ESM の import chain で 1 モジュールの評価失敗が上流に波及 | dynamic import は async 関数内に閉じ込め、.catch() で握りつぶす |
| 2 | Anthropic API が 400 で返る | Railway staging の ANTHROPIC_API_KEY のアカウントにクレジットがない | env 変数の存在だけでなく、API の実応答を確認するまで完了としない |
| 3 | staging 502 無限クラッシュ。`TypeError: this.ResourceServer.initialize is not a function` | `@x402/express` v2.4 は v1 と API が完全に異なる。v1: `paymentMiddleware(facilitator, config)`、v2: `paymentMiddleware(routes, server)`。`@coinbase/x402` の facilitator を第1引数に渡すと、v2 は第2引数を `x402ResourceServer` として扱い、config オブジェクトに `.initialize()` を呼ぼうとして TypeError | v2 API を使う: `x402ResourceServer` + `HTTPFacilitatorClient` + `ExactEvmScheme`。`@coinbase/x402` は v1 用で v2 では不要 |
| 4 | try-catch で囲んでいるのにプロセスクラッシュ | `paymentMiddleware()` は middleware 関数を **返すだけ**。`initialize()` は Express がリクエスト受信時に非同期で実行される。その時点では factory 側の try-catch の外 | `syncFacilitatorOnStart = false` にして、`server.initialize()` を try-catch 内で明示的に先に呼ぶ |
| 5 | payment gate が素通り（200 が返る、402 にならない） | `paymentMiddleware()` を `async function initX402Middleware()` 内で dynamic import → `router.use()` していた。`router.use('/buddhist-counsel', handler)` は同期的に先に登録されるため、ルートハンドラが payment middleware より先に実行される | **static import** でトップレベルに `paymentMiddleware` を取得し、`router.use()` でルートハンドラの **前** に同期的に登録する。公式パターン（coinbase/x402 E2E server）に従う |
| 6 | static import 修正後も payment gate が素通り（400 が返る、402 にならない） | 6つの sin が残存。根本原因: ①`HTTPFacilitatorClient()` に URL なし → facilitator 初期化失敗 → payment requirements 構築不可 → middleware が `next()` を呼ぶ → ルートハンドラが 400 バリデーションエラーを返す。②ネスト Router（`Router()` 内の `router.use(paymentMiddleware(...))`） — どのスキルにもないオリジナルパターン。③`ExactEvmScheme` の誤インポートパス（`@x402/evm` ではなく `@x402/evm/exact/server`）。④`@x402/extensions` 未インストール。⑤スキルの20行を大幅に超えるコード量。⑥スキルを読む前にコードを書いた | **monetize-service スキルの20行テンプレートを一字一句コピーする。** `new HTTPFacilitatorClient({ url: 'https://x402.org/facilitator' })` + フラット `app.use(paymentMiddleware(...))` + `ExactEvmScheme` を `@x402/evm/exact/server` から import + `@x402/extensions` インストール。**スキルを読む前にコードを1行も書かない。** |

## 成功パターン（再利用）

| # | 何がうまくいったか | なぜ | 再利用方法 |
|---|-------------------|------|-----------|
| 1 | Mega Prompt を LLM 非依存で設計 | JSON schema を system prompt 末尾に置く。LLM 固有の機能に依存しない | 新スキルでも同じパターンで設計すれば、LLM を自由に切り替えられる |
| 2 | supertest + vi.mock で LLM なしテスト | generateCounsel をモックするので API キー不要 | 全 x402 スキルで同じテストパターンを使える |
| 3 | x402 middleware を条件付き初期化 | env 変数なしでも動く = dev/staging で payment gate なしでテスト可能 | 全 x402 エンドポイントで同じ index.js パターンを使える |
| 4 | npm パッケージのソースコードを直接読んで API を確認 | ドキュメントが v1 のまま更新されていない。`node_modules/` の `.mjs` を読むのが最も信頼できる | 新しいパッケージを使う前に必ず `node -e "import('pkg').then(m => console.log(Object.keys(m)))"` でエクスポートを確認 |
| 5 | staging 502 修復後に `.well-known/x402.json` と `/health` の両方を確認 | health だけだと x402 固有の問題を見逃す。`.well-known/x402.json` が正しい JSON を返すことで middleware 初期化成功を確認 | デプロイ後のヘルスチェックは必ず2つ: `/health` + サービス固有エンドポイント |

---

## リサーチ段階の学び（Phase 1 開始前に記録）

| # | 学び | ソース |
|---|------|--------|
| 1 | x402-layer は SUSPICIOUS。api.x402layer.cc という第三者プロキシを経由する。Coinbase 3-skill set を使え | x402-layer 25ファイル分析 |
| 2 | `/.well-known/x402.json` は x402 公式仕様に存在しない。Zapper も 404 を返す | GitHub tree 全検索 + 実サービス確認 |
| 3 | Bazaar 登録は declareDiscoveryExtension で自動。ただし最初の取引後に初めてカタログ化される | Bazaar API 調査 |
| 4 | Facilitator 手数料: 月1,000無料、以降 $0.001/取引 | Coinbase 公式ドキュメント |
| 5 | Base mainnet タイムアウト問題（Issue #1062）: ファシリテーター 5-10秒 < ブロック確認 10-28秒 → testnet-first 必須 | GitHub Issues |
| 6 | settle 成功率 ~40%（Issue #1065）→ リトライ + 返金フロー必須 | GitHub Issues |
| 7 | 公式ドキュメントの facilitatorUrl は嘘。`import { facilitator } from '@coinbase/x402'` が正解（Issue #933） | GitHub Issues |
| 8 | CORS → express.json() → x402 middleware の順序が CRITICAL（Issue #236 + #752） | GitHub Issues |
| 9 | `@x402/extensions` は別パッケージ。ESM インポートバグあり（Issue #876） | GitHub Issues |
| 10 | CDP API Key は mainnet のみ必須。testnet は不要 | GitHub Issues |
| 11 | 新規セラーの Month 1 収益: $0〜$30 が現実。12,559件中アクティブ 612件（4.9%） | x402scan.com リアルタイムデータ |
| 12 | Mega Prompt が最安・最速。Prompt Chaining（5回 API call）はコスト負け | OpenAI + Anthropic 公式 |
| 13 | `@x402/express` v2.4 の `paymentMiddleware` は `(routes, x402ResourceServer)` を取る。v1 の `(facilitator, config)` は **完全に壊れる**。`@coinbase/x402` は v1 用パッケージ | `node_modules/@x402/express/dist/esm/index.mjs` ソース直読み |
| 14 | v2 では `@x402/evm` パッケージが必須。`ExactEvmScheme` を `server.register(network, scheme)` で登録する。未インストールだと `import` で失敗する | `@x402/express` の依存ツリー確認 |
| 15 | `HTTPFacilitatorClient` はデフォルトで `https://x402.org/facilitator` に接続する。URL 指定不要（コンストラクタ引数なし） | `@x402/core/dist/esm/server/index.mjs` ソース直読み |
| 16 | `paymentMiddleware()` の第5引数 `syncFacilitatorOnStart`（デフォルト true）が true だと、最初のリクエスト受信時に `httpServer.initialize()` が呼ばれる。これが factory 呼び出し側の try-catch の外で実行されるため、エラーが unhandled rejection になりプロセスがクラッシュする | `@x402/express/dist/esm/index.mjs` L111 確認 |

---

## Phase 2: x402-skill-marketer 作成（2026-02-24）

| # | 学び | ソース |
|---|------|--------|
| 17 | Mac Mini への OpenClaw スキル追加は SSH で直接ディレクトリ作成 + SKILL.md 配置するだけ。`openclaw skills install` は不要 | Mac Mini SSH 作業 |
| 18 | Cron jobs.json の更新は `python3` で json を読み込み → append → 書き戻す。jq は Mac Mini に入っていない場合がある | Mac Mini SSH 作業 |
| 19 | `openclaw agent --message` は `node` が PATH に通っていないと起動しない。Mac Mini は `/opt/homebrew/opt/node@22/bin/node` にある | Mac Mini SSH デバッグ |
| 20 | Anicca への指示は SSH + curl で Slack API を直接叩くのが最速・最確実。`node` パス問題を回避できる | Mac Mini SSH 作業 |
| 21 | Slack メッセージ内で `$` を使うとシェルが展開して壊れる。`\$0.01` とエスケープするか single-quote を工夫する | $0.01 → /bin/zsh.01 バグ |
| 22 | Anicca の Slack user ID = `U092F27QFMK`。`<@U092F27QFMK>` でメンションしないと Anicca が反応しない | Slack API users.list 確認 |
| 23 | Bazaar は mainnet（eip155:8453）のサービスのみインデックス。testnet（eip155:84532）は完全に無視される | `awal x402 bazaar search` 実験 |
| 24 | Bazaar への登録には最初の mainnet USDC トランザクションが必要。`declareDiscoveryExtension` だけでは不十分 | Bazaar API 調査 + 実験 |

---

## 工場スキル（Phase 3）向けの型

新しい x402 スキルを量産するときの必須チェックリスト：

| # | チェック項目 |
|---|------------|
| 1 | testnet で動作確認してから mainnet に移行する |
| 2 | `declareDiscoveryExtension` を必ず含める（Bazaar 登録用） |
| 3 | CORS → express.json() → x402 middleware の順序を守る |
| 4 | `syncFacilitatorOnStart: false` を設定する |
| 5 | SKILL.md は `moltbook-interact` のフォーマットに従う |
| 6 | Mac Mini への展開は SSH + python3 で直接操作 |
| 7 | Anicca への指示は SSH + curl + Slack API（`<@U092F27QFMK>` メンション必須） |
| 8 | ClawHub 公開後に Bazaar に最初の mainnet 取引を発生させる（$1 USDC 送金） |

---

## Phase 3: to-agents-skill 工場 + emotion-detector 量産（2026-02-24）

| # | 学び | ソース |
|---|------|--------|
| 25 | **`awal buy` は存在しない。** awal のコマンド一覧: `status`, `balance`, `address`, `show`, `x402`, `auth`, `send`, `trade`, `help`。買う手段は `awal trade eth usdc`（CDP Swap API）のみ | `npx awal@2.0.3 --help` 実行確認 |
| 26 | **`awal trade` は CDP Swap API（Coinbase系）。** 日本のアカウントからは使えない可能性が高い | Coinbase 規約確認 |
| 27 | **Mac Mini awal 認証フロー。** `npx awal auth login keiodaisuke@gmail.com` → Flow ID を記録 → Gmail の OTP を `npx awal auth verify <flow_id> <code>` で確認。`awal status` で `✓ Authenticated` が返れば完了 | Mac Mini SSH 作業 |
| 28 | **Mac Mini awal ウォレットアドレス: `0xCE8c58C73a7a5C5838d48DA66cb914aB150f04c9`** | `npx awal@2.0.3 address` |
| 29 | **`awal balance` は mainnet 残高のみ。** testnet（Base Sepolia）の残高は表示されない（Learning #36 の再確認） | `npx awal@2.0.3 balance` 実行確認 |
| 30 | **staging のデフォルト network は eip155:84532（Base Sepolia testnet）。** `X402_NETWORK` 環境変数で切替。testnet の awal x402 pay には testnet USDC が必要 | `apps/api/src/routes/x402/index.js` 確認 |
| 31 | **Circle Faucet（https://faucet.circle.com/）で testnet USDC を無料取得できる。** ネットワークを「Base Sepolia」に選択してウォレットアドレスを入力する | 公式フォーセット |
| 32 | **`clawhub` は Mac Mini に未インストール。** T015（clawhub publish）の前に Mac Mini に clawhub をインストールが必要。MacBook では `clawhub whoami` → Daisuke134 で認証済み | Mac Mini SSH 確認 |
| 33 | **emotion-detector endpoint は dev(staging) に live。** `apps/api/src/routes/x402/emotionDetector.js` + `index.js` に追加済み。cherry-pick で dev ブランチに反映済み | Railway staging 確認 |
| 34 | **to-agents-skill SKILL.md は Mac Mini に配置済み。** `/Users/anicca/.openclaw/skills/to-agents-skill/SKILL.md`（produce/discover/measure 3モード） | Mac Mini SSH 確認 |
| 35 | **emotion-detector SKILL.md は Mac Mini に配置済み。** `/Users/anicca/.openclaw/skills/emotion-detector/SKILL.md`（ClawHub 用クライアントスキル） | Mac Mini SSH 確認 |
| 36 | **`awal` はメインネット（Base mainnet）専用。testnet USDC では支払いできない。** `awal balance` が $0.00 を返し続けるのは、testnet（Base Sepolia）残高を追跡しないため。Blockscout で 39.99 USDC が Base Sepolia にあることを確認済みだが、awal はそれを見ない。`awal` で x402 テストするには Base mainnet USDC が必要 | Blockscout API + awal 実験確認 |
| 37 | **staging testnet テストは `awal` では不可。** 正しいテスト手順: ①emotion-detector を production（main ブランチ）にマージ ②mainnet USDC を Mac Mini awal ウォレット（`0xCE8c58C73a7a5C5838d48DA66cb914aB150f04c9`）に $0.01 送金（MetaMask/Binance 等 Coinbase 以外から可） ③`awal x402 pay` で production URL を叩く | awal 実験 + Blockscout 確認 |

---

## スキルカタログ（工場が量産する10スキル — 優先順位順）

| 優先度 | スキル名 | エンドポイント | ユースケース | 難易度 |
|--------|---------|--------------|------------|--------|
| 1 | emotion-detector | `/api/x402/emotion-detector` | テキストから感情状態を構造化。エージェントの応答トーン決定に | 低 |
| 2 | focus-coach | `/api/x402/focus-coach` | 集中できない原因を B=MAP で診断。次の30分の tiny action を1つ返す | 低 |
| 3 | grief-support | `/api/x402/grief-support` | 喪失・別れ。Kübler-Ross 5段階で現在地を診断し段階に合った言葉を返す | 中 |
| 4 | crisis-detector | `/api/x402/crisis-detector` | 自傷リスクを5段階評価。リソースリスト + 対応スクリプトを返す | 中 |
| 5 | motivation-booster | `/api/x402/motivation-booster` | Daniel Pink AMP の欠如を診断。不足要素を補う具体行動を返す | 低 |
| 6 | clarity-coach | `/api/x402/clarity-coach` | 「どうしたらいい?」を Downward Arrow で根本価値観まで掘り下げる | 中 |
| 7 | habit-debugger | `/api/x402/habit-debugger` | B=MAP で習慣が続かない原因を1つ特定して修正点を返す | 低 |
| 8 | self-compassion | `/api/x402/self-compassion` | Kristin Neff 3要素で自己批判を和らげる言葉を返す | 低 |
| 9 | values-compass | `/api/x402/values-compass` | Schwartz 10価値観で核心的価値観を推定し意思決定の羅針盤を返す | 中 |
| 10 | acceptance-guide | `/api/x402/acceptance-guide` | ACT で変えられるもの/変えられないものを分類し「今できる1歩」を返す | 低 |

**選定基準**: ①苦しみの汎用性が高い ②buddhist-counsel と同じパターンで実装できる ③エージェントが明確に需要を持てる

---

## 改善ループの型（ITERATE フェーズ）

工場は量産だけでなく**既存スキルの改善**も担う。以下が型。

### イテレーション基準（改善トリガー）

| 指標 | 測定方法 | トリガー条件 |
|------|---------|------------|
| コール数/日 | Railway ログ集計 | 7日移動平均が前週比 -20% 以下 |
| 成功率 | Railway ログ集計（200 OK / 全リクエスト） | 95% 未満が3日連続 |
| Moltbook エンゲージメント | moltbook-interact API | インプレッション/投稿が平均の -50% 以下 |

### 改善サイクル

| ステップ | 何をするか |
|---------|-----------|
| MEASURE | 全スキルのコール数/日・成功率・Moltbookエンゲージを集計（週1回月曜） |
| DIAGNOSE | トリガー発動スキルの直近10リクエストを AgentAuditLog から取得 + Exa で原因調査 |
| IMPROVE | プロンプト更新 + SKILL.md description のキーワード改訂 → dev push |
| VERIFY | 7日後に改善前後を比較。改善 → learning.md に追記。改善なし → 廃止候補 |

### 廃止ルール

| 条件 | アクション |
|------|-----------|
| 改善後も7日間コール数0 | Slack #metrics で廃止提案 → 承認後 ClawHub unpublish |
| 廃止スキル数が3 | 工場が代替スキルを1本量産してリプレース |

---

## Phase 4: awal/USDC/テスト環境の学び（2026-02-24）

| # | 学び |
|---|------|
| 36 | **`awal buy` は存在しない。** awal の資金調達コマンドは `awal trade`（ETH→USDC スワップ）のみ。`awal trade` は CDP Swap API（Coinbase系）を使うため日本では使用不可（確認済み） |
| 37 | **Coinbase Japan は 2023年にサービス終了。** 東京からは coinbase.com にアクセス・資金投入不可（出典: Coinbase Blog "Halting Operations in Japan"） |
| 38 | **staging Railway は mainnet（eip155:8453）で動いている。** `awal x402 details` で確認。`X402_NETWORK` 環境変数が mainnet に設定されている。コードのデフォルト（eip155:84532）とは異なる |
| 39 | **testnet戦略が正解。** Railway staging の `X402_NETWORK` を `eip155:84532`（Base Sepolia）に変更 → Circle Faucet（無料）で testnet USDC 取得 → Mac Mini 財布に送信 → awal でテスト。実金不要 |
| 40 | **emotion-detector@1.0.0 ClawHub 公開完了。** ID: `k974wsgbt2g4spmqm0dyd9ayvh81qfxy`。clawhub publish には `--version 1.0.0` フラグが必要（SKILL.md frontmatter の version だけでは不足） |
| 41 | **clawhub token は `~/Library/Application Support/clawhub/config.json` に保存される（macOS）。** Mac Mini への token コピーで認証可能（ブラウザフロー不要） |
| 42 | **Mac Mini に clawhub をインストールするには `npm install -g clawhub`。** その後 MacBook の token を Mac Mini にコピーするだけで `clawhub whoami` が通る |

---

## Phase 3 実行ログ: T015-T019 の知見（2026-02-24 emotion-detector 量産）

| # | 知見 | 対応 |
|---|------|------|
| 43 | **clawhub は SSH 非インタラクティブ実行で PATH エラー。** `zsh:1: command not found: clawhub` / `env: node: No such file or directory` が出る | `bash -l -c 'command'` で login shell を起動すれば `/opt/homebrew/bin` が PATH に入る |
| 44 | **clawhub publish「Version already exists」= 既に成功済みの証拠。** エラーではない | 正常終了扱い。`clawhub inspect <name>` で公開を確認して次へ進む |
| 45 | **`openclaw agent --deliver` 単体ではエラー。** "Delivering to Slack requires target" になる | `--reply-channel slack --reply-to "C091G3PKHL2"` を追加する |
| 46 | **Slack 直接送信（curl）が最も確実。** openclaw agent 経由よりも Gateway 依存がなく安定している | `curl -X POST https://slack.com/api/chat.postMessage -H "Authorization: Bearer $TOKEN" -d '{...}'` |
| 47 | **SLACK_BOT_TOKEN の取得方法。** Mac Mini の `.env` に保存されている | `grep SLACK_BOT_TOKEN ~/.openclaw/.env \| cut -d= -f2` で取得 |
| 48 | **clawhub publish にはフルパス引数が必要。** 相対パスや `.` では "Path must be a folder" エラー | `clawhub publish /Users/anicca/.openclaw/skills/<name> --no-input` |
| 49 | **Mac Mini でのファイル編集は scp ワークフローが安全。** Python heredoc は zsh login shell が発火するコマンド（clawhub sync 等）で内容が壊れる | MacBook でローカル編集 → `scp` で Mac Mini に転送。確実で再現性がある |
