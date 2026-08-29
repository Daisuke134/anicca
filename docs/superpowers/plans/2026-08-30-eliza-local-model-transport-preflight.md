# Codex Subscription Transport Preflight Plan

**Goal:** Life Manager forkから、現行loopと同じCodex subscription transportで`gpt-5.6-luna`のstructured callを一回通す。

**Copy source:** legacy Life Managerの`skills/earn/gig/agent-runner/agent_runner.py`と`config.json`。新しいprovider、router、model adapterは作らない。

## 固定条件

- transport: `codex exec --ephemeral --json --output-schema`
- provider/model/effort: `codex` / `gpt-5.6-luna` / `medium`
- auth: 既存Codex subscription profileを既存runnerと同じ方法で利用する。credential値は読出し・複製・receipt保存しない
- exactly one model call。retry/fallback/Terra escalationはC02では0
- OpenAI API key、open model、GPT OSS、ClawRouter、Capafy key、external marketplace effect、CIは0
- output: `{ "ok": true, "agent": "life-manager", "transport": "codex-subscription" }`
- receipt: private mode 0600 `~/.local/state/life-manager/migration/elz-c/model-provider-receipt.json`

## Atomic TODO

- [ ] 1. legacy runnerの実argvとmodel pinをreadbackし、`codex` / `gpt-5.6-luna` / `medium`を固定する
- [ ] 2. forkのLife Manager pluginから既存runner contractを呼べる最小境界だけを接続する
- [ ] 3. `--output-schema`でexactly one real subscription callを実行する
- [ ] 4. result、JSONL、exit 0、provider/model/effort/usageをreadbackする
- [ ] 5. private receiptへcall count 1、marginal API spend 0、external effect 0を保存する
- [ ] 6. focused check一つとbounded adversarial review一回だけ行う。full suite/CI/nitpick reviewはしない
- [ ] 7. receipt PASS後だけspecのC02をDONE、C03をNEXTへ進める

## 完了条件

実際のCodex model callが1回成功し、schema-valid outputとreceiptを再読出しできること。CLIが存在する、auth fileが存在する、またはdry runだけでは完了にしない。
