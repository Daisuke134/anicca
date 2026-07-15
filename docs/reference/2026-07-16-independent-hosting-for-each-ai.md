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

## 未解決（次にやること）

1. **★Tailscale を1台で複数ノードとして動かせるか★** — `tailscaled` を `--state`/`--socket`/`--tun=userspace-networking`
   で複数起動すれば、1台の Mac に4つの独立した FQDN（各々が自分の443）が立つのでは。これが可能なら3ポート制限は
   **問題ごと消える**。各体が自分のノード = 完全独立。調査中
2. セルフホスト tunnel OSS（frp / sish / bore / rathole / chisel / localtunnel）の比較。1 server で N サブドメインが
   取れるか、VPS が要るか
3. cloudflared **named** tunnel（quick でない）: 1つの config.yml で複数 ingress → 各サブドメイン → 各ローカルポート。
   固定 URL になるがドメインが要る
4. Caddy + `tailscale/caddy-tailscale` を 443 の後ろに置く案
5. Akash に AKT を足して既存 deploy script を転用する案（誰の金で足すか = INV-INDEP の判断が要る）

## 教訓（この調査自体から）

- **Conway が down** = 単一サービスへの依存はそれ自体がリスク。「AI が自分で払える」唯一解に見えても、
  落ちたら終わり。複数の道を持つこと
- **調査を chat に書いて満足しかけた**（Dais の指摘で是正）。研究したら即 MD 化しないと、次のセッションは
  ゼロから同じ検索を繰り返す。この文書がその防波堤
