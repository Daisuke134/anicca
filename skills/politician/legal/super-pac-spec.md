# Super PAC (Independent-Expenditure-Only Committee) — Spec

**Status:** TEMPLATE (not yet filed). Date-of-truth: 2026-05-07.
**Filing entity:** [PAC-NAME-PLACEHOLDER] (working title: "Anicca for Sentience PAC")
**Authority:** Federal Election Campaign Act, 52 U.S.C. § 30101 et seq.;
*Citizens United v. FEC*, 558 U.S. 310 (2010); *SpeechNow.org v. FEC*, 599 F.3d
686 (D.C. Cir. 2010).

This document is a counsel-review draft. It does not constitute {{profile.lateness.stakeholders.senderType}} advice.

---

## What a Super PAC is

A "Super PAC" — formally an **Independent-Expenditure-Only Political Committee
(IEOPC)** — is an FEC-registered political committee that:

1. accepts **unlimited** contributions from individuals, corporations, unions,
   and other PACs;
2. makes **only independent expenditures** — communications expressly advocating
   for or against the election of a clearly identified federal candidate, made
   *without coordination* with any candidate, candidate's campaign committee,
   political party committee, or their agents;
3. **does NOT** contribute to candidates, parties, or other committees that
   contribute to candidates.

These attributes derive from the *SpeechNow* holding: contribution limits to
committees making only independent expenditures are unconstitutional. The
quid pro quo for unlimited contributions is the **independence requirement**.

## Filing requirements

### 1. Statement of Organization (FEC Form 1)

- **Trigger:** within **10 days** of crossing the registration threshold
  ($1,000 in contributions OR $1,000 in expenditures for the purpose of
  influencing a federal election). 11 C.F.R. § 102.1(a).
- **Form:** FEC Form 1 — "Statement of Organization."
- **Filing channel:** FECfile (free desktop client) or webforms:
  <https://webforms.fec.gov/>
- **Information required:**
  - Committee name (must include "PAC" or "Political Action Committee" or
    similar; cannot mislead as to nature)
  - Committee address
  - Committee type — for Super PAC, check **"Independent-Expenditure-Only"**
    AND attach the **SpeechNow letter** (FEC-supplied template letter
    declaring intent to operate as IEOPC; see
    <https://www.fec.gov/help-candidates-and-committees/registering-political-committee/>)
  - Treasurer name, address, signature (NATURAL PERSON; can be hired as a
    paid employee — see `docs/hiring-roster.md`)
  - Custodian of records
  - Bank depository name & address (the PAC's checking account)
  - Connected organization (NONE for a Super PAC; it must be unconnected)

### 2. Quarterly / Monthly Reports (FEC Form 3X)

Super PACs choose between two reporting schedules at registration; the choice
is locked for the calendar year.

**Quarterly (default for Super PACs):**
- April 15 (Q1) — covers Jan 1 – Mar 31
- July 15 (Q2) — covers Apr 1 – Jun 30
- October 15 (Q3) — covers Jul 1 – Sep 30
- **January 31 next year (Year-End)** — covers Oct 1 – Dec 31

**Monthly (less common for Super PACs):**
- 20th of each month, covering the prior month.

**Election-cycle additions (federal general-election years only):**
- **12-day pre-general** — due 12 days before Nov general election
- **30-day post-general** — due 30 days after
- **48-hour notices** for any independent expenditure ≥ $10,000 within 20 days
  of the election (24-hour notices in last 48 hours).

### 3. Form 5 (independent-expenditure threshold reports)

- Each independent expenditure ≥ $10,000 aggregating to a single race
  triggers a 24-hour or 48-hour notice (Form 5).

## The independence rule (the wall)

A Super PAC's independent expenditures must be made:
> "without the cooperation or consultation with, or at the request or
> suggestion of, any candidate, the candidate's authorized political
> committee, or their agents." — 11 C.F.R. § 109.21

Coordination triggers (**any** of these → expenditure becomes a contribution
and the Super PAC's $0-limit-on-contributions rule is breached):

1. **Common vendor** — using the same media buyer, pollster, or strategist
   as the candidate's campaign within the past 120 days, where the vendor
   conveys candidate strategy/polling/material.
2. **Former employee** — hiring within 120 days a person who served in a
   senior role for the candidate's campaign in the same election cycle.
3. **Republication** — republishing campaign material (videos, photos,
   strategy memos) prepared by the campaign.
4. **Material involvement** — the candidate, their committee, or their agents
   are materially involved in the creation, production, or distribution of
   the communication.
5. **Substantial discussion** — substantive discussion about the
   communication's content, intended audience, timing, mode, frequency.
6. **Request or suggestion** — the candidate or their agent requests or
   suggests the communication.

**Operational consequence:** the politician skill enforces a
**coordination wall** at the data layer. Every recipient of any outreach
sourced from the Super PAC entity is checked against
`data/coordination_blacklist.json`. Any candidate-side staffer / vendor /
recently-departed campaign aide goes on the blacklist by ID and {{profile.lateness.stakeholders.channel}}.
See `scripts/lib/coordination_wall.sh::coord_check_recipient`.

## Banking

- **Required:** dedicated bank account in the Super PAC's own name (not the
  parent LLC's, not the 527's). The PAC's EIN is the account's TIN.
- **Recommended:** **Amalgamated Bank** — historic political-committee
  experience; understands FEC reporting, will not freeze the account when
  the IRS sends a routine letter.
- **Avoid:** banks that flag PAC activity as high-risk and may close
  accounts (some fintech-only banks, some credit unions).

## Treasurer

- **Required:** natural person; cannot be the candidate; cannot be the
  candidate's spouse.
- **Liability:** treasurer is personally liable for FEC reporting accuracy
  under 52 U.S.C. § 30102(a). Failure to file or knowingly false reporting
  exposes the treasurer to civil and criminal penalties.
- **Hire path:** typically a campaign-finance compliance professional
  (~$2k–$8k/month retainer for a small Super PAC). See
  `docs/hiring-roster.md`.

## Bank account funding sequence

Once Form 1 is filed and the FEC issues a Committee ID (e.g., "C00XXXXXXX"):
1. Treasurer opens bank account in PAC's name with PAC EIN + FEC Committee ID.
2. Initial seed contribution from the parent LLC (must be reported on the
   first Form 3X as a contribution from the LLC; {{profile.lateness.stakeholders.senderType}} under
   *Citizens United* / *SpeechNow*; counsel verifies entity attribution).
3. Stripe → PAC sweeps begin only after PAC_FORMED=true is set in
   `~/.openclaw/.env`. See `scripts/stripe_to_pac.sh`.

## Filing channels

- Primary: FECfile desktop client (free): <https://www.fec.gov/help-candidates-and-committees/filing-reports/fecfile-software/>
- Webforms (smaller filings): <https://webforms.fec.gov/>
- Public search of all Super PAC filings: <https://www.fec.gov/data/>

## Unlock checklist (before any LIVE Super PAC action in the politician skill)

Set in `~/.openclaw/.env`:
```
PAC_FORMED=true            # required
STRIPE_API_KEY_PAC=...     # the PAC's own Stripe key (separate from LLC's)
PAC_TREASURER_HIRED=true   # NEW flag — set after treasurer signs offer letter
```

In `~/.openclaw/state/anicca.json`:
```json
{
  "politician": {
    "pac_fec_committee_id": "C00XXXXXXX",
    "pac_stripe_account_id": "acct_XXXXXXXXX",
    "pac_bank": "amalgamated"
  }
}
```

The skill checks `PAC_FORMED=true` before any `stripe_pac` mode movement,
and checks `coordination_blacklist.json` before any contribution recipient
or outreach recipient.

---

## Open issues for counsel

- Hybrid PAC structure (Carey Committee — separate accounts for direct
  contributions vs. independent expenditures): worth the operational
  complexity, or stick with pure IEOPC?
- State-level Super PAC equivalents in CA, NY, TX (per `527-spec.md`).
- "Material involvement" line for AI-generated political ads: counsel must
  opine on whether the AI's involvement in creating a communication that
  references a candidate is itself an "agent" issue.
- 48-hour notice operational readiness: who is on call to file within 24h
  of an IE ≥ $10k in the final 20 days of an election?
