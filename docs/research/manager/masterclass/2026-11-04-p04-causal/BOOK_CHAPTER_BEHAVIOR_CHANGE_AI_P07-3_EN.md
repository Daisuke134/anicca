# Book draft — From Persuasion to Causal Behavior Engineering
Anicca / Manager, P07-3. 2026-11-06. Scientific research and engineering, not clinical advice.

An intelligent reminder can be flawlessly phrased and useless. Someone may understand the importance of exercise and still lack the necessary time, place, skills or support. A system that diagnoses every failure as low motivation cannot distinguish an environmental constraint from a learned habit. The COM-B framework asks a more precise question: what contribution is being made by Capability, Opportunity and Motivation?

Michie and colleagues introduced COM-B at the center of the Behaviour Change Wheel in 2011. Capability includes physical ability and psychological skill or understanding; Opportunity includes physical and social conditions; Motivation includes reflective goals and automatic processes. These categories support testable hypotheses but are not a validated sensor that reads a human's hidden state.

The field built many behavioral tools before large language models: implementation intentions, self-monitoring, social support, feedback, stimulus control, training and environmental restructuring. The 93 behavior change techniques of BCTTv1 and the Behavior Change Intervention Ontology provide reusable vocabularies. A function (training), a technique (action planning), and a delivery channel (voice or calendar) are different. Their causal contributions must be distinguished.

Minchalle, Duolingo, Finch, Beeminder, stickK and Headspace illustrate different design patterns, but product success is not scientific proof for transplantation into Manager. Peers can encourage or shame; streaks can increase app engagement without building a durable beneficial habit. A careful system actively measures burden, agency and withdrawal.

Suppose a person wishes to meditate for five minutes after dinner. The first question is not which encouragement to send but why the intended action did not occur. A knowledge gap suggests short instruction; a scheduling constraint suggests an opportunity change; a cue problem suggests an implementation intention. Opt-in peer support is another candidate. Doing nothing is an essential option, not an error.

Prediction and intervention cannot be merged by rhetoric. Estimating P(action|history) does not identify P(action|do(intervention),history). A model can predict which people seek coaching and completely misunderstand whether coaching helps them. Causal evidence requires actual randomization or carefully defended identification assumptions. A small factorial experiment could compare If-Then planning, optional peer support and their combination, while measuring behavior, quality of life, guilt, autonomy, and dropout. Network-based peer support requires attention to interference across participants.

A general Behavior Foundation Model will need to transfer representations across people, times, domains and task structures. Before declaring that it exists, compare shared architectures against strong per-task baselines on unseen studies and domains. ManagerBench therefore separates individual choice prediction, state forecasting, group distribution matching, causal effect forecasting, policy safety and real human benefit. Never blend these into a flattering aggregate score before the protocols and weights are specified independently.

In early work, the research team evaluated 269,603 published human choices across five Collins WMH studies and ran participant-separated next-state forecasts for public Hoebeke and Dejonckheere experience sampling datasets. These are real data, but they are not an independently tested general foundation model or clinical proof that rumination is reduced.

The most defensible contribution to the field may be an evaluator that welcomes competitors, discloses negative findings, exposes leakage, respects licenses, and tests the consequences of an intervention rather than the elegance of its suggested words. Long-term scientific value—and any resulting commercial recognition—depends on that discipline.

Sources:
- Michie et al. (2011). https://doi.org/10.1186/1748-5908-6-42
- Michie et al. (2013). https://doi.org/10.1007/s12160-013-9486-6
- Human Behaviour Change Project. https://github.com/HumanBehaviourChangeProject/ontologies
- HeartSteps micro-randomized intervention. https://pubmed.ncbi.nlm.nih.gov/30192907/
- Centaur, Nature 2025. https://www.nature.com/articles/s41586-025-09215-4
- BehaviorBench evaluation. https://github.com/umich-foreseer/behaviorbench_eval
- Detailed methodology: P07-1_JA.md, P07-2_JA.md, P07-3_JA.md.
