#!/usr/bin/env bash
# test-loop.sh — reddit-loop measurement contract (FIND-018). Seams: RD_TEST/RD_ACCOUNTS/RD_DIR/RD_REQ.
set -uo pipefail; P=0; F=0; H="$(cd "$(dirname "${BASH_SOURCE[0]}")"&&pwd)"; LOOP="$H/loop.sh"
mkacct(){ local d; d="$(mktemp -d)"; printf '[{"username":"u","email":"e","password":"p","created":"2026-07-01","comment_karma":3}]' > "$d/acct.json"; echo "$d"; }
run(){ local dir="$1" acct="$2"; RD_TEST=1 RD_ACCOUNTS="$acct" RD_DIR="$dir" RD_REQ="$dir/req.json" bash "$LOOP" 2>&1; }
st(){ grep -E "^$2:" "$1/state/STATE.md" 2>/dev/null | tail -1; }
a(){ echo "$2"|grep -qE "$3"&&{ echo "  ok $1"; P=$((P+1)); }||{ echo "  FAIL $1 /$3/"; F=$((F+1)); }; }

# 1 no account → HEAL self-provision (honest, no CapSolver)
D="$(mktemp -d)"; O="$(run "$D" /nonexistent)"
a "no-acct → HEAL NO-REDDIT-ACCOUNT" "$O" 'NO-REDDIT-ACCOUNT'
echo "$O" | grep -qiE 'capsolver|tier-a-bypass' && { echo "  FAIL honest: CapSolver leaked (FIND-012)"; F=$((F+1)); } || { echo "  ok honest: no covert-bypass wording (FIND-012)"; P=$((P+1)); }

# 2 account present, no posts → ACT-FIRST-POST, no HEAL
AD="$(mkacct)"; D="$(mktemp -d)"; O="$(run "$D" "$AD/acct.json")"
a "acct+no-posts → ACT-FIRST-POST" "$(st "$D" status)" 'ACT-FIRST-POST'
a "acct present → no HEAL" "$(st "$D" heal_first)" 'account present'
a "posts_made single 0 (no STATE corruption / FIND-010)" "$(grep -c '^posts_made:' "$D/state/STATE.md")" '^1$'

# 3 posts fresh → ACT (not first-post)
D="$(mktemp -d)"; mkdir -p "$D/state"; printf '{"url":"https://reddit.com/x","sub":"SideProject","ts":"now"}\n' > "$D/state/posts.jsonl"; O="$(run "$D" "$AD/acct.json")"
a "posts fresh → ACT" "$(st "$D" status)" '^status: ACT '
a "posts_freshness fresh" "$(st "$D" posts_freshness)" 'fresh'

# 4 posts stale (>48h) → STALE
D="$(mktemp -d)"; mkdir -p "$D/state"; printf '{"url":"https://reddit.com/y"}\n' > "$D/state/posts.jsonl"; touch -t 202607010000 "$D/state/posts.jsonl"; O="$(run "$D" "$AD/acct.json")"
a "posts stale → REDDIT-POSTS-STALE" "$(st "$D" posts_freshness)" 'REDDIT-POSTS-STALE'
a "posts stale → status STALE" "$(st "$D" status)" '^status: STALE'

# 5 record timestamp wins over a freshly touched ledger file (the production false-green bug).
D="$(mktemp -d)"; mkdir -p "$D/state"; printf '{"url":"https://reddit.com/z","ts":"2026-07-01T00:00:00Z"}\n' > "$D/state/posts.jsonl"; O="$(run "$D" "$AD/acct.json")"
a "old record + fresh mtime → REDDIT-POSTS-STALE" "$(st "$D" posts_freshness)" 'REDDIT-POSTS-STALE'
a "old record + fresh mtime → status STALE" "$(st "$D" status)" '^status: STALE'

echo "=== reddit-loop: $P passed $F failed ==="; [ "$F" = 0 ]&&echo GREEN||exit 1
