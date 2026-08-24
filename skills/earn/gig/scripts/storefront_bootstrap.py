#!/usr/bin/env python3
"""Build the public AI/Mac skill inventory used for a first Storefront listing."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
SKILLS = REPO / "skills"
REGISTRY = SKILLS / "registry.json"


def _frontmatter(source: str) -> dict[str, str]:
    if not source.startswith("---\n"):
        return {}
    end = source.find("\n---", 4)
    if end < 0:
        return {}
    rows: dict[str, str] = {}
    lines = source[4:end].splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if ":" not in line or line[:1].isspace():
            index += 1
            continue
        key, raw = line.split(":", 1)
        value = raw.strip().strip("'\"")
        if value in {"|", ">", "|-", ">-"}:
            continuation = []
            index += 1
            while index < len(lines) and lines[index][:1].isspace():
                continuation.append(lines[index].strip())
                index += 1
            value = " ".join(continuation)
        else:
            index += 1
        rows[key.strip()] = value
    return rows


def inventory(repo: Path = REPO) -> dict[str, Any]:
    skills = repo / "skills"
    registry_path = skills / "registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    live = {
        str(row.get("dir")): name
        for name, row in registry.get("slots", {}).items()
        if isinstance(row, dict) and row.get("status") == "live" and row.get("dir")
    }
    rows = []
    for path in sorted(skills.glob("**/SKILL.md")):
        source = path.read_text(encoding="utf-8")
        meta = _frontmatter(source)
        name = str(meta.get("name") or path.parent.name).strip()
        description = " ".join(str(meta.get("description") or "").split())[:1000]
        if not name or not description:
            continue
        relative_dir = path.parent.relative_to(repo).as_posix()
        rows.append({
            "name": name,
            "description": description,
            "skill_path": path.relative_to(repo).as_posix(),
            "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            "runtime": "live_adapter" if relative_dir in live else "agent_skill",
            "slot": live.get(relative_dir),
        })
    canonical = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "version": 1,
        "source": "public_repo_skills",
        "skills": rows,
        "inventory_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }


def select_capability(
    value: dict[str, Any], *, runner: Path, schema: Path,
    evidence_dir: Path, workdir: Path, timeout_seconds: int = 180,
    rejected: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    prompt = """Choose the single strongest first Coconala service from CAPABILITY_INVENTORY and
return only the strict schema object. The AI/Mac/tool system is the delivery workforce: never use
the account owner's personal labor, experience, health, time, identity, credentials, or external
authority as a capability. Select only an outcome that this installed skill can produce and verify
from buyer-supplied inputs. Prefer clear recurring business value, low marginal compute/tool cost,
bounded scope, objective quality checks, and low refund/deadline risk. service_query is a natural
Japanese phrase suitable for checking official Coconala demand, not listing copy. Do not select
trading, account creation, outreach, marketplace operation, regulated advice, physical work, or a
skill that merely orchestrates another money loop. If no listed skill supports an honest standalone
buyer deliverable, choose no_op and set skill_path/service_query/outcome/deliverable/inputs to null.
Never repeat an exact skill_path + service_query pair in REJECTED_OFFICIAL_DEMAND; the official
marketplace already proved that candidate has no sold/reviewed demand.
CAPABILITY_INVENTORY=""" + json.dumps(value, ensure_ascii=False, separators=(",", ":")) + \
        "\nREJECTED_OFFICIAL_DEMAND=" + json.dumps(rejected or [], ensure_ascii=False, separators=(",", ":"))
    evidence_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    completed = subprocess.run([
        sys.executable, str(runner), "--task-class", "storefront-proposal-agent",
        "--prompt-stdin", "--schema", str(schema), "--evidence-dir", str(evidence_dir),
        "--task-label", "gig-storefront-bootstrap-select", "--loop", "gig-storefront",
        "--workdir", str(workdir), "--timeout-seconds", str(timeout_seconds),
    ], input=prompt, text=True, capture_output=True, timeout=timeout_seconds + 30, check=False)
    if completed.returncode != 0:
        raise RuntimeError("storefront_bootstrap_selection_failed")
    summary = json.loads((evidence_dir / "summary.json").read_text(encoding="utf-8"))
    result_path = Path(str(summary.get("result_path") or "")).resolve(strict=True)
    result_path.relative_to(evidence_dir.resolve())
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if summary.get("status") != "success" or min(
        (evidence_dir / "summary.json").stat().st_mtime, result_path.stat().st_mtime
    ) < started:
        raise RuntimeError("storefront_bootstrap_selection_stale")
    nullable = ("skill_path", "service_query", "buyer_outcome", "deliverable", "required_buyer_inputs")
    if result.get("decision") == "no_op":
        if any(result.get(key) is not None for key in nullable) or not result.get("no_op_reason"):
            raise RuntimeError("storefront_bootstrap_noop_invalid")
        return result
    known = {row["skill_path"] for row in value["skills"]}
    rejected_pairs = {(row.get("skill_path"), row.get("service_query")) for row in rejected or []}
    if (result.get("decision") != "sell" or result.get("skill_path") not in known
            or not all(result.get(key) for key in nullable)
            or result.get("no_op_reason") is not None
            or (result.get("skill_path"), result.get("service_query")) in rejected_pairs):
        raise RuntimeError("storefront_bootstrap_selection_invalid")
    return result


def _official_form_options(snapshot: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in snapshot.get("fields") or [] if isinstance(row, dict)]
    checkboxes: dict[str, list[str]] = {}
    radios: dict[str, list[str]] = {}
    selects: dict[str, list[str]] = {}
    for row in rows:
        name, value, kind = str(row.get("name") or ""), str(row.get("value") or ""), str(row.get("type") or "")
        if not name:
            continue
        if kind == "checkbox" and value:
            checkboxes.setdefault(name, []).append(value)
        elif kind == "radio" and value:
            radios.setdefault(name, []).append(value)
        elif row.get("tag") == "SELECT":
            selects[name] = [str(item) for item in row.get("options") or [] if str(item)]
    prices = []
    for row in snapshot.get("price_options") or []:
        if not isinstance(row, dict):
            continue
        label = str(row.get("text") or "").replace(",", "")
        digits = "".join(character for character in label if character.isdigit())
        if str(row.get("value") or "").isdigit() and digits:
            prices.append({"value": str(row["value"]), "display_price_jpy": int(digits)})
    return {"checkboxes": checkboxes, "radios": radios, "selects": selects,
            "display_prices": prices}


def _validate_listing(result: dict[str, Any], official: dict[str, Any]) -> None:
    nullable = (
        "title_stem", "catchphrase", "head", "body", "display_price_jpy", "delivery_days",
        "paid_option_title", "paid_option_price_jpy", "image_copy", "features", "industries",
        "languages", "provision_format", "fix_limit", "unit_price_jpy_per_character",
        "subscription_discount_ratio", "success_metric", "observation_window_days",
    )
    if result.get("decision") == "no_op":
        if any(result.get(key) is not None for key in nullable) or not result.get("no_op_reason"):
            raise RuntimeError("storefront_bootstrap_listing_noop_invalid")
        return
    required_create = (
        "title_stem", "catchphrase", "head", "body", "display_price_jpy", "delivery_days",
        "image_copy", "features", "industries", "languages", "success_metric",
        "observation_window_days",
    )
    if result.get("decision") != "create" or any(result.get(key) is None for key in required_create):
        raise RuntimeError("storefront_bootstrap_listing_required_field_missing")
    prices = {row["display_price_jpy"] for row in official["display_prices"]}
    if result["display_price_jpy"] not in prices:
        raise RuntimeError("storefront_bootstrap_listing_price_not_official")
    for key, name in (("features", "data[facets][163][]"), ("industries", "data[facets][164][]"),
                      ("languages", "data[facets][165][]")):
        if not set(result[key]) <= set(official["checkboxes"].get(name, [])):
            raise RuntimeError(f"storefront_bootstrap_listing_{key}_not_official")
    provision = official["radios"].get("data[Service][provision_format]", [])
    if provision and result["provision_format"] not in provision:
        raise RuntimeError("storefront_bootstrap_listing_format_not_official")
    option_prices = set(official["selects"].get("data[Option][0][price]", []))
    if option_prices:
        if (not result.get("paid_option_title")
                or str(result.get("paid_option_price_jpy") or "") not in option_prices):
            raise RuntimeError("storefront_bootstrap_listing_option_price_not_official")
    elif result.get("paid_option_title") is not None or result.get("paid_option_price_jpy") is not None:
        raise RuntimeError("storefront_bootstrap_listing_option_unavailable")
    discounts = set(official["selects"].get("data[ServiceSubscription][discount_ratio]", []))
    if discounts and result.get("subscription_discount_ratio") not in discounts:
        raise RuntimeError("storefront_bootstrap_listing_discount_not_official")


def _invoke_listing_agent(
    prompt: str, *, runner: Path, schema: Path, evidence_dir: Path,
    workdir: Path, timeout_seconds: int,
) -> dict[str, Any]:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    completed = subprocess.run([
        sys.executable, str(runner), "--task-class", "storefront-proposal-agent", "--prompt-stdin",
        "--schema", str(schema), "--evidence-dir", str(evidence_dir),
        "--task-label", "gig-storefront-bootstrap-listing", "--loop", "gig-storefront",
        "--workdir", str(workdir), "--timeout-seconds", str(timeout_seconds),
    ], input=prompt, text=True, capture_output=True, timeout=timeout_seconds + 30, check=False)
    if completed.returncode != 0:
        raise RuntimeError("storefront_bootstrap_listing_failed")
    summary_path = evidence_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    result_path = Path(str(summary.get("result_path") or "")).resolve(strict=True)
    result_path.relative_to(evidence_dir.resolve())
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if summary.get("status") != "success" or min(summary_path.stat().st_mtime, result_path.stat().st_mtime) < started:
        raise RuntimeError("storefront_bootstrap_listing_stale")
    return result


def compose_listing(
    *, selection: dict[str, Any], demand: dict[str, Any], category: dict[str, Any],
    form_snapshot: dict[str, Any], runner: Path, schema: Path,
    evidence_dir: Path, workdir: Path, timeout_seconds: int = 180,
) -> tuple[dict[str, Any], dict[str, Any]]:
    official = _official_form_options(form_snapshot)
    context = {"selection": selection, "demand": demand, "category": category,
               "official_form_options": official}
    base_prompt = """Create the first buyer-facing Coconala listing and return only the strict schema
object. The selected installed AI skill is the delivery workforce. Sell exactly selection.buyer_outcome
and require the buyer inputs listed there; do not claim personal experience, sales, speed guarantees,
live data, credentials, or work outside the selected skill. Use Japanese buyer-facing prose. title_stem
excludes the final `ます` and must end in a Japanese continuative verb form. head states outcome,
inclusions, exclusions, required inputs, deliverable and support boundary. body gives purchase steps
and unsupported work. image_copy is exactly three non-empty lines: headline, support line, then two
or three badges separated by `｜`; no price/review/sales/guarantee. Choose display_price_jpy only from
official_form_options.display_prices. Choose facet/radio/select values only from the exact official
lists; copy the literal ids and never infer an id from meaning. Use empty arrays/null when that control
is absent. When `data[Option][0][price]` has options, provide one concise paid option and copy its exact
numeric value as paid_option_price_jpy. When it is absent, both paid option fields are null.
When `data[ServiceSubscription][discount_ratio]` has options, copy one exact value;
otherwise subscription_discount_ratio is null. Choose no_op when the official form cannot
represent an honest listing and set every nullable commercial/form/metric field to null.
CONTEXT_JSON=""" + json.dumps(context, ensure_ascii=False, separators=(",", ":"))
    feedback = ""
    for attempt in range(2):
        result = _invoke_listing_agent(
            base_prompt + feedback,
            runner=runner, schema=schema, evidence_dir=evidence_dir / f"attempt-{attempt + 1}",
            workdir=workdir, timeout_seconds=timeout_seconds,
        )
        try:
            _validate_listing(result, official)
            return result, official
        except RuntimeError as error:
            if attempt == 1:
                raise
            feedback = (
                "\nThe previous schema-valid answer was rejected by the deterministic official-form "
                f"validator with `{error}`. Correct only that mismatch. Every create answer must set "
                "delivery_days, success_metric and observation_window_days. Copy each facet id only "
                "from its own named list; do not move ids between features/industries/languages."
            )
    raise RuntimeError("storefront_bootstrap_listing_unreachable")


def import_catalog(
    *, sources: list[dict[str, Any]], capabilities: dict[str, Any], runner: Path,
    schema: Path, evidence_dir: Path, workdir: Path, timeout_seconds: int = 180,
) -> dict[str, Any]:
    public_sources = [{key: row.get(key) for key in (
        "service_id", "public_url", "title", "price_jpy", "category", "scope",
        "service_version_sha256",
    )} for row in sources]
    prompt = """Map every official Coconala listing in OFFICIAL_LISTINGS exactly once to the
single installed AI skill that can honestly produce and verify it. Return only the strict schema.
The AI/Mac/tool system is the workforce; never rely on owner labor or personal experience. supported
is true only when a listed skill directly covers the buyer-visible outcome from supplied inputs.
For supported rows, copy an exact skill_path and provide concise Japanese outcome, inclusions,
deliverables, required_inputs, inquiry principles, and reusable answer patterns grounded in the
official listing. For unsupported rows set skill_path/outcome null and every array empty, explain why,
and do not invent capability. Do not change listing copy or claim revenue.
OFFICIAL_LISTINGS=""" + json.dumps(public_sources, ensure_ascii=False, separators=(",", ":")) + \
        "\nCAPABILITIES=" + json.dumps(capabilities, ensure_ascii=False, separators=(",", ":"))
    result = _invoke_listing_agent(
        prompt, runner=runner, schema=schema, evidence_dir=evidence_dir,
        workdir=workdir, timeout_seconds=timeout_seconds,
    )
    mappings = result.get("mappings")
    wanted = {str(row.get("service_id") or "") for row in sources}
    if not isinstance(mappings, list) or {row.get("service_id") for row in mappings} != wanted:
        raise RuntimeError("storefront_bootstrap_import_coverage_invalid")
    known = {row["skill_path"] for row in capabilities["skills"]}
    for row in mappings:
        arrays = ("inclusions", "deliverables", "required_inputs", "principles", "answer_patterns")
        if row.get("supported") is True:
            if (row.get("skill_path") not in known or not row.get("outcome")
                    or any(not row.get(key) for key in arrays)):
                raise RuntimeError("storefront_bootstrap_import_supported_invalid")
        elif (row.get("skill_path") is not None or row.get("outcome") is not None
              or any(row.get(key) for key in arrays)):
            raise RuntimeError("storefront_bootstrap_import_unsupported_invalid")
    return {"version": 1, "mappings": mappings}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inventory", "select"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--runner", type=Path)
    parser.add_argument("--schema", type=Path)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--workdir", type=Path, default=Path.home())
    args = parser.parse_args()
    if args.command == "inventory":
        value = inventory()
        summary = {"status": "ready", "skills": len(value["skills"]),
                   "inventory_sha256": value["inventory_sha256"]}
    else:
        if not all((args.inventory, args.runner, args.schema, args.evidence_dir)):
            parser.error("select requires --inventory --runner --schema --evidence-dir")
        value = json.loads(args.inventory.read_text(encoding="utf-8"))
        result = select_capability(
            value, runner=args.runner, schema=args.schema,
            evidence_dir=args.evidence_dir, workdir=args.workdir,
        )
        value = result
        summary = {"status": "ready", "decision": result["decision"],
                   "skill_path": result.get("skill_path")}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
