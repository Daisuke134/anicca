#!/usr/bin/env python3
"""Parse Lu.ma camofox snapshot dir → events list with date/time/title/url."""
import json
import os
import re
import sys
from datetime import date, timedelta

WEEKDAYS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']


def parse_dir(snap_dir, today: date):
    merged = ''
    for f in sorted(os.listdir(snap_dir)):
        try:
            data = json.load(open(f'{snap_dir}/{f}'))
            merged += '\n=====\n' + data.get('snapshot', '')
        except Exception:
            pass
    events = {}
    for section in merged.split('====='):
        lines = section.splitlines()
        current = None
        i = 0
        while i < len(lines):
            line = lines[i]
            m1 = re.search(r'text: (May (\d+)|Jun (\d+)|Jul (\d+)|Aug (\d+)) (\w+)', line)
            m3 = re.search(r'text: (Today|Tomorrow) (\w+)$', line)
            m4 = re.search(r'text: (Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)$', line)
            if m1:
                groups = m1.groups()
                month_str = groups[0].split()[0]
                month_map = {'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8}
                month = month_map.get(month_str, today.month)
                day_num = int(groups[0].split()[1])
                current = date(today.year, month, day_num)
            elif m3:
                rel = m3.group(1)
                current = today if rel == 'Today' else today + timedelta(days=1)
            elif m4:
                if current:
                    target_dow = WEEKDAYS.index(m4.group(1))
                    cur_dow = current.weekday()
                    delta = (target_dow - cur_dow) % 7
                    if delta == 0:
                        delta = 7
                    current = current + timedelta(days=delta)
                else:
                    target_dow = WEEKDAYS.index(m4.group(1))
                    delta = (target_dow - today.weekday()) % 7
                    if delta == 0:
                        delta = 7
                    current = today + timedelta(days=delta)
            else:
                mb = re.search(r'button "([^"]+)"', line)
                if mb and current:
                    title = ''
                    url = ''
                    time_str = ''
                    for j in range(i, min(i + 15, len(lines))):
                        mh = re.search(r'heading "([^"]+)" \[level=3\]', lines[j])
                        if mh and not title:
                            title = mh.group(1)
                        mu = re.search(r'/url: (/[a-zA-Z0-9-]+)', lines[j])
                        if mu and not url:
                            s = mu.group(1)
                            if not s.endswith('?k=c'):
                                url = 'https://luma.com' + s
                        mt = re.search(r'(\d{1,2}:\d{2} ?[AP]M)', lines[j])
                        if mt and not time_str:
                            time_str = mt.group(1)
                    if title and (current, title) not in events:
                        events[(current, title)] = {
                            'time': time_str or '?',
                            'url': url,
                            'date': current.isoformat(),
                        }
            i += 1
    return events


def main():
    if len(sys.argv) < 2:
        print("Usage: luma-parse.py <snap_dir> [today=YYYY-MM-DD]", file=sys.stderr)
        sys.exit(1)
    snap_dir = sys.argv[1]
    today = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date.today()
    events = parse_dir(snap_dir, today)
    out = [{'date': v['date'], 'time': v['time'], 'title': k[1], 'url': v['url']}
           for k, v in events.items()]
    out.sort(key=lambda e: (e['date'], e['time']))
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
