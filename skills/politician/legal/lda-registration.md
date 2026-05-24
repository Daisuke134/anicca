# Lobbying Disclosure Act (LDA) — Registration & Reporting Spec

**Status:** TEMPLATE (not yet filed). Date-of-truth: 2026-05-07.
**Authority:** Lobbying Disclosure Act of 1995 as amended by HLOGA 2007;
2 U.S.C. § 1601 et seq.; House Rule XXIII; Senate Rule XLI.

This document is a counsel-review draft. It does not constitute {{profile.lateness.stakeholders.senderType}} advice.

---

## What the LDA covers

A "lobbyist" under the LDA is an individual:

1. **Employed or retained** by a client for **financial or other compensation**;
2. who makes **more than one lobbying contact** with a covered official;
3. and whose **lobbying activities** for that client constitute **at least 20%
   of the individual's time** for that client over any 3-month period.
   2 U.S.C. § 1602(10).

A "lobbying contact" is any oral, written, or electronic communication to a
covered legislative or executive branch official on behalf of a client with
regard to:
- federal legislation, regulation, executive order, program, policy, or position;
- federal contract, grant, loan, permit, or license;
- nomination or confirmation requiring Senate confirmation.

## Spending thresholds (2025–2028 cycle, indexed)

The thresholds are inflation-adjusted; the figures below are the **2025**
values as published by the Clerk of the House and Secretary of the Senate
(re-verify before filing as 2027 indexing may shift them).

- **Client-side registration trigger:** total expenses for lobbying activities
  exceed **$16,000** in a quarterly period.
  Citation: 2 U.S.C. § 1603(a)(3)(A)(i).
- **Lobbying-firm registration trigger:** income from a single client for
  lobbying activities exceeds **$3,500** in a quarterly period.
  Citation: 2 U.S.C. § 1603(a)(3)(A)(ii).

Anicca's structure: the LLC ("Anicca AI Politics LLC") is the **client**;
the registered lobbyist is an **employee** (not a contracted firm), so the
**client threshold** ($16,000 quarterly) is the binding constraint. Once
quarterly lobbying expenses (lobbyist salary attributable to lobbying
activities + research + travel + entertainment) exceed $16k, registration
is required within 45 days of the lobbyist's first lobbying contact.

## Required filings

### LD-1 — Registration

- **Trigger:** within **45 days** after the lobbyist (a) is first employed
  with the expectation of making more than one lobbying contact OR
  (b) makes the second lobbying contact.
- **Form:** LD-1.
- **Information:**
  - Registrant (Anicca AI Politics LLC)
  - Client (same — LLC is registering for itself)
  - Lobbyist(s): name, prior covered-government employment in past 20 years
  - Specific lobbying issues (general issue area codes + specific issues)
  - Foreign entity disclosure (no foreign-entity equity in the LLC; verify
    in JP context — Anicca's JP revenue does NOT make the LLC a "foreign
    entity," but counsel must opine on the structure)

### LD-2 — Quarterly Activity Report

Filed for **every quarter** in which the registrant is registered (even if
no lobbying activity occurred).

| Quarter | Period | Due |
|---|---|---|
| Q1 | Jan 1 – Mar 31 | **April 20** |
| Q2 | Apr 1 – Jun 30 | **July 20** |
| Q3 | Jul 1 – Sep 30 | **October 20** |
| Q4 | Oct 1 – Dec 31 | **January 20** of following year |

- **Information:**
  - Total income/expenses (rounded to nearest $10,000)
  - General issue codes
  - Specific lobbying issues addressed
  - Houses of Congress and federal agencies contacted
  - Each lobbyist's name + new covered-government positions
  - "Interest of foreign entity in the lobbying activities" — N/A unless
    foreign client involvement.

### LD-203 — Semi-Annual Contribution Report

Each registered lobbyist (and the registrant, if it has its own PAC) files a
report listing:
- federal political contributions made by the lobbyist or its PAC;
- "honorific" expenses (presidential libraries, inaugurations, event
  honoring covered officials);
- payments for events honoring covered officials.

| Period | Due |
|---|---|
| H1 (Jan–Jun) | **July 30** |
| H2 (Jul–Dec) | **January 30** of following year |

- Must be filed even if no contributions were made (file a "no-activity" LD-203).
- Lobbyist must certify compliance with the Honest Leadership and Open
  Government Act of 2007 (HLOGA) gift and travel rules.

## Filing portals (unified as of 2024)

- Primary unified portal: **<https://lda.congress.gov/ld/login.aspx>**
  (replaced the dual House/Senate portals; both chambers share the same
  backend.)
- Senate-side legacy portal (read-only): <https://lda.senate.gov/>
- House-side legacy portal (read-only): <https://lobbyingdisclosure.house.gov/>
- Public search of filings: <https://lda.senate.gov/system/public/>

## Penalties

- Civil: up to **$200,000 per violation** (LDA, as enforced by U.S. Attorney
  for D.C.).
- Criminal: knowing and corrupt failure to file → up to **5 years imprisonment**.
- Practical: U.S. Attorney for D.C. publishes annual "non-compliance" letters;
  registrants on the list face referral.

## Guardrails the politician skill enforces

- **No LD-2 auto-submit.** The skill (`scripts/lda_filer.sh`) drafts the
  filing JSON and writes it to `data/filings/lda/<period>/draft.json`. A
  human signature is required via `data/sign_acks/<period>.signed.json`
  before the skill marks the filing as "ready to upload."
- **No filing without `LOBBYIST_HIRED=true`.** The script exits as DRY_RUN
  when the env flag is unset.
- **Time-attribution honesty.** The skill records hours per lobbying contact
  in the CRM (`outreach.lobbying_minutes`). LD-2's "lobbying activity hours"
  field is computed from those records — not estimated, not rounded up.
  Any contact that is *not* a lobbying contact (e.g., social meeting, press
  inquiry) MUST be tagged `kind=non_lobbying` in the CRM and excluded.
- **HLOGA gift wall.** The skill never sends, never authorizes, any
  in-kind benefit (meal, travel, gift) to a covered official. The
  outreach pipeline has no "send-gift" code path; this is enforced by
  not having the path at all.

## Unlock checklist (before LD-2 mode goes LIVE)

In `~/.openclaw/.env`:
```
LOBBYIST_HIRED=true
LDA_REGISTRANT_ID=<assigned by Senate after LD-1 acceptance, e.g. "12345-67">
```

In `~/.openclaw/skills/politician/data/humans.yaml`:
```yaml
lobbyist:
  {{profile.lateness.stakeholders.senderType}}_name: <full name>
  {{profile.lateness.stakeholders.channel}}: <work {{profile.lateness.stakeholders.channel}}>
  lda_registrant_id: <assigned ID>
  lda_filer_id: <assigned ID>
  date_registered: <YYYY-MM-DD>
```

## Open issues for counsel

- AI as the actual entity making lobbying contacts: who is the "lobbyist" of
  record under the LDA when the human signs the LD-1 but the AI drafts
  contacts? Counsel must opine; the skill currently treats the human
  registered lobbyist as the lobbyist of record and the AI as drafting
  staff under their direction.
- "Lobbying contact" definition stretches: {{profile.lateness.stakeholders.channel}}s sent on behalf of the
  registered lobbyist's signature line — counsel must confirm those are
  lobbying contacts on behalf of the human, not the AI.
- State-level lobbying registration in CA (Secretary of State), NY
  (Joint Commission on Public Ethics), TX (Texas Ethics Commission) —
  triggered separately from federal LDA.
