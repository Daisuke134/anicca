import unittest
from datetime import datetime, timezone, timedelta
from uuid import UUID
from graphiti_projection import project, to_edge


def uid(n):
    return str(UUID(int=n))


class TestProjection(unittest.TestCase):
    def setUp(self):
        now = datetime(2026,11,25,tzinfo=timezone.utc)
        self.p = dict(owner=uid(1), branch=uid(2), event_id=uid(3), goal_id=uid(4),
                      kind='goal_plan', observed_at=now, recorded_at=now,
                      intended_at=now+timedelta(days=1))

    def test_plan_not_completion(self):
        r = project(**self.p)
        self.assertEqual(r['name'], 'HAS_PLAN')
        self.assertEqual(r['valid_at'], self.p['observed_at'])
        self.assertIsNone(r['invalid_at'])
        self.assertEqual(r['attributes']['intended_at'], self.p['intended_at'].isoformat())

    def test_completion_requires_explicit_type(self):
        p = dict(self.p, kind='goal_completion', intended_at=None)
        self.assertEqual(project(**p)['name'], 'REPORTED_COMPLETION')
        with self.assertRaises(ValueError):
            project(**dict(self.p, kind='goal_completion'))

    def test_scope(self):
        r = project(**self.p)
        for key in ('owner','branch'):
            s = project(**dict(self.p, **{key:uid(99)}))
            for field in ('group_id','uuid','source_node_uuid','target_node_uuid'):
                self.assertNotEqual(r[field],s[field])

    def test_replay_ids(self):
        self.assertEqual(project(**self.p),project(**self.p))
        self.assertNotEqual(project(**self.p)['uuid'],project(**dict(self.p,event_id=uid(9)))['uuid'])

    def test_future_observation(self):
        with self.assertRaises(ValueError):
            project(**dict(self.p, observed_at=self.p['intended_at']))

    def test_naive_time(self):
        with self.assertRaises(ValueError):
            project(**dict(self.p, observed_at=self.p['observed_at'].replace(tzinfo=None)))

    def test_bad_scope(self):
        with self.assertRaises(ValueError):
            project(**dict(self.p, owner='not-a-uuid'))

    def test_official_type_if_installed(self):
        try:
            from graphiti_core.edges import EntityEdge
        except ImportError:
            self.skipTest('Graphiti not installed')
        self.assertIsInstance(to_edge(**self.p),EntityEdge)
