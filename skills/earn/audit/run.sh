#!/usr/bin/env bash
# earn/audit — ONE Anicca loop slot. EARN_MODE=discover|execute. Smart-contract audit contests
# (code4rena + Cantina) pay $60-135k+ USDC pools per VALID finding. ONE bounded unit per wake:
#   discover  — fetch LIVE open contests → state/contests.json → narrate (the always-safe default).
#   execute   — pick one in-scope contest, fetch its scope/repo, the brain analyzes ONE contract for
#               a candidate finding, DRAFT it to state/findings/<id>.md. (Real SUBMIT needs a
#               code4rena/Cantina account + a genuinely valid unique vuln — flagged, never faked.)
# ANTI-SHORTCUT: only a real external on-chain USDC payout counts as earned (INV-7); discover/analyze
# earn 0. NO HUMAN for discover/analyze; submission account = the one honest gap (flag it).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EARN_MODE="${EARN_MODE:-discover}"
WAKE="${WAKE_ID:-$(date -u +%s)}"
PY=/opt/homebrew/bin/python3
FC="$(command -v firecrawl || echo /opt/homebrew/bin/firecrawl)"
STATE="$HERE/state"; mkdir -p "$STATE/findings"
emit(){ printf '{"slot":"earn/audit","did":%s,"earn_usdc":0,"cost_usdc":0}\n' \
  "$(printf '%s' "$1" | "$PY" -c 'import json,sys;print(json.dumps(sys.stdin.read()))')"; }

# ── discover: scrape live open contests (real, verifiable) ──
discover(){
  local cj="$STATE/contests.json" md="/tmp/audit-c4r-$$.md"
  "$FC" scrape "https://code4rena.com/audits" markdown > "$md" 2>/dev/null || true
  WAKE="$WAKE" "$PY" - "$cj" "$md" <<'PY' 2>/dev/null
import json,re,sys,os
cj,mdf=sys.argv[1],sys.argv[2]
md=open(mdf,encoding="utf-8").read() if os.path.exists(mdf) else ""
# FIND-001 fix: only OPEN audits. code4rena lists active audits ABOVE the "Completed audits"
# header (everything after it is the archive). Within the active region, drop entries whose
# nearby text says Completed / Judging / Report in progress (those windows are closed).
head=re.split(r'Completed audits', md, maxsplit=1)[0]
seen={}
for m in re.finditer(r'\$([0-9,]+)\s+in USDC\]\((https://code4rena\.com/audits/[^)]+)\)', head):
    ctx=head[max(0,m.start()-160):m.start()]   # the label sits just before the $amount link
    if re.search(r'Completed|Judging|Report in progress|Mitigation', ctx, re.I): continue
    seen[m.group(2)]={"platform":"code4rena","pool_usdc":int(m.group(1).replace(",","")),"url":m.group(2),"status":"open"}
ranked=sorted(seen.values(), key=lambda c:-c["pool_usdc"])
if not ranked and os.path.exists(cj):
    print(len(json.load(open(cj)).get('open_contests',[]))); sys.exit()  # FIND-002: keep prior good data on empty fetch
json.dump({"fetched_at":os.environ.get("WAKE",""),"open_contests":ranked}, open(cj,"w"), indent=2)
print(len(ranked))
PY
  rm -f "$md"
  local n; n=$([ -f "$cj" ] && "$PY" -c "import json;print(len(json.load(open('$cj')).get('open_contests',[])))" 2>/dev/null || echo 0)
  local top; top=$([ -f "$cj" ] && "$PY" -c "import json;c=json.load(open('$cj')).get('open_contests',[]);print((c[0]['url']+' \$'+str(c[0]['pool_usdc'])) if c else 'none')" 2>/dev/null || echo none)
  echo "[audit] discover wake=$WAKE open_now=$n top=$top"
  emit "discover: $n OPEN code4rena audits (top: $top). Real submission needs a code4rena account + a valid unique finding (the hard gap)."
}

# ── execute: draft a candidate finding for the top in-scope contest (no fake submit) ──
execute(){
  local cj="$STATE/contests.json"
  [ -f "$cj" ] || discover >/dev/null 2>&1
  local url; url=$("$PY" -c "import json;c=json.load(open('$cj')).get('open_contests',[]);print(c[0]['url'] if c else '')" 2>/dev/null)
  [ -n "$url" ] || { emit "no open contest to analyze"; return; }
  # the brain (this loop's claude) reads the scope/repo from $url and drafts ONE candidate finding to
  # state/findings/. This script seeds the draft target; the cron prompt does the actual analysis.
  local id; id=$(printf '%s' "$url" | sed 's#.*/##')
  echo "{\"contest\":\"$url\",\"draft_target\":\"$STATE/findings/$id.md\",\"note\":\"brain: read scope, analyze one in-scope contract, write a candidate finding here\"}" > "$STATE/findings/$id.target.json"
  emit "execute: analysis target set for $url (draft → state/findings/$id.md). Submission account = honest gap."
}

case "$EARN_MODE" in
  execute) execute ;;
  *)       discover ;;
esac
exit 0
