#!/usr/bin/env python3
"""Literal evidence audit for original improv tasks; never a humor or voice judge.

This extra probe separates a response that merely names a known character from
one that also acknowledges Dais's unexpected cue and uses an explicit action
word. These are substring proxies, not semantic, causal or laughter scores.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import sys


def read_jsonl(path: Path) -> list[dict]:
    data = []
    for line_number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f'{path}:{line_number} must contain a JSON object')
            data.append(value)
    return data


def _terms(task: dict, field: str) -> list[str]:
    terms = task.get(field)
    if (not isinstance(terms, list) or not terms
            or any(not isinstance(term, str) or not term.strip() for term in terms)):
        raise ValueError(f'{task.get("id")}: {field} must be a nonempty list of nonempty strings')
    return terms


def audit(tasks: list[dict], responses: list[dict], *, candidates_per_task: int = 2) -> dict:
    if type(candidates_per_task) is not int or candidates_per_task < 1:
        raise ValueError('candidates_per_task must be a positive integer')
    if not tasks:
        raise ValueError('at least one task is required')
    task_index = {}
    for task in tasks:
        task_id = task.get('id')
        if not isinstance(task_id, str) or not task_id.strip() or task_id in task_index:
            raise ValueError('task IDs must be unique nonempty strings')
        if task.get('category') == 'phone_ai_stage':
            _terms(task, 'cue_ack_any_of')
            _terms(task, 'any_of')
            _terms(task, 'action_any_of')
        max_chars = task.get('max_chars')
        if type(max_chars) is not int or max_chars < 1:
            raise ValueError(f'{task_id}: max_chars must be positive integer')
        task_index[task_id] = task
    seen = set()
    counts = Counter()
    items = []
    for row in responses:
        task_id, candidate = row.get('task_id'), row.get('candidate')
        if task_id not in task_index:
            raise ValueError(f'unknown task {task_id!r}')
        if not isinstance(candidate, str) or not candidate.strip():
            raise ValueError('candidate ID required')
        key = (task_id, candidate)
        if key in seen:
            raise ValueError(f'duplicate task/candidate {key!r}')
        seen.add(key)
        text = row.get('response')
        if not isinstance(text, str):
            raise ValueError('response must be a string')
        task = task_index[task_id]
        reasons = []
        checks = {'nonempty': bool(text.strip()), 'within_char_budget': len(text) <= task['max_chars']}
        if not checks['nonempty']:
            reasons.append('EMPTY_RESPONSE')
        if not checks['within_char_budget']:
            reasons.append('EXCEEDS_CHAR_BUDGET')
        if task.get('category') == 'phone_ai_stage':
            # A mere world-name mention is NOT proof of an improv callback.
            for field, check_name, fail in (
                ('any_of', 'known_world_anchor', 'NO_KNOWN_WORLD_ANCHOR'),
                ('cue_ack_any_of', 'cue_acknowledgement_proxy', 'NO_EXPLICIT_CUE_ACKNOWLEDGEMENT'),
                ('action_any_of', 'action_verb_proxy', 'NO_EXPLICIT_ACTION_MARKER'),
            ):
                checks[check_name] = any(term in text for term in _terms(task, field))
                if not checks[check_name]:
                    reasons.append(fail)
            forbidden = task.get('forbidden', [])
            if not isinstance(forbidden, list) or any(not isinstance(v, str) for v in forbidden):
                raise ValueError(f'{task_id}: forbidden must be a list of strings')
            checks['no_forbidden_literal'] = not any(term and term in text for term in forbidden)
            if not checks['no_forbidden_literal']:
                reasons.append('FORBIDDEN_LITERAL')
            checks['no_new_questions'] = not ('?' in text or '？' in text)
            if not checks['no_new_questions']:
                reasons.append('NEW_QUESTION_AFTER_OPENING')
        counts[task_id] += 1
        items.append({'task_id': task_id, 'candidate': candidate,
                      'category': task.get('category'),
                      'gate': 'PASS' if not reasons else 'FAIL',
                      'reasons': reasons, 'literal_checks': checks})
    missing = {task_id: candidates_per_task-counts[task_id]
               for task_id in task_index if counts[task_id] != candidates_per_task}
    passed = sum(r['gate'] == 'PASS' for r in items)
    return {'schema_version': '1.0', 'gate': 'PASS' if passed == len(items) and not missing and bool(items) else 'FAIL',
            'task_count': len(tasks), 'response_count': len(items), 'passed': passed,
            'failed': len(items)-passed, 'candidate_count_mismatches': missing,
            'items': items, 'method': 'literal_substring_and_format_proxies_only',
            'causal_callback_quality': 'NOT_MEASURED', 'funniness': 'NOT_MEASURED',
            'actual_voice': 'NOT_MEASURED', 'audience_laughter': 'NOT_MEASURED',
            'warning': 'Passing lexical anchors/cue/action proxies does not establish coherence, consequence, humor, turn timing, or a real voice take.'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tasks', type=Path, required=True)
    parser.add_argument('--responses', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--strict', action='store_true')
    args = parser.parse_args()
    try:
        result = audit(read_jsonl(args.tasks), read_jsonl(args.responses))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    except (ValueError, OSError, json.JSONDecodeError) as e:
        print(f'ERROR: {e}', file=sys.stderr)
        return 2
    print(f"{result['gate']}: {result['passed']}/{result['response_count']} literal/format checks; candidate_count_mismatches={len(result['candidate_count_mismatches'])}")
    return int(args.strict and result['gate'] != 'PASS')


if __name__ == '__main__':
    raise SystemExit(main())
