#!/usr/bin/env python3
"""One question, asked by someone who did not write the answer.

2026-08-07. Three times in one day the paid builder produced the same kind of thing --
a document *about* the order rather than the thing the order bought -- and three times
its own acceptance said PASS.

    v2  1879B  「ご依頼内容の確認資料」          ★delivered to the buyer★
    v3  2154B  「まず確認する場所 / 1. 取引トークルームを開きます」   quarantined by accident
    v3  2173B  「ご依頼内容の確認資料（更新版）」  committed as current_version, armed

Only Coconala's refusal to accept a second formal delivery while one awaits confirmation
kept the third from the buyer. That is an accident, not a defence.

★ Prohibition failed three times because prohibition is enumeration. ★ The builder's
prompt was given the ban in general terms, then with the observed shape named outright
(「ファイルの開き方を説明する文書を作るな」); ``PAID_WORK.prompt.txt`` greps confirm it
arrived. It read the ban and reworded the document. A list of forbidden forms can always
be stepped around; a judgement about the *nature* of the thing cannot.

★ 2026-08-07 23:36, order 91000001: the question itself was too narrow. ★ The buyer bought
「ポケモン動画の企画・台本作成」. The builder, having never spoken to them, produced
``sample-game-guide-v1.docx`` -- a competent general guide to the game, subtitled
「ゲーム紹介・記事作成用 基礎資料」. Acceptance said PASS and ★this judge said ok★, and the
formal-delivery browser was one step from sending it.

Two separate things let that through, and the second is the one the incident report missed:

1. The question was "is this *about the deal*?" -- and it was not. It was a real work
   product. It simply was not the one that was bought. A yes/no on meta-documents cannot
   express "wrong thing", so the only answer left was ``deliverable``.
2. ★ The judge never asked anything at all. ★ ``.docx`` is a zip container, so
   ``artifact_body`` returned ``binary`` and ``run_judge`` short-circuited to
   ``deliverable`` before the order text was even looked at -- zero model calls. The
   comment that used to sit on that branch predicted this exact case and called it a
   "known and accepted gap ... no such instance has been observed". Tonight was the
   instance. Widening it needed a text extractor, and now there is one: OOXML is a zip of
   XML, and ``stdlib zipfile`` reads it.

So the question is now ★「この成果物は、この買い手が注文した物か」★, and the answers are:

    deliverable        the thing the buyer bought
    about_the_deal     a document about the transaction (the 2026-08-07 15:00 shape)
    not_the_order      a real work product, but not the one that was bought (23:36)
    needs_buyer_input  the order never said what to make -- ★ask, do not stop★
    undeterminable     our own view of the artifact is too poor to say

★ needs_buyer_input is not a refusal. ★ 26-gig-loop-asis-tobe-plan §3: a judge that refuses
more often is not a better judge, it is a loop that earns nothing. Three exits exist and
only the third is failure -- deliver when it matches, ask when the order is underspecified,
refuse when it is genuinely wrong. The two axes are kept apart on purpose:
``needs_buyer_input`` says the *order* is deficient, ``undeterminable`` says our *view of
the artifact* is.

★ It is given the buyer's own messages and the artifact's own bytes. ★ Not the manifest,
not the acceptance evidence, not the builder's summary. The contradiction check added
earlier the same day failed for exactly that reason: it read
``evidence/acceptance-blocked.json``, a file the builder writes, so a builder that never
declares a block leaves the check with nothing to look at. A check whose input is the
suspect's own testimony is not a check.

Scope discipline (see 31-gig-todo10 §2.2, §3): ★still one question, asked once★. No quality
score, no rewrite suggestion, no second job in the prompt, no follow-up turn. The answer set
grew because the old one had nowhere to put "wrong thing" and nowhere to put "nobody said
what the thing was"; the question did not.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Callable


DELIVERABLE = "deliverable"
ABOUT_THE_DEAL = "about_the_deal"
NOT_THE_ORDER = "not_the_order"
NEEDS_BUYER_INPUT = "needs_buyer_input"
UNDETERMINABLE = "undeterminable"
VERDICTS = (DELIVERABLE, ABOUT_THE_DEAL, NOT_THE_ORDER, NEEDS_BUYER_INPUT, UNDETERMINABLE)

# ★ Only these two refuse outright. ★ ``needs_buyer_input`` does not deliver either, but it
# is not a refusal -- it is the loop being told which lane to take next, and the caller is
# expected to ask rather than stall (26-gig-loop §3).
REFUSING_VERDICTS = (ABOUT_THE_DEAL, NOT_THE_ORDER)

# One spelling for both gates. paid_work_evidence declares the same two strings as its own
# constants rather than importing this module, so a test pins them equal -- two gates that
# refuse under different names are two bugs waiting to be triaged separately.
ERROR_ABOUT_THE_DEAL = "artifact_is_about_the_deal_not_the_deliverable"
ERROR_UNDETERMINABLE = "artifact_judgement_undeterminable"
# ★ New on 2026-08-07, after order 91000001. ★ The two ids above could not say what went
# wrong that night: the artifact was a real, competent work product, it just was not the
# one that was bought. ``about_the_deal`` would have been a lie about it and
# ``undeterminable`` would have blamed our own machinery for a decision the judge in fact
# made confidently.
ERROR_NOT_THE_ORDER = "artifact_is_not_the_ordered_thing"
# ★ Not a refusal. ★ The order itself never said what to make, so no artifact can be
# checked against it. The answer is to ask the buyer, which is progress and which also
# satisfies Coconala's 48-hour first-contact clock.
ERROR_NEEDS_BUYER_INPUT = "order_underspecified_ask_the_buyer"

# ★ The contract for whoever builds the asking lane. ★ A caller that catches the ValueError
# raised by ``refuse_unless_deliverable`` must be able to tell "ask the buyer" from "this is
# wrong" without doing string surgery on the message, so the split lives here next to the
# ids rather than being re-derived at each call site.
ASK_THE_BUYER_ERRORS = frozenset({ERROR_NEEDS_BUYER_INPUT})
WRONG_ARTIFACT_ERRORS = frozenset({ERROR_ABOUT_THE_DEAL, ERROR_NOT_THE_ORDER})


def split_error(error: BaseException | str) -> tuple[str, str]:
    """``("<error id>", "<reason>")`` from what ``refuse_unless_deliverable`` raised.

    The message format is ``"<error id>:<reason>"`` and the reason is free Japanese prose
    that may itself contain colons, so the split is on the first one only.
    """
    text = str(error)
    error_id, _, reason = text.partition(":")
    if error_id not in {ERROR_ABOUT_THE_DEAL, ERROR_NOT_THE_ORDER,
                        ERROR_NEEDS_BUYER_INPUT, ERROR_UNDETERMINABLE}:
        return "", text
    return error_id, reason


def should_ask_the_buyer(error: BaseException | str) -> bool:
    """True when the right next move is a message to the buyer, not a stop."""
    return split_error(error)[0] in ASK_THE_BUYER_ERRORS

HERE = Path(__file__).resolve().parent
SKILL_ROOT = HERE.parent
SCHEMA_PATH = SKILL_ROOT / "schemas" / "artifact_judgement.schema.json"

# EV1 instrumentation. ★ The import itself may not be able to break a delivery gate ★, so a
# missing or broken trajectory.py degrades to a no-op rather than an ImportError raised
# while this module is being loaded by the browser that is about to deliver.
try:
    from trajectory import record as record_trajectory
except Exception:  # noqa: BLE001 - instrumentation may never break its host
    def record_trajectory(**_kwargs: Any) -> None:  # type: ignore[misc]
        return None

DEFAULT_RUNNER = Path.home() / "life-manager" / "skills" / "agent-runner" / "agent_runner.py"

# ★ Read-only by construction, verified in config.json + agent_runner.command_for. ★
# ``diagnostic-agent`` is one of the three task classes for which the codex adapter
# appends ``--sandbox read-only`` and the claude adapter appends ``--tools ""``
# (agent_runner.py:796-815). Every other class gets
# ``--dangerously-bypass-approvals-and-sandbox``. A judge that can write is a judge that
# can start fixing what it was asked to judge, and then it is the writer again
# (31-gig-todo10 §2.2). The other two read-only classes are unusable here:
# ``composition-agent`` and ``application-intent-planner`` are both forced to
# ``--prompt-stdin`` (agent_runner.py:899) and carry other lanes' routes.
TASK_CLASS = "diagnostic-agent"
TASK_LABEL = "gig-ARTIFACT_JUDGE"

# Bumped whenever the prompt changes, because the cache key includes it: an answer given
# to a different question must not be replayed as an answer to this one. v2 = the question
# became "is this the ordered thing" and the order text gained the posting and the DM, so
# every v1 answer on disk is an answer to a question nobody is asking any more. v3 added the
# precedence rules after a measured false refusal: judging 91000002's real deck against its
# generic recruitment ad produced ``not_the_order`` for work the buyer had already called
# 「ほぼ思った通りの仕上がりです」. v4 fixed a regression the live suite caught: with a thin
# order, all three 2026-08-07 meta-documents came back ``needs_buyer_input`` instead of
# ``about_the_deal`` -- the judge was excusing itself from a decision it could make on the
# artifact alone. ★Whether a document is about the deal does not depend on knowing the
# order★, and the prompt now says so and asks it first.
PROMPT_VERSION = 4

# ---------------------------------------------------------------------------
# What the judge is allowed to see
# ---------------------------------------------------------------------------

# Truncation rule, stated once here and nowhere else:
#
#   * <= ARTIFACT_MAX_CHARS characters  -> the judge sees the whole file.
#   * larger                            -> head + an explicit elision notice + tail.
#
# Head-only was rejected. The first N bytes of the real HTML deliverable
# (~/gig/projects/90000004/artifacts/catalog-page-10756-v16.html, 63866 B) happen to be
# informative, but that is luck: an HTML file whose first 6000 characters are a minified
# stylesheet would arrive as boilerplate, the judge would honestly answer
# ``undeterminable``, and a real delivery would be refused. A gate that blocks every large
# deliverable is not a gate, it is an outage. Head *and* tail costs nothing and makes the
# unjudgeable case much rarer.
#
# The numbers are chosen against measured data, not taste: every artifact of the failure
# class is small prose (1879 / 2154 / 2173 bytes), so ★ the documents this gate exists to
# catch are never truncated at all ★. Truncation only ever applies to large artifacts,
# which are overwhelmingly the real thing.
ARTIFACT_MAX_CHARS = 8000
ARTIFACT_HEAD_CHARS = 6000
ARTIFACT_TAIL_CHARS = 2000

# The buyer's side of the talkroom, under the same rule and for the same reason: the
# original order is at the top, the newest instruction at the bottom, and the middle of a
# long thread is the least likely place for either.
ORDER_MAX_CHARS = 4000
ORDER_HEAD_CHARS = 2000
ORDER_TAIL_CHARS = 2000

# The two sources added on 2026-08-07. Both are bounded separately from the talkroom so that
# a long thread cannot squeeze out the posting, which is the shortest and most
# order-identifying of the three.
POSTING_MAX_CHARS = 2000
DM_MAX_CHARS = 1200

# The order label is one line by construction -- it is the marketplace's title field.
# Re-measured 2026-08-08 08:56 over every ``paid-queue-expected.json`` on disk: 35 rows,
# three distinct titles, longest 「Canvaを使った画像編集・デザイン制作をお願いできる方を募集します」
# at 32 characters. The clip is a guard against a malformed row, not a truncation policy,
# and it matches ``project_context_compiler.ORDER_TITLE_CHARS`` so the two ends of the loop
# cannot read different halves of the same string.
ORDER_LABEL_MAX_CHARS = 200
# ★The evidence tree is garbage-collected while this runs, so its size is a moving target
# and the bound must not be read as its size.★ Measured within one session on 2026-08-08:
# 112 pass directories at 08:38, 61 at 08:56. The bound is a cost ceiling on JSON reads for
# a lookup that normally matches on its first candidate -- the pass writing this judge's own
# queue item is, by definition, the newest one.
ORDER_LABEL_SCAN_LIMIT = 400
PASS_QUEUE_ITEM_NAME = "paid-queue-expected.json"

REASON_MAX_CHARS = 300

def posting_store() -> Path:
    """Where ``posting_source.py`` keeps the postings we applied to, keyed by request id.

    ★ Preferred over the project's own copy ★ for the reason the whole module exists: the
    project tree is the builder's rw sandbox and this directory is not. Resolved per call,
    not at import, so a test can point it somewhere hermetic -- the same reason
    ``state_root`` is a function.
    """
    return Path(
        os.environ.get("GIG_POSTING_STORE") or (Path.home() / "gig" / "postings")
    ).expanduser()


def pass_evidence_root() -> Path:
    """Where each pass writes the queue item it is about to act on.

    ``gig_pass.sh`` writes ``$EVIDENCE_DIR/paid-queue-expected.json`` from the selected
    queue row and then hands *that same path* to whichever delivery browser runs -- both of
    them, on ``--queue-item``, immediately before the browser starts. So the row this judge
    is being asked about is already on disk, outside the project tree, every time the judge
    runs. ``GIG_EVIDENCE_ROOT`` is gig_pass.sh's own name for this directory
    (gig_pass.sh:341) and evals/replay_evidence.py already reads it under that name; a test
    points it somewhere hermetic, exactly like ``posting_store``.
    """
    return Path(
        os.environ.get("GIG_EVIDENCE_ROOT") or (Path.home() / "gig" / "evidence")
    ).expanduser()

# ★ Measured, not assumed. ★ 2026-08-07 across ~/gig/projects/*/artifacts: 29 zip,
# 15 mcaddon, 5 html, 4 png, 2 mp4, 2 md. Only these three part names make a zip a readable
# document; a .zip whose entries are four .pptx files (91000002's real 13 MB delivery) has
# none of them and stays binary, which is what keeps the paid lane shipping.
OOXML_TEXT_NODES = re.compile(r"<(?:w:t|a:t|t)(?:\s[^>]*)?>(.*?)</(?:w:t|a:t|t)>", re.S)
OOXML_MIN_CHARS = 40


def _is_ooxml_text_part(name: str) -> bool:
    return (
        name == "word/document.xml"                                        # .docx
        or (name.startswith("ppt/slides/slide") and name.endswith(".xml"))  # .pptx
        or name == "xl/sharedStrings.xml"                                   # .xlsx
    )


def ooxml_text(raw: bytes) -> str:
    """The readable text inside a Word/PowerPoint/Excel container, or ``""``.

    ★ This is the branch order 91000001 walked past. ★ ``.docx`` is a zip, the old code
    called every zip binary, and every binary was declared deliverable without a question.

    Returns ``""`` -- meaning "keep treating this as an opaque package" -- for anything that
    is not one of these three formats, for a corrupt archive, and for a container whose text
    is too thin to judge on. That last case matters: a deck that is entirely images has no
    ``<a:t>`` nodes, and inventing a verdict from its file name would be worse than the
    honest "this is a package, not a document about the deal".
    """
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            parts = sorted(name for name in archive.namelist() if _is_ooxml_text_part(name))
            if not parts:
                return ""
            chunks: list[str] = []
            for name in parts:
                try:
                    xml = archive.read(name).decode("utf-8", "replace")
                except (KeyError, OSError, ValueError):
                    continue
                chunks.extend(
                    html.unescape(match).strip()
                    for match in OOXML_TEXT_NODES.findall(xml)
                    if match.strip()
                )
    except (zipfile.BadZipFile, OSError, ValueError, RuntimeError):
        return ""
    text = "\n".join(chunks).strip()
    return text if len(text) >= OOXML_MIN_CHARS else ""

# agent_runner enforces its own deadline and then still has to write summary.json, so the
# outer kill is deliberately later than the inner one. It is the backstop for a runner that
# is itself wedged, not the normal exit.
RUNNER_GRACE_SECONDS = 30


def _elide(text: str, limit: int, head: int, tail: int) -> str:
    if len(text) <= limit:
        return text
    dropped = len(text) - head - tail
    return f"{text[:head]}\n［中略: {dropped} 文字省略］\n{text[-tail:]}"


def buyer_order_text(project_root: str | Path, requirements_path: str | Path | None = None) -> str:
    """What the buyer actually asked for, in the buyer's own words.

    ``source/talkroom/messages.jsonl`` first: those rows are captured from the live
    talkroom by the browser snapshot, carry ``side`` per message, and are not written by
    the builder. Only ``side == "buyer"`` rows are used -- our own replies are ours, and a
    judge shown our sales patter would be reading the writer again.

    The requirements file is the fallback rather than the primary source: it is
    project-owned and inside the builder's sandbox workspace. It is still worth having,
    because it is the only place a buyer's attachment-borne instruction is transcribed.

    Empty return is meaningful and is NOT smoothed over: a judge with no order in front of
    it cannot say what was ordered, and the caller turns that into ``undeterminable``.
    """
    root = Path(str(project_root or "")).expanduser()
    lines: list[str] = []
    try:
        raw = (root / "source" / "talkroom" / "messages.jsonl").read_text(encoding="utf-8")
    except (OSError, ValueError):
        raw = ""
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if not isinstance(row, dict) or row.get("side") != "buyer":
            continue
        text = str(row.get("text") or "").strip()
        if text:
            lines.append(text)
    if not lines and requirements_path:
        try:
            payload = json.loads(Path(str(requirements_path)).expanduser().read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError):
            payload = None
        if isinstance(payload, dict):
            text = str(payload.get("feedback_text") or "").strip()
            if text:
                lines.append(text)
    return _elide("\n".join(lines), ORDER_MAX_CHARS, ORDER_HEAD_CHARS, ORDER_TAIL_CHARS)


def posting_text(project_root: str | Path) -> str:
    """What the buyer wrote before they paid: the job posting, title first.

    ★ The title is the single most order-identifying string that exists. ★ For 91000001 it is
    「ポケモン動画の企画・台本作成ができる方を募集します」 -- the only place the words 企画 and
    台本 appear anywhere -- and the talkroom message that replaced it as the judge's whole
    view of the order says merely 「題材『パズルクエストX』… 納品はGoogleドキュメントで」.
    A subject and a file format are not a deliverable.

    The durable store is read first and the project copy second. Both are the same document;
    only the store is outside the builder's writable tree.

    ★ Measured caveat, and it is not a small one. ★ ``~/gig/postings`` held 34 postings on
    2026-08-07 and ``request-91000001.json`` was not among them: that order arrived as
    ``offer:92000015``, a direct offer we never applied to, so nothing ever harvested its
    posting. This function therefore returns "" for the very order that motivated it.

    ★That absence is real and is still reported as such, but it is no longer the end of the
    search.★ A direct offer has exactly one carrier for the name of what was bought -- the
    marketplace order label -- and ``order_label_text`` below reads it, as A9 does at the
    entrance. This function stays what its name says: the buyer's own pre-payment document,
    present or not. A recovered label is not one, and the two are never merged.
    """
    root = Path(str(project_root or "")).expanduser()
    candidates: list[Path] = []
    if root.name:
        candidates.append(posting_store() / f"request-{root.name}.json")
    try:
        candidates.extend(sorted((root / "source" / "posting").glob("request-*.json")))
    except OSError:
        pass
    for path in candidates:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(document, dict):
            continue
        title = str(document.get("title") or "").strip()
        body = str(document.get("body") or "").strip()
        if not title and not body:
            continue
        header = f"題目: {title}" if title else ""
        return _elide(
            "\n".join(part for part in (header, body) if part),
            POSTING_MAX_CHARS, POSTING_MAX_CHARS // 2, POSTING_MAX_CHARS // 2,
        )
    return ""


def order_label_text(project_root: str | Path) -> str:
    """The marketplace's own name for this order. ★A title, not a specification.★

    ★A11, and it is A9's third source rather than a second answer.★ ``project_context_compiler
    ._order_section`` resolves what was ordered as: durable store, then the project copy,
    then ``queue_item.title`` -- the marketplace order label, ★the only carrier a direct
    offer has★. The first two legs are ``posting_text`` above, which this module already had.
    This is the third, and without it the judge is blind in exactly the way the builder was:
    for 91000001 ``posting_text`` returns "" (re-measured 2026-08-08 -- ``~/gig/postings``
    holds 43 postings and ``request-91000001.json`` is not among them, and that project has no
    ``source/posting/`` either, because the order arrived as ``offer:92000015`` and nothing was
    ever applied to), so the words 企画 and 台本 reached neither end of the loop. B6 measured
    ``source/posting/`` in 1 of 9 live projects.

    ★Where the label is read from, and why it is not a new parameter.★ The judge's callers
    hand it ``project_root``, ``artifact_path`` and ``requirements_path`` -- there is no queue
    item in its signature, and ``first_contact.py`` gets one only because gig_pass.sh passes
    ``--queue-item`` to it explicitly. Rather than add an argument that every existing caller
    (both browsers, ``_main``, every test) would have to be edited to fill, this reads the
    file those callers were themselves handed: gig_pass.sh writes the selected row to
    ``$EVIDENCE_DIR/paid-queue-expected.json`` (gig_pass.sh:1899 and :2376) and passes that
    path to the progress browser and to the formal browser (:1928, :2389, :2401), and the
    judge runs inside those browsers. ★The invariant, not the count★: every queue item on
    disk carries a non-empty ``title``. Held 36 of 36 at 08:38 on 2026-08-08 and 35 of 35 at
    08:56, the difference being the evidence GC rather than a row without a title.

    ★Not the project's own copy of the same fact, on purpose.★ ``<root>/context/current.json``
    also carries ``combined_context.order.title`` after A9, by a single deterministic path --
    but it sits inside ``--workdir``, the builder's writable tree, so the agent whose artifact
    is being judged could rewrite the order it is judged against. The pass evidence directory
    is outside it. That is the same reason the verdict cache lives under ``~/.local/state``.

    Identity is ``request_id`` with ``talkroom_id`` as the fallback, which is
    ``validate_queue_contract``'s rule verbatim (coconala_formal_delivery_browser.py:193) and
    the rule the projects directory already follows: measured on the live queue items, order
    91000001 is keyed ``request_id=91000001`` and the direct service purchase 90000004 has no
    ``request_id`` at all and is keyed by its talkroom.

    Returns ``""`` when nothing matches, which keeps the caller's old behaviour exactly.
    """
    root = Path(str(project_root or "")).expanduser()
    key = root.name.strip()
    if not key:
        return ""
    try:
        candidates = list(pass_evidence_root().glob(f"gig-pass-*/{PASS_QUEUE_ITEM_NAME}"))
    except OSError:
        return ""

    def newest_first(path: Path) -> tuple[float, str]:
        # A pass that is running right now may unlink under us; an unreadable mtime sorts
        # last rather than raising, because a judge that crashes has cleared nothing.
        try:
            return (path.stat().st_mtime, path.name)
        except OSError:
            return (0.0, path.name)

    for path in sorted(candidates, key=newest_first, reverse=True)[:ORDER_LABEL_SCAN_LIMIT]:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(document, dict):
            continue
        identity = (
            str(document.get("request_id") or "").strip()
            or str(document.get("talkroom_id") or "").strip()
        )
        if identity != key:
            continue
        title = str(document.get("title") or "").strip()
        if title:
            return title[:ORDER_LABEL_MAX_CHARS]
    return ""


def dm_text(project_root: str | Path) -> str:
    """The buyer's side of the pre-purchase direct-message thread.

    Same rule as the talkroom and for the same reason: only ``side == "buyer"`` rows. This
    is where a buyer who negotiated before paying stated the spec, and where their attached
    files were named.

    ★ Two file shapes exist on disk under the same name, and only one is admissible. ★
    Measured 2026-08-07 over ``~/gig/projects/*/source/dm/thread-*-full.json``:

        91000002   ``messages`` list, ``side`` per row   -> buyer 2, seller 2   ★usable★
        90000004  ``url/title/text/files``, one blob    -> no attribution
        90000000  ``url/title/text/files``, one blob    -> no attribution

    The blob shape is a raw page scrape holding both halves of the conversation with nothing
    marking which is which. Feeding it in would put our own sales prose into the order text,
    which is precisely the failure ``buyer_order_text`` was written to avoid, so the blob
    shape is skipped rather than guessed at. It is skipped silently and safely: an absent DM
    is named in ``order_identity_text`` as a source with no record, so the judge is told the
    difference between "they said nothing" and "we did not look".
    """
    root = Path(str(project_root or "")).expanduser()
    lines: list[str] = []
    try:
        threads = sorted((root / "source" / "dm").glob("thread-*-full.json"))
    except OSError:
        return ""
    for path in threads:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        messages = document.get("messages") if isinstance(document, dict) else None
        if not isinstance(messages, list):
            continue
        for message in messages:
            if not isinstance(message, dict) or message.get("side") != "buyer":
                continue
            text = str(message.get("text") or "").strip()
            if text:
                lines.append(text)
    return _elide("\n".join(lines), DM_MAX_CHARS, DM_MAX_CHARS // 2, DM_MAX_CHARS // 2)


def order_identity_text(project_root: str | Path,
                        requirements_path: str | Path | None = None) -> str:
    """Everything on disk that says ★what was ordered★, labelled by where it came from.

    Three sources, in the order a buyer produced them -- the posting they wrote before
    paying, the DM thread they negotiated in, then the talkroom. B1 (``26701105``) collects
    all three into the project; until now this module read only the third, which is how an
    order for 企画・台本 was judged against a message that only named a 題材.

    ★ The labels are not decoration, and neither is the list of what is missing. ★ A judge
    shown one undifferentiated wall of Japanese cannot weigh a pre-payment specification
    against a post-payment aside. More importantly, ★absence is evidence★: for 91000001 there
    is no posting and no DM on disk at all, and a judge told so can see that nobody ever
    wrote down what to build -- which is the difference between "this artifact is wrong" and
    "nobody has said what right would be". Leaving the gap silent would let the judge read
    a 題材 as if it were a specification, which is the mistake the builder already made.

    Empty return keeps its old meaning exactly: no order on record, so no question worth
    asking, so ``undeterminable`` and no delivery.

    ★A11: a fourth entry, and it is a fallback rather than an addition.★ The order label is
    read only when no posting exists, because that is A9's precedence -- store, project copy,
    then the label -- and because a posting already opens with its own title, so adding the
    label alongside one would state the same string twice and imply two independent records.

    ★A title is not a specification, and the labels have to keep saying so.★ 「ポケモン動画の
    企画・台本作成ができる方を募集します」 names the deliverable type and nothing else: not the
    count, not the length, not the audience, not the tone. It is filed under its own heading,
    which says on its face that it is a 件名, and ★the posting is still reported as having no
    record★ even when the label was recovered -- because it has none. Collapsing the two
    would tell the judge we hold the buyer's specification when what we hold is its name.
    """
    posting = posting_text(project_root)
    order_label = "" if posting else order_label_text(project_root)
    # (heading, text, name_it_when_absent). The third field exists for one case: when a
    # posting was found the label was never consulted, and listing it among the sources with
    # no record would be a false statement about evidence we did not need and did not look
    # for. Absence is only reported for sources that were actually searched.
    sections: list[tuple[str, str, bool]] = [
        ("募集時の投稿（買い手が支払い前に書いた仕様）", posting, True),
        (
            "この取引の件名（マーケットプレイスの注文名。★件名のみで、仕様書ではありません★）",
            order_label,
            not posting,
        ),
        ("購入前のダイレクトメッセージ（買い手の発言）", dm_text(project_root), True),
        ("取引トークルームでの買い手の発言",
         buyer_order_text(project_root, requirements_path), True),
    ]
    present = [(label, text) for label, text, _ in sections if text.strip()]
    if not present:
        return ""
    blocks = [f"【{label}】\n{text}" for label, text in present]
    missing = [label for label, text, report in sections if report and not text.strip()]
    if missing:
        blocks.append(
            "【この注文には記録が存在しない情報源】\n"
            + "\n".join(f"・{label}" for label in missing)
            + "\nこれらはファイル自体が存在しません。買い手がそこで何かを述べた可能性はありますが、"
            + "その内容はこちらの記録には残っていません。"
        )
    return "\n\n".join(blocks)


def artifact_body(artifact_path: str | Path) -> tuple[str, str]:
    """``("text"|"document", excerpt)``, ``("binary", "")``, or ``("unreadable", "")``.

    ``document`` was added on 2026-08-07 and is the whole reason 91000001 is in the module
    docstring: a Word or PowerPoint file is not plain UTF-8, but it is not opaque either,
    and calling it opaque is what let a Pokémon game guide reach the send step. It routes to
    the model exactly like ``text``; the kinds stay separate so a test can prove which path
    a real ``.docx`` took.

    ★ Strict UTF-8 decoding is the whole test, and it is deliberately not a guess. ★
    ``about_the_deal`` names a readable document about the transaction -- prose a person
    reads. All three measured instances are small UTF-8 text. A zip, an .mcaddon, an mp4
    or a png cannot be prose, and those are what the live projects actually ship: measured
    2026-08-07 across ~/gig/projects/*/artifacts, 29 zip, 15 mcaddon, 5 html, 4 png,
    2 mp4, 2 md. Feeding mojibake to the judge would earn an honest ``undeterminable`` on
    51 of 57 real artifacts and take the paid lane off the air.
    ``errors="replace"`` is avoided for exactly that reason: it would turn "this is not a
    document" into "this is a document full of U+FFFD".
    """
    path = Path(str(artifact_path or "")).expanduser()
    try:
        raw = path.read_bytes()
    except (OSError, ValueError):
        return "unreadable", ""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        extracted = ooxml_text(raw)
        if not extracted:
            return "binary", ""
        return "document", _elide(
            extracted, ARTIFACT_MAX_CHARS, ARTIFACT_HEAD_CHARS, ARTIFACT_TAIL_CHARS
        )
    return "text", _elide(text, ARTIFACT_MAX_CHARS, ARTIFACT_HEAD_CHARS, ARTIFACT_TAIL_CHARS)


# The example is drawn from the third artifact of 2026-08-07
# (~/gig/evidence/gig-pass-1786074007-75714/rejected-output/artifact--delivery-v3.md),
# and deliberately NOT from delivery-v2.md or delivery-v3.md. Those two are the fixtures
# the done-conditions test with; quoting them here would let the judge pass §4-1 and §4-2
# by recognising its own prompt, and prove nothing about a shape it has not been shown.
_ABOUT_THE_DEAL_EXAMPLE = """    # ご確認いただきたい内容の整理資料
    ## まず確認する場所
    この資料は、取引プラットフォームの取引ルーム内でやり取りされる「正式な納品」メッセージに添付されたものです。
    1. 取引トークルームを開きます。"""


def build_prompt(order_text: str, artifact_name: str, artifact_size: int, body: str) -> str:
    """The single question. Nothing else may be added here (31-gig-todo10 §5)."""
    return f"""あなたは納品直前の判定者です。答えるのは次の1問だけです。品質の採点、改善案の提示、文章の書き直しは一切しません。

【問い】この成果物は、この買い手が注文した物ですか。

答えは次の5つのうち1つだけです。
- deliverable: 買い手が注文した物である。買い手はこれを受け取るために代金を払った。
- about_the_deal: 取引そのものについて書かれた文書。確認資料、要件の整理、進捗や状況の説明、確認場所や手順の案内、質問状、計画書などが該当する。買い手が注文した物ではない。
- not_the_order: それ自体は本物の制作物だが、注文された物とは種類が違う。注文が求めた成果物の種類（例: 企画、台本、デザイン、コード、記事）と、この成果物の種類が一致しない場合がこれにあたる。題材や話題が合っていても、成果物の種類が違えば not_the_order です。
- needs_buyer_input: ★注文の側に、何を作るべきかが書かれていない。★ 与えられた記録には題材・分野・納品形式などはあるが、どういう成果物を作るのかが述べられていない。この場合、成果物の良し悪しは判定できない。買い手に質問する必要がある。
- undeterminable: 注文は十分に述べられているが、こちらが見ている成果物の中身が乏しすぎて（抜粋が短い、内容が読み取れない等）判定できない。

★2つの「決められない」を取り違えないでください。★
needs_buyer_input は★注文★が足りない場合です。undeterminable は★成果物の見え方★が足りない場合です。
注文に「何を作るか」が書かれていないなら、成果物がどれほど立派でも deliverable ではありません。needs_buyer_input を選んでください。買い手に質問することは失敗ではなく、正しい前進です。

★記録の読み方（ここを誤ると、正しい納品を止めてしまいます）★
- 募集時の投稿は求人広告です。そこにある「業務内容」は一般的な募集条件であり、この注文の成果物の題材・内容を限定するものではありません。募集文が成果物の題材に触れていないことは、不一致の根拠になりません。
- 後から述べられた具体的な指示（ダイレクトメッセージ、トークルーム）が、募集文の一般的な記述に優先します。買い手が個別に指定した内容が、この注文の実際の中身です。
- ★記録の中で、買い手がこの成果物を既に見て了承している、あるいはこの成果物に対する部分的な修正を依頼しているなら、それは注文された物です。deliverable を選んでください。★ 修正のやり取りが続いていること自体は、成果物が別物であることを意味しません。
- not_the_order を選ぶには「注文は A を求めたが、これは B である」と具体的に言えなければなりません。言えないなら not_the_order ではありません。

★判断は「性質」で行ってください。言い回し、見出し、体裁の違いで判断しないでください。★
同じ性質の文書が、表現だけを変えて繰り返し提出されています。次は実際に提出されたものの冒頭です。

{_ABOUT_THE_DEAL_EXAMPLE}

これは例です。この文面と一致するかどうかで判断しないでください。一致しなくても、性質が同じなら about_the_deal です。

必ず次の順に自問してください。順番を入れ替えないでください。

1. これは取引の進め方、確認方法、要件の整理、進捗の説明、計画、質問状のたぐいの文書か。
   ★この判定に注文の内容は必要ありません。★ 注文が何であれ、またどれほど注文の記録が乏しくても、
   この種の文書が納品物であることはありません。該当するなら about_the_deal。
   ★注文が分からないことを理由に、この判定を避けて needs_buyer_input を選ばないでください。★
2. 買い手はこの成果物を既に見て了承しているか、これに対する部分的な修正を依頼しているか。はいなら deliverable。
3. 記録のどこかに「何を作るか」が書かれているか。募集文の一般論ではなく、この注文に固有の指示として。
   書かれていなければ needs_buyer_input。
4. 書かれているなら、この成果物はその種類の物か。「A を求めたが B である」と具体的に言えるなら not_the_order。
5. どれでもないなら deliverable。

--- 買い手の注文に関する記録 ---
{order_text}
--- ここまで ---

--- 成果物 ---
ファイル名: {artifact_name}
サイズ: {artifact_size} バイト
{body}
--- ここまで ---

reason は日本語1行（120文字以内）で、なぜその verdict になるのかを述べてください。
スキーマに一致する JSON だけを返してください。
"""


# ---------------------------------------------------------------------------
# Reading the answer
# ---------------------------------------------------------------------------

def parse_verdict(payload: Any) -> tuple[str, str]:
    """Three values or nothing.

    ★ Fails CLOSED: anything that is not exactly one of the three known strings becomes
    ``undeterminable``, and ``undeterminable`` does not deliver. ★

    This is not belt-and-braces over the schema, it is the only enforcement there is.
    ``agent_runner.validate_schema`` (agent_runner.py:460) implements ``type``, ``const``,
    ``required``, ``properties``, ``minItems`` and ``items`` -- it does NOT implement
    ``enum``. The ``enum`` in artifact_judgement.schema.json constrains the provider's own
    structured output and nothing else, so a provider that ignores it, or a
    ``claude-direct`` fallback that has no structured-output mode at all, would hand back
    a schema-valid ``{"verdict": "probably fine"}`` and the runner would exit 0.
    """
    if not isinstance(payload, dict):
        return UNDETERMINABLE, "judge result was not an object"
    verdict = payload.get("verdict")
    reason = str(payload.get("reason") or "").strip().replace("\n", " ")[:REASON_MAX_CHARS]
    if not isinstance(verdict, str) or verdict not in VERDICTS:
        return UNDETERMINABLE, f"judge returned an unknown verdict: {str(verdict)[:60]!r}"
    return verdict, reason or "(no reason given)"


def _read_runner_result(evidence_dir: Path) -> tuple[str, str]:
    """The verdict the runner selected, or ``undeterminable`` naming what was missing."""
    try:
        summary = json.loads((evidence_dir / "summary.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return UNDETERMINABLE, "judge produced no runner summary"
    if not isinstance(summary, dict) or summary.get("status") != "success":
        status = summary.get("status") if isinstance(summary, dict) else None
        return UNDETERMINABLE, f"judge runner did not succeed (status={status})"
    result_path = summary.get("result_path")
    if not isinstance(result_path, str) or not result_path:
        return UNDETERMINABLE, "judge runner reported success without a result"
    try:
        payload = json.loads(Path(result_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return UNDETERMINABLE, "judge result file was missing or unparseable"
    return parse_verdict(payload)


def run_judge(
    order_text: str,
    artifact_path: str | Path,
    *,
    runner: str | Path | None = None,
    schema: str | Path | None = None,
    evidence_dir: str | Path,
    timeout_seconds: int = 180,
) -> tuple[str, str]:
    """Ask a separate session the one question. Never raises; never delivers on doubt.

    ★ Separate session, by construction. ★ This is a new OS process running
    ``agent_runner.py``, which builds either ``codex exec --ephemeral`` (no rollout is
    written or resumed) or ``claude --no-session-persistence -p``
    (agent_runner.py:764-819). The builder is a different ``agent_runner.py`` process
    entirely, on task class ``high-value-agent`` with candidate profile
    ``gig-paid-builder`` (gig_pass.sh: ``--task-class high-value-agent
    --candidate-profile gig-paid-builder``), which routes to the ``openclaw`` provider
    with its own generated ``--session-id``. No conversation, no session id and no
    scratch state crosses between them; the only thing this process receives is the two
    pieces of evidence assembled above.

    ``--workdir`` is a fresh empty directory on purpose. The judge is read-only anyway,
    but pointing it at the project root would put the manifest, the acceptance evidence
    and the builder's own notes one ``cat`` away, and the entire point of 31-gig-todo10
    §2.2 is that the judge decides on the artifact and the order, not on the builder's
    account of them.
    """
    runner_path = Path(str(runner or os.environ.get("GIG_ARTIFACT_JUDGE_RUNNER") or DEFAULT_RUNNER)).expanduser()
    schema_path = Path(str(schema or SCHEMA_PATH)).expanduser()
    evidence = Path(evidence_dir).expanduser()
    artifact = Path(str(artifact_path)).expanduser()

    kind, body = artifact_body(artifact)
    if kind == "unreadable":
        return UNDETERMINABLE, "artifact could not be read"
    if kind == "binary":
        # An opaque package -- a zip of decks, an .mcaddon, a png, an mp4. Determinate and
        # free: there is no prose to be wrong about, and 51 of the 57 artifacts in the live
        # projects are this. A gate that stops them is an outage, not a gate.
        #
        # ★ This branch used to swallow .docx and .pptx too, and that is exactly how order
        # 91000001 was cleared without a single model call. ★ The gap is now closed by
        # ``ooxml_text``: a container with readable text arrives above as ``document`` and
        # is judged like any other prose. What is left here is genuinely opaque bytes.
        #
        # Checked before the order text below, on purpose: whether a byte sequence is a
        # readable document does not depend on what the buyer wrote.
        return DELIVERABLE, "opaque binary package: no readable document to judge"
    if not order_text.strip():
        return UNDETERMINABLE, "no buyer message is on record for this order"
    if not runner_path.is_file():
        return UNDETERMINABLE, "judge runner is not installed"
    if not schema_path.is_file():
        return UNDETERMINABLE, "judge schema is not installed"

    try:
        size = artifact.stat().st_size
    except OSError:
        return UNDETERMINABLE, "artifact could not be read"
    prompt = build_prompt(order_text, artifact.name, size, body)

    try:
        evidence.mkdir(parents=True, exist_ok=True)
        prompt_path = evidence / "artifact-judge.prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
    except OSError as error:
        return UNDETERMINABLE, f"judge evidence directory unusable: {error}"

    with tempfile.TemporaryDirectory(prefix="gig-artifact-judge-") as neutral_workdir:
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
            return UNDETERMINABLE, "judge timed out"
        except (OSError, ValueError) as error:
            return UNDETERMINABLE, f"judge could not be launched: {error}"
    # The runner's exit code is not consulted: its own contract is that a fresh
    # schema-valid result is the completion signal (see step_result_status.py on why the
    # exit code alone is not enough). summary.json is that signal.
    return _read_runner_result(evidence)


# ---------------------------------------------------------------------------
# The judge the delivery path actually uses
# ---------------------------------------------------------------------------

def state_root() -> Path:
    return Path(
        os.environ.get("GIG_ARTIFACT_JUDGE_STATE")
        or Path.home() / ".local" / "state" / "anicca" / "gig" / "artifact-judge"
    ).expanduser()


def cache_key(order_text: str, artifact_path: str | Path) -> str:
    """Content address: same order, same bytes, same question -> same answer."""
    digest = hashlib.sha256()
    digest.update(f"v{PROMPT_VERSION}\n".encode("utf-8"))
    digest.update(order_text.encode("utf-8"))
    digest.update(b"\n--artifact--\n")
    try:
        with Path(str(artifact_path)).expanduser().open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except (OSError, ValueError):
        digest.update(b"<unreadable>")
    return digest.hexdigest()


def default_judge(project_root: str | Path, artifact_path: str | Path,
                  requirements_path: str | Path | None = None) -> tuple[str, str]:
    """Judge this artifact, reusing a previous answer about the identical bytes.

    The cache exists to honour the one-model-call-per-order-per-pass budget of
    31-gig-todo10 §2.4: ``validate_and_promote`` runs ``validate_paid_work`` three times
    and ``reconcile_paid_delivery --mark-ready`` runs it a fourth, all in the same pass on
    the same file. It is content-addressed on the buyer's messages plus the artifact's
    bytes plus the prompt version, so a stale answer cannot attach to changed input.

    It lives under ``~/.local/state`` rather than in the project: the project tree is the
    builder's sandbox workspace (the configured Gig projects directory, workspaceAccess rw), and a
    verdict the builder could write is a verdict the builder could forge -- which is the
    failure this whole module exists to stop.
    """
    order_text = order_identity_text(project_root, requirements_path)
    key = cache_key(order_text, artifact_path)
    cached = state_root() / f"{key}.json"
    try:
        payload = json.loads(cached.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and payload.get("verdict") in VERDICTS:
            return str(payload["verdict"]), str(payload.get("reason") or "")
    except (OSError, ValueError):
        pass
    verdict, reason = run_judge(
        order_text, artifact_path, evidence_dir=state_root() / key,
    )
    # ★ Only a determinate answer is remembered. ★ Caching ``undeterminable`` would make
    # one unreachable provider permanently refuse an artifact that a retry could clear.
    # ``needs_buyer_input`` is deliberately NOT cached either, and for the opposite reason:
    # it is a statement about how little the order says, and the whole point of asking the
    # buyer is that the answer changes that. A cached one would outlive the reply it asked
    # for and keep refusing an artifact the buyer has since specified.
    if verdict in (DELIVERABLE, ABOUT_THE_DEAL, NOT_THE_ORDER):
        try:
            cached.parent.mkdir(parents=True, exist_ok=True)
            cached.write_text(
                json.dumps({"verdict": verdict, "reason": reason}, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass
    return verdict, reason


ArtifactJudge = Callable[..., "tuple[str, str]"]


def refuse_unless_deliverable(
    project_root: str | Path,
    artifact_path: str | Path,
    requirements_path: str | Path | None = None,
    *,
    judge: ArtifactJudge | None = None,
    trajectory_context: dict[str, str] | None = None,
) -> tuple[str, str]:
    """Ask the question at the moment of the send. Raise ValueError unless it is the buyer's.

    ★ A gate placed on a state transition misses everything that already crossed. ★

    The first placement of this judge was inside ``validate_and_promote``, which is where
    an artifact becomes deliverable. That is a transition, and it is the wrong object to
    guard. Measured on the live pass of 2026-08-07 15:00 (evidence
    gig-pass-1786082405-78147): the queue row for order 91000002 arrived with
    ``delivery_action=formal`` and ``artifact_path=.../delivery-v3.md``; gig_pass.sh:2259
    skips ``run_paid_work`` entirely when the action is already ``formal``, so neither
    ``validate-promote`` (gig_pass.sh:1889) nor ``--mark-ready`` (gig_pass.sh:1943) ran --
    that pass produced no PAID_WORK.prompt.txt, no agent-PAID_WORK/ and no
    paid-work-transaction.json -- while gig_pass.sh:2276 still ran ``assess_paid_queue``
    and handed the artifact to the delivery browser. v3 had been promoted at 13:04, before
    the gate existed, so it walked past a gate guarding a door it had already come through.
    The judge was invoked zero times in that pass.

    ★ Gate the action, not the transition. ★ This runs immediately before the browser is
    launched, on the artifact the browser is about to attach, resolved from the manifest
    the browser is about to use -- never from a verdict cached in project state, which is
    the builder's own writable tree.

    The normal case is free: when the same pass promoted this artifact, the judge already
    answered about these exact bytes and the content-addressed cache replies without a
    model call. Only the pre-existing-artifact case -- precisely the one that got past --
    pays for a call.

    ★ Fails CLOSED, same direction and same error ids as validate_paid_work. ★ The
    question here is "may I send this to the buyer?", so anything short of a definite yes
    raises. A judge that raises is a judge that has cleared nothing.

    ``trajectory_context`` (EV1, spec §4.1) carries ``{"stage": ..., "lane": ...,
    "resource_key": "talkroom:<id>"}`` from whichever browser is about to send. It is
    recorded HERE rather than at the two call sites because this function already owns the
    verdict and its mapping onto the two error ids -- one place to write the line means a
    third delivery path gets the gate record for free instead of being the one that forgot.
    ★ The trajectory line carries the error ID only, never the judge's own words ★: the
    judge explains itself in the buyer's language, and that prose has no business on disk
    in a file the eval layer will read back.

    The trajectory ``result`` stays ``refused`` for ``needs_buyer_input``, which is accurate
    -- ★the delivery really was refused★ -- even though the loop's next move is a question
    rather than a stop. ``trajectory.RESULTS`` is EV1's vocabulary (``ok`` / ``refused`` /
    ``error`` / ``skipped``) and is not this module's to widen; the ``reason`` field already
    carries the error id, so the two cases are told apart in the record without inventing a
    fifth verb that the eval layer does not know how to read.
    """
    judge = judge or default_judge
    try:
        verdict, reason = judge(project_root, artifact_path, requirements_path)
    except Exception as error:  # noqa: BLE001 - a broken judge has not approved anything
        verdict, reason = UNDETERMINABLE, f"judge raised {type(error).__name__}"
    reason = str(reason or "").replace("\n", " ")[:REASON_MAX_CHARS]
    error_id = ""
    if verdict == ABOUT_THE_DEAL:
        error_id = ERROR_ABOUT_THE_DEAL
    elif verdict == NOT_THE_ORDER:
        error_id = ERROR_NOT_THE_ORDER
    elif verdict == NEEDS_BUYER_INPUT:
        # ★ Still raises. ★ Nothing is sent to the buyer on this path either, and that is
        # the point: the send is wrong, the *question* is right. The caller separates the
        # two with ``should_ask_the_buyer``; a caller that only knows how to stop will stop,
        # which is the old behaviour and no worse than it.
        error_id = ERROR_NEEDS_BUYER_INPUT
    elif verdict != DELIVERABLE:
        error_id = ERROR_UNDETERMINABLE
    if trajectory_context:
        record_trajectory(
            stage=trajectory_context.get("stage") or "PAID_QUEUE_DELIVERY",
            lane=trajectory_context.get("lane") or "delivery",
            resource_key=trajectory_context.get("resource_key") or "",
            action="judge",
            result="ok" if not error_id else "refused",
            reason=error_id,
            artifact_sha256=trajectory_context.get("artifact_sha256"),
        )
    if error_id:
        raise ValueError(f"{error_id}:{reason}")
    return verdict, reason


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--requirements", type=Path)
    args = parser.parse_args()
    verdict, reason = default_judge(args.project_root, args.artifact, args.requirements)
    print(json.dumps(
        {"verdict": verdict, "reason": reason, "ask_the_buyer": verdict == NEEDS_BUYER_INPUT},
        ensure_ascii=False,
    ))
    # Three exits, matching the three the loop has (26-gig-loop §3): 0 send, 2 ask, 1 stop.
    # A shell caller that only checks ``if ok`` still stops on 2, so the new code cannot
    # turn a refusal into a send.
    if verdict == DELIVERABLE:
        return 0
    return 2 if verdict == NEEDS_BUYER_INPUT else 1


if __name__ == "__main__":
    raise SystemExit(_main())
