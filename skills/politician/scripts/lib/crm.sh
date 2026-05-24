#!/usr/bin/env bash
# crm.sh — SQLite helpers for politician CRM.
# Uses python3 sqlite3 module (sqlite3 CLI not always present).
set -euo pipefail

CRM_DB="${CRM_DB:-$SKILL/data/crm.sqlite}"

crm_init() {
  python3 - "$CRM_DB" <<'PY'
import sqlite3, sys
db = sys.argv[1]
con = sqlite3.connect(db)
cur = con.cursor()
cur.executescript("""
CREATE TABLE IF NOT EXISTS office (
  id INTEGER PRIMARY KEY,
  member_name TEXT,
  party TEXT,
  chamber TEXT,
  district TEXT,
  committees TEXT
);
CREATE TABLE IF NOT EXISTS staffer (
  id INTEGER PRIMARY KEY,
  full_name TEXT,
  office_id INTEGER,
  title TEXT,
  {{profile.lateness.stakeholders.channel}} TEXT,
  ai_relevance_score INTEGER,
  last_contacted_at TEXT,
  response_history TEXT,
  FOREIGN KEY (office_id) REFERENCES office(id)
);
CREATE TABLE IF NOT EXISTS outreach (
  id INTEGER PRIMARY KEY,
  staffer_id INTEGER,
  channel TEXT,
  draft_id TEXT,
  sent_at TEXT,
  opened_at TEXT,
  replied_at TEXT,
  sentiment TEXT,
  FOREIGN KEY (staffer_id) REFERENCES staffer(id)
);
CREATE TABLE IF NOT EXISTS bill_draft (
  id INTEGER PRIMARY KEY,
  title TEXT,
  pillar INTEGER,
  drafted_at TEXT,
  status TEXT,
  body_path TEXT
);
""")
con.commit()
print(".schema written")
PY
}

crm_load_targets() {
  # Idempotent seed of office table from data/target_legislators.json.
  python3 - "$CRM_DB" "$SKILL/data/target_legislators.json" <<'PY'
import sqlite3, sys, json
db, src = sys.argv[1], sys.argv[2]
data = json.load(open(src))
con = sqlite3.connect(db); cur = con.cursor()
n = 0
for entry in data["targets"]:
    cur.execute("SELECT id FROM office WHERE member_name=?", (entry["name"],))
    if cur.fetchone():
        continue
    cur.execute(
        "INSERT INTO office(member_name,party,chamber,district,committees) VALUES(?,?,?,?,?)",
        (entry["name"], entry.get("party",""), entry.get("chamber",""),
         entry.get("district",""), ",".join(entry.get("committees",[]))),
    )
    n += 1
con.commit()
print(f"crm_load_targets: inserted {n} new offices ({len(data['targets'])} total in JSON)")
PY
}

crm_count() {
  local table="$1"
  python3 - "$CRM_DB" "$table" <<'PY'
import sqlite3, sys
con = sqlite3.connect(sys.argv[1])
n = con.execute(f"SELECT COUNT(*) FROM {sys.argv[2]}").fetchone()[0]
print(n)
PY
}

crm_offices_due() {
  # Offices whose primary staffer (lowest staffer.id per office) hasn't been
  # contacted in 30+ days. Returns one office per line: "id|member_name|party".
  python3 - "$CRM_DB" <<'PY'
import sqlite3, sys, datetime
con = sqlite3.connect(sys.argv[1])
cur = con.cursor()
cutoff = (datetime.datetime.utcnow() - datetime.timedelta(days=30)).isoformat()
rows = cur.execute("""
  SELECT o.id, o.member_name, o.party
  FROM office o
  LEFT JOIN staffer s ON s.office_id = o.id
  GROUP BY o.id
  HAVING MAX(COALESCE(s.last_contacted_at, '1970-01-01T00:00:00')) < ?
  ORDER BY o.id
""", (cutoff,)).fetchall()
for r in rows:
    print(f"{r[0]}|{r[1]}|{r[2]}")
PY
}
