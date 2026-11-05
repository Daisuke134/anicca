# Manager / P07-4 — Psychological Flexibility Is Not a Notification Strategy
*Book and product chapter · 5 November 2026 · Evidence-first; no clinical claims.*

A model can predict that a person will fail to start a task without understanding why that person avoids it. Better prediction may make a system more persuasive, but it does not make the advice useful—or wanted. The natural bridge from a behavioral world model to meaningful assistance is to distinguish the person's actual circumstances and freely chosen values from a system's preferred engagement metric.

## What CBT adds

Cognitive behavioral therapy (CBT) comprises clinical methods for examining relations among thoughts, emotions, behavior, and contextual factors. Behavioral activation (BA), behavioral experiments, and considering alternative interpretations are examples—not universally interchangeable modules. NICE NG222 details appropriate treatment delivery by trained practitioners and guided self-help under structured support. A consumer AI drafting a tiny ordinary-life habit does not become a CBT therapist because it uses a planning idea.

## What ACT adds

Acceptance and Commitment Therapy (ACT), developed within contextual behavioral science, emphasizes **psychological flexibility**—responding flexibly to circumstances while pursuing goals that matter to the person, even when difficult thoughts or feelings arise. It groups six interrelated processes:

1. Acceptance: make room for internal experiences without automatically fighting their existence.
2. Defusion: recognize thoughts as mental events rather than unquestionable instructions.
3. Present-moment awareness: flexibly attend to what is happening now.
4. Self-as-context: take perspective on experiences and personal descriptions.
5. Chosen values: freely choose a direction for action, not an externally imposed streak.
6. Committed action: take feasible, revisable steps in that valued direction.

These constructs describe theoretical processes, not a six-question AI diagnosis. The 2024 treatment-mechanism meta-analysis examined 67 studies involving 9,123 participants. A 2026 review of digital third-wave programs examined 147 randomized trials involving 26,391 participants, with heterogeneity and substantial differences among control conditions. Neither result establishes that our Manager code improves mental health.

## Values, goals, and acts are not the same

**Value:** "I care about curiosity and continuous learning." This is not a metric to complete.

**Goal:** "I want to understand a particular paper." This can be made measurable.

**Tiny action:** "After lunch, read one paragraph for one minute." This is a bounded candidate, not a prescription.

The distinction matters because a system that treats completion streaks or dwell time as the ultimate objective may coerce users into tasks that conflict with their actual life priorities. A useful Manager protects the user's ability to decline, pause, or change course.

## Reuse the existing code; add only the missing permission boundary

The Manager repo already has a paid x402 Habit Designer endpoint that returns Tiny Habits plans, including a safety flag, a proposed tiny behavior, and an implementation intention. Reimplementing its prompt is unnecessary.

The P07-4 bridge adds a *typed, read-only policy gate*:

- It accepts explicit user-chosen value, action, timing, location, and opt-in.
- It checks revocation, availability, a bounded one-to-five-minute duration and a nonclinical scope.
- It can check the existing Habit Designer's `safe_t_flag` as an additional warning, but **never trusts model-generated suggested actions as user authorization**.
- If every condition passes, it returns `DRAFT_ONLY`; otherwise `NO_ACTION`.
- It produces **no** network requests, reminders, financial changes, diagnoses, or clinical interventions.

The software contract was executed as **15/15 unit tests** on free GitHub-hosted CPU, including revocation, missing consent, unsafe URL-like text, clinical requests, model-hallucinated instructions, and the no-notification invariant. This verifies code behavior on synthetic software fixtures. It does **not** validate ACT or CBT treatment efficacy, individual outcomes, or population-level intervention effects.

## The next proof obligation

A future real-product comparison must ask whether this value-aligned choice mechanism improves independently measured *user-chosen* behavior more than existing ordinary planning support, while reporting attrition, autonomy, user burden, missed goals, and adverse consequences. Even a statistically positive step count in an earlier unrelated trial would not prove that this product works.

The one canonical roadmap remains `ROADMAP_STATUS_JA.md`. P07-4 is a learn→implement→test increment, not a replacement for P07-5 Vipassana, P07-6 harm measurement, or P08–P12. Be.FM 4B cloud inference is a different still-open gate in the same Manager product process, requiring model terms and authorized cloud credentials.

## Key vocabulary / FAQ

**Psychological flexibility:** the capacity to choose context- and value-consistent action without treating discomfort as a universal stop signal.

**Defusion:** loosening the automatic rule-giving role of a thought, not deleting it.

**Behavioral activation:** a structured psychological treatment approach focused on activity and avoidance patterns; ordinary habit planning alone is not that treatment.

**NO_ACTION:** a full decision to abstain when the action is unsupported or unwanted.

**Q: Is ACT proven effective for Manager users?** No. Prior clinical research is not a randomized trial of our new module.

**Q: Does a passing test mean the person will change?** No. It means our code obeyed software boundaries under the tested inputs.

**Q: Why no automated notifications?** A generated plan is not an authorization to interrupt; execution permissions and benefits need separate evidence.

## Primary sources
- [Association for Contextual Behavioral Science — About ACT](https://contextualscience.org/about_act)
- [American Psychological Association — ACT](https://www.apa.org/pubs/books/acceptance-commitment-therapy)
- [Mechanisms of flexibility in ACT, systematic meta-analysis, 2024](https://pubmed.ncbi.nlm.nih.gov/38615492/)
- [Process-based ACT in contextual behavioral science, 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11444665/)
- [NICE NG222 — CBT and BA in clinical depression care](https://www.nice.org.uk/guidance/ng222/chapter/recommendations)
- [Digital third-wave interventions: RCT systematic review, 2026](https://pmc.ncbi.nlm.nih.gov/articles/PMC13630215/)
