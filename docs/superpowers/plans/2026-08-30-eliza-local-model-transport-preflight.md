# Eliza Native Codex SDK Transport Preflight Plan

**Goal:** Eliza既存`@elizaos/plugin-cli-inference`を使い、Life Manager runtimeからCodex subscriptionの`gpt-5.6-luna` structured planner callを一回通す。

**Architecture:** Eliza fixed source `bd24601e…`の`plugin-cli-inference` / `codex-sdk` backendをそのまま使う。新しいrunner、model provider、adapterは作らない。

**Tech Stack:** Eliza AgentRuntime、`@elizaos/plugin-cli-inference`、`@openai/codex-sdk`、system Codex CLI `0.151.0`、`@elizaos/plugin-life-manager`。

**Spec:** `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`

## Upstream evidence

- `plugins/plugin-cli-inference/index.ts`: Eliza `models` map、all-tiers registration、Codex model/effort settings、planner handler
- `plugins/plugin-cli-inference/src/codex-sdk-session.ts`: warm thread、system Codex override、native `outputSchema`、error時thread reset
- `packages/agent/src/runtime/core-plugins.ts`: `@elizaos/plugin-cli-inference`をcore pluginとして収録
- `packages/agent/src/runtime/plugin-collector.ts`: runtimeのplugin解決へ収録
- `plugins/plugin-cli-inference/__tests__/cli-inference.test.ts`: `codex-sdk` backendとall-tiers registration contract

## 固定設定

- `ELIZA_CHAT_VIA_CLI=codex-sdk`
- `ELIZA_CLI_CODEX_MODEL=gpt-5.6-luna`
- `ELIZA_CLI_CODEX_PLANNER_MODEL=gpt-5.6-luna`
- `ELIZA_CLI_CODEX_REASONING_EFFORT=medium`
- `ELIZA_CLI_CODEX_BIN=/Users/anicca/.local/bin/codex`
- `ELIZA_PLANNER_NATIVE_TOOLS=0`
- `ELIZA_CLI_CLAUDE_ALL_TIERS=1`。名称はupstream互換のまま使い、独自renameしない
- `CODEX_HOME`は現行Life Managerのsubscription profileを指す。credential値は読出し、複製、log、receipt保存しない
- C02のmodel callはexactly 1回。retry、fallback、Terra escalation、marketplace effectは0
- GPT-OSS、local open-weight model、OpenAI API key、ClawRouter、Hermes、独自Codex adapterは0

## Atomic TODO

- [x] `C02-01` upstream Codex SDK code pathをprivate evidenceへ保存する — `~/.local/state/life-manager/migration/elz-c/c02/codex-sdk-code-path-evidence.json` mode 0600、source/file SHA再計算一致、model/effect 0
- [x] `C02-02` upstream host inclusionをprivate evidenceへ保存する — `~/.local/state/life-manager/migration/elz-c/c02/codex-sdk-host-inclusion-evidence.json` mode 0600、6 file SHA再計算一致、Local Node auto-enable/Cloud inclusion PASS、runtime/model/effect 0
- [x] `C02-03` isolated runtimeへ`ELIZA_CHAT_VIA_CLI`を設定する — private env exact 1行、backend=`codex-sdk`、mode 0600、SHA readback一致、model/runtime/effect 0
- [x] `C02-04` isolated runtimeへLuna modelを設定する — private env exact 2行、`ELIZA_CLI_CODEX_MODEL=gpt-5.6-luna`、mode 0600、SHA readback一致、planner/runtime/model call/effect 0
- [x] `C02-05` isolated runtimeへLuna planner modelを設定する — private env exact 3行、planner=`gpt-5.6-luna`、mode 0600、SHA readback一致、effort/runtime/model call/effect 0
- [x] `C02-06` isolated runtimeへmedium effortを設定する — private env exact 4行、effort=`medium`、mode 0600、SHA readback一致、binary/runtime/model call/effect 0
- [x] `C02-07` isolated runtimeへsystem Codex binaryを設定する — private env exact 5行、system Codex `0.151.0` path/SHA固定、mode 0600、planner mode/runtime/model call/effect 0
- [x] `C02-08` isolated runtimeへplanner modeを設定する — private env exact 6行、`ELIZA_PLANNER_NATIVE_TOOLS=0`、mode 0600、SHA readback一致、all-tiers/runtime/model call/effect 0
- [ ] `C02-09` isolated runtimeへall-tiers modeを設定する
- [ ] `C02-10` 全text tier registrationを読む
- [ ] `C02-11` ACTION_PLANNER registrationを読む
- [ ] `C02-12` Life ManagerとCLI inferenceを同じruntimeで起動する
- [ ] `C02-13` Luna planner callを一回実行する
- [ ] `C02-14` structured action resultを読む
- [ ] `C02-15` private receiptを保存する
- [ ] `C02-16` adversarial reviewを一回行う
- [ ] `C02-17` receiptをPASSへ更新する
- [ ] `C02-18` C02をDONEへ更新する
- [ ] `C02-19` C03をNEXTへ更新する

## 完了条件

同じEliza runtimeに`plugin-life-manager`と既存`plugin-cli-inference`が各一つあり、`runtime.useModel(ModelType.ACTION_PLANNER, ...)`がsystem Codex経由のLuna structured resultを一回返す。pluginの存在、auth fileの存在、mock、dry runだけでは完了にしない。
