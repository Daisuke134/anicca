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
PLANNER_TASK_CLASS = "application-intent-planner"
PLANNER_TIMEOUT_SECONDS = 180
DEFAULT_STATE_PATH = Path.home() / ".local/state/anicca/lancers/application.json"
DEFAULT_EVIDENCE_ROOT = Path.home() / ".local/state/anicca/lancers/planner"
DEFAULT_EVIDENCE_DIR = DEFAULT_EVIDENCE_ROOT
DECISION_FIELDS = frozenset({"request_id", "eligibility", "reason_codes", "proposal_text", "price_jpy", "deliver_date", "qualification"})
QUALIFICATION_FIELDS = frozenset({"commercial_buyer_evidence", "ongoing_sns_outsourcing_evidence", "expected_platform_fee_jpy", "expected_ai_cost_jpy", "expected_subcontractor_cost_jpy", "expected_revision_refund_allowance_jpy", "cost_source_version"})
QUALIFICATION_COST_FIELDS = ("expected_platform_fee_jpy", "expected_ai_cost_jpy", "expected_subcontractor_cost_jpy", "expected_revision_refund_allowance_jpy")
JAPANESE_TEXT_RE = re.compile(r"[ぁ-ゖァ-ヺ一-龯]")
COMMERCIAL_BUYER_SIGNAL_RE = re.compile(r"依頼主の業種[:：]\s*\S{2,}")
SNS_SCOPE_SIGNAL_RE = re.compile(r"(?:SNS|Instagram|インスタ|X(?:運用|投稿)|Twitter|LinkedIn|Facebook|TikTok)", re.IGNORECASE)
ONGOING_SCOPE_SIGNAL_RE = re.compile(r"(?:継続|長期|月額|毎月|定期|運用)")
OUTSOURCING_SIGNAL_RE = re.compile(r"(?:外注|外部委託|業務委託|委託|外部パートナー|担当者募集|運用代行|代行.{0,12}(?:依頼|募集|お願い)|運用.{0,12}(?:募集|お願い)|(?:運用[\s\S]{0,40}依頼|依頼[\s\S]{0,40}運用))")
PUBLIC_FIELDS = ("schema_version", "record_type", "platform", "external_id", "title", "description", "url", "category", "budget_type", "budget_min_minor", "budget_max_minor", "currency", "buyer_external_id", "observed_at")
DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
ID_RE = re.compile(r"^[0-9]+$")
KANA_RE = re.compile(r"[ぁ-ゖァ-ヺ]")
FORBIDDEN_TERMS = ("receipt", "gate", "agent", "model", "browser", "token", "prompt", "internal id", "レシート", "ゲート", "エージェント", "モデル", "ブラウザ", "トークン", "プロンプト", "内部ID")
FORBIDDEN_RE = re.compile("|".join(re.escape(term).replace(r"\ ", r"[ _]") for term in FORBIDDEN_TERMS), re.IGNORECASE)

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

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {"ok": bool(self.ok), "platform": PLATFORM, "submitted": bool(self.submitted), "application_verified": bool(self.application_verified)}
        for key in ("reason", "error", "project_id", "provider_proposal_id", "cleanup_error"):
            value = getattr(self, key)
            if value is not None: result[key] = value
        for key in ("observed_count", "eligible_count", "verified_count", "provider_terminal_blocked_count"):
            value = getattr(self, key)
            result[key] = int(value) if isinstance(value, int) and not isinstance(value, bool) else 0
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

PLANNER_RULES = ("Lancersの公開案件だけを読み、全案件を一対一でeligible/ineligibleに分類する。ブラウザ・認証・外部操作はできない。"
    "eligibleは日本語の商用組織案件で、公開descriptionの公式依頼主の業種行からcommercial_buyer_evidence、依頼概要からSNS/channel・継続scope・外部委任を同時に示すongoing_sns_outsourcing_evidenceを各4〜240文字の完全一致抜粋で返す。"
    "commercial_buyer_evidenceは依頼主の業種: で始まる空でない一行、ongoing_sns_outsourcing_evidenceはSNS/channel・継続・外部委任を全て示すこと。純粋な不明、個人趣味、単発投稿はineligible。"
    "eligibleは買い手宛て自然な日本語200〜3000文字、観測されたJPY予算内の整数価格、98000円以上、翌日から60日以内の実在日を返し、qualificationには4コストとcost_source_versionを指定する。"
    "expected_platform_fee_jpyは価格の20%切上げ以上、他コストは非負整数、cost_source_versionはlancers-g1-conservative-v1とする。"
    "提案文には買い手の課題、最初の30日間の納品物、チャネル数・投稿本数・修正回数上限、価格・納期、継続範囲、確認質問をちょうど1つ含める。"
    "物理出席、ライブ通話・講義、本人固有の調査、AI禁止、声や顔の収録、実写動画編集はineligibleとし、提案・価格・納期・qualificationをnullにする。"
    "提案文には次の語を含めない: " + ", ".join(FORBIDDEN_TERMS) + "。送信・受注・納品・支払済みと主張せず、指定スキーマのJSONだけを返す。\nSNAPSHOT:\n")

def build_planner_prompt(rows: Sequence[Mapping[str, object]], today: date) -> str:
    return PLANNER_RULES + json.dumps(_snapshot(rows, _tick_date(today)), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def invoke_planner(prompt: str, evidence_dir: Path) -> Mapping[str, object]:
    command = [sys.executable, str(AGENT_RUNNER), "--task-class", PLANNER_TASK_CLASS, "--prompt-stdin", "--schema", str(PLANNER_SCHEMA), "--evidence-dir", str(evidence_dir), "--task-label", "lancers-application-intent", "--loop", "lancers-application", "--workdir", str(SKILLS_ROOT.parent)]
    try:
        completed = subprocess.run(command, input=prompt, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=PLANNER_TIMEOUT_SECONDS + 30)
        if completed.returncode != 0: raise ValueError
        evidence = Path(evidence_dir); summary = json.loads((evidence / "summary.json").read_text(encoding="utf-8"))
        result_path = Path(str(summary["result_path"])).resolve(); result_path.relative_to(evidence.resolve())
        if summary.get("status") != "success": raise ValueError
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if not isinstance(result, Mapping): raise ValueError
        return result
    except Exception: raise RuntimeError("planner_failed") from None

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

def _valid_qualification_evidence(qualification: Mapping[str, object], public_text: str) -> bool:
    commercial, ongoing = qualification.get("commercial_buyer_evidence"), qualification.get("ongoing_sns_outsourcing_evidence")
    if any(not isinstance(item, str) or not 4 <= len(item) <= 240 or item not in public_text for item in (commercial, ongoing)):
        return False
    overview = re.search(r"(?:^|\n)依頼概要[:：](.*)", public_text, re.S)
    return bool(JAPANESE_TEXT_RE.search(public_text) and commercial in public_text.splitlines() and COMMERCIAL_BUYER_SIGNAL_RE.fullmatch(commercial) and overview and ongoing in overview.group(1) and all(pattern.search(ongoing) for pattern in (SNS_SCOPE_SIGNAL_RE, ONGOING_SCOPE_SIGNAL_RE, OUTSOURCING_SIGNAL_RE)))

def _validate(rows: Sequence[Mapping[str, object]], value: object, today: date) -> dict[str, Mapping[str, object]]:
    try:
        if not isinstance(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")), Mapping) or not isinstance(value, Mapping): raise ValueError
        decisions = value.get("decisions")
        if set(value) != {"decisions"} or not isinstance(decisions, list) or len(decisions) != len(rows) or len(decisions) > MAX_OPPORTUNITIES: raise ValueError
        expected = [str(row["external_id"]) for row in rows]; rows_by_id = {str(row["external_id"]): row for row in rows}; found: dict[str, Mapping[str, object]] = {}
        for decision in decisions:
            if not isinstance(decision, Mapping) or set(decision) != DECISION_FIELDS: raise ValueError
            project_id, eligibility, reasons = decision.get("request_id"), decision.get("eligibility"), decision.get("reason_codes")
            if not isinstance(project_id, str) or project_id not in expected or project_id in found or eligibility not in ("eligible", "ineligible") or not isinstance(reasons, list) or any(not isinstance(reason, str) or not reason for reason in reasons) or (eligibility == "ineligible" and not reasons): raise ValueError
            proposal, price, due, qualification = decision.get("proposal_text"), decision.get("price_jpy"), decision.get("deliver_date"), decision.get("qualification")
            if eligibility == "ineligible":
                if proposal is not None or price is not None or due is not None or qualification is not None: raise ValueError
            elif not _safe_proposal(proposal, expected) or isinstance(price, bool) or not isinstance(price, int) or price < 98000 or not _valid_date(due, today): raise ValueError
            elif not isinstance(qualification, Mapping) or set(qualification) != QUALIFICATION_FIELDS: raise ValueError
            else:
                public_row = rows_by_id[project_id]
                public_text = public_row.get("description") if isinstance(public_row.get("description"), str) else ""
                if not _valid_qualification_evidence(qualification, public_text): raise ValueError
                if qualification.get("cost_source_version") != "lancers-g1-conservative-v1": raise ValueError
                costs = [qualification.get(key) for key in QUALIFICATION_COST_FIELDS]
                if any(isinstance(cost, bool) or not isinstance(cost, int) or cost < 0 for cost in costs): raise ValueError
                if qualification["expected_platform_fee_jpy"] < (price * 20 + 99) // 100: raise ValueError
                if 10 * (price - sum(costs)) < 7 * price: raise ValueError
            found[project_id] = decision
        if set(found) != set(expected): raise ValueError
        for row in rows:
            if not _valid_observed_budget(row): raise ValueError
            minimum, maximum = row.get("budget_min_minor"), row.get("budget_max_minor")
            decision, price = found[str(row["external_id"])], found[str(row["external_id"])].get("price_jpy")
            if decision["eligibility"] == "eligible" and (row.get("currency") != "JPY" or minimum is None or maximum is None or price < minimum or price > maximum): raise ValueError
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

def _plan_and_submit(rows: Sequence[Mapping[str, object]], today: date, evidence: Path, planner: Optional[Callable[..., object]], submitter: Optional[Callable[..., object]], state_path: Path) -> ApplicationLoopResult:
    observed_count = len(rows)
    try:
        rows, claimed_project_id = _filter_claimed_rows(rows, state_path)
        if not rows:
            return _batch_summary(ApplicationLoopResult(True, reason="duplicate_project", project_id=claimed_project_id), observed_count, 0, (), ())
        prompt = build_planner_prompt(rows, today); planned = (planner or _default_planner)(prompt, evidence); decisions = _validate(rows, planned, today)
    except Exception: return _batch_summary(ApplicationLoopResult(False, error="planner_failed"), observed_count, 0, (), ())
    eligible = [
        (row, decisions[str(row["external_id"])])
        for row in rows
        if decisions[str(row["external_id"])].get("eligibility") == "eligible"
    ]
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

def run_loop(*, state_path: Path = DEFAULT_STATE_PATH, evidence_root: Optional[Path] = None, discoverer: Optional[Callable[..., Mapping[str, object]]] = None, planner: Optional[Callable[..., object]] = None, submitter: Optional[Callable[..., object]] = None, clock: Optional[Callable[[], object]] = None, discovery: Optional[Callable[..., Mapping[str, object]]] = None, now: Optional[Callable[[], object]] = None, evidence_dir: Optional[Path] = None, output_stream: Optional[TextIO] = None, query: Optional[str] = None, timeout: float = 20.0) -> dict[str, object]:
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
    root = Path(evidence_root if evidence_root is not None else evidence_dir or DEFAULT_EVIDENCE_ROOT); result = ApplicationLoopResult(False, error="planner_failed"); cleanup_failed = False; evidence: Optional[Path] = None
    try:
        try:
            _reset(root); evidence = root / f"run-{uuid.uuid4().hex}"; evidence.mkdir(mode=0o700, exist_ok=False); os.chmod(evidence, 0o700)
        except Exception: evidence = None
        if evidence is not None:
            try: observed = (discoverer or discovery or status.run_discovery)(query=DEFAULT_DISCOVERY_QUERY if query is None else query, limit=MAX_OPPORTUNITIES, timeout=timeout)
            except Exception: observed = None
            if observed is None: result = ApplicationLoopResult(False, error="discovery_failed")
            elif not isinstance(observed, Mapping): result = ApplicationLoopResult(False, error="discovery_failed")
            else:
                error, opportunities = observed.get("error"), observed.get("opportunities", [])
                if observed.get("ok") is not True:
                    clean_error = error if isinstance(error, str) and re.fullmatch(r"[A-Za-z0-9._:-]{1,256}", error or "") else "discovery_failed"
                    result = ApplicationLoopResult(False, error=clean_error)
                elif error is not None and error != "no_normalized_opportunities":
                    result = ApplicationLoopResult(False, error=error if isinstance(error, str) and re.fullmatch(r"[A-Za-z0-9._:-]{1,256}", error) else "discovery_failed")
                elif isinstance(opportunities, (str, bytes, bytearray)) or not isinstance(opportunities, Sequence): result = ApplicationLoopResult(False, error="discovery_failed")
                elif not opportunities: result = ApplicationLoopResult(True, reason="no_eligible_project")
                else:
                    try: today = _tick_date((clock or now or (lambda: datetime.now(timezone.utc)))())
                    except Exception: result = ApplicationLoopResult(False, error="planner_failed")
                    else: result = _plan_and_submit(opportunities, today, evidence, planner, submitter, Path(state_path))
    finally:
        try:
            if root.is_symlink() or root.is_file(): root.unlink()
            elif root.is_dir(): shutil.rmtree(root)
        except OSError: cleanup_failed = True
    if cleanup_failed:
        result = ApplicationLoopResult(False, submitted=result.submitted, application_verified=result.application_verified, reason=result.reason, error=result.error or "evidence_cleanup_failed", project_id=result.project_id, provider_proposal_id=result.provider_proposal_id, cleanup_error="evidence_cleanup_failed" if result.error else None, observed_count=result.observed_count, eligible_count=result.eligible_count, verified_count=result.verified_count, provider_terminal_blocked_count=result.provider_terminal_blocked_count, verified_project_ids=result.verified_project_ids, verified_provider_proposal_ids=result.verified_provider_proposal_ids, provider_terminal_blocked_project_ids=result.provider_terminal_blocked_project_ids, unresolved_project_id=result.unresolved_project_id)
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
