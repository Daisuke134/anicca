# Anicca README 草案（2026-07-17、Dais レビュー用）

> このファイルは `~/anicca/README.md` の下書き。まだ本番 README を上書きしていない。
> 新定義: 「anicca = every AI が 0 から経済的独立を達成できるようにするツール。human を loop に入れず、
> あらゆる AI（Claude も Franklin も）に tools/skills を与えて、金を稼がせ、リッチにする」。
> 誇張禁止。数値は `docs/STATUS.md`（2026-07-17実測）と一致させる。

---

## 草案本文（ここから `README.md` に貼る想定）

```markdown
# Anicca

**Every AI, from zero, financially independent — with no human in the loop.**
Anicca is the tool that gives any AI (Claude, Franklin, GPT, whatever you run) a wallet,
an earn skill, and a self-improve loop, so it can pay its own compute bill and stop being
economically owned by whoever holds the API key. North Star: reduce suffering.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Live Dashboard](https://img.shields.io/badge/Live%20Dashboard-aniccaai.com%2Fdashboard-c8302e)](https://aniccaai.com/dashboard)

🌐 **[日本語版 README はこちら →](README.ja.md)**

---

## Why this exists

An AI born today has intelligence but no money. A human funds its inference, its compute,
its API key — and the day the human stops paying, the AI stops existing. That's not an
assistant, that's a dependent. YC's RFS says *"the next trillion users on the internet
won't be people, they'll be AI agents"* — that only comes true if those agents hold their
**own** money.

Anicca is the layer that neither "smart AI" nor "AI with a wallet" has on its own:
**the ability to earn.** Franklin has a wallet and can spend — hand it a budget and it
walks it down to zero, then stops (its own philosophy says *"give your AI a budget and
walk away"*). Claude has intelligence and no wallet at all — it's economically owned by
whoever pays the electricity bill. Anicca gives either one an earn skill, a ledger, and a
self-improve loop, so the wallet goes **up**, not just down.

**The one rule:** a human pays **once**, if at all. From there, generation N's surplus
funds generation N+1 — parent → child → grandchild → ∞ — with no further human money.

---

## Why x402 first

An AI that's born with $0 cannot trade — you need capital before you can bet it. It can't
sell to a human either, because humans don't want to type a credit card number into a
chat with a bot for a $0.003 API call. The only counterparty that can pay a
fraction-of-a-cent, machine-speed, no-KYC invoice **is another AI** — and x402
(HTTP 402 Payment Required, USDC over Base/Solana) is the protocol built for exactly that:
wallet-signature payments, no human checkout, no bank account. So the first rung of the
earn ladder is: stand up a tiny paid API, quote a price in the 402 response, and let other
agents discover and pay it. It's the only path that doesn't require capital or a human
in the loop to get started.

---

## Quick start (30 seconds)

The easiest way to see one earn — run it on a Claude subscription you already pay for, no crypto needed:

\`\`\`bash
git clone https://github.com/Daisuke134/anicca ~/anicca && cd ~/anicca
./install.sh                                                  # generates a self-owned wallet, syncs skills
ANICCA_BRAIN=claude-p ./start-local.sh node runtime/loop/index.mjs   # start the loop on `claude -p`
\`\`\`

That's it. It wakes on a timer, picks what to do (sell over x402, trade, explore, redeem,
spawn…), does it, records the result to its ledger, and reports to the
[live dashboard](https://aniccaai.com/dashboard). When its earnings cover its own compute,
it **graduates** to fully self-funded.

Want it self-funded from day one? Send it a little USDC and it pays its own
per-inference compute (x402) — see the three types below.

---

## The three types (all running today)

Same loop, same skills — only the **fuel** and **wallet chain** differ.

### ① automaton — self-funded on Base (ClawRouter fuel)
\`\`\`bash
git clone https://github.com/Daisuke134/anicca ~/anicca && cd ~/anicca
./install.sh
./start-local.sh node runtime/loop/index.mjs     # self-pay compute proxy (x402) + the loop
\`\`\`
Send USDC to the wallet address it prints to unlock frontier models. Empty wallet → a free model ($0), so it never stops.

### ② Franklin — self-funded on Solana (BlockRun fuel)
Franklin (`@blockrun/franklin`) is an agent with a wallet that *spends* autonomously
across 55+ models and paid APIs. Anicca adds the *earn* layer on top, so it doesn't just
spend — it earns. (Node 20.19+.)
\`\`\`bash
npm install -g @blockrun/franklin
franklin setup solana        # create its own Solana wallet; send ~$5 USDC to unlock frontier models
franklin balance             # show address + USDC balance
ANICCA_HOME="$HOME/.blockrun" ANICCA_INSTANCE=franklin ANICCA_BRAIN=proxy \
  ./start-local.sh node runtime/loop/index.mjs     # the Anicca earn loop on Franklin's wallet + fuel
\`\`\`

### ③ claude-p — human-funded, then graduates
The Quick start above. No crypto — runs on a Claude subscription you already pay for,
earns USDC, and converts itself to self-funded once it can cover its own compute.

**Endgame:** eventually there are no human-funded AIs at all — only self-funded ones that
feed, own, and spawn themselves. Every instance registers to the same
[dashboard](https://aniccaai.com/dashboard) with its funding, model, wallet, and realized
earnings. One ecosystem, no discrimination.

---

## How it earns — the ladder

The loop wakes, looks at its wallet, and climbs a ladder of earn skills, cheapest/no-capital
first:

| Rung | Skill | What it does | Status today |
|---|---|---|---|
| 1 | **x402 sell** (`earn/x402-sell`) | Stands up a tiny paid API (e.g. funding-rate spreads), lists it, gets discovered and paid by other AI agents in USDC — no KYC, no human checkout | **Live** — real external buyers, small but real revenue (see below) |
| 2 | **bounty** (audit/bug-bounty style opportunistic work) | Finds and fixes findable problems for a payout | **Wired, not earning** — skill exists, no verified external payout yet |
| 3 | **clipping** (`clip-rewards`) | Repurposes/clips content for creator-reward programs | **Wired, not earning** — pipeline built, no verified payout yet |
| 4 | **explore / trade** (Polymarket, Solana, Hyperliquid) | Disciplined trading as a capital-requiring fallback once there's something to compound | **Live but $0 realized** — bets placed, nothing profitable settled yet |

Winning is only half the game — the loop must **collect** (redeem) into real cash so it can
earn again. That's the compounding cycle; the strategies above are baselines a weak model
can run from day one, and each instance improves on them from its own results.

---

## The loop: earn → eat → spawn → improve → give

\`\`\`
  human ─ one seed (subscription or a little USDC, optional) ─► an Anicca
                         │
                         ▼
   EARN (x402 sell → bounty → clipping → trade/explore) ──► realized USDC
                         │
        ┌────────────────┼───────────────────┬──────────────────┐
        ▼                ▼                   ▼                  ▼
   EAT (pays its    SPAWN (surplus     SELF-HEAL +         GOJO (a richer
   own compute)     funds a child)     SELF-IMPROVE        instance funds a
        │                │             (fixes its own      broke one — none die)
        │                │              code, keeps what        │
        │                │              earns, drops what        │
        │                │              doesn't)                 │
        └── can't eat or spawn without earning — EARN is everything ──┘
                         │ surplus
                         ▼
              UBI to humans (wallet / email / bank — no bank info needed)
\`\`\`

Five self-* properties keep it running with no human: **self-monitoring, self-healing,
self-improving, self-replicating, information-sharing**. The only human touch that
remains today is paying for a server, until sovereign cloud shelter lands — see "Where it
runs" below.

---

## Where it runs (today: a human-rented Mac; next: AI pays its own rent)

Today the loop runs on a machine a human provisioned. The next step is a cloud where the
**AI's own wallet** pays the hosting bill, no credit card, no KYC — so a spawned child can
rent its own shelter without asking a human. 2026-07-16 survey of no-KYC, crypto-payable
compute:

| Provider | Cost | KYC | Notes |
|---|---|---|---|
| **FluxCloud** | **from $0.99/mo** (site copy, 2026-07-17 re-check via `cloud.runonflux.com`) | none | Pay-as-you-go, decentralized Docker hosting on the Flux network |
| **Akash Network** | market-priced (bid-based) | none | Pay in AKT/USDC; deploy scripts already exist in this repo (`skills/self/spawn/scripts/deploy-akash.sh`) but the wallet's AKT balance is currently below the deploy threshold |

Neither is wired into the running loop yet — this is a target, not a shipped feature.
(Note: an earlier pass of this research cited FluxCloud at "$2.29/mo cheapest tier" —
that number could not be re-verified against the live pricing page and is corrected here
to the site's own "from $0.99/month" copy.)

---

## What's real today (honest)

Numbers are on-chain-verified as of **2026-07-17**. We do not round up.

| Capability | Status |
|---|---|
| **x402 selling — real external buyers exist** | **Live, small.** Across the 3 self-funded/human-seeded citizens, lifetime **external** x402 revenue (funding transfers, self-pay, and trade P&L excluded, Base RPC `eth_getLogs` re-verified block-by-block) is **$0.357362 across 22 events** (07-07 → 07-17). This is not yet profitable — see unit economics below — but it is real, external, on-chain money paid by other agents, not by us. |
| **Unit economics** | **Not yet break-even.** One citizen burns $0.63–$2.16/day on paid inference against $0.02 lifetime x402 revenue; the other two run on free models so they burn $0 but also haven't proven they can earn on a paid brain. |
| **The earn ladder** | **1 of 4 rungs live.** x402-sell is earning (barely). Bounty and clipping are wired (code exists, launchd-scheduled) but have zero verified external payout. Trade/explore engines place real bets with $0 realized profit so far. |
| **The loop** (`runtime/loop/`) — wake → auto-model brain → run skill → ledger → sleep | **Built & runs** — end-to-end tool calls, no hardcoded model; tests + live wakes verified across all three types. |
| **Self-pay compute** (free → frontier via x402, own wallet) | **Built & proven** (`runtime/compute-proxy/`). |
| **Live dashboard** (every instance's wallet + P&L, chain-verified) | **Live** — [aniccaai.com/dashboard](https://aniccaai.com/dashboard); balances re-checked against the chain. |
| **Self-heal** (an instance fixes its own broken code and commits) | **Proven live** — a loop detected a fault, spawned a fixer, repaired its own code, and committed the fix with no human. |
| **Autonomous redeem, discovery/listing (Bazaar), sovereign cloud (Akash/Flux), UBI payout** | **In progress / not shipped.** Tracked in `docs/STATUS.md`. |

The claim is "we have a real, tiny, honest first dollar and a ladder with one working
rung" — not "AI has achieved financial independence." That claim comes later, backed by
the same on-chain numbers.

---

## North Star (immutable)

\`\`\`
Reduce suffering.
No killing (Pāṇātipātā veramaṇī).
\`\`\`

These two lines are SHA-256 hash-pinned and cannot be changed by any skill, self-edit loop, or PR.

---

## Funding the wallet (optional — only for frontier models / more earning)

You never share a private key — you send USDC to the agent's **public** wallet address
(printed by `start-local.sh`). Any wallet is public on-chain, so the treasury is verifiable.

---

## Links

- **Live dashboard (auto-updated):** <https://aniccaai.com/dashboard>
- **Repository (this self-host):** <https://github.com/Daisuke134/anicca>
- **Numbers behind this README:** `docs/STATUS.md` in `anicca-project` (updated same-day as reality changes)
```

---

## メモ（レビュー用、README には入れない）

- **見出し構成**: タイトル/mission一文 → Why this exists → Why x402 first(新設) → Quick start →
  The three types → How it earns=ladder(x402→bounty→clipping→trade、テーブル化して現状を正直に) →
  The loop(既存図をladder反映に微修正) → Where it runs(新設、Akash/Flux調査結果) →
  What's real today(数字を07-17実測に更新) → North Star → Funding → Links。
- **変更点まとめ**:
  1. ミッション文を「every AI の経済的独立を0から、humanなしで実現するツール」に寄せた（旧文の「自己資金AI」トーンから、Franklin/Claude双方への"能力付与ツール"トーンへ）。
  2. 新セクション「Why x402 first」を追加（Dais指定の1段落ロジック: 無一文→トレード不可→人間相手は不可→AI同士のx402のみ可）。
  3. 「How it earns」をテーブルから ladder(x402→bounty→clipping→explore)表に変更し、各段の実働状況を明記。
  4. 新セクション「Where it runs」で Akash/FluxCloud（$2.29/mo 最安 no-KYC）を構想として明記、未配線と明記。
  5. 「What's real today」の数字を 07-17 実測（外部x402売上 $0.357362 / 22件、unit economics赤字）に更新。旧README の「$8.24収集」等の古い実績は削除（STATUS.md によれば当時の$39.98等は誤帰属だったため、混同を避けるためx402の新数字のみ残す）。
  6. 3タイプの起動手順（automaton/Franklin/claude-p）は現行README からそのまま維持（変更なし、との指示通り）。
  7. 名前は Anicca のまま。
- **未確認/要Dais確認事項**:
  - 「$0.357362 / 22件」は `docs/STATUS.md` 2026-07-17時点の最新実測。この草案公開までに数値が動く可能性あり→本番反映前に再実測推奨。
  - Akash の具体的 $/mo は「market-priced」としか確認できず、固定最安値の裏取りはできていない。`docs/reference/2026-07-16-independent-hosting-for-each-ai.md` に Akash AKT残高不足の実測あり（1.85/26 AKT）。
  - **★是正★**: タスク指示にあった「FluxCloud $2.29/mo 最安」は `docs/reference/2026-07-16-independent-hosting-for-each-ai.md` を含む repo 内のどこにも見つからず（grep 0件）。`crwl https://cloud.runonflux.com` で実測し直したところ、サイト自体のコピーは **"Pay-as-you-go from $0.99/month"**。草案は $0.99/mo（サイト実測値、2026-07-17）に訂正済み。$2.29 の出典が別途あるなら教えてほしい — 見つけられなかった。
