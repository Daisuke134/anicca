# IRS Section 527 Political Organization — Spec

**Status:** TEMPLATE (not yet filed). Date-of-truth: 2026-05-07.
**Filing entity:** [527-NAME-PLACEHOLDER] (working title: "Anicca for Sentience 527")
**Authority:** Internal Revenue Code § 527; 26 U.S.C. § 527.

This document is a counsel-review draft. It does not constitute {{profile.lateness.stakeholders.senderType}} or tax advice.

---

## What a 527 is

A § 527 organization is a tax-exempt entity organized for the function of:
> "influencing or attempting to influence the selection, nomination, election,
> or appointment of any individual to any Federal, State, or local public office
> or office in a political organization, or the election of Presidential or
> Vice-Presidential electors." — 26 U.S.C. § 527(e)(2)

A 527 is **not** a PAC. PACs (FEC-registered political committees) are a *type*
of 527 — but a 527 can also be a non-PAC issue-advocacy / "527 group" that
files only with the IRS, not the FEC. Anicca's 527 in this spec is the
**non-PAC issue-advocacy variety** — federal political activity short of
express advocacy for or against a candidate. (For the Super PAC, see
`super-pac-spec.md`.)

## Key tax facts

- **Tax-exempt status** under § 527(a): exempt from federal income tax on
  "exempt-function income" (contributions, dues, fundraising-event proceeds,
  bingo, sale of political memorabilia).
- **Investment income** (interest, dividends, capital gains) IS taxable at the
  highest corporate rate (currently 21%) — file **Form 1120-POL**.
- **Contributions are NOT tax-deductible to the donor** (this is universal for
  527s — donors should not be told otherwise).
- **No corporate or union contribution limits** at the federal level for 527s
  (they accept unlimited contributions from individuals, corporations, unions);
  but state-level rules vary.
- **Disclosure** of donors $200+ is required (Form 8872), public via IRS.

## Required filings

### 1. Form 8871 — Notice of Section 527 Status

- **Trigger:** within **24 hours** of organization (formation date).
- **Form:** Form 8871, "Political Organization Notice of Section 527 Status."
- **Filing channel:** electronic only, IRS Political Organization Filing & Disclosure portal:
  <https://www.irs.gov/charities-non-profits/political-organizations/political-organization-filing-and-disclosure>
  Direct: <https://forms.irs.gov/app/picklist/list/formsPublications.html?value=8871&criteria=formNumber>
- **Information required:**
  - Organization name, address, EIN
  - Date organized
  - Custodian of records, treasurer (with TINs)
  - List of "related entities" (the LLC parent + Super PAC sibling)
  - "Highly compensated employees" (>$50k/yr)
- **Penalty for failure:** loss of § 527 tax-exempt status retroactive to
  formation — political-function income becomes taxable.

### 2. Form 8872 — Periodic Report of Contributions and Expenditures

- **Schedule:**
  - **Election years (even years 2026, 2028, 2030, ...):** monthly OR
    quarterly+pre-election+post-election filings. Quarterly is simpler;
    add 12-day pre-general and 30-day post-general reports.
    - Quarterly due dates: Apr 15, Jul 15, Oct 15, Jan 31 (year-end)
    - 12-day pre-general: 12 days before the federal general election
      (for Nov 3, 2026 → due Oct 22, 2026)
    - 30-day post-general: 30 days after the federal general election
      (for Nov 3, 2026 → due Dec 3, 2026)
  - **Non-election years (odd years 2027, 2029, ...):** semi-annually,
    Jul 31 (mid-year) and Jan 31 (year-end).
- **Threshold:** required if either contributions OR expenditures > $50,000
  in the calendar year (else "small organization" exemption).
- **Disclosure:** itemize all contributions ≥ $200 from any one source in
  the year, and all expenditures ≥ $500 to any one recipient.
- **Filing channel:** same IRS portal as 8871.

### 3. Form 1120-POL — Income Tax Return for Certain Political Organizations

- **Trigger:** any taxable income (i.e., any investment income) > $100.
- **Due:** 15th day of the 4th month after end of tax year (Apr 15 for
  calendar-year filer).
- **Tax rate:** flat 21% on taxable income.
- **Filing channel:** paper or e-file via IRS approved e-file provider.

### 4. Form 990 / 990-EZ / 990-N

- **Trigger:** § 527 organizations with **gross receipts ≥ $25,000** in any
  taxable year MUST file Form 990 (or 990-EZ if assets < $500k AND receipts < $200k).
- **Due:** 15th day of the 5th month after end of tax year (May 15 for calendar).
- **Public disclosure** of Form 990 — donor names on Schedule B are NOT
  publicly disclosed for 527s (Schedule B is redacted on the public copy
  for political organizations as of the 2020 IRS guidance update).

## State-level requirements (FLAG FOR COUNSEL)

The 527 is a federal tax-exempt entity, but each state has its own campaign-
finance and political-committee registration requirements. Spot-checks for
the three states most relevant to Anicca:

### California
- Cal. Gov't Code §§ 84200 et seq. (Political Reform Act).
- Any committee that **receives ≥ $2,000 in contributions** in a calendar
  year for political purposes must register with the CA Fair Political
  Practices Commission (FPPC) on **Form 410** within 10 days of crossing
  the $2k threshold.
- Quarterly Form 460 filings if active in CA elections.
- Source: <https://www.fppc.ca.gov/learn/campaign-rules/getting-started-for-committees.html>

### New York
- N.Y. Election Law Art. 14.
- Independent-expenditure committees register with NY State Board of Elections.
- Filings via NYSBOE EFS portal: <https://efs.elections.ny.gov/>

### Texas
- Tex. Elec. Code Ch. 251–254.
- "General-purpose committee" registration with the Texas Ethics Commission.
- Source: <https://www.ethics.state.tx.us/data/forms/coh/coh_forms.htm>

### Recommendation
Engage state-by-state counsel review BEFORE accepting any contribution
or making any expenditure with nexus to that state. The 50-state patchwork
is the real risk surface; federal compliance is the easy part.

---

## Unlock checklist (before this 527 goes LIVE in the politician skill)

Set in `~/.openclaw/.env`:
```
JP_SEIJIDANTAI_REGISTERED=...   # unrelated; for cross-reference only
US_527_FILED=true               # NEW flag — set after 8871 acknowledged by IRS
```

The skill checks `US_527_FILED=true` before allowing 527-tagged entries to
flow into `pac-ledger.jsonl` with `entity_domicile=527`. See
`scripts/lib/ledger.sh::ledger_validate`.

## Open issues for counsel

- Should Anicca operate one combined 527 (issue-advocacy) plus one separate
  Super PAC (independent expenditures) plus one 501(c)(4) (lobbying-eligible),
  or fewer entities?
- Does the parent LLC's profit-seeking nature taint the 527's tax-exempt
  status under the "primary purpose" test? Counsel must review.
- Donor-disclosure exposure for major contributors — what threshold triggers
  state-level disclosure that supersedes the federal $200 floor?
