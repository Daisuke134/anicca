#!/usr/bin/env python3
"""Find next eligible task from tasks.json.

Eligible = status pending + all dependencies done + dueTs <= now.
Sort by priority (critical>high>medium>low) then dueTs asc.
"""
import json, sys, datetime, pathlib

TASKS_FILE = pathlib.Path('/Users/anicca/.openclaw/workspace/tasks.json')
PRIORITY_RANK = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}

def main():
    if not TASKS_FILE.exists():
        print(json.dumps({'eligible': []}))
        return

    d = json.loads(TASKS_FILE.read_text())
    tasks = d.get('master', {}).get('tasks', [])
    now = datetime.datetime.now(datetime.timezone.utc)

    # Build status map
    by_id = {t['id']: t for t in tasks}

    eligible = []
    for t in tasks:
        if t.get('status') != 'pending':
            continue
        # Check dependencies
        deps = t.get('dependencies', [])
        if not all(by_id.get(d, {}).get('status') == 'done' for d in deps):
            continue
        # Check dueTs
        # eligibility uses nextAttemptAt (when can we attempt) if present, else dueTs as soft deadline
        due_ts_str = t.get('metadata', {}).get('nextAttemptAt') or t.get('metadata', {}).get('dueTs')
        if due_ts_str:
            try:
                due_ts = datetime.datetime.fromisoformat(due_ts_str.replace('Z', '+00:00'))
                if due_ts > now:
                    continue  # not yet due
            except Exception:
                pass
        eligible.append(t)

    # Sort
    eligible.sort(key=lambda x: (
        PRIORITY_RANK.get(x.get('priority', 'medium'), 2),
        x.get('metadata', {}).get('dueTs', '9999')
    ))

    # --no-external filter: skip Dais-only tasks (executor can't act on them)
    if '--no-external' in sys.argv:
        eligible = [t for t in eligible if not t.get('metadata', {}).get('external_action_only')]

    if '--first' in sys.argv:
        print(json.dumps(eligible[0] if eligible else None, ensure_ascii=False))
    else:
        print(json.dumps({'eligible_count': len(eligible), 'tasks': [{'id': t['id'], 'priority': t.get('priority'), 'dueTs': t.get('metadata', {}).get('dueTs')} for t in eligible]}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
