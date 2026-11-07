# From Cultural Transmission to Comedy: A Research Design for Manager
November 6, 2026 | Unpublished research article draft. No new model, human experiment, competition entry, or efficacy result.

## A shared problem, not a single response label
Gestures, rumors and comedy all involve people interpreting stimuli in a social and cultural context. A shared behavioral model could estimate a conditional distribution over responses given permitted histories, stimulus, delivery, context and relationships. This is a research hypothesis, not evidence that Manager can simulate every response perfectly.

Folklore contributes an essential distinction: a visible motion is not its locally understood meaning. Ethnographic observation and participants' accounts help define what should be measured. A transmitted story may be retold without being believed; a gesture may be copied with a changed interpretation. Prestige, conformity, content and observed success are different candidate mechanisms. Experimental transmission chains and social-network experiments provide precedents [S01–S07]. The book mentioned in conversation as being by Shibata has not been identified; Toru Tsunemitsu's book on gesture folklore is a related verified title, not a confirmed match.

## What existing simulations establish
SOCRATES uses SocSci210, comprising 2.9 million responses from 400,491 participants in 210 experiments. The EMNLP 2025 proceedings report a 36% improvement in distribution alignment over its Qwen base, not 36% individual-response accuracy [S08]. The original interview-agent study of 1,052 people reports performance normalized by humans' own test–retest agreement; its 85% is not raw accuracy across arbitrary behavior [S09]. The July 2026 Nature paper analyzes 469 effects from 70 experiments and 119,330 participants, plus 606 effects from 15 megastudies. High correlations coexist with overestimated effect magnitudes [S10]. These findings motivate empirical work, not universal performance claims.

## Humor as a serious test of response modeling
Laughter detection, pre-response laughter prediction, subjective amusement, preference, judge scores, advancement and tournament victory are separate tasks. A detector that hears laughter is not forecasting an audience before a performance. Individual historical ratings can be more useful than generic demographic or personality descriptions [S12]. Other people's laughter also changes reactions [S13], so a room is not a collection of independent viewers.

Reuse existing benchmarks: UR-FUNNY for multimodal humor-associated segments [S14]; the New Yorker corpus with over 250 million ratings on over 2.2 million captions [S15]; audience-aligned caption ranking [S16]; Oogiri-Master and user-level Japanese Oogiri preference analysis [S17–S19]. The official Oogiri repository licenses its builder code under MIT, not the underlying website content. It explicitly requires checking website terms and copyright before crawling. No crawler was executed for this work.

A 2025 Witscript comparison measured laughter for selected AI and professional jokes before a small live audience [S20]. The absence of a significant difference is not proof of equivalence, universal professional quality or contest-winning ability. Human selection of candidates is part of that workflow and must not disappear from the description.

## Forecasting a tournament is a layered problem
The M-1 2026 entry rules assign two-, three- and four-minute performances to different stages and require at least two comedians [S21]. Documented previous finals distinguish scores from a subsequent top-three vote [S22]. A simulator must pin the year, stage, candidate set, observed versus missing labels and what information was available at forecast time. Future opponents' routines and delivery are unknown scenario variables. Joint event effects create correlated errors across judges and performers. Solo standardized clips remove some interaction variables but do not establish easier R-1 victory or an entitlement to enter an AI performer [S23].

## A falsifiable development path
Start with permitted original short material and specialist baselines. Learn person–stimulus preference with hierarchical or Bradley–Terry models, then compare a shared temporal/multimodal representation. Keep all rewrites, translations and alternative endings from the same routine in the same split. Hold out people, performers, rooms, years and cultural contexts. Measure both future reactions and uncertainty; use untouched audiences for candidate selection tests.

Compare random, human and Manager selection from the same candidate pool under equal production budgets. Freeze generation and ranking before the final audience test. For laughter-focused studies, define a behavioral primary outcome and independently collect amusement, discomfort and autonomy. Do not optimize microphone volume, humiliating laughter or the model's own self-rating. Account for repeated viewers, shared rooms and stimulus dependence; preregister confirmatory analyses and calculate power using pilot estimates rather than equating thousands of ratings with independent participants.

Folklore transmission and humor are applications of existing ManagerBench A–F, not separate products or new universal scores. Phase 9 is the natural next learning step: disjoint evaluation, few-shot adaptation, out-of-distribution uncertainty, negative-transfer tests and shared-model comparisons. Phase 8 implementation and real-world benefit remain incomplete. General simulation is the ambition; independently measured improvements on new people and stimuli are the evidence.

Sources and version/rights audit: [ledger](../masterclass/2026-11-04-p04-causal/CULTURE_HUMOR_SOURCES_20261106.md).
