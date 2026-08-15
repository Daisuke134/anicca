"""TODO 3c -- one mouth per room.

On 2026-08-07 talkroom 90000002 (order 91000002, deadline 08-11) had two lanes speaking into
it. PAID_WORK carried the requirements, the BLOCKED record and the four gates built that
day. The B1 reply lane carried the text on the screen and nothing else, and it was B1 that
told a paying buyer to go and read delivery-v2.md -- 1879 bytes that are not a deliverable
-- and separately reported 「こちらでさせていただきました」 over no work at all.

These tests hold the two halves of the fix apart on purpose:

  * the registry (project_effect_fence) must name paid rooms from LOOKED-UP order data,
  * the chokepoint (reply_executor) must refuse before the browser is ever touched,
  * a pre-purchase DM must still go out, because converting enquiries is the lane's job,
  * and observation of a fenced room must be untouched, because downstream consumes it.
"""

import hashlib
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(f"todo3c_{name}", SCRIPTS / f"{name}.py")
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fence = load("project_effect_fence")
gate = load("b1_conversation_gate")

PAID_ROOM = "90000002"
OTHER_PAID_ROOM = "90000004"
ENQUIRY_ROOM = "42"
NOW = datetime(2026, 8, 7, 3, 0, tzinfo=timezone.utc)


def snapshot_with(paid_ids, inquiry_ids=()):
    return {
        "version": 1,
        "captured_at": "2026-08-07T03:00:00+00:00",
        "inbox": {"url": "https://coconala.com/message?fromMyPage=true", "not_found": False},
        "orders": [
            {
                "contract_id": f"direct-offer:{room}",
                "talkroom_id": room,
                "status": "paid",
                "marketplace_url": f"https://coconala.com/talkrooms/{room}",
            }
            for room in paid_ids
        ],
        "quotes": [],
        "inquiries": [
            {
                "talkroom_id": room,
                "talkroom_url": f"https://coconala.com/talkrooms/{room}",
                "reply_required": True,
            }
            for room in inquiry_ids
        ],
    }


class RecordingBrowser:
    """Records every method the executor reaches, so 'never sent' is provable."""

    def __init__(self, controller, action_id):
        self.controller = controller
        self.action_id = action_id
        self.events = []
        self.body = ""
        self.url = "https://coconala.com/mypage/direct_message/42"

    def read_before(self):
        self.events.append("read_before")
        return (
            {"latest_buyer_message": "購入前の質問です"},
            {"talkroom_id": "42", "url": self.url, "fingerprint": "before", "seller_count": 1},
        )

    def fill(self, body):
        self.events.append("fill")
        self.body = body

    def click(self):
        self.events.append("click")

    def read_after(self):
        self.events.append("read_after")
        return {
            "talkroom_id": "42",
            "url": self.url,
            "fingerprint": "after",
            "seller_count": 2,
            "seller_message_hashes": [hashlib.sha256(self.body.encode()).hexdigest()],
            "seller_sent_at": "1970-01-01T00:01:45+00:00",
            "last_sender": "seller",
        }

    def failure_evidence(self, error):
        return {"status": "read_failed", "send_network": [], "browser_error_code": "x"}


class PaidTalkroomRegistryTest(unittest.TestCase):
    def test_membership_comes_from_orders_not_from_titles_or_text(self):
        # Looked up, never inferred. A room is fenced because an order names it.
        registry = fence.paid_conversation_registry(
            snapshot_with([PAID_ROOM, OTHER_PAID_ROOM], inquiry_ids=[ENQUIRY_ROOM]),
            opened_at=NOW,
        )

        fence.validate_registry(registry)
        self.assertEqual(
            {f["identities"]["talkroom_id"] for f in registry["fences"]},
            {PAID_ROOM, OTHER_PAID_ROOM},
        )
        self.assertEqual(
            fence.write_fenced_talkroom_ids(registry, now=NOW),
            frozenset({PAID_ROOM, OTHER_PAID_ROOM}),
        )

    def test_the_delivery_queue_is_unioned_in_so_neither_source_alone_can_miss_a_room(self):
        registry = fence.paid_conversation_registry(
            snapshot_with([OTHER_PAID_ROOM]),
            {"items": [{"talkroom_id": PAID_ROOM, "queue_class": "buyer_feedback_or_revision"}]},
            opened_at=NOW,
        )

        self.assertEqual(
            fence.write_fenced_talkroom_ids(registry, now=NOW),
            frozenset({PAID_ROOM, OTHER_PAID_ROOM}),
        )

    def test_a_source_that_cannot_be_trusted_raises_instead_of_returning_a_short_set(self):
        # A half-read orders list would silently unfence a paying customer's room.
        with self.assertRaises(fence.FenceError):
            fence.paid_talkroom_ids({"orders": "not-a-list"})
        with self.assertRaises(fence.FenceError):
            fence.paid_talkroom_ids(snapshot_with([]), {"items": ["not-a-row"]})

    def test_an_unreadable_registry_is_none_not_an_empty_set(self):
        # "I could not look" must not arrive at a caller looking like "nothing is fenced".
        self.assertIsNone(fence.write_fenced_talkroom_ids(None))
        self.assertIsNone(fence.write_fenced_talkroom_ids({"version": 2, "fences": []}))
        self.assertEqual(fence.write_fenced_talkroom_ids({"version": 1, "fences": []}), frozenset())


class B1ContextFenceTest(unittest.TestCase):
    """The registry has existed and been unwired; this proves it now reaches the lane."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def _context(self, fence_registry):
        snapshot_path = self.root / "marketplace-snapshot.json"
        queue_path = self.root / "delivery-queue.json"
        snapshot = snapshot_with([PAID_ROOM], inquiry_ids=[ENQUIRY_ROOM])
        snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
        queue_path.write_text(json.dumps({"items": []}), encoding="utf-8")
        return gate.build_context(
            snapshot,
            {"items": []},
            snapshot_path,
            queue_path,
            fence_registry=fence_registry,
        )

    def test_a_paid_room_is_absent_from_b1_targets_and_an_enquiry_is_still_there(self):
        # The real prevention. Marking the room unwritable was never going to hold: B1 has
        # a shell and a websocket and reached 送信 without calling one line of ours. A room
        # it is never given is a room it does not open. The enquiry must survive, because
        # answering unbought buyers is the entire reason this lane exists.
        for registry in (None, fence.paid_conversation_registry(
            snapshot_with([PAID_ROOM], inquiry_ids=[ENQUIRY_ROOM]), opened_at=NOW
        )):
            with self.subTest(fenced=registry is not None):
                context = self._context(registry)
                ids = [r["talkroom_id"] for r in context["actionable_talkrooms"]]

                self.assertNotIn(PAID_ROOM, ids)
                self.assertIn(ENQUIRY_ROOM, ids)
                # Removal does not depend on the fence file existing. A registry that fails
                # to build cannot hand the paid room back to B1.
                self.assertEqual(context["forbidden_talkrooms"], [PAID_ROOM])

    def test_the_collector_observation_of_the_paid_room_is_what_survives(self):
        # The fact the removal rests on: coconala_queue_snapshot writes the paid room's
        # screenshot and DOM for every order, before any lane, with no model. Asserted
        # against the collector's own source so a future edit that stops writing these --
        # which would turn this removal into real blindness -- fails here.
        collector = (SCRIPTS / "coconala_queue_snapshot.py").read_text(encoding="utf-8")

        self.assertIn("for order in orders:", collector)
        self.assertIn(
            'args.evidence_dir / f"talkroom-{safe_name(order[\'talkroom_id\'])}.png"',
            collector,
        )
        self.assertIn(
            'talkroom_path = args.evidence_dir / f"talkroom-{safe_name(order[\'talkroom_id\'])}.json"',
            collector,
        )
        # ...and it runs before any lane, into the pass evidence dir the readers glob.
        pass_source = (ROOT / "gig_pass.sh").read_text(encoding="utf-8")
        self.assertIn(
            'coconala_queue_snapshot.py" --output "$SNAPSHOT" --evidence-dir "$EVIDENCE_DIR/live-dom"',
            pass_source,
        )
        for reader in ("thread_freshness.py", "state_reconciler.py"):
            self.assertIn(
                'glob.glob(str(EVIDENCE / "*" / "live-dom" / f"talkroom-{talkroom_id}.json"))',
                (SCRIPTS / reader).read_text(encoding="utf-8"),
            )

    def test_no_consumer_reads_b1_own_talkroom_evidence(self):
        # The claim this whole step rests on, checked rather than asserted. The only reader
        # of anything under agent-B1/ is report_envelope, and it reads the result JSON for
        # talkroom ids and outcomes -- never the per-room screenshot or live DOM.
        readers = []
        for path in list(SCRIPTS.glob("*.py")) + [ROOT / "gig_pass.sh"]:
            # Code only. Prose that merely names the directory -- including the comment in
            # b1_conversation_gate that records this very finding -- is not a consumer.
            code = "\n".join(
                line for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()
                if not line.lstrip().startswith("#")
            )
            if "agent-B1" in code:
                readers.append(path.name)

        self.assertEqual(readers, ["report_envelope.py"])
        envelope = (SCRIPTS / "report_envelope.py").read_text(encoding="utf-8")
        self.assertIn('evidence_dir / "agent-B1" / "attempt-01.result.json"', envelope)
        # It takes ids and outcomes off the result, never a per-room evidence file. The one
        # live_dom_path in this module belongs to the PAID_WORK delivery event, which is a
        # different lane reading a different artifact.
        self.assertEqual(
            [line.strip() for line in envelope.splitlines() if "live_dom" in line],
            ['"live_dom_path": delivery.get("live_dom_path"),'],
        )
        self.assertNotIn("live-dom", envelope)

    def _run_validate_result(self, *, visited_paid_room, outcome="observed_no_action"):
        """Drive the real validate_result over a real evidence tree, not a stand-in."""
        evidence = self.root / "agent-B1"
        evidence.mkdir(parents=True, exist_ok=True)
        registry = fence.paid_conversation_registry(
            snapshot_with([PAID_ROOM], inquiry_ids=[ENQUIRY_ROOM]), opened_at=NOW
        )
        context = self._context(registry)
        context_path = self.root / "b1-context.json"
        context_path.write_text(
            json.dumps(context, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )

        def observed(name, url):
            shot = evidence / f"{name}.png"
            shot.write_bytes(b"\x89PNG observed")
            dom = evidence / f"{name}.live-dom.json"
            dom.write_text(
                json.dumps({"url": url, "not_found": False, "observed": True}),
                encoding="utf-8",
            )
            return str(shot), str(dom)

        inbox_shot, inbox_dom = observed("inbox", gate.INBOX_URL)
        rows = list(context["actionable_talkrooms"])
        if visited_paid_room:
            # B1 wandering into a room it was never given -- what the removal is meant to
            # make impossible, and what the gate must catch if it happens anyway.
            rows.append({
                "talkroom_id": PAID_ROOM,
                "url": f"https://coconala.com/talkrooms/{PAID_ROOM}",
            })
        inspected = []
        for row in rows:
            shot, dom = observed(f"talkroom-{row['talkroom_id']}", row["url"])
            inspected.append({
                "talkroom_id": row["talkroom_id"],
                "url": row["url"],
                # Only the paid room varies; the enquiry is always merely observed, so any
                # failure below is attributable to the paid room and nothing else.
                "outcome": outcome if row["talkroom_id"] == PAID_ROOM else "observed_no_action",
                "screenshot_path": shot,
                "live_dom_path": dom,
            })

        result_path = evidence / "attempt-01.result.json"
        result_path.write_text(json.dumps({
            "status": "ok",
            "current_b1": {
                "context_path": str(context_path),
                "context_sha256": gate.sha256_file(context_path),
                "inbox_url": gate.INBOX_URL,
                "inbox_status": "ok",
                "inbox_screenshot_path": inbox_shot,
                "inbox_live_dom_path": inbox_dom,
                "inspected_talkrooms": inspected,
            },
        }), encoding="utf-8")
        summary_path = evidence / "summary.json"
        summary_path.write_text(json.dumps({
            "status": "success", "task_label": "gig-B1", "result_path": str(result_path),
        }), encoding="utf-8")

        return gate.validate_result(context_path, summary_path, evidence, 0.0)

    def test_a_result_that_reports_visiting_a_paid_room_is_rejected(self):
        # The coverage contract, run the other way. Before TODO 3c a paid room in the result
        # was normal -- it was in the target list. Now reaching one at all is the violation,
        # whatever the lane claims it did there: merely opening order 91000002's room means
        # the lane went looking for work that is not its own, and the only reason it would
        # look is to act. Named, not folded into talkroom_coverage_mismatch.
        for outcome in ("observed_no_action", "blocked", "replied", "submitted"):
            with self.subTest(outcome=outcome):
                ok, errors = self._run_validate_result(
                    visited_paid_room=True, outcome=outcome
                )
                self.assertFalse(ok, errors)
                self.assertIn(f"talkroom_visit_forbidden:{PAID_ROOM}", errors)

    def test_a_result_that_stayed_out_of_the_paid_room_passes(self):
        # A gate that failed everything would pass the test above while destroying the lane.
        ok, errors = self._run_validate_result(visited_paid_room=False)

        self.assertTrue(ok, errors)
        self.assertEqual(errors, [])

    def test_a_context_written_before_this_change_is_refused_rather_than_trusted(self):
        # An old context has no forbidden_talkrooms and therefore cannot prove B1 stayed
        # out of anything. Treated as unreadable, not as "nothing was forbidden".
        stale = self.root / "stale-context.json"
        context = self._context(None)
        context.pop("forbidden_talkrooms")
        stale.write_text(json.dumps(context), encoding="utf-8")

        ok, errors = gate.validate_result(stale, self.root / "no-summary.json", self.root, 0.0)

        self.assertFalse(ok)
        self.assertEqual(errors, ["b1_context_unreadable"])


class ReplyChokepointTest(unittest.TestCase):
    """The physical refusal, at the position TODO 1 put check_style."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.database = self.root / "outbox.sqlite3"
        self.manifest = ROOT / "config" / "connectors" / "coconala.json"
        outbox_module = load("connector_outbox")
        outbox = outbox_module.ConnectorOutbox(self.database, self.manifest)
        self.action = outbox.enqueue(
            event_key=outbox_module.coconala_message_event_key(ENQUIRY_ROOM, "message-1"),
            thread_id=ENQUIRY_ROOM,
            thread_url=f"https://coconala.com/mypage/direct_message/{ENQUIRY_ROOM}",
            observed_at=100,
        )
        self.controller = load("reply_action").ReplyActionController(self.database, self.manifest)
        self.executor = load("reply_executor")

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def clock(*values):
        ticks = iter(values)
        return lambda: next(ticks)

    def _run(self, *, talkroom_id, paid_talkroom_ids, browser, url=None):
        return self.executor.execute_reply(
            controller=self.controller,
            queue_item={
                "event_key": f"coconala:message:v1:{ENQUIRY_ROOM}:message-1",
                "talkroom_id": talkroom_id,
                "talkroom_url": url or f"https://coconala.com/talkrooms/{talkroom_id}",
                "origin_at": "1970-01-01T00:01:40+00:00",
            },
            owner="worker-1",
            clock=self.clock(101, 102, 103, 106),
            compose=lambda context: "本文",
            browser=browser,
            paid_talkroom_ids=paid_talkroom_ids,
        )

    def test_a_send_into_a_paid_talkroom_is_refused_before_the_browser_is_touched(self):
        # done-condition 1. B1's own record for 90000002 says it confirmed the reply was in
        # the thread body afterwards -- by then it is in the buyer's inbox. The proof that
        # matters is therefore not "no error was raised" but "the browser was never driven":
        # events stays empty, so no fill and no click ever happened.
        browser = RecordingBrowser(self.controller, self.action["action_id"])

        with self.assertRaisesRegex(ValueError, f"paid_talkroom_write_refused:{PAID_ROOM}"):
            self._run(
                talkroom_id=PAID_ROOM,
                paid_talkroom_ids=frozenset({PAID_ROOM}),
                browser=browser,
            )

        self.assertEqual(browser.events, [])
        self.assertNotIn("fill", browser.events)
        self.assertNotIn("click", browser.events)

    def test_a_pre_purchase_direct_message_still_goes_out(self):
        # done-condition 2. Answering unbought enquiries is what this lane is FOR; a fence
        # that also silences them has not fixed the bug, it has replaced it.
        browser = RecordingBrowser(self.controller, self.action["action_id"])

        result = self._run(
            talkroom_id=ENQUIRY_ROOM,
            paid_talkroom_ids=frozenset({PAID_ROOM}),
            browser=browser,
            url=f"https://coconala.com/mypage/direct_message/{ENQUIRY_ROOM}",
        )

        self.assertEqual(result["status"], "replied")
        self.assertEqual(browser.events, ["read_before", "fill", "click", "read_after"])

    def test_undeterminable_membership_sends_nothing(self):
        # done-condition 3. None is "the registry could not be read", the fourth answer
        # blocked_evidence_verdict added. Refused exactly like a known paid room.
        browser = RecordingBrowser(self.controller, self.action["action_id"])

        with self.assertRaisesRegex(ValueError, "membership_undeterminable"):
            self._run(
                talkroom_id=ENQUIRY_ROOM,
                paid_talkroom_ids=None,
                browser=browser,
            )

        self.assertEqual(browser.events, [])

    def test_a_thread_that_cannot_be_named_is_refused(self):
        # Exercised directly rather than through execute_reply: the outbox binds every
        # claimed action to a thread id, so this state cannot be reached from that
        # direction today. The branch stays because a send whose destination cannot be
        # named cannot be checked against the fence at all, and a future caller that
        # loses the id must be refused rather than allowed through an empty string.
        with self.assertRaisesRegex(ValueError, "unidentifiable_thread"):
            self.executor.refuse_fenced_talkroom(
                queue_item={"event_key": "k"},
                action={},
                paid_talkroom_ids=frozenset(),
            )

    def test_the_refusal_helper_lets_an_unfenced_room_through(self):
        self.assertIsNone(self.executor.refuse_fenced_talkroom(
            queue_item={"talkroom_id": ENQUIRY_ROOM},
            action={"thread_id": ENQUIRY_ROOM},
            paid_talkroom_ids=frozenset({PAID_ROOM}),
        ))

    def test_the_membership_argument_has_no_default(self):
        # A caller that never considered the question must not be able to send. This is why
        # the parameter is required rather than defaulted: the one call site that forgets is
        # the one that would speak in somebody else's room.
        import inspect

        signature = inspect.signature(self.executor.execute_reply)
        parameter = signature.parameters["paid_talkroom_ids"]
        self.assertIs(parameter.default, inspect.Parameter.empty)
        self.assertIs(parameter.kind, inspect.Parameter.KEYWORD_ONLY)


class LaneRefusalIsCountedTest(unittest.TestCase):
    def test_a_fenced_room_is_reported_rather_than_silently_dropped(self):
        lane = load("reply_lane")
        source = (SCRIPTS / "reply_lane.py").read_text(encoding="utf-8")

        self.assertTrue(lane._is_paid_talkroom_refusal(ValueError("paid_talkroom_write_refused:1")))
        self.assertFalse(lane._is_paid_talkroom_refusal(ValueError("something else")))
        self.assertIn('summary["paid_talkroom_refused"]', source)
        self.assertIn("paid_talkroom_ids=fenced_ids_from_file(args.fences)", source)


class PassWiringTest(unittest.TestCase):
    """The mechanism was built and unwired for the whole life of this branch."""

    def test_gig_pass_builds_the_registry_and_hands_it_to_every_mouth(self):
        source = (ROOT / "gig_pass.sh").read_text(encoding="utf-8")

        self.assertIn('project_effect_fence.py" build-paid', source)
        self.assertIn('PROJECT_FENCE_FILE="$EVIDENCE_DIR/project-fences.json"', source)
        self.assertEqual(source.count('--fences "$PROJECT_FENCE_FILE"'), 3)
        # The comment that justified leaving the argument off must not survive the wiring.
        self.assertNotIn("PROJECT_FENCE_FILE does not exist on this branch", source)

    def test_b1_is_also_told_in_words_that_a_forbidden_room_is_not_its_to_open(self):
        # Third layer now, and still never the first: three prompt-only prohibitions on
        # 2026-08-07 moved the wording and not the behaviour. The prompt matches the data
        # B1 is actually handed -- telling it to "observe write_allowed=false rooms" after
        # those rooms stopped being supplied would be an instruction about nothing.
        source = (ROOT / "gig_pass.sh").read_text(encoding="utf-8")

        self.assertIn("forbidden_talkrooms are paid orders' rooms", source)
        self.assertIn("Do not open them, do not navigate to them", source)
        self.assertIn("may legitimately be empty", source)
        self.assertNotIn("A row with write_allowed=false is a paid order's talkroom", source)


if __name__ == "__main__":
    unittest.main()
