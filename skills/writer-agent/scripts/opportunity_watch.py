#!/usr/bin/env python3
"""Reverify official paid-writing calls and advance their durable states."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from claim_store import _text, _timestamp, canonicalize_url  # noqa: E402
from claim_supply import _extract_json  # noqa: E402
from opportunity_store import OpportunityStore  # noqa: E402


class SourceUnavailable(RuntimeError):
    pass


class ReviewUnavailable(RuntimeError):
    pass


def build_review_prompt(source: dict[str, Any], body: str) -> str:
    return f"""You verify a paid-writing opportunity from the FULL official page below.
Never infer OPEN, compensation, payout, AI policy, or requirements from a search snippet.
Use UNKNOWN whenever the official evidence does not say. Do not treat old dates, credits,
views, exposure, or charity donations as money paid to the writer. Distinguish a fee per
accepted/published article from recurring compensation. Read the AI-authorship policy,
originality/exclusivity, editorial steps, payout rail, account/KYC/tax/contract needs, and
geographic limits literally. Return exactly one JSON object and no prose:
{{
  "publisher":{json.dumps(source['publisher'])},
  "application_url":"<exact official HTTPS application URL or unknown>",
  "contact_email":"<exact official contributor contact email or unknown>",
  "intake_state":"OPEN|CLOSED|PAUSED|STALE|UNKNOWN",
  "fee_min":<number|null>,"fee_max":<number|null>,"currency":"USD|...|null",
  "fee_basis":"accepted_article|published_article|recurring|unknown",
  "topics":["..."],
  "originality_terms":"<official fact or unknown>",
  "exclusivity_terms":"<official fact or unknown>",
  "editorial_steps":["..."],
  "expected_delay":"<official fact or unknown>",
  "payout_rail":"<official fact or unknown>",
  "requirements":{{"account":"...","kyc":"...","tax":"...","contract":"...","geography":"..."}},
  "ai_policy":"ALLOWED|ALLOWED_WITH_DISCLOSURE|PROHIBITED|UNKNOWN",
  "fit_evidence":"<specific named topic/form evidence>",
  "next_action":"<one executable next action>",
  "evidence_excerpt":"<short decisive paraphrase; do not invent a quote>"
}}

Official program URL: {source['official_program_url']}
Full official page bytes rendered as text:
{body[:60000]}
"""


def _validated_routes(
    source: dict[str, Any], review: dict[str, Any], body: str
) -> tuple[str | None, str | None]:
    raw_url = review.get("application_url")
    if not isinstance(raw_url, str) or raw_url.strip().lower() == "unknown":
        configured = source.get("application_url")
        if (
            isinstance(configured, str)
            and configured != source.get("official_program_url")
            and configured in body
        ):
            raw_url = configured
        else:
            raw_url = None
    if raw_url is not None:
        try:
            application_url = canonicalize_url(raw_url, "rss")
        except ValueError as error:
            raise ReviewUnavailable("application_url is not valid public HTTPS") from error
        official_url = canonicalize_url(source["official_program_url"], "rss")
        if application_url == official_url:
            application_url = None
        if application_url is not None and raw_url not in body and application_url not in body:
            raise ReviewUnavailable("application_url is absent from official page evidence")
    else:
        application_url = None

    raw_email = review.get("contact_email")
    if not isinstance(raw_email, str) or raw_email.strip().lower() == "unknown":
        contact_email = None
    else:
        contact_email = raw_email.strip().lower()
        if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", contact_email) is None:
            raise ReviewUnavailable("contact_email is not a valid email address")
        if contact_email not in body.lower():
            raise ReviewUnavailable("contact_email is absent from official page evidence")
    return application_url, contact_email


def model_review(
    source: dict[str, Any], body: str, *, runner: Path, run_id: str, timeout: int = 300
) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [str(runner), "judge", "--prompt-file", "-"],
            input=build_review_prompt(source, body),
            capture_output=True,
            text=True,
            env={**os.environ, "ARTICLE_RUN_ID": run_id},
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ReviewUnavailable(type(error).__name__) from error
    if result.returncode != 0:
        raise ReviewUnavailable(f"model runner returned {result.returncode}")
    try:
        review = _extract_json(result.stdout)
    except Exception as error:
        raise ReviewUnavailable("model returned no review JSON") from error
    if review.get("publisher") != source.get("publisher"):
        raise ReviewUnavailable("model review publisher identity differs")
    return review


def _assert_public_destination(
    url: str, *, resolver: Callable[..., Any] | None = None
) -> None:
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError as error:
        raise SourceUnavailable("official program URL is invalid") from error
    if parsed.scheme.lower() != "https" or not host or port not in (None, 443):
        raise SourceUnavailable("official program URL must be public HTTPS on port 443")
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise SourceUnavailable("official program URL has a non-public destination")
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        if not literal.is_global:
            raise SourceUnavailable("official program URL has a non-public destination")
        return
    if resolver is None:
        return
    try:
        answers = resolver(host, 443, type=socket.SOCK_STREAM)
    except OSError as error:
        raise SourceUnavailable("official program hostname did not resolve") from error
    addresses = {answer[4][0] for answer in answers if len(answer) >= 5 and answer[4]}
    if not addresses:
        raise SourceUnavailable("official program hostname did not resolve")
    if any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise SourceUnavailable("official program hostname resolved to a non-public destination")


def _fetch_official_url(
    url: str, *, resolver: Callable[..., Any] = socket.getaddrinfo
) -> bytes:
    _assert_public_destination(url)
    errors: list[str] = []
    targets = (f"https://r.jina.ai/{url}", url)
    for index, target in enumerate(targets):
        if index == 1:
            _assert_public_destination(url, resolver=resolver)
        request = urllib.request.Request(
            target, headers={"User-Agent": "Writer-Agent-Opportunity-Watch/1.0"}
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                body = response.read(2 * 1024 * 1024 + 1)
            if body and len(body) <= 2 * 1024 * 1024:
                return body
            errors.append("empty_or_oversize")
        except OSError as error:
            errors.append(type(error).__name__)
    raise SourceUnavailable("official page unavailable: " + ",".join(errors))


def fetch_official(
    source: dict[str, Any], *, resolver: Callable[..., Any] = socket.getaddrinfo
) -> bytes:
    official = _text(source.get("official_program_url"), "official_program_url")
    supporting = source.get("supporting_urls", [])
    if not isinstance(supporting, list) or len(supporting) > 4:
        raise SourceUnavailable("supporting_urls must be a list of at most four URLs")
    urls = [official, *[_text(url, "supporting_url") for url in supporting]]
    if len(set(urls)) != len(urls):
        raise SourceUnavailable("official evidence URLs must be unique")
    if len(urls) == 1:
        return _fetch_official_url(official, resolver=resolver)
    parts: list[bytes] = []
    for url in urls:
        body = _fetch_official_url(url, resolver=resolver)
        parts.append(f"\nSOURCE {url}\n".encode("utf-8") + body)
    combined = b"".join(parts)
    if len(combined) > 2 * 1024 * 1024:
        raise SourceUnavailable("combined official evidence exceeds byte cap")
    return combined


def _validate_config(config: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(config, dict) or config.get("version") != 1:
        raise ValueError("opportunity watch config version must be 1")
    sources = config.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("opportunity watch requires sources")
    ids: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("opportunity source must be an object")
        source_id = _text(source.get("id"), "source.id")
        _text(source.get("publisher"), "publisher")
        _text(source.get("official_program_url"), "official_program_url")
        supporting = source.get("supporting_urls", [])
        if not isinstance(supporting, list) or len(supporting) > 4:
            raise ValueError("supporting_urls must be a list of at most four URLs")
        for url in supporting:
            _text(url, "supporting_url")
        if source_id in ids:
            raise ValueError("opportunity source ids must be unique")
        ids.add(source_id)
    return sources


def _target(review: dict[str, Any]) -> str:
    intake = str(review.get("intake_state") or "UNKNOWN")
    policy = str(review.get("ai_policy") or "UNKNOWN")
    # A publisher may set the exact rate in the acceptance contract. That must not
    # block a low-cost pitch when the official call already proves that external
    # money is paid for accepted/published work and names the payout rail. The
    # article itself still cannot enter DRAFTING until ACCEPTED evidence exists.
    value_known = (
        review.get("fee_basis") in {"accepted_article", "published_article", "recurring"}
        and str(review.get("payout_rail") or "unknown").strip().lower() != "unknown"
    )
    if intake in {"CLOSED", "PAUSED", "STALE"}:
        return "CLOSED"
    if intake != "OPEN":
        return "VALUE_UNKNOWN"
    if policy == "PROHIBITED":
        return "REJECTED_POLICY"
    if policy == "UNKNOWN" or not value_known:
        return "VALUE_UNKNOWN"
    return "POLICY_CLEAR"


def _advance_to_target(
    store: OpportunityStore, opportunity_id: str, target: str, *,
    official_evidence_id: str, policy_evidence_id: str, observed_at: str,
) -> str:
    current = store.get(opportunity_id)["state"]
    if current == target:
        return "UNCHANGED"
    protected = {"PITCH_READY", "SUBMITTED", "ACCEPTED", "DRAFTING", "ARTICLE_SUBMITTED", "PUBLISHED", "RECEIVED"}
    if current in protected:
        return "UNCHANGED_ACTIVE_APPLICATION"
    transitions: list[str] = []

    def advance(state: str, evidence_id: str | None, reason: str) -> None:
        nonlocal current
        store.advance(
            opportunity_id, state, observed_at=observed_at,
            evidence_id=evidence_id, reason=reason,
        )
        transitions.append(f"{current}->{state}")
        current = state

    if current in {"CLOSED", "REJECTED_POLICY", "EXPIRED"} and target != current:
        advance("DISCOVERED", official_evidence_id, "official program state changed; re-open verification")
    if current == "VALUE_UNKNOWN" and target in {"CLOSED", "REJECTED_POLICY"}:
        advance("DISCOVERED", official_evidence_id, "official evidence resolved parked state")
    if target == "POLICY_CLEAR":
        if current == "VALUE_UNKNOWN":
            advance("VERIFIED_OPEN", official_evidence_id, "official intake and compensation verified")
        elif current == "DISCOVERED":
            advance("VERIFIED_OPEN", official_evidence_id, "official intake and compensation verified")
        if current == "VERIFIED_OPEN":
            advance("POLICY_CLEAR", policy_evidence_id, "official AI and originality policy is compatible")
    elif current != target:
        advance(target, official_evidence_id, f"official evidence maps program to {target}")
    return "->".join(transitions) if transitions else "UNCHANGED"


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def run_watch(
    config: dict[str, Any], database: Path | str, receipt_path: Path | str, *,
    observed_at: str, fetcher: Callable[[dict[str, Any]], bytes] = fetch_official,
    reviewer: Callable[[dict[str, Any], str], dict[str, Any]],
) -> dict[str, Any]:
    observed_at = str(_timestamp(observed_at, "observed_at"))
    sources = _validate_config(config)
    store = OpportunityStore(database)
    rows: list[dict[str, Any]] = []
    inserted_count = 0
    for source in sources:
        try:
            body = fetcher(source)
            if not isinstance(body, bytes) or not body.strip():
                raise SourceUnavailable("official source returned no bytes")
            review = reviewer(source, body.decode("utf-8", errors="replace"))
            if not isinstance(review, dict) or review.get("publisher") != source["publisher"]:
                raise ReviewUnavailable("review publisher identity differs")
            application_url, contact_email = _validated_routes(
                source, review, body.decode("utf-8", errors="replace")
            )
            candidate = {
                **review,
                "publisher": source["publisher"],
                "official_program_url": source["official_program_url"],
                "application_url": application_url,
                "contact_email": contact_email,
                "supporting_urls": source.get("supporting_urls", []),
                "observed_at": observed_at,
                "retrieved_sha256": hashlib.sha256(body).hexdigest(),
            }
            discovered = store.discover(candidate)
            inserted_count += int(discovered["inserted"])
            opportunity_id = discovered["opportunity_id"]
            official = store.record_evidence(
                opportunity_id, kind="official", url=source["official_program_url"],
                observed_at=observed_at, retrieved_sha256=candidate["retrieved_sha256"],
                excerpt=review["evidence_excerpt"], payload=review,
            )
            target = _target(review)
            policy_evidence_id = official["evidence_id"]
            if target == "POLICY_CLEAR":
                policy = store.record_evidence(
                    opportunity_id, kind="policy", url=source["official_program_url"],
                    observed_at=observed_at, retrieved_sha256=candidate["retrieved_sha256"],
                    excerpt=review["evidence_excerpt"], payload={"ai_policy": review["ai_policy"]},
                )
                policy_evidence_id = policy["evidence_id"]
            transition = _advance_to_target(
                store, opportunity_id, target,
                official_evidence_id=official["evidence_id"],
                policy_evidence_id=policy_evidence_id, observed_at=observed_at,
            )
            rows.append(
                {
                    "id": source["id"], "publisher": source["publisher"],
                    "status": "OK", "opportunity_id": opportunity_id,
                    "inserted": discovered["inserted"], "state": store.get(opportunity_id)["state"],
                    "application_url": application_url,
                    "contact_email": contact_email,
                    "transition": transition,
                }
            )
        except SourceUnavailable as error:
            rows.append(
                {"id": source["id"], "publisher": source["publisher"],
                 "status": "SOURCE_UNAVAILABLE", "reason": str(error)}
            )
        except ReviewUnavailable as error:
            rows.append(
                {"id": source["id"], "publisher": source["publisher"],
                 "status": "REVIEW_UNAVAILABLE", "reason": str(error)}
            )
    ok = sum(row["status"] == "OK" for row in rows)
    receipt = {
        "version": 1, "observed_at": observed_at, "sources": rows,
        "totals": {"sources": len(rows), "ok": ok, "unavailable": len(rows) - ok,
                   "inserted": inserted_count},
    }
    _atomic_json(Path(receipt_path), receipt)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--runner", type=Path, default=SCRIPT_DIR.parent / "runtime/model-runner.sh")
    parser.add_argument(
        "--observed-at", default=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    args = parser.parse_args(argv)
    observed_at = args.observed_at() if callable(args.observed_at) else args.observed_at
    config = json.loads(args.config.read_text(encoding="utf-8"))
    run_id = f"opportunity-watch-{str(observed_at).replace(':', '').replace('-', '')}"
    receipt = run_watch(
        config, args.db, args.receipt, observed_at=observed_at,
        reviewer=lambda source, body: model_review(
            source, body, runner=args.runner, run_id=run_id
        ),
    )
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0 if receipt["totals"]["ok"] else 75


if __name__ == "__main__":
    raise SystemExit(main())
