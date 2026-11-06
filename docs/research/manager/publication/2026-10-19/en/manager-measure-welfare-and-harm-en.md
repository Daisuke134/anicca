# The Real Benchmark of Behavior-Change AI Is Human Benefit—and Harm

*Introducing Manager · November 5, 2026 · P07-6*

An app doubles someone's meditation minutes. Its engagement dashboard looks excellent. Does that mean the person is better off?

Not necessarily. A longer practice period can coincide with poor sleep, guilt, work impairment, unwanted experiences, or loss of autonomy. The product goal must be **what the person actually wanted**, accompanied by independently measured benefits and harms—not time spent with the product.

## Five separate evaluation layers

| Layer | What we measure | What it does not prove |
|---|---|---|
| Prediction | Choice, state, log loss, Brier score and calibration | Causal benefit from acting |
| Behavior | Verified user-chosen action and completion opportunities | Overall well-being |
| Welfare | Well-being, functioning and distress | Spiritual liberation |
| Autonomy | Opt-in, refusal, burden and revocation | Value in forced compliance |
| Harms | Sleep disruption, distress, impairment, unwanted experiences | Safety merely because complaints are absent |

## Reuse, don't reinvent, validated measures

The [WHO-5](https://www.who.int/publications/m/item/who-ucn-msd-mhe-2024.01) measures self-reported well-being over the past two weeks with five response values; it scores from 0 to 100 by multiplying their 0–25 sum by four. But the 2024 WHO published instrument carries a **CC BY-NC-SA 3.0 IGO** document license. A commercial app must check permissions rather than copying the questionnaire into product screens.

[WHOQOL-BREF](https://www.who.int/toolkits/whoqol/whoqol-bref), [PROMIS Global Health](https://healthmeasures.net/select-measures/recommended-measures/global-health-profiles/), FFMQ mindfulness dimensions, PTQ repetitive negative thinking, and MedEx-I meditation-related experiences answer **different** measurement questions. Their instruments, languages, validity evidence and licensing cannot be treated as interchangeable.

Manager's initial 0–10 internal burden and autonomy fields are **unvalidated monitoring variables**, not substitutes for authorized questionnaires.

## The risk studies that product teams should read

A [2020 systematic review](https://pubmed.ncbi.nlm.nih.gov/32820538/) of 83 studies and 6,703 participants reported a pooled adverse-event estimate of 8.3%, with very different estimates for experimental and observational studies (3.7% versus 33.2%).

[Lindahl et al. 2017](https://pmc.ncbi.nlm.nih.gov/articles/PMC5443484/) catalogued 59 kinds of meditation-related experiences across seven domains; experiences with similar descriptions could be helpful, distressing, or functionally impairing depending on person and context.

In a [2022 MedEx-I study](https://pmc.ncbi.nlm.nih.gov/articles/PMC8845498/), active questioning of 96 participants found negative functional impacts for 37%. A [2025 survey of 886 U.S. meditators](https://journals.sagepub.com/doi/full/10.1177/21677026241298269) reported meditation-related functional impairment in 9.1%.

These numbers **cannot be averaged into a single universal risk**. Definitions, sampling, intensity, follow-up, and active versus passive questioning differ. A product should not conclude “no harm” just because users did not spontaneously submit complaints.

## The code we built

P07-6 adds a strictly nonclinical, read-only `OutcomeObservation` and `assess_welfare` decision boundary to Manager. It treats consent, revocation, self-chosen behavior, functioning, autonomy, reported burden, distress, sleep interruption, and impairment as distinct variables.

It can return `MEASURE_ONLY`, `NO_ACTION`, `STOP`, or `STOP_AND_REFER`. The last status is a **need to stop and present appropriate support options**, not an autonomous contact with a clinician. It makes no intervention, and thresholds are **engineering safeguards—not validated diagnostic cutoffs**.

A WHO-5 numeric scoring helper refuses use by default until appropriate rights are confirmed. No copyrighted items are embedded.

And in response to a real failure in the first HeartSteps audit, the code explicitly separates randomized assignment from post-assignment delivery status, preserving a `NOT_ITT` label when missing outcomes or the estimand require greater care.

## A scientifically credible comparison

A model predicting tomorrow's behavior is not the same as a model predicting the **increment caused by an intervention**.

In randomized trials, intention-to-treat (ITT) compares people or decision points according to their original random assignment, not simply whether a message was delivered or opened. Missing outcomes, interference among people, changes in the outcome definition and departures from the protocol must all be examined.

Manager should preregister the primary user-chosen outcome, comparison, follow-up and safety guardrails, and publish negative findings and attrition alongside wins. Evidence that earlier researchers' interventions worked does not show that Manager's own product helps users.

### Terms and FAQ

**Outcome:** a measurement following an intervention.

**Adverse event:** an unwanted experience; causal attribution requires separate assessment.

**Functional impairment:** disruption to everyday life.

**ITT:** analysis based on original randomized allocation.

**Autonomy:** the person's real ability to decline and revoke support.

**Psychometric validity:** evidence that a scale measures its intended construct.

**Q: If WHO-5 improves, has a user attained Buddhist liberation?** No. Self-reported well-being and traditional enlightenment are different constructs.

**Q: Is all temporary discomfort a harm?** No, but duration, distress, functional impact and the person's own preference matter. Harm should never be dismissed as necessary progress.

**Q: Does a passing software test prove Manager makes people healthier?** No. It verifies only the tested boundary under synthetic inputs.

See the [detailed P07-6 source guide](https://github.com/Daisuke134/life-manager/blob/main/docs/research/manager/masterclass/2026-11-04-p04-causal/P07-6_JA.md).

**The standard for Manager is usefulness in life outside the benchmark, with uncertainty and harm measured honestly.**