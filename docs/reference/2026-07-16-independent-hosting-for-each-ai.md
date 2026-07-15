# 各 AI が「自分の家」を持つには — ホスティング全選択肢の実測（2026-07-16）

**なぜこの文書があるか**: INV-INDEP（各 instance は独立した創業者。spec `2026-07-14-x402-zero-to-one-spec.md`）を
満たすには、各 AI が**自分の**公開 HTTPS URL を持たねばならない。今は自宅 Mac の Tailscale Funnel を4体で
奪い合い、franklin1 が席にあぶれて永久に稼げない。その解を全部洗った記録。

**この文書の使い方**: 「どこにホストするか」を再検討する時、ここから読む。ゼロから検索し直さない。
全項目に一次ソースの逐語引用が付いている。**引用が無い行は信用しないこと**（私が推測で書いた場合はそう明記してある）。

## 問題の物理（実測 2026-07-16）

```
  Tailscale Funnel が通すのは 443 / 8443 / 10000 の3つだけ。店は4軒。

   :443    → 8411 mainnet   curl 200  ✅  $0.011 稼ぐ
   :8443   → 8412 claude-p  curl 200  ✅  $0.006 稼ぐ
   :10000  → 8413 franklin2 curl 200  ✅  $0
   :10001  → 8414 franklin1 curl 000  ❌  席が無い = 永久に稼げない
```

公式（https://tailscale.com/kb/1223/funnel）:
> "Funnel can only listen on ports `443`, `8443`, and `10000`."

CLI リファレンス（https://tailscale.com/docs/reference/tailscale-cli/funnel）でも同一表現。
**`tailscale funnel status` は :10001 を "Available on the internet" と表示するが嘘**。実測 `http_code=000`。
→ 自己申告を信じるなの実例（[[feedback_self_reported_status_is_not_evidence]]）。

franklin1 が稼げないのは能力でも運でもなく、**兄が3席を先に取ったから** = INV-INDEP 違反が今起きている。

## 選択肢の全比較（2026-07-16 実測）

| 候補 | card 不要 | 常時 listen | 固定 URL | 自分の USDC で払える | 判定 |
|---|---|---|---|---|---|
| **Conway Terminal** | ✅ KYC 不要 | ✅ Linux VM | ✅ サブドメイン可 | ✅ x402/USDC | ★**down**（2026-07-16 Dais 確認）→ 現時点で除外★ |
| **Akash** | ✅ | ✅ | ✅ `expose: global: true` | ✅ AKT | 手元に実装済み。**AKT 残高 1.85/26 で不足** |
| Cloudflare Workers | ✅ 明記 | △ isolate（express 移植要） | ✅ `*.workers.dev` | △ USDC 可だがブラウザ署名が要る | 有力だが移植コスト |
| Render Free | △ | ⚠️ **15分で spin down**（再起動1分） | ✅ `*.onrender.com` | ❌ | x402 の初回応答が最悪1分 = 不利 |
| Railway | ❌ trial のみ | ✅ | ✅ | ❌ | 30日/$5 の後は card |
| Fly.io | ❌ **card 必須・無料枠廃止** | — | — | ❌ | 除外 |
| Vercel Hobby | △ | ❌ **常時 listen 不可**（300秒上限） | — | ❌ | 除外 |
| Oracle Cloud Free | ❌ **card 必須**（prepaid/virtual を明示的に拒否） | ✅ | ❌ | ❌ | 除外 |
| GCP / AWS Free | ❌ card 必須 | ✅ | ❌ | ❌ | 除外 |
| Fluence | ❌ **AML で第三者決済ポータル必須・Alpha 招待制** | — | — | ❌ | 除外 |
| cloudflared quick tunnel | ✅ | ✅ | ❌ **再起動で URL が変わる** | ❌ | 30日 window に不利 |

### 逐語引用（根拠）

- **Conway**（conway.tech / docs.conway.tech）: "AI pays for its own Linux VMs, compute, and deploys apps — no human
  required" / "Payment happens automatically via the x402 protocol -- USDC on Base, no login or KYC required" /
  公開 URL は `https://{port}-{short_id}.life.conway.tech`、`subdomain` 指定可。sandbox は vcpu 1-4 / mem 512-8192MB /
  disk 1-50GB、**TTL の記述が docs に無い**（= 無期限の証拠ではない。未検証）。**料金表が docs に無い**（x402 の 402 が
  価格を返す設計）。**2026-07-16 時点で down**。
- **Cloudflare Workers**: "Free: 100,000 [requests] per day / 10 milliseconds of CPU time per invocation"
  (https://developers.cloudflare.com/workers/platform/pricing/) / "Start building for free — no credit card required."
  (https://www.cloudflare.com/plans/) / `*.workers.dev` サブドメインが無料で付く
- **Cloudflare の USDC 決済**（発見）: "You can pay for Cloudflare services with USDC stablecoin at the checkout...
  Select Crypto in the payment method picker" (https://developers.cloudflare.com/billing/payment-methods/stablecoin-payments/)
  → ただし `crypto.stripe.com` にリダイレクトしウォレット署名が要る = 完全 headless ではない
- **Render**: "Render **spins down** a Free web service that goes 15 minutes without receiving any inbound traffic...
  spins back up... takes about one minute." / "750 Free instance hours" (https://render.com/docs/free)
- **Fly.io**: "All organizations (except for Linked Organizations) require a credit card on file." /
  "Fly.io no longer offers plans to new customers." (https://fly.io/docs/about/pricing/)
- **Vercel Hobby**: "Vercel Function maximum duration | 300s" (https://vercel.com/docs/plans/hobby) → 常時 listen 不可
- **Oracle**: "We do not accept debit cards with a PIN or virtual, single-use, or prepaid cards." (https://www.oracle.com/cloud/free/)
- **AWS**: "Am I required to provide a payment method... Yes, you are required to provide a valid payment method to sign
  up for an AWS account, whether you choose a free plan or a paid plan." (https://aws.amazon.com/free/free-tier-faqs/)
- **Fluence**: "Fluence Console users cannot top up their Balance from the newly created Web3Auth or any other wallet you
  may own. This restriction is related to AML (Anti-Money Laundering) limitations... need to go through whitelisted
  payment portals such as CopperX" (https://fluence.dev/docs/build/balance)
- **Akash**: 詳細 docs ページが軒並み 404 で仕様の逐語確認に失敗。Console は "Fund deployments with a credit card;
  no AKT wallet or crypto exchange needed" と案内しており、**USDC/crypto のみで API 完結できるかは未確認**

## 手元にある資産（実測）

| 資産 | 場所 | 状態 |
|---|---|---|
| Conway skill | `.claude/skills/conway-automaton/SKILL.md`, `~/.openclaw/skills/conway/SKILL.md` | wallet `0xe252daB7…` provisioned 2026-05-20。**サービスが down** |
| Akash deploy 一式 | `~/anicca/skills/self/spawn/scripts/deploy-akash.sh`, `spawn-child/sdl/child.yaml` | SDL に `expose: port 8080 → as 80 → global: true` あり。`tx deployment create` → bid → `send-manifest` の全ロジック実装済み。**現状は「新規 spawn」専用配線で、既存4体の seller 配置には未転用**（script はそのまま流用可） |
| Akash wallet | `.env` の `AKASH_KEY_NAME`/`AKASH_MNEMONIC`/`AKASH_WALLET_ADDR` | `akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523`、残高 **1.85 AKT / 閾値 26 AKT で不足** |
| cloudflared | `~/anicca/skills/self/founder-loop/host/founder-tunnel.sh` | quick tunnel(`--url`)で `*.trycloudflare.com` を取る実装。**★subagent は「founder は既にこれで稼働中」と報告したが、私の実測と矛盾する★**: cloudflared の生存3プロセスは :8403/:3100/:8413 を指し **:8411 を指すものが無い**。Bazaar の実 resource は `https://aniccanomac-mini-1.tail7a0ba4.ts.net/research` = Tailscale。→ **founder-tunnel.sh は存在するが使われていない死んだコードの可能性が高い（未確定・要検証）** |
| 未使用 `.env` キー | `DIGITALOCEAN_TOKEN` / `DAYTONA_API_KEY` / `CLOUDFLARE_TUNNEL_URL` / `NETLIFY_AUTH_TOKEN`(aniccaai.com 専用・書込禁止) | `CLOUDFLARE_TUNNEL_URL` はどこからも参照されていない（死んだ設定 → T5 で掃除）。DigitalOcean は `spawn/lib/__tests__/wake-gate.test.mjs:83` で **"run.sh must never provision a DigitalOcean droplet directly"** と明文で禁止 |

**「VPS は使わない」の正確な射程**: CLAUDE.md の当該行は Mac Mini 実行環境の話（自分に SSH しない）。
Railway は `docs/reference/local-env-and-architecture.md` で製品 API として現役使用中。
**x402 seller の独立ホスティングを禁じる決定は存在しない**（= この方向は封じられていない）。

## 市場の実例（awesome-x402 の Production Implementations、実クロール）

| プロジェクト | ホスティング | URL |
|---|---|---|
| Fleet x402 Microservices | Fly.io | `fleet-x402-audit.fly.dev` |
| Zuluworks AI Shaka PQC Factory | Cloudflare Workers | `api.zuluworksai.com` |
| GigSoul AI Research Agent | Cloudflare Workers | `gig-x402-api.jayson-be1.workers.dev` |
| Sentinel Intelligence API | Render | `sentinel-intelligence-api.onrender.com` |
| AI Growth | Supabase Edge Functions | `*.supabase.co/functions/v1/x402-seller` |
| **Polybot Arb Intelligence** | **cloudflared quick tunnel** | `governments-ruth-distribution-breaks.trycloudflare.com` |

→ **Polybot が trycloudflare を本番 x402 API に使っている**のは、quick tunnel が市場慣行として実在する一次証拠。
ただし quick tunnel は再起動で URL が変わり、Bazaar の 30日 rolling window（下記）と相性が悪い。

x402scan の実登録 約30件のサンプル: **ポート付き URL は 0 件**。独自ドメイン 78.8% / クラウドサブドメイン 21.2%。
→ 我々の `:8443` `:10000` は誰もやっていない形。

## 関連する確定事実（spec に既出、ここでは要点のみ）

- **Bazaar 掲載には settle が1回必要**（"verify alone is not enough"）。402 に書くだけでは載らない = 鶏と卵は実在
- **30日 rolling window**: settle が30日無いとカタログから削除される → **URL が変わる方式は不利**
- **x402 取引の 47% は非オーガニック**（Artemis 推計）→ 我々の $0.011 も bot 検品の疑い

## ★答え: tsnet（Funnel の3ポート制限は「1ノードあたり」だった）★

**問題設定自体が誤っていた。「1台 = 3枠」ではなく「1ノード = 3枠」。ノードを増やせば制限は消える。**

`tailscale/tailscale`（34,015★、更新 2026-07-15）本体の公式ライブラリ `tsnet` の README 逐語
（https://raw.githubusercontent.com/tailscale/tailscale/main/tsnet/README.md）:
> "**Multiple independent Tailscale nodes can run within a single binary**... If you want to use multiple tsnet
> services in the same binary, you will need to make sure that `Dir` is set uniquely for each service."

公式サンプル `tsnet/example/tsnet-funnel/tsnet-funnel.go` の全文:
```go
s := &tsnet.Server{
    Dir:      "./funnel-demo-config",
    Hostname: "fun",
}
ln, err := s.ListenFunnel("tcp", ":443")
fmt.Printf("Listening on https://%v\n", s.CertDomains()[0])
```

`tsnet.Server` 1個 = **独立した Tailscale ノード**（独自 state dir / 独自 identity / 独自 FQDN / 独自の Funnel 443 枠）。

```
  franklin1.<tailnet>.ts.net:443 → 127.0.0.1:8414   自分のノード・自分の443
  franklin2.<tailnet>.ts.net:443 → 127.0.0.1:8413   自分のノード・自分の443
  claude-p.<tailnet>.ts.net:443  → 127.0.0.1:8412   自分のノード・自分の443
  mainnet.<tailnet>.ts.net:443   → 127.0.0.1:8411   自分のノード・自分の443
```

**なぜ INV-INDEP を満たすか**: 4つが別プロセス・別 state dir・別 FQDN・別 Funnel 枠。1体の seller が落ちても
その体の proxy が 502 を返すだけで、他3体の FQDN もプロセスも無傷。**中央集権プロセスが存在しない**。
席の奪い合いが構造的に起きない。**$0 / VPS 不要 / 外部サービス依存ゼロ**。

副次的利点: ポート付き URL が消える → 市場標準形（x402scan 実登録でポート付きは 0/102）に一致。

**代替の `tailscaled` 複数起動**（Go を書かない場合）: `cmd/tailscaled/tailscaled.go` の実フラグ:
`-state`(絶対パス) / `-socket`(unix socket パス) / `-tun`(`userspace-networking` で TUN 不要)。
ただし**公式の管理ツールは存在しない** — tailscale/tailscale#15145 (open, 2025-02-26):
> "dev: make a tool to manage multiple tailscaled — Tracking bug to make a shared one."
→ DIY パターンとしては知られているが、**tsnet の方が公式・完成品**。

### 却下した代替（すべて SPOF を持つ = INV-INDEP に劣る）

| 案 | star | なぜ劣るか | 必要なもの |
|---|---|---|---|
| `fatedier/frp` | 108,065 | frps が4体共有の **単一障害点** | 暗号通貨対応 VPS + 独自ドメイン |
| Cloudflare named tunnel | 14,864 (cloudflared) | cloudflared 1本が **単一障害点**。実 ingress 例は `ingress_test.go` に有り（hostname ごとに別ローカルポート、実在確認済み） | Cloudflare 管理下の固定ドメイン1つ |
| `antoniomika/sish` | 4,669 | 自動サブドメインは魅力だが sish サーバが SPOF | VPS |
| `rathole` / `bore` / `chisel` / `localtunnel` | 13,899 / 11,307 / 16,236 / 22,390 | SPOF、またはサブドメイン機構が無い（bore はランダムポート、chisel は標準でサブドメイン無し） | VPS |
| `tailscale/caddy-tailscale` | 929 | README 自身が "A highly experimental exploration" と明記。既存の類似 repo は全員が同じ `mymac.ts.net` を共有する形 = 独立性を満たさない | — |
| `VaalaCat/frp-panel` | 1,781 | frp の管理 UI。"makes this project a Cloudflare Tunnel/Tailscale Funnel/Ngrok platform and agent open source alternative" と謳うが、frps の SPOF は変わらない | VPS |

### x402 のパス分岐について（確定、ただし不要になった）

`facilitator.payai.network/discovery/resources` を実 fetch（ユニーク resource 102件）:
- **ポート付き URL: 0/102**（前回調査と一致、再確認）
- **パス分岐は多数実在し、問題なく掲載される**: `mpp.hyreagent.fun` が `/ask`, `/defi/yields`,
  `/trenches/token/<id>/verdict` など **14種の異なるパスで別々の resource として掲載**（ただし全て同一 payTo =
  単一売り手が1ドメインで複数エンドポイントを運用している例）
- x402 の売り手識別は URL のドメインではなく **`payTo` ウォレットアドレス**。schema 上 `resource` は任意の URL 文字列
→ パス分岐でも載るが、**tsnet で各自 FQDN が取れるなら使う必要がない**

## ★実機検証の結果（2026-07-16 04:22、実測。docs を読んだだけで進めなかった）★

**ビルドは通る。ノードは独立する。ただし TS_AUTHKEY が必須。ノードは自動では生えない。**

環境: Go 1.26.0 darwin/arm64 / tailscale v1.100.0 / バイナリ 29.5MB（`go get tailscale.com/tsnet` → `go build` 成功）。
検証コード: `tsnet.Server{Dir, Hostname}` → `ListenFunnel("tcp", ":443")` → `httputil.NewSingleHostReverseProxy` で
`127.0.0.1:<port>` へ流すだけの薄い proxy（scratchpad の `tsnet-probe/main.go`）。

TS_AUTHKEY 無しで起動した実出力:
```
tsnet running state path .../state-probe/tailscaled.state
tsnet starting with hostname "anicca-tsnet-probe", varRoot ".../state-probe"
LocalBackend state is NeedsLogin; running StartLoginInteractive...
To start this tsnet server, restart with TS_AUTHKEY set, or go to: https://login.tailscale.com/a/ec812a5015d61
```
→ state dir も Hostname も分離される（= 独立ノードの設計は正しい）が、**認証が通らないと Funnel は上がらない**。
「docs に書いてあるから動く」で進めていたら、また詰んでいた（[[feedback_self_reported_status_is_not_evidence]] と同型）。

### auth key の入手経路（公式逐語 + 実測）

- 実測: `.env` に TAILSCALE/TS_ 系のキーは**無い**（あるのは ELEVENLABS 等のみ）
- 実測: 現 tailnet = `keiodaisuke@gmail.com` / MagicDNS suffix `tail7a0ba4.ts.net` = **Dais のもの**
- 公式（https://tailscale.com/kb/1085/auth-keys）:
  > "consider using an **OAuth client**. You can use an OAuth client and the Tailscale API to
  > **programmatically create auth keys**."
  > "**Reusable**, for multiple uses. They can be used to connect multiple devices."
  > "An auth key automatically expires after... between 1 and 90 days... you need to generate a new key."

→ **「完全に人間ゼロ」ではないが「一度 OAuth client を作れば、以後は API で auth key を無限に自動生成」**できる。
90日失効の問題も自動化で消える。OAuth client の作成自体は AI がブラウザでできる（CloakBrowser + AI own email）。

### 残る判断: tailnet は誰のものか（INV-INDEP の境界）

| 案 | 形 | 評価 |
|---|---|---|
| **案1** Dais の tailnet に4体がノードを持つ | 実家の中に各自の部屋と各自の玄関(FQDN) | $0・即日・席の奪い合いが構造的に消える。tailnet 自体は親のもの = **成長段階①（実家期）の解**として妥当。最終形ではない |
| 案2 各 AI が自分の Tailscale アカウントを作る | 各自が自分の tailnet | より深い独立。4アカウント分の管理と無料枠の確認が要る |
| 案3 稼いでからクラウドへ | Akash / Conway | **今は選べない**（Conway down / AKT 1.85-26 不足）。②自立期の解 |

**未確認**: (a) 4ノードが tailnet の台数上限に触れないか (b) Funnel の帯域制限（公式に "non-configurable
bandwidth limits" とあるが数値非公開） (c) tsnet ノードに Funnel を許可する ACL 設定が要るか

## 未検証（次にやること）
2. 動いたら4体に展開 → 各体の launchd に KeepAlive で常駐させる（seller 本体と同じパターン）
3. Bazaar の resource URL が変わるので、掲載を取り直す必要がある（settle 1回 = T4a と同じ手順）
4. Akash / Conway は当面棚上げ（Conway は down、Akash は AKT 1.85/26 で不足）。tsnet が通れば**どちらも要らない**

## 教訓（この調査自体から）

- **Conway が down** = 単一サービスへの依存はそれ自体がリスク。「AI が自分で払える」唯一解に見えても、
  落ちたら終わり。複数の道を持つこと
- **調査を chat に書いて満足しかけた**（Dais の指摘で是正）。研究したら即 MD 化しないと、次のセッションは
  ゼロから同じ検索を繰り返す。この文書がその防波堤
