import copy
import json
import sys
from pathlib import Path


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import capafy_cleanup_execution as execution
from test_capafy_portfolio_cleanup import complete_cleanup, portfolio


def remote_states(queue: dict) -> dict:
    return {
        item["agent_id"]: {
            "ok": True,
            "latest_version": {
                "agentId": item["agent_id"],
                "status": 1,
                "isConfirmedSkills": 1,
                "title": f"Remote {item['agent_id']}",
                "shortDescription": "Current verified positioning.",
            },
        }
        for item in queue["items"]
    }


def candidate(queue: dict) -> dict:
    rows = []
    for item in queue["items"]:
        decision = "retire" if item["action"] == "retire_candidate" else "already_satisfied"
        rows.append(
            {
                "agent_id": item["agent_id"],
                "decision": decision,
                "reason": "The current remote state satisfies the cited observable boundary.",
                "proposed_title": None,
                "proposed_description": None,
                "evidence": [
                    {
                        "url": f"https://capafy.ai/agent/{item['agent_id']}",
                        "observed_at": "2026-08-02T00:20:00Z",
                        "claim": "The remote product state was read directly.",
                        "confidence": "high",
                    }
                ],
                "observable_success": "Remote status and listing positioning are independently readable.",
            }
        )
    return {
        "schema_version": 1,
        "kind": "capafy_cleanup_execution",
        "queue_source_digest": execution.queue_digest(queue),
        "assessed_at": "2026-08-02T00:20:00Z",
        "items": rows,
    }


def test_execution_candidate_covers_exact_queue_and_accepts_remote_grounded_judgment() -> None:
    queue = complete_cleanup(portfolio())
    value = candidate(queue)

    assert execution.validate_execution(queue, remote_states(queue), value) == []


def test_submit_once_requires_a_concrete_repositioning() -> None:
    queue = complete_cleanup(portfolio())
    value = candidate(queue)
    row = next(row for row in value["items"] if row["agent_id"] == queue["items"][-1]["agent_id"])
    row["decision"] = "submit_once"

    errors = execution.validate_execution(queue, remote_states(queue), value)

    assert any("proposed_title" in error for error in errors)
    assert any("proposed_description" in error for error in errors)


def test_execution_rejects_missing_duplicate_or_mismatched_remote_ids() -> None:
    queue = complete_cleanup(portfolio())
    value = candidate(queue)
    value["items"].pop()
    remotes = remote_states(queue)
    remotes[queue["items"][0]["agent_id"]]["latest_version"]["agentId"] = "wrong"

    errors = execution.validate_execution(queue, remotes, value)

    assert any("exactly" in error for error in errors)
    assert any("remote agentId" in error for error in errors)


def test_retire_decision_is_only_valid_for_retire_candidate() -> None:
    queue = complete_cleanup(portfolio())
    value = candidate(queue)
    repair = next(item for item in value["items"] if item["agent_id"] == queue["items"][0]["agent_id"])
    repair["decision"] = "retire"

    assert any("retire" in error for error in execution.validate_execution(queue, remote_states(queue), value))


def test_codex_output_schema_types_every_const_property() -> None:
    schema = json.loads((SCRIPTS.parent / "schemas/capafy-cleanup-execution.schema.json").read_text())

    untyped = []
    stack = [("$", schema)]
    while stack:
        path, node = stack.pop()
        if not isinstance(node, dict):
            continue
        if "const" in node and "type" not in node:
            untyped.append(path)
        for key, child in node.items():
            if isinstance(child, dict):
                stack.append((f"{path}.{key}", child))

    assert untyped == []


def test_apply_terminal_judgments_closes_only_non_mutating_items() -> None:
    queue = complete_cleanup(portfolio())
    value = candidate(queue)
    remotes = remote_states(queue)

    result = execution.apply_terminal_judgments(queue, remotes, value)

    by_id = {item["agent_id"]: item for item in result["items"]}
    for row in value["items"]:
        item = by_id[row["agent_id"]]
        if row["decision"] == "already_satisfied":
            assert item["status"] == "verified"
            assert item["remote_url"] == f"https://capafy.ai/agent/{row['agent_id']}"
        elif row["decision"] == "retire":
            assert item["status"] == "retired"
            assert item["remote_url"] is None
        else:
            assert item["status"] == "queued"


def test_apply_terminal_judgments_is_idempotent() -> None:
    queue = complete_cleanup(portfolio())
    value = candidate(queue)
    remotes = remote_states(queue)

    first = execution.apply_terminal_judgments(queue, remotes, value)
    retry = execution.apply_terminal_judgments(first, remotes, value)

    assert retry == first
