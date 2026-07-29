"""What happened to the application? -- the identity chain 募集id -> talkroom id -> 入金.

Why this file exists (measured 2026-07-27 on the real ledgers):

  ~/gig/applied.jsonl      224 rows, but NOT an application ledger. status breakdown:
                           applied 110, replied 71, no_action_all_current 24, missing 10,
                           plus one-off strings. requestId holds non-application tokens
                           like "b1-nurture-sweep-pass129", "dm-9954245",
                           "talkroom-17943244" alongside real 募集 ids.
  of the 110 applications  only 2 ever got a follow-up row under the same requestId.
  ~/gig/earnings.jsonl     2 rows whose requestId is a TALKROOM id (18011694) while
                           applied.jsonl's requestId is a 募集 id (5167108). The id join
                           matched nothing, so category_bandit.py fell back to joining on
                           an exact title string.

The missing piece was never the learning algorithm. It was that nothing recorded which
talkroom an application turned into, so no reward could ever be attributed. The link does
exist on disk: coconala_queue_snapshot.py already walks talkroom -> offer page and reads
the 募集 id off it (OFFER_EXPRESSION), producing
  orders[] = {"talkroom_id": "18011694", "request_id": "5167108", ...}
Nothing consumed it. These tests pin the taxonomy, the durable chain, and the stage
function that replaces the title join.

Rules these tests enforce:
  * exact match only -- an unproven link is `unlinked`, never guessed
  * the deepest stage an application reached is a property of the application, not of
    whichever row happened to be read last
  * what cannot be recovered is counted as unrecoverable, not invented
"""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


al = load(SCRIPTS / "application_ledger.py", "application_ledger")


class TaxonomyTest(unittest.TestCase):
    """"What is an application" is decided here and nowhere else."""

    def test_applied_status_is_an_application_event(self):
        kind = al.classify_event({"requestId": "5167108", "status": "applied"})
        self.assertEqual(kind, al.EVENT_APPLICATION)

    def test_reply_status_is_engagement_not_a_second_application(self):
        kind = al.classify_event({"requestId": "5167108", "status": "replied"})
        self.assertEqual(kind, al.EVENT_ENGAGEMENT)

    def test_pass_level_sweep_row_is_not_an_application(self):
        # 24 live rows look like this; counting them as applications inflates the funnel.
        kind = al.classify_event(
            {"requestId": "b1-nurture-sweep-pass129", "status": "no_action_all_current"})
        self.assertEqual(kind, al.EVENT_SWEEP)

    def test_row_without_status_is_unknown_not_applied(self):
        # 10 live rows have no status at all. Silence is not evidence of an application.
        self.assertEqual(al.classify_event({"requestId": "5176621"}), al.EVENT_UNKNOWN)


class IdentityTest(unittest.TestCase):
    def test_bare_digits_are_a_request_id(self):
        ident = al.identify("5167108")
        self.assertEqual((ident.kind, ident.value), (al.ID_REQUEST, "5167108"))

    def test_talkroom_prefixed_token_is_a_talkroom_not_a_request(self):
        ident = al.identify("talkroom-17943244")
        self.assertEqual((ident.kind, ident.value), (al.ID_TALKROOM, "17943244"))

    def test_sweep_token_names_nothing(self):
        self.assertEqual(al.identify("b1-nurture-sweep-pass129").kind, al.ID_NONE)

    def test_known_talkroom_id_is_not_mistaken_for_a_request_id(self):
        # gig_pass.sh's paid-progress writer falls back to the talkroom id in the
        # requestId field. Only the chain can tell them apart -- never digit length.
        chain = al.IdentityChain.from_links([
            al.IdentityLink(request_id="5167108", talkroom_id="18011694",
                            lane="orders", source="queue_snapshot", evidence="x.json"),
        ])
        self.assertEqual(al.identify("18011694", chain=chain).kind, al.ID_TALKROOM)
        self.assertEqual(al.identify("5167108", chain=chain).kind, al.ID_REQUEST)


class ChainExtractionTest(unittest.TestCase):
    def test_queue_snapshot_order_yields_an_exact_link(self):
        snapshot = {"orders": [
            {"talkroom_id": "18011694", "request_id": "5167108",
             "contract_id": "direct-offer:6254275"},
        ]}
        links = al.links_from_queue_snapshot(snapshot, evidence="queue-snapshot-pass508.json")
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].request_id, "5167108")
        self.assertEqual(links[0].talkroom_id, "18011694")
        self.assertEqual(links[0].lane, "orders")

    def test_order_without_a_request_id_produces_no_link(self):
        # Real row: talkroom 17943244's offer page has request_id null. Unlinkable is
        # unlinked; a direct offer has no 募集 behind it and must not be invented.
        snapshot = {"orders": [
            {"talkroom_id": "17943244", "request_id": None,
             "contract_id": "direct-offer:6198868"},
        ]}
        self.assertEqual(al.links_from_queue_snapshot(snapshot, evidence="x.json"), ())


class ChainStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "identity_chain.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def link(self, request_id="5167108", talkroom_id="18011694", evidence="a.json"):
        return al.IdentityLink(request_id=request_id, talkroom_id=talkroom_id,
                               lane="orders", source="queue_snapshot", evidence=evidence)

    def test_recorded_link_survives_a_reload(self):
        al.record_links([self.link()], path=self.path, now=1784695670)
        chain = al.IdentityChain.load(self.path)
        self.assertEqual(chain.talkroom_for("5167108"), "18011694")
        self.assertEqual(chain.request_for("18011694"), "5167108")

    def test_recording_the_same_pair_twice_appends_nothing(self):
        al.record_links([self.link()], path=self.path, now=1)
        added = al.record_links([self.link(evidence="b.json")], path=self.path, now=2)
        self.assertEqual(added, 0)
        self.assertEqual(len(self.path.read_text(encoding="utf-8").strip().splitlines()), 1)

    def test_conflicting_links_are_surfaced_not_silently_resolved(self):
        al.record_links([self.link(), self.link(request_id="5138597")],
                        path=self.path, now=1)
        chain = al.IdentityChain.load(self.path)
        self.assertIn("18011694", chain.conflicts)
        # An ambiguous talkroom resolves to nothing rather than to a coin flip.
        self.assertIsNone(chain.request_for("18011694"))

    def test_missing_chain_file_is_an_empty_chain_not_an_error(self):
        chain = al.IdentityChain.load(Path(self.tmp.name) / "nope.jsonl")
        self.assertIsNone(chain.talkroom_for("5167108"))


class StageTest(unittest.TestCase):
    """applied -> engaged -> contracted -> paid, from authoritative evidence only."""

    CHAIN = al.IdentityChain.from_links([
        al.IdentityLink(request_id="5167108", talkroom_id="18011694",
                        lane="orders", source="queue_snapshot", evidence="q.json"),
    ])

    def test_application_with_no_follow_up_is_applied(self):
        ledger = al.build([{"requestId": "5000001", "status": "applied", "ts": 1}], [],
                          chain=al.IdentityChain.from_links([]))
        self.assertEqual(ledger.applications[0].stage, al.STAGE_APPLIED)

    def test_a_later_reply_row_lifts_the_same_application_to_engaged(self):
        rows = [{"requestId": "5000001", "status": "applied", "ts": 1},
                {"requestId": "5000001", "status": "replied", "ts": 2}]
        ledger = al.build(rows, [], chain=al.IdentityChain.from_links([]))
        self.assertEqual(len(ledger.applications), 1)      # one application, not two trials
        self.assertEqual(ledger.applications[0].stage, al.STAGE_ENGAGED)

    def test_an_order_lane_link_proves_the_application_was_contracted(self):
        # The talkroom appears in the orders lane, so a deal exists -- independent of
        # whatever the agent did or did not write into applied.jsonl.
        ledger = al.build([{"requestId": "5167108", "status": "applied", "ts": 1}], [],
                          chain=self.CHAIN)
        self.assertEqual(ledger.applications[0].stage, al.STAGE_CONTRACTED)

    def test_payment_joins_through_the_chain_not_through_the_title(self):
        # THE bug this module exists for: earnings.requestId is the talkroom id.
        earnings = [{"requestId": "18011694", "talkroom_id": "18011694", "jpy": 12000,
                     "status": "検収完了", "evidence": "url", "title": "まったく別の題名"}]
        ledger = al.build([{"requestId": "5167108", "status": "applied", "ts": 1}],
                          earnings, chain=self.CHAIN)
        self.assertEqual(ledger.applications[0].stage, al.STAGE_PAID)

    def test_identical_titles_alone_never_attribute_a_payment(self):
        # Without a chain link, a title match is a guess. Guesses poison the reward.
        earnings = [{"requestId": "18011694", "jpy": 12000, "status": "検収完了",
                     "evidence": "url", "title": "ロゴ制作"}]
        ledger = al.build([{"requestId": "5000001", "status": "applied", "ts": 1,
                            "title": "ロゴ制作"}], earnings,
                          chain=al.IdentityChain.from_links([]))
        self.assertEqual(ledger.applications[0].stage, al.STAGE_APPLIED)
        self.assertEqual(ledger.unattributed_earnings, ("18011694",))

    def test_a_stage_never_goes_backwards(self):
        rows = [{"requestId": "5000001", "status": "delivered", "ts": 1},
                {"requestId": "5000001", "status": "applied", "ts": 9}]
        ledger = al.build(rows, [], chain=al.IdentityChain.from_links([]))
        self.assertEqual(ledger.applications[0].stage, al.STAGE_CONTRACTED)


class CoverageTest(unittest.TestCase):
    def test_unlinked_applications_are_counted_and_visible(self):
        chain = al.IdentityChain.from_links([
            al.IdentityLink(request_id="5167108", talkroom_id="18011694",
                            lane="orders", source="queue_snapshot", evidence="q.json"),
        ])
        rows = [{"requestId": "5167108", "status": "applied", "ts": 1},
                {"requestId": "5000001", "status": "applied", "ts": 1}]
        ledger = al.build(rows, [], chain=chain)
        self.assertEqual(ledger.linked, 1)
        self.assertEqual(ledger.unlinked, 1)

    def test_application_row_without_a_usable_id_is_unrecoverable_not_dropped(self):
        rows = [{"requestId": "N/A", "status": "applied", "ts": 1}]
        ledger = al.build(rows, [], chain=al.IdentityChain.from_links([]))
        self.assertEqual(ledger.applications, ())
        self.assertEqual(ledger.unrecoverable, 1)

    def test_sweep_rows_are_neither_applications_nor_unrecoverable(self):
        rows = [{"requestId": "b1-nurture-sweep-pass129", "status": "no_action_all_current"}]
        ledger = al.build(rows, [], chain=al.IdentityChain.from_links([]))
        self.assertEqual((ledger.applications, ledger.unrecoverable), ((), 0))
        self.assertEqual(ledger.sweep_events, 1)

    def test_engagement_for_an_application_we_never_recorded_is_visible(self):
        # 71 live rows are 'replied' with no matching 'applied' row -- the pre-history
        # the loop can no longer reconstruct. It must be counted, never back-filled.
        rows = [{"requestId": "5999999", "status": "replied", "ts": 1}]
        ledger = al.build(rows, [], chain=al.IdentityChain.from_links([]))
        self.assertEqual(ledger.orphan_engagements, 1)
        self.assertEqual(ledger.applications, ())

    def test_counts_by_stage_are_reported(self):
        rows = [{"requestId": "5000001", "status": "applied", "ts": 1},
                {"requestId": "5000002", "status": "applied", "ts": 1},
                {"requestId": "5000002", "status": "replied", "ts": 2}]
        ledger = al.build(rows, [], chain=al.IdentityChain.from_links([]))
        self.assertEqual(ledger.by_stage[al.STAGE_APPLIED], 1)
        self.assertEqual(ledger.by_stage[al.STAGE_ENGAGED], 1)


class ObservationTest(unittest.TestCase):
    """What a learner may treat as a trial -- wider than `applications`, and labelled.

    71 live rows are engagements on a 募集 whose 'applied' row was never written. We
    cannot claim those applications exist (that is `applications`, kept pure), but we
    also cannot throw away the only outcome evidence the loop has. They are exposed
    separately, flagged, so a consumer opts in knowingly instead of by accident.
    """

    def test_an_orphan_engagement_is_an_observation_but_not_an_application(self):
        rows = [{"requestId": "5999999", "status": "replied", "ts": 1, "category": "A"}]
        ledger = al.build(rows, [], chain=al.IdentityChain.from_links([]))
        self.assertEqual(ledger.applications, ())
        self.assertEqual(len(ledger.observations), 1)
        self.assertFalse(ledger.observations[0].application_recorded)
        self.assertEqual(ledger.observations[0].stage, al.STAGE_ENGAGED)

    def test_a_recorded_application_is_flagged_as_such(self):
        rows = [{"requestId": "5000001", "status": "applied", "ts": 1}]
        ledger = al.build(rows, [], chain=al.IdentityChain.from_links([]))
        self.assertTrue(ledger.observations[0].application_recorded)

    def test_an_orphan_can_still_be_proven_paid_and_must_be_visible(self):
        """The live case, both settled orders: engagement rows and payment exist, the
        'applied' row never does. Reporting only applications showed paid=0 next to two
        real payments -- the same invisibility this module was built to end."""
        chain = al.IdentityChain.from_links([
            al.IdentityLink(request_id="5167108", talkroom_id="18011694",
                            lane="orders", source="queue_snapshot", evidence="q.json"),
        ])
        rows = [{"requestId": "5167108", "status": "replied", "ts": 1, "category": "A"}]
        earnings = [{"requestId": "18011694", "talkroom_id": "18011694", "jpy": 13260,
                     "status": "検収完了"}]
        ledger = al.build(rows, earnings, chain=chain)
        self.assertEqual(ledger.observation_by_stage[al.STAGE_PAID], 1)
        self.assertEqual(ledger.by_stage[al.STAGE_PAID], 0)   # no application recorded
        # The money is explained by a 募集 we know about, so it is not unattributed.
        self.assertEqual(ledger.unattributed_earnings, ())

    def test_one_request_id_is_one_observation_however_many_rows_it_has(self):
        rows = [{"requestId": "5000001", "status": "applied", "ts": 1},
                {"requestId": "5000001", "status": "replied", "ts": 2},
                {"requestId": "5000001", "status": "delivered", "ts": 3}]
        ledger = al.build(rows, [], chain=al.IdentityChain.from_links([]))
        self.assertEqual(len(ledger.observations), 1)
        self.assertEqual(ledger.observations[0].events, 3)


class HarvestTest(unittest.TestCase):
    """Both on-disk shapes that already carry the link, harvested without a browser."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_queue_snapshot_files_are_harvested(self):
        (self.dir / "queue-snapshot-pass508.json").write_text(json.dumps(
            {"orders": [{"talkroom_id": "18011694", "request_id": "5167108"}]}),
            encoding="utf-8")
        links = al.harvest_links(self.dir)
        self.assertEqual([(l.request_id, l.talkroom_id) for l in links],
                         [("5167108", "18011694")])

    def test_offer_evidence_file_is_harvested_from_its_own_filename(self):
        # offer-<talkroom>.json is what coconala_queue_snapshot.py drops per talkroom;
        # the talkroom id is in the name and the 募集 id is in the body.
        evidence = self.dir / "evidence" / "pass499"
        evidence.mkdir(parents=True)
        (evidence / "offer-17963099.json").write_text(
            json.dumps({"request_id": "5138597", "url": "/mypage/offers/6216643"}),
            encoding="utf-8")
        links = al.harvest_links(self.dir)
        self.assertEqual([(l.request_id, l.talkroom_id) for l in links],
                         [("5138597", "17963099")])

    def test_offer_evidence_with_null_request_id_yields_nothing(self):
        evidence = self.dir / "evidence"
        evidence.mkdir()
        (evidence / "offer-17943244.json").write_text(
            json.dumps({"request_id": None, "url": "/direct_offers/edit/6198868"}),
            encoding="utf-8")
        self.assertEqual(al.harvest_links(self.dir), ())

    def test_unreadable_file_does_not_stop_the_harvest(self):
        (self.dir / "queue-snapshot-broken.json").write_text("{not json", encoding="utf-8")
        (self.dir / "queue-snapshot-ok.json").write_text(json.dumps(
            {"orders": [{"talkroom_id": "18011694", "request_id": "5167108"}]}),
            encoding="utf-8")
        self.assertEqual(len(al.harvest_links(self.dir)), 1)

    def test_harvest_is_read_only_until_recorded(self):
        (self.dir / "queue-snapshot-a.json").write_text(json.dumps(
            {"orders": [{"talkroom_id": "18011694", "request_id": "5167108"}]}),
            encoding="utf-8")
        al.harvest_links(self.dir)
        self.assertFalse((self.dir / al.CHAIN_FILENAME).exists())


class HarvestCliTest(unittest.TestCase):
    """The pass must be able to fill the chain without a browser and without asking."""

    def test_harvest_mode_records_what_it_finds_and_is_idempotent(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            root = Path(tmp.name)
            (root / "queue-snapshot-pass508.json").write_text(json.dumps(
                {"orders": [{"talkroom_id": "18011694", "request_id": "5167108"}]}),
                encoding="utf-8")
            chain_path = root / al.CHAIN_FILENAME
            self.assertEqual(al._main(["--harvest", "--state-dir", str(root)]), 0)
            self.assertEqual(al.IdentityChain.load(chain_path).talkroom_for("5167108"),
                             "18011694")
            al._main(["--harvest", "--state-dir", str(root)])
            self.assertEqual(
                len(chain_path.read_text(encoding="utf-8").strip().splitlines()), 1)
        finally:
            tmp.cleanup()


class ReadOnlyTest(unittest.TestCase):
    def test_building_a_ledger_writes_nothing(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            applied = Path(tmp.name) / "applied.jsonl"
            applied.write_text(json.dumps({"requestId": "1", "status": "applied"}) + "\n",
                               encoding="utf-8")
            before = sorted(p.name for p in Path(tmp.name).iterdir())
            al.build(al.read_jsonl(applied), [], chain=al.IdentityChain.from_links([]))
            self.assertEqual(sorted(p.name for p in Path(tmp.name).iterdir()), before)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
