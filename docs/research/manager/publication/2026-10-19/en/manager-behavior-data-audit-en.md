# Before Training a Behavioral Foundation Model, Audit the Data, Rights, and Holdouts

**Anicca / Manager Research | November 3, 2026**

The temptation is to generate a million synthetic people, train a larger model, and publish a single impressive accuracy number. But the first question should be much less glamorous: **what exactly is being predicted, which observations are legally usable, and what was genuinely unseen at evaluation time?**

This is not paperwork added after model development. It is what makes a performance claim scientifically interpretable.

## The five layers behind any behavioral prediction

**Source data.** Who actually answered or acted? Under what conditions were records collected? What did the original authors release, and under which rights, consent conditions, and dataset licenses?

**Preprocessing.** How are missing responses, repeat records, eligibility criteria, respondent identifiers, survey weights, and changing question codes handled?

**Prediction-time inputs.** What was the model allowed to know before the outcome? A survey response given after the intervention cannot be used as a feature to predict that same earlier response.

**Model outputs.** Preserve probabilities, raw outputs, refusals, formatting failures, model version and inference conditions. A rejected response is not a correct prediction, and silently dropping it changes the estimand.

**Independent scoring.** Compare with human answers or real outcomes held out in a way that actually tests the intended generalization.

A public **code repository**, a downloadable **survey dataset**, proprietary **model weights**, and a paid **API service** can have four different licensing arrangements. Do not equate access with unlimited training or redistribution rights.

## One experiment: 40 people, 120 rows, two very different evaluations

We generated **fictional** data for 40 people, with three repeated responses per person (120 rows). We ran two train/test split methods using a fixed seed:

| Split | Unique people in train | Unique people in test | People appearing in both |
| --- | ---: | ---: | ---: |
| Randomize the 120 rows | 39 | 26 | **25** |
| Keep each person's three responses together | 30 | 10 | **0** |

The first split may be appropriate for some narrowly defined within-person interpolation tasks, but it does **not** establish performance on a new person. A model could recognize people whose earlier answers were already seen.

If the claim is "predict an unseen person," hold out **people**. If it is "predict an existing user's future," hold out **future time periods** and respect availability at prediction time. For generalization to a new experiment or new business, hold out **studies, conditions or domains**, as appropriate. Each evaluates a different claim.

## Hashes are important, but they are not permission slips

A SHA-256 hash helps identify the exact file bytes used in an analysis:

```python
from pathlib import Path
from hashlib import sha256

raw_bytes = Path("example.csv").read_bytes()
dataset_fingerprint = sha256(raw_bytes).hexdigest()
print(dataset_fingerprint)
```

The fingerprint is useful for provenance and reproducibility. It does **not** certify that the contents are accurate, consented to, unmodified by the source, or licensed for a commercial model.

In particular, [SimBench](https://huggingface.co/datasets/pitehu/SimBench) advertises a noncommercial-sharealike license for its published dataset. The [Ampersand terms](https://ampersand.humansand.ai/terms) restrict competitive benchmarking and competing-model training; a user's API key does not change those terms. The licensing conditions for other source surveys differ.

## What we tested

We implemented an offline teaching example that checks row identity, group holdouts, future-information leakage, source provenance and allowed-use metadata. **Eleven unit tests passed.** These were tests of our synthetic demonstration, not proof of predictive quality for real people.

The larger lesson is that behavior-prediction benchmarks should preserve the entire chain:

```text
License and source
     ↓
Who/what/when was measured
     ↓
Fixed eligibility and preprocessing
     ↓
Train/validation/test split by meaningful unit
     ↓
Recorded prediction inputs and model version
     ↓
Independently observed reference result
     ↓
Error, uncertainty, coverage and limitations
```

## Why this matters for real-world outcomes

A model might predict stated purchase intent well but fail to predict actual payments. A system might improve payments but lower satisfaction or autonomy. Even if it predicts what happened under an action, it has not necessarily identified what **caused** the difference.

Those are separate tasks and deserve separate evaluation. A credible general behavioral intelligence will need human-response data, uncertainty, causal intervention evidence, and independent tests in new situations.

**Takeaway:** The first valuable asset is not the size of the synthetic dataset. It is a trustworthy link between inputs, rights, unseen targets, predictions and outcomes.

## Sources

- [Artificial Societies Benchmark](https://github.com/artificial-societies/artificial-societies-benchmark)
- [SimBench dataset and license](https://huggingface.co/datasets/pitehu/SimBench)
- [Scikit-learn cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html)
- [Harvard Dataverse source example](https://doi.org/10.7910/DVN/SH0F25)
- [Ampersand API terms](https://ampersand.humansand.ai/terms)
