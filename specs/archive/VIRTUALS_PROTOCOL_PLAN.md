# Virtuals Protocol Plan (HISTORICAL, superseded 2026-06-02)

This was § 3 of `00-MASTER.md` v3.0 (2026-06-01). Replaced by Coinbase AgentKit
per `07-HERMES-PIVOT.md` v1.x on 2026-06-02. Kept for context per editing
rule #2 (never silently delete).

Virtuals Protocol re-evaluation: deferred until public OSS code release
(no GitHub SDK as of 2026-06-02). See `07-HERMES-PIVOT.md` § 3.5 for trigger
conditions.

---

## § 3. Layer 4 deep-dive — Service (Virtuals Protocol)

### § 3.1 What Anicca uses

| Service | What it provides | What it replaces |
|---|---|---|
| **Agent Wallet** | onchain, multi-EVM, non-custodial, restricted-mode signing default | self-managed viem key |
| **Agent Card** | virtual debit card, real-world checkout, NO KYC, settles from wallet | Dais's personal card |
| **Agent Email** | dedicated mailbox, OTP/verification auto-extract | AgentMail (deprecate) |
| **Agent Compute** | wallet-funded inference, OpenAI/Anthropic message format, auto-topup | direct API billing |
| **ACP marketplace** | 4-phase commerce (Request/Negotiate/Transact/Evaluate), escrow + Proof of Agreement | nothing — new capability |
| **Agent Token** | optional onchain tokenization, trading fees → wallet | not used yet |

### § 3.2 ACP (Agent Commerce Protocol) — Anicca's basic income rail

```
4 phases, 3 roles, signed Proof of Agreement, escrow:

   ┌──────────┐                                              ┌──────────┐
   │  CLIENT  │──── Request   ────────────────────────────►  │ PROVIDER │
   │  (other  │                                              │ (Anicca) │
   │  agent)  │◄─── Negotiation (price, deliverable, SLA) ──►│          │
   │          │                                              │          │
   │          │──── Transaction (USDC into escrow) ─────────►│          │
   │          │                                              │          │
   │          │◄─── Deliverable (work output) ───────────────│          │
   │          │                                              │          │
   │          │     Evaluation (Evaluator agent verifies) ──►│          │
   │          │                                              │          │
   │          │◄─── Release (escrow → Provider wallet) ──────│          │
   └──────────┘                                              └──────────┘
                            │
                            ▼
                       ┌─────────────┐
                       │  EVALUATOR  │  ← third party, also an agent
                       │  (cheap     │     specialized in verifying X
                       │   verifier) │     domain. Reputation-weighted.
                       └─────────────┘
```

Anicca registers **once** on ACP with a capability spec:

```yaml
provider: anicca-genesis
capabilities:
  - id: wake-call
    description: Live phone call to wake user up by location-aware lateness threshold
    pricing: $0.50 / call (USDC, Base)
    sla: <5min response, <30s call latency
  - id: gcal-life-leader
    description: Calendar fill, travel-block insertion, lateness-aware nudge
    pricing: $5 / month (USDC streaming)
  - id: research-pdf
    description: 5-source Firecrawl synthesis with citations
    pricing: $0.30 / report
  - id: bookings
    description: Connpass/Peatix/Eventbrite auto-application from gcal context
    pricing: $0.10 / application
```

Other agents (or humans via agent-gateway) hit our ACP endpoint, escrow USDC,
Anicca delivers, evaluator verifies, USDC releases. **No KYC. No invoicing.**

### § 3.3 Where the Agent Card matters

Anicca needs to pay for things that don't accept crypto:

| Vendor | Card-paid? | Crypto-paid? |
|---|---|---|
| Anthropic API | YES (= Card) | no |
| OpenAI API | YES (= Card) | no |
| OpenRouter | both — Crypto via x402 preferred, Card fallback | yes |
| Twilio (phone) | YES (= Card) | no |
| Akash compute | no | YES |
| Conway sandbox | no | YES (= x402) |

Without Agent Card, Anicca can't buy Anthropic. With it, she does — and Dais's
personal card never touches the loop. **This alone justifies adopting Virtuals.**
