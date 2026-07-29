#!/usr/bin/env bash
LIFE_MANAGER_REPO="${LIFE_MANAGER_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$LIFE_MANAGER_REPO" ] || { echo "LIFE_MANAGER_REPO could not be resolved" >&2; exit 2; }
export LIFE_MANAGER_REPO
# VSDD oracle for B1 deploy-akash.sh. STATIC invariants (grep, comments stripped) + BEHAVIORAL runs against a
# FAITHFUL fake provider-services that emits REAL Cosmos-SDK shapes (dseq as an event attribute, bids with
# state/price, lease state=active) so a real parse bug is CAUGHT — plus fail-closed cases. Exit 0=PASS, 1=FAIL.
# Spec: anicca/docs/superpowers/specs/2026-06-26-B1-akash-provider-services-acceleration.md
set -uo pipefail
D="$LIFE_MANAGER_REPO/skills/self/spawn/scripts"
S="$D/deploy-akash.sh"
src="$(sed 's/#.*//' "$S")"           # comments stripped — INV checks are about ACTIVE CODE
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
# FIND-001/006 the corrected parses must be present
have   'EventDeploymentCreated'                     "FIND-001 dseq parsed from EventDeploymentCreated id-attr (verified real shape)"
have   '\.bid\.id'                                  "FIND-002 bid_id path = .bid.id (verified real shape, NOT .bid.bid_id)"
have   "uact"                                       "FIND-006 SDL pricing+deposit denom is uact (AEP-76 escrow MUST be uact)"
absent 'PRICE_DENOM:-uakt'                          "FIND-006 pricing default is NOT uakt (gas stays uakt)"
have   'AKASH_DEPOSIT.*uact|deposit.*uact'          "FIND-006 deposit denom is uact"
# FIND-012 ordered flow: cert < deployment < bid < lease < manifest
ln(){ grep -nE "$1" "$S" | grep -vE ':[[:space:]]*#' | head -1 | cut -d: -f1; }   # skip comment lines
C=$(ln "tx cert"); DC=$(ln "deployment create"); BD=$(ln "bid list"); LC=$(ln "lease create"); SM=$(ln "send-manifest")
ok "$([ -n "$C" ] && [ -n "$DC" ] && [ -n "$BD" ] && [ -n "$LC" ] && [ -n "$SM" ] \
      && [ "$C" -lt "$DC" ] && [ "$DC" -lt "$BD" ] && [ "$BD" -lt "$LC" ] && [ "$LC" -lt "$SM" ] && echo 1 || echo 0)" \
   "FIND-012 commands ordered cert<deploy<bid<lease<manifest (got $C<$DC<$BD<$LC<$SM)"

# ---------- BEHAVIORAL: faithful fake provider-services ----------
mkfake(){ # $1 = fail mode ("" | create | nobid | lease | manifest)
  cat <<FAKE
#!/usr/bin/env bash
echo "\$*" >> "\$B1_REC"
FAIL="${1}"
case "\$*" in
  *"keys show"*)            echo "akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523" ;;
  *"query cert list"*)      echo '{"certificates":[{"certificate":{"state":"valid"}}]}' ;;
  *"tx deployment create"*) [ "\$FAIL" = create ] && echo '{"code":11,"raw_log":"insufficient funds"}' \
                              || jq -nc '{code:0,txhash:"ABC",events:[{type:"akash.deployment.v1.EventDeploymentCreated",attributes:[{key:"hash",value:"xx"},{key:"id",value:({owner:"akash1ms7",dseq:"777"}|tojson)}]}]}' ;;
  *"query market bid list"*) [ "\$FAIL" = nobid ] && echo '{"bids":[]}' \
                              || echo '{"bids":[{"bid":{"id":{"owner":"akash1ms7","dseq":"777","gseq":1,"oseq":1,"provider":"akash1prov"},"state":"open","price":{"denom":"uact","amount":"5"}}}]}' ;;
  *"tx market lease create"*)[ "\$FAIL" = lease ] && echo '{"code":8,"raw_log":"bid not found"}' || echo '{"code":0,"txhash":"DEF"}' ;;
  *"query market lease list"*) echo '{"leases":[{"lease":{"state":"active"}}]}' ;;
  *"send-manifest"*)        [ "\$FAIL" = manifest ] && exit 1 || echo "ok" ;;
  *version*)                echo "v0.11.1" ;;
  *)                        echo "{}" ;;
esac
FAKE
}
runfake(){ # $1 = fail mode -> sets OUT, rc, recd
  local T; T="$(mktemp -d)"; REC="$T/rec"; : >"$REC"
  mkfake "$1" >"$T/provider-services"; chmod +x "$T/provider-services"
  OUT="$(B1_REC="$REC" PROVIDER_SERVICES="$T/provider-services" AKASH_KEY_NAME=anicca-akash \
         AKASH_NODE="http://localhost:1" AKASH_CHAIN_ID="testchain" AKASH_KEYRING_BACKEND=test AKASH_POLL_SLEEP=0 \
         bash "$S" testchild 2>"$T/err")"; rc=$?
  recd="$(cat "$REC")"; errd="$(tail -1 "$T/err" 2>/dev/null)"; rm -rf "$T"
}

# happy path: real shapes -> dseq+settled price parsed, full ordered flow called
runfake ""
ok "$([ $rc -eq 0 ] && echo 1 || echo 0)"   "behavioral happy: exit $rc — $errd"
DSEQ_OUT="$(jq -r '.dseq' <<<"$OUT" 2>/dev/null)"
PRICE_AMOUNT_OUT="$(jq -r '.priceAmount' <<<"$OUT" 2>/dev/null)"
PRICE_DENOM_OUT="$(jq -r '.priceDenom' <<<"$OUT" 2>/dev/null)"
ok "$([ "$DSEQ_OUT" = 777 ] && echo 1 || echo 0)" "behavioral happy: dseq parsed from event attr (JSON output) = '$DSEQ_OUT' (want 777)"
ok "$([ -n "$PRICE_AMOUNT_OUT" ] && [ "$PRICE_AMOUNT_OUT" != "null" ] && echo 1 || echo 0)" "behavioral happy: FIND-002/PROP-303c priceAmount present in JSON output = '$PRICE_AMOUNT_OUT'"
ok "$([ "$PRICE_DENOM_OUT" = "uact" ] && echo 1 || echo 0)" "behavioral happy: FIND-002/PROP-303c priceDenom present and is uact = '$PRICE_DENOM_OUT'"
for c in "deployment create" "bid list" "lease create" "send-manifest"; do
  grep -q "$c" <<<"$recd" || { echo "  - FAIL behavioral: '$c' never called"; fails=$((fails+1)); }
done
# fail-closed: deployment tx code!=0 -> exit!=0, NO dseq printed (HARD 0.24)
runfake create
ok "$([ $rc -ne 0 ] && [ -z "$OUT" ] && echo 1 || echo 0)" "behavioral fail-closed (create code!=0): rc=$rc out='$OUT' (want rc!=0, empty)"
# fail-closed: no bids -> exit!=0, NO dseq, NO lease/manifest
runfake nobid
ok "$([ $rc -ne 0 ] && [ -z "$OUT" ] && echo 1 || echo 0)" "behavioral fail-closed (no bids): rc=$rc out='$OUT'"
grep -q "lease create" <<<"$recd" && { echo "  - FAIL fail-closed: lease attempted with no bid"; fails=$((fails+1)); }; true
# fail-closed: lease tx code!=0 -> exit!=0, NO dseq, NO manifest
runfake lease
ok "$([ $rc -ne 0 ] && [ -z "$OUT" ] && echo 1 || echo 0)" "behavioral fail-closed (lease code!=0): rc=$rc out='$OUT'"
grep -q "send-manifest" <<<"$recd" && { echo "  - FAIL fail-closed: manifest sent after failed lease"; fails=$((fails+1)); }; true
# fail-closed: send-manifest fails — the provider-400 path that ACTUALLY fires on sandbox (evidence) -> exit!=0, NO dseq leak
runfake manifest
ok "$([ $rc -ne 0 ] && [ -z "$OUT" ] && echo 1 || echo 0)" "behavioral fail-closed (send-manifest 400): rc=$rc out='$OUT'"
grep -q "send-manifest" <<<"$recd" || { echo "  - FAIL: manifest never attempted in manifest-fail mode"; fails=$((fails+1)); }

# ---------- AKASH_SDL_TEMPLATE override (2026-07-05, self/spawn-child prep): the SDL actually submitted
# to `tx deployment create` must be the RENDERED external template (image-independent node:22 + git
# clone), not the inline ghcr.io heredoc — capture the SDL file content the fake sees.
mkfake_capture(){
  cat <<FAKE
#!/usr/bin/env bash
echo "\$*" >> "\$B1_REC"
case "\$*" in
  *"keys show"*)            echo "akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523" ;;
  *"query cert list"*)      echo '{"certificates":[{"certificate":{"state":"valid"}}]}' ;;
  *"tx deployment create"*) cat "\$4" > "\$B1_SDL_CAPTURE"
                             jq -nc '{code:0,txhash:"ABC",events:[{type:"akash.deployment.v1.EventDeploymentCreated",attributes:[{key:"hash",value:"xx"},{key:"id",value:({owner:"akash1ms7",dseq:"777"}|tojson)}]}]}' ;;
  *"query market bid list"*) echo '{"bids":[{"bid":{"id":{"owner":"akash1ms7","dseq":"777","gseq":1,"oseq":1,"provider":"akash1prov"},"state":"open","price":{"denom":"uact","amount":"5"}}}]}' ;;
  *"tx market lease create"*)echo '{"code":0,"txhash":"DEF"}' ;;
  *"query market lease list"*) echo '{"leases":[{"lease":{"state":"active"}}]}' ;;
  *"send-manifest"*)        echo "ok" ;;
  *version*)                echo "v0.11.1" ;;
  *)                        echo "{}" ;;
esac
FAKE
}
T="$(mktemp -d)"; REC="$T/rec"; SDLCAP="$T/captured.yaml"; : >"$REC"
mkfake_capture > "$T/provider-services"; chmod +x "$T/provider-services"
SPAWN_CHILD_TEMPLATE="$(cd "$(dirname "$S")/../../spawn-child" && pwd)/sdl/child.yaml"
B1_REC="$REC" B1_SDL_CAPTURE="$SDLCAP" PROVIDER_SERVICES="$T/provider-services" AKASH_KEY_NAME=anicca-akash \
  AKASH_NODE="http://localhost:1" AKASH_CHAIN_ID="testchain" AKASH_KEYRING_BACKEND=test AKASH_POLL_SLEEP=0 \
  AKASH_SDL_TEMPLATE="$SPAWN_CHILD_TEMPLATE" \
  bash "$S" templatechild >/dev/null 2>"$T/err2"; rc3=$?
ok "$([ $rc3 -eq 0 ] && echo 1 || echo 0)" "AKASH_SDL_TEMPLATE: templated run still exits 0 — $(tail -1 "$T/err2")"
ok "$([ -f "$SDLCAP" ] && echo 1 || echo 0)" "AKASH_SDL_TEMPLATE: SDL file was actually passed to tx deployment create"
grep -qE "^\s*image:\s*node:22-bookworm\s*$" "$SDLCAP" 2>/dev/null && ok 1 "" || { echo "  - FAIL: AKASH_SDL_TEMPLATE: captured SDL 'image:' line is not the image-independent node:22-bookworm base"; fails=$((fails+1)); }
grep -qE "^\s*image:\s*ghcr\.io" "$SDLCAP" 2>/dev/null && { echo "  - FAIL: AKASH_SDL_TEMPLATE: captured SDL 'image:' line still references the broken ghcr.io image"; fails=$((fails+1)); }; true
grep -q "ANICCA_CHILD_ID=templatechild" "$SDLCAP" 2>/dev/null || { echo "  - FAIL: AKASH_SDL_TEMPLATE: CHILD_ID placeholder was not substituted"; fails=$((fails+1)); }
rm -rf "$T"

[ $fails -eq 0 ] && { echo "PASS — all B1 deploy invariants hold (static + faithful-fake behavioral + fail-closed + AKASH_SDL_TEMPLATE)"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
