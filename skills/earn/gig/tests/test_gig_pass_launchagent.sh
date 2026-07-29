#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
PLIST="$ROOT/skills/gig-work/launchd/ai.anicca.hf-gig-pass.plist"
AUDITOR_PLIST="$ROOT/skills/gig-work/launchd/ai.anicca.hf-gig-auditor.plist"
REGISTRY="$ROOT/config/launchd/agents/gig.json"
README="$ROOT/README.md"
LAUNCHER="/Users/anicca/profitable-claude/skills/gig-work/scripts/launch_gig_worker.sh"

test -f "$PLIST" || { echo 'canonical gig pass LaunchAgent missing'; exit 1; }
plutil -lint "$PLIST" >/dev/null
plutil -lint "$AUDITOR_PLIST" >/dev/null
test "$(plutil -extract Label raw -o - "$PLIST")" = 'ai.anicca.hf-gig-pass'
test "$(plutil -extract ProgramArguments.0 raw -o - "$PLIST")" = '/bin/bash'
test "$(plutil -extract ProgramArguments.1 raw -o - "$PLIST")" = '/Users/anicca/profitable-claude/skills/gig-work/scripts/run_with_cdp_lock.sh'
test "$(plutil -extract ProgramArguments.2 raw -o - "$PLIST")" = 'gig-pass'
grep -q "$LAUNCHER" "$PLIST"
test "$(plutil -extract StartCalendarInterval.0.Minute raw -o - "$PLIST")" = '0'
test "$(plutil -extract StartCalendarInterval raw -o - "$PLIST" | jq 'length')" = '1'
test "$(jq -r '.agents["ai.anicca.hf-gig-pass"].schedule.type' "$REGISTRY")" = 'calendar'
test "$(jq -c '.agents["ai.anicca.hf-gig-pass"].schedule.minutes' "$REGISTRY")" = '[0]'
test "$(jq -r '.agents["ai.anicca.hf-gig-pass"].model_call_limit_per_pass' "$REGISTRY")" = '7'
test "$(jq -r '.agents["ai.anicca.hf-gig-pass"].b2_model_call_limit_per_pass' "$REGISTRY")" = '40'
test "$(jq -r '.agents["ai.anicca.hf-gig-pass"].b2_min_new_inspections_per_attempt' "$REGISTRY")" = '12'
# X18: the plist is the value that actually binds. The shell default was raised to 4, but
# a plist still exporting 1 would override it and the loop would keep running one lane a
# waking while every test claimed otherwise -- a change that looks shipped and does
# nothing. Assert the env the LaunchAgent really sets, not just the registry note.
test "$(plutil -extract EnvironmentVariables.GIG_MODEL_CALL_LIMIT raw -o - "$PLIST")" = '7'
test "$(plutil -extract EnvironmentVariables.GIG_B2_MODEL_CALL_LIMIT raw -o - "$PLIST")" = '40'
test "$(plutil -extract EnvironmentVariables.GIG_B2_MIN_NEW_INSPECTIONS raw -o - "$PLIST")" = '12'
test "$(plutil -extract EnvironmentVariables.GIG_PASS_WALL_CLOCK_LIMIT_SECONDS raw -o - "$PLIST")" = '3480'
test "$(plutil -extract EnvironmentVariables.GIG_PASS_FINALIZE_RESERVE_SECONDS raw -o - "$PLIST")" = '120'
test "$(plutil -extract EnvironmentVariables.GIG_B2_MIN_INVOCATION_SECONDS raw -o - "$PLIST")" = '600'
test "$(jq -r '.agents["ai.anicca.hf-gig-pass"].wall_clock.pass_limit_seconds' "$REGISTRY")" = '3480'
test "$(jq -r '.agents["ai.anicca.hf-gig-pass"].wall_clock.finalize_reserve_seconds' "$REGISTRY")" = '120'
test "$(jq -r '.agents["ai.anicca.hf-gig-pass"].wall_clock.b2_min_invocation_seconds' "$REGISTRY")" = '600'
# Daily limits are circuit breakers, not throttles: they must sit well above
# normal spend so they only fire on a runaway. Production pass 1785282568-41648
# spent 554,962 charged tokens across seven calls and was still only 1/4 while
# live sources had next pages. The B2 volume ceiling is forty calls, so the pass
# breaker is 4,194,304 and the daily breaker is 33,554,432. Raw telemetry totals
# include cached input reads and are not the budget unit.
# Each owner gets its own daily pool via ANICCA_BUDGET_DAILY_SCOPE, because a
# single shared "gig" pool let the auditor's 262144 limit be evaluated against
# the revenue pass's spend and dead-blocked the auditor every day.
test "$(plutil -extract EnvironmentVariables.GIG_PASS_TOKEN_BUDGET raw -o - "$PLIST")" = '4194304'
test "$(plutil -extract EnvironmentVariables.GIG_DAILY_TOKEN_BUDGET raw -o - "$PLIST")" = '33554432'
test "$(plutil -extract EnvironmentVariables.GIG_BUDGET_DAILY_SCOPE raw -o - "$PLIST")" = 'gig-pass'
test "$(jq -r '.agents["ai.anicca.hf-gig-pass"].token_budget.pass_tokens' "$REGISTRY")" = '4194304'
test "$(jq -r '.agents["ai.anicca.hf-gig-pass"].token_budget.loop_daily_tokens' "$REGISTRY")" = '33554432'
test "$(jq -r '.agents["ai.anicca.hf-gig-pass"].token_budget.daily_scope' "$REGISTRY")" = 'gig-pass'
test "$(jq -r '.agents["ai.anicca.hf-gig-pass"].token_budget.circuit_breaker_exit' "$REGISTRY")" = '75'
test "$(plutil -extract EnvironmentVariables.GIG_AUDIT_TOKEN_BUDGET raw -o - "$AUDITOR_PLIST")" = '32768'
test "$(plutil -extract EnvironmentVariables.GIG_DAILY_TOKEN_BUDGET raw -o - "$AUDITOR_PLIST")" = '262144'
test "$(plutil -extract EnvironmentVariables.GIG_BUDGET_DAILY_SCOPE raw -o - "$AUDITOR_PLIST")" = 'gig-auditor'
test "$(jq -r '.agents["ai.anicca.hf-gig-auditor"].token_budget.pass_tokens' "$REGISTRY")" = '32768'
test "$(jq -r '.agents["ai.anicca.hf-gig-auditor"].token_budget.loop_daily_tokens' "$REGISTRY")" = '262144'
test "$(jq -r '.agents["ai.anicca.hf-gig-auditor"].token_budget.daily_scope' "$REGISTRY")" = 'gig-auditor'

# The reply detector runs a composition model call every 300s on its own timer,
# outside any pass. Before X20 it exported no budget env at all, so every one of
# those calls recorded budget_not_configured and was never charged.
DETECTOR_PLIST="$ROOT/skills/gig-work/launchd/ai.anicca.hf-gig-reply-detector.plist"
plutil -lint "$DETECTOR_PLIST" >/dev/null
test "$(plutil -extract EnvironmentVariables.GIG_REPLY_PASS_TOKEN_BUDGET raw -o - "$DETECTOR_PLIST")" = '65536'
test "$(plutil -extract EnvironmentVariables.GIG_DAILY_TOKEN_BUDGET raw -o - "$DETECTOR_PLIST")" = '1048576'
test "$(plutil -extract EnvironmentVariables.GIG_BUDGET_DAILY_SCOPE raw -o - "$DETECTOR_PLIST")" = 'gig-reply-detector'
test "$(jq -r '.agents["ai.anicca.hf-gig-reply-detector"].token_budget.pass_tokens' "$REGISTRY")" = '65536'
test "$(jq -r '.agents["ai.anicca.hf-gig-reply-detector"].token_budget.loop_daily_tokens' "$REGISTRY")" = '1048576'
test "$(jq -r '.agents["ai.anicca.hf-gig-reply-detector"].token_budget.daily_scope' "$REGISTRY")" = 'gig-reply-detector'

# Every owner that reaches agent_runner must fail closed rather than silently
# run unbudgeted.
for owner_plist in "$PLIST" "$AUDITOR_PLIST" "$DETECTOR_PLIST"; do
  test "$(plutil -extract EnvironmentVariables.ANICCA_BUDGET_REQUIRED raw -o - "$owner_plist")" = '1'
done
test "$(jq -c '.agents["ai.anicca.hf-gig-pass"].model_routes' "$REGISTRY")" = \
  '[{"task_class":"composition-agent","route":"terra-medium-bounded"},{"task_class":"tool-agent","route":"terra-medium-bounded"},{"task_class":"repeatable-agent","route":"luna-medium-decision"},{"task_class":"high-value-agent","route":"luna-medium-decision"}]'
test "$(jq -c '.agents["ai.anicca.hf-gig-pass"].escalation' "$REGISTRY")" = \
  '{"task_class":"escalation-agent","route":"explicit-escalation","requires_reason":true}'
! grep -q '<string>.*gig_pass.sh</string>' "$PLIST" || { echo 'LaunchAgent bypasses launcher'; exit 1; }
grep -q 'ai.anicca.hf-gig-pass.plist.*Library/LaunchAgents' "$README"
grep -q 'launchctl bootstrap.*ai.anicca.hf-gig-pass.plist' "$README"

echo 'PASS: OS scheduler directly targets canonical production launcher'
