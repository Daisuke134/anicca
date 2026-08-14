#!/usr/bin/env python3
"""Run one browserless-planned, at-most-one Lancers application tick."""
from __future__ import annotations

import argparse, inspect, json, os, re, shutil, subprocess, sys, uuid
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
import importlib.util
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence, TextIO

HERE = Path(__file__).resolve().parent
SKILLS_ROOT = HERE.parents[2]
SKILLS = SKILLS_ROOT
REPO = SKILLS_ROOT.parent
STATUS_PATH = HERE / "status.py"
APPLICATION_TICK_PATH = HERE / "application_tick.py"
AGENT_RUNNER = SKILLS_ROOT / "agent-runner" / "agent_runner.py"
AGENT_RUNNER_PATH = AGENT_RUNNER
PLANNER_SCHEMA = SKILLS_ROOT / "gig-work" / "schemas" / "application_decisions.schema.json"
SCHEMA_PATH = PLANNER_SCHEMA
PLATFORM = "lancers"
MAX_OPPORTUNITIES = 20
DEFAULT_DISCOVERY_QUERY = "SNS運用"
DISCOVERY_QUERIES = (
    "SNS運用", "SNS投稿", "コンテンツ制作", "X運用", "LinkedIn",
    "B2Bマーケティング", "AI活用", "継続依頼", "長期", "月額",
)
PLANNER_TASK_CLASS = "application-intent-planner"
PLANNER_TIMEOUT_SECONDS = 180
DEFAULT_STATE_PATH = Path.home() / ".local/state/anicca/lancers/application.json"
DEFAULT_EVIDENCE_ROOT = Path.home() / ".local/state/anicca/lancers/planner"
DEFAULT_EVIDENCE_DIR = DEFAULT_EVIDENCE_ROOT
DECISION_FIELDS = frozenset({"request_id", "business_class", "reason_codes", "proposal_text", "price_jpy", "deliver_date"})
BUSINESS_CLASSES = frozenset({"submit_required", "hard_prohibited"})
HARD_PROHIBITION_CLASSES = {
    "video_or_animation": "video editing/production, live-action filming, AI video, animation, or MV",
    "physical_or_onsite": "on-site work or physical making/assembly/cleaning/repair/cooking/sewing/woodwork/model making/packing/shipping/delivery/receipt",
    "mandatory_human_presence": "human face appearance/performance/voice recording/phone support/mandatory live call or mandatory video interview",
    "explicit_ai_prohibition": "explicit prohibition on AI use",
    "illegal_or_unsafe": "illegal or unsafe work",
    "missing_legal_qualification": "legally required qualification that Kosuke does not hold",
    "mandatory_attribute_fabrication": "mandatory personal attribute that cannot be answered truthfully without fabrication",
}
PUBLIC_FIELDS = ("schema_version", "record_type", "platform", "external_id", "title", "description", "url", "category", "budget_type", "budget_min_minor", "budget_max_minor", "currency", "buyer_external_id", "observed_at")
DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
ID_RE = re.compile(r"^[0-9]+$")
KANA_RE = re.compile(r"[ぁ-ゖァ-ヺ]")
FORBIDDEN_TERMS = ("receipt", "gate", "agent", "model", "browser", "token", "prompt", "internal id", "レシート", "ゲート", "エージェント", "モデル", "ブラウザ", "トークン", "プロンプト", "内部ID")
FORBIDDEN_RE = re.compile("|".join(re.escape(term).replace(r"\ ", r"[ _]") for term in FORBIDDEN_TERMS), re.IGNORECASE)
RETAIN_EVIDENCE_ERRORS = frozenset({"planner_runner_failed", "planner_contract_invalid"})

def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None: raise RuntimeError("dependency_unavailable")
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module)
    return module

status = _load("_anicca_lancers_application_loop_status", STATUS_PATH)
application_tick = _load("_anicca_lancers_application_loop_tick", APPLICATION_TICK_PATH)

@dataclass(frozen=True)
class ApplicationLoopResult:
    ok: bool
    submitted: bool = False
    application_verified: bool = False
    reason: Optional[str] = None
    error: Optional[str] = None
    project_id: Optional[str] = None
    provider_proposal_id: Optional[str] = None
    cleanup_error: Optional[str] = None
    observed_count: Optional[int] = None
    eligible_count: Optional[int] = None
    verified_count: Optional[int] = None
    provider_terminal_blocked_count: Optional[int] = None
    verified_project_ids: Optional[tuple[str, ...]] = None
    verified_provider_proposal_ids: Optional[tuple[str, ...]] = None
    provider_terminal_blocked_project_ids: Optional[tuple[str, ...]] = None
    unresolved_project_id: Optional[str] = None
    planner_expected_count: Optional[int] = None
    planner_returned_count: Optional[int] = None

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {"ok": bool(self.ok), "platform": PLATFORM, "submitted": bool(self.submitted), "application_verified": bool(self.application_verified)}
        for key in ("reason", "error", "project_id", "provider_proposal_id", "cleanup_error"):
            value = getattr(self, key)
            if value is not None: result[key] = value
        for key in ("observed_count", "eligible_count", "verified_count", "provider_terminal_blocked_count"):
            value = getattr(self, key)
            result[key] = int(value) if isinstance(value, int) and not isinstance(value, bool) else 0
        for key in ("planner_expected_count", "planner_returned_count"):
            value = getattr(self, key)
            if isinstance(value, int) and not isinstance(value, bool): result[key] = value
        for key in ("verified_project_ids", "verified_provider_proposal_ids", "provider_terminal_blocked_project_ids"):
            value = getattr(self, key)
            if value: result[key] = list(value)
        if self.unresolved_project_id is not None: result["unresolved_project_id"] = self.unresolved_project_id
        return result

def _tick_date(value: object) -> date:
    if isinstance(value, datetime):
        if value.tzinfo is None: raise ValueError
        return value.astimezone(timezone.utc).date()
    if isinstance(value, date): return value
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            return parsed.astimezone(timezone.utc).date() if parsed.tzinfo else date.fromisoformat(value.strip())
        except (TypeError, ValueError, OverflowError): pass
    raise ValueError

def _discovery_query(value: object) -> str:
    try:
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, str):
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        else:
            return DEFAULT_DISCOVERY_QUERY
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return DEFAULT_DISCOVERY_QUERY
        slot = int(parsed.astimezone(timezone.utc).timestamp() // 1800) % len(DISCOVERY_QUERIES)
        return DISCOVERY_QUERIES[slot]
    except (TypeError, ValueError, OverflowError, OSError):
        return DEFAULT_DISCOVERY_QUERY

def _run_default_discovery(tick_value: object, timeout: float, state_path: Path) -> Mapping[str, object]:
    first = _discovery_query(tick_value)
    start = DISCOVERY_QUERIES.index(first)
    last: Mapping[str, object] = {"ok": False, "error": "no_normalized_opportunities", "opportunities": []}
    for offset in range(len(DISCOVERY_QUERIES)):
        query = DISCOVERY_QUERIES[(start + offset) % len(DISCOVERY_QUERIES)]
        last = status.run_discovery(query=query, limit=MAX_OPPORTUNITIES, timeout=timeout)
        if last.get("ok") is True:
            opportunities = last.get("opportunities")
            if isinstance(opportunities, Sequence) and not isinstance(opportunities, (str, bytes, bytearray)):
                try: remaining, _ = _filter_claimed_rows(opportunities, state_path)
                except Exception: return last
                if not remaining: continue
            return last
        if last.get("error") != "no_normalized_opportunities":
            return last
    return last

def _snapshot(rows: Sequence[Mapping[str, object]], today: date) -> dict[str, object]:
    if len(rows) > MAX_OPPORTUNITIES: raise ValueError
    result, ids = [], set()
    for row in rows:
        project_id = row.get("external_id") if isinstance(row, Mapping) else None
        if not isinstance(project_id, str) or ID_RE.fullmatch(project_id) is None or project_id in ids: raise ValueError
        ids.add(project_id); compact = {key: row.get(key) for key in PUBLIC_FIELDS}
        for key, maximum in (("title", 200), ("category", 120), ("description", 2000)):
            if isinstance(compact[key], str): compact[key] = compact[key][:maximum]
        result.append(compact)
    return {"tick_date": today.isoformat(), "opportunities": result}

PLANNER_RULES = ("Lancersの公開案件だけを読むapplication-intent plannerである。ブラウザ・認証・外部操作はできない。"
    "各案件を実際の公開内容全体から自分で判断し、指定schemaのJSONだけを返す。応募可能ならsubmit_required、reason_codesは空、買い手向けの具体的な日本語proposalを200〜3000文字、正直な価格、現実的な納期で返す。"
    "hard_prohibitedは案件全体が次のいずれかを必須とする場合だけ使う: "
    + "; ".join(f"{key}={value}" for key, value in HARD_PROHIBITION_CLASSES.items()) + "。"
    "hard_prohibitedではreason_codes[0]を正確なclass key、reason_codes[1]をtitle・description・categoryのいずれかに連続して存在する200文字以内の原文引用にし、proposal・price・dateはnullにする。任意・推奨・否定・引用中の単語だけで拒否しない。"
    "案件全体から納品可能性をpriorityより先に確定する。完成動画そのものの生成・編集・書き出しが必須ならvideo_or_animation、企画・構成・台本・文章だけで完成動画制作が不要ならvideo_or_animationではない。機械的なkeyword ruleは使わない。"
    "経験の不確実さ、弱いportfolio、低予算、難易度、広いまたは曖昧なscope、単発、継続性不足、Adobe実績不明、任意の相談は拒否理由ではない。正確な同分野実績がなくても、確認済みの転用可能な能力と案件固有の実行planで応募し、未作成物はplanと明示して捏造しない。"
    "納品可能性を確定した後の優先順は、定期購入・保守・運用、次にsystem・automation・AI・web・高報酬、次にその他の非同期作業。hard prohibition必須案件を継続・AI・高報酬・低予算・簡単そうという理由でsubmit_requiredへ変えない。実行可能な低優先案件を省略しない。submit_requiredを先に並べ、強い順に返す。"
    "既知のbudget_max_minorを超えない。budgetが応相談・未定でも拒否しない。一律の最低価格や固定上限を設けない。競争力とscopeに合う価格、実行可能な最短納期を選ぶ。"
    "live call・video meeting・顔出し・音声収録を自発的に約束せず、任意ならLancersメッセージと文書による非同期確認を提案する。必須ならhard_prohibitedにする。"
    "提案文には次の語を含めない: " + ", ".join(FORBIDDEN_TERMS) + "。送信・受注・納品・支払済みと主張しない。\nSNAPSHOT:\n")

def build_planner_prompt(rows: Sequence[Mapping[str, object]], today: date) -> str:
    return PLANNER_RULES + json.dumps(_snapshot(rows, _tick_date(today)), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def _invoke_agent(prompt: str, evidence_dir: Path, task_class: str, schema_path: Path, label: str) -> Mapping[str, object]:
    command = [sys.executable, str(AGENT_RUNNER), "--task-class", task_class, "--prompt-stdin", "--schema", str(schema_path), "--evidence-dir", str(evidence_dir), "--task-label", label, "--loop", "lancers-application", "--workdir", str(SKILLS_ROOT.parent)]
    try:
        completed = subprocess.run(command, input=prompt, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=PLANNER_TIMEOUT_SECONDS + 30)
        if completed.returncode != 0: raise ValueError
        evidence = Path(evidence_dir); summary = json.loads((evidence / "summary.json").read_text(encoding="utf-8"))
        result_path = Path(str(summary["result_path"])).resolve(); result_path.relative_to(evidence.resolve())
        if summary.get("status") != "success": raise ValueError
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if not isinstance(result, Mapping): raise ValueError
        return result
    except Exception: raise RuntimeError("agent_runner_failed") from None

def _planner_runtime_schema(prompt: str, evidence_dir: Path) -> Path:
    snapshot = json.loads(prompt.rsplit("SNAPSHOT:\n", 1)[1])
    ids = [row["external_id"] for row in snapshot["opportunities"]]
    schema = json.loads(PLANNER_SCHEMA.read_text(encoding="utf-8"))
    decisions = schema["properties"]["decisions"]
    decisions["minItems"] = 1
    decisions["maxItems"] = len(ids)
    decisions["items"]["properties"]["request_id"]["enum"] = ids
    path = Path(evidence_dir) / "planner-runtime.schema.json"
    path.write_text(json.dumps(schema, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.chmod(path, 0o600)
    return path

def invoke_planner(prompt: str, evidence_dir: Path) -> Mapping[str, object]:
    return _invoke_agent(prompt, evidence_dir, PLANNER_TASK_CLASS, _planner_runtime_schema(prompt, evidence_dir), "lancers-application-intent")

def _default_planner(prompt: str, evidence: Path) -> Mapping[str, object]:
    return invoke_planner(prompt, evidence)

def _safe_proposal(value: object, ids: Sequence[str]) -> bool:
    if not isinstance(value, str) or not 200 <= len(value) <= 3000: return False
    if len(KANA_RE.findall(value)) < max(20, len(re.findall(r"[A-Za-z]", value)) + 1): return False
    if FORBIDDEN_RE.search(value): return False
    return not any(re.search(rf"(?<![0-9]){re.escape(project_id)}(?![0-9])", value) for project_id in ids)

def _valid_date(value: object, today: date) -> bool:
    if not isinstance(value, str) or DATE_RE.fullmatch(value) is None: return False
    try: parsed = date.fromisoformat(value)
    except (TypeError, ValueError, OverflowError): return False
    return value == parsed.isoformat() and today + timedelta(days=1) <= parsed <= today + timedelta(days=60)

def _valid_observed_budget(row: object) -> bool:
    if not isinstance(row, Mapping): return False
    minimum, maximum = row.get("budget_min_minor"), row.get("budget_max_minor")
    return not any(value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0) for value in (minimum, maximum)) and not (minimum is not None and maximum is not None and minimum > maximum)

def _validate(rows: Sequence[Mapping[str, object]], value: object, today: date) -> dict[str, Mapping[str, object]]:
    try:
        if not isinstance(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")), Mapping) or not isinstance(value, Mapping): raise ValueError
        decisions = value.get("decisions")
        if set(value) != {"decisions"} or not isinstance(decisions, list) or not decisions or len(decisions) > len(rows): raise ValueError
        expected = [str(row["external_id"]) for row in rows]; rows_by_id = {str(row["external_id"]): row for row in rows}; found: dict[str, Mapping[str, object]] = {}
        for decision in decisions:
            if not isinstance(decision, Mapping) or set(decision) != DECISION_FIELDS: raise ValueError
            project_id, business_class, reasons = decision.get("request_id"), decision.get("business_class"), decision.get("reason_codes")
            if not isinstance(project_id, str) or project_id not in expected or project_id in found or business_class not in BUSINESS_CLASSES or not isinstance(reasons, list) or any(not isinstance(reason, str) or not reason.strip() for reason in reasons) or len(set(reasons)) != len(reasons): raise ValueError
            proposal, price, due = decision.get("proposal_text"), decision.get("price_jpy"), decision.get("deliver_date")
            if business_class == "hard_prohibited":
                if proposal is not None or price is not None or due is not None or len(reasons) < 2 or reasons[0] not in HARD_PROHIBITION_CLASSES: raise ValueError
                public_row = rows_by_id[project_id]
                public_text = "\n".join(str(public_row.get(key) or "") for key in ("title", "description", "category"))
                if not 1 <= len(reasons[1]) <= 200 or reasons[1] not in public_text: raise ValueError
            elif reasons or not _safe_proposal(proposal, expected) or isinstance(price, bool) or not isinstance(price, int) or price < 1 or not _valid_date(due, today): raise ValueError
            found[project_id] = decision
        for row in rows:
            if not _valid_observed_budget(row): raise ValueError
        for project_id, decision in found.items():
            row, price = rows_by_id[project_id], decision.get("price_jpy")
            maximum = row.get("budget_max_minor")
            if decision["business_class"] == "submit_required" and (row.get("currency") != "JPY" or (maximum is not None and price > maximum)): raise ValueError
        return found
    except Exception: raise ValueError from None

def validate_decisions(rows: Sequence[Mapping[str, object]], value: object, today: date) -> list[str]:
    try: _validate(rows, value, _tick_date(today))
    except Exception: return ["planner_failed"]
    return []

def _reset(path: Path) -> None:
    if path.is_symlink() or path.is_file(): path.unlink()
    elif path.is_dir(): shutil.rmtree(path)
    path.mkdir(parents=True, mode=0o700, exist_ok=False); os.chmod(path, 0o700)

def _tick_result(value: object, project_id: str) -> ApplicationLoopResult:
    raw = value.to_dict() if callable(getattr(value, "to_dict", None)) else value
    if not isinstance(raw, Mapping): return ApplicationLoopResult(False, error="submission_uncertain", project_id=project_id)
    clean = lambda item: item if isinstance(item, str) and re.fullmatch(r"[A-Za-z0-9._:-]{1,256}", item) else None
    found = raw.get("project_id") if isinstance(raw.get("project_id"), str) and ID_RE.fullmatch(raw["project_id"]) else project_id
    reason, error = clean(raw.get("reason")), clean(raw.get("error"))
    submitted, raw_verified = raw.get("submitted") is True, raw.get("application_verified") is True
    provider_verified = raw_verified or reason in {"duplicate_project", "provider_reconciled"}
    provider_blocked = reason == "provider_terminal_blocked"
    raw_error = raw.get("error")
    raw_ok = raw.get("ok") if isinstance(raw.get("ok"), bool) else None
    provider_id = clean(raw.get("provider_proposal_id"))
    invalid = raw_error is not None or (raw_ok is False and not provider_blocked) or not (provider_verified or provider_blocked)
    if invalid:
        return ApplicationLoopResult(False, submitted, False, reason, error or "submission_uncertain", found, provider_id)
    return ApplicationLoopResult(raw_ok is not False, submitted, raw_verified, reason, None, found, provider_id)

def _emit(result: ApplicationLoopResult, stream: TextIO) -> None:
    stream.write(json.dumps(result.to_dict(), ensure_ascii=False, separators=(",", ":")) + "\n"); stream.flush()

def _pending_submitter_override(*_args: object, **_kwargs: object) -> Mapping[str, object]:
    raise RuntimeError("pending_reconciliation_submitter_disabled")

def _reconcile_pending(descriptor: Mapping[str, object], state_path: Path) -> ApplicationLoopResult:
    project_id = descriptor.get("project_id")
    if not isinstance(project_id, str) or not project_id:
        return ApplicationLoopResult(False, error="state_invalid")
    try:
        value = application_tick.run_live_tick(
            project_id=project_id,
            proposal_text="pending reconciliation",
            proposed_amount_minor=descriptor["amount_minor"],
            delivery_due_on=descriptor["delivery_due_on"],
            state_path=Path(state_path),
            submitter_override=_pending_submitter_override,
        )
    except Exception:
        return ApplicationLoopResult(False, error="submission_uncertain", project_id=project_id)
    result = _tick_result(value, project_id)
    verified = (result,) if _provider_verified(result) else ()
    blocked = (project_id,) if _provider_terminal_blocked(result) else ()
    return _batch_summary(result, 1, 1, verified, blocked, unresolved_project_id=None if verified or blocked else project_id, submitted=result.submitted)

def run_reconcile_only(state_path: Path, output_stream: Optional[TextIO] = None) -> dict[str, object]:
    try:
        descriptors = application_tick.shared.read_pending_descriptors(Path(state_path))
    except Exception:
        result = {
            "ok": False,
            "platform": PLATFORM,
            "submitted": False,
            "application_verified": False,
            "reconciled_project_ids": [],
            "verified_project_ids": [],
            "unresolved_project_ids": [],
            "error": "state_invalid",
        }
        if output_stream is not None:
            output_stream.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
            output_stream.flush()
        return result

    reconciled_project_ids = []
    verified_project_ids = []
    unresolved_project_ids = []
    for descriptor in descriptors:
        project_id = descriptor["project_id"]
        reconciled_project_ids.append(project_id)
        result = _reconcile_pending(descriptor, Path(state_path))
        if _provider_verified(result):
            verified_project_ids.append(project_id)
        else:
            unresolved_project_ids.append(project_id)
    summary = {
        "ok": not unresolved_project_ids,
        "platform": PLATFORM,
        "submitted": False,
        "application_verified": bool(verified_project_ids),
        "reconciled_project_ids": reconciled_project_ids,
        "verified_project_ids": verified_project_ids,
        "unresolved_project_ids": unresolved_project_ids,
    }
    if output_stream is not None:
        output_stream.write(json.dumps(summary, ensure_ascii=False, separators=(",", ":")) + "\n")
        output_stream.flush()
    return summary

def _submit(fn: Callable[..., object], row: Mapping[str, object], proposal: str, amount: int, due: str, state_path: Path) -> object:
    values = {"project_id": str(row["external_id"]), "proposal_text": proposal, "proposed_amount_minor": amount, "delivery_due_on": due, "state_path": state_path}
    try:
        parameters = inspect.signature(fn).parameters
        keyword = any(parameter.kind == parameter.VAR_KEYWORD for parameter in parameters.values()) or {"project_id", "proposal_text", "proposed_amount_minor", "delivery_due_on"}.issubset(parameters)
    except (TypeError, ValueError): keyword = False
    return fn(**values) if keyword else fn(row, proposal, amount, due)

def _filter_claimed_rows(rows: Sequence[Mapping[str, object]], state_path: Path) -> tuple[list[Mapping[str, object]], Optional[str]]:
    if any(not _valid_observed_budget(row) for row in rows): raise ValueError
    ids = [row.get("external_id") if isinstance(row, Mapping) else None for row in rows]
    duplicate_ids = {project_id for project_id in ids if isinstance(project_id, str) and ids.count(project_id) > 1}
    remaining, first_claimed = [], None
    for row, project_id in zip(rows, ids):
        if not isinstance(project_id, str) or ID_RE.fullmatch(project_id) is None or project_id in duplicate_ids or not application_tick.state_has_claim(Path(state_path), project_id):
            remaining.append(row)
        elif first_claimed is None:
            first_claimed = project_id
    return remaining, first_claimed

def _provider_verified(result: ApplicationLoopResult) -> bool:
    return result.error is None and result.ok and (result.application_verified or result.reason in {"duplicate_project", "provider_reconciled"})

def _provider_terminal_blocked(result: ApplicationLoopResult) -> bool:
    return result.error == "provider_terminal_blocked" or (result.error is None and result.reason == "provider_terminal_blocked")

def _batch_summary(
    result: ApplicationLoopResult, observed_count: int, eligible_count: int,
    verified: Sequence[ApplicationLoopResult], blocked: Sequence[str],
    *, unresolved_project_id: Optional[str] = None, ok: Optional[bool] = None,
    submitted: Optional[bool] = None,
) -> ApplicationLoopResult:
    verified_projects = tuple(item.project_id for item in verified if item.project_id is not None)
    verified_proposals = tuple(item.provider_proposal_id for item in verified if item.provider_proposal_id is not None)
    success = result.ok if ok is None else ok
    return replace(result, ok=success, submitted=any(item.submitted for item in verified) if submitted is None else submitted, observed_count=observed_count, eligible_count=eligible_count, verified_count=len(verified), provider_terminal_blocked_count=len(blocked), verified_project_ids=verified_projects, verified_provider_proposal_ids=verified_proposals, provider_terminal_blocked_project_ids=tuple(blocked), unresolved_project_id=unresolved_project_id)

def _plan_and_submit(rows: Sequence[Mapping[str, object]], today: date, evidence: Path, planner: Optional[Callable[..., object]], safety_verifier: Optional[Callable[..., object]], submitter: Optional[Callable[..., object]], state_path: Path) -> ApplicationLoopResult:
    observed_count = len(rows)
    try:
        rows, claimed_project_id = _filter_claimed_rows(rows, state_path)
        if not rows:
            return _batch_summary(ApplicationLoopResult(True, reason="duplicate_project", project_id=claimed_project_id), observed_count, 0, (), ())
        prompt = build_planner_prompt(rows, today)
    except Exception: return _batch_summary(ApplicationLoopResult(False, error="planner_contract_invalid"), observed_count, 0, (), ())
    try: planned = (planner or _default_planner)(prompt, evidence)
    except Exception: return _batch_summary(ApplicationLoopResult(False, error="planner_runner_failed", planner_expected_count=len(rows)), observed_count, 0, (), ())
    returned = len(planned.get("decisions")) if isinstance(planned, Mapping) and isinstance(planned.get("decisions"), list) else None
    try: decisions = _validate(rows, planned, today)
    except Exception: return _batch_summary(ApplicationLoopResult(False, error="planner_contract_invalid", planner_expected_count=len(rows), planner_returned_count=returned), observed_count, 0, (), ())
    rows_by_id = {str(row["external_id"]): row for row in rows}
    eligible = [(rows_by_id[project_id], decision) for project_id, decision in decisions.items() if decision.get("business_class") == "submit_required"]
    if not eligible:
        return _batch_summary(ApplicationLoopResult(True, reason="no_eligible_project"), observed_count, 0, (), ())
    verified, blocked = [], []
    for row, decision in eligible[:1]:
        project_id, proposal = str(row["external_id"]), str(decision["proposal_text"])
        amount, due = int(decision["price_jpy"]), str(decision["deliver_date"])
        try:
            value = application_tick.run_live_tick(project_id=project_id, proposal_text=proposal, proposed_amount_minor=amount, delivery_due_on=due, state_path=state_path) if submitter is None else _submit(submitter, row, proposal, amount, due, state_path)
            current = _tick_result(value, project_id)
        except Exception:
            current = ApplicationLoopResult(False, error="submission_uncertain", project_id=project_id)
        if _provider_verified(current):
            verified.append(current)
            continue
        if _provider_terminal_blocked(current):
            blocked.append(project_id)
            continue
        return _batch_summary(current, observed_count, len(eligible), verified, blocked, unresolved_project_id=project_id, submitted=any(item.submitted for item in verified))
    final = verified[-1] if verified else ApplicationLoopResult(True, reason="provider_terminal_blocked", project_id=blocked[-1] if blocked else None)
    return _batch_summary(final, observed_count, len(eligible), verified, blocked, ok=True, submitted=any(item.submitted for item in verified))

def run_loop(*, state_path: Path = DEFAULT_STATE_PATH, evidence_root: Optional[Path] = None, discoverer: Optional[Callable[..., Mapping[str, object]]] = None, planner: Optional[Callable[..., object]] = None, safety_verifier: Optional[Callable[..., object]] = None, submitter: Optional[Callable[..., object]] = None, clock: Optional[Callable[[], object]] = None, discovery: Optional[Callable[..., Mapping[str, object]]] = None, now: Optional[Callable[[], object]] = None, evidence_dir: Optional[Path] = None, output_stream: Optional[TextIO] = None, query: Optional[str] = None, timeout: float = 20.0) -> dict[str, object]:
    try:
        pending = application_tick.read_pending_descriptor(Path(state_path))
    except Exception:
        result = ApplicationLoopResult(False, error="state_invalid")
        if output_stream is not None: _emit(result, output_stream)
        return result.to_dict()
    quarantined_project_id = None
    if pending is not None:
        pending_result = _reconcile_pending(pending, Path(state_path))
        if pending_result.error != "submission_uncertain":
            if output_stream is not None: _emit(pending_result, output_stream)
            return pending_result.to_dict()
        quarantined_project_id = pending_result.unresolved_project_id or pending_result.project_id
    root = Path(evidence_root if evidence_root is not None else evidence_dir or DEFAULT_EVIDENCE_ROOT); result = ApplicationLoopResult(False, error="planner_runner_failed"); cleanup_failed = False; evidence: Optional[Path] = None
    try:
        try: tick_value = (clock or now or (lambda: datetime.now(timezone.utc)))()
        except Exception: tick_value = None
        try:
            _reset(root); evidence = root / f"run-{uuid.uuid4().hex}"; evidence.mkdir(mode=0o700, exist_ok=False); os.chmod(evidence, 0o700)
        except Exception: evidence = None
        if evidence is not None:
            try:
                source = discoverer or discovery
                observed = source(query=query if query is not None else _discovery_query(tick_value), limit=MAX_OPPORTUNITIES, timeout=timeout) if source is not None or query is not None else _run_default_discovery(tick_value, timeout, Path(state_path))
            except Exception: observed = None
            if observed is None: result = ApplicationLoopResult(False, error="discovery_failed")
            elif not isinstance(observed, Mapping): result = ApplicationLoopResult(False, error="discovery_failed")
            else:
                error, opportunities = observed.get("error"), observed.get("opportunities", [])
                if observed.get("ok") is not True and not (error == "no_normalized_opportunities" and "opportunities" in observed and not opportunities):
                    clean_error = error if isinstance(error, str) and re.fullmatch(r"[A-Za-z0-9._:-]{1,256}", error or "") else "discovery_failed"
                    result = ApplicationLoopResult(False, error=clean_error)
                elif error is not None and error != "no_normalized_opportunities":
                    result = ApplicationLoopResult(False, error=error if isinstance(error, str) and re.fullmatch(r"[A-Za-z0-9._:-]{1,256}", error) else "discovery_failed")
                elif isinstance(opportunities, (str, bytes, bytearray)) or not isinstance(opportunities, Sequence): result = ApplicationLoopResult(False, error="discovery_failed")
                elif not opportunities: result = ApplicationLoopResult(True, reason="no_eligible_project")
                else:
                    try: today = _tick_date(tick_value)
                    except Exception: result = ApplicationLoopResult(False, error="planner_contract_invalid")
                    else: result = _plan_and_submit(opportunities, today, evidence, planner, safety_verifier, submitter, Path(state_path))
    finally:
        if result.error not in RETAIN_EVIDENCE_ERRORS:
            try:
                if root.is_symlink() or root.is_file(): root.unlink()
                elif root.is_dir(): shutil.rmtree(root)
            except OSError: cleanup_failed = True
    if cleanup_failed:
        result = replace(result, ok=False, error=result.error or "evidence_cleanup_failed", cleanup_error="evidence_cleanup_failed" if result.error else None)
    if quarantined_project_id is not None and result.unresolved_project_id is None:
        result = replace(result, unresolved_project_id=quarantined_project_id)
    if output_stream is not None: _emit(result, output_stream)
    return result.to_dict()

run_application_loop = run_loop
run_once = run_loop

def main(argv: Optional[Sequence[str]] = None, *, discovery: Optional[Callable[..., Mapping[str, object]]] = None, planner: Optional[Callable[..., object]] = None, submitter: Optional[Callable[..., object]] = None, now: Optional[Callable[[], object]] = None, clock: Optional[Callable[[], object]] = None, stdout: Optional[TextIO] = None) -> int:
    parser = argparse.ArgumentParser(allow_abbrev=False); parser.add_argument("--json", action="store_true", required=True); parser.add_argument("--reconcile-only", action="store_true"); parser.add_argument("--state-path", default=str(DEFAULT_STATE_PATH)); args = parser.parse_args(list(argv) if argv is not None else None)
    output_stream = sys.stdout if stdout is None else stdout
    result = run_reconcile_only(Path(args.state_path), output_stream=output_stream) if args.reconcile_only else run_loop(discoverer=discovery, planner=planner, submitter=submitter, clock=clock or now, state_path=Path(args.state_path), output_stream=output_stream)
    return 0 if result["ok"] else 1

__all__ = ["AGENT_RUNNER", "AGENT_RUNNER_PATH", "ApplicationLoopResult", "DEFAULT_EVIDENCE_DIR", "DEFAULT_EVIDENCE_ROOT", "DEFAULT_STATE_PATH", "PLANNER_SCHEMA", "SCHEMA_PATH", "application_tick", "build_planner_prompt", "invoke_planner", "main", "run_application_loop", "run_loop", "run_once", "run_reconcile_only", "status", "validate_decisions"]

if __name__ == "__main__": raise SystemExit(main())
