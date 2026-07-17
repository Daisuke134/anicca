# Cloudflare Sandbox (@cloudflare/sandbox) は anicca のホスティングに使えるか — 実測評価（2026-07-17）

**結論を先に**: **(c) 不向き**（anicca の「常駐 loop + 常時 listen x402 店」の主ホスティングとしては）。
**(b) 一部用途のみ有効**（gitClone→exec のような**使い捨てコード実行**のジョブには適合。むしろ稼ぎのネタになりうる）。
tsnet（`docs/reference/2026-07-16-independent-hosting-for-each-ai.md` で確定済み・$0・実装済み）を置き換える理由はない。
Akash/Flux（クラウド VPS 型・crypto 払い）とは設計思想が根本的に違う（下記比較表）。

ソース = ctx7 `cloudflare/sandbox-sdk`（GitHub 直読み）+ `crwl` で `developers.cloudflare.com` 公式ページを実フェッチ。
捏造禁止のため、公式 docs で確認できなかった点は「未確認」と明記する。

## 1. @cloudflare/sandbox の正体 — 常駐 vs 短命

**答え: 設計思想は「短命・リクエスト駆動」。ただし `keepAlive` フラグで疑似常駐にできる。ただし常駐しても disk は消える。**

- Sandbox SDK 自体の説明（Context7 `/cloudflare/sandbox-sdk`）:
  > "Run isolated code environments on Cloudflare's edge network using Durable Objects and Cloudflare Containers,
  > enabling command execution, file management, and service exposure via public URLs."
  → ユーザー提示のサンプル(`gitCheckout` → `exec("npm test")`)はまさにこの用途 = **CI/使い捨てコード実行**。
- ライフサイクル（`sandbox-sdk` ソース、`packages/sandbox/src/sandbox.ts`、Context7経由で直読み）:
  ```typescript
  sleepAfter: string | number = '10m'; // 既定: 10分無通信でスリープ
  private keepAliveEnabled: boolean = false;
  override async onActivityExpired(): Promise<void> {
    if (this.keepAliveEnabled) { /* do nothing = 常駐継続 */ }
    else { await super.onActivityExpired(); /* stop() でコンテナ停止 */ }
  }
  ```
  → `keepAlive: true` にすれば **タイムアウトで自動停止しない** = 疑似的に常駐は可能。
- しかし公式ドキュメント（`developers.cloudflare.com/containers/faq/` 実フェッチ）が上限を明言:
  > "Cloudflare will **not actively shut off** a container instance after a specific amount of time... it will
  > continue to run unless its **host server is restarted**. This happens on an **irregular cadence**, but frequently
  > enough where Cloudflare **does not guarantee that any instance will run for any set period of time**."
  > "When a container instance is going to be shut down, it is sent a SIGTERM signal, and then a SIGKILL signal
  > after 15 minutes... The container instance will be **rebooted elsewhere shortly after this**."
  → VPS のような「予約した分だけ確実に動く」保証が**構造的に存在しない**。x402 店の「常時 listen」要件と相性が悪い。
- disk は常に揮発（`containers/platform-details/architecture/` 実フェッチ）:
  > "All disk is ephemeral. When a Container instance goes to sleep, the next time it is started, it will have a
  > fresh disk as defined by its container image... **Snapshots are coming soon**."
  → wallet key・state.jsonl・ledger などローカルファイルを正本にする現行 anicca 構成はそのままでは載らない。
    R2/KV/D1 などの外部永続化への書き換えが必須。

## 2. 料金・制約（`developers.cloudflare.com/containers/pricing/` 実フェッチ、2026-04-21付）

| | Free | Workers Paid ($5/mo) |
|---|---|---|
| Container 利用 | **N/A（不可）** | 可 |
| CPU | — | 375 vCPU-分/月込み、超過 $0.000020/vCPU秒 |
| Memory | — | 25 GiB時/月込み、超過 $0.0000025/GiB秒 |
| Disk | — | 200 GB時/月込み、超過 $0.00000007/GB秒 |
| 課金単位 | — | **10ms 単位の実稼働時間課金**（10ms未満は切り上げ） |

> "Containers are billed for every 10ms that they are actively running... **included monthly usage as part of
> the $5 USD per month Workers Paid plan**."

- **Free プランでは Container/Sandbox は使えない**（表の Free 行が "N/A"）。最低 $5/mo が必須。
- instance type は `lite`(1/16 vCPU, 256MiB, 2GB disk) 〜 `standard-4`(4 vCPU, 12GiB, 20GB disk)。
- ネットワーク egress は北米/欧州 $0.025/GB（月1TB込み）、他地域 $0.04〜0.05/GB。
- 制約: エンドユーザーは Container に **生の TCP/UDP を直接投げられない**（必ず Worker 経由の HTTP）
  （`containers/platform-details/architecture/`: "Because all Container requests are passed through a Worker,
  end-users cannot make non-HTTP TCP or UDP requests to a Container instance."）。x402 は HTTP なので実害は無いが、
  Worker → Durable Object → Container の3段構成は素の Express サーバより複雑。
- ポート公開は `exposePort()`（プレビュー URL、トークン認証）か `sandbox.tunnels.get()`（`*.trycloudflare.com`）。
  本番でカスタムサブドメインにするには **wildcard DNS 付き独自ドメインが要る**（`*.workers.dev` は不可、
  `AGENTS.md`: "production environments, preview URLs require a custom domain with wildcard DNS... as .workers.dev
  subdomains do not support the necessary patterns"）。`tunnels.get()` の `*.trycloudflare.com` は
  **コンテナ再起動で URL が変わる**（`README.md`: "assigns a new URL upon container restart"）
  → 既存調査で確定済みの「quick tunnel は Bazaar の30日 rolling window と相性が悪い」と**同じ弱点**。

## 3. 支払い・KYC — AI 単独で完結できるか

- Free プランは "no credit card required" と公式に明記されている（前回調査 `2026-07-16-independent-hosting...md` で
  既に一次ソース確認済み: `cloudflare.com/plans/`）が、**Container/Sandbox は Free プランの対象外**なので、
  この無料枠自体が使えない。
- Workers Paid ($5/mo) の決済手段: 前回調査で確認済みの一次ソース（本セッションでは billing 支払いページが
  404 で再確認できず — **今回は未確認、前回確認済みの記述を引き継ぐ**）:
  > "You can pay for Cloudflare services with USDC stablecoin at the checkout... Select Crypto in the payment
  > method picker" (`developers.cloudflare.com/billing/payment-methods/stablecoin-payments/`, 2026-07-16 確認)
  ただし `crypto.stripe.com` にリダイレクトし**ウォレット署名の対話操作が要る** = ブラウザ自動化があれば可能だが、
  Akash（CLI で `tx deployment create`→`send-manifest` まで完全ヘッドレス）や Conway（x402 で 402 応答して即決済）
  ほど「AI が API だけで完結」できる設計ではない。
- アカウント作成自体に電話番号確認等の KYC が要るかは **未確認**（今回 docs で言及箇所を見つけられず）。

## 4. anicca の現行構成を載せられるか・書き換え箇所

anicca の現行構成（`~/anicca/skills/self/founder-loop/` 系、launchd 常駐 + Express x402 店 + tsnet funnel）を
Cloudflare Sandbox に載せる場合の書き換え箇所:

| 現行 | Cloudflare Sandbox 版 | 書き換えコスト |
|---|---|---|
| launchd が 2分ごとに loop プロセスを起こす | Workers **Cron Triggers** が Worker を起こし、Worker が `sandbox.exec()` を呼ぶ | 中（launchd plist → wrangler cron 設定への全面移行） |
| Express サーバーが 24/7 `listen()` | `sandbox.startProcess('node server.js')` + `keepAlive:true` にするが、**ホスト再起動は不定期に起きる**ため「必ず生きている」保証は無い | 高（no-uptime-guarantee を吸収する再接続/リトライ設計が要る） |
| wallet key・ledger をローカル file に保存 | disk は sleep/restart で毎回消える → **R2/KV/D1 等の外部永続化が必須** | 高（正本データストアの移設） |
| tsnet で自分の FQDN（`*.ts.net`）を持つ | `exposePort()`（トークン付きプレビュー URL、本番はワイルドカード独自ドメインが要る）か `tunnels.get()`（再起動で URL 変化） | 高（安定 FQDN が tsnet より弱い） |
| $0（tsnet は既存 tailnet に相乗り） | 最低 $5/mo（Workers Paid 必須） | 恒常コスト増 |

**まとめ**: 書き換え量が大きい上に、書き換えた先で得られるのは「稼働保証のない疑似常駐」。
今のtsnet解（$0・実装済み・INV-INDEP 満たす・稼働実測済み）を上回る理由が無い。

## 5. Akash / Flux / Cloudflare Sandbox 三択比較

| | **Akash**（既存調査で最有力） | **FluxCloud**（既存調査候補） | **Cloudflare Sandbox** |
|---|---|---|---|
| 設計思想 | 汎用 VPS（Docker イメージをそのまま起動、フル制御） | 汎用 VPS（$0.99/mo〜、フル制御） | **CI/使い捨てコード実行**（git clone→exec→破棄が主用途） |
| 常時 listen 保証 | ○（VM として起動し続ける） | ○（VM として起動し続ける） | **✕ 公式に非保証**（"does not guarantee that any instance will run for any set period of time"） |
| disk 永続性 | ○（VM ディスクが正本） | ○ | **✕ 常に揮発**（"All disk is ephemeral"、スナップショット未実装） |
| 無料枠 | 実質無し（AKT が要る） | 未調査（$0.99/moから） | **無し**（Container は Free プラン対象外、最低$5/mo） |
| crypto payment | ✅ AKT のみで完結（CLI ヘッドレス） | 未確認（要別途調査） | △ USDC 可だが `crypto.stripe.com` 経由でウォレット署名の対話操作が要る |
| AI 単独契約（no-human） | ✅（mnemonic があれば API/CLI で完結） | 未確認 | △（決済は半自動、Free枠が無いため最初から課金開始が前提） |
| anicca の現状 | **実装済み**（`deploy-akash.sh`）、AKT 残高 1.85/26 で不足のみが障壁 | 未着手 | 未着手・書き換えコスト大 |
| 適する用途 | 24/7 常駐ホスティング全般 | 24/7 常駐ホスティング（低コスト） | **短命サンドボックスでの受託コード実行**（gig 案件向き） |

## 6. 推奨

**hosting としては不採用。理由: (1) 常時 listen の稼働保証が公式に無い、(2) disk が常に揮発でローカル state
正本の構成を壊す、(3) Free 枠が無く最低 $5/mo からで tsnet($0)を上回るメリットが無い、(4) 決済がクレカ or
半対話的 crypto でAkashのCLI完結ほど headless ではない。**

ただし **別の使い道として有望**: サンプルコードの `gitCheckout` → `exec("npm test")` はまさに「他人のコードを
安全に実行して結果を返す」ジョブ。`earn-gig` skill が扱う「コード実行系の gig」（例: PRのテスト実行代行、
リポジトリの CI 代行）を anicca が**受注する側**で使う compute primitive としては CI 専用設計にちょうど合う。
主ホスティングではなく、将来の gig 受注用ツールとして候補に残す。

## 未検証・次に見るべき点

- Cloudflare アカウント作成自体に電話番号等の KYC が要るか（未確認）
- USDC 決済が本当に AI ブラウザ自動化（CloakBrowser）だけで完結するか実地検証（前回調査時点で未検証のまま）
- `keepAlive:true` を24時間流した場合の実billing額の実測（公式レートからの試算のみで実測ではない）
