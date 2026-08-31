#!/usr/bin/env python3
"""W1 (26-gig-loop-asis-tobe-plan.md §FH'/§FI'/§FL'): feed measured winning/losing
proposal patterns back into the application planner's prompt, so proposals get
individualized by evidence instead of vibes.

Reply rate 8.6%, win rate 2.1% (§FH', 2026-08-09 measurement) vs a comparable human
operator's 9%->17% by individualizing what the buyer screens for. §FH' isolated the
two measurable levers this file turns into planner guidance every pass:
  - applicants_at_bid / client_order_rate bands correlate with reply rate far more
    than anything about the proposal text itself (a crowded listing or a buyer who
    has never ordered is close to dead regardless of what we write).
  - a won request's actual accepted proposal_text, when it is still on disk in a
    recent pass's evidence, is the only ground truth this loop has for "what worked".

Both are read fresh from ~/gig state every call -- nothing here is a hardcoded phrase
or a cached snapshot, and no real customer text is ever committed: this file only
reads machine-local state at runtime. If the state is thin (fresh install, no history
yet) every section degrades to nothing and fragment() returns "" -- the planner
prompt is byte-identical to before this file existed.

SAFETY (fail-closed, mirrors e4_correlation.py / domain_skills.py): a missing or
unparsable ledger, or one bad evidence file, is skipped, never fatal. No network
calls, no writes -- read-only.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path
from typing import Any, Callable

DEFAULT_ROOT = Path(os.environ.get("GIG_STATE_DIR", str(Path.home() / "gig")))

# Public/professional claims already verified in the private owner-profile SSOT.
# Contact details, address, compensation, legal attestations, and job-search
# preferences are intentionally absent: an application proposal never needs them.
PROPOSAL_FACT_IDS = frozenset({
    "muit_role_2025",
    "muit_agent_crm",
    "muit_genie_logs",
    "muit_rm_summary",
    "mufg",
    "iclr",
    "naist",
    "atr_research",
    "agent_club",
    "anicca_consumer",
    "mr_bot",
    "a10_marketing",
    "education",
    "languages",
    "mr_bot_open_source_operations_20260805",
    "async_operating_practices_20260805",
    "agent_reliability_engineering_20260805",
})

# Same knee as failure_lessons.THRESHOLD (5): a band under 5 samples is noise, not a
# measured lesson, and would make the planner overreact to one unlucky/lucky request.
MIN_BAND_SAMPLES = 5

# applied.jsonl status values that mean the buyer actually responded (26-gig-loop
# §FH': 32/373 "replied" at measurement time). A project that reached delivery
# necessarily got a reply first, so those terminal-good statuses count too.
REPLIED_STATUSES = frozenset({"replied", "delivered", "delivered_pending", "followed_up"})

# Evidence dirs are GC'd (see evidence-gc.jsonl) and this is a live-state scan done on
# every planner prompt build, not a batch job -- bound how many pass dirs get opened.
MAX_EVIDENCE_PASSES = 20
EXEMPLAR_CHAR_LIMIT = 800


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        handle = path.open(encoding="utf-8", errors="replace")
    except OSError:
        return rows
    with handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if isinstance(value, dict):
                rows.append(value)
    return rows


def _num(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _applicants_band(value: Any) -> str | None:
    n = _num(value)
    if n is None or n < 0:
        return None
    if n == 0:
        return "応募者0（先着）"
    if n <= 3:
        return "応募者1-3"
    if n <= 7:
        return "応募者4-7"
    return "応募者8+（混雑）"


def _order_rate_band(value: Any) -> str | None:
    n = _num(value)
    if n is None or n < 0:
        return None
    if n == 0:
        return "発注率0%"
    if n < 50:
        return "発注率1-49%"
    return "発注率50%+"


def _band_reply_rates(
    rows: list[dict[str, Any]], *, key: str, bander: Callable[[Any], str | None]
) -> list[tuple[str, int, int]]:
    counts: dict[str, list[int]] = {}
    for row in rows:
        status = row.get("status")
        if not isinstance(status, str) or not status:
            continue
        band = bander(row.get(key))
        if band is None:
            continue
        bucket = counts.setdefault(band, [0, 0])
        bucket[0] += 1
        if status in REPLIED_STATUSES:
            bucket[1] += 1
    out = [
        (band, applied, replied)
        for band, (applied, replied) in counts.items()
        if applied >= MIN_BAND_SAMPLES
    ]
    out.sort(key=lambda item: -item[1])
    return out


def band_guidance(applied_path: Path) -> str:
    """Deterministic reply-rate-by-band counts, read fresh from applied.jsonl."""
    rows = _read_jsonl(applied_path)
    if not rows:
        return ""
    lines: list[str] = []
    for label, key, bander in (
        ("応募者数", "applicants_at_bid", _applicants_band),
        ("buyer発注率", "client_order_rate", _order_rate_band),
    ):
        bands = _band_reply_rates(rows, key=key, bander=bander)
        if not bands:
            continue
        lines.append(f"実測の返信率（{label}別、応募ログ集計、n>={MIN_BAND_SAMPLES}のみ）:")
        for band, applied, replied in bands:
            rate = 100.0 * replied / applied
            lines.append(f"  - {band}: {replied}/{applied} = {rate:.1f}%")
    return "\n".join(lines)


def _won_request_ids(projects_root: Path) -> set[str]:
    try:
        return {p.name for p in projects_root.iterdir() if p.is_dir()}
    except OSError:
        return set()


def _recent_decision_files(evidence_root: Path, limit: int) -> list[Path]:
    try:
        pass_dirs = [p for p in evidence_root.iterdir() if p.is_dir()]
    except OSError:
        return []
    pass_dirs.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    files: list[Path] = []
    for pass_dir in pass_dirs[:limit]:
        candidate = pass_dir / "agent-B2" / "application-decisions.json"
        if candidate.is_file():
            files.append(candidate)
    return files


def win_exemplar(projects_root: Path, evidence_root: Path) -> str:
    """The first still-on-disk eligible proposal_text for a request this loop actually
    won, found by walking recent pass evidence. Most wins will have no match -- their
    evidence was already GC'd -- and that is fine, this degrades to "" silently."""
    won = _won_request_ids(projects_root)
    if not won:
        return ""
    for path in _recent_decision_files(evidence_root, MAX_EVIDENCE_PASSES):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        decisions = payload.get("decisions") if isinstance(payload, dict) else None
        if not isinstance(decisions, list):
            continue
        for row in decisions:
            # New planner evidence uses the mandatory-submit contract.  Retain the
            # retired binary spelling only while reading historical on-disk passes.
            if not isinstance(row, dict) or (
                row.get("business_class") != "submit_required"
                and row.get("eligibility") != "eligible"
            ):
                continue
            request_id = str(row.get("request_id") or "")
            if request_id not in won:
                continue
            text = row.get("proposal_text")
            if isinstance(text, str) and text.strip():
                trimmed = text.strip()[:EXEMPLAR_CHAR_LIMIT]
                return (
                    f"実際に成約した応募文の実例（request_id={request_id}）:\n"
                    f"「{trimmed}」\n"
                    "この案件固有の語彙・制約に触れている点を真似ること。文面そのものを使い回すのでは"
                    "なく、同じ個別化の程度を今回の依頼に対して再現する。"
                )
    return ""


INDIVIDUALIZATION_INSTRUCTION = (
    "個別化の指示: 依頼文で使われている語彙をそのまま反映し、依頼が明記した制約に具体的に応える。"
    "検証可能な具体（過去の類似実績・使用技術・納期の根拠など）を最低1つ入れる。テンプレ感のある"
    "定型文（挨拶と依頼内容の言い換えだけの文）は避ける。返信率は応募者が多い案件・buyer発注率が"
    "低い案件では構造的に低い — 個別化はその差を埋める唯一のレバーである。"
)


def verified_fact_guidance(profile_path: Path) -> str:
    """Render allowlisted work facts plus non-sensitive derived application answers."""
    try:
        payload = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    facts = payload.get("facts") if isinstance(payload, dict) else None
    if not isinstance(facts, list):
        return ""
    claims: list[tuple[str, str]] = []
    for row in facts:
        if not isinstance(row, dict) or row.get("id") not in PROPOSAL_FACT_IDS:
            continue
        claim = str(row.get("claim") or "").strip()
        evidence = str(row.get("evidence") or "").strip()
        if claim and evidence:
            claims.append((str(row["id"]), claim))
    candidate = payload.get("candidate") if isinstance(payload, dict) else None
    application_answers: list[str] = []
    if isinstance(candidate, dict):
        raw_dob = candidate.get("date_of_birth")
        if isinstance(raw_dob, str):
            try:
                born = date.fromisoformat(raw_dob)
                today = date.today()
                age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
                if 18 <= age <= 120:
                    application_answers.append(f"年代: {age // 10 * 10}代")
            except ValueError:
                pass
        address = candidate.get("mailing_address_ja")
        prefecture = address.get("prefecture") if isinstance(address, dict) else None
        if isinstance(prefecture, str) and prefecture.strip():
            application_answers.append(f"居住都道府県: {prefecture.strip()}")
    if not claims and not application_answers:
        return ""
    claims.sort()
    lines = [
        "提案文に使ってよい検証済みの職歴・能力（今回に関係するものだけ使う）:",
        *(f"  - [{fact_id}] {claim}" for fact_id, claim in claims),
        *(f"  - [derived_application_answer] {answer}" for answer in application_answers),
        "この一覧と案件本文にない資格・本人属性・職歴・年数・数値実績・ポートフォリオを事実として足さない。",
        "一致する実績がなくても応募は止めず、近いtransferable experienceと、案件本文から今ここで作れる具体的なsample/進行planを示す。未作成物を作成済みとは書かない。",
    ]
    return "\n".join(lines)


def fragment(
    *,
    applied_path: Path | None = None,
    projects_root: Path | None = None,
    evidence_root: Path | None = None,
    profile_path: Path | None = None,
) -> str:
    """Verified seller facts plus measured bands/win exemplar when available."""
    root = DEFAULT_ROOT
    resolved_applied = applied_path or Path(
        os.environ.get("GIG_APPLIED_LEDGER", str(root / "applied.jsonl"))
    )
    resolved_projects = projects_root or Path(
        os.environ.get("GIG_PROJECTS_ROOT", str(root / "projects"))
    )
    resolved_evidence = evidence_root or Path(
        os.environ.get("GIG_EVIDENCE_ROOT", str(root / "evidence"))
    )
    resolved_profile = profile_path or Path(
        os.environ.get(
            "ANICCA_JOB_PROFILE",
            str(Path.home() / ".config" / "anicca" / "job-search" / "profile.json"),
        )
    )

    parts: list[str] = []
    truths = verified_fact_guidance(resolved_profile)
    if truths:
        parts.append(truths)
    bands = band_guidance(resolved_applied)
    if bands:
        parts.append(bands)
    exemplar = win_exemplar(resolved_projects, resolved_evidence)
    if exemplar:
        parts.append(exemplar)
    if not parts:
        return ""
    parts.append(INDIVIDUALIZATION_INSTRUCTION)
    return "\n提案文の根拠と個別化:\n" + "\n\n".join(parts) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.parse_args(argv)
    out = fragment()
    if out:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
