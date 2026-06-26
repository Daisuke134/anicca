#!/usr/bin/env bash
# VSDD oracle for B1: deploy-akash.sh acceleration. STATIC invariants (grep) + a BEHAVIORAL run against a fake
# provider-services recorder (no network, no real money). Exit 0=PASS, 1=FAIL.
# Spec: anicca/docs/superpowers/specs/2026-06-26-B1-akash-provider-services-acceleration.md
set -uo pipefail
D="/Users/operator/anicca/skills/self/spawn/scripts"
S="$D/deploy-akash.sh"
src="$(sed 's/#.*//' "$S")"   # strip comments — INV checks are about ACTIVE CODE (comments may name what we DON'T do)
fails=0
have(){   grep -qE "$1" <<<"$src" || { echo "  - FAIL missing [$1] — $2"; fails=$((fails+1)); }; }
absent(){ grep -qE "$1" <<<"$src" && { echo "  - FAIL present [$1] — $2"; fails=$((fails+1)); }; true; }
ok(){     [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

# ---------- STATIC INV-1..6 ----------
absent "console-api|credit card|managed wallet"  "INV-1 no-human: NO Console/credit-card path"
have   "AKASH_KEY_NAME"                            "INV-1 own-wallet --from key"
have   "cert"                                      "INV-2 ensure client cert"
have   "deployment create"                         "INV-2 deployment create"
have   "(market )?bid list|query market bid"       "INV-2 bid query"
have   "(market )?lease create|tx market lease"    "INV-2 lease create"
have   "send-manifest"                             "INV-2 send-manifest"
absent "sleep 30"                                  "INV-3 NO fixed 30s sleep"
have   "for [^;]*seq|while "                        "INV-3 bid poll loop"
absent "bme mint-act|usdc.*akt|swap"               "INV-5 funding OFF the per-deploy path (no mint/swap here)"
have   "exit 1"                                    "INV-6 fail-closed"

# ---------- BEHAVIORAL: fake provider-services recorder ----------
T="$(mktemp -d)"; REC="$T/rec"; : >"$REC"
cat >"$T/provider-services" <<'FAKE'
#!/usr/bin/env bash
echo "$*" >> "$B1_REC"
case "$*" in
  *"keys show"*)            echo "akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523" ;;
  *"query cert list"*)      echo '{"certificates":[{"certificate":{}}]}' ;;          # cert exists -> skip create
  *"tx deployment create"*) echo '{"dseq":"777","logs":[]}' ;;
  *"query market bid list"*)echo '{"bids":[{"bid":{"bid_id":{"gseq":1,"oseq":1,"provider":"akash1prov"}}}]}' ;;
  *"tx market lease create"*) echo '{"code":0}' ;;
  *"send-manifest"*)        echo "ok" ;;
  *version*)                echo "v0.11.1" ;;
  *)                        echo "{}" ;;
esac
FAKE
chmod +x "$T/provider-services"
OUT="$(B1_REC="$REC" PROVIDER_SERVICES="$T/provider-services" AKASH_KEY_NAME=anicca-akash \
       AKASH_NODE="http://localhost:1" AKASH_CHAIN_ID="testchain" AKASH_KEYRING_BACKEND=test \
       bash "$S" testchild 2>"$T/err")"; rc=$?
recd="$(cat "$REC")"
ok "$([ $rc -eq 0 ] && echo 1 || echo 0)" "behavioral: deploy-akash.sh exited $rc — $(tail -1 "$T/err" 2>/dev/null)"
ok "$([ "$OUT" = 777 ] && echo 1 || echo 0)" "behavioral: printed dseq='$OUT' (want 777)"
for c in "deployment create" "bid list" "lease create" "send-manifest"; do
  grep -q "$c" <<<"$recd" || { echo "  - FAIL behavioral: '$c' never called"; fails=$((fails+1)); }
done
rm -rf "$T"

[ $fails -eq 0 ] && { echo "PASS — all B1 deploy invariants hold (static + behavioral)"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
