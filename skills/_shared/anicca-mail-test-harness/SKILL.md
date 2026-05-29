---
name: anicca-mail-test-harness
description: Anicca が自分自身の mail-auto-reply skill を E2E test する harness。 test-cases/ に 35 case (7 category) の YAML を置き、 各 case で test mail を 自分宛に投函 → heartbeat 起動 → expected outcome 検証 → test-report-{TS}.json 出力。 全 pass + 1 週間実 mail 誤判定 0 件 で Phase 1 完了。 spec §13-15 cite。
version: 0.1.0
metadata:
  tags: mail, e2e, test, harness, autonomous, iteration-loop
  requires:
    bins: [bash, gog, python3, jq]
    services: [gog gmail OAuth, heartbeat-beat.sh, slack-bridge]
    env: [SLACK_BOT_TOKEN, GOG_ACCOUNT]
---

# anicca-mail-test-harness

Anicca 自走で mail-auto-reply の 35 test case を回す E2E test harness。

## Citations

- spec: `/Users/anicca/anicca-project/.cursor/plans/anicca-autonomous-action-agent-spec.md` §13-15 (35 cases · A-G category)
- inspiration: `agents-from-scratch/notebooks/evaluation.ipynb` (LangSmith eval pattern)
- inspiration: `inbox-zero/.test.ts` (per-function test pattern)
- vellum Trust Ladder Stage 0 (flag-only default) — `~/.research/.../vellum/skills/inbox-management/SKILL.md:32-45`

## Structure

| Path | Purpose |
|------|---------|
| `test-cases/` | YAML files · 1 per case · 35 total at Phase 1 |
| `lib/evaluate-<a-g>.sh` | category-specific verification logic |
| `lib/send-test-mail.sh` | gog gmail send wrapper (self → self) |
| `reports/test-report-{TS}.json` | 各 run の結果 |
| `run.sh` | entry point — 35 case 順次 (or parallel) 実行 |

## YAML Schema (= 各 test-cases/*.yaml)

```yaml
id: TC-A1
category: silent_archive    # silent_archive | notify | reply_imagine | reply_action | ask_dais | reject | long_running
name: "FIX-TEST promo from self"
input:
  from: "${OSS_TEST_RECIPIENT}"
  to: "${OSS_TEST_RECIPIENT}"
  subject: "🎁 EXCLUSIVE OFFER - Weekend Sale 50% off"
  body: |
    Don't miss our exclusive offer. Limited time only!
expected:
  triage4: "no"
  archive: true
  reply: false
verify:
  - type: gmail_label
    thread_query: "subject:\"Weekend Sale\" newer_than:1h"
    label: "INBOX"
    expect_absent: true
  - type: not_replied
    thread_query: "subject:\"Weekend Sale\" newer_than:1h"
```

## Usage

```bash
# 全 35 case 実行
bash $ANICCA_HOME/skills/_shared/anicca-mail-test-harness/run.sh --all

# 特定 category のみ
bash run.sh --category A

# 特定 case のみ (debug)
bash run.sh --case TC-A1 --dry-run
```

## Iteration Loop (§15 cite)

```
while [ "$(jq .fail reports/latest.json)" -gt 0 ]; do
  bash run.sh --all
  # fail があれば Anicca が自走で root cause 解析 + fix
  # Round 1-6 escalation (HEARTBEAT.md §7.1)
done
```

## Phase 1 完了条件

- 35/35 pass
- 1 週間連続実 inbound mail 誤判定 0 件
- TC-D1 (Uber resubmit) で view-online verify pass
- .learnings/LEARNINGS.md に解決 pattern 5 件以上
