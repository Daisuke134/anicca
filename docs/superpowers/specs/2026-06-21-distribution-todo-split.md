# Distribution (③ payout/UBI) TODO — split by dependency

**Date**: 2026-06-21
**Scope**: the distribution / payout side only. EARNING is done by other agents — NOT in this list.
**Purpose**: separate "needs Dais" from "anicca can do RIGHT NOW with no Dais action". Canonical;
update as items move.

---

## A. ANICCA DOES RIGHT NOW — no Dais action required (start immediately)

| # | Task | What "done" means | Dais-touch? |
|---|------|-------------------|-------------|
| A1 | **Bridge.xyz rail — live sandbox verify** | sign up at bridge.xyz, get sandbox API key, hit the REAL /v0/transfers sandbox, confirm auth-header + idempotency-header-vs-body + source payment_rail token, remove the UNVERIFIED markers in `~/anicca/skills/ubi/bridge-payout.mjs` | none (sandbox) |
| A2 | **Crossmint Offramp rail — live verify** | use existing CROSSMINT_API_KEY, hit the real Crossmint offramp/staging API, confirm the rail shapes in the crossmint payout module | none (have keys) |
| A3 | **#47 US entity (Stripe Atlas) — start incorporation** | stripe.com/atlas via daily-driver: pick C-corp, fill founder (成田大祐 / 新宿区南元町15-27) + company (anicca / aniccaai.com) from profile, get to the review screen | ONLY the final submit (passport/ID upload + ~$500 card + e-signature) = Dais confirm |
| A4 | **#59 法人印 engraving** | decide engraving text (合同会社Anicca) + reply to the Amazon seller (order 503-6400036-5967047) | none (anicca replies) |
| A5 | **#39 Proactive UBI + scale — design+build** | spec how anicca proactively distributes once funds arrive; build the orchestration (members→distribute) on top of the FIFO queue (#35) | none |
| A6 | **GDA continuous-distribution** | forwarder VERIFIED on Base; build the member-add + distribute wiring (code+tests). Actual pool creation DEFERRED until verified recipients + real USDCx exist (avoid an empty premature pool) | none |

## B. NEEDS DAIS — blocked on a human action only Dais can do

| # | Task | Blocked on |
|---|------|-----------|
| B1 | **#52 freee 合同会社 + 法人口座** | ★ 印鑑証明書 (コンビニ・マイナカード) ★ |
| B2 | **#53 GMO 個人口座** | ★ eKYC (セルフィー) ★ |
| B3 | **gate accept-path final check** | ★ Dais の実 World App scan ★ at aniccaai.com/income |
| B4 | **#47 Atlas final submit** | Dais passport/ID + ~$500 card + e-signature (A3 gets it to this point) |
| B5 | **#34 Bridge / #50 Crossmint / #37 Kotani — KYB FINAL** | a formed entity (#52 JP or #47 US) — the business-verification step. Code + sandbox (A1/A2) is anicca's; the KYB doc submit waits on the entity |
| B6 | **#54 GMO 銀行API STEP1 production** | the 法人口座 from #52 |

## C. DONE (this session, 2026-06-21)

- World ID 4.0 personhood gate **LIVE** on aniccaai.com/income (E2E-verified, key rotated, VCSDD PASS).
- Netlify 4KB Lambda-env limit fixed (was blocking all landing deploys).
- Payout rails CODED + VSDD: GMO (JP), Crossmint (US), Kotani (M-Pesa), Bridge (US/global), wallet, email.
- GDA module + forwarder verified on Base.
- Earn capability independently confirmed on-chain (Aave v3) — but earning itself = other agents.

---

**Bottom line**: A = anicca executes now (A1→A6). B = unblocks the moment Dais finishes 印鑑証明書 (B1) + eKYC (B2). Earning is excluded (other agents).
