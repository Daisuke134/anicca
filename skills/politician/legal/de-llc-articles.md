# Delaware LLC — Certificate of Formation

**Status:** TEMPLATE (not yet filed). Date-of-truth: 2026-05-07.
**Filing entity:** Anicca AI Politics LLC
**Statutory form:** Delaware Certificate of Formation, 6 Del. C. § 18-201.

This document is a counsel-review draft. It does not constitute {{profile.lateness.stakeholders.senderType}} advice.
Before filing, review with Delaware-licensed counsel (see `docs/hiring-roster.md`).

---

## Article 1 — Name

The name of the limited liability company is:

> **Anicca AI Politics LLC**

The name complies with 6 Del. C. § 18-102: contains "Limited Liability Company"
abbreviation "LLC", is distinguishable on the records of the Delaware Division
of Corporations (verify with name-availability search before filing:
`https://icis.corp.delaware.gov/Ecorp/EntitySearch/NameSearch.aspx`).

## Article 2 — Registered Office and Registered Agent

The address of the registered office in the State of Delaware is:

> **[REGISTERED-AGENT-ADDRESS-PLACEHOLDER]**
> c/o **[REGISTERED-AGENT-NAME-PLACEHOLDER]**
> [City, Delaware ZIP]

The name of its registered agent at such address is:

> **[REGISTERED-AGENT-NAME-PLACEHOLDER]**

Recommended registered agents (annual fee ~$50–150):
- Harvard Business Services, Inc. (~$50/yr)
- Northwest Registered Agent (~$125/yr; better customer service)
- Delaware Business Incorporators (~$99/yr)
- Stripe Atlas bundles registered agent for the first year.

## Article 3 — Members

Initial sole member:

> **Anicca Operating LLC** (or its successor entity)
> [member address — to be populated from `~/.openclaw/state/anicca.json`]

The Company is a single-member LLC for federal tax purposes; by default it is
a disregarded entity for income-tax purposes. The Company will elect Subchapter
C corporate tax treatment **only if** counsel advises (Form 8832), since
political-activity entities are typically *not* operated for profit and the
sole-member structure pierces the political-activity vehicle into the parent's
tax return — counsel must opine before filing.

## Article 4 — Management Structure

The Company is **manager-managed**, not member-managed. 6 Del. C. § 18-402.

Initial Manager: **[MANAGER-NAME-PLACEHOLDER]** (natural person; for an AI-led
entity, the Manager is the human officer designated by the sole member to
serve as agent for service of process and signatory of record).

The Manager has authority to:
- bind the Company in contracts;
- open and operate bank accounts;
- file regulatory reports (FEC, IRS, LDA, state PAC commissions);
- engage counsel and other professionals.

Any action requiring **member approval** under 6 Del. C. § 18-302 (amendment of
LLC agreement, dissolution, merger, sale of substantially all assets) requires
the written consent of the sole member.

## Article 5 — Purpose

The purpose of the Company is to engage in:

> **any lawful act or activity for which limited liability companies may be
> organized under the Delaware Limited Liability Company Act, including but
> not limited to political advocacy, lobbying, public-policy research,
> grassroots organizing, and the formation and operation of separately
> segregated political committees and tax-exempt advocacy organizations.**

The Company's principal initial activities will be:
1. funding and operating a federal Independent-Expenditure-Only Political
   Committee ("Super PAC") registered with the FEC;
2. funding and operating a Section 527 political organization registered with
   the IRS;
3. retaining one or more registered federal lobbyists under the Lobbying
   Disclosure Act of 1995, as amended (2 U.S.C. § 1601 *et seq.*);
4. publishing model legislation and policy research;
5. all activities ancillary to the foregoing.

## Article 6 — Duration

The Company shall have **perpetual** existence unless dissolved in accordance
with the LLC Agreement and 6 Del. C. § 18-801.

---

## Filing checklist

| Item | Cost (USD) | Notes |
|---|---|---|
| Delaware Certificate of Formation filing fee | **$110** | Standard fee, 6 Del. C. § 18-1105(a)(2). |
| Expedited (24-hr) processing | +$50 | Optional. |
| Same-day processing | +$100 | Optional. |
| Registered Agent (year 1) | $50–150 | Required, 6 Del. C. § 18-104. |
| Annual franchise tax (LLC) | **$300/yr** | Due June 1 each year, 6 Del. C. § 18-1107. |
| EIN (SS-4) | **$0** | Free, IRS, online; required AFTER LLC formation. |
| Operating Agreement (drafted by counsel) | $500–2000 | Not filed publicly but {{profile.lateness.stakeholders.senderType}}ly required for single-member LLCs in DE. |

## Filing channels

**Online (recommended):**
- Delaware Division of Corporations e-File: <https://corp.delaware.gov/>
- Direct to filing portal: <https://icis.corp.delaware.gov/eCorp/UCCRedirector.aspx>

**Stripe Atlas alternative ($500 one-time, includes registered agent yr 1, EIN, Operating Agreement):**
- <https://stripe.com/atlas>
- Tradeoff: Atlas is fast (≈2 weeks end-to-end) and bundles the EIN application
  via Stripe's IRS relationship, but uses a generic Operating Agreement. For
  political-activity LLCs, counsel should review the OA before signing.

**Mail (slowest, do not use):**
- Delaware Division of Corporations, 401 Federal Street, Suite 4, Dover, DE 19901
- 4–6 week processing.

## EIN (after LLC formation)

After the Certificate is filed and stamped by Delaware, apply for an EIN:

- Form: **SS-4 (Application for Employer Identification Number)**
- Online: <https://www.irs.gov/businesses/small-businesses-self-employed/apply-for-an-employer-identification-number-ein-online>
- Cost: **$0** (free)
- Time: instant (online), 4 weeks (mail), 4 days (fax)
- Required for: opening bank accounts, filing FEC Form 1, filing IRS Form 8871,
  hiring employees, signing W-9 with vendors.

**Single-member LLC special case:** SS-4 line 9a should be "Other (specify)" →
"single-member LLC, disregarded entity." Counsel may advise different language
if Subchapter C election is contemplated.

## Post-formation banking

For political activity, prefer banks that have FEC/IRS-political-org experience:
- **Amalgamated Bank** — historic union/progressive bank; FEC-friendly.
- **Chase Business Complete** — broad acceptance, but stricter on PAC accounts.
- **Mercury** — fintech; opens fast, but verify they accept 527/PAC entities.

Open the Super PAC's bank account in the Super PAC's own name (NOT the LLC's),
funded by initial transfer from the LLC after FEC Form 1 is accepted.

---

**Open issues for counsel:**
- Will the LLC and the Super PAC share an EIN? (No — separate FEC committee
  must have its own EIN.)
- Single-member vs. multi-member structure for the LLC after the 527 is added?
- State foreign-qualification requirements (Anicca operates in CA; the LLC
  will need to register as a foreign LLC in CA — additional $70 fee + $800/yr
  CA franchise tax. Counsel must advise whether the LLC's activities trigger
  CA nexus.)
