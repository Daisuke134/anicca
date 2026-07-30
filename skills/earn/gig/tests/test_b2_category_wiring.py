"""X8c: the bandit's ranking must actually reach the apply lane.

Run: python3 -m pytest tests/test_b2_category_wiring.py

The bug this guards against is the one X8c fixed: category_bandit.py computed a correct
Thompson-sampling ranking for weeks and had zero callers, so the apply lane went on
ordering categories by LLM hypothesis. A unit-tested decision that nothing consumes
changes no behaviour. These tests assert the two consumers exist and that neither of
them can take the loop down when the bandit is broken.

Two consumers, because the apply lane is reached by two paths:
  passprep.py   the deterministic pass-prep JSON the runbook agent reads (STEP 0)
  gig_pass.sh   the B2 lane_step prompt, same injection pattern as B0_OBJECTIVE
"""

import json
import os
import subprocess
import sys
from pathlib import Path

GIG_WORK = Path(__file__).resolve().parents[1]
SCRIPTS = GIG_WORK / "scripts"


def _run_passprep(state_dir: Path) -> dict:
    env = dict(os.environ, GIG_STATE_DIR=str(state_dir), GIG_DIR=str(state_dir),
               HOME=str(state_dir.parent))
    proc = subprocess.run([sys.executable, str(GIG_WORK / "passprep.py")],
                          capture_output=True, text=True, env=env)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout.strip().splitlines()[-1])


def _run_b2_context(prep: dict, state_dir: Path) -> dict:
    output = state_dir / "b2-context.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "b2_result_gate.py"),
            "build",
            "--prep-json",
            json.dumps(prep, ensure_ascii=False),
            "--applied",
            str(state_dir / "applied.jsonl"),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return json.loads(output.read_text(encoding="utf-8"))


def _state(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    state = home / "gig"
    state.mkdir(parents=True)
    (state / "strategy.json").write_text(json.dumps({
        "priority_categories": ["PPT/スライド", "文字起こし"],
        "skip_categories": ["イラスト/VTuber (art skill required)"],
        "max_apply_per_pass": 5,
    }, ensure_ascii=False), encoding="utf-8")
    (state / "applied.jsonl").write_text("", encoding="utf-8")
    return state


# --- consumer 1: the pass-prep JSON ------------------------------------------------

def test_passprep_publishes_the_measured_category_order(tmp_path):
    result = _run_passprep(_state(tmp_path))
    assert "category_order" in result
    assert "category_source" in result
    assert result["category_order"], "the lane must never be handed an empty order"


def test_passprep_names_which_authority_chose_the_order(tmp_path):
    """Without this the ledger cannot tell a measured order from a fallback one."""
    result = _run_passprep(_state(tmp_path))
    assert result["category_source"] in ("thompson_sampling", "fallback")


def test_passprep_publishes_the_experiment_freeze(tmp_path):
    result = _run_passprep(_state(tmp_path))
    assert "experiment_freeze" in result
    assert isinstance(result["experiment_freeze"], bool)


def test_active_strategy_experiment_reaches_the_frozen_b2_context(tmp_path):
    """Dropping this projection makes a started proposal experiment behaviorless."""
    state = _state(tmp_path)
    strategy_path = state / "strategy.json"
    strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    strategy["proposal_playbook"] = "Put verified proof first."
    strategy["experiments"] = [{
        "id": "proposal-proof-v2",
        "status": "active",
        "field_changed": "proposal_playbook",
        "new_value": "Put verified proof first.",
        "target_metric": "replied",
        "hypothesis": "Specific proof should raise reply rate.",
        "source_url": "https://example.com/evidence",
        "old_value": "Lead with a generic greeting.",
        "frozen_category_order": ["PPT/スライド", "文字起こし"],
    }]
    strategy_path.write_text(json.dumps(strategy, ensure_ascii=False), encoding="utf-8")

    prep = _run_passprep(state)
    assert prep["active_strategy_experiment"] == {
        "id": "proposal-proof-v2",
        "field_changed": "proposal_playbook",
        "new_value": "Put verified proof first.",
        "target_metric": "replied",
    }

    context = _run_b2_context(prep, state)
    assert context["active_strategy_experiment"] == prep["active_strategy_experiment"]


def test_apply_prompt_consumes_the_active_strategy_experiment_without_a_second_change():
    """A context field alone is inert unless the B2 agent is bound to consume it."""
    source = (GIG_WORK / "gig_pass.sh").read_text(encoding="utf-8")
    assert (
        "When active_strategy_experiment is non-null, apply its field_changed=new_value "
        "to every relevant application"
    ) in source
    assert "do not improvise a second strategy change" in source


def test_apply_prompt_consumes_only_anonymized_verified_portfolio_proof():
    source = (GIG_WORK / "gig_pass.sh").read_text(encoding="utf-8")
    assert "verified_portfolio" in source
    assert "buyer-visible paid delivery" in source
    assert "Never disclose project IDs, buyer names, local paths, or hashes" in source
    assert '--projects-dir "$HOME/gig/projects"' in source
    assert '--delivery-evidence-dir "$HOME/gig/delivery-evidence"' in source
    assert '--paid-progress-ledger "$HOME/gig/paid-progress.jsonl"' in source


def test_passprep_clamps_live_application_volume_to_seven_and_persists_it(tmp_path):
    state = _state(tmp_path)
    strategy_path = state / "strategy.json"
    strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    strategy["max_apply_per_pass"] = 12
    strategy_path.write_text(json.dumps(strategy), encoding="utf-8")
    result = _run_passprep(state)
    persisted = json.loads(strategy_path.read_text(encoding="utf-8"))
    assert result["max_apply_per_pass"] == 7
    assert persisted["max_apply_per_pass"] == 7


def test_passprep_migrates_the_old_four_application_cap_to_seven(tmp_path):
    state = _state(tmp_path)
    strategy_path = state / "strategy.json"
    strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    strategy["max_apply_per_pass"] = 4
    strategy_path.write_text(json.dumps(strategy), encoding="utf-8")

    result = _run_passprep(state)
    persisted = json.loads(strategy_path.read_text(encoding="utf-8"))

    assert result["max_apply_per_pass"] == 7
    assert persisted["max_apply_per_pass"] == 7


def test_passprep_repairs_live_proposal_templates_to_coconala_minimum(tmp_path):
    """A frozen experiment must never freeze a form-invalid proposal."""
    state = _state(tmp_path)
    strategy_path = state / "strategy.json"
    strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    strategy["proposal_templates"] = {
        "コード/IT開発": "短い提案です。",
        "already-valid": "有" * 200,
    }
    strategy_path.write_text(json.dumps(strategy, ensure_ascii=False), encoding="utf-8")

    _run_passprep(state)
    persisted = json.loads(strategy_path.read_text(encoding="utf-8"))

    assert 200 <= len(persisted["proposal_templates"]["コード/IT開発"]) <= 3000
    assert persisted["proposal_templates"]["already-valid"] == "有" * 200


def test_passprep_falls_back_to_priority_categories_with_no_ledgers(tmp_path):
    """No trials yet -> the LLM's hypothesis order, verbatim. This is today's live state."""
    result = _run_passprep(_state(tmp_path))
    assert result["category_source"] == "fallback"
    assert result["category_order"] == result["priority_categories"]


def test_passprep_still_emits_valid_json_when_the_bandit_is_unusable(tmp_path):
    """A bandit failure must cost the pass its ordering, never its prep."""
    state = _state(tmp_path)
    (state / "applied.jsonl").write_text("{ this is not json\n" * 3, encoding="utf-8")
    (state / "strategy.json").write_text("{ broken", encoding="utf-8")
    result = _run_passprep(state)
    assert result["category_order"], "prep must still name categories"
    assert result["category_source"] == "fallback"


def test_passprep_never_offers_a_skipped_category(tmp_path):
    state = _state(tmp_path)
    (state / "strategy.json").write_text(json.dumps({
        "priority_categories": ["イラスト", "PPT/スライド"],
        "skip_categories": ["イラスト/VTuber (art skill required)"],
    }, ensure_ascii=False), encoding="utf-8")
    result = _run_passprep(state)
    assert "イラスト" not in result["category_order"]


# --- consumer 2: the B2 lane prompt -------------------------------------------------

def test_gig_pass_computes_the_b2_objective_before_the_apply_step():
    source = (GIG_WORK / "gig_pass.sh").read_text(encoding="utf-8")
    assert "b2_objective.py" in source, "the apply lane must consult the bandit"
    assert "B2_OBJECTIVE" in source


def test_gig_pass_injects_the_objective_into_the_apply_prompt():
    """Computing it and not putting it in the prompt is the X8c bug all over again."""
    source = (GIG_WORK / "gig_pass.sh").read_text(encoding="utf-8")
    apply_step = [ln for ln in source.splitlines()
                  if ln.lstrip().startswith('lane_step "B2"')]
    assert apply_step, "B2 lane_step not found"
    assert "$B2_OBJECTIVE" in apply_step[0]
    assert "eligible_count" in apply_step[0]
    assert "目標4件" in apply_step[0]
    assert "最大7件" in apply_step[0]
    assert "accepting_applications" in apply_step[0]
    assert "競争率はhard exclusionではない" in apply_step[0]
    assert "cdp_nav_snapshot.py open-application" in apply_step[0]
    assert "cdp_nav_snapshot.py submit-application" in apply_step[0]
    assert "submit_verified=true" in apply_step[0]


def test_b2_allows_owner_facts_and_accounts_but_rejects_live_human_modalities():
    """Identity facts and connected accounts are not live face/voice/body work."""
    source = (GIG_WORK / "gig_pass.sh").read_text(encoding="utf-8")
    apply_step = [ln for ln in source.splitlines()
                  if ln.lstrip().startswith('lane_step "B2"')]
    assert apply_step, "B2 lane_step not found"
    assert "$B2_OBJECTIVE" in apply_step[0]
    lowered = source.lower()
    assert "age, sex, location, and career history" in lowered
    assert "authorized owner profile" in lowered
    assert "connected credentials" in lowered
    assert "external account" in lowered
    assert "Google Meet, Zoom, phone, live lecture, face-on interview" in source
    assert "human voice recording" in source
    assert "physical on-site action" in source
    assert "personal account/identity" not in source
    assert "real person's account or identity" not in source


def test_b2_accepts_recurring_asynchronous_text_work_the_loop_can_fulfill():
    """Ongoing chat is scheduler work, not synchronous human availability.

    Production pass 1785308400 observed request 5174303 as chat-only and
    explicitly non-synchronous, yet rejected it merely because the work recurs
    daily for one month.  That excludes exactly the retainer work the loop is
    meant to win.
    """
    source = (GIG_WORK / "gig_pass.sh").read_text(encoding="utf-8")
    assert "fulfillment_capabilities" in source
    assert "scheduled recurring asynchronous text" in source
    assert "do not classify it as synchronous human availability" in source.lower()
    assert "durable follow-up objective" in source
    assert "chat形式" in source
    assert "隙間時間" in source


def test_b2_prompt_scans_and_submits_the_retainer_bucket_it_reports():
    source = (GIG_WORK / "gig_pass.sh").read_text(encoding="utf-8")
    apply_step = next(
        line for line in source.splitlines()
        if line.lstrip().startswith('lane_step "B2"')
    )
    assert "$B2_OBJECTIVE" in apply_step
    assert "retainer:new" in source
    assert "/job_matching/outsources" in source
    assert "open-retainer-application" in source
    assert "submit-retainer-application" in source
    assert "target_retainer_applications" in source
    assert "compensation_type" in source
    assert "weekly_hours_min" in source
    assert "synchronous_interview_required" in source
    assert "/mypage/job_matching/applied/outsource_applications" in source


def test_b2_browser_rules_use_code_verified_helper_paths_without_rediscovery():
    source = (GIG_WORK / "gig_pass.sh").read_text(encoding="utf-8")
    start = source.index("    B2)")
    end = source.index("    REFLECT)", start)
    b2_rules = source[start:end]

    assert "Parent code already acquired the step-owned context lease" in b2_rules
    assert '--lease \\"\\$ANICCA_BROWSER_LEASE\\"' in b2_rules
    assert "--ws <returned_ws>" not in b2_rules
    assert "Do not copy or transcribe the opaque page websocket" in b2_rules
    assert "python3 $B/cdp_context_lease.py release $step_context" not in b2_rules
    assert "Do not run cdp_context_lease.py release" in b2_rules
    assert "Parent code releases this exact context only after this agent exits" in b2_rules
    assert "Do not run --help, rg, find, or path discovery" in b2_rules
    assert "Both helper paths were verified by parent code" in b2_rules
    assert 'B2_TOOLING_PREFLIGHT="verified"' in source
    assert '[ -f "$B/cdp_context_lease.py" ]' in source
    assert '[ -f "$G/scripts/cdp_nav_snapshot.py" ]' in source


def test_parent_acquires_b2_lease_and_exports_only_its_stable_handle():
    source = (GIG_WORK / "gig_pass.sh").read_text(encoding="utf-8")
    runner = source.index('python3 "$RUNNER"', source.index("\nstep() {"))
    acquire = source.rindex('acquire_agent_step_context "$label"', 0, runner)
    exported_handle = source.rindex(
        'export ANICCA_BROWSER_LEASE="$step_context"',
        0,
        runner,
    )
    assert acquire < exported_handle < runner
    apply_step = next(
        line for line in source.splitlines()
        if line.lstrip().startswith('lane_step "B2"')
    )
    assert '--lease \\"\\$ANICCA_BROWSER_LEASE\\"' in apply_step
    assert "--ws <leased_ws>" not in apply_step


def test_shared_browser_skill_does_not_tell_agents_to_transcribe_opaque_ws_ids():
    browser_skill = (GIG_WORK.parents[1] / "browser" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert 'WS=$(echo "$LEASE"' not in browser_skill
    assert "the parent/controller acquires and releases the lease" in browser_skill
    assert '--lease "$ANICCA_BROWSER_LEASE"' in browser_skill


def test_parent_releases_the_b2_step_context_after_the_runner_returns():
    source = (GIG_WORK / "gig_pass.sh").read_text(encoding="utf-8")

    assert "release_agent_step_context()" in source
    helper = source.index("release_agent_step_context()")
    parent_release = source.index(
        'python3 "$B/cdp_context_lease.py" release "$step_context"', helper
    )
    runner = source.index('python3 "$RUNNER"', source.index("step()"))
    cleanup = source.index('release_agent_step_context "$label"', runner)
    failure_gate = source.index('if [ "$step_runner_rc" -ne 0 ]', cleanup)

    assert helper < parent_release
    assert runner < cleanup < failure_gate


def test_gig_pass_has_a_literal_fallback_objective_for_the_apply_lane():
    """Same shape as B0: an empty computed objective must not yield an empty prompt."""
    source = (GIG_WORK / "gig_pass.sh").read_text(encoding="utf-8")
    assert 'B2_OBJECTIVE="APPLY' in source or '[ -n "$B2_OBJECTIVE" ]' in source


def test_gig_pass_records_the_category_decision_with_its_pass_id():
    """X8b's lesson: a decision whose inputs were not recorded cannot be audited."""
    source = (GIG_WORK / "gig_pass.sh").read_text(encoding="utf-8")
    assert "--pass-id" in source and "b2_objective.py" in source
    b2_lines = [ln for ln in source.splitlines() if "b2_objective.py" in ln]
    assert any("--pass-id" in ln for ln in b2_lines), \
        "the objective call must stamp the decision with the pass it steered"


# --- the freeze needs a consumer, or it is decoration ------------------------------

def test_the_runbook_hands_the_measured_order_to_the_apply_step():
    """STEP 0 already tells the pass to parse PREP_JSON; it must parse the new field."""
    runbook = (GIG_WORK / "GIG_PASS_RUNBOOK.md").read_text(encoding="utf-8")
    assert "category_order" in runbook


def test_the_runbook_makes_the_explore_step_honour_the_freeze():
    """A freeze that nothing reads is decoration. B4-EXPLORE is what starts experiments."""
    runbook = (GIG_WORK / "GIG_PASS_RUNBOOK.md").read_text(encoding="utf-8")
    assert "may_start_experiment" in runbook


def test_the_runbook_still_lets_running_experiments_be_evaluated():
    """Freezing new experiments must not strand the ones already in flight."""
    runbook = (GIG_WORK / "GIG_PASS_RUNBOOK.md").read_text(encoding="utf-8")
    # Anchor on the gate itself, not on the STEP 0 field list that merely names it.
    idx = runbook.find("EXPERIMENT FREEZE GATE")
    assert idx != -1, "the freeze gate must be stated where experiments are started"
    window = runbook[idx:idx + 1600]
    assert "experiments_due" in window, \
        "the freeze text must say evaluation of due experiments continues"


def test_freeze_never_turns_live_form_validation_into_ineligibility():
    source = (SCRIPTS / "b2_objective.py").read_text(encoding="utf-8")
    assert "200" in source and "form validation" in source
    assert "not an experiment" in source
    assert "live category minimum" in source
    assert "request budget ceiling" in source
    assert "hold proposal wording, price and templates exactly" not in source


def test_apply_lane_continues_same_pass_when_only_volume_gate_is_red():
    source = (GIG_WORK / "gig_pass.sh").read_text(encoding="utf-8")
    assert "b2_under_target_continue" in source
    assert '--pass-id "$PASS_ID"' in source
    assert "return 3" in source
    assert '--prep-json "$PREP"' in source
    assert "PREP_JSON" not in source


def test_apply_volume_contract_is_not_cut_off_by_the_shared_lane_call_budget():
    """The shared seven-call guard ended a live pass at 1/4 while sources had next pages."""
    source = (GIG_WORK / "gig_pass.sh").read_text(encoding="utf-8")
    assert "B2_MODEL_CALL_COUNT" in source
    assert "GIG_B2_MODEL_CALL_LIMIT" in source
    assert 'label" = "gig-B2"' in source
    assert "B2_CONTINUATION_HINT" in source
    assert "B2_MODEL_CALL_COUNT" in source[source.index("b2_under_target_continue"):]


def test_one_b2_invocation_means_quantity_not_one_page_or_one_application():
    source = (GIG_WORK / "gig_pass.sh").read_text(encoding="utf-8")
    apply_step = next(
        line for line in source.splitlines()
        if line.lstrip().startswith('lane_step "B2"')
    )
    assert "Do not return after one application or one page" in apply_step
    assert "at least 12 new live request detail pages" in apply_step
    assert "before ending this B2 invocation while still below target" in apply_step


def test_apply_lane_carries_search_progress_into_the_continuation_prompt():
    source = (GIG_WORK / "gig_pass.sh").read_text(encoding="utf-8")
    assert "B2_CONTINUATION_HINT" in source
    assert "This is a continuation, not a restart" in source
    assert "Do not re-inspect a prior inspected request" in source
    assert "applications is cumulative across this pass" in source
    assert "do not re-inspect a carried verified application" in source
    assert "CODE-OWNED FIRST NAVIGATION CONTRACT" in source
    assert "navigate to the exact next_url" in source
    assert "parent code rejects the attempt if it remains at previous_url" in source
    assert "INITIAL SEARCH CONTRACT: open newest-first" in source
    assert "Open newest-first https://coconala.com/requests?sort=new and save" not in source


def test_apply_lane_builds_and_enforces_the_next_cursor_contract():
    source = (GIG_WORK / "gig_pass.sh").read_text(encoding="utf-8")
    assert 'b2_result_gate.py" next-cursor' in source
    assert '--cursor-contract "$B2_CURSOR_CONTRACT"' in source
    assert 'record_failure "b2_continuation_cursor_build_failed"' in source


def test_continuation_cursor_evidence_is_fresh_for_each_b2_invocation():
    """Production call 7 must not satisfy its cursor with call 6's live DOM."""
    source = (GIG_WORK / "gig_pass.sh").read_text(encoding="utf-8")
    captured = source.index('B2_ATTEMPT_START_EPOCH="$(python3 -c')
    runner = source.index('python3 "$RUNNER"', captured)
    freshness_gate = source.index(
        '--cursor-min-mtime "$B2_ATTEMPT_START_EPOCH"',
        runner,
    )
    assert captured < runner < freshness_gate


def test_apply_lane_persists_and_resumes_cursor_across_hourly_wakes():
    source = (GIG_WORK / "gig_pass.sh").read_text(encoding="utf-8")
    assert "b2-search-objective.json" in source
    assert 'b2_search_objective.py" resume' in source
    assert 'b2_search_objective.py" checkpoint' in source
    assert 'b2_search_objective.py" finish' in source
    assert "PRIOR-WAKE RESUME CONTRACT" in source
    assert "market_refresh_after_exhaustion" in (
        SCRIPTS / "b2_search_objective.py"
    ).read_text(encoding="utf-8")


def test_apply_lane_yields_before_it_can_block_the_next_hourly_wake():
    source = (GIG_WORK / "gig_pass.sh").read_text(encoding="utf-8")
    assert 'b2_wall_clock.py" plan' in source
    assert "GIG_PASS_WALL_CLOCK_LIMIT_SECONDS" in source
    assert "GIG_PASS_FINALIZE_RESERVE_SECONDS" in source
    assert "GIG_B2_MIN_INVOCATION_SECONDS" in source
    assert "--timeout-seconds" in source
    assert "b2_deadline_yield" in source
    assert "B2_CURSOR_CONTRACT" in source[source.index("b2_deadline_yield") - 500:]


def test_initial_apply_gate_never_expands_an_unset_or_empty_bash_array():
    """Production pass 1785267692 died before continuation under `set -u`."""
    source = (GIG_WORK / "gig_pass.sh").read_text(encoding="utf-8")
    assert "b2_cursor_args" not in source
    assert 'if [ -n "$B2_CURSOR_CONTRACT" ]; then' in source
    assert source.count('b2_result_gate.py" validate') >= 2


def test_unexpected_shell_exit_is_recorded_and_preserves_nonzero_status():
    source = (GIG_WORK / "gig_pass.sh").read_text(encoding="utf-8")
    assert 'record_failure "unexpected_shell_exit:rc=$rc" "SHELL"' in source
    assert "FAILURE_RECORDED=1" in source
    assert 'exit "$rc"' in source


def test_apply_prompt_inspects_the_whole_newest_page_before_exhaustion_sweep():
    source = (GIG_WORK / "gig_pass.sh").read_text(encoding="utf-8")
    assert "all 40 newest cards" in source
    assert "Do not begin the required-source exhaustion sweep" in source


def test_the_objective_command_cannot_abort_the_pass():
    """b2_objective is prompt-building, not a gate. It must be || true / || fallback."""
    source = (GIG_WORK / "gig_pass.sh").read_text(encoding="utf-8")
    b2_lines = [ln for ln in source.splitlines() if "b2_objective.py" in ln]
    assert b2_lines
    assert all("||" in ln for ln in b2_lines), \
        "an unguarded objective call can kill the apply lane"
