# Manager G0–G3 Zero-UI Research-Only Integration — Design

2026-11-07; owner: Manager research lane; source: Daisuke134/life-manager; no parallel company SSOT.

## Intent
Create a continuously runnable, no-extra-screen, no-per-action-prompt *engineering* foundation for Manager: G0 merge evidence, G1 cross-task benchmark contract, G2 a real trained model artifact, G3 an offline zero-UI shadow that cannot send notifications or reach unauthorized people. This is an honest prototype, **not a universal BFM, live deployment, or invisible intervention system**.

## Product/ethical boundary
No extra Manager UI is a UX decision, not a license to collect data, infer hidden psychological states of nonparticipants, or manipulate people who do not know about the service. Existing legitimate host consent/permission and revocation mechanisms are required for any future personal-data integration, even if no separate Manager account or approval prompt is used. Apple App Review 5.1 requires disclosure and permission for data collection; user choice must be preserved. No covert observation, no unconsented intervention, no unsafe advice. All current demo inputs are public aggregate results or synthetic fixtures; all outputs are NO_ACTION in the real world, no network calls after source import.

## Current software and evidence
- G0 PR #9292 and #9303 merged after green GitHub Actions; Qwen3-4B real GGUF CPU inference, MaMe-Re frozen 24-context eval 10/18 (55.6%) versus historical baseline 11/18 (61.1%), 6 human rating ties.
- products/manager/evals/hbcp_study_disjoint_lightweight.py handles 405 studies, 971 arm aggregates with pinned SHA. Existing held-out 5-fold Ridge MAE 9.925 versus mean 9.987; interval contains zero. Existing manager_core.authority.AuthorityVerifier and StateMachine handle offline authorization and NO_ACTION; owned_provider_shadow.py already implements a bounded public-catalog comparison, so do not copy its provider/private checkpoint implementation.
- Avoid user-specific connected data or Apple Health, production event paths, browser/host secrets, or deployments in this branch.

## Architecture
**G1**: managerbench_v1.py ingests published pinned aggregate result receipts for Nature, MaMe-Re, HBCP and optional official Qwen run. Validate schema, dataset SHA, observation units, holdout labels and finite metrics. Emit ordered per-task rows and stronger-baseline comparisons; prohibit a single global accuracy across incomparable units. CLI accepts file paths so untrusted inputs cannot claim verified provenance without exact hashes.
**G2**: hbcp_train_v0.py reads SHA-pinned public arm data; deterministic **study-disjoint** 70/10/20 train/calibrate/test split, trains regularized linear head with preprocessing fit only on training, evaluates held-out test against train mean, stores JSON weights, transform, source SHA, split IDs/summary and calibration width. It is a genuine model trained from human study aggregates, **not trained Qwen LoRA nor a universal BFM**. No real-user outcome predictions are served.
**G3**: manager_core/zero_ui_shadow_v0.py a **pure offline computation** returning a small privacy-limited receipt. Uses AuthorityVerifier fixture grant within source and checks revocation/scope/expiry. Accepts only public aggregate provenance with adequate group size (>=30), no raw personal identifiers. enabled=False by default; unverified/expired scope returns NO_ACTION. Never initiates host/provider calls, writes, notifications, or irreversible actions. The model_receipt is an existing holdout public arm prediction only, not individualized welfare.
**Ops/docs**: Original Manager SSOT is unchanged except append-only research checkpoint; no new ongoing automation, no public endpoint, no subscriber list, no production integration without separate authorized acceptance.

## Alternatives considered
1. Universal always-on covert engine — technically unbounded, unauthorized, contrary to source/OS permission contracts; rejected.
2. New separate app/UI/manual goal entry — contradicts Zero-UI philosophy; rejected as initial Manager surface.
3. **Existing host integrations with legitimate standing permissions + read-only model evaluation + no-extra-UI shadow** — selected: lowest risk, reuse of existing Core, real evidence and reversible deployment path.

## Acceptance
G0 remote merged receipts; G1 multiple source-backed tasks, no pooled score/leakage and robust schema tests; G2 actual source hash, real held-out train/test, saved inference artifact and reproducible metrics; G3 no UI, no external effect, fail-closed on scope and inputs with fixture tests, no personal data; PR with CI and independent readback. Claims separated: local computation, staged branch, merged main, publicly released product, welfare benefit.
