# Manager BFM-01 / First real-data model comparison card
*Date: 2026-11-05 America/Los_Angeles; 2026-11-06 UTC. Status: executed model pilot, not a released Manager foundation model.*

**Actual publicly inspectable cloud run:** https://github.com/Daisuke134/life-manager/actions/runs/42140073436

## Which weights actually ran?
- **Model**: third-party Qwen/Qwen3-4B-Instruct-2507, GGUF Q4_K_M quantization from bartowski, source SHA256 `2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e`.
- **Inference**: fully loaded into GitHub Actions hosted Ubuntu CPU using verified upstream llama.cpp b12137. Local-only HTTP inference, 12 prompts, deterministic decoding temperature zero; aggregate inference time **61.72s**.
- **NOT RUN**: gated `befm/BeFM1.5-4B` LoRA adapter; Centaur 70B, Be.FM70B, independent complete BehaviorBench model leaderboard, any new Manager general-purpose trained weights, real-world users. The model checkpoint is *not* Manager-owned or newly fine-tuned.

## Real outcome-prediction task
Reuse publicly released Human Behaviour-Change Project trial-arm dataset:
- Original source: https://github.com/HumanBehaviourChangeProject/semantic-prediction ; study paper https://pmc.ncbi.nlm.nih.gov/articles/PMC12603517/
- Real underlying data, 971 annotated smoking-cessation randomized trial arms across 405 reports. Source study-arm dataset is licensed CC0, per primary paper; never upload individual-level participants because no individual-level patient rows are in this corpus.
- Source CSV pinned by SHA256 `eec4ba6ffc51961fda1308f690a97a60111d93858fa67ca19ffd4392fd49679b`.
- Select 16 studies deterministically by a predeclared SHA256 hash of the study identifiers; exclude ALL arms of those studies from training baseline. 937 study arms remain in the train pool. Evaluate a fixed 12 eligible arms from 8 of those selected studies; none of their study IDs appear in the local train pool.
- Prompt contains a selected subset of **coded group-level intervention context / behavior change techniques**, NEVER the target cessation rate, report filename, study ID, or arm ID. Zero generated patients.
- Format asks the LLM to produce a percentage abstinent at reported study follow-up. Prediction rate is not a causal effect of one BCT.
- Baseline uses the **mean outcome of training arms**, not the mean of held-out arms.
- If model output cannot be parsed into a 0-100 rate, predeclare fallback to train mean and count it. Actual invalid generations: **0 of 12**.
- **Crucial limitation**: this is a small test drawn from already-public trial data; possible pretraining contamination is not independently excluded. Variables are reported study annotations, not a prospectively collected real-world feature stream. The selected 12 arms and unadapted prompting are not the official 5-fold HBCP RuleNN protocol.

## Result: one small real-data pilot, NOT a benchmark win

| Fixed local study-disjoint pilot | MAE in percentage points | RMSE in percentage points |
| --- | ---: | --- |
| Train-mean baseline | **6.1418587691** | **8.7018759132** |
| Unadapted Qwen3-4B Q4 | **30.6416666667** | **32.9451438000** |

- Evaluation: 12 published real RCT-arm labels from 8 held-out studies.
- The simple mean beats generic Qwen directly prompted on this sample. It is an observed failure for this **specific** setup, useful for prioritizing behavior-specific adaptation. It is **not** evidence that Qwen fails all behavioral tasks or that Be.FM is inferior.
- This local 12-arm result must NOT be directly compared to the original HBCP RuleNN (MAE 9.15) or our earlier HBCP group 5fold RF (MAE 9.45); splits, questions, models, and evaluation designs differ.
- These MAEs are **absolute prediction errors in smoking cessation rate, percentage points**, not percent accuracy, not treatment effects, not user welfare or clinical benefit.

## Product consequence
- A general language model producing fluent answers is not automatically a useful *quantitative* behavior predictor. We will retain a simple well-calibrated numerical/statistical baseline as a serious competing model and abstain where Qwen is not supported by evidence.
- **Exactly one outstanding current TODO**: complete BFM-01 by running the official gated Be.FM 1.5-4B adapter on a 24 GB cloud GPU under accepted model terms and provider secrets; compare on the **same fixed test cohort and prompt contract**, then integrate only the validated behavior head behind a read-only Model interface and publish the model card. Do not start a separate “next curriculum” task.
- Be.FM API/model access is blocked by HF gated terms (anonymous fetch 401). Modal Starter compute credit is advertised at $30/month with $0 subscription, but there is no connected authorized Modal GPU workspace/secret or accepted model access at the time of this pilot. **Do not bypass access restrictions, commit secrets or spend without an actual provider account/budget.**

## First principles / FAQ
**MAE** = mean absolute error = average of `abs(actual_rate - predicted_rate)` across test intervention arms; lower is better.  
**Study holdout** = no intervention arm from a selected study in the local baseline-training set, unlike row-based random splits.  
**LoRA** = a relatively small trained adapter applied to a base model's weights. Running the base Qwen3 checkpoint does not run Be.FM.  
**Q4** = weights compressed using a 4-bit quantization scheme, not the original BF16 numerical precision.  
**Outcome vs treatment effect** = predicting an arm's cessation rate differs from predicting the counterfactual change caused by an intervention.  
**Q: Did we train a new Behavioral Foundation Model?** No.  
**Q: Is this a valid representative SOTA benchmark?** No, only a real-data smoke/pilot evaluation.  
**Q: What is next?** The *same single BFM-01* task—Be.FM model access/inference, matched heldout comparison, product integration and publication.


## BFM-01 extension: a small genuinely trained **open JSON** outcome head (2026-11-06 UTC)

The 12-arm Qwen4 pilot above was disappointing: unadapted Qwen's numeric outcome error was much larger than an honest train-mean baseline. Instead of assuming a big LLM must win, we **reused** the original HBCP annotated RCT-arm corpus and the repo's pre-existing Ridge/RandomForest baseline evaluator.

Actual model-training and code integration run: https://github.com/Daisuke134/life-manager/actions/runs/42141805282

**Learned model**: `manager-hbcp-ridge-arm-rate-v0`. Fit scikit-learn Ridge on all 971 published study arms (405 reports), with median imputation and missing-value indicators. Exported **142 numerical learned coefficients** plus feature schema and imputation medians to [plain JSON](checkpoints/manager-hbcp-ridge-arm-rate-v0.json). There is no pickle deserialization, no uploaded patient rows, no proprietary model weights. Original HBCP annotated underlying data license: CC0 per the paper.

**Integrity**: exported checkpoint integrity `同梱の manager-hbcp-ridge-arm-rate-v0.manifest.json が記録する重みの SHA256（配布時に検証）`. Independent JSON predictor matches the scikit trained model within `1.7763568394e-14` percentage points on all training arms. The source CSV is pinned by SHA256 `eec4ba6ffc51961fda1308f690a97a60111d93858fa67ca19ffd4392fd49679b`.

**Repeated study-disjoint cross-validation under pinned CPU libraries**: five folds of 405 reports, held out by entire study. The latest complete fixed-environment run found MAE (percentage points) **train mean 10.0048, Ridge 9.2615, RandomForest 9.2130**. The final exported Ridge weights are refit on **all** published arms, so this score is the validation performance of the same **model class/protocol**, not a held-out test of that final refit on future studies. Pin environment: Python 3.11; numpy 2.4.6, pandas 3.1.1, sklearn 1.8.0, scipy 1.17.1. The original HBCP authors' RuleNN 9.15 and our earlier different environment/division outputs must not be treated as identical conditions.

**Manager integration**: [read-only adapter](../manager_core/hbcp_readonly_adapter.py) verifies exact checkpoint SHA256, requires a separately verified **aggregated RCT study-arm** context and at least five recognized coded features, returns a scoped percentage forecast or `ABSTAIN`. It never accepts arbitrary patient identifiers, sends no notification, does not claim clinical recommendation or authorize treatment. Seven adapter contract tests pass. This is not a deployment to real users.

**Status boundary**: a small, domain-specific *trained model head* is now built and has reusable weights. It is **not** a general Behavioral Foundation Model, not evidence that Manager improves behavior, and not Be.FM 1.5-4B or Centaur. No clinical deployment or external authority.

**The one remaining BFM-01 task** remains accepted Hugging Face Be.FM adapter terms + Modal token/credit, run actual Be.FM 1.5-4B inference on the same feature and prompt contract as Qwen3, assess legally licensed heldout human outcomes, and integrate the validated model behind controlled product interfaces. P07-5 is knowledge to be learned when needed, not a second active next task.


### Reproducible checkpoint release gate

The JSON model now exports 142 coefficients with ten-decimal-place serialization, plus a separate committed `checkpoints/manager-hbcp-ridge-arm-rate-v0.manifest.json` containing the exact generated SHA256, provenance digest and a false clinical/intervention authorization flag. The Manager Core adapter checks both files and refuses mismatches. This avoids hardcoding a floating-point BLAS-dependent training digest before release. Numerical libraries are pinned in GitHub Actions, predictions are compared against the original fitted sklearn implementation, and the two files are versioned together on the reviewed PR. This does not grant clinical use or prove BFM generalization.
