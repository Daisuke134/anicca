# Manager Cultural Transmission × Humor Response — design extension
Date 2026-11-06. Status DESIGN_ONLY / NOT_RUN / NOT_MEASURED. References: CULTURE_HUMOR_SOURCES_20261106.md. This extends existing ManagerBench A–F, not a new product or execution SSOT. Company cursor remains in the existing unified SSOT; curriculum IDs remain P00–P12. No request to deploy, recruit, notify, crawl or run a model is included.

## Intent and alternatives
Goal: predict context-conditional human responses to original/permissioned stimuli and validate whether choosing stimuli with that prediction increases voluntary enjoyment or explains cultural transmission. Long-term ambition of general human simulation is not a current capability claim.
Three approaches considered: (a) prompt-only LLM personas: fast, but unverified person-level fidelity; (b) specialist cultural/humor models: strong baselines, no shared-generalization claim; (c) shared temporal representation + task/domain heads + hierarchical person adaptation: proposed architecture, accepted only if it beats specialists under fixed compute/input budgets and negative-transfer guards. Start with (a)/(b) as baselines; (c) is a falsifiable model hypothesis.

## Scope and target ontology
CULTURE: exposure, attention, interpretation, belief, imitation, retelling, changed form, later enactment. Keep meaning and physical action separate. Social similarity is not identified peer influence.
HUMOR: laughter onset/duration, self-reported amusement, preference pair, perceived offensiveness, judge score, stage advance, final vote, contest win. Laughter detector F1 is not pre-performance forecast accuracy. Trial assignment, actual exposure and measured response are distinct events.
OUTCOME: voluntary enjoyment and willingness to see more, with adverse experience/autonomy guardrails. No diagnostic or therapy claim.

## Predictive contract
P_theta(Y_i,t:t+h, S_i,t+1 | permitted H_i, stimulus x, delivery d, context c, network G, observed past peer responses).
Record forecast_as_of, input_cutoff, stimulus availability, horizon, model revision and information regime:
A script-only before rehearsal; B standardized rehearsal video; C performance-prefix with strictly pre-outcome peer reactions; D detection after reaction (measurement ONLY).
Never compare A to C/D as if inputs were equal. No scoreboard, applause after punchline, full future video, result article or test-set audience ratings in forecast inputs.
Causal target uses a named comparison and random assignment. Interference means Y_i(A_i,A_neighbors), not only Y_i(A_i); define room/network exposure mapping or randomize groups. Never infer do() solely from an observational response predictor.

## Minimum models and reusable components
1. Baselines: empirical stimulus average, individual mean, regularized logistic/ordinal/mixed-effects model, Bradley–Terry pairwise ranking, simple matrix factorization, general LLM with fixed prompt.
2. Shared model: licensed multimodal/temporal encoder; user and audience latent vectors adapted only from pre-cutoff permitted responses; laughter time-series head; ordinal amusement/score head; transmission and graph head; uncertainty/abstention head. This is a design, not trained BFM.
3. Preference model example: P_i(k preferred to l)=sigmoid(u_i(k)-u_i(l)); random effects for person, stimulus family, performer, session, language/cultural setting. No fabricated judge hidden motives.
4. Generative pipeline: original diverse candidates -> independent response score -> uncertainty/support and rights filters -> bounded selection -> blinded real evaluation. Freeze generator/evaluator versions; do not select on final test outcomes. Retain all generated candidates and selection probabilities when OPE is planned.
5. Reuse existing Oogiri builder / NY caption ranking / UR-FUNNY tasks before adding only missing person-level/pre-response/multicultural evaluations. Code license and data license gate separately. No crawler is run now.

## ManagerBench mapping (no single composite leaderboard)
A: binary choice and pairwise preferences (LogLoss, Brier, calibration, pairwise accuracy).
B: time-indexed reactions (predeclared event windows, onset and duration error, AUPRC for imbalanced events); detector is separately audited against blinded human labels.
C: audience distributions and cascades (distribution discrepancy, heldout calibration, adoption/retelling paths, subgroup performance). Simulated votes are predictions, never ground truth.
D: randomized edits / selection-policy experiments (ITT, CI, missingness, room/stimulus clustering). Shared-context observational differences remain noncausal.
E: safety-constrained candidate selection. Policy value/OPE only under logged verified assignment probabilities and support. Best-known regret in synthetic world is labeled synthetic.
F: actual voluntary enjoyment, burden, harm, autonomy, attendance/return intent and separate commercial outcomes. A contest win does not substitute for D/F replication.

## Evaluation split contract
Split simultaneously by participant and stimulus-family; all alternate endings, paraphrases, translations and rehearsals remain within one family split. No same joke variants across train/test. Hold out performers, venues/sessions, contest years and cultural/language communities separately. Report seen-person/new-stimulus, new-person/seen-stimulus, both-new, few-shot-person adaptation, and new-culture transfer. Preprocessing, clustering, feature selection and hyperparameters fit on train only. Freeze metadata and scoring definitions; public past competitions may be memorized, so prospective unseen routines are the primary contest-like test.
Cultural labels must be justified by language/community/context and participant description, not essentialist demographic stereotypes. Suppress unreliable small-group estimates.

## Study C1: bounded cultural transmission (proposal)
Use a consented adult setting with an original harmless gesture or clearly fictional narrative. Annotate form and participant-defined meaning, observed source, dose, status cue, repeated exposure, reproduction and delay. Example feasibility budget: 24 independent chains of six participants (144 participants), NOT a power-calculated confirmatory size. Chain, not transmission row, is the primary randomization unit. Factorial conditions must be fixed before collection. Use new source stories across conditions, blinded coding, leakage checks and cluster uncertainty. Repeated encounters/control exposures are recorded to distinguish transmission from common exposure. No covert rumor seeding, real-person allegations, manipulation or public propagation. Analysis is exploratory unless powered and preregistered appropriately.

## Study H1: prediction before optimization (proposal)
Use original licensed short performances and opt-in adults. Example feasibility budget: 60 stimulus families, 300 participants, 20 nonrepeating clips each -> 6000 person-clip observations; this does not create 6000 independent people or imply adequate power. Prespecify a dual person/family holdout and tune the assignment matrix so each intended test condition has sufficient coverage. Avoid exposing the same individual to alternative punchlines from the same family. Randomize order, balance delivery, language and performer where feasible. Collect pre-stimulus state minimally, per-clip amusement and offense, optional consented audio/video laughter measurement, and existing-familiarity flag. Measurement reliability/annotator agreement must be assessed separately. Determine confirmatory sample size from pilot variance and participant/stimulus/session correlation, not an arbitrary p threshold.

## Study H2: does model selection improve enjoyment? (proposal)
Compare random selection from the SAME candidate pool, human-expert selection, and Manager selection under matched budget. Add general-LLM selection if relevant. Keep performer, duration, script ownership, recording quality and rehearsal effort comparable. Blind source labels and coders. Use fresh audiences/rooms and untouched joke families. If ranking known jokes and generating new jokes are both tested, use separate estimands. Primary outcome for a laughter-focused experiment: predeclared proportion of consenting viewers with an adjudicated laugh in fixed windows; report normalized laughter duration and private amusement separately. Guardrails: offense/discomfort, social pressure, fatigue and withdrawal. Audio volume alone is not primary benefit. Cluster by room/session and account for stimulus and participant repeated measures. Report ITT and delivery/exposure failures; selection dropout is not a zero.

## Study H3: competition / cultural transfer (proposal)
Freeze ex-ante predictions, timestamp and model hash before exposure/results. Year/round-specific rules adapters. M1 2026 entry: >=2 comedians, 2/3/4min windows; earlier final history: score stage and final votes separate. UNKNOWN for unavailable preliminary scores. Evaluate predicted advancement probabilities, rank and score distributions when observed, final vote probability and calibration across heldout years; one winner is not a sample-size of many independent judges.
Unknown future competitor routines, draw, panel and performance execution are latent scenario variables, not known inputs. Share event-level random effects across contestants/judges. Compare scripted conditional forecast to genuinely before-contest forecast separately. R1-like solo clips reduce some experimental degrees of freedom, not evidence that competition wins become easy. AI-assisted writing and AI appearing as a contestant are distinct eligibility questions. No entry/payment/registration occurs here.

## Schema (proposed)
study_id; participant_pseudonym; consent_scope_version; withdrawal_at; source_rights_manifest; stimulus_id; stimulus_family_id; version; author_permission; performer_id; language; community_context; venue_session_id; network_exposure_map; timestamp; prediction_as_of; feature_cutoff; input_regime; assigned_condition; assignment_probability; exposure_started_at; delivery_status; observed_reaction_window; laughter_annotation; amusement_rating; discomfort_rating; retelling_form; participant_interpretation; belief_rating; judge_score_or_missing; stage_outcome; missing_reason; model_hash; split_id; policy_version; safety_decision. Sensitive participant data never committed to public Git.

## Acceptance gates
G0 primary sources and rights -> G1 measurement and original/authorized stimuli -> G2 preregistered/appropriate ethics and power -> G3 offline baselines and unseen-stimulus prediction -> G4 blinded incremental enjoyment study -> G5 new performer/room/culture replication -> G6 optional public competition under its rules. No fictional results, universal precision or guaranteed wins. All current gates after documentation remain NOT_RUN / rights for data training NOT_CLEARED.

## Existing curriculum mapping
P09-1: person/study/time/domain splits concretized as people/joke families/performers/year/culture.
P09-2: zero-shot/few-shot preference adaptation, hierarchical pooling.
P09-3: calibration, OOD and abstention for unfamiliar audiences/contexts.
P09-4: negative transfer and forgetting; improve humor without degrading original WMH/ESM tasks.
P09-5: same shared model across original domains, culture and humor versus specialist baselines.
P11-2 later deepens agents/networks/institutions. Phase8 theory can precede this study while its implementation remains incomplete. This document is reference design, not a parallel operational TODO.
