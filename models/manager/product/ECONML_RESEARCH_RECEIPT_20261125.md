# EconML × Manager: CATE before policy promotion (2026-11-25)

Upstream https://github.com/py-why/EconML/tree/0a42032ece0e6d662d32dc135713422604a8e49e, metalearners source blob 76312a0d5784296793d22508f2d821d32eb10741. MIT (some tree/grf code BSD-3-Clause). TLearner fits separate outcome models and differences predictions. Direct optional EconML backend in script, not an estimator fork. Local package absent; git ls-remote failed DNS. Official package path unexecuted. Reference backend uses existing sklearn clone and outcome models, run completed 5/5 seeds, 3 arms, 30k synthetic rows, 10k heldout. Python 3.13.5, NumPy 2.3.5, sklearn 1.8.0. No API, no human data, no new spend. Command OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python econml_smoke.py --backend reference; --backend econml must be run separately in compatible pinned environment. Output values recorded in JSON receipt.

Research question: distinguish average effect from heterogeneous conditional effect. X ~ N(0,I3), T ~ Bernoulli(.5), tau=.3+.8*x0-.6*x1^2, Y=1+x0+.5*x2+T*tau+N(0,1). Independent train 4000/test 2000 per seed. Cost threshold .1 in synthetic reward units. PEHE is RMSE against known synthetic conditional effect. Oracle regret is mean max(tau-cost,0) minus mean policy*(tau-cost). The mean ATE-only policy chooses no treatment; HGB T-learner learns heterogeneity and treats 40.59% on average. PEHE 1.128679 / .824814 / .488408; regret .247523 / .087866 / .033610 for ATE / linear T / HGB T. No statistical superiority inference or individual observed counterfactual. No human efficacy.

Existing real Hillstrom MG-06 arms already compare S/T learner logistic/HGB on 3 contrasts x 2 outcomes (ops files/eval/mg06/mg06-hillstrom-arms.json); historical womens vs none visit T logreg Qini .07120, CI [.04085,.09539], n=12808. Two of six historical best-arm cells pass stated gate; post-selection caveat. Do not rerun or replace frozen baselines here. No direct numerical comparison with synthetic PEHE.

Product: CATE estimator is a candidate research scorer for Manager, not a trained BFM or deployed policy. Use fixed action/no-action definitions and predecision features, explicit outcomes, randomized assignment / overlap, heldout participants, participant-cluster CI, separate burden/safety and no-action. OBP evaluates frozen policy, BCTO identifies technique; SSR response score is not causal reward. Current app logs need outcome ascertainment. No delivery changes. Next run exact EconML T/S/X and causal forest arms on same existing authorized Hillstrom split, use existing sklift evaluator and no test-based tuning, then independent human prospective evidence. Model, app, public article not released.

## Abstract / blog draft
Personalized interventions require estimating heterogeneous causal effects rather than high baseline success. In a synthetic nonlinear randomized experiment, the HGB T-learner reduced mean PEHE from 1.129 to .488 and oracle policy regret from .248 to .034 versus the ATE baseline. These are engineering checks with known simulated truth, not evidence of Anicca's human benefit. The official EconML package run remains pending. Next compare identical heldout human benchmarks and assess intervention burden.

## Slide source / social copy draft (not posted)
1. Prediction versus causal uplift.
2. Randomized synthetic DGP and heldout split.
3. ATE, linear T and HGB T: PEHE/regret table.
4. BCTO + CATE + OBP + real outcomes, no-send option.
5. Limitations and next official run.
Post: A model that predicts success is not necessarily a model that predicts intervention benefit. Our 5-seed synthetic CATE check tests this distinction. Real human validation and official EconML run are next.
