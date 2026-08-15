import json
import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
GIG_PASS = Path(__file__).resolve().parents[1] / "gig_pass.sh"
sys.path.insert(0, str(SCRIPTS))

import experiment_evaluator as evaluator


def _experiment(**overrides):
    row = {
        "id": "proposal-v2",
        "ts": 100,
        "status": "active",
        "field_changed": "proposal_playbook",
        "old_value": "old",
        "new_value": "new",
        "target_metric": "replied",
        "baseline": {
            "pass_id": "90",
            "ts": 90,
            "applied": 100,
            "replied": 10,
            "won": 2,
            "paid": 1,
        },
        "eval_by_pass": 12,
        "min_post_applications": 8,
    }
    row.update(overrides)
    return row


def _strategy(*experiments):
    return {
        "pass_count": 12,
        "proposal_playbook": "new",
        "experiments": list(experiments),
    }


def _funnel(**overrides):
    row = {
        "pass_id": "120",
        "ts": 120,
        "applied": 110,
        "replied": 13,
        "won": 2,
        "paid": 1,
    }
    row.update(overrides)
    return row


def test_overlapping_legacy_experiments_are_quarantined_not_false_promoted():
    strategy = _strategy(
        _experiment(id="a"),
        _experiment(id="b", field_changed="profile.icon"),
    )

    result = evaluator.assess(strategy, _funnel(), now=130)

    assert result["summary"]["quarantined"] == 2
    assert {row["status"] for row in result["strategy"]["experiments"]} == {
        "quarantined"
    }
    assert all(
        row["evaluation"]["reason"] == "overlapping_active_experiments"
        for row in result["strategy"]["experiments"]
    )
    assert result["strategy"]["proposal_playbook"] == "new"


def test_isolated_experiment_is_kept_only_after_fresh_rate_improvement():
    result = evaluator.assess(_strategy(_experiment()), _funnel(), now=130)

    experiment = result["strategy"]["experiments"][0]
    assert experiment["status"] == "kept"
    assert experiment["evaluation"]["baseline_rate"] == 0.1
    assert experiment["evaluation"]["observed_rate"] == 0.3
    assert result["summary"]["kept"] == 1


def test_isolated_degradation_reverts_the_code_owned_strategy_field():
    latest = _funnel(replied=10)

    result = evaluator.assess(_strategy(_experiment()), latest, now=130)

    experiment = result["strategy"]["experiments"][0]
    assert experiment["status"] == "reverted"
    assert result["strategy"]["proposal_playbook"] == "old"
    assert experiment["evaluation"]["reason"] == "metric_did_not_improve"


def test_external_profile_mutation_is_quarantined_because_code_cannot_revert_it():
    strategy = _strategy(_experiment(
        field_changed="profile.icon",
        old_value="old-url",
        new_value="new-url",
    ))

    result = evaluator.assess(strategy, _funnel(), now=130)

    experiment = result["strategy"]["experiments"][0]
    assert experiment["status"] == "quarantined"
    assert experiment["evaluation"]["reason"] == "mutation_not_code_reversible"


def test_active_experiment_without_evaluation_deadline_cannot_live_forever():
    result = evaluator.assess(
        _strategy(_experiment(eval_by_pass=None)),
        _funnel(),
        now=130,
    )

    experiment = result["strategy"]["experiments"][0]
    assert experiment["status"] == "quarantined"
    assert experiment["evaluation"]["reason"] == "evaluation_deadline_missing"


def test_insufficient_post_mutation_sample_defers_without_a_verdict():
    latest = _funnel(applied=105, replied=12)

    result = evaluator.assess(_strategy(_experiment()), latest, now=130)

    experiment = result["strategy"]["experiments"][0]
    assert experiment["status"] == "active"
    assert experiment["evaluation"]["reason"] == "insufficient_post_applications"
    assert result["summary"]["deferred"] == 1


def test_stale_funnel_defers_without_a_verdict():
    latest = _funnel(ts=99, pass_id="90")

    result = evaluator.assess(_strategy(_experiment()), latest, now=130)

    experiment = result["strategy"]["experiments"][0]
    assert experiment["status"] == "active"
    assert experiment["evaluation"]["reason"] == "fresh_funnel_required"


def test_evaluate_files_is_atomic_and_event_append_is_idempotent(tmp_path):
    strategy_path = tmp_path / "strategy.json"
    funnel_path = tmp_path / "funnel.jsonl"
    events_path = tmp_path / "experiment-evaluations.jsonl"
    strategy_path.write_text(json.dumps(_strategy(_experiment())), encoding="utf-8")
    funnel_path.write_text(json.dumps(_funnel()) + "\n", encoding="utf-8")

    first = evaluator.evaluate_files(
        strategy_path=strategy_path,
        funnel_path=funnel_path,
        events_path=events_path,
        now=130,
    )
    second = evaluator.evaluate_files(
        strategy_path=strategy_path,
        funnel_path=funnel_path,
        events_path=events_path,
        now=131,
    )

    assert first["kept"] == 1
    assert second["evaluated"] == 0
    assert len(events_path.read_text(encoding="utf-8").splitlines()) == 1
    assert not list(tmp_path.glob("*.tmp"))


def test_runtime_evaluates_fresh_funnel_before_learn_and_before_failure_exit():
    source = GIG_PASS.read_text(encoding="utf-8")
    apply_index = source.index('lane_step "B2"')
    funnel_index = source.index('python3 "$G/gig_funnel.py"', apply_index)
    evaluator_index = source.index(
        'python3 "$G/scripts/experiment_evaluator.py"', funnel_index
    )
    learn_index = source.index('lane_step "LEARN"', evaluator_index)
    failure_index = source.index(
        'if [ "${#LANE_STEP_FAILURES[@]}" -gt 0 ]', learn_index
    )

    assert apply_index < funnel_index < evaluator_index < learn_index < failure_index
    learn_window = source[learn_index:failure_index]
    assert "experiment_evaluator.py start --spec-json" in learn_window
    assert "never edit strategy.json directly" in learn_window


def test_start_creates_one_reversible_experiment_and_freezes_category_epoch():
    strategy = {
        "pass_count": 20,
        "improve_cadence_passes": 4,
        "proposal_playbook": "old",
        "experiments": [],
    }
    spec = {
        "id": "proposal-specific-proof",
        "hypothesis": "具体的な証拠を冒頭に置くと返信率が上がる",
        "source_url": "https://example.com/evidence",
        "field_changed": "proposal_playbook",
        "new_value": "new",
        "target_metric": "replied",
    }

    result = evaluator.start(
        strategy, _funnel(), spec,
        category_order=["資料作成", "Web制作"],
        now=140,
    )

    assert result["ok"] is True
    updated = result["strategy"]
    assert updated["proposal_playbook"] == "new"
    experiment = updated["experiments"][0]
    assert experiment["old_value"] == "old"
    assert experiment["eval_by_pass"] == 28
    assert experiment["frozen_category_order"] == ["資料作成", "Web制作"]
    assert experiment["baseline"]["pass_id"] == "120"


def test_start_rejects_a_second_active_experiment_and_unsupported_field():
    active = _strategy(_experiment())
    spec = {
        "id": "second",
        "hypothesis": "x",
        "source_url": "https://example.com",
        "field_changed": "proposal_playbook",
        "new_value": "other",
        "target_metric": "replied",
    }
    assert evaluator.start(
        active, _funnel(), spec, category_order=["資料作成"], now=140
    )["reason"] == "active_experiment_exists"

    empty = {"pass_count": 20, "experiments": [], "profile": {"icon": "old"}}
    spec["field_changed"] = "profile.icon"
    assert evaluator.start(
        empty, _funnel(), spec, category_order=["資料作成"], now=140
    )["reason"] == "field_not_code_reversible"
