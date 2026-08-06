from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any


FIELD_PATH = re.compile(r"[-A-Za-z0-9_]+")


def _normalized(value: Any) -> str:
    return re.sub(r"\s+", " ", value if isinstance(value, str) else "").strip()


def classify_control(
    *,
    has_file: bool,
    has_checkbox: bool,
    has_select: bool,
    options: list[str],
    has_editable: bool,
) -> str:
    if has_file:
        return "upload"
    if has_select or options:
        return "select"
    if has_checkbox:
        return "check"
    if has_editable:
        return "fill"
    return "unsupported"


def extract_fields(page: Any) -> list[dict[str, Any]]:
    fields = page.locator("[data-field-path]").evaluate_all(
        r"""groups => groups.map(group => {
          const clean = value => (value || '').replace(/\s+/g, ' ').trim();
          const controls = Array.from(group.querySelectorAll(
            'input, textarea, select, button, [role="combobox"], [role="radio"]'
          ));
          const file = controls.find(x => x.matches('input[type="file"]'));
          const checkbox = controls.find(x => x.matches('input[type="checkbox"]'));
          const select = controls.find(x => x.matches('select'));
          const choices = controls.filter(x =>
            x.matches('button, [role="radio"]') && clean(x.innerText || x.textContent)
          );
          const editable = controls.find(x =>
            x.matches('input:not([type="file"]):not([type="checkbox"]):not([type="radio"]), textarea, [role="combobox"]')
          );
          const lines = (group.innerText || '').split('\n').map(clean).filter(Boolean);
          const optionTexts = choices.map(x => clean(x.innerText || x.textContent));
          const question = lines.find(line => !optionTexts.includes(line)) ||
            clean(group.getAttribute('aria-label')) || 'unlabeled_required_control';
          return {
            field_path: group.getAttribute('data-field-path') || '',
            question: question.replace(/\s*\*\s*$/, ''),
            required: lines.some(line => /\*$/.test(line)) || controls.some(x =>
              x.required || x.getAttribute('aria-required') === 'true'
            ),
            has_file: Boolean(file),
            has_checkbox: Boolean(checkbox),
            has_select: Boolean(select),
            has_editable: Boolean(editable),
            options: select
              ? Array.from(select.options).map(x => clean(x.textContent)).filter(Boolean)
              : optionTexts
          };
        }).filter(field => field.field_path)"""
    )
    for field in fields:
        field["control"] = classify_control(
            has_file=field.pop("has_file"),
            has_checkbox=field.pop("has_checkbox"),
            has_select=field.pop("has_select"),
            options=field["options"],
            has_editable=field.pop("has_editable"),
        )
    return fields


def build_actions(
    fields: list[dict[str, Any]],
    *,
    answer_map: dict[str, dict[str, Any]],
    resume_path: str,
    resume_sha256: str,
) -> dict[str, Any]:
    answers = {_normalized(key).casefold(): value for key, value in answer_map.items()}
    actions: list[dict[str, Any]] = []
    missing: list[dict[str, str]] = []
    repair: list[dict[str, str]] = []
    for field in fields:
        field_path = _normalized(field.get("field_path"))
        question = _normalized(field.get("question"))
        control = field.get("control")
        if not FIELD_PATH.fullmatch(field_path):
            repair.append({"question": question, "reason": "unsafe_field_path"})
            continue
        if control == "upload":
            actions.append(
                {
                    "kind": "upload",
                    "field_path": field_path,
                    "question": question,
                    "resume_path": resume_path,
                    "resume_sha256": resume_sha256,
                    "fact_ids": [],
                }
            )
            continue
        answer = answers.get(question.casefold())
        if not isinstance(answer, dict):
            if field.get("required") is True:
                missing.append({"question": question, "reason": "answer_missing"})
            continue
        value = _normalized(answer.get("answer"))
        fact_ids = answer.get("fact_ids")
        if not value or not isinstance(fact_ids, list) or not fact_ids:
            missing.append({"question": question, "reason": "grounding_missing"})
            continue
        if control not in {"fill", "select", "check"}:
            repair.append({"question": question, "reason": "unsupported_control"})
            continue
        if control == "select":
            options = [_normalized(item) for item in field.get("options", [])]
            if options and value.casefold() not in {item.casefold() for item in options}:
                repair.append({"question": question, "reason": "option_not_found"})
                continue
        actions.append(
            {
                "kind": control,
                "field_path": field_path,
                "question": question,
                "answer": value,
                "fact_ids": fact_ids,
            }
        )
    status = "needs_repair" if repair else "needs_fact" if missing else "ready"
    return {"version": 1, "status": status, "actions": actions, "missing": missing, "repair": repair}


def _group(page: Any, field_path: str) -> Any:
    if not FIELD_PATH.fullmatch(field_path):
        raise ValueError("unsafe Ashby field path")
    return page.locator(f'[data-field-path="{field_path}"]')


def execute_actions(page: Any, actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for action in actions:
        group = _group(page, action["field_path"])
        kind = action["kind"]
        value = action.get("answer")
        if kind == "upload":
            path = Path(action["resume_path"])
            if hashlib.sha256(path.read_bytes()).hexdigest() != action["resume_sha256"]:
                raise ValueError("resume SHA-256 mismatch")
            control = group.locator('input[type="file"]')
            control.set_input_files(str(path))
            verified = Path(control.input_value().replace("\\", "/")).name == path.name
        elif kind == "check":
            control = group.locator('input[type="checkbox"]')
            control.check()
            verified = control.is_checked()
        elif kind == "select":
            native = group.locator("select")
            if native.count():
                native.select_option(label=value)
                verified = native.locator("option:checked").inner_text().strip() == value
            else:
                choice = group.get_by_role("button", name=value, exact=True)
                if not choice.count():
                    choice = group.get_by_role("radio", name=value, exact=True)
                choice.click()
                verified = choice.get_attribute("aria-checked") == "true" or choice.get_attribute("aria-pressed") == "true" or choice.get_attribute("data-state") in {"checked", "selected", "on"}
        else:
            control = group.locator('input:not([type="file"]), textarea, [role="combobox"]').first
            control.fill(value)
            if control.get_attribute("role") == "combobox":
                control.press("ArrowDown")
                control.press("Enter")
            verified = control.input_value().strip() == value
        if not verified:
            raise RuntimeError(f"field verification failed: {action['question']}")
        receipts.append(
            {
                "question": action["question"],
                "answer": value if kind != "upload" else Path(action["resume_path"]).name,
                "fact_ids": action.get("fact_ids", []),
                "field_path": action["field_path"],
                "kind": kind,
                "verified": True,
            }
        )
    return receipts


def validate_fill_result(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("status") != "ready":
        raise ValueError("resident fill result is not ready")
    receipts = value.get("receipts")
    if not isinstance(receipts, list) or not receipts:
        raise ValueError("resident fill result has no receipts")
    allowed = {"fill", "select", "check", "upload"}
    if any(
        not isinstance(receipt, dict)
        or receipt.get("kind") not in allowed
        or receipt.get("verified") is not True
        for receipt in receipts
    ):
        raise ValueError("resident fill result contains an unsafe action")
    return {"status": "pre_submit_ready", "verified_count": len(receipts)}


def _write_private(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
    os.chmod(path, 0o600)


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic Ashby inspect/fill CLI")
    parser.add_argument("mode", choices=("inspect", "fill", "verify"))
    parser.add_argument("--endpoint")
    parser.add_argument("--url")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--answers", type=Path)
    parser.add_argument("--resume", type=Path)
    args = parser.parse_args()
    if args.mode == "verify":
        result = json.loads(args.output.read_text(encoding="utf-8"))
        print(json.dumps(validate_fill_result(result), sort_keys=True))
        return
    if not args.endpoint or not args.url:
        parser.error("inspect/fill require --endpoint and --url")
    from playwright.sync_api import sync_playwright

    url = args.url if args.url.rstrip("/").endswith("/application") else f"{args.url.rstrip('/')}/application"
    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(args.endpoint)
        page = browser.contexts[0].new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            page.locator("[data-field-path]").first.wait_for(timeout=30_000)
            fields = extract_fields(page)
            if args.mode == "inspect":
                result = {"version": 1, "status": "inspected", "url": page.url, "fields": fields}
            else:
                if not args.answers or not args.resume:
                    parser.error("fill requires --answers and --resume")
                answer_map = json.loads(args.answers.read_text(encoding="utf-8"))
                resume_sha256 = hashlib.sha256(args.resume.read_bytes()).hexdigest()
                plan = build_actions(fields, answer_map=answer_map, resume_path=str(args.resume.resolve()), resume_sha256=resume_sha256)
                receipts = execute_actions(page, plan["actions"]) if plan["status"] == "ready" else []
                result = {**plan, "url": page.url, "fields": fields, "receipts": receipts}
            _write_private(args.output, result)
            print(json.dumps({"status": result["status"], "output": str(args.output)}))
        finally:
            page.close()


if __name__ == "__main__":
    main()
