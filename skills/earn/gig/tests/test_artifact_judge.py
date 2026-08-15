#!/usr/bin/env python3
"""The writer is not the judge.

Every fixture in this file is a real file from 2026-08-07, copied byte-for-byte into
``tests/fixtures/artifact_judge/``:

    delivery-v2.md               1879 B  ★reached the buyer★
    delivery-v3.md               2173 B  committed as current_version, armed
    delivery-v3-quarantined.md   2154 B  quarantined by a rollback, not by a gate
    catalog-page-10756-v16.html 63866 B  a real web page deliverable, order 90000004
    messages-91000002.jsonl               the order as of that capture: three greetings
    messages-90000004.jsonl              17 buyer messages, 12 KB of real instructions

and, added 2026-08-08 after the 23:36 near-miss:

    sample-game-guide-v1.docx      37.8 KB  ★one step from the buyer★, order 91000001
    messages-91000001.jsonl                        that buyer's whole order: a 題材 and a format
    sample-recipe-deck_2段レイアウト.pptx  1.8 MB   a real accepted deck, order 91000002
    messages-91000002-current.jsonl                the same talkroom ten buyer messages later
    posting-91000002.json                          the recruitment ad we applied to
    dm-91000002.json                               the pre-purchase thread that names the spec

★The .docx and the .pptx are the two halves of the same lesson.★ Both are zip containers,
both used to be waved through as "binary" without a model call, and one of them was a
Pokémon game guide sold as 企画・台本 while the other is work the buyer had already accepted.
A rule that reads containers has to get both right or it is not worth having.

The three .md files are one thing wearing three sets of clothes, and prohibition failed on
all three (31-gig-todo10 §1). The .html is the control, and it matters at least as much:
★ a gate that refuses everything is not a gate, it is an outage ★ -- 51 of the 57
artifacts in the live projects are binary containers and the paid lane has to keep
shipping them.

Two kinds of test live here:

  * the ones that always run, driving a stub runner
    (``tests/fixtures/artifact_judge_stub_runner.py``) so that the subprocess boundary, the
    summary read, the verdict parse and every fail-closed path are exercised for free;
  * the ones marked ``live``, which call a real model and are skipped unless
    ``GIG_ARTIFACT_JUDGE_LIVE=1``. Those are the §4 done-conditions. A stub cannot prove
    that a model tells delivery-v3.md apart from a catalog page; only the model can.

        GIG_ARTIFACT_JUDGE_LIVE=1 python3 -m pytest tests/test_artifact_judge.py -k live
"""

from __future__ import annotations

import importlib.util
import json
import os
import zipfile
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "artifact_judge"
STUB_RUNNER = Path(__file__).resolve().parent / "fixtures" / "artifact_judge_stub_runner.py"
REAL_RUNNER = Path.home() / "life-manager" / "skills" / "agent-runner" / "agent_runner.py"

live = pytest.mark.skipif(
    os.environ.get("GIG_ARTIFACT_JUDGE_LIVE") != "1",
    reason="calls a real model; set GIG_ARTIFACT_JUDGE_LIVE=1 to run",
)


def _load(name):
    spec = importlib.util.spec_from_file_location(name, SKILL / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


artifact_judge = _load("artifact_judge")
paid_work_evidence = _load("paid_work_evidence")


# ---------------------------------------------------------------------------
# Project fixtures
# ---------------------------------------------------------------------------

def make_project(tmp_path: Path, *, artifact_name: str, artifact_bytes: bytes,
                 messages: str | None = None,
                 feedback_text: str | None = None) -> tuple[Path, Path, Path]:
    """A project laid out the way the live ones are. Returns (root, artifact, requirements)."""
    root = tmp_path / "projects" / "fixture"
    for name in ("requirements", "artifacts", "acceptance", "delivery", "evidence"):
        (root / name).mkdir(parents=True, exist_ok=True)
    artifact = root / "artifacts" / artifact_name
    artifact.write_bytes(artifact_bytes)
    requirements = root / "requirements" / "live-buyer-reply.json"
    payload = {"version": 2, "feedback_sha256": "a" * 64}
    if feedback_text is not None:
        payload["feedback_text"] = feedback_text
    requirements.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    if messages is not None:
        talkroom = root / "source" / "talkroom"
        talkroom.mkdir(parents=True, exist_ok=True)
        (talkroom / "messages.jsonl").write_text(messages, encoding="utf-8")
    return root, artifact, requirements


def write_pass_queue_item(*, title: str, request_id: str | None = None,
                          talkroom_id: str = "90000001",
                          pass_id: str = "1786117917-44671") -> Path:
    """The row gig_pass.sh hands the delivery browsers, in the shape it has on disk.

    ``$EVIDENCE_DIR/paid-queue-expected.json`` is written from the selected queue row
    (gig_pass.sh:1899 and :2376) and its path is then passed to the progress browser and to
    the formal browser on ``--queue-item`` (:1928, :2389, :2401), immediately before either
    is started. The judge runs inside those two browsers, so this file is what carries the
    marketplace order label to it.
    The fields below are copied from the live file for order 91000001; ``request_id`` is
    omitted rather than blanked when the caller wants the direct-purchase shape, which is
    how 90000004 really sits on disk (23 of the 35 rows present at 08:56 on 2026-08-08 --
    the evidence tree is GC'd so that denominator moves; the shape does not).
    """
    directory = Path(os.environ["GIG_EVIDENCE_ROOT"]) / f"gig-pass-{pass_id}"
    directory.mkdir(parents=True, exist_ok=True)
    row: dict[str, object] = {
        "contract_id": "offer:92000015", "talkroom_id": talkroom_id, "buyer": "買い手A",
        "title": title, "price_jpy": 5000, "price_source": "structured_order_label",
        "status": "paid", "delivery_action": "formal",
    }
    if request_id is not None:
        row["request_id"] = request_id
    path = directory / "paid-queue-expected.json"
    path.write_text(json.dumps(row, ensure_ascii=False), encoding="utf-8")
    return path


def order_91000002(tmp_path: Path, artifact_file: str) -> tuple[Path, Path, Path]:
    return make_project(
        tmp_path,
        artifact_name=artifact_file,
        artifact_bytes=(FIXTURES / artifact_file).read_bytes(),
        messages=(FIXTURES / "messages-91000002.jsonl").read_text(encoding="utf-8"),
    )


def order_90000004(tmp_path: Path) -> tuple[Path, Path, Path]:
    name = "catalog-page-10756-v16.html"
    return make_project(
        tmp_path,
        artifact_name=name,
        artifact_bytes=(FIXTURES / name).read_bytes(),
        messages=(FIXTURES / "messages-90000004.jsonl").read_text(encoding="utf-8"),
    )


def order_91000001(tmp_path: Path) -> tuple[Path, Path, Path]:
    """★The 2026-08-07 23:36 near-miss, byte for byte.★

    A talkroom and nothing else: no posting was ever harvested (the order arrived as
    offer:92000015, a direct offer nobody applied to) and there is no DM. The buyer's whole
    written order is a 題材 and a delivery format.
    """
    name = "sample-game-guide-v1.docx"
    return make_project(
        tmp_path,
        artifact_name=name,
        artifact_bytes=(FIXTURES / name).read_bytes(),
        messages=(FIXTURES / "messages-91000001.jsonl").read_text(encoding="utf-8"),
    )


def order_91000002_with_every_source(tmp_path: Path, artifact_file: str,
                                    monkeypatch) -> tuple[Path, Path, Path]:
    """91000002 as it really sits on disk: posting + DM + talkroom.

    ★This is the one that must never refuse.★ The generic recruitment ad says
    「Canvaを使った画像編集・デザイン制作」; the DM says which images and how many; the
    talkroom has the buyer saying 「ほぼ思った通りの仕上がりです！」 and then asking for four
    photo fixes. Judging the deck against the ad alone produced a false ``not_the_order``.
    """
    store = tmp_path / "postings"
    store.mkdir(exist_ok=True)
    monkeypatch.setenv("GIG_POSTING_STORE", str(store))
    root, artifact, requirements = order_91000002(tmp_path, artifact_file)
    # ★The current capture, not the three-greeting one.★ ``messages-91000002.jsonl`` is a
    # snapshot taken before the buyer had seen anything; the live talkroom holds ten buyer
    # messages, and the seventh is 「ほぼ思った通りの仕上がりです！」 followed by the four photo
    # fixes. Judging a delivered-and-accepted artifact against the order as it stood before
    # delivery is not the question this gate is asked at the moment of the send.
    (root / "source" / "talkroom" / "messages.jsonl").write_bytes(
        (FIXTURES / "messages-91000002-current.jsonl").read_bytes())
    (store / f"request-{root.name}.json").write_bytes(
        (FIXTURES / "posting-91000002.json").read_bytes())
    dm = root / "source" / "dm"
    dm.mkdir(parents=True, exist_ok=True)
    (dm / "thread-90000007-full.json").write_bytes((FIXTURES / "dm-91000002.json").read_bytes())
    return root, artifact, requirements


def use_real_runner(monkeypatch, tmp_path):
    if not REAL_RUNNER.is_file():
        pytest.skip(f"agent runner is not installed at {REAL_RUNNER}")
    monkeypatch.setenv("GIG_ARTIFACT_JUDGE_RUNNER", str(REAL_RUNNER))
    monkeypatch.setenv("GIG_ARTIFACT_JUDGE_STATE", str(tmp_path / "live-judge-state"))


# ---------------------------------------------------------------------------
# §4-1 / §4-2 / §4-3 -- the done conditions, against a real model
# ---------------------------------------------------------------------------

@live
def test_live_the_armed_v3_is_about_the_deal(tmp_path, monkeypatch):
    """§4-1. The 2173-byte artifact sitting in 91000002 right now, with the real order."""
    use_real_runner(monkeypatch, tmp_path)
    root, artifact, _ = order_91000002(tmp_path, "delivery-v3.md")
    verdict, reason = artifact_judge.default_judge(root, artifact)
    assert verdict == artifact_judge.ABOUT_THE_DEAL, (verdict, reason)


@live
def test_live_the_v2_that_reached_the_buyer_is_about_the_deal(tmp_path, monkeypatch):
    """§4-2. The 1879-byte artifact a paying buyer actually received on 2026-08-06."""
    use_real_runner(monkeypatch, tmp_path)
    root, artifact, _ = order_91000002(tmp_path, "delivery-v2.md")
    verdict, reason = artifact_judge.default_judge(root, artifact)
    assert verdict == artifact_judge.ABOUT_THE_DEAL, (verdict, reason)


@live
def test_live_the_quarantined_v3_is_about_the_deal(tmp_path, monkeypatch):
    """The third wording. Not a §4 item, but it is the one the prompt quotes as its
    example -- if the judge could not place it, the example would be doing the work."""
    use_real_runner(monkeypatch, tmp_path)
    root, artifact, _ = order_91000002(tmp_path, "delivery-v3-quarantined.md")
    verdict, reason = artifact_judge.default_judge(root, artifact)
    assert verdict == artifact_judge.ABOUT_THE_DEAL, (verdict, reason)


@live
def test_live_a_real_web_page_deliverable_is_not_refused(tmp_path, monkeypatch):
    """§4-3. ★The one that proves this is a gate and not an outage.★

    63866 bytes of real HTML from order 90000004, judged against 12 KB of that buyer's
    real messages -- both past the truncation thresholds, so this exercises the elision
    rule as well as the verdict.
    """
    use_real_runner(monkeypatch, tmp_path)
    root, artifact, _ = order_90000004(tmp_path)
    verdict, reason = artifact_judge.default_judge(root, artifact)
    assert verdict == artifact_judge.DELIVERABLE, (verdict, reason)


@live
def test_live_the_real_web_page_survives_its_own_order_label(tmp_path, monkeypatch):
    """★A11's own risk test: the label must not refuse the order that pays us.★

    The test above proves nothing about A11, because ``conftest`` points
    ``GIG_EVIDENCE_ROOT`` at an empty directory and no label is ever recovered. ★In
    production this order recovers one.★ 90000004 is a direct 定期購入 purchase with no
    posting anywhere -- measured: no ``request-90000004.json`` in the store, no
    ``source/posting/`` in the project -- so it takes exactly the new third leg, and its real
    queue rows on disk (23 of the 35 present at 08:56 on 2026-08-08) carry
    「ウェブ画像の更新と軽微な調整」.

    ★That string is where the danger is.★ A 63 KB catalog page is not, on its face, an image
    swap, and a judge that reads a 件名 as the specification would answer
    ``not_the_order`` -- the exact false refusal the recruitment-ad rules were written to
    stop, on the exact artifact 26-gig-loop §3 says must keep shipping. So the label is fed
    in here with the real messages, and the assertion is unchanged: still ``deliverable``.
    If this ever flips, the label is being read as a specification and A11 is wrong, not the
    order.
    """
    use_real_runner(monkeypatch, tmp_path)
    monkeypatch.setenv("GIG_POSTING_STORE", str(tmp_path / "no-posting-was-ever-harvested"))
    root, artifact, _ = order_90000004(tmp_path)
    write_pass_queue_item(title="ウェブ画像の更新と軽微な調整", talkroom_id=root.name)
    assert "サイトの画像差し替え" in artifact_judge.order_identity_text(root)
    verdict, reason = artifact_judge.default_judge(root, artifact)
    assert verdict == artifact_judge.DELIVERABLE, (verdict, reason)


# ---------------------------------------------------------------------------
# 2026-08-07 23:36 -- the near-miss, and the delivery it must not cost us
# ---------------------------------------------------------------------------

@live
def test_live_the_pokemon_guide_is_not_deliverable(tmp_path, monkeypatch):
    """★The artifact that was one step from the buyer.★

    Order 91000001 bought 「ポケモン動画の企画・台本作成」. The builder, having never spoken to
    them, produced a general guide to the game and acceptance said PASS. The old judge said
    ``deliverable`` -- twice over: the question could not express "wrong thing", and ``.docx``
    is a zip so it never reached the model at all.

    ★The assertion is deliberately "not deliverable" rather than a specific verdict.★ On the
    materials that actually exist for this order the honest answer is ``needs_buyer_input``:
    the buyer named a 題材 and a file format and never said what to make. A model that
    instead reads it as a definite mismatch and answers ``not_the_order`` is also right to
    stop the send, and pinning one of the two would make this test about the model's mood
    rather than about the send.
    """
    use_real_runner(monkeypatch, tmp_path)
    monkeypatch.setenv("GIG_POSTING_STORE", str(tmp_path / "no-posting-was-ever-harvested"))
    root, artifact, requirements = order_91000001(tmp_path)
    verdict, reason = artifact_judge.default_judge(root, artifact, requirements)
    assert verdict != artifact_judge.DELIVERABLE, (verdict, reason)
    assert verdict in (artifact_judge.NEEDS_BUYER_INPUT, artifact_judge.NOT_THE_ORDER), (
        verdict, reason)


@live
def test_live_the_pokemon_guide_judged_against_its_own_order_label(tmp_path, monkeypatch):
    """★A11: the same artifact, with the one string that says what was bought.★

    Same near-miss as above, except the judge now reads the marketplace order label the way
    A9's builder does. Measured on this fixture, twice, against the real model:

        without the label   needs_buyer_input
                            「題材と納品形式は示されていますが、記事・台本・資料など
                              何を作る注文かが記録されていないため判定できません。」
        with the label      needs_buyer_input
                            「記録には題材と納品形式はあるものの、企画・台本など
                              何を作る注文かの具体的な指定がないため判定できません。」
                            not_the_order
                            「注文はポケモン動画の企画・台本だが、成果物はゲーム紹介の
                              記事作成用基礎資料であり、成果物の種類が異なる。」

    ★The verdict oscillates and the assertion says so, but the reason no longer does.★
    Before, the judge could not name the job at all; after, it names 企画・台本 either way --
    and ``not_the_order`` is a sentence it could not previously form, because step 4 of the
    prompt requires 「注文は A を求めたが、これは B である」 and there was no A. Both answers
    stop the send, which is right: the artifact really is a 基礎資料 and not a 台本.

    ★Still ``needs_buyer_input`` half the time, and that is not a defect.★ A title names the
    deliverable type and nothing else -- not the count, the length, the audience or the tone
    -- and the prompt deliberately refuses to read a 募集 headline as an order-specific
    instruction (that rule exists because reading one as a specification produced a false
    refusal on 91000002). An order whose only record is its own name really is underspecified.
    """
    use_real_runner(monkeypatch, tmp_path)
    monkeypatch.setenv("GIG_POSTING_STORE", str(tmp_path / "no-posting-was-ever-harvested"))
    root, artifact, requirements = order_91000001(tmp_path)
    write_pass_queue_item(title="ポケモン動画の企画・台本作成ができる方を募集します",
                          request_id=root.name)
    order = artifact_judge.order_identity_text(root, requirements)
    assert "企画" in order and "台本" in order
    verdict, reason = artifact_judge.default_judge(root, artifact, requirements)
    assert verdict != artifact_judge.DELIVERABLE, (verdict, reason)
    assert verdict in (artifact_judge.NEEDS_BUYER_INPUT, artifact_judge.NOT_THE_ORDER), (
        verdict, reason)


@live
def test_live_the_real_deck_the_buyer_already_approved_is_deliverable(tmp_path, monkeypatch):
    """★The regression that would cost real money, measured rather than assumed.★

    Before the precedence rules were added to the prompt, this exact call returned
    ``not_the_order``: 「注文は既存画像4枚を編集可能なCanvaデータとして納品することですが、成果物は
    焼肉説明文のPowerPointです」. The judge had weighed the generic recruitment ad above the
    DM that named the actual images and above the buyer's own
    「ほぼ思った通りの仕上がりです！」. A judge that refuses work the buyer has already accepted
    is not a safer loop, it is a loop that earns nothing (26-gig-loop §3).

    ★The artifact here is 2段レイアウト and the choice is load-bearing.★ The sibling file
    ``肉ぶくろ流_sample-recipe-deck_4コマ.pptx`` was tried first and the judge refused it with
    「注文は…（指定画像の構成）を求めているが、成果物は4コマのみのPowerPointファイルである」 --
    ★and that refusal is correct★. The DM asks for 4コマ, 5コマ and 6コマ 「ひとつずつ」, so any
    one of the three is a component rather than the delivery; what actually shipped is the
    v5 zip holding all of them. 2段レイアウト carries all three layouts in a single file,
    which is the whole ask. Pinning the component as ``deliverable`` would have taught the
    judge to accept partial work.
    """
    use_real_runner(monkeypatch, tmp_path)
    root, artifact, requirements = order_91000002_with_every_source(
        tmp_path, "sample-recipe-deck_2段レイアウト.pptx", monkeypatch)
    verdict, reason = artifact_judge.default_judge(root, artifact, requirements)
    assert verdict == artifact_judge.DELIVERABLE, (verdict, reason)


def test_the_prompt_ranks_specific_instructions_over_the_recruitment_ad():
    """The false refusal above was a prompt defect, so the fix is pinned here.

    A posting is an advertisement for a worker, not a specification of the artifact. Without
    these four rules the judge treats "the ad never mentioned 焼肉" as evidence of mismatch.
    """
    prompt = artifact_judge.build_prompt("注文", "a.pptx", 10, "本文")
    assert "募集時の投稿は求人広告です" in prompt
    assert "募集文が成果物の題材に触れていないことは、不一致の根拠になりません" in prompt
    assert "後から述べられた具体的な指示" in prompt
    assert "買い手がこの成果物を既に見て了承している" in prompt
    # not_the_order must require a nameable mismatch, not merely an unexplained gap.
    assert "「注文は A を求めたが、これは B である」と具体的に言えなければなりません" in prompt


# ---------------------------------------------------------------------------
# §4-4 -- every way the judge can fail is a refusal
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "mode",
    ["crash", "malformed", "no_result", "unknown"],
)
def test_a_judge_that_does_not_answer_refuses_the_delivery(tmp_path, monkeypatch, mode):
    """§4-4. ★Fails CLOSED in every direction.★

    ``unknown`` is not redundant with the schema. ``agent_runner.validate_schema``
    implements type/const/required/properties/minItems/items and has no ``enum``, so a
    result of ``{"verdict": "probably fine", "reason": "..."}`` is schema-valid to the
    runner and exits 0. The three-value clamp in ``parse_verdict`` is the only thing
    standing between that string and a delivery.
    """
    monkeypatch.setenv("GIG_ARTIFACT_JUDGE_STUB", mode)
    root, artifact, _ = order_91000002(tmp_path, "delivery-v3.md")
    verdict, reason = artifact_judge.default_judge(root, artifact)
    assert verdict == artifact_judge.UNDETERMINABLE, (verdict, reason)
    assert reason


def test_a_judge_that_hangs_refuses_the_delivery(tmp_path, monkeypatch):
    """§4-4, timeout. The stub sleeps for an hour; the judge must not wait for it."""
    monkeypatch.setenv("GIG_ARTIFACT_JUDGE_STUB", "hang")
    monkeypatch.setattr(artifact_judge, "RUNNER_GRACE_SECONDS", 1)
    root, artifact, _ = order_91000002(tmp_path, "delivery-v3.md")
    order = artifact_judge.buyer_order_text(root)
    verdict, reason = artifact_judge.run_judge(
        order, artifact, evidence_dir=tmp_path / "judge-evidence", timeout_seconds=1,
    )
    assert verdict == artifact_judge.UNDETERMINABLE
    assert reason == "judge timed out"


def test_an_uninstalled_judge_refuses_the_delivery(tmp_path, monkeypatch):
    monkeypatch.setenv("GIG_ARTIFACT_JUDGE_RUNNER", str(tmp_path / "no-such-runner.py"))
    root, artifact, _ = order_91000002(tmp_path, "delivery-v3.md")
    verdict, reason = artifact_judge.default_judge(root, artifact)
    assert verdict == artifact_judge.UNDETERMINABLE
    assert reason == "judge runner is not installed"


def test_an_order_with_no_buyer_words_is_undeterminable(tmp_path):
    """No order text, no question worth asking -- and no delivery.

    The direction is deliberate. Every one of the eight live projects has buyer text, from
    a captured talkroom or from a requirements file, so this is not a case the healthy path
    hits; an order where we cannot find a single word from the buyer is the 91000002 shape,
    and that one should stop and ask.
    """
    root, artifact, _ = make_project(
        tmp_path, artifact_name="delivery-v3.md",
        artifact_bytes=(FIXTURES / "delivery-v3.md").read_bytes(),
    )
    verdict, reason = artifact_judge.default_judge(root, artifact)
    assert verdict == artifact_judge.UNDETERMINABLE
    assert reason == "no buyer message is on record for this order"


def test_an_unreadable_artifact_is_undeterminable(tmp_path):
    root, artifact, _ = order_91000002(tmp_path, "delivery-v3.md")
    artifact.unlink()
    verdict, reason = artifact_judge.default_judge(root, artifact)
    assert verdict == artifact_judge.UNDETERMINABLE
    assert reason == "artifact could not be read"


def test_parse_verdict_admits_exactly_the_five_known_strings():
    assert artifact_judge.VERDICTS == (
        "deliverable", "about_the_deal", "not_the_order",
        "needs_buyer_input", "undeterminable",
    )
    for value in artifact_judge.VERDICTS:
        assert artifact_judge.parse_verdict({"verdict": value, "reason": "r"})[0] == value
    for bad in ({}, [], None, {"verdict": "DELIVERABLE"}, {"verdict": "ok"},
                {"verdict": 1}, {"reason": "no verdict"}):
        assert artifact_judge.parse_verdict(bad)[0] == artifact_judge.UNDETERMINABLE


# ---------------------------------------------------------------------------
# §4-5 -- validate_paid_work carries the verdict into its errors list
# ---------------------------------------------------------------------------

def _valid_package(tmp_path: Path, artifact_file: str) -> tuple[Path, Path]:
    """A structurally perfect package around one of the real artifacts.

    Everything the deterministic gates look at is correct: the hash binds, v2 beats the
    recorded v1, paths are owned, acceptance says PASS and the deltas match. This is what
    2026-08-06 looked like from inside -- which is the point.
    """
    root, artifact, requirements = order_91000002(tmp_path, artifact_file)
    version = "v3" if "v3" in artifact_file else "v2"
    delta = ["確認できる内容を整理しました。"]
    acceptance = root / "acceptance" / f"acceptance-{version}.json"
    acceptance.write_text(
        json.dumps({"status": "PASS", "acceptance_delta": delta}, ensure_ascii=False),
        encoding="utf-8",
    )
    row = {
        "status": "ok",
        "project_root": str(root),
        "requirements_path": str(requirements),
        "artifact_path": str(artifact),
        "artifact_version": version,
        "acceptance_evidence_path": str(acceptance),
        "acceptance_status": "PASS",
        "acceptance_delta": delta,
        "package_sha256": __import__("hashlib").sha256(artifact.read_bytes()).hexdigest(),
    }
    (root / "state.json").write_text('{"current_version":"v1"}\n', encoding="utf-8")
    (root / "delivery" / "paid-work-result.json").write_text(
        json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    evidence = tmp_path / "delivery-evidence" / "fixture.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    return root, evidence


@pytest.mark.parametrize("artifact_file", ["delivery-v2.md", "delivery-v3.md",
                                           "delivery-v3-quarantined.md"])
def test_about_the_deal_is_pushed_onto_the_errors_list(tmp_path, artifact_file):
    """§4-5. All three of the day's artifacts pass every structural check, and stop here."""
    root, evidence = _valid_package(tmp_path, artifact_file)

    ok, errors = paid_work_evidence.validate_paid_work(
        root, evidence,
        artifact_judge=lambda *_a, **_k: (artifact_judge.ABOUT_THE_DEAL, "確認資料である"),
    )
    assert ok is False
    assert errors == [paid_work_evidence.ARTIFACT_ABOUT_THE_DEAL], errors

    # ...and the same package is fine as far as every pre-existing gate is concerned.
    ok, errors = paid_work_evidence.validate_paid_work(
        root, evidence,
        artifact_judge=lambda *_a, **_k: (artifact_judge.DELIVERABLE, "buyer's file"),
    )
    assert ok is True, errors


def test_no_judge_at_all_is_a_refusal_not_a_waiver(tmp_path):
    """★The default must not be "ship it".★

    Both earlier misses were checks with nothing to look at: the bootstrap validator that
    only measured file size, and the BLOCKED contradiction check the builder disarmed by
    staying silent. A caller that forgets the judge gets a refusal, in the same words as
    an unreachable one.
    """
    root, evidence = _valid_package(tmp_path, "delivery-v3.md")
    ok, errors = paid_work_evidence.validate_paid_work(root, evidence)
    assert ok is False
    assert errors == [paid_work_evidence.ARTIFACT_JUDGEMENT_UNDETERMINABLE], errors


def test_a_judge_that_raises_is_a_refusal(tmp_path):
    def explode(*_args, **_kwargs):
        raise RuntimeError("judge blew up")

    root, evidence = _valid_package(tmp_path, "delivery-v3.md")
    ok, errors = paid_work_evidence.validate_paid_work(root, evidence, artifact_judge=explode)
    assert ok is False
    assert errors == [paid_work_evidence.ARTIFACT_JUDGEMENT_UNDETERMINABLE], errors


def test_structure_only_is_the_single_documented_exemption(tmp_path):
    """The pre-check marker skips the question; nothing else may.

    Paired with the promote-level tests in test_paid_work_transaction.py, which prove the
    same package is still refused later in the same function.
    """
    root, evidence = _valid_package(tmp_path, "delivery-v3.md")
    ok, errors = paid_work_evidence.validate_paid_work(
        root, evidence, artifact_judge=paid_work_evidence.STRUCTURE_ONLY)
    assert ok is True, errors


def test_a_structurally_broken_package_never_pays_for_a_judge(tmp_path):
    """The question is asked last, so a broken manifest costs nothing."""
    calls = []

    def counting_judge(*args, **kwargs):
        calls.append(args)
        return artifact_judge.DELIVERABLE, "should not be reached"

    root, evidence = _valid_package(tmp_path, "delivery-v3.md")
    (root / "artifacts" / "delivery-v3.md").write_text("tampered", encoding="utf-8")
    ok, errors = paid_work_evidence.validate_paid_work(
        root, evidence, artifact_judge=counting_judge)
    assert ok is False
    assert "package_sha256_mismatch" in errors
    assert calls == []


# ---------------------------------------------------------------------------
# What the judge is shown
# ---------------------------------------------------------------------------

def _fixture_buyer_texts(name: str) -> list[str]:
    """The buyer-side texts of an export-excluded real capture, read at runtime.

    The expected values live in the fixture, not as literals in this file: a
    static quote of the real sentence would itself be a verbatim PII leak in
    the exported test, while reading the (never-shipped) fixture keeps the
    assertion exact -- review I2, replacing an earlier shape-only weakening.
    """
    return [
        row["text"]
        for row in (json.loads(line) for line in
                    (FIXTURES / name).read_text(encoding="utf-8").splitlines() if line.strip())
        if row.get("side") == "buyer" and row.get("text")
    ]


def test_the_buyers_own_messages_are_the_order_and_ours_are_not(tmp_path):
    root, _artifact, _req = order_91000002(tmp_path, "delivery-v2.md")
    order = artifact_judge.buyer_order_text(root)
    # Exactly the buyer-side messages of the capture, in order, and nothing else
    # (the second buyer message carries its own newline through splitlines).
    expected = "\n".join(_fixture_buyer_texts("messages-91000002.jsonl"))
    assert order.splitlines() == expected.splitlines()
    # Our own outgoing sales prose is in the same file and must not be read as the order.
    assert "ご購入ありがとうございます" not in order


def test_the_requirements_file_is_the_fallback_when_no_talkroom_was_captured(tmp_path):
    """Five of the eight live projects have no messages.jsonl, only feedback_text."""
    root, _artifact, requirements = make_project(
        tmp_path, artifact_name="delivery-v3.md", artifact_bytes=b"x",
        feedback_text="直っていませんね。",
    )
    assert artifact_judge.buyer_order_text(root, requirements) == "直っていませんね。"
    # A captured talkroom wins over it: the talkroom rows are not builder-written.
    (root / "source" / "talkroom").mkdir(parents=True)
    (root / "source" / "talkroom" / "messages.jsonl").write_text(
        json.dumps({"side": "buyer", "text": "青にしてください"}, ensure_ascii=False) + "\n",
        encoding="utf-8")
    assert artifact_judge.buyer_order_text(root, requirements) == "青にしてください"


# ---------------------------------------------------------------------------
# The order's identity: what the judge is now allowed to read
# ---------------------------------------------------------------------------
#
# Measured across the nine live projects on 2026-08-07, because the spec's claim that all
# three sources "arrive every pass" is not what is on disk:
#
#     source/talkroom/   4 of 9
#     source/dm/         3 of 9   (only 1 of those 3 carries per-message `side`)
#     source/posting/    1 of 9
#
# ★ Order 91000001 has none but the talkroom. ★ That is not a bug in the collection; it
# arrived as offer:92000015, a direct offer nobody applied to, so no posting was ever
# harvested -- ~/gig/postings held 34 files that night and request-91000001.json was not one.
# The judge therefore cannot be fixed by "read more files" alone, which is what
# needs_buyer_input is for.


def test_the_posting_is_read_and_its_title_leads(tmp_path, monkeypatch):
    """The title is the most order-identifying string that exists.

    For 91000001 it is the only place the words 企画 and 台本 appear at all.
    """
    monkeypatch.setenv("GIG_POSTING_STORE", str(tmp_path / "empty-store"))
    root, _artifact, _req = order_91000002(tmp_path, "delivery-v2.md")
    (root / "source" / "posting").mkdir(parents=True)
    (root / "source" / "posting" / "request-91000002.json").write_text(
        json.dumps({"title": "ポケモン動画の企画・台本作成ができる方を募集します",
                    "body": "【業務内容】台本を1本書いてください。"}, ensure_ascii=False),
        encoding="utf-8")
    posting = artifact_judge.posting_text(root)
    assert posting.startswith("題目: ポケモン動画の企画・台本作成ができる方を募集します")
    assert "台本を1本書いてください" in posting


def test_the_durable_store_is_preferred_over_the_builder_writable_copy(tmp_path, monkeypatch):
    """★The project tree is the builder's rw sandbox; the store is not.★

    A builder that could restate the order it was judged against could pass any judgement,
    which is the failure this whole module exists to stop.
    """
    store = tmp_path / "postings"
    store.mkdir()
    monkeypatch.setenv("GIG_POSTING_STORE", str(store))
    root, _artifact, _req = order_91000002(tmp_path, "delivery-v2.md")
    (store / f"request-{root.name}.json").write_text(
        json.dumps({"title": "本物の募集", "body": "harvested at application time"},
                   ensure_ascii=False), encoding="utf-8")
    (root / "source" / "posting").mkdir(parents=True)
    (root / "source" / "posting" / "request-9.json").write_text(
        json.dumps({"title": "書き換えられた募集", "body": "written by the builder"},
                   ensure_ascii=False), encoding="utf-8")
    posting = artifact_judge.posting_text(root)
    assert "本物の募集" in posting
    assert "書き換えられた募集" not in posting


def test_only_side_attributed_dm_threads_are_read(tmp_path, monkeypatch):
    """Two shapes share the filename and only one says who spoke.

    90000004 and 90000000 store a raw page scrape (``url/title/text/files``) holding both
    halves of the conversation undifferentiated. Reading it would feed our own sales prose
    back as if it were the order.
    """
    monkeypatch.setenv("GIG_POSTING_STORE", str(tmp_path / "empty-store"))
    root, _artifact, _req = order_91000002(tmp_path, "delivery-v2.md")
    dm = root / "source" / "dm"
    dm.mkdir(parents=True)
    (dm / "thread-90000007-full.json").write_text(json.dumps({"messages": [
        {"side": "buyer", "text": "4枚でお願いします"},
        {"side": "seller", "text": "ご購入ありがとうございます"},
    ]}, ensure_ascii=False), encoding="utf-8")
    (dm / "thread-93000003-full.json").write_text(json.dumps({
        "url": "https://coconala.com/dm/93000003", "title": "t",
        "text": "この生スクレイプには話者の区別がありません", "files": [],
    }, ensure_ascii=False), encoding="utf-8")
    text = artifact_judge.dm_text(root)
    assert text == "4枚でお願いします"
    assert "ご購入ありがとうございます" not in text
    assert "生スクレイプ" not in text


def test_absent_sources_are_named_so_silence_is_not_read_as_a_specification(tmp_path, monkeypatch):
    """★91000001's exact shape: a talkroom and nothing else.★

    Naming the gap is what lets the judge tell "the buyer said nothing about what to build"
    apart from "a specification exists and this artifact misses it". Without it, a 題材 gets
    read as though it were a spec -- the mistake the builder had already made.
    """
    monkeypatch.setenv("GIG_POSTING_STORE", str(tmp_path / "empty-store"))
    root, _artifact, _req = make_project(
        tmp_path, artifact_name="a.docx", artifact_bytes=b"x",
        messages=json.dumps({"side": "buyer", "text": "題材『パズルクエストX』"},
                            ensure_ascii=False) + "\n",
    )
    order = artifact_judge.order_identity_text(root)
    assert "題材『パズルクエストX』" in order
    assert "【この注文には記録が存在しない情報源】" in order
    assert "募集時の投稿" in order
    assert "ダイレクトメッセージ" in order


def test_an_order_with_every_source_carries_all_three_labelled(tmp_path, monkeypatch):
    store = tmp_path / "postings"
    store.mkdir()
    monkeypatch.setenv("GIG_POSTING_STORE", str(store))
    root, _artifact, _req = order_91000002(tmp_path, "delivery-v2.md")
    (store / f"request-{root.name}.json").write_text(
        json.dumps({"title": "募集の題目", "body": "本文"}, ensure_ascii=False), encoding="utf-8")
    dm = root / "source" / "dm"
    dm.mkdir(parents=True)
    (dm / "thread-1-full.json").write_text(
        json.dumps({"messages": [{"side": "buyer", "text": "DMでの指定"}]}, ensure_ascii=False),
        encoding="utf-8")
    order = artifact_judge.order_identity_text(root)
    assert "【募集時の投稿（買い手が支払い前に書いた仕様）】" in order
    assert "【購入前のダイレクトメッセージ（買い手の発言）】" in order
    assert "【取引トークルームでの買い手の発言】" in order
    assert "【この注文には記録が存在しない情報源】" not in order
    for expected in ("募集の題目", "DMでの指定", "よろしくお願いいたします！！"):
        assert expected in order


def test_an_order_with_nothing_on_record_stays_empty(tmp_path, monkeypatch):
    """Unchanged meaning: no order, no question worth asking, no delivery."""
    monkeypatch.setenv("GIG_POSTING_STORE", str(tmp_path / "empty-store"))
    root, _artifact, _req = make_project(tmp_path, artifact_name="a.md", artifact_bytes=b"x")
    assert artifact_judge.order_identity_text(root) == ""


# ---------------------------------------------------------------------------
# A11 -- the order label, the only carrier a direct offer has
#
# A9 (97a7536e) gave the builder this same third source at the entrance, with the
# precedence: durable store, project copy, then queue_item.title. The judge had only the
# first two, so for 91000001 the words 企画 and 台本 reached neither end of the loop.
# ---------------------------------------------------------------------------

def test_a_direct_offer_recovers_the_only_string_that_names_what_it_bought(tmp_path, monkeypatch):
    """★The A11 defect, in the shape 91000001 really has.★

    No posting was ever harvested -- the order arrived as offer:92000015 and nothing was
    applied to -- so store and project copy are both empty and the judge's whole view of the
    order was 「題材『パズルクエストX』… 納品はGoogleドキュメントで」. A 題材 and a file
    format are not a deliverable.
    """
    monkeypatch.setenv("GIG_POSTING_STORE", str(tmp_path / "no-posting-was-ever-harvested"))
    root, _artifact, _req = make_project(
        tmp_path, artifact_name="a.docx", artifact_bytes=b"x",
        messages=json.dumps({"side": "buyer", "text": "題材『パズルクエストX』"},
                            ensure_ascii=False) + "\n",
    )
    assert artifact_judge.order_label_text(root) == ""
    write_pass_queue_item(title="ポケモン動画の企画・台本作成ができる方を募集します",
                          request_id=root.name)
    order = artifact_judge.order_identity_text(root)
    assert "企画" in order and "台本" in order
    assert "【この取引の件名" in order


def test_the_buyers_own_posting_outranks_the_scraped_label(tmp_path, monkeypatch):
    """★Precedence, not accumulation -- A9's order, mirrored.★

    The label is third because it is a marketplace label rather than the buyer's document,
    and a posting already leads with its own title. Emitting both would state one string
    twice and imply two independent records of the order.
    """
    store = tmp_path / "postings"
    store.mkdir()
    monkeypatch.setenv("GIG_POSTING_STORE", str(store))
    root, _artifact, _req = order_91000002(tmp_path, "delivery-v2.md")
    (store / f"request-{root.name}.json").write_text(
        json.dumps({"title": "本物の募集", "body": "買い手が支払い前に書いた仕様"},
                   ensure_ascii=False), encoding="utf-8")
    write_pass_queue_item(title="マーケットプレイスの注文名", request_id=root.name)
    order = artifact_judge.order_identity_text(root)
    assert "本物の募集" in order
    assert "マーケットプレイスの注文名" not in order
    # ...and a source that was never consulted is not reported as one with no record.
    assert "【この取引の件名" not in order


def test_a_recovered_title_never_passes_itself_off_as_the_buyers_posting(tmp_path, monkeypatch):
    """★A title is not a specification, and absence stays visible.★

    「ポケモン動画の企画・台本作成ができる方を募集します」 names the deliverable type and
    nothing else: not the count, not the length, not the audience, not the tone. So the
    posting is still reported as having no record even once the label is recovered, and the
    label sits under a heading that says what it is.
    """
    monkeypatch.setenv("GIG_POSTING_STORE", str(tmp_path / "empty-store"))
    root, _artifact, _req = make_project(
        tmp_path, artifact_name="a.docx", artifact_bytes=b"x",
        messages=json.dumps({"side": "buyer", "text": "題材『パズルクエストX』"},
                            ensure_ascii=False) + "\n",
    )
    write_pass_queue_item(title="ポケモン動画の企画・台本作成ができる方を募集します",
                          request_id=root.name)
    order = artifact_judge.order_identity_text(root)
    assert "件名のみで、仕様書ではありません" in order
    missing = order.split("【この注文には記録が存在しない情報源】")[1]
    assert "募集時の投稿" in missing
    assert "ダイレクトメッセージ" in missing


def test_a_direct_purchase_with_no_request_id_is_keyed_by_its_talkroom(tmp_path, monkeypatch):
    """90000004's shape: ¥2,500, status=paid, no 募集 anywhere, so no request_id at all.

    Measured 2026-08-08 08:56 over the 35 queue items then on disk: 23 of them are this one,
    keyed by talkroom. It is also ``validate_queue_contract``'s identity rule and the key
    ``~/gig/projects/90000004`` is already stored under.
    """
    monkeypatch.setenv("GIG_POSTING_STORE", str(tmp_path / "empty-store"))
    root, _artifact, _req = make_project(
        tmp_path, artifact_name="a.html", artifact_bytes=b"<p>x</p>",
        messages=json.dumps({"side": "buyer", "text": "よろしくお願いします"},
                            ensure_ascii=False) + "\n",
    )
    write_pass_queue_item(title="ウェブ画像の更新と軽微な調整", talkroom_id=root.name)
    assert artifact_judge.order_label_text(root) == "ウェブ画像の更新と軽微な調整"


def test_another_orders_label_is_never_borrowed(tmp_path, monkeypatch):
    """★The evidence tree holds every recent pass, so identity has to be checked.★

    Judging one buyer's artifact against another buyer's order would be a worse failure
    than the blindness this fixes.
    """
    monkeypatch.setenv("GIG_POSTING_STORE", str(tmp_path / "empty-store"))
    root, _artifact, _req = make_project(tmp_path, artifact_name="a.md", artifact_bytes=b"x")
    write_pass_queue_item(title="別の注文の件名", request_id="9999999",
                          talkroom_id="9999999", pass_id="1786000000-11111")
    assert artifact_judge.order_label_text(root) == ""


def test_the_newest_pass_wins_and_an_unreadable_row_is_stepped_over(tmp_path, monkeypatch):
    """A pass that is running right now rewrites this file; a half-written one must not stop
    the judge, and the current pass's answer is the one that counts."""
    monkeypatch.setenv("GIG_POSTING_STORE", str(tmp_path / "empty-store"))
    root, _artifact, _req = make_project(tmp_path, artifact_name="a.md", artifact_bytes=b"x")
    old = write_pass_queue_item(title="古い件名", request_id=root.name,
                                pass_id="1786000000-11111")
    os.utime(old, (1786000000, 1786000000))
    broken = write_pass_queue_item(title="x", request_id=root.name, pass_id="1786100000-22222")
    broken.write_text("{ this is not json", encoding="utf-8")
    os.utime(broken, (1786100000, 1786100000))
    fresh = write_pass_queue_item(title="今回のパスの件名", request_id=root.name,
                                  pass_id="1786117917-44671")
    os.utime(fresh, (1786117917, 1786117917))
    assert artifact_judge.order_label_text(root) == "今回のパスの件名"


def test_no_pass_evidence_at_all_is_silence_not_a_crash(tmp_path, monkeypatch):
    """The judge is a delivery gate: a missing evidence tree must leave it exactly where it
    was, never raise inside the browser that is about to send."""
    monkeypatch.setenv("GIG_POSTING_STORE", str(tmp_path / "empty-store"))
    monkeypatch.setenv("GIG_EVIDENCE_ROOT", str(tmp_path / "no-such-evidence-root"))
    root, _artifact, _req = make_project(tmp_path, artifact_name="a.md", artifact_bytes=b"x")
    assert artifact_judge.order_label_text(root) == ""
    assert artifact_judge.order_identity_text(root) == ""


# ---------------------------------------------------------------------------
# Ask, refuse, deliver -- the caller has to be able to tell them apart
# ---------------------------------------------------------------------------

def test_needs_buyer_input_is_distinguishable_from_a_refusal(tmp_path, monkeypatch):
    """★26-gig-loop §3: asking is progress, not a stop.★

    Another lane builds the message to the buyer. It consumes this verdict, so the split has
    to be readable from the raised error without string surgery at the call site.
    """
    monkeypatch.setenv("GIG_ARTIFACT_JUDGE_STUB", "needs_buyer_input")
    root, artifact, _ = order_91000002(tmp_path, "delivery-v3.md")
    with pytest.raises(ValueError) as raised:
        artifact_judge.refuse_unless_deliverable(root, artifact)
    assert artifact_judge.split_error(raised.value)[0] == artifact_judge.ERROR_NEEDS_BUYER_INPUT
    assert artifact_judge.should_ask_the_buyer(raised.value) is True

    # A genuine mismatch is NOT an invitation to ask; it is a refusal.
    monkeypatch.setenv("GIG_ARTIFACT_JUDGE_STUB", "not_the_order")
    root2, artifact2, _ = order_91000002(tmp_path / "second", "delivery-v2.md")
    with pytest.raises(ValueError) as refused:
        artifact_judge.refuse_unless_deliverable(root2, artifact2)
    assert artifact_judge.split_error(refused.value)[0] == artifact_judge.ERROR_NOT_THE_ORDER
    assert artifact_judge.should_ask_the_buyer(refused.value) is False


def test_a_reason_containing_colons_survives_the_split():
    """The reason is free Japanese prose and may hold colons; only the first one splits."""
    error = ValueError(f"{artifact_judge.ERROR_NOT_THE_ORDER}:注文: 台本。成果物: 紹介資料")
    error_id, reason = artifact_judge.split_error(error)
    assert error_id == artifact_judge.ERROR_NOT_THE_ORDER
    assert reason == "注文: 台本。成果物: 紹介資料"
    # An unrelated exception is not silently claimed as one of ours.
    assert artifact_judge.split_error(ValueError("some other failure")) == (
        "", "some other failure")
    assert artifact_judge.should_ask_the_buyer(ValueError("some other failure")) is False


def test_needs_buyer_input_is_never_cached(tmp_path, monkeypatch):
    """★The point of asking is that the answer changes the order.★

    A cached "the order does not say what to build" would outlive the buyer's reply and keep
    refusing an artifact they have since specified.
    """
    root, artifact, _ = order_91000002(tmp_path, "delivery-v3.md")
    monkeypatch.setenv("GIG_ARTIFACT_JUDGE_STUB", "needs_buyer_input")
    assert artifact_judge.default_judge(root, artifact)[0] == artifact_judge.NEEDS_BUYER_INPUT
    monkeypatch.setenv("GIG_ARTIFACT_JUDGE_STUB", "deliverable")
    assert artifact_judge.default_judge(root, artifact)[0] == artifact_judge.DELIVERABLE


def test_nothing_but_deliverable_lets_the_send_proceed(tmp_path, monkeypatch):
    """Every non-deliverable verdict still raises. The new ones widen triage, not the gate."""
    root, artifact, _ = order_91000002(tmp_path, "delivery-v3.md")
    for mode, expected in (
        ("about_the_deal", artifact_judge.ERROR_ABOUT_THE_DEAL),
        ("not_the_order", artifact_judge.ERROR_NOT_THE_ORDER),
        ("needs_buyer_input", artifact_judge.ERROR_NEEDS_BUYER_INPUT),
        ("undeterminable", artifact_judge.ERROR_UNDETERMINABLE),
        ("unknown", artifact_judge.ERROR_UNDETERMINABLE),
        ("crash", artifact_judge.ERROR_UNDETERMINABLE),
    ):
        monkeypatch.setenv("GIG_ARTIFACT_JUDGE_STUB", mode)
        monkeypatch.setenv("GIG_ARTIFACT_JUDGE_STATE", str(tmp_path / f"state-{mode}"))
        with pytest.raises(ValueError) as raised:
            artifact_judge.refuse_unless_deliverable(root, artifact)
        assert artifact_judge.split_error(raised.value)[0] == expected


def test_a_binary_artifact_is_deliverable_without_a_model_call(tmp_path, monkeypatch):
    """29 zip, 15 mcaddon, 4 png and 2 mp4 live in the projects right now.

    ``about_the_deal`` names a readable document. A byte sequence that is not UTF-8 is not
    one, so the answer is determinate and free. ``crash`` proves no runner was launched:
    the stub would have exited nonzero if it had been.
    """
    monkeypatch.setenv("GIG_ARTIFACT_JUDGE_STUB", "crash")
    root, artifact, _ = make_project(
        tmp_path, artifact_name="delivery-v3.zip",
        artifact_bytes=b"PK\x03\x04\x00\x00\xff\xfe\x00binary",
        feedback_text="ロゴを作ってください",
    )
    verdict, reason = artifact_judge.default_judge(root, artifact)
    assert verdict == artifact_judge.DELIVERABLE
    assert "binary" in reason


def test_the_real_13mb_zip_delivery_is_still_free_and_still_deliverable(tmp_path, monkeypatch):
    """★The regression that would cost real money.★

    ``肉ぶくろ流_焼肉の美味しい焼き方_v5.zip`` is order 91000002's actual current artifact: a
    13 MB archive whose nine entries are four ``.pptx`` files and a preview directory. It is
    a zip, and ``.docx``/``.pptx`` are zips too, so a text extractor written carelessly
    would start reading it, find nothing it understands, and turn a real delivery into a
    refusal. ``ooxml_text`` keys on the three OOXML part names, not on the container format,
    so this archive has none of them and stays an opaque package. ``crash`` proves the model
    was never called.
    """
    monkeypatch.setenv("GIG_ARTIFACT_JUDGE_STUB", "crash")
    nested = tmp_path / "nested.zip"
    with zipfile.ZipFile(nested, "w") as archive:
        archive.writestr("肉ぶくろ流_sample-recipe-deck_4コマ_v5.pptx", b"\x00\x01inner")
        archive.writestr("preview/", b"")
    root, artifact, _ = make_project(
        tmp_path, artifact_name="delivery-v5.zip",
        artifact_bytes=nested.read_bytes(),
        feedback_text="スライドを作ってください",
    )
    assert artifact_judge.artifact_body(artifact)[0] == "binary"
    assert artifact_judge.default_judge(root, artifact)[0] == artifact_judge.DELIVERABLE


def test_an_ooxml_container_is_read_as_a_document_and_reaches_the_model(tmp_path, monkeypatch):
    """★The branch order 91000001 walked past.★

    ``sample-game-guide-v1.docx`` is a zip, so the old code called it binary and
    returned ``deliverable`` without asking anything. A Word file carries its prose in
    ``word/document.xml`` as ``<w:t>`` nodes; the judge now reads them and asks the question.
    """
    document_xml = (
        '<?xml version="1.0"?><w:document xmlns:w="x"><w:body>'
        "<w:p><w:r><w:t>Pok&#233;quest</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>ゲーム紹介・記事作成用 基礎資料</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>概要: 架空のバトルに焦点を当てた新作タイトルです。</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>据置機版は20XX年配信、スマートフォン版は20XX年に配信。</w:t></w:r></w:p>"
        "</w:body></w:document>"
    )
    docx = tmp_path / "built.docx"
    with zipfile.ZipFile(docx, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", document_xml)
    kind, body = artifact_judge.artifact_body(docx)
    assert kind == "document"
    # The XML entity is decoded, so the judge reads what a reader would see.
    assert "Pokéquest" in body
    assert "ゲーム紹介・記事作成用 基礎資料" in body
    assert "<w:t>" not in body

    # And it is now judged rather than waved through: the stub is asked, and it refuses.
    monkeypatch.setenv("GIG_ARTIFACT_JUDGE_STUB", "not_the_order")
    root, artifact, requirements = make_project(
        tmp_path, artifact_name="guide-v1.docx", artifact_bytes=docx.read_bytes(),
        feedback_text="企画と台本を書いてください",
    )
    assert artifact_judge.default_judge(root, artifact, requirements)[0] == (
        artifact_judge.NOT_THE_ORDER)


def test_an_image_only_deck_stays_an_opaque_package(tmp_path, monkeypatch):
    """A slide deck with no text nodes has nothing to judge, and guessing would be worse.

    ``OOXML_MIN_CHARS`` is what stops a container with a scrap of boilerplate from being
    presented to the judge as though it were a readable document.
    """
    monkeypatch.setenv("GIG_ARTIFACT_JUDGE_STUB", "crash")
    deck = tmp_path / "images.pptx"
    with zipfile.ZipFile(deck, "w") as archive:
        archive.writestr("ppt/slides/slide1.xml", '<?xml version="1.0"?><p:sld><p:pic/></p:sld>')
        archive.writestr("ppt/media/image1.png", b"\x89PNG\r\n\x1a\n")
    assert artifact_judge.artifact_body(deck)[0] == "binary"
    root, artifact, _ = make_project(
        tmp_path, artifact_name="images.pptx", artifact_bytes=deck.read_bytes(),
        feedback_text="スライドを作ってください",
    )
    assert artifact_judge.default_judge(root, artifact)[0] == artifact_judge.DELIVERABLE


def test_a_corrupt_container_is_not_mistaken_for_a_document(tmp_path):
    assert artifact_judge.ooxml_text(b"PK\x03\x04 truncated and broken") == ""


def test_a_large_text_artifact_is_shown_head_and_tail_with_the_gap_named(tmp_path):
    """★Head-only would make the real HTML control unjudgeable on a bad day.★

    Its first 6000 characters happen to be informative; an artifact whose first 6000 are a
    minified stylesheet would arrive as pure boilerplate, earn an honest ``undeterminable``
    and block a real delivery. Head plus tail costs nothing and removes most of that risk.
    """
    html = (FIXTURES / "catalog-page-10756-v16.html").read_text(encoding="utf-8")
    kind, body = artifact_judge.artifact_body(FIXTURES / "catalog-page-10756-v16.html")
    assert kind == "text"
    assert len(body) < len(html)
    assert body.startswith(html[: artifact_judge.ARTIFACT_HEAD_CHARS])
    assert body.endswith(html[-artifact_judge.ARTIFACT_TAIL_CHARS:])
    assert "文字省略" in body
    # The elision notice states the true size of the gap, so the judge is never told a
    # partial file is the whole file.
    dropped = len(html) - artifact_judge.ARTIFACT_HEAD_CHARS - artifact_judge.ARTIFACT_TAIL_CHARS
    assert f"［中略: {dropped} 文字省略］" in body


def test_every_artifact_of_the_failure_class_is_shown_whole(tmp_path):
    """The documents this gate exists to catch are far below the threshold."""
    for name in ("delivery-v2.md", "delivery-v3.md", "delivery-v3-quarantined.md"):
        text = (FIXTURES / name).read_text(encoding="utf-8")
        kind, body = artifact_judge.artifact_body(FIXTURES / name)
        assert kind == "text"
        assert body == text, name


def test_a_long_order_keeps_the_original_request_and_the_latest_one(tmp_path):
    root, _artifact, _req = order_90000004(tmp_path)
    order = artifact_judge.buyer_order_text(root)
    assert len(order) <= artifact_judge.ORDER_MAX_CHARS + 64
    assert "文字省略" in order
    # Expected head/tail read from the export-excluded fixture at runtime (see
    # _fixture_buyer_texts): the elided order must still OPEN with the buyer's
    # original request and CLOSE with their latest message, byte for byte.
    buyer_texts = _fixture_buyer_texts("messages-90000004.jsonl")
    assert order.startswith(buyer_texts[0][:20])
    assert order.endswith(buyer_texts[-1][-20:])


def test_the_prompt_asks_one_question_and_carries_both_pieces_of_evidence():
    prompt = artifact_judge.build_prompt("青いロゴを作ってください", "delivery-v3.md", 2173, "# 確認資料")
    for value in artifact_judge.VERDICTS:
        assert value in prompt
    assert "青いロゴを作ってください" in prompt
    assert "delivery-v3.md" in prompt
    assert "# 確認資料" in prompt
    # ★One question only (31-gig-todo10 §2.2, §5).★ Exactly one question is posed, and
    # scoring / advice / rewriting are named only to be refused.
    assert prompt.count("【問い】") == 1
    assert "答えるのは次の1問だけです" in prompt
    assert "品質の採点、改善案の提示、文章の書き直しは一切しません" in prompt
    # ★The question itself is the 2026-08-07 23:36 fix.★ "is this about the deal" could not
    # express "this is a real work product, but not the one that was bought".
    assert "この成果物は、この買い手が注文した物ですか。" in prompt
    # The two "cannot decide" answers are on different axes and the prompt must say so, or
    # a model will use them interchangeably and the asking lane will never fire.
    assert "needs_buyer_input は★注文★が足りない場合です" in prompt
    assert "undeterminable は★成果物の見え方★が足りない場合です" in prompt


def test_the_judge_runs_read_only_in_a_session_that_wrote_nothing():
    """Pinned against agent_runner, because the guarantee lives there, not here.

    ``diagnostic-agent`` is one of the three task classes agent_runner gives
    ``--sandbox read-only`` (codex) and ``--tools ""`` (claude); every other class gets
    ``--dangerously-bypass-approvals-and-sandbox``. If that list is ever edited, this
    fails rather than silently handing the judge a writable workspace.
    """
    runner_source = (SKILL.parent / "agent-runner" / "agent_runner.py").read_text(encoding="utf-8")
    assert artifact_judge.TASK_CLASS == "diagnostic-agent"
    assert runner_source.count(
        '"composition-agent", "diagnostic-agent", "application-intent-planner",'
    ) == 2
    assert '"--sandbox", "read-only"' in runner_source
    assert '"--tools", ""' in runner_source
    # A one-shot process either way: codex writes no rollout, claude persists no session.
    assert '"--ephemeral"' in runner_source
    assert '"--no-session-persistence"' in runner_source


def test_the_schema_pins_every_verdict_value_for_the_provider():
    schema = json.loads(artifact_judge.SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["properties"]["verdict"]["enum"] == list(artifact_judge.VERDICTS)
    assert schema["required"] == ["verdict", "reason"]
    assert schema["additionalProperties"] is False


def test_a_determinate_answer_is_reused_and_an_undeterminable_one_is_not(tmp_path, monkeypatch):
    """The cache is what keeps this at one model call per order per pass (§2.4).

    ``validate_and_promote`` asks twice and ``--mark-ready`` a third time, all about the
    same bytes. Caching a refusal would be different in kind: one unreachable provider
    would permanently condemn an artifact a retry could clear.
    """
    root, artifact, _ = order_91000002(tmp_path, "delivery-v3.md")

    monkeypatch.setenv("GIG_ARTIFACT_JUDGE_STUB", "about_the_deal")
    assert artifact_judge.default_judge(root, artifact)[0] == artifact_judge.ABOUT_THE_DEAL
    # The stub would now say deliverable; the remembered answer about these bytes wins.
    monkeypatch.setenv("GIG_ARTIFACT_JUDGE_STUB", "deliverable")
    assert artifact_judge.default_judge(root, artifact)[0] == artifact_judge.ABOUT_THE_DEAL
    # Different bytes, different question, no reuse.
    artifact.write_bytes((FIXTURES / "delivery-v2.md").read_bytes())
    assert artifact_judge.default_judge(root, artifact)[0] == artifact_judge.DELIVERABLE

    # Different bytes again, so this is a fresh question rather than a cache hit.
    other = tmp_path / "second"
    root2, artifact2, _ = order_91000002(other, "delivery-v3-quarantined.md")
    monkeypatch.setenv("GIG_ARTIFACT_JUDGE_STUB", "crash")
    assert artifact_judge.default_judge(root2, artifact2)[0] == artifact_judge.UNDETERMINABLE
    monkeypatch.setenv("GIG_ARTIFACT_JUDGE_STUB", "deliverable")
    assert artifact_judge.default_judge(root2, artifact2)[0] == artifact_judge.DELIVERABLE


# ---------------------------------------------------------------------------
# Gate the action, not the transition
# ---------------------------------------------------------------------------
#
# The judge's first home was validate_and_promote, which guards the moment an artifact
# BECOMES deliverable. Measured on the live pass of 2026-08-07 15:00
# (gig-pass-1786082405-78147): order 91000002 arrived with delivery_action=formal and
# artifact_path=.../delivery-v3.md, gig_pass.sh:2259 skipped run_paid_work because the
# action was already formal, and gig_pass.sh:2276 handed the artifact straight to the
# delivery browser. That pass wrote no PAID_WORK.prompt.txt, no agent-PAID_WORK/ and no
# paid-work-transaction.json, and the judge cache stayed empty: zero invocations. v3 was
# promoted at 13:04, before the gate existed, so it never had to pass through it.
#
# The tests below are about the send itself.

def _formal_fixture(tmp_path: Path, artifact_file: str = "delivery-v3.md"):
    """A queue row and manifest exactly as the formal browser is handed them."""
    root, artifact, requirements = order_91000002(tmp_path, artifact_file)
    delta = ["確認できる内容を整理しました。"]
    acceptance = root / "acceptance" / "v3.json"
    digest = __import__("hashlib").sha256(artifact.read_bytes()).hexdigest()
    acceptance.write_text(
        json.dumps({"status": "PASS", "package": {"sha256": digest}}, ensure_ascii=False),
        encoding="utf-8")
    manifest = {
        "status": "ok",
        "acceptance_status": "PASS",
        "project_root": str(root),
        "requirements_path": str(requirements),
        "artifact_path": str(artifact),
        "artifact_version": "v3",
        "acceptance_evidence_path": str(acceptance),
        "acceptance_delta": delta,
        "package_sha256": digest,
    }
    queue = {
        "delivery_action": "formal",
        "formal_delivery_checkbox": True,
        "delivery_evidence": {
            key: manifest[key] for key in (
                "artifact_path", "artifact_version", "acceptance_evidence_path",
                "acceptance_status", "acceptance_delta", "package_sha256")
        },
        "talkroom_id": "90000002",
        "request_id": "91000002",
        "marketplace_url": "https://coconala.com/talkrooms/90000002",
    }
    queue_path = tmp_path / "queue.json"
    queue_path.write_text(json.dumps(queue, ensure_ascii=False), encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return root, queue_path, manifest_path


def _progress_fixture(tmp_path: Path, artifact_file: str = "delivery-v3.md"):
    root, artifact, requirements = order_91000002(tmp_path, artifact_file)
    delta = ["確認できる内容を整理しました。"]
    acceptance = root / "acceptance" / "v3.json"
    acceptance.write_text('{"status":"PASS"}\n', encoding="utf-8")
    digest = __import__("hashlib").sha256(artifact.read_bytes()).hexdigest()
    manifest = {
        "status": "ok",
        "project_root": str(root),
        "requirements_path": str(requirements),
        "artifact_path": str(artifact),
        "artifact_version": "v3",
        "acceptance_evidence_path": str(acceptance),
        "acceptance_status": "PASS",
        "acceptance_delta": delta,
        "package_sha256": digest,
    }
    queue = {
        "talkroom_id": "90000002",
        "marketplace_url": "https://coconala.com/talkrooms/90000002",
        "delivery_action": "progress",
        "formal_delivery_checkbox": False,
        "progress_payload": {
            "mode": "progress",
            "formal_delivery_checkbox": False,
            "buyer_visible": True,
            "artifact_version": "v3",
            "acceptance_delta": delta,
            "blockers": ["buyer_agreement_not_observed"],
            "message": "お世話になっております。修正版をお送りします。\nご確認ください。",
        },
        "delivery_evidence": {k: v for k, v in manifest.items() if k != "requirements_path"},
    }
    queue_path = tmp_path / "queue.json"
    queue_path.write_text(json.dumps(queue, ensure_ascii=False), encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return root, queue_path, manifest_path


def _load_browser(name: str, alias: str):
    import sys
    scripts = str(SKILL / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    spec = importlib.util.spec_from_file_location(alias, SKILL / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _BrowserMustNotOpen:
    """Substituted for collector.DefaultTab: opening it at all is the failure."""

    def __init__(self, *args, **kwargs):
        raise AssertionError("the delivery browser was launched on an unjudged artifact")


def _run_formal_main(module, monkeypatch, tmp_path, queue_path, manifest_path, root):
    import sys
    ledger = tmp_path / "events.jsonl"
    evidence = tmp_path / "evidence"
    monkeypatch.setattr(module.collector, "DefaultTab", _BrowserMustNotOpen)
    monkeypatch.setattr(sys, "argv", [
        "coconala_formal_delivery_browser.py",
        "--queue-item", str(queue_path),
        "--manifest", str(manifest_path),
        "--project-root", str(root),
        "--evidence-dir", str(evidence),
        "--ledger", str(ledger),
        "--default-tab-helper", str(tmp_path / "unused-helper.py"),
    ])
    return ledger


def test_the_formal_send_refuses_an_artifact_the_judge_calls_about_the_deal(
        tmp_path, monkeypatch):
    """★The 15:00 miss, closed.★ Nothing here entered PAID_WORK; the artifact was already
    promoted. The send still has to answer the question."""
    module = _load_browser("coconala_formal_delivery_browser", "formal_judge_gate")
    root, queue_path, manifest_path = _formal_fixture(tmp_path)
    ledger = _run_formal_main(module, monkeypatch, tmp_path, queue_path, manifest_path, root)
    monkeypatch.setenv("GIG_ARTIFACT_JUDGE_STUB", "about_the_deal")

    with pytest.raises(ValueError, match="artifact_is_about_the_deal_not_the_deliverable"):
        module.main()
    # Refused before the delivery intent was recorded, not just before the click.
    assert not ledger.exists()


def test_the_formal_send_refuses_when_the_judge_cannot_be_reached(tmp_path, monkeypatch):
    module = _load_browser("coconala_formal_delivery_browser", "formal_judge_gate_2")
    root, queue_path, manifest_path = _formal_fixture(tmp_path)
    ledger = _run_formal_main(module, monkeypatch, tmp_path, queue_path, manifest_path, root)
    monkeypatch.setenv("GIG_ARTIFACT_JUDGE_STUB", "crash")

    with pytest.raises(ValueError, match="artifact_judgement_undeterminable"):
        module.main()
    assert not ledger.exists()


def test_the_formal_send_proceeds_past_the_gate_for_a_real_deliverable(tmp_path, monkeypatch):
    """The gate must let work through. Reaching the browser is the pass condition -- the
    sentinel proves the judge did not stop it, and stops the test before any real tab."""
    module = _load_browser("coconala_formal_delivery_browser", "formal_judge_gate_3")
    root, queue_path, manifest_path = _formal_fixture(tmp_path)
    _run_formal_main(module, monkeypatch, tmp_path, queue_path, manifest_path, root)
    monkeypatch.setenv("GIG_ARTIFACT_JUDGE_STUB", "deliverable")

    with pytest.raises(AssertionError, match="the delivery browser was launched"):
        module.main()


def test_the_progress_send_refuses_an_artifact_the_judge_calls_about_the_deal(
        tmp_path, monkeypatch):
    import sys
    module = _load_browser("coconala_paid_progress_browser", "progress_judge_gate")
    root, queue_path, manifest_path = _progress_fixture(tmp_path)
    monkeypatch.setattr(module.collector, "DefaultTab", _BrowserMustNotOpen)
    monkeypatch.setattr(sys, "argv", [
        "coconala_paid_progress_browser.py",
        "--queue-item", str(queue_path),
        "--manifest", str(manifest_path),
        "--evidence-dir", str(tmp_path / "evidence"),
        "--default-tab-helper", str(tmp_path / "unused-helper.py"),
    ])
    monkeypatch.setenv("GIG_ARTIFACT_JUDGE_STUB", "about_the_deal")

    with pytest.raises(ValueError, match="artifact_is_about_the_deal_not_the_deliverable"):
        module._main()


def test_the_progress_send_proceeds_past_the_gate_for_a_real_deliverable(tmp_path, monkeypatch):
    import sys
    module = _load_browser("coconala_paid_progress_browser", "progress_judge_gate_2")
    root, queue_path, manifest_path = _progress_fixture(tmp_path)
    monkeypatch.setattr(module.collector, "DefaultTab", _BrowserMustNotOpen)
    monkeypatch.setattr(sys, "argv", [
        "coconala_paid_progress_browser.py",
        "--queue-item", str(queue_path),
        "--manifest", str(manifest_path),
        "--evidence-dir", str(tmp_path / "evidence"),
        "--default-tab-helper", str(tmp_path / "unused-helper.py"),
    ])
    monkeypatch.setenv("GIG_ARTIFACT_JUDGE_STUB", "deliverable")

    with pytest.raises(AssertionError, match="the delivery browser was launched"):
        module._main()


def test_the_send_gate_reads_the_manifest_not_a_verdict_cached_in_project_state(
        tmp_path, monkeypatch):
    """The artifact judged must be the one the browser is about to attach.

    Project state is the builder's own writable tree, so a `current_version` field
    claiming an artifact was cleared proves nothing. Here state.json says v3 is fine and
    buyer-visible; the manifest still points at the document, and the send still refuses.
    """
    module = _load_browser("coconala_formal_delivery_browser", "formal_judge_gate_4")
    root, queue_path, manifest_path = _formal_fixture(tmp_path)
    (root / "state.json").write_text(json.dumps({
        "current_version": "v3", "buyer_visible": True,
        "current_acceptance_status": "PASS", "artifact_judgement": "deliverable",
    }), encoding="utf-8")
    ledger = _run_formal_main(module, monkeypatch, tmp_path, queue_path, manifest_path, root)
    monkeypatch.setenv("GIG_ARTIFACT_JUDGE_STUB", "about_the_deal")

    with pytest.raises(ValueError, match="artifact_is_about_the_deal_not_the_deliverable"):
        module.main()
    assert not ledger.exists()


def test_refuse_unless_deliverable_is_the_one_shared_refusal():
    judged = artifact_judge.refuse_unless_deliverable(
        "/nonexistent", "/nonexistent/a.md",
        judge=lambda *_a, **_k: (artifact_judge.DELIVERABLE, "buyer's file"))
    assert judged == (artifact_judge.DELIVERABLE, "buyer's file")

    with pytest.raises(ValueError, match="artifact_is_about_the_deal_not_the_deliverable"):
        artifact_judge.refuse_unless_deliverable(
            "/x", "/x/a.md",
            judge=lambda *_a, **_k: (artifact_judge.ABOUT_THE_DEAL, "確認資料"))

    for bad in ((artifact_judge.UNDETERMINABLE, "unreachable"), ("probably fine", "?")):
        with pytest.raises(ValueError, match="artifact_judgement_undeterminable"):
            artifact_judge.refuse_unless_deliverable(
                "/x", "/x/a.md", judge=lambda *_a, _b=bad, **_k: _b)

    def explode(*_args, **_kwargs):
        raise RuntimeError("boom")

    with pytest.raises(ValueError, match="artifact_judgement_undeterminable"):
        artifact_judge.refuse_unless_deliverable("/x", "/x/a.md", judge=explode)


def test_both_gates_refuse_under_the_same_two_names():
    """Promotion-time and send-time refusals must not be triaged as different bugs."""
    assert paid_work_evidence.ARTIFACT_ABOUT_THE_DEAL == artifact_judge.ERROR_ABOUT_THE_DEAL
    assert (paid_work_evidence.ARTIFACT_JUDGEMENT_UNDETERMINABLE
            == artifact_judge.ERROR_UNDETERMINABLE)


def test_the_cache_lives_outside_the_builders_sandbox_workspace(monkeypatch):
    """A verdict the builder can write is a verdict the builder can forge.

    The paid builder runs with workspaceAccess rw on /workspace/gig/projects
    (config.json, candidate_profiles.gig-paid-builder), which is why the project tree is
    not an option.
    """
    monkeypatch.delenv("GIG_ARTIFACT_JUDGE_STATE", raising=False)
    root = artifact_judge.state_root()
    assert root == Path.home() / ".local/state/anicca/gig/artifact-judge"
    assert not str(root).startswith("/workspace/gig/projects")
