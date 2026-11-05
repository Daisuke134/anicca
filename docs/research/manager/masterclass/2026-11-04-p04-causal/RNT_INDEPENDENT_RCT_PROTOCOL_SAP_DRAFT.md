# Independent RNT evaluation — protocol and statistical analysis plan

Version 0.1, 2026-11-06. INTERNAL DRAFT. NOT REGISTERED, NOT ETHICS-APPROVED, NO RECRUITMENT, NO PARTICIPANTS, NO OUTCOMES. This is not a claim of independent clinical review.

## Question and scope
Does a frozen Manager self-care support package reduce repetitive negative thinking at four weeks compared with attention-matched general wellbeing information? This comparison estimates the effect of the whole package, not AI personalization alone. A later fixed-versus-adaptive-policy comparison must hold content and opportunities constant to isolate adaptation.

## Design
Proposed parallel 1:1 individually randomized trial, four weeks of support and follow-up at eight weeks. Adults 18+ using an appropriately validated-language PTQ and reporting bothersome RNT are a candidate population. Final eligibility and safeguarding exclusions require qualified independent review. Do not improvise a PTQ diagnostic cutoff. No peer-network intervention in this first trial, to avoid unmodeled interference.

An independent team must control allocation and masked A/B outcome analysis. Participants cannot be assumed blinded. Any stratification variables, block scheme and allocation concealment mechanism must be finalized before registration. Manager must not generate its own primary outcomes. A second AI reviewer does not constitute an independent investigator or clinical assessor.

## Intervention and comparator
Freeze model/provider revision, prompts, approved self-care content, decision rules, dose, stop rules and delivery channels before randomization. The initial dose proposal is at most one proactive suggestion per day, with quiet hours, skip, withdrawal and no-action options. This is not autonomous clinical psychotherapy. The comparator offers general wellbeing information through comparable contact and measurement schedules. Match attention as far as practical and measure expectations; do not advertise one arm as superior.

Authorized delivery, burden and fidelity are recorded separately from benefit. No covert psychological manipulation, unconsented third-party contact, financial penalties, or medication changes. Independent reviewers must assess the content and contraindications before launch. Ordinary clinical care remains available and is recorded rather than replaced.

## Outcomes and schedule
Primary: PTQ total at day 28 (proposed window ±3 days), adjusted for baseline PTQ and any prespecified allocation strata. PTQ is a 15-item RNT scale (0–60 in its original scoring), not a diagnostic test. Japanese RTQ is a distinct questionnaire: do not relabel it PTQ or invent a Japanese translation and call it validated. A Japanese trial needs verified psychometric and use-permission suitability and an amended protocol before enrollment.

Secondary: PTQ at day 56 (proposed ±7 days), everyday interference, distress, chosen-action completion, burden, unwanted contact, guilt, autonomy, dropout, and adverse experiences. Exploratory daily self-report items are not claimed as a validated scale. Fix instruments, schedules, scoring and clinically meaningful thresholds before registration. Do not substitute app-open rate for wellbeing.

## Planning sample size
The separate reproducible script uses statsmodels TTestIndPower for two equal independent groups, two-sided alpha .05, power .80. No gain from baseline adjustment is assumed. At assumed d=.35, n=129.112 per analyzable arm, conservatively rounded to130, then divided by .80 retention and rounded to163 randomized per arm: total326. Sensitivity: d=.30 →440 total; d=.40 →250 total. These are hypothetical planning assumptions, not observed Manager effects or established clinically important differences. Feasibility and independent oversight may require a pilot and revised registered design.

## Estimand and analysis
Primary estimand: intention-to-treat treatment-policy contrast in week-4 PTQ under assignment to the two packages in the enrolled population. Analyze by randomized group despite nonuse, where outcome collection is consented. Primary model: ANCOVA with baseline PTQ and frozen stratification terms; robust standard errors, effect estimate and 95% confidence interval. Lower scores are better; explicitly state the contrast direction. One primary endpoint, two-sided alpha .05. Secondary/exploratory findings must not be upgraded to primary success. Do not stop early based on repeated unadjusted significance tests.

Candidate missing-data strategy: multiple imputation under MAR, 50 imputations, using prespecified baseline and outcome predictors; the exact model must be frozen before registration. Report missingness by arm, complete-case sensitivity and prespecified MNAR delta/tipping analyses. No last-observation-carried-forward default, no coding missing outcomes as zero or as treatment success. No efficacy claim from a within-arm before–after difference alone.

## Safety, independence and data governance
Independent investigators must set adverse-event definitions, deterioration rules, reporting timelines, pause criteria and escalation services. No actual clinical team or 24-hour response service has been secured; do not claim one exists. Participants need genuine informed consent, withdrawal, appropriate care/referral information, data minimization, retention/deletion rules and clear AI limitations.

A qualified independent team—not the product generation system—must oversee consent, outcomes, harm evaluation and analysis. Roles, conflict disclosures, budget and contracts are not yet secured. Participant-level data must never enter the public GitHub repository. Store deidentified study records in an approved controlled environment with access logs and a separate linkage key. Log frozen content/model versions and execution receipts without unnecessary sensitive text.

## Registration and launch gates
Before recruitment: final protocol/SAP, independent responsible team, funded site, ethics review, consent materials, validated measurement, data-management and safety plans, randomization setup, preregistration, and software/fidelity validation. All are currently unresolved or draft-only. Company autonomy does not waive research governance.

For a Japanese study, confirm the guidance in force at the actual start date. The MEXT page lists an amendment announced August 27, 2026 with effective date December 1, 2026; do not treat it as already effective on November 6. Jurisdictional applicability requires institutional review, not inference from a product roadmap.

Report regardless of favorable or unfavorable findings using applicable SPIRIT 2025 and CONSORT 2025 guidance. Register before recruitment, and disclose amendments with dates and reasons. No actual registration ID, trial results or ethics number exists for this draft.

## Sources
PTQ: https://pmc.ncbi.nlm.nih.gov/articles/PMC3042595/
Japanese RTQ: https://doi.org/10.4092/jsre.21.65
SPIRIT: https://www.bmj.com/content/389/bmj-2024-081477
CONSORT: https://doi.org/10.1136/bmj-2024-081123
MEXT: https://www.mext.go.jp/a_menu/lifescience/bioethics/seimeikagaku_igaku.html
