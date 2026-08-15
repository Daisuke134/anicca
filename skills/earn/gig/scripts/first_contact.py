#!/usr/bin/env python3
"""Decide, before building anything, whether this paid order says what to build.

★ The exit that matters is not "stop". ★ 2026-08-07 23:36, order 91000001: the buyer had
written 「題材『パズルクエストX』… 納品はGoogleドキュメントでお願いします」 and nothing else,
the posting they bought from said 「ポケモン動画の企画・台本作成」, and the builder ran blind for
two and a half minutes and produced a general guide to the game. It passed acceptance, it
passed the artifact judge, and the pass came one step from formally delivering it. The
platform cancels an order the seller has not spoken in within 48 hours, so the same
silence that produced the wrong artifact was also about to lose the fee outright.

Three exits, and only one of them is failure:

| exit    | when                                                                        |
|---------|-----------------------------------------------------------------------------|
| build   | the order is understood -- the loop proceeds exactly as before               |
| ask     | the order is underspecified -- ask the buyer a real question about the job,  |
|         | which is progress AND satisfies the 48-hour first-contact clock              |
| await   | we already asked and they have not answered -- do not build a guess          |

★ The judgement is only ever made about a room we have never spoken in. ★ Once a
conversation exists the answer stops being reliable enough to act on -- measured, see
``decide`` branch 4 -- and the paths built for that case (the builder's own BLOCKED record,
and the artifact judge) are already better than a guess.

★ Why this exists as a separate cheap step. ★ Before it, the only path from "a paid order
with no artifact" to "a message reaching the buyer" ran through the builder writing
``evidence/acceptance-blocked.json`` (gig_pass.sh ``ask_buyer_when_blocked``, called from
inside ``run_paid_work`` after the builder returns). Contact was therefore a side effect of
spending a full model-budget build, never its purpose -- and a builder confident enough to
produce the wrong thing never writes that record at all. This asks one bounded question of
one toolless session and, when the answer is "nobody has said what to make", writes the
same BLOCKED record the builder would have written. ★ Nothing downstream changes. ★ The
existing ask lane (``ask_buyer.py`` / ``ask_buyer_pass.py``), its persona, its ledger, its
telegram report and its send path all read that record exactly as before.

★ What it reads. ★ ``context/current.json``, compiled every pass by
``project_context_compiler.py`` from posting, DM, talkroom and requirements (B1 / 26701105
collects them). No second collector. The one thing the compiled context does NOT carry is
★what was ordered★ -- measured on the live 23:30 pass, ``grep -c 企画 PAID_WORK.prompt.txt``
returned 0, so the builder never saw the words 「企画・台本作成」 at all. That title lives on
the queue item, so the queue item is the second input here and the title is what the
decision turns on.

★ Fails to ``build``. ★ Unreachable provider, malformed answer, unknown decision string:
all become ``build``, which is what the loop did before this file existed. The opposite
direction would let one broken model call freeze a paid order, and -- worse -- a gate that
guessed "ask" would put a question in front of a paying customer on the strength of a
result it could not read.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ask_buyer  # noqa: E402
import paid_work_evidence  # noqa: E402


HERE = Path(__file__).resolve().parent
SKILL_ROOT = HERE.parent
SCHEMA_PATH = SKILL_ROOT / "schemas" / "first_contact_decision.schema.json"
DEFAULT_RUNNER = Path.home() / "life-manager" / "skills" / "agent-runner" / "agent_runner.py"

# Toolless, read-only, one question -- the same class artifact_judge uses, for the same
# reason: this session decides, it does not touch the project.
TASK_CLASS = "diagnostic-agent"
TASK_LABEL = "gig-FIRST_CONTACT"
RUNNER_GRACE_SECONDS = 30
DEFAULT_TIMEOUT_SECONDS = 180

BUILD = "build"
ASK = "ask"
AWAIT = "await"
DECISIONS = (BUILD, ASK)

# Bump when the prompt changes meaning: cached answers are keyed on it, so an old verdict
# cannot survive a new question.
PROMPT_VERSION = 1

CACHE_RELATIVE = Path("context") / "first-contact-decision.json"
MISSING_MAX_ITEMS = 6
MISSING_MAX_CHARS = 200
BLOCKER_MAX_CHARS = 300


# ---------------------------------------------------------------------------
# The contract with the artifact judge (A8), consumed and never required
# ---------------------------------------------------------------------------
#
# ★ Documented because the other half is being written in parallel. ★ When the judge is
# shown an artifact it cannot rule on because ★the order itself never said what to make★,
# it reports that as its own error id rather than as a refusal. That is the same situation
# this module decides before the build, so when it has already been observed there is no
# reason to pay for a second opinion.
#
# Expected, all optional:
#   artifact_judge.ERROR_NEEDS_BUYER_INPUT : str       the error id
#   artifact_judge.ASK_THE_BUYER_ERRORS    : container of str
#   artifact_judge.should_ask_the_buyer(x) : callable  x is an error id or "<id>:<reason>"
#
# Observed at TWO surfaces, because the verdict reaches disk by two routes and the second
# one was found by measurement, not by reading the code:
#
#   a) ``~/gig/evidence/gig-pass-*/paid-work-transaction.json`` -- newest FINISHED ledger
#      for this project_root; key ``failure_reason`` (written by ``rollback_transaction``)
#      plus any string in ``validation.errors``. This is the route when the builder ran and
#      its package was refused, and it is the same reader shape
#      ``paid_work_prior_rejection_clause`` in gig_pass.sh already uses.
#
#   b) ``~/gig/evidence/gig-pass-*/trajectory.jsonl`` -- rows with ``action == "judge"``,
#      ``ok == false`` and ``reason`` set, keyed by ``resource_key`` of
#      ``project:<request_id>`` or ``talkroom:<talkroom_id>``.
#      ★ Measured live 2026-08-08 00:05 JST. ★ Order 91000001 arrived with
#      delivery_action=formal, so gig_pass.sh skipped run_paid_work entirely, no
#      transaction ledger was opened at all, and the judge fired from inside the delivery
#      browser instead: the only record of
#      ``reason":"order_underspecified_ask_the_buyer"`` anywhere in that pass was one
#      trajectory line. A reader that only knew route (a) would have seen nothing and paid
#      for a second opinion about a question already answered.
#
# ★ Degrades to absent. ★ If the module will not import, or none of the three names exist,
# this shortcut is simply not taken and the model call below decides instead. Nothing here
# may raise: their file is not committed yet and may be mid-edit on disk.
JUDGE_ASK_ERROR_FALLBACK = "order_underspecified_ask_the_buyer"


def _artifact_judge_module() -> Any:
    """The judge module, or None. Loaded by path, never fatal."""
    try:
        spec = importlib.util.spec_from_file_location(
            "artifact_judge_contract", HERE / "artifact_judge.py"
        )
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except BaseException:  # noqa: BLE001 - a file being edited must not break a paid lane
        return None


def judge_ask_error_ids() -> frozenset[str]:
    """Error ids that mean "ask the buyer", from the judge if it declares any.

    The fallback literal is deliberately still returned when the module is missing: it is
    the string in their spec, so a row written by a judge whose module we could not load
    is still recognised. It can only ever cause us to ask a question we were about to
    decide on anyway.
    """
    module = _artifact_judge_module()
    ids: set[str] = {JUDGE_ASK_ERROR_FALLBACK}
    if module is None:
        return frozenset(ids)
    declared = getattr(module, "ASK_THE_BUYER_ERRORS", None)
    if isinstance(declared, (set, frozenset, list, tuple)):
        ids.update(str(item) for item in declared if isinstance(item, str))
    single = getattr(module, "ERROR_NEEDS_BUYER_INPUT", None)
    if isinstance(single, str) and single:
        ids.add(single)
    return frozenset(ids)


def _looks_like_ask_the_buyer(text: Any) -> bool:
    """One recorded reason, matched against the judge's own vocabulary."""
    value = str(text or "").strip()
    if not value:
        return False
    module = _artifact_judge_module()
    asker = getattr(module, "should_ask_the_buyer", None) if module is not None else None
    if callable(asker):
        try:
            if bool(asker(value)):
                return True
        except BaseException:  # noqa: BLE001 - their helper may be mid-edit
            pass
    identifier = value.partition(":")[0]
    return identifier in judge_ask_error_ids() or value in judge_ask_error_ids()


def iso_epoch(text: Any) -> float | None:
    """An ISO-8601 stamp as epoch seconds, or None. Never raises."""
    raw = str(text or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        moment = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.timestamp()


def _judge_said_ask_in_ledgers(root: str, base: Path, not_before: float | None) -> tuple[bool, str]:
    """Route (a): a transaction the builder opened and the judge refused.

    Reads only FINISHED ledgers. The pass running right now writes its own row at
    ``begin``, before anything has been judged, and reading that as history is how a live
    attempt gets blamed for a verdict it has not reached yet (measured on
    ``paid_work_prior_rejection_clause``, 2026-08-07 13:01).
    """
    best: tuple[str, str] | None = None
    try:
        candidates = sorted(base.glob("gig-pass-*/paid-work-transaction.json"))
    except OSError:
        return False, ""
    for ledger_path in candidates:
        try:
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(ledger, dict) or str(ledger.get("project_root") or "") != root:
            continue
        stamp = str(ledger.get("finished_at") or "")
        if not stamp:
            continue
        if not _verdict_still_open(iso_epoch(stamp), not_before):
            continue
        reasons = [str(ledger.get("failure_reason") or "")]
        validation = ledger.get("validation")
        if isinstance(validation, dict):
            reasons.extend(
                str(item) for item in (validation.get("errors") or []) if isinstance(item, str)
            )
        for reason in reasons:
            if _looks_like_ask_the_buyer(reason):
                if best is None or stamp > best[0]:
                    best = (stamp, reason)
                break
    if best is None:
        return False, ""
    return True, best[1]


def _verdict_still_open(recorded_at: float | None, not_before: float | None) -> bool:
    """Has the buyer said nothing since this verdict was recorded?

    ★ A judge verdict is a statement about the order as it stood when it was made. ★
    Without this, one refusal is permanent: order refused as underspecified, we ask, the
    buyer answers in full, the builder is ready to work -- and the same row on disk sends
    the order straight back to asking, forever. The buyer's own reply is what spends it.

    ``not_before`` is when the buyer's currently-open message was observed. A verdict
    recorded before it has already been answered. Unknown timestamps do not filter: a
    verdict we cannot date is still a verdict, and the ask ledger bounds the damage to one
    message either way.

    ★ Considered and rejected: scoping by the artifact's sha256 instead. ★ It looks tighter
    and is in fact weaker -- at the moment the pre-build gate runs, the refused artifact is
    still the armed one even though the buyer has just answered, so sha-scoping would have
    let exactly the failure above through.
    """
    if not_before is None or recorded_at is None:
        return True
    return recorded_at >= not_before


def _judge_said_ask_in_trajectory(
    keys: set[str], base: Path, not_before: float | None
) -> tuple[bool, str]:
    """Route (b): the judge fired from a delivery browser, with no transaction open.

    This is the route the live incident actually took -- an order already at
    ``delivery_action=formal`` never enters ``run_paid_work``, so no ledger exists and the
    one line naming the verdict is in ``trajectory.jsonl``.
    """
    best: tuple[float, str] | None = None
    try:
        candidates = sorted(base.glob("gig-pass-*/trajectory.jsonl"))
    except OSError:
        return False, ""
    for path in candidates:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if not isinstance(row, dict) or row.get("action") != "judge" or row.get("ok") is not False:
                continue
            if str(row.get("resource_key") or "") not in keys:
                continue
            reason = str(row.get("reason") or "")
            if not _looks_like_ask_the_buyer(reason):
                continue
            try:
                stamp = float(row.get("ts") or 0)
            except (TypeError, ValueError):
                stamp = 0.0
            if not _verdict_still_open(stamp or None, not_before):
                continue
            if best is None or stamp > best[0]:
                best = (stamp, reason)
    if best is None:
        return False, ""
    return True, best[1]


def judge_already_said_ask(
    project_root: Any,
    evidence_root: Any = None,
    resource_keys: Any = None,
    not_before: float | None = None,
) -> tuple[bool, str]:
    """Has a previous pass's judge already said this order is underspecified?

    ``(True, "<the recorded reason>")`` or ``(False, "")``. Two surfaces, see the contract
    note above; either one answering is enough. ``not_before`` spends a verdict the buyer
    has since replied to -- see ``_verdict_still_open``.
    """
    root = str(project_root or "")
    if not root:
        return False, ""
    base = Path(str(evidence_root)) if evidence_root else Path.home() / "gig" / "evidence"
    found, reason = _judge_said_ask_in_ledgers(root, base, not_before)
    if found:
        return True, reason
    keys = {str(key) for key in (resource_keys or []) if str(key)}
    if not keys:
        return False, ""
    return _judge_said_ask_in_trajectory(keys, base, not_before)


# ---------------------------------------------------------------------------
# The material the decision is made from
# ---------------------------------------------------------------------------

def _load_json(path: Any) -> Any:
    try:
        return json.loads(Path(str(path)).expanduser().read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return None


def _text(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def order_brief(project_root: Any, queue_item: Any) -> dict[str, Any]:
    """Everything the decision is allowed to see, from the two files that already exist.

    ``context/current.json`` is the compiled context (posting + DM + talkroom +
    requirements + our own promises). The queue item carries the one thing it does not:
    ★the title of the thing that was bought★.
    """
    root = Path(str(project_root or "")).expanduser()
    item = queue_item if isinstance(queue_item, dict) else {}
    context = _load_json(root / "context" / "current.json")
    combined = {}
    if isinstance(context, dict) and isinstance(context.get("combined_context"), dict):
        combined = context["combined_context"]
    requirements = combined.get("requirements") if isinstance(combined.get("requirements"), dict) else {}

    buyer_messages: list[str] = []
    for row in requirements.get("everything_the_buyer_has_asked_for") or []:
        if isinstance(row, dict):
            body = _text(row.get("text"), 1200)
            if body:
                buyer_messages.append(body)
    dm = combined.get("dm") if isinstance(combined.get("dm"), dict) else {}
    for thread in dm.get("threads") or []:
        if not isinstance(thread, dict):
            continue
        for row in thread.get("messages") or []:
            if isinstance(row, dict) and row.get("side") == "buyer":
                body = _text(row.get("text"), 1200)
                if body and body not in buyer_messages:
                    buyer_messages.append(body)

    commitments = [
        _text(row.get("text"), 600)
        for row in (combined.get("our_commitments") or [])
        if isinstance(row, dict) and _text(row.get("text"), 600)
    ]
    posting = combined.get("posting")
    posting_text = ""
    if isinstance(posting, dict):
        posting_text = _text(posting.get("text") or posting.get("body"), 3000)
    elif isinstance(posting, str):
        posting_text = _text(posting, 3000)

    requirements_path = str(
        requirements.get("path")
        or item.get("buyer_feedback_requirements_path")
        or (root / "requirements" / "live-buyer-reply.json")
    )
    feedback = _load_json(requirements_path)
    feedback_sha = ""
    feedback_text = ""
    # When the buyer's currently-open message was observed. A judge verdict older than
    # this has already been answered -- see _verdict_still_open.
    buyer_spoke_at: float | None = None
    if isinstance(feedback, dict):
        feedback_sha = _text(feedback.get("feedback_sha256"), 64)
        feedback_text = _text(feedback.get("feedback_text"), 2000)
        buyer_spoke_at = iso_epoch(
            feedback.get("accumulated_observed_at") or feedback.get("observed_at")
        )
    if not feedback_sha:
        feedback_sha = _text(item.get("buyer_feedback_sha256"), 64)
    if feedback_text and feedback_text not in buyer_messages:
        buyer_messages.insert(0, feedback_text)

    attachments = combined.get("buyer_attachments")
    attachment_names = [
        Path(str(row.get("path"))).name
        for row in (attachments or [])
        if isinstance(row, dict) and row.get("path")
    ][:12]

    return {
        "project_root": str(root),
        "request_id": _text(item.get("request_id"), 40),
        "talkroom_id": _text(item.get("talkroom_id"), 40),
        "order_title": _text(item.get("title"), 300),
        "price_jpy": item.get("price_jpy"),
        "delivery_date": _text(item.get("delivery_date"), 40),
        "delivery_action": _text(item.get("delivery_action"), 40),
        "contact_deadline": _text(item.get("contact_deadline"), 60),
        "seller_message_observed": item.get("seller_message_observed") is True,
        "sources_present": [str(name) for name in (combined.get("sources_present") or [])],
        "posting": posting_text,
        "buyer_messages": buyer_messages[:12],
        "our_commitments": commitments[:6],
        "attachments": attachment_names,
        "requirements_path": requirements_path,
        "feedback_sha256": feedback_sha,
        "buyer_spoke_at": buyer_spoke_at,
        "package_sha256": _text(
            (item.get("delivery_evidence") or {}).get("package_sha256")
            if isinstance(item.get("delivery_evidence"), dict)
            else item.get("package_sha256"), 64),
        "project_context_sha256": _text(
            context.get("project_context_sha256") if isinstance(context, dict) else "", 64
        ),
    }


def decision_key(brief: dict[str, Any]) -> str:
    """Identity of one decision.

    Everything that could change the answer, and nothing that could not: the question, the
    title of what was bought, the digest of the buyer's current words, and the digest of
    the compiled context. A buyer who says something new gets a new decision; an hourly
    pass over unchanged facts does not pay for one.
    """
    digest = hashlib.sha256()
    digest.update(f"v{PROMPT_VERSION}\n".encode("utf-8"))
    for part in (
        brief.get("order_title"),
        brief.get("feedback_sha256"),
        brief.get("project_context_sha256"),
    ):
        digest.update(str(part or "").encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# The question
# ---------------------------------------------------------------------------

def decision_prompt(brief: dict[str, Any]) -> str:
    """One question, asked of a session that will not build anything.

    ★ Absence is evidence and has to be stated as such. ★ For 91000001 there is no posting
    and no DM on disk; a model handed only the talkroom message would read 「題材」 as if it
    were a specification, which is precisely the mistake the builder made. So the sections
    that are empty are named as empty.
    """
    lines: list[str] = [
        ask_buyer.PERSONA,
        "",
        "あなたは今から制作をしません。判断だけをします。",
        "この注文に★今すぐ着手できるか★だけを答えてください。",
        "",
        "判断の問い: ★この材料だけで、注文された物そのものを作り始められるか。★",
        "- 作り始められる → decision = \"build\"",
        "- 作り始めると、注文された物とは★別の物★を作ることになる"
        "（何を作るのかが決まらない、本数・分量・形式・用途・対象が分からない、"
        "必要な素材が届いていない 等） → decision = \"ask\"",
        "",
        "★実例★ 2026-08-07、題材だけが書かれた注文に対して、何も確認せずに"
        "「そのゲームの紹介ガイド」を作って納品しかけました。注文は「動画の企画と台本」でした。"
        "題材が分かることと、何を作るのかが分かることは別です。",
        "",
        "判断してよい材料は以下だけです。ここに書かれていない事は"
        "★「まだ決まっていない」★として扱ってください。想像で補わないでください。",
        "",
        f"【買い手が購入した商品・募集の題名】\n{brief.get('order_title') or '（記録なし）'}",
    ]
    if brief.get("delivery_date"):
        lines.append(f"【納期】{brief['delivery_date']}")
    if brief.get("price_jpy"):
        lines.append(f"【金額】{brief['price_jpy']}円")

    posting = str(brief.get("posting") or "").strip()
    lines.append(
        f"\n【募集時の投稿（買い手が支払い前に書いた仕様）】\n{posting}"
        if posting
        else "\n【募集時の投稿（買い手が支払い前に書いた仕様）】\n"
        "（この注文にはファイルが存在しません。買い手がそこで何かを書いた可能性はありますが、"
        "こちらの記録には残っていません）"
    )

    messages = [str(row).strip() for row in (brief.get("buyer_messages") or []) if str(row).strip()]
    lines.append(
        "\n【買い手が実際に送ったメッセージ（全文・古い順）】\n"
        + "\n---\n".join(messages)
        if messages
        else "\n【買い手が実際に送ったメッセージ】\n（記録なし）"
    )

    commitments = [str(row).strip() for row in (brief.get("our_commitments") or []) if str(row).strip()]
    if commitments:
        lines.append("\n【こちらが既に約束した内容】\n" + "\n---\n".join(commitments))
    attachments = [str(name) for name in (brief.get("attachments") or []) if str(name)]
    lines.append(
        "\n【買い手から受け取った素材ファイル】\n" + "\n".join(f"・{name}" for name in attachments)
        if attachments
        else "\n【買い手から受け取った素材ファイル】\n（1件もありません）"
    )

    lines += [
        "",
        "出力:",
        "- decision は \"build\" か \"ask\" のどちらか1つ。",
        "- ask の場合、missing に★買い手に聞くべき事★を日本語で3〜5点、具体的に書く。"
        "この注文で本当に決まっていない事だけを書き、一般論の要件チェックリストにしない。"
        "相手が1回の返信で全部答えられる粒度にする。",
        "- ask の場合、blocker に着手できない理由を★日本語1文★で書く。"
        "何を注文されたか、そして何が決まっていないかの両方に触れる。",
        "- build の場合、missing は空の配列、blocker は空文字列。",
        "- 社内用語・ファイルパス・ハッシュ・英語の専門用語を書かない。",
        "スキーマに一致する JSON だけを返してください。",
    ]
    return "\n".join(lines)


def parse_decision(payload: Any) -> tuple[str, list[str], str]:
    """``(decision, missing, blocker)``.

    ★ Fails to ``build``, and the direction is the whole point. ★ ``agent_runner``'s schema
    validator implements ``type``/``required``/``properties``/``items`` but NOT ``enum``
    (agent_runner.py:460), so an unknown decision string arrives here schema-valid. Before
    this module existed the loop always built; anything this function cannot read must
    therefore leave the loop exactly where it was, and must never put a question in front
    of a paying customer on the strength of a result nobody could parse.

    ``ask`` with nothing missing is also ``build``: a question that cannot say what it is
    asking for is the 「ご連絡いたします」 this whole lane exists to stop.
    """
    if not isinstance(payload, dict):
        return BUILD, [], ""
    decision = payload.get("decision")
    if not isinstance(decision, str) or decision not in DECISIONS:
        return BUILD, [], ""
    missing = [
        str(row).strip()[:MISSING_MAX_CHARS]
        for row in (payload.get("missing") or [])
        if isinstance(row, str) and str(row).strip()
    ][:MISSING_MAX_ITEMS]
    blocker = str(payload.get("blocker") or "").strip().replace("\n", " ")[:BLOCKER_MAX_CHARS]
    if decision == ASK and not missing:
        return BUILD, [], ""
    if decision == ASK and not blocker:
        blocker = "ご注文の内容を始めるために必要な情報が、まだ確認できていないため"
    return decision, missing, blocker


def _read_runner_result(evidence_dir: Path) -> Any:
    try:
        summary = json.loads((evidence_dir / "summary.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(summary, dict) or summary.get("status") != "success":
        return None
    result_path = summary.get("result_path")
    if not isinstance(result_path, str) or not result_path:
        return None
    try:
        return json.loads(Path(result_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def run_decider(
    brief: dict[str, Any],
    *,
    evidence_dir: Any,
    runner: Any = None,
    schema: Any = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[str, list[str], str, str]:
    """``(decision, missing, blocker, status)``. Never raises.

    ★ The fourth value is not decoration. ★ Every failure here returns ``build``, which is
    also what a healthy "this order is fine" answer returns, so without a status the two
    are the same bytes. Measured 2026-08-08: the runner path did not exist, no provider was
    ever launched, and the decision came back reported as ``source=model`` -- a degraded
    check wearing the uniform of one that ran. ``status`` is ``answered`` only when a
    provider actually replied; everything else names what was missing, is never cached, and
    is never charged to the pass's model-call budget.

    ``--workdir`` is a fresh empty directory: the decision is about what the buyer wrote,
    not about what our own tree contains, and the project root is the builder's writable
    sandbox.
    """
    runner_path = Path(
        str(runner or os.environ.get("GIG_FIRST_CONTACT_RUNNER") or DEFAULT_RUNNER)
    ).expanduser()
    schema_path = Path(str(schema or SCHEMA_PATH)).expanduser()
    evidence = Path(str(evidence_dir)).expanduser()
    if not runner_path.is_file():
        return BUILD, [], "", f"runner_missing:{runner_path}"
    if not schema_path.is_file():
        return BUILD, [], "", f"schema_missing:{schema_path}"
    try:
        evidence.mkdir(parents=True, exist_ok=True)
        prompt_path = evidence / "first-contact.prompt.txt"
        prompt_path.write_text(decision_prompt(brief), encoding="utf-8")
    except OSError as error:
        return BUILD, [], "", f"evidence_unusable:{error}"
    with tempfile.TemporaryDirectory(prefix="gig-first-contact-") as neutral_workdir:
        command = [
            sys.executable, str(runner_path),
            "--task-class", TASK_CLASS,
            "--prompt-file", str(prompt_path),
            "--schema", str(schema_path),
            "--evidence-dir", str(evidence),
            "--task-label", TASK_LABEL,
            "--loop", "gig",
            "--workdir", neutral_workdir,
            "--timeout-seconds", str(int(timeout_seconds)),
        ]
        try:
            subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout_seconds + RUNNER_GRACE_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return BUILD, [], "", "timed_out"
        except (OSError, ValueError) as error:
            return BUILD, [], "", f"launch_failed:{type(error).__name__}"
    payload = _read_runner_result(evidence)
    if payload is None:
        return BUILD, [], "", "no_readable_result"
    decision, missing, blocker = parse_decision(payload)
    return decision, missing, blocker, "answered"


# ---------------------------------------------------------------------------
# What being stuck is written down as
# ---------------------------------------------------------------------------

def blocked_record(brief: dict[str, Any], missing: list[str], blocker: str) -> dict[str, Any]:
    """The BLOCKED record the builder would have written, written cheaply instead.

    Shape is fixed by ``paid_work_evidence.blocked_evidence_verdict``: ``status``,
    ``requirements_path`` and a ``feedback_sha256`` that equals the digest inside that
    file, or the record reads as ``stale``/``undeterminable`` and no question is sent.

    ``order_title`` is ours and is additive. ``ask_buyer.question_prompt`` uses it when it
    is there and behaves exactly as before when it is not, which is what a record written
    by the builder still looks like.
    """
    checks = [
        {
            "command": "first_contact.py decide",
            "result": row,
        }
        for row in missing
    ]
    return {
        "version": 1,
        "status": ask_buyer.BLOCKED,
        "source": "first_contact",
        "order_title": brief.get("order_title") or "",
        "requirements_path": brief.get("requirements_path") or "",
        "feedback_sha256": brief.get("feedback_sha256") or "",
        "checks": checks,
        "blocker": blocker,
    }


def write_blocked_record(project_root: Any, record: dict[str, Any]) -> bool:
    try:
        target = Path(str(project_root)).expanduser() / ask_buyer.BLOCKED_EVIDENCE
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".tmp")
        temporary.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, target)
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Remembering the answer
# ---------------------------------------------------------------------------

def read_cache(project_root: Any, key: str) -> dict[str, Any] | None:
    payload = _load_json(Path(str(project_root)).expanduser() / CACHE_RELATIVE)
    if not isinstance(payload, dict) or payload.get("key") != key:
        return None
    if payload.get("decision") not in DECISIONS:
        return None
    return payload


def write_cache(project_root: Any, payload: dict[str, Any]) -> None:
    try:
        target = Path(str(project_root)).expanduser() / CACHE_RELATIVE
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, target)
    except OSError:
        return


def asked_keys(path: Any) -> set[str]:
    """Blocked states a question has already gone out for.

    Same file and same key as ``ask_buyer_pass`` -- ``~/gig/ask-buyer.jsonl``, keyed by the
    buyer-feedback digest -- read here rather than duplicated, because this module needs
    the same fact one step earlier: an order we have already asked about must not be
    rebuilt on a guess while we wait for the answer.
    """
    keys: set[str] = set()
    try:
        lines = Path(str(path)).expanduser().read_text(encoding="utf-8").splitlines()
    except (OSError, TypeError, ValueError):
        return keys
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and row.get("blocker_key"):
            keys.add(str(row["blocker_key"]))
    return keys


# ---------------------------------------------------------------------------
# A judge refusal, turned from a dead end into a redirect
# ---------------------------------------------------------------------------
#
# ★ A10. ★ The judge refuses at the delivery browser -- and by then this pass has already
# skipped ``run_paid_work``, because gig_pass.sh only enters it when
# ``TOP_ACTION != "formal"``. Measured 2026-08-08 00:33 on the live queue: order 91000001
# sat at ``delivery_action=formal, formal_delivery_checkbox=true, priority -1``, A8's judge
# refused the armed artifact with ``order_underspecified_ask_the_buyer``, and the order
# could not reach the lane that would have asked. The refusal stopped a bad delivery and
# stopped nothing else: ~/gig/ask-buyer.jsonl stayed at two rows, the buyer heard nothing,
# and Coconala cancels the order on 8/9 23:00.
#
# ★ Only recorded facts open this path -- never a judgement. ★ On the pre-build side
# (``decide``) a model may be asked whether an order is understood. Here it may not: an
# order at ``formal`` has an artifact that passed every gate, and diverting a good delivery
# on a guess stops the loop earning, which is worse than the bug. The single trigger is a
# judge verdict, for this order, that the buyer has not since replied to.
#
# ★ The artifact is left armed. ★ Nothing is deleted and nothing is unarmed. Rebuilding
# produced the same wrong thing on 2026-08-07 and would again; what changes is where this
# pass routes, not what is on disk. When the buyer answers, ``delivery_cadence`` raises
# ``buyer_feedback_unprocessed`` on its own, ``artifact_missing`` becomes true and the order
# reaches ``work_required`` -- the builder resumes with the answer, through machinery that
# already exists.

JUDGE_MISSING = ["ご注文の内容について、制作を始めるために確認が必要な点があります。"]
JUDGE_BLOCKER = "ご注文いただいた内容から、何をどこまでお作りするかが確定できていないため"


def resource_keys_for(brief: dict[str, Any]) -> set[str]:
    """The names trajectory.py records this order under.

    Both, because which one the judge wrote depends on which send path invoked it.
    """
    return {
        f"project:{brief['request_id']}" if brief.get("request_id") else "",
        f"talkroom:{brief['talkroom_id']}" if brief.get("talkroom_id") else "",
    } - {""}


def judge_refused_this_order(
    brief: dict[str, Any], project_root: Any, evidence_root: Any = None
) -> tuple[bool, str]:
    """The judge's standing verdict on this order, if the buyer has not spent it."""
    return judge_already_said_ask(
        project_root, evidence_root, resource_keys_for(brief), brief.get("buyer_spoke_at"))


def record_judge_refusal(
    brief: dict[str, Any], project_root: Any, reason: str
) -> dict[str, Any]:
    """Write the refusal down as the BLOCKED record the ask lane already reads.

    ★ This is the whole redirect. ★ The asking machinery is keyed on one file, so turning
    a judge verdict into that file is all it takes to reach it -- no second send path, no
    second ledger, no second question format.
    """
    record = blocked_record(brief, JUDGE_MISSING, JUDGE_BLOCKER)
    written = write_blocked_record(project_root, record)
    return {
        "decision": ASK,
        "source": "artifact_judge",
        "reason": reason,
        "missing": list(JUDGE_MISSING),
        "blocker": JUDGE_BLOCKER,
        "blocked_record_written": written,
    }


def redirect_on_judge_refusal(
    *,
    project_root: Any,
    queue_item: Any,
    ask_ledger: Any,
    evidence_root: Any = None,
) -> dict[str, Any]:
    """``none`` | ``ask`` | ``await`` for an order on its way to the delivery browser.

    ``none`` means "nothing recorded says this order is unbuildable" and the delivery
    proceeds exactly as before -- which is the answer for every healthy order, and is
    reached without reading a model, a cache, or anything but two evidence globs.
    """
    brief = order_brief(project_root, queue_item)
    result: dict[str, Any] = {
        "decision": "none",
        "source": "",
        "reason": "",
        "missing": [],
        "blocker": "",
        "blocked_record_written": False,
        "order_title": brief.get("order_title") or "",
        "feedback_sha256": brief.get("feedback_sha256") or "",
        "package_sha256": brief.get("package_sha256") or "",
    }
    judged, reason = judge_refused_this_order(brief, project_root, evidence_root)
    if not judged:
        result["reason"] = "no standing judge refusal for this order"
        return result
    # Already asked about exactly this request: the redirect still has to happen -- the
    # delivery must not proceed -- but there is no second question to send.
    verdict, state = paid_work_evidence.blocked_evidence_verdict(project_root)
    if verdict == paid_work_evidence.BLOCK_FRESH and state is not None:
        if ask_buyer.blocker_key(state) in asked_keys(ask_ledger):
            result.update({
                "decision": AWAIT,
                "source": "already_asked",
                "reason": reason,
            })
            return result
    result.update(record_judge_refusal(brief, project_root, reason))
    return result


# ---------------------------------------------------------------------------
# The decision
# ---------------------------------------------------------------------------

def decide(
    *,
    project_root: Any,
    queue_item: Any,
    ask_ledger: Any,
    evidence_dir: Any,
    evidence_root: Any = None,
    runner: Any = None,
    schema: Any = None,
    allow_model_call: bool = True,
) -> dict[str, Any]:
    """``build`` / ``ask`` / ``await``, and why.

    Ordered cheapest first. Only the last branch costs anything, and only for an order
    whose facts have changed since the last time it was asked about.
    """
    brief = order_brief(project_root, queue_item)
    key = decision_key(brief)
    result: dict[str, Any] = {
        "decision": BUILD,
        "source": "",
        "reason": "",
        "missing": [],
        "blocker": "",
        "blocked_record_written": False,
        "key": key,
        "order_title": brief.get("order_title") or "",
        "feedback_sha256": brief.get("feedback_sha256") or "",
    }

    # 1. A BLOCKED record that is fresh for the buyer's current words already exists.
    #    Whoever wrote it -- the builder or a previous run of this file -- the ask lane
    #    owns the order now. If the question has already gone out, waiting is the only
    #    honest move: building a guess while a paying customer is mid-answer is the
    #    23:36 failure with an extra step in front of it.
    verdict, state = paid_work_evidence.blocked_evidence_verdict(project_root)
    if verdict == paid_work_evidence.BLOCK_FRESH and state is not None:
        blocker_key = ask_buyer.blocker_key(state)
        if blocker_key in asked_keys(ask_ledger):
            result.update({
                "decision": AWAIT,
                "source": "already_asked",
                "reason": "a question about this exact request has already been sent",
            })
            return result
        result.update({
            "decision": ASK,
            "source": "existing_blocked_record",
            "reason": "a fresh BLOCKED record is on disk and no question has gone out yet",
            "blocker": str(state.get("blocker") or ""),
            "missing": ask_buyer.missing_items(state),
        })
        return result

    # 2. The artifact judge has already ruled that this order does not say what to make.
    #    Free, and more authoritative than our own guess: it looked at a real attempt.
    judged, judged_reason = judge_refused_this_order(brief, project_root, evidence_root)
    if judged:
        result.update(record_judge_refusal(brief, project_root, judged_reason))
        write_cache(project_root, {"key": key, "decision": ASK, "source": "artifact_judge"})
        return result

    # 3. The same facts were decided before. An hourly pass over an unchanged order pays
    #    nothing.
    cached = read_cache(project_root, key)
    if cached is not None and cached.get("decision") == BUILD:
        result.update({"source": "cache", "reason": "same order, same words, same answer"})
        return result

    # 4. ★ Have we ever spoken to this buyer? ★ Everything above is a determinate fact --
    #    a BLOCKED record on disk, a judge's verdict, a remembered answer. What follows is
    #    a judgement, and a judgement made once per hour on an order already in
    #    conversation is a judgement that will eventually be wrong in the expensive
    #    direction.
    #
    #    Measured 2026-08-08, five runs of the real decider per order:
    #      91000001 (nobody had ever spoken to them)  ask ask ask ask ask   5/5
    #      91000002 (a DM thread, our own agreement,  build build ask build ask
    #               and a delivery already sent)
    #    The second order is the one the brief requires NOT to be diverted, and no single
    #    stochastic call delivers that. So the model is not asked about it at all: this is
    #    the FIRST-contact gate, and an order we are already talking to has the paths that
    #    were built for it -- the builder's own BLOCKED record (branch 1), and the artifact
    #    judge (branch 2), both of which still run above.
    #
    #    ``seller_message_observed`` is a live-DOM fact from coconala_queue_snapshot, the
    #    same one A5's ``first_contact_at_risk`` and Coconala's own 48-hour cancellation
    #    banner turn on. Nothing has to remember that we replied.
    if brief.get("seller_message_observed") is True:
        result.update({
            "source": "already_in_conversation",
            "reason": "we have spoken in this room; first contact is not the open question",
        })
        return result

    if not allow_model_call:
        result.update({"source": "no_budget", "reason": "no model call available this pass"})
        return result

    # 5. Ask.
    decision, missing, blocker, status = run_decider(
        brief, evidence_dir=evidence_dir, runner=runner, schema=schema
    )
    if status != "answered":
        # ★ Nothing asked anything. ★ Say so instead of reporting the fallback as a verdict,
        # and do not remember it: a cached "build" from a check that never ran would make
        # every later pass free and wrong.
        result.update({"source": f"degraded:{status}", "reason": "no decision was reached"})
        return result
    if decision == ASK:
        record = blocked_record(brief, missing, blocker)
        written = write_blocked_record(project_root, record)
        result.update({
            "decision": ASK,
            "source": "model",
            "reason": blocker,
            "missing": missing,
            "blocker": blocker,
            "blocked_record_written": written,
        })
        if not written:
            # No record means the ask lane will find nothing and the pass would build
            # anyway with the decision silently discarded. Say so instead.
            result.update({"decision": BUILD, "source": "model_write_failed"})
        else:
            write_cache(project_root, {"key": key, "decision": ASK, "source": "model"})
        return result
    result.update({"source": "model", "reason": "the order says what to build"})
    write_cache(project_root, {"key": key, "decision": BUILD, "source": "model"})
    return result


def _decide_command(args: argparse.Namespace) -> int:
    item = _load_json(args.queue_item)
    result = decide(
        project_root=args.project_root,
        queue_item=item,
        ask_ledger=args.ask_ledger,
        evidence_dir=args.evidence_dir,
        evidence_root=args.evidence_root,
        runner=args.runner,
        schema=args.schema,
        allow_model_call=not args.no_model_call,
    )
    payload = json.dumps(result, ensure_ascii=False)
    if args.output:
        try:
            target = Path(args.output)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(payload, encoding="utf-8")
        except OSError:
            pass
    print(payload)
    return 0


def _emit(result: dict[str, Any], output: str | None) -> int:
    payload = json.dumps(result, ensure_ascii=False)
    if output:
        try:
            target = Path(output)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(payload, encoding="utf-8")
        except OSError:
            pass
    print(payload)
    return 0


def _redirect_command(args: argparse.Namespace) -> int:
    return _emit(redirect_on_judge_refusal(
        project_root=args.project_root,
        queue_item=_load_json(args.queue_item),
        ask_ledger=args.ask_ledger,
        evidence_root=args.evidence_root,
    ), args.output)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    redirect_parser = sub.add_parser("redirect")
    redirect_parser.add_argument("--project-root", required=True)
    redirect_parser.add_argument("--queue-item", required=True)
    redirect_parser.add_argument("--ask-ledger", required=True)
    redirect_parser.add_argument("--evidence-root")
    redirect_parser.add_argument("--output")
    redirect_parser.set_defaults(handler=_redirect_command)
    decide_parser = sub.add_parser("decide")
    decide_parser.add_argument("--project-root", required=True)
    decide_parser.add_argument("--queue-item", required=True)
    decide_parser.add_argument("--ask-ledger", required=True)
    decide_parser.add_argument("--evidence-dir", required=True)
    decide_parser.add_argument("--evidence-root")
    decide_parser.add_argument("--runner")
    decide_parser.add_argument("--schema")
    decide_parser.add_argument("--output")
    decide_parser.add_argument("--no-model-call", action="store_true")
    decide_parser.set_defaults(handler=_decide_command)
    args = parser.parse_args()
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
