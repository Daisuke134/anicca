#!/usr/bin/env bash
LIFE_MANAGER_REPO="${LIFE_MANAGER_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$LIFE_MANAGER_REPO" ] || { echo "LIFE_MANAGER_REPO could not be resolved" >&2; exit 2; }
export LIFE_MANAGER_REPO
# Static VSDD oracle for the founder persistent-host scripts/plists. Fences the entity-separation + auto-restart
# invariants (founder wallet/port, founder-OWN url file, atomic persist, KeepAlive). Live reachability/auto-restart
# is verified separately by installing the launchd services and curling the persisted URL.
set -uo pipefail
HD="$LIFE_MANAGER_REPO/skills/self/founder-loop/host"
fails=0; ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

s="$(cat "$HD/founder-serve.sh")"
ok "$(grep -q '0x810f6d61f7606deee2657d3083e150a222bc29c5' <<<"$s" && echo 1 || echo 0)" "serve uses the FOUNDER wallet 0x810f"
ok "$(grep -q 'X402_PORT="8410"' <<<"$s" && echo 1 || echo 0)" "serve on founder port 8410 (distinct from the :8403 endpoint)"
ok "$(grep -qiE '0xa3CDd4|automaton/wallet' <<<"$(sed 's|#.*||' <<<"$s")" && echo 0 || echo 1)" "serve does NOT use the automaton wallet/path (code, not the explanatory comment)"
ok "$(grep -q 'exec ' <<<"$s" && echo 1 || echo 0)" "exec node so launchd KeepAlive supervises the server directly"

t="$(cat "$HD/founder-tunnel.sh")"
ok "$(grep -qF '$HOME/.anicca-founder/state/seller-url.txt' <<<"$t" && echo 1 || echo 0)" "tunnel persists the URL to the FOUNDER state file"
ok "$(grep -q 'openclaw/state/anicca_x402_url' <<<"$t" && echo 0 || echo 1)" "tunnel does NOT write the shared/automaton URL file"
ok "$(grep -q 'mv ' <<<"$t" && echo 1 || echo 0)" "tunnel persists the URL atomically (mv)"
ok "$(grep -q 'wait ' <<<"$t" && echo 1 || echo 0)" "tunnel waits on cloudflared (its death → KeepAlive respawn)"

for pl in serve tunnel; do
  p="$(cat "$HD/ai.anicca.founder-x402-$pl.plist")"
  ok "$(grep -q 'KeepAlive</key><true/>' <<<"$p" && echo 1 || echo 0)" "$pl plist KeepAlive=true (auto-restart)"
  ok "$(grep -q 'RunAtLoad</key><true/>' <<<"$p" && echo 1 || echo 0)" "$pl plist RunAtLoad=true"
done

[ $fails -eq 0 ] && { echo "PASS — founder persistent-host static invariants (founder wallet 0x810f / port 8410 / founder-own url file / atomic / KeepAlive)"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
