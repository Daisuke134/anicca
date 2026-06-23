# Capafy Skill Monetization — road to $10k MRR (2026-06-23)

SSOT for selling Anicca skills on capafy.ai as subscriptions. OSS is free (nobody pays) → ALL skill
revenue comes from Capafy `run_online` subscriptions. Life Manager is product #1 (the flagship that
proves the pipeline); $10k MRR requires a CLONED PORTFOLIO, not one skill.

Companion: `~/.openclaw/docs/CAPAFY_PROFITABLE_PLAYBOOK.md` (winner patterns), memories
`reference_capafy_profitable_playbook`, `reference_capafy_buyer_search_auth_and_otp_read`.

---

## 1. Pricing (cloned EXACTLY from the top sellers — originality is a sin)

**COPY ONE SKILL VERBATIM — the top money-maker that has NO trial. Zero originality, no blending,
no stripping a trial off a trial-skill (that is a modification = a sin).** Dais directive 2026-06-23:
copy the highest-earning skill that natively has no free trial = **Serenity Stock Tracker (57 sales,
`supportFreeTrial=0`)**. Life Manager clones its EXACT billings array verbatim:

| tier | cyclePrice | cycleMaxMessageCount | supportFreeTrial |
|---|---|---|---|
| week | **$9.90** | **30** | **0 (no trial)** |
| month | **$29.90** | **120** | **0 (no trial)** |

`run_online`, `subscription`, `Claude Sonnet 4.6`, `containerMode: on_demand`. **No day tier, no
trial** — exactly as Serenity ships them. Do not add/remove a tier or a trial (that = our originality).

---

## 2. Revenue model (honest)

- **Gross MRR = active subscribers × blended ARPU.** Blended ARPU ≈ **$11/mo** (mix of week renewals +
  month tier).
- **Net to us** = gross − Capafy platform fee (`platformFeeRate`, assume ~30%) − our hosted LLM/call cost.
- **Margin differs by skill type**: text/image skills = fat margin (one cheap LLM/image call). Life
  Manager = thinner (real Telnyx + Gemini phone-call cost) → the `cycleMaxMessageCount` cap is the
  loss-prevention lifeline.

### Life Manager alone (gross MRR by active subs)
| active subs | gross MRR | net ~70% | after call cost |
|---|---|---|---|
| 25 (slow) | $275 | ~$193 | ~$140 |
| 60 (top-seller traction) | $660 | ~$462 | ~$340 |
| 150 (strong) | $1,650 | ~$1,155 | ~$850 |

**A single top-tier skill ≈ $500–700 gross MRR.** So Life Manager alone CANNOT reach $10k.

### Path to $10k MRR = portfolio
| approach | math |
|---|---|
| one flagship | impossible (~$700 MRR ceiling per skill) |
| **portfolio of clones** | ~15–20 skills × ~$500–700 = **$10k MRR** |
| few hits + tail | 3 hits @ $1.5k + 12 tail @ $400 ≈ $9.3k |

To hit $10k gross MRR at $11 ARPU ≈ **~900 active subscribers** across the portfolio. Lead with
**cheap-marginal skills** (writers, generators, optimizers — fat margin) + Life Manager as the flagship.

---

## 3. Pipeline (use the skills we built — no hand-driving browsers)

| tool | role |
|---|---|
| `capafy-user` skill | research: search winners by salesVolume + `GET /agent/agent/agents/{id}` full listing to clone |
| `capafy-publisher` skill | CLI: publish-init → configure (--deep-scan) → ship; remote-status / refresh-url |
| **`capafy-autopublish` skill** | end-to-end: CLI chain + `drive_checkpoint1.py` (camofox :9377) drives the 3 web checkpoints — Card edit, **Deselect-All workspace docs**, logo, category, pricing, leak-gate (fail-closed), Submit-for-Review, verify status=1/4, ledger `published.jsonl` |

Credential model (run_online subscription): LLM + Telnyx + Gemini = OUR keys → `PLATFORM_MANAGED_*` →
Capafy-hosted (buyer enters nothing). Buyer connects ONLY their own Google Calendar (Composio OAuth) +
phone number. Requires our LLM account funded before publishing.

---

## 4. Remaining TODO until the END

### Track A — Life Manager on Capafy (flagship, product #1)
- [ ] A1 build cloned listing metadata (title `Anicca Life Manager — Never Be Late Again`, pain-first
      shortDesc, 👋 welcomeMessage, emoji-headed detailedDescription, tags `calendar,reminder,wake-call`,
      category 1, Sonnet 4.6) — clone the winner structures
- [ ] A2 confirm our LLM account is funded (subscription publish fails on $0.01)
- [ ] A3 run `capafy-autopublish` on `~/life-manager` (improved skill already re-bundled @ draft 7631594519):
      Card edit + Deselect-All workspace docs + 3-tier pricing + logo → leak-gate → Submit for Review
- [ ] A4 verify status=1 (審査中) then 4 (listed); record to `published.jsonl`
- [ ] A5 first real paid subscriber E2E: buyer connects gcal + phone → gets a wake call (no-mock)

### Track B — Content (the journey = build-in-public)
- [ ] B1 write the Capafy article via `ai-entity-article-writer` (reverse-engineer winners → build →
      sell Life Manager), de-slop via stop-ai-slop(-jp), publish
- [ ] B2 demo-reel of the journey → TikTok/X (#45)

### Track C — Portfolio scale to $10k MRR (the real goal)
- [ ] C1 pick 10–20 cheap-marginal niches from the winner list (writers, generators, optimizers)
- [ ] C2 clone each via the playbook (capafy-user research → metadata clone → autopublish)
- [ ] C3 track active subs + MRR per skill; double down on hits, kill duds
- [ ] C4 reach ~900 active subs / $10k gross MRR

### Track D — Life Manager WEB app (separate managed-keys product, #29) + PH launch (#51/#89/#90)
- [ ] D1 Product Hunt schedule + launch-day (#89/#90)
- [ ] D2 web app dogfood + launch (#29); Telegram onboarding (#63/#67/#68); Outlook/no-gcal (#70)
- [ ] D3 local Node convergence, retire Python (#74/#77)
