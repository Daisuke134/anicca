import json
import os
import stat
import subprocess
import sys
from pathlib import Path


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import capafy_portfolio as portfolio


def inventory_agents() -> list[dict]:
    statuses = ["online"] * 27 + ["under_review"] * 2 + ["draft", "review_rejected"]
    return [
        {
            "agentId": str(1000000000 + index),
            "name": f"Skill {index}",
            "desc": f"Description {index}",
            "agentType": "run_online" if index < 25 else "download",
            "agentStatus": status,
            "updatedAt": 1785000000000 + index,
            "sales": None,
        }
        for index, status in enumerate(statuses)
    ]


def company_projection() -> dict:
    return {
        "projection_id": "sha256:" + "a" * 64,
        "gross_usd": "9.99",
        "cost_usd": "4.78",
        "contribution_usd": "-4.78",
    }


def test_snapshot_preserves_all_rows_unknown_sales_and_no_business_judgment() -> None:
    snapshot = portfolio.build_snapshot(
        inventory_agents(), company_projection(), "2026-08-02T12:00:00Z"
    )

    assert len(snapshot["products"]) == 31
    assert snapshot["inventory"] == {
        "online": 27,
        "under_review": 2,
        "draft": 1,
        "rejected": 1,
    }
    assert all(product["platform_sales"] is None for product in snapshot["products"])
    assert all(product["decision"] == "unaudited" for product in snapshot["products"])
    assert all(product["purchase_model"] == "undecided" for product in snapshot["products"])
    assert all(product["recurring_mechanism"] is None for product in snapshot["products"])
    assert all(
        value is None
        for product in snapshot["products"]
        for value in product["unit_economics"].values()
    )
    assert snapshot["company_projection_id"] == company_projection()["projection_id"]
    assert portfolio.validate_snapshot(snapshot) == []


def test_validator_rejects_invalid_enum_money_evidence_and_count() -> None:
    snapshot = portfolio.build_snapshot(
        inventory_agents(), company_projection(), "2026-08-02T12:00:00Z"
    )
    snapshot["products"][0]["decision"] = "make_me_rich"
    snapshot["products"][1]["unit_economics"]["gross_usd"] = "9.9"
    snapshot["products"][2]["evidence"] = [
        {
            "url": "http://example.com",
            "observed_at": "not-a-time",
            "claim": "proof",
            "confidence": "certain",
        }
    ]
    snapshot["inventory"]["online"] = 26

    errors = portfolio.validate_snapshot(snapshot)

    assert any("decision" in error for error in errors)
    assert any("unit_economics.gross_usd" in error for error in errors)
    assert any("evidence.url" in error for error in errors)
    assert any("evidence.observed_at" in error for error in errors)
    assert any("evidence.confidence" in error for error in errors)
    assert any("inventory counts" in error for error in errors)


def test_cli_snapshot_is_mode_0600_and_identical_retry_is_byte_stable(
    tmp_path: Path,
) -> None:
    inventory = tmp_path / "inventory.json"
    projection = tmp_path / "projection.json"
    output = tmp_path / "portfolio.json"
    inventory.write_text(json.dumps({"agents": {"list": inventory_agents()}}))
    projection.write_text(json.dumps(company_projection()))
    command = [
        sys.executable,
        str(SCRIPTS / "capafy_portfolio.py"),
        "snapshot",
        "--inventory-json",
        str(inventory),
        "--projection",
        str(projection),
        "--output",
        str(output),
        "--observed-at",
        "2026-08-02T12:00:00Z",
    ]

    first = subprocess.run(command, text=True, capture_output=True, check=False)
    first_bytes = output.read_bytes()
    retry = subprocess.run(command, text=True, capture_output=True, check=False)

    assert first.returncode == 0, first.stderr
    assert retry.returncode == 0, retry.stderr
    assert output.read_bytes() == first_bytes
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert list(tmp_path.glob("*.tmp")) == []
    assert json.loads(first.stdout)["product_count"] == 31


def test_validate_cli_refuses_unknown_top_level_field(tmp_path: Path) -> None:
    source = tmp_path / "portfolio.json"
    snapshot = portfolio.build_snapshot(
        inventory_agents(), company_projection(), "2026-08-02T12:00:00Z"
    )
    snapshot["secret"] = "must not pass"
    source.write_text(json.dumps(snapshot))

    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "capafy_portfolio.py"), "validate", "--input", str(source)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "unsupported top-level fields" in result.stderr
