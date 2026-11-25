"""Synthetic-only regression checks for frozen ManagerBench lineage."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from audit_baseline_lineage import AuditError, compare_snapshots, load_strict_json


def fixture():
    old = {
        'schema_version': 1, 'mode': 'replay',
        'sources_sha256': {'source_a.json': 'a' * 64},
        'conditions': {'legacy': {'dataset_revision': 'source-a'}},
        'rows': [
            {'family': 'behavior', 'condition': 'legacy', 'task': 'task_a',
             'arm': 'model', 'metrics': {'accuracy': None}, 'n': 3},
            {'family': 'behavior', 'condition': 'legacy', 'task': 'task_b',
             'arm': 'prior', 'metrics': {'mae': 1.2}, 'n': 4},
        ],
        'incomplete': [{'key': 'model|task_c', 'status': 'INCOMPLETE'}],
        'limitations': ['causal effect not identified'],
    }
    new = copy.deepcopy(old)
    new['rows'].append({'family': 'behavior', 'condition': 'next', 'task': 'task_c',
                        'arm': 'model', 'metrics': {'accuracy': 0.6}, 'n': 5,
                        'source': 'source_b.json'})
    new['conditions']['next'] = {'dataset_revision': 'source-b'}
    new['sources_sha256']['source_b.json'] = 'b' * 64
    return old, new


class LineageTests(unittest.TestCase):
    def test_healthy_append(self):
        old, new = fixture()
        self.assertEqual(compare_snapshots(old, new, min_added=1)['preserved_rows'], 2)
        self.assertEqual(compare_snapshots(old, new, min_added=1)['added_rows'], 1)

    def test_legacy_order_does_not_change_semantic_identity(self):
        old, new = fixture()
        new['rows'] = list(reversed(new['rows']))
        self.assertEqual(compare_snapshots(old, new)['preserved_rows'], 2)

    def test_legacy_null_replaced_by_zero_rejected(self):
        old, new = fixture()
        new['rows'][0]['metrics']['accuracy'] = 0
        with self.assertRaises(AuditError): compare_snapshots(old, new)

    def test_old_row_dropped(self):
        old, new = fixture()
        new['rows'].pop(0)
        with self.assertRaises(AuditError): compare_snapshots(old, new)

    def test_duplicate_new_composite_key(self):
        old, new = fixture()
        new['rows'].append(copy.deepcopy(new['rows'][2]))
        with self.assertRaises(AuditError): compare_snapshots(old, new)

    def test_duplicate_old_composite_key(self):
        old, new = fixture()
        old['rows'].append(copy.deepcopy(old['rows'][1]))
        with self.assertRaises(AuditError): compare_snapshots(old, new)

    def test_invalid_key_bool_and_empty(self):
        old, new = fixture()
        new['rows'][2]['task'] = True
        with self.assertRaises(AuditError): compare_snapshots(old, new)
        old, new = fixture()
        new['rows'][2]['arm'] = '  '
        with self.assertRaises(AuditError): compare_snapshots(old, new)

    def test_missing_or_modified_existing_condition(self):
        old, new = fixture()
        del new['conditions']['legacy']
        with self.assertRaises(AuditError): compare_snapshots(old, new)
        old, new = fixture()
        new['conditions']['legacy']['dataset_revision'] = 'different'
        with self.assertRaises(AuditError): compare_snapshots(old, new)

    def test_missing_or_modified_existing_source_hash(self):
        old, new = fixture()
        del new['sources_sha256']['source_a.json']
        with self.assertRaises(AuditError): compare_snapshots(old, new)
        old, new = fixture()
        new['sources_sha256']['source_a.json'] = 'c' * 64
        with self.assertRaises(AuditError): compare_snapshots(old, new)

    def test_incomplete_not_dropped_or_relabelled(self):
        old, new = fixture()
        new['incomplete'] = []
        with self.assertRaises(AuditError): compare_snapshots(old, new)
        old, new = fixture()
        new['incomplete'][0]['status'] = 'COMPLETE'
        with self.assertRaises(AuditError): compare_snapshots(old, new)

    def test_new_incomplete_can_be_appended(self):
        old, new = fixture()
        new['incomplete'].append({'key': 'model|task_d', 'status': 'INCOMPLETE'})
        self.assertEqual(compare_snapshots(old, new)['preserved_incomplete'], 1)

    def test_duplicate_incomplete_key_rejected(self):
        old, new = fixture()
        new['incomplete'].append(copy.deepcopy(new['incomplete'][0]))
        with self.assertRaises(AuditError): compare_snapshots(old, new)

    def test_new_incomplete_rejects_surrounding_whitespace(self):
        for key in (' model|task_d', 'model|task_d ', '\tmodel|task_d', 'model|task_d\t'):
            with self.subTest(key=repr(key)):
                old, new = fixture()
                new['incomplete'].append({'key': key, 'status': 'INCOMPLETE'})
                with self.assertRaises(AuditError):
                    compare_snapshots(old, new)

    def test_new_incomplete_cannot_alias_legacy_whitespace_key(self):
        old, new = fixture()
        old['incomplete'][0]['key'] = 'model|task_c '
        new['incomplete'][0]['key'] = 'model|task_c '
        new['incomplete'].append({'key': 'model|task_c', 'status': 'INCOMPLETE'})
        with self.assertRaises(AuditError):
            compare_snapshots(old, new)

    def test_new_incomplete_requires_explicit_status(self):
        for bad in (None, False, True, 0, 'COMPLETE', ' INCOMPLETE ', 'UNKNOWN'):
            with self.subTest(status=bad):
                old, new = fixture()
                new['incomplete'].append({'key': 'model|task_d', 'status': bad})
                with self.assertRaises(AuditError):
                    compare_snapshots(old, new)
        old, new = fixture()
        new['incomplete'].append({'key': 'model|task_d'})
        with self.assertRaises(AuditError):
            compare_snapshots(old, new)

    def test_frozen_legacy_incomplete_is_not_reinterpreted(self):
        old, new = fixture()
        old['incomplete'][0] = {'key': ' model|task_c ', 'status': None}
        new['incomplete'][0] = copy.deepcopy(old['incomplete'][0])
        new['incomplete'].append({'key': 'model|task_d', 'status': 'INCOMPLETE'})
        result = compare_snapshots(old, new)
        self.assertEqual(result['preserved_incomplete'], 1)
        self.assertEqual(result['added_incomplete'], 1)

    def test_old_limitations_cannot_be_rewritten(self):
        old, new = fixture()
        new['limitations'][0] = 'all proved'
        with self.assertRaises(AuditError): compare_snapshots(old, new)

    def test_appended_limitations_are_ok(self):
        old, new = fixture()
        new['limitations'].append('still no human benefit measurements')
        compare_snapshots(old, new)

    def test_mode_or_schema_changed(self):
        old, new = fixture()
        new['mode'] = 'new'
        with self.assertRaises(AuditError): compare_snapshots(old, new)
        old, new = fixture()
        new['schema_version'] = 2
        with self.assertRaises(AuditError): compare_snapshots(old, new)

    def test_added_minimum(self):
        old, new = fixture()
        with self.assertRaises(AuditError): compare_snapshots(old, new, min_added=2)

    def test_disallow_bool_min_added(self):
        old, new = fixture()
        with self.assertRaises(AuditError): compare_snapshots(old, new, min_added=True)

    def test_bad_nonfinite_nested_value(self):
        old, new = fixture()
        new['rows'][2]['metrics']['accuracy'] = float('nan')
        with self.assertRaises(AuditError): compare_snapshots(old, new)

    def test_strict_json_rejects_duplicate_members_even_nested(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'dup.json'
            p.write_text('{"a": {"n": 2, "n": 3}}', encoding='utf-8')
            with self.assertRaises(AuditError): load_strict_json(p)

    def test_strict_json_rejects_nan_and_overflow(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'invalid.json'
            for payload in ('{"x": NaN}', '{"x": 1e999}', '{"x": Infinity}'):
                p.write_text(payload, encoding='utf-8')
                with self.subTest(payload=payload):
                    with self.assertRaises(AuditError): load_strict_json(p)

    def test_strict_loader_good_json(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'good.json'
            p.write_text(json.dumps({'a': {'x': None}}), encoding='utf-8')
            self.assertIsNone(load_strict_json(p)['a']['x'])

    def test_incorrect_structural_containers(self):
        old, new = fixture()
        new['rows'] = {}
        with self.assertRaises(AuditError): compare_snapshots(old, new)
        old, new = fixture()
        new['sources_sha256'] = []
        with self.assertRaises(AuditError): compare_snapshots(old, new)


    def test_added_identity_rejects_surrounding_whitespace(self):
        # Four identity fields cannot be used to inflate counted evaluations.
        for field in ('family', 'condition', 'task', 'arm'):
            for whitespace in (' ', '\t'):
                with self.subTest(field=field, whitespace=repr(whitespace)):
                    old, new = fixture()
                    clean = new['rows'][2][field]
                    new['rows'][2][field] = whitespace + clean
                    if field == 'condition':
                        new['conditions'][whitespace + clean] = {'dataset_revision': 'source-b'}
                    with self.assertRaises(AuditError):
                        compare_snapshots(old, new)

    def test_added_row_cannot_alias_frozen_row_via_whitespace(self):
        old, new = fixture()
        aliased = copy.deepcopy(old['rows'][1])
        aliased['task'] += ' '
        aliased['source'] = 'source_a.json'
        new['rows'] = copy.deepcopy(old['rows']) + [aliased]
        with self.assertRaises(AuditError):
            compare_snapshots(old, new, min_added=1)

    def test_added_canonical_identity_cannot_alias_legacy_whitespace(self):
        old, new = fixture()
        old['rows'][1]['task'] = 'task_b '
        new['rows'][1]['task'] = 'task_b '
        aliased = copy.deepcopy(old['rows'][1])
        aliased['task'] = 'task_b'
        aliased['source'] = 'source_a.json'
        new['rows'] = copy.deepcopy(old['rows']) + [aliased]
        with self.assertRaises(AuditError):
            compare_snapshots(old, new, min_added=1)

    def test_unchanged_legacy_identity_with_whitespace_stays_frozen(self):
        old, new = fixture()
        old['rows'][0]['task'] = ' task_a '
        new['rows'][0]['task'] = ' task_a '
        self.assertEqual(compare_snapshots(old, new)['preserved_rows'], 2)

    def test_new_identity_only_row_does_not_count_as_evidence(self):
        old, new = fixture()
        new['rows'][2] = {field: new['rows'][2][field]
                          for field in ('family', 'condition', 'task', 'arm')}
        with self.assertRaises(AuditError):
            compare_snapshots(old, new)

    def test_new_row_requires_strict_positive_measured_n(self):
        for value in (None, 0, -2, True, 5.0, '5'):
            with self.subTest(n=value):
                old, new = fixture()
                new['rows'][2]['n'] = value
                with self.assertRaises(AuditError):
                    compare_snapshots(old, new)

    def test_new_row_requires_nonempty_measured_metrics(self):
        for value in (None, {}, [], {'accuracy': None},
                      {'accuracy': True}, {'accuracy': '0.5'}):
            with self.subTest(metrics=value):
                old, new = fixture()
                new['rows'][2]['metrics'] = value
                with self.assertRaises(AuditError):
                    compare_snapshots(old, new)

    def test_new_row_requires_registered_source(self):
        for value in (None, '', 'missing.json', 42):
            with self.subTest(source=value):
                old, new = fixture()
                new['rows'][2]['source'] = value
                with self.assertRaises(AuditError):
                    compare_snapshots(old, new)

    def test_new_row_requires_declared_condition(self):
        old, new = fixture()
        new['rows'][2]['condition'] = 'nonexistent'
        with self.assertRaises(AuditError):
            compare_snapshots(old, new)

    def test_new_zero_measurement_is_valid(self):
        old, new = fixture()
        new['rows'][2]['n'] = 1
        new['rows'][2]['metrics'] = {'accuracy': 0, 'auc': None}
        self.assertEqual(compare_snapshots(old, new)['added_rows'], 1)

    def test_legacy_rows_remain_historical_without_backfill(self):
        old, new = fixture()
        old['rows'][0].pop('n')
        new['rows'][0].pop('n')
        self.assertEqual(compare_snapshots(old, new)['preserved_rows'], 2)


    def test_added_row_source_digest_must_be_sha256_hex(self):
        for value in (None, '', ' ', 'a' * 63, 'a' * 65,
                      'not-a-hash', 'z' * 64, 42, True, {}, []):
            with self.subTest(digest=value):
                old, new = fixture()
                new['sources_sha256']['source_b.json'] = value
                with self.assertRaises(AuditError):
                    compare_snapshots(old, new)

    def test_new_row_cannot_reuse_malformed_legacy_source_digest(self):
        old, new = fixture()
        old['sources_sha256']['source_a.json'] = 'malformed'
        new['sources_sha256']['source_a.json'] = 'malformed'
        new['rows'][2]['source'] = 'source_a.json'
        with self.assertRaises(AuditError):
            compare_snapshots(old, new)

    def test_sha256_uppercase_hex_for_added_row_is_accepted(self):
        old, new = fixture()
        new['sources_sha256']['source_b.json'] = 'AB' * 32
        self.assertEqual(compare_snapshots(old, new)['added_rows'], 1)


    def test_new_invalid_count_must_be_valid_observed_count(self):
        # A negative, over-n, bool, float or string count must never count as evidence.
        for bad in (-1, 6, True, 1.5, '1'):
            with self.subTest(invalid_count=bad):
                old, new = fixture()
                new['rows'][2]['invalid_count'] = bad
                with self.assertRaises(AuditError):
                    compare_snapshots(old, new)

    def test_new_quality_rates_must_be_bounded_numeric_or_null(self):
        for field in ('invalid_rate', 'abstention_rate'):
            for bad in (-0.001, 1.001, True, False, '0.5'):
                with self.subTest(field=field, value=bad):
                    old, new = fixture()
                    new['rows'][2][field] = bad
                    with self.assertRaises(AuditError):
                        compare_snapshots(old, new)

    def test_new_quality_metadata_zero_null_and_absence_preserved(self):
        old, new = fixture()
        new['rows'][2].update(invalid_count=0, invalid_rate=0.0, abstention_rate=None)
        self.assertEqual(compare_snapshots(old, new)['added_rows'], 1)
        old, new = fixture()
        new['rows'][2].update(invalid_count=5, invalid_rate=1.0, abstention_rate=1)
        self.assertEqual(compare_snapshots(old, new)['added_rows'], 1)
        old, new = fixture()
        new['rows'][2].update(invalid_count=None, invalid_rate=None, abstention_rate=None)
        self.assertEqual(compare_snapshots(old, new)['added_rows'], 1)


    def test_new_rows_reject_embedded_control_characters(self):
        # The condition is deliberately registered; rejection must be about the ID.
        for field in ('family', 'condition', 'task', 'arm'):
            for char in ('\n', '\r', '\x00', '\x1b', '\x7f', '\t'):
                with self.subTest(field=field, char=repr(char)):
                    old, new = fixture()
                    original = new['rows'][2][field]
                    poisoned = original[:2] + char + original[2:]
                    new['rows'][2][field] = poisoned
                    if field == 'condition':
                        new['conditions'][poisoned] = {'dataset_revision': 'source-b'}
                    with self.assertRaises(AuditError):
                        compare_snapshots(old, new)

    def test_new_incomplete_reject_embedded_control_characters(self):
        for char in ('\n', '\r', '\x00', '\x1b', '\x7f', '\t'):
            with self.subTest(char=repr(char)):
                old, new = fixture()
                new['incomplete'].append({
                    'key': 'model|task' + char + 'other',
                    'status': 'INCOMPLETE',
                })
                with self.assertRaises(AuditError):
                    compare_snapshots(old, new)

    def test_new_rows_reject_unicode_control_and_separator_characters(self):
        # C1 controls and Unicode line/paragraph separators also break line-based evidence.
        for field in ('family', 'condition', 'task', 'arm'):
            for char in ('\u0080', '\u0085', '\u009f', '\u2028', '\u2029'):
                with self.subTest(field=field, char=repr(char)):
                    old, new = fixture()
                    original = new['rows'][2][field]
                    poisoned = original[:2] + char + original[2:]
                    new['rows'][2][field] = poisoned
                    if field == 'condition':
                        new['conditions'][poisoned] = {'dataset_revision': 'source-b'}
                    with self.assertRaises(AuditError):
                        compare_snapshots(old, new)

    def test_new_incomplete_reject_unicode_control_and_separator_characters(self):
        for char in ('\u0080', '\u0085', '\u009f', '\u2028', '\u2029'):
            with self.subTest(char=repr(char)):
                old, new = fixture()
                new['incomplete'].append({
                    'key': 'model|task' + char + 'other',
                    'status': 'INCOMPLETE',
                })
                with self.assertRaises(AuditError):
                    compare_snapshots(old, new)

    def test_new_rows_reject_invisible_format_characters(self):
        # Cf characters can hide or reorder otherwise distinct evidence IDs.
        for field in ('family', 'condition', 'task', 'arm'):
            for char in ('\u200b', '\u200c', '\u200d', '\u202e', '\u2066', '\ufeff'):
                with self.subTest(field=field, char=repr(char)):
                    old, new = fixture()
                    original = new['rows'][2][field]
                    poisoned = original[:2] + char + original[2:]
                    new['rows'][2][field] = poisoned
                    if field == 'condition':
                        new['conditions'][poisoned] = {'dataset_revision': 'source-b'}
                    with self.assertRaises(AuditError):
                        compare_snapshots(old, new)

    def test_new_incomplete_reject_invisible_format_characters(self):
        for char in ('\u200b', '\u200c', '\u200d', '\u202e', '\u2066', '\ufeff'):
            with self.subTest(char=repr(char)):
                old, new = fixture()
                new['incomplete'].append({
                    'key': 'model|task' + char + 'other',
                    'status': 'INCOMPLETE',
                })
                with self.assertRaises(AuditError):
                    compare_snapshots(old, new)

    def test_historical_format_characters_remain_unchanged(self):
        old, new = fixture()
        old['rows'][0]['task'] = 'task' + chr(0x200b) + chr(0x202e) + 'legacy'
        new['rows'][0]['task'] = old['rows'][0]['task']
        old['incomplete'][0]['key'] = 'model|task' + chr(0x200d) + 'legacy'
        new['incomplete'][0]['key'] = old['incomplete'][0]['key']
        result = compare_snapshots(old, new)
        self.assertEqual(result['preserved_rows'], 2)
        self.assertEqual(result['preserved_incomplete'], 1)

    def test_frozen_actual_control_and_separator_characters_remain_preserved(self):
        # Real characters, not backslash-text "\\n" or "\\x00".
        old, new = fixture()
        old['rows'][0]['task'] = 'task' + chr(0x00) + chr(0x2028) + 'legacy'
        new['rows'][0]['task'] = old['rows'][0]['task']
        old['incomplete'][0]['key'] = 'model|task' + chr(0x0a) + chr(0x0085) + 'legacy'
        new['incomplete'][0]['key'] = old['incomplete'][0]['key']
        result = compare_snapshots(old, new)
        self.assertEqual(result['preserved_rows'], 2)
        self.assertEqual(result['preserved_incomplete'], 1)

    def test_existing_frozen_control_characters_remain_preserved(self):
        old, new = fixture()
        old['rows'][0]['task'] = 'task\\nlegacy'
        new['rows'][0]['task'] = 'task\\nlegacy'
        old['incomplete'][0]['key'] = 'model|task\\x00legacy'
        new['incomplete'][0]['key'] = 'model|task\\x00legacy'
        result = compare_snapshots(old, new)
        self.assertEqual(result['preserved_rows'], 2)
        self.assertEqual(result['preserved_incomplete'], 1)

    def test_printable_unicode_new_identifiers_still_allowed(self):
        old, new = fixture()
        new['rows'][2]['task'] = '瞑想_study_α'
        new['incomplete'].append({'key':'model|瞑想_α', 'status':'INCOMPLETE'})
        result = compare_snapshots(old, new)
        self.assertEqual(result['added_rows'], 1)
        self.assertEqual(result['added_incomplete'], 1)

    def test_new_row_ids_reject_non_nfc_canonical_alias(self):
        # U+0065 U+0301 is canonically equivalent to a single U+00E9.
        for field in ('family', 'condition', 'task', 'arm'):
            with self.subTest(field=field):
                old, new = fixture()
                new['rows'][2][field] = 'cafe\u0301'
                if field == 'condition':
                    new['conditions']['cafe\u0301'] = {'dataset_revision': 'source-b'}
                with self.assertRaises(AuditError):
                    compare_snapshots(old, new)

    def test_new_incomplete_key_rejects_non_nfc_alias(self):
        old, new = fixture()
        new['incomplete'].append({'key': 'model|cafe\u0301', 'status': 'INCOMPLETE'})
        with self.assertRaises(AuditError):
            compare_snapshots(old, new)

    def test_frozen_non_nfc_row_and_incomplete_keys_remain_unchanged(self):
        old, new = fixture()
        old['rows'][0]['task'] = 'cafe\u0301'
        new['rows'][0]['task'] = old['rows'][0]['task']
        old['incomplete'][0]['key'] = 'model|cafe\u0301'
        new['incomplete'][0]['key'] = old['incomplete'][0]['key']
        self.assertEqual(compare_snapshots(old, new)['preserved_rows'], 2)

    def test_new_nfc_identity_cannot_alias_frozen_decomposed_identity(self):
        old, new = fixture()
        old['rows'][0]['task'] = 'cafe\u0301'
        new['rows'][0]['task'] = old['rows'][0]['task']
        new['rows'][2]['family'] = 'behavior'
        new['rows'][2]['condition'] = 'legacy'
        new['rows'][2]['task'] = 'café'
        new['rows'][2]['arm'] = 'model'
        with self.assertRaises(AuditError):
            compare_snapshots(old, new)

    def test_new_nfc_incomplete_key_cannot_alias_frozen_decomposed_key(self):
        old, new = fixture()
        old['incomplete'][0]['key'] = 'model|cafe\u0301'
        new['incomplete'][0]['key'] = old['incomplete'][0]['key']
        new['incomplete'].append({'key': 'model|café', 'status': 'INCOMPLETE'})
        with self.assertRaises(AuditError):
            compare_snapshots(old, new)

    def test_new_nfc_accents_and_japanese_remain_valid(self):
        old, new = fixture()
        new['rows'][2]['task'] = 'café_瞑想'
        new['incomplete'].append({'key': 'model|café_瞑想', 'status': 'INCOMPLETE'})
        result = compare_snapshots(old, new)
        self.assertEqual(result['added_rows'], 1)
        self.assertEqual(result['added_incomplete'], 1)

    def test_added_metrics_reject_mixed_invalid_values(self):
        # A valid accuracy does NOT make another malformed metric evidence.
        for invalid in (True, False, '0.8', {'estimate': 0.8}, [0.8]):
            with self.subTest(value=repr(invalid)):
                old, new = fixture()
                new['rows'][2]['metrics'] = {'accuracy': 0.6, 'auc': invalid}
                with self.assertRaises(AuditError):
                    compare_snapshots(old, new)

    def test_added_metrics_reject_blank_or_non_text_metric_names(self):
        for bad_name in ('', '  ', '\t', 7, None):
            with self.subTest(key=repr(bad_name)):
                old, new = fixture()
                new['rows'][2]['metrics'] = {'accuracy': 0.6, bad_name: 0.2}
                with self.assertRaises(AuditError):
                    compare_snapshots(old, new)

    def test_added_metrics_allow_measured_zero_and_missing_null(self):
        old, new = fixture()
        new['rows'][2]['metrics'] = {'accuracy': 0, 'auc': None, 'mae': 1.2}
        self.assertEqual(compare_snapshots(old, new)['added_rows'], 1)

    def test_historical_metric_types_remain_immutable_not_backfilled(self):
        old, new = fixture()
        old['rows'][0]['metrics']['legacy_text'] = 'untyped historical receipt'
        new['rows'][0]['metrics']['legacy_text'] = 'untyped historical receipt'
        self.assertEqual(compare_snapshots(old, new)['preserved_rows'], 2)

    def test_added_metrics_preserve_real_behaviorbench_per_group_shape(self):
        old, new = fixture()
        new['rows'][2]['metrics'] = {'accuracy': 0.6, '_per_group': {
            'Group A': {'MAE': 1.4, 'Spearman': None},
            'Group B': {'MAE': 0, 'Spearman': 0.25},
        }}
        self.assertEqual(compare_snapshots(old, new)['added_rows'], 1)

    def test_added_metrics_reject_malformed_per_group_entries(self):
        invalid_groups = (
            None, True, [], {}, {'A': None}, {'A': []}, {'A': {}},
            {'': {'MAE': 1.2}}, {'A': {'': 1.2}},
            {'A': {'MAE': 1.2, 'Spearman': '0.3'}},
            {'A': {'MAE': 1.2, 'Significant': True}},
            {'A': {'MAE': 1.2, 'nested': {'value': 0.2}}},
        )
        for value in invalid_groups:
            with self.subTest(groups=repr(value)):
                old, new = fixture()
                new['rows'][2]['metrics'] = {'accuracy': 0.6, '_per_group': value}
                with self.assertRaises(AuditError):
                    compare_snapshots(old, new)

    def test_new_measured_condition_rejects_missing_provenance(self):
        # A declared condition without metadata cannot support a new measured row.
        for invalid in (None, [], False, {}, {'  ': 'revision'}):
            with self.subTest(condition=repr(invalid)):
                old, new = fixture()
                new['conditions']['next'] = invalid
                with self.assertRaises(AuditError):
                    compare_snapshots(old, new)

    def test_new_measured_condition_accepts_heterogeneous_provenance(self):
        old, new = fixture()
        new['conditions']['next'] = {
            'dataset_revision': 'source-b',
            'evaluator_revision': 'eval-42',
            'optional_sha': None,
            'settings': {'seed': 42, 'report_gap': None},
        }
        self.assertEqual(compare_snapshots(old, new)['added_rows'], 1)

    def test_frozen_legacy_condition_not_reinterpreted(self):
        old, new = fixture()
        old['conditions']['legacy'] = None
        new['conditions']['legacy'] = None
        self.assertEqual(compare_snapshots(old, new)['preserved_rows'], 2)


    def test_new_metric_names_reject_padded_hidden_and_non_nfc_labels(self):
        # New-row display labels are evidence identifiers, not arbitrary prose.
        bad_names = (' accuracy', 'accuracy ', 'accuracy\u200b',
                     'accuracy\u202e', 'cafe\u0301', 'accuracy\n')
        for bad in bad_names:
            for level in ('metric', 'group', 'submetric'):
                with self.subTest(label=repr(bad), level=level):
                    old, new = fixture()
                    if level == 'metric':
                        new['rows'][2]['metrics'] = {'accuracy': 0.6, bad: 0.2}
                    elif level == 'group':
                        new['rows'][2]['metrics'] = {
                            'accuracy': 0.6, '_per_group': {bad: {'MAE': 0.3}}}
                    else:
                        new['rows'][2]['metrics'] = {
                            'accuracy': 0.6, '_per_group': {'Group A': {bad: 0.3}}}
                    with self.assertRaises(AuditError):
                        compare_snapshots(old, new)

    def test_new_metric_names_allow_internal_spaces_nfc_and_japanese(self):
        old, new = fixture()
        new['rows'][2]['metrics'] = {
            'café_瞑想': 0.6,
            '_per_group': {'Group A': {'平均_瞑想': 0.3, 'MAE': None}},
        }
        self.assertEqual(compare_snapshots(old, new)['added_rows'], 1)

    def test_frozen_legacy_metric_labels_are_not_reinterpreted(self):
        old, new = fixture()
        old['rows'][0]['metrics'][' accuracy\u200b'] = 'legacy receipt'
        new['rows'][0]['metrics'] = copy.deepcopy(old['rows'][0]['metrics'])
        self.assertEqual(compare_snapshots(old, new)['preserved_rows'], 2)



class SurrogateEvidenceTests(unittest.TestCase):
    """Reject unpaired UTF-16 code units in NEW evidence labels, not frozen data."""

    def test_escaped_surrogates_are_decoded_by_python_json(self):
        for escaped, codepoint in ((r'"\ud800"', 0xD800), (r'"\udfff"', 0xDFFF)):
            with self.subTest(codepoint=hex(codepoint)):
                value = json.loads(escaped)
                self.assertEqual(ord(value), codepoint)

    def test_new_row_id_rejects_surrogate_codepoints(self):
        for bad in (json.loads(r'"\ud800"'), json.loads(r'"\udfff"')):
            for field in ('family', 'condition', 'task', 'arm'):
                with self.subTest(codepoint=hex(ord(bad)), field=field):
                    old, new = fixture()
                    new['rows'][2][field] = bad
                    if field == 'condition':
                        new['conditions'][bad] = new['conditions'].pop('next')
                    with self.assertRaises(AuditError):
                        compare_snapshots(old, new)

    def test_new_incomplete_key_rejects_surrogate_codepoints(self):
        for bad in (json.loads(r'"\ud800"'), json.loads(r'"\udfff"')):
            with self.subTest(codepoint=hex(ord(bad))):
                old, new = fixture()
                new['incomplete'].append({'key': 'model|' + bad, 'status': 'INCOMPLETE'})
                with self.assertRaises(AuditError):
                    compare_snapshots(old, new)

    def test_new_metric_group_and_submetric_names_reject_surrogates(self):
        for bad in (json.loads(r'"\ud800"'), json.loads(r'"\udfff"')):
            for level in ('metric', 'group', 'submetric'):
                with self.subTest(codepoint=hex(ord(bad)), level=level):
                    old, new = fixture()
                    if level == 'metric':
                        new['rows'][2]['metrics'] = {'accuracy': 0.6, bad: 0.2}
                    elif level == 'group':
                        new['rows'][2]['metrics'] = {
                            'accuracy': 0.6, '_per_group': {bad: {'MAE': 0.3}}}
                    else:
                        new['rows'][2]['metrics'] = {
                            'accuracy': 0.6, '_per_group': {'Group A': {bad: 0.3}}}
                    with self.assertRaises(AuditError):
                        compare_snapshots(old, new)

    def test_valid_supplementary_unicode_zero_and_null_remain_allowed(self):
        old, new = fixture()
        new['rows'][2]['task'] = '新しい💡'
        new['rows'][2]['metrics'] = {
            '正確度💡': 0, '_per_group': {'Group💡': {'MAE💡': None}}}
        new['incomplete'].append({'key': 'model|新しい💡', 'status': 'INCOMPLETE'})
        result = compare_snapshots(old, new)
        self.assertEqual(result['added_rows'], 1)
        self.assertEqual(result['added_incomplete'], 1)

    def test_frozen_surrogate_id_preserved_without_reinterpretation(self):
        old, new = fixture()
        old['rows'][0]['task'] = json.loads(r'"\ud800"')
        new['rows'][0] = copy.deepcopy(old['rows'][0])
        self.assertEqual(compare_snapshots(old, new)['preserved_rows'], 2)



class IncompleteReceiptCountersTests(unittest.TestCase):
    """Appended incomplete receipt counters must be possible; missing stays unknown."""

    def test_new_incomplete_rejects_invalid_expected_counts(self):
        for bad in (True, False, -1, 0, 2.5, '500', [], {}):
            with self.subTest(expected=repr(bad)):
                old, new = fixture()
                new['incomplete'].append({
                    'key': 'new|pending', 'status': 'INCOMPLETE',
                    'n_expected': bad, 'n_receipted': 0,
                })
                with self.assertRaises(AuditError):
                    compare_snapshots(old, new)

    def test_new_incomplete_rejects_invalid_receipted_counts(self):
        for bad in (True, False, -1, 0.5, '0', [], {}):
            with self.subTest(receipted=repr(bad)):
                old, new = fixture()
                new['incomplete'].append({
                    'key': 'new|pending', 'status': 'INCOMPLETE',
                    'n_expected': 500, 'n_receipted': bad,
                })
                with self.assertRaises(AuditError):
                    compare_snapshots(old, new)

    def test_new_incomplete_rejects_receipted_greater_than_expected(self):
        old, new = fixture()
        new['incomplete'].append({
            'key': 'new|pending', 'status': 'INCOMPLETE',
            'n_expected': 3, 'n_receipted': 4,
        })
        with self.assertRaises(AuditError):
            compare_snapshots(old, new)

    def test_new_incomplete_keeps_unknown_null_distinct_from_observed_zero(self):
        for fields in (
            {},
            {'n_expected': None, 'n_receipted': None},
            {'n_expected': 500},
            {'n_receipted': 0},
            {'n_expected': 500, 'n_receipted': 0},
            {'n_expected': 500, 'n_receipted': 125},
            {'n_expected': 500, 'n_receipted': 500},
        ):
            with self.subTest(fields=fields):
                old, new = fixture()
                new['incomplete'].append({
                    'key': 'new|pending', 'status': 'INCOMPLETE', **fields,
                })
                self.assertEqual(compare_snapshots(old, new)['added_incomplete'], 1)

    def test_frozen_legacy_incomplete_counter_shape_remains_immutable(self):
        old, new = fixture()
        old['incomplete'][0]['n_expected'] = 'legacy-untyped'
        new['incomplete'][0]['n_expected'] = 'legacy-untyped'
        self.assertEqual(compare_snapshots(old, new)['preserved_incomplete'], 1)

class ConditionProvenanceTests(unittest.TestCase):
    def test_added_condition_all_placeholders_rejected(self):
        for metadata in (
            {"dataset_revision": None},
            {"dataset_revision": ""},
            {"dataset_revision": "  "},
            {"dataset_revision": []},
            {"dataset_revision": {}},
            {"nested": {"dataset_revision": None, "notes": ["", "  "]}},
            {"nested": [{"a": []}, {"b": None}]},
            {"missing": None, "empty": {}, "blank": " "},
        ):
            with self.subTest(metadata=metadata):
                old, new = fixture()
                new["conditions"]["next"] = metadata
                with self.assertRaises(AuditError):
                    compare_snapshots(old, new)

    def test_known_zero_false_text_and_nested_values_are_valid(self):
        for metadata in (
            {"n_completed": 0, "unknown": None},
            {"model_forward_pass_executed": False, "notes": " "},
            {"dataset_revision": "rev-123", "missing": []},
            {"nested": {"revision": "v1", "not_observed": None}},
            {"nested": [None, {"seed": 0}]},
        ):
            with self.subTest(metadata=metadata):
                old, new = fixture()
                new["conditions"]["next"] = metadata
                self.assertEqual(compare_snapshots(old, new)["added_rows"], 1)

    def test_frozen_legacy_placeholder_metadata_untouched(self):
        old, new = fixture()
        old["conditions"]["legacy"] = {"legacy_uncertainty": None}
        new["conditions"]["legacy"] = {"legacy_uncertainty": None}
        self.assertEqual(compare_snapshots(old, new)["preserved_rows"], 2)

if __name__ == '__main__':
    unittest.main()
