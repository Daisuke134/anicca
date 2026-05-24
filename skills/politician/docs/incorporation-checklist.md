# Incorporation checklist

Step-by-step {{profile.lateness.stakeholders.senderType}}-shell formation for the four-entity stack (Delaware LLC + 527 + Super PAC + 501(c)(4)) plus the Japan 政治団体. All fees and deadlines reflect 2026-05 conditions; verify on each authoritative site before filing.

> **Disclaimer.** This is a checklist, not {{profile.lateness.stakeholders.senderType}} advice. Use it as the structure for your conversation with counsel. The skill captures `politician.counsel_{{profile.lateness.stakeholders.channel}}` for that reason — every step here should be reviewed by an attorney before filing.

---

## US side

### 1. Delaware LLC — operating company

- **Name.** Choose one matching `politician.de_llc_name`. Recommended: `Anicca AI Politics LLC`.
- **Registered agent.** Required. Options:
  - Stripe Atlas — bundled with EIN + agent (≈$500 one-time).
  - LegalZoom — agent-only ≈$299/yr.
  - Northwest Registered Agent — ≈$125/yr (lowest cost).
- **Filing.** Delaware Division of Corporations, Certificate of Formation. Fee: **$110**. Online: https://corp.delaware.gov/
- **EIN.** Apply at https://www.irs.gov/businesses/small-businesses-self-employed/apply-for-an-employer-identification-number-ein-online — free, instant.
- **Operating agreement.** Single-member LLC, manager-managed. Counsel drafts.
- **Bank.** Mercury or Brex. Mercury preferred (no min balance, fast onboarding).
- **Stripe account.** Add the LLC EIN. This is the source for the `STRIPE_API_KEY_PAC` sweep.

### 2. Section 527 organization

- **Name.** Default: `Anicca for Sentience 527`.
- **IRS Form 8871.** "Notice of Section 527 Status." File electronically within **24 hours of formation**. Fee: **$0**. URL: https://www.irs.gov/charities-non-profits/political-organizations
- **IRS Form 8872.** "Report of Contributions and Expenditures." Quarterly during election year, semi-annually otherwise. Fee: **$0**.
- **Bank.** Separate account from LLC, in 527's name + EIN.

### 3. Independent-Expenditure-Only Committee (Super PAC)

- **FEC Form 1.** "Statement of Organization." File within **10 days** of registering as a political committee. Fee: **$0**. URL: https://webforms.fec.gov/webforms/form1/
- **Name.** Default: `Anicca for Sentience Super PAC`.
- **Treasurer.** Required NATURAL PERSON. Must be filled in `humans.yaml: treasurer` before this step. (See `hiring-roster.md`.)
- **Bank.** Amalgamated Bank — preferred bank for progressive Super PACs; experienced with FEC compliance. Account in committee name + FEC ID.
- **Independent-expenditure pledge.** Must include the Carey-Committee-style language disclaiming coordination with candidate campaigns.
- **FEC Form 3X.** Annual or quarterly receipts/disbursements report. Fee: **$0**. Auto-prepared by `fec_reporter.sh` after `PAC_FORMED=true`.

### 4. 501(c)(4) — social welfare arm (optional, defer until v0.5)

- **IRS Form 1024-A.** "Application for Recognition of Exemption Under Section 501(c)(4)." Fee: **$600**. URL: https://www.irs.gov/forms-pubs/about-form-1024-a
- **Purpose.** Issue advocacy outside electoral activity. Useful for the bill-drafting + grassroots education work that doesn't directly support candidates.
- **Filing window.** Within 60 days of formation under IRC §506. URL: https://www.irs.gov/charities-non-profits/other-non-profits/section-501c4-organizations

### 5. LDA registration — separate from entity formation

- **LD-1 Registration.** Filed by the registered lobbyist, not by the firm. Threshold: ≥$14,000 quarterly client revenue + 20% lobbyist time + 2+ contacts. Fee: **$0**. URL: https://lda.congress.gov/LD/help/Default.htm?Form=LD-1
- **LD-2 Quarterly.** Auto-prepared by `lda_filer.sh` after `LOBBYIST_HIRED=true`.
- **LD-203 Semi-annual.** Contributions report (separate from LD-2). Counsel reviews.

---

## JP side

### 6. 政治団体 (まずは諸団体として届出)

- **届出先.**
  - 国会議員関係政治団体 → **総務省**.
  - その他（国政・都道府県政・市町村政）→ **都道府県選挙管理委員会** または **総務省**.
- **必要書類.**
  - 政治団体設立届
  - 規約
  - 代表者・会計責任者の確認書類（住民票写し）
- **手数料.** **¥0**（届出制）。
- **代表者・会計責任者・職務代行者** の3名（natural persons、日本国籍要）が必要。`humans.yaml` の jp_seijidantai_daihyo / jp_kaikei_sekininsha / jp_shokumu_dairisha を埋めること。
- **銀行口座.** 政治団体名義で開設（みずほ・三菱UFJ・りそな等）。設立届の写しが必要。
- **収支報告書.** 翌年 5 月末までに前年分を提出。`jp_shushihokoku.sh` が自動準備。

### 7. 国会議員関係政治団体への移行（任意・後段）

- 国会議員（または同候補者）と整合する政治活動を行う場合に必要。総務省直轄。
- 移行は政治団体設立から後で可。

---

## Total cost & timeline

| step | fee | timeline |
|---|---|---|
| DE LLC + agent + EIN | ~$235–$610 | 1–3 days |
| 527 (Form 8871) | $0 | same day |
| Super PAC (Form 1) | $0 | 10-day window |
| 501(c)(4) (Form 1024-A) | $600 | 90–180 days IRS review |
| 政治団体 設立届 | ¥0 | 即日〜数日 |
| **subtotal** | **~$835 + ¥0** | **2–4 weeks for active state** |

The 501(c)(4) is optional in v0.1 — defer until after first bill drafted.

---

## Sequencing note

The minimum stack for v0.1 to flip from DRY to LIVE on the action crons:

1. DE LLC + EIN + Stripe.  → unlocks `stripe_pac` sweep math.
2. Super PAC (Form 1) + treasurer hire + Amalgamated account.  → unlocks `fec_reporter` + `stripe_pac` LIVE.
3. LDA-registered lobbyist hire + LD-1 filing.  → unlocks `lda_filer` LIVE + {{profile.lateness.stakeholders.channel}}-send to staffers.
4. 政治団体 設立届 + 代表/会計/職務代行 hire.  → unlocks `jp_shushihokoku` LIVE.

Each unlock corresponds to one env flag in `.env`:

```
PAC_FORMED=true                  # after step 2
LOBBYIST_HIRED=true              # after step 3
JP_SEIJIDANTAI_REGISTERED=true   # after step 4
POLITICIAN_DRY_RUN=false         # global LIVE switch — flip last
```
