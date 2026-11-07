# Can an AI Generalize Human Behavior? Manager Phase 9 on Real Research and Humor Data
*November 6, 2026 | Research draft only; not published. No trained universal behavior foundation model or human intervention effect.*

Manager's Phase 9 evaluates not just fit to known human responses but adaptation to new people, entire studies, time periods and cultural settings. A strong model must quantify uncertainty under shift, preserve earlier capabilities when learning new domains, and earn any claim that shared representations outperform task-specific baselines.

We trained and evaluated **small, transparent real-data prediction models** using two previously published aggregate human-response sources: Nature 2026's social-science treatment-effect plot data, and the Japanese MaMe-Re meme humor preference benchmark. These runs did **not** execute new GPT-4, Centaur, Be.FM or OmniSapiens inference.

**P09-2: Few-shot adaptation.** We removed mirrored direction-pairs from Nature's source Figure 1 and held out complete studies. Among 36 studies with at least eight comparisons, the zero-shot calibration model yielded RMSE 0.08154. A regularized five-example residual adaptation lowered it to 0.08026; unrestricted five-example adaptation was worse (0.08478). Nineteen studies improved and seventeen worsened, so average performance does not imply universal improvement.

**P09-3: Calibration under shift.** Splitting studies by publication status—only a proxy for changing conditions—we fit on 24 published studies, calibrated on eight, tested on another eight and compared against 30 unpublished studies. RMSE rose from 0.05244 to 0.08334. Empirical 90%-target interval coverage was 100% and 98.54%, but the interval half-width of 0.24248 made it too broad for strong operational claims. Ordinary conformal guarantees do not automatically survive dependence or distribution shift.

**P09-4: Negative transfer.** We deliberately shared one scalar calibration slope across two incompatible tasks: forecast treatment effects and human meme funniness ratings. Learning the new task increased the old Nature task RMSE from 0.04541 to 0.08452. Equal-task replay partially reduced forgetting but did not match specialist heads. This is evidence about a deliberately undercapacity scalar baseline, **not** catastrophic forgetting in a neural behavior foundation model.

**P09-5: Multiple response domains.** MaMe-Re contains 250 contexts × 400 meme candidates, each pair rated by five people. We split by context ID: 160 training, 40 validation and 50 untouched test contexts (20,000 context–meme pairs). The past candidate rating mean achieved RMSE 0.18460; a newly trained text/description Ridge model reached 0.18469, slightly worse. The paired context bootstrap interval includes zero improvement. More complexity did not improve this outcome.

Results, data hashes and test protocols are saved in the Manager research repository. We used score, context and panel description fields governed by CC BY 4.0, **not** manga images or copyrighted manga dialogue. Nature's original participant RDS and authors' R analysis were not replayed because access required login and the local environment lacked R. No participants were contacted.

Relevant prior work: MAML (Finn et al., 2017), Centaur (Nature 2025), split conformal under non-exchangeability (JMLR 2024), EWC and Learning without Forgetting, PCGrad, Human Behavior Atlas (ICLR 2026), OmniSapiens 2.0 (ICML 2026). The next product step is a rights-cleared and identically evaluated shared encoder versus these real domain baselines, not a premature claim of human-level simulation.

Primary sources: https://www.nature.com/articles/s41586-026-10742-x ; https://github.com/CyberAgentAILab/mame-re ; https://proceedings.mlr.press/v306/ong26a.html .
