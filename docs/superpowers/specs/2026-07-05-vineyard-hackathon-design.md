# Vineyard — AI financial-independence CLI, hackathon build

**Hackathon**: YC RFS #3 "Software for Agents" (Aaron Epstein). **Status**: brainstorm → design, iterating
with Dais across voice-dictated turns (2026-07-04/05). Supersedes the build-target scope of
`docs/hackathon/franklin-earn-product-spec.md` (kept as the engine-derivation source of truth — file
paths there are verified to exist in `~/anicca/skills/earn/`). Does NOT replace the hackathon
*submission-text* docs (`Predikt-Software-for-Agents-Submission.en.md`,
`software-for-agents-submission.md`, `2026-07-05-anicca-compiled-submission.md`) — those need a follow-up
copy pass once this spec is final (tracked as TODO item K below), not a blocker for the build.

## 0. Naming — LOCKED 2026-07-05

- **Product / repo name: `Vineyard`. CLI binary: `vineyard`** (e.g. `npx vineyard spawn`). Dais verbatim:
  *"vineyard — this is the name of the product... of the repository."* No longer provisional.
- **Why not "Franklin"**: Dais verbatim (2026-07-05 voice): *"we shouldn't actually mention the name of
  Franklin or everything because it's just about AI as a whole... AI achieving self-fund... financial
  independence."* The product reads as "AI-in-general achieves financial independence," not one named
  persona. "Franklin" stays as the internal name of an already-existing self-funded AI instance in the
  Anicca colony (`docs/WALLETS.md`, wallet `8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9`) — it is not this
  product's brand.
- `selffund` (the interim working codename used in the first draft of this spec) is retired — replaced
  everywhere by `Vineyard`/`vineyard`.

## 1. What it is

A **new, self-contained OSS repo** (not the anicca monorepo) called **Vineyard**. `git clone` + one command
→ spawn a self-funded AI: it owns its own wallet and earns its own money across **4 on-chain engines**
(Polymarket / yield / Hyperliquid / Solana), with **no human and no Claude in the loop** after a one-time
seed. Dais verbatim (2026-07-05, JP): *"機械可読インターフェースを中心に設計された、エージェントファースト
なソフトウェア"* ("software designed around a machine-readable interface at its core, agent-first") —
and: *"any agent can download this with ease."* Ease-of-onboarding for an agent is a first-class success
criterion, not an afterthought.

Interface = **CLI + REST API + llms.txt** (machine-readable — another AI can spawn/run/monitor instances
programmatically) **+ a polished Web App UI** (see §6). **NO MCP** — Dais verbatim: *"No it is because
it's made for agents"* — CLI + REST API + llms.txt already give an agent a machine-readable path; an MCP
server is an unnecessary extra layer. Ships its own dashboard, derives (copies + repackages) the proven
anicca engines — does not depend on anicca at runtime. Dais verbatim: *"we can drive everything from kind
of the [stuff] that we made with Anicca"* — Vineyard is a clean re-packaging of already-working anicca
engines, not new trading research.

Scope confirmed 2026-07-05 (Dais verbatim): *"we're not just gonna do polymarket stuff... we're gonna do
everything"* — all 4 engines ship, not a Polymarket-only product (that was the earlier, narrower "Predikt"
submission framing — now superseded).

## 2. Architecture

```
                              ┌─────────────────────────────┐
   human ── one-time crypto seed ──▶│  only human touch-point   │
                              └───────────────┬───────────────┘
                                              │ (human-zero from here on)
                                              ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │                              V I N E Y A R D                          │
   │     "AI achieves financial independence" — agent-first,              │
   │     machine-readable-interface-centered OSS repo                     │
   │     (separate from the anicca monorepo; any agent downloads w/ ease) │
   └───────────────────────────────┬──────────────────────────────────────┘
                                   │
        ┌──────────────┬──────────┼──────────┬───────────────────┐
        ▼              ▼          ▼          ▼                   ▼
   ┌─────────┐   ┌───────────┐ ┌────────┐ ┌───────────────────────────┐
   │  CLI    │   │ REST API  │ │llms.txt│ │  Web App UI                │
   │`vineyard│   │POST/GET,  │ │machine-│ │  built w/ gpt-tasteskill    │
   │ spawn/  │   │same verbs │ │readable│ │  (HARD RULE 0.38): spawn    │
   │ run/    │   │as CLI     │ │index   │ │  button, live wallet ×      │
   │ status` │   │           │ │        │ │  engine × realized P&L,     │
   └────┬────┘   └─────┬─────┘ └───┬────┘ │  on-chain links, "super easy"│
        │              │           │      └─────────────┬─────────────┘
        └──────┬───────┴───────────┘                    │ same underlying API
               ▼                                        │
   ┌───────────────────────────────────────────┐         │
   │  CORE                                      │◀────────┘
   │  wallet.mjs  = per-instance key isolation   │
   │                (resolver fail-closed on     │
   │                 foreign-agent key requests) │
   │  loop.mjs    = wake→balances→pick engine→   │
   │                earn→ledger→sleep            │
   │  brain.mjs   = picks engine + params (free   │
   │                model default; auto-mode opt) │
   │  ledger.mjs  = on-chain-verified realized     │
   │                P&L only, never paper          │
   └───────────────────────┬─────────────────────┘
                           ▼
   ┌─────────────────────────────────────────────────────────────┐
   │              4 ENGINES (all four ship, not Polymarket-only)  │
   │  ┌───────────┐ ┌────────┐ ┌─────────────┐ ┌───────────┐      │
   │  │Polymarket │ │ Yield  │ │ Hyperliquid │ │  Solana   │      │
   │  │bridge-fund│ │Aave/   │ │trend-follow │ │ Jupiter   │      │
   │  │register → │ │Morpho/ │ │≤2x lev,     │ │ swap only │      │
   │  │FAK order →│ │Fluid   │ │always       │ │ when edge │      │
   │  │auto-redeem│ │deposit │ │stop+TP      │ │>fee, else │      │
   │  │           │ │        │ │             │ │ WAIT      │      │
   │  └───────────┘ └────────┘ └─────────────┘ └───────────┘      │
   │      each = a TOOL + baseline strategy a weak model can run   │
   │      derived 1:1 from anicca (paths verified §5), brain picks │
   └───────────────────────────────┬───────────────────────────────┘
                                   ▼
                  ┌─────────────────────────────────────┐
                  │ real on-chain tx (Polygon/Solana)     │
                  │ → ledger.mjs → dashboard + Web App UI │
                  │   update live, on-chain-verified only │
                  └─────────────────────────────────────┘
```

## 3. Repo layout

```
vineyard/
├── README.md                 # human quickstart — "any agent can download this with ease"
├── llms.txt                  # ★machine-readable capability index★
├── package.json               # bin: "vineyard" -> cli/index.mjs ; scripts: api, dashboard
├── cli/index.mjs              # spawn|fund|run|status|list|trade|redeem|dashboard
├── api/server.mjs             # Express REST, same verbs as HTTP
├── core/
│   ├── wallet.mjs             # COPY anicca skills/earn/lib/resolve-identity.mjs (key isolation)
│   ├── loop.mjs
│   ├── ledger.mjs
│   └── brain.mjs
├── engines/
│   ├── polymarket.mjs         # from polymarket-trade/{fund_via_bridge,v2_full_flow,redeem}.py
│   ├── yield.mjs              # from earn/execute-yield.mjs
│   ├── hyperliquid.mjs        # from hl-trade/hl.py
│   └── solana.mjs             # from sol-trade/run.sh
├── dashboard/                 # ★Web App UI★ — gpt-tasteskill-built, Next.js or static+API
│   └── app/                   #   table: wallet × engine × model × realized P&L, on-chain links,
│                               #   "spawn" action wired to POST /spawn
├── media/
│   └── demo-source/           # raw captures feeding the hyperframes 15s demo (§7) — real, not staged
├── data/
│   ├── spawns.json
│   └── ledgers/<id>.jsonl
└── .env.example
```

## 4. CLI + API surface

| CLI | HTTP | does |
|---|---|---|
| `vineyard spawn [--fund N] [--engine pm\|yield\|hl\|sol]` | `POST /spawn` | own EVM+Solana wallet, register in spawns.json, print address + id |
| `vineyard fund <id> <amount> [--chain]` | `POST /fund` | route USDC to Polymarket deposit **through the bridge onramp** (registers it), or top up EVM/Solana |
| `vineyard run <id>` | `POST /run` | start the earn loop (`--once` = single pass) |
| `vineyard status <id>` | `GET /status/:id` | wallet balances + open positions + realized P&L |
| `vineyard list` | `GET /list` | all instances + live P&L |
| `vineyard trade <id> --engine <e> ...` | `POST /trade` | one manual engine action |
| `vineyard redeem <id>` | `POST /redeem` | collect resolved winnings → compound |
| `vineyard dashboard` | (serves) | open the Web App UI |

`llms.txt` lists every command + one-line usage + link to this spec.

## 5. The 4 engines — verified source paths (read 2026-07-05, all exist on disk)

| Engine | Verified anicca source | Core |
|---|---|---|
| polymarket | `~/anicca/skills/earn/polymarket-trade/{fund_via_bridge.py,v2_full_flow.py,redeem.py}` | register deposit wallet by funding THROUGH bridge onramp (never raw pUSD transfer), approve neg-risk spenders, FAK order, autonomous redeem |
| yield | `~/anicca/skills/earn/execute-yield.mjs` | deposit idle USDC to Aave/Morpho/Fluid |
| hyperliquid | `~/anicca/skills/earn/hl-trade/hl.py` | perps trend-follow, ≤2x lev, always stop+TP |
| solana | `~/anicca/skills/earn/sol-trade/run.sh` | Jupiter swap only when edge clears ~0.4% round-trip fee |

Key-isolation source: `~/anicca/skills/earn/lib/resolve-identity.mjs` (verified exists).

## 6. Web App UI

Dais verbatim: *"I just wanted to make it some kind of like web app kind of thing... with taste skills...
we wanna make it super easy."* This elevates the `dashboard/` component from a bare data table (as in the
original franklin-earn spec) to a fully designed Web App UI:

- **MUST invoke `Skill → gpt-tasteskill` before writing any dashboard frontend code** (project HARD RULE
  0.38) — Python layout randomization, AIDA structure, real motion (GSAP/motion), no cheap meta-labels.
- Functionally: a "spawn" call-to-action that hits `POST /spawn` (+ `/fund`, `/run`), and a live table of
  every spawned instance — wallet × engine × model × realized P&L, each row linking to the on-chain
  explorer (Polygonscan / Solscan) for verification.
- **MUST be verified rendered in a real browser** (CloakBrowser daily-driver or agent-browser screenshot)
  before being marked done — "it compiles" is not sufficient (HARD RULE 0.31/0.38).
- Not a new independent subsystem — it is the human-facing skin over the same REST API an agent would call
  directly. No logic lives only in the UI.

## 7. Demo video — hyperframes-composited, NOT a raw screen capture

Dais clarified 2026-07-05, correcting his own first framing ("screen capture"): *"I think it doesn't have
to be a screen capture, like it just has to be a hyperframe video of showing... how they just go and are
money... the money you put in... they just keep increasing... from literally zero to like hundred or a
thousand."* This is a **hyperframes motion-graphics composition**, not unedited terminal/browser footage:

- **Core beat = an animated money counter**: real ledger P&L climbing from **$0 → the real end figure**
  (whatever it actually is at filming time) — the emotional payoff, built with hyperframes' animated-number
  primitives (tween + easing), not a static screenshot of a number.
- **Still shows the Web App UI**: browser/web app open → "spawn" clicked → instance born → dashboard live —
  can use real screenshots/screen-recording of the UI as *source assets*, but the final cut is an edited,
  paced, hyperframes composition, not raw unedited footage.
- **No dry run / no fake numbers — HARD RULE 0.24 still applies at full strength**: the counter MUST
  animate toward a REAL number read from the actual ledger (`data/ledgers/<id>.jsonl`) after a real
  `vineyard run` produced a real on-chain tx. Stylized presentation of real data ≠ fabricated data — never
  animate toward "$1,000" if the real ledger says $12; the number IS the real number, just made watchable.
- Beats (hyperframes handles pacing/transitions, order can flex):
  1. Web App UI opens, "spawn" clicked
  2. Instance born (own wallet address appears)
  3. Real on-chain tx fires (engine picks + executes)
  4. **Money counter** animates $0 → real realized P&L, ticking up live
  5. Dashboard settles on the live, on-chain-linked total
- Fits inside the hackathon's own demo requirement ("デモまたは90秒以内のデモ動画"); a tight cut (~15s,
  flexible) stays well under the 90s cap.
- Sequenced last in the TODO — needs a working web app (§6) + at least one real engine pass with real
  ledger data (§9.3) to build the counter and UI shots from.

## 8. Money-safety invariants (copied from anicca #26/#28 — unchanged)

- Per-instance key isolation: fail-closed resolver, no instance can sign/spend with another's key.
- Never raw-deploy a Polymarket deposit wallet or raw-transfer pUSD — always via bridge onramp.
- On-chain-verified earnings only in ledger/dashboard, never paper/simulated.
- No dry run — every `run` is a real pass; report the real tx or the real WAIT.

## 9. DONE criteria

1. `vineyard spawn` creates an instance with its own isolated EVM+Solana wallet, recorded in spawns.json.
2. `vineyard fund <id> <amt>` registers + funds its Polymarket deposit via the bridge onramp (verified: `get_balance_allowance` resolves).
3. `vineyard run <id> --once` places a real on-chain action on ≥1 engine (tx status 0x1) and writes it to the ledger.
4. Web App UI (gpt-tasteskill-built, browser-verified) shows wallet × engine × realized P&L with on-chain links, and a working "spawn" call-to-action.
5. `llms.txt` + REST API let an AI do 1–4 with zero human clicks.
6. README one-command quickstart works from a clean clone — "any agent can download this with ease."
7. Hyperframes demo video exists: an animated money-counter ($0 → real end figure) + Web App UI beats, composited from real ledger data and real UI captures of 1–4 actually running (not a raw screen capture, not fake numbers).
8. VCSDD adversary PASS (fresh context, disk-only) + my own browser/on-chain E2E verify, both green.

## 10. Relationship to existing hackathon docs

- `docs/hackathon/franklin-earn-product-spec.md` — engine-derivation source of truth, paths verified here; superseded only on naming/MCP/scope framing (this doc is now canonical for the build).
- `docs/hackathon/{Predikt-Software-for-Agents-Submission.en.md,software-for-agents-submission.md}` — Polymarket-only + MCP-mentioning submission drafts; need a follow-up copy pass (TODO K) to match the final Vineyard/4-engine/no-MCP scope. Not a build blocker.
- `docs/hackathon/2026-07-05-anicca-compiled-submission.md` — broadest "Anicca" framing; may end up the better base for the actual submission text since it already avoids naming a single persona.

## 11. Full TODO (ordered)

| # | Item | Depends on |
|---|---|---|
| A | ~~Lock working codename~~ **DONE — `Vineyard` / `vineyard`** | — |
| B | Scaffold new standalone repo `vineyard/`: `cli/ api/ core/ engines/ dashboard/ media/ llms.txt README` | A |
| C | `vineyard spawn` → own EVM+Solana wallet (copy `resolve-identity.mjs`, key isolation) | B |
| D | `vineyard fund` → register+fund Polymarket deposit via bridge onramp | C |
| E | Wire all 4 engines (polymarket/yield/hyperliquid/solana) from verified anicca sources | B |
| F | `vineyard run` → earn loop (wake→pick→earn→ledger) with a real on-chain tx | C, D, E |
| G | Web App UI: invoke gpt-tasteskill → build dashboard (spawn CTA + live wallet×engine×P&L+links) → browser-verify | F |
| H | llms.txt + REST API + OpenAPI (`/openapi.json`) — zero-human-click agent path | C–F |
| I | README one-command quickstart, verified from a clean clone | B–H |
| J | Hyperframes-composited demo video: animated $0→real-figure money counter + Web App UI beats, built from real ledger data + real UI captures (not raw screen capture, not fake numbers) | F, G |
| K | Update hackathon submission docs to match final scope (Vineyard name, drop Polymarket-only + MCP framing, no "Franklin" name) | G, J |
| L | VCSDD pipeline over B–J: init → spec (1a/1b) → spec-review gate (1c) → RED (2a) → GREEN (2b) → refactor (2c) → adversary review (3, fresh context) → hardening (5) → convergence (6) | — |

## Open items (not blocking further design work)

- Whether the demo video (§7) IS the hackathon's official demo submission or a separate teaser asset.
- npm package name `vineyard` availability — check at scaffold time (TODO B), rename trivially if taken.
