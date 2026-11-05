# Cloud L02 Maritime runtime 実行計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 既製runtime一件でSol medium・実ブラウザ・永続diskを動かし、実行証拠と費用を得る。
**Architecture:** 既存Cloud入口・custom worker・台帳を保護し、Maritime公式OpenClawを既存枠内の検証workerとして配置する。独自harness/bridgeは書かない。
**Tech Stack:** Maritime REST / official OpenClaw / existing Capafy-host OpenRouter connection.
**Spec:** docs/superpowers/specs/2026-09-25-life-manager-unified-ssot.md のL02-A〜H（状態の正本）。

## Global Constraints

- private、2GB RAM、1vCPU、5GB disk、auto-sleep。一件だけ作成し、既存worker/モデル/予定/Publisherへ変更しない。
- 外部effectのrequest開始とresource idをprivate既存stateへ永続保存し、uncertain createは再送せず公式GETで照合する。
- 秘密はCredential SSOT→公式secret envのみ。会話/repo/logへ値を出さず、個人Google/Factory専用key/全vaultを使わない。
- OpenRouterの既存日次$3上限を上げない。検証は短い有限call、automatic scheduleなし。新しいplan/有料add-on/credit top-upは行わない。
- Codex UIのmodelを変更しない。旧skillのDeepSeek/Gemini既定は現行specのSol候補より下位。
- 今回はprovider設定と手動acceptanceが対象。新しいproduction logicやmock suiteを追加せず、実callでRED→GREENを確認する。
- source/planはrepoにcommit/push。raw runtime state/secret/receiptは既存private stateに置く。

## Review Focus

- 重複create：externalIdをPOST前後に照合し、通信断で二台目を作らない。
- 費用：既存free/seat契約と新料金表を区別し、model代をVM使用量0へ埋めない。
- 秘密：env取得はkey名とmask flagだけ、公開URLにtokenを載せない。
- 独立性：旧workerをwake/sleep/redeployせず、検証workerだけを操作する。
- 実証：モデル返答、実browser screenshot、/data再読取を別々に記録する。

### Task 1: L02-A〜H の公式runtime acceptance

**Files:** Modify canonical spec only; this plan carries commands/decisions. Provider-owned config lives on the new VM under its persistent mount.
**Consumes:** SSOT maritime.sh API key and capafy-host scoped provider credential; official SDK create/env schema.
**Produces:** one owned agent id, pinned image/version, config model/effort, response/tool/browser evidence, persistence and usage readback.

- [x] GET /api/agents, /api/computers/plan, /api/billing/metered-usage; find exact old worker and available slots. Expected: one old sleeping worker, 3 machine / 1 awake cap; no duplicate new externalId.
- [x] Read official OpenClaw docs and SDK0.11.0 CreateAgentParams/toCreateBody. Read provider key cap and catalogue. Expected: model image/tool support, existing daily cap unchanged.
- [ ] Read-only review this request boundary, then POST /api/agents once with name=lm-cloud-l02-20261105, externalId=lm-runtime-validation-20261105, templateId=openclaw, memMb=2048, vcpus=1, diskGb=5, publicWeb=false; seed only required scoped provider env. Expected: provider id or explicit refusal; save receipt before further calls.
- [ ] Poll GET exact agent until deployed; inspect exec uname/version and /data mount. Expected: official image starts; if image fails, inspect exact deployment failure and choose officially supported image/harness, never a custom wrapper.
- [ ] Read upstream provider config schema for installed version, configure Sol medium using native OpenClaw config. Expected: native provider/model/effort readback, no secret values printed.
- [ ] Run short Responses text/tool and image calls from the same VM. Expected: model id, medium effort, success response and image observation; preserve refusal as diagnostic boundary.
- [ ] Ask OpenClaw to use its browser on https://aniccaai.com/lm, take screenshot and report observed title/CTA. Expected: actual browser tool result + screenshot, not model-only prose or HTTP HTML fetch.
- [ ] Write a nonsecret marker under /data; sleep/start only the new worker, then read marker/profile location. Expected: same marker after resume.
- [ ] Read resource/usage/provider cost and old worker state; summarize evidence in canonical spec and advance only when all acceptance steps pass. Expected: no old-worker mutation, no signup/sale claimed from readiness checks.

Self-review: one bounded provider-configuration task; no cross-task interfaces or new application code. Current execution cursor is canonical L02-C.
