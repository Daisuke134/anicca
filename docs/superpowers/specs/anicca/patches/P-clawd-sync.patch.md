# P-clawd-sync — sync OSS skills to the live runtime ~/clawd (env-allowlist FIRST, or earn halts)

> Spec: `28-product-redesign-merge-2026-06-16.md` §6 rows 1-3. Task #9. Targets: live runtime `~/clawd`
> (main-direct per HARD RULE #0 exception — runtime store, no worktree) + a small `~/anicca` earn `run.sh` diff.
> **Goal:** the three applied OSS patches (P-malice-guard, P-oss-local, P-lm-local-calling) reach the LIVE body
> WITHOUT halting the running earn loop. **Order is load-bearing.**

---

## §1 Reality found (cited)

| fact | evidence |
|---|---|
| live runtime exists with its own skills | `~/clawd/skills/{earn,...}` (verified `ls`) |
| earn `run.sh` SOURCES full env files | `~/anicca/skills/earn/run.sh:23` `for ENVF in /opt/anicca.env "$HOME/.openclaw/.env" "$HOME/clawd/.env"; do ... source ...` |
| malice-guard fails CLOSED if the earn process can SEE a user-PII env var | `~/anicca/skills/earn/lib/identity-guard.mjs` (P-malice-guard) throws before recording if `COMPOSIO_API_KEY`/`GOOGLE_LOGIN_*`/user mailbox vars are present in the process env |
| ∴ sourcing the FULL `~/.openclaw/.env` (which holds COMPOSIO/GOOGLE_LOGIN) into the earn process trips the guard → **earn loop HALTS** | combination of the two rows above |

**Conclusion:** before P-malice-guard goes live in `~/clawd`, `run.sh` must source ONLY the earn-needed vars (wallet key + RPC), not the whole `.env`. Otherwise the guard we just added halts the very loop it protects.

## §2 Diff — `~/anicca/skills/earn/run.sh`: allowlist the earn env (then mirror to ~/clawd)

```diff
diff --git a/skills/earn/run.sh b/skills/earn/run.sh
--- a/skills/earn/run.sh
+++ b/skills/earn/run.sh
@@ env discovery
-for ENVF in /opt/anicca.env "$HOME/.openclaw/.env" "$HOME/clawd/.env"; do
-  [ -f "$ENVF" ] && set -a && . "$ENVF" && set +a
-done
+# Allowlist ONLY the vars the earn path needs — never expose user-PII env (gmail/gcal/composio/
+# google-login) to the earn process, or identity-guard.mjs (malice-guard) fails closed and halts.
+# Reconciled against EVERY env var read by run.sh + execute-0xwork.py (verified 2026-06-16):
+#   run.sh: PKVAR BASE_RPC_URL EARN_MODE EARN_STRATEGY EARN_TX EARN_SOURCE EARN_AMOUNT EARN_COST EARN_TASK EARN_LEDGER WAKE_ID
+#   execute-0xwork.py: BASE_RPC_URL USDC_ADDRESS OXWORK_PKVAR PKVAR BLOCKRUN_WALLET_KEY OXWORK_API OXWORK_CAPS OXWORK_DELIVER OXWORK_POLL_SECS OXWORK_ANY_CATEGORY OXWORK_TASK_ID
+#   P-auto-cancel instance-side: AUTO_CANCEL_USDC SUB_ID SELF_CANCEL_TOKEN ANICCA_API_BASE
+EARN_ALLOW="BLOCKRUN_WALLET_KEY PKVAR OXWORK_PKVAR BASE_RPC_URL USDC_ADDRESS EARN_MODE EARN_STRATEGY EARN_TX EARN_SOURCE EARN_AMOUNT EARN_COST EARN_TASK EARN_LEDGER WAKE_ID OXWORK_API OXWORK_CAPS OXWORK_DELIVER OXWORK_POLL_SECS OXWORK_ANY_CATEGORY OXWORK_TASK_ID AUTO_CANCEL_USDC SUB_ID SELF_CANCEL_TOKEN ANICCA_API_BASE"
+for ENVF in /opt/anicca.env "$HOME/.openclaw/.env" "$HOME/clawd/.env"; do
+  [ -f "$ENVF" ] || continue
+  while IFS= read -r kv; do
+    k="${kv%%=*}"
+    case " $EARN_ALLOW " in *" $k "*) export "$kv" ;; esac
+  done < <(grep -E '^[A-Z_]+=' "$ENVF")
+done
```

(This keeps the wallet key reachable for the USDC-delta proof but hides COMPOSIO/GOOGLE_LOGIN/AGENTMAIL from the earn process so malice-guard stays green.)

## §3 Sync procedure (ORDER MATTERS)
```bash
# 1. land the env-allowlist diff in ~/anicca FIRST + push (so the canonical skill is safe)
cd ~/anicca && git add skills/earn/run.sh && git commit -m "earn: allowlist env (malice-guard safe)" && git push
# 2. THEN mirror the three applied OSS skills into the live body ~/clawd:
rsync -a ~/anicca/skills/earn/        ~/clawd/skills/earn/         # incl. identity-guard + allowlisted run.sh
mkdir -p ~/clawd/skills/life ~/clawd/runtime
rsync -a ~/anicca/skills/life/locate/ ~/clawd/skills/life/locate/  # P-lm-local-calling (source verified: skills/life/locate/locate.js)
# compute-proxy source is verified present (runtime/compute-proxy/{proxy.mjs,start-local.sh,package.json}); do NOT mask a missing source:
test -f ~/anicca/runtime/compute-proxy/start-local.sh || { echo "FATAL: compute-proxy source missing"; exit 1; }
rsync -a ~/anicca/runtime/compute-proxy/ ~/clawd/runtime/compute-proxy/  # P-oss-local proxy+start-local
# 3. register life/locate: add a slot to the registry, mirroring the existing life/* entries
#    (~/anicca/skills/registry.json:43-72 has life/travel|call|ask|notify, each {dir:"skills/life/<x>"}).
#    Add: "life/locate": { "dir": "skills/life/locate", ... } to BOTH ~/anicca/skills/registry.json and ~/clawd's registry.
# 4. verify the earn loop still runs a real wake AFTER sync (next section)
```

## §4 Acceptance (HARD 0.31 — verify earn NOT halted)
1. After sync, run one earn beat in the live body: `EARN_MODE=execute bash ~/clawd/skills/earn/run.sh` → exits 0, writes an `earn-ledger.jsonl` line, identity-guard does NOT throw.
2. `node -e "require('~/clawd/skills/earn/lib/identity-guard.mjs')"` style guard test passes with the allowlisted env (no COMPOSIO/GOOGLE_LOGIN visible).
3. `life/locate` slot added to the registry (`grep -q "life/locate" ~/clawd/.../registry*` → present) + a dry cadence tick run directly (`node ~/clawd/skills/life/locate/locate.js --dry-run --mode schedule`, the actual flags per locate.js:32) logs the 15/14/13+5 schedule (no real call in the dry test).
4. compute-proxy source confirmed present (`test -f ~/anicca/runtime/compute-proxy/start-local.sh`) then boots in the live body (`bash ~/clawd/runtime/compute-proxy/start-local.sh` health check) — P-oss-local live. No `|| true` masking.

## §5 Boundaries
`~/anicca/skills/earn/run.sh` (allowlist) is the only `~/anicca` code change; the rest is rsync of already-reviewed+applied OSS skills into `~/clawd` + registry wiring. No products-repo change. Runtime store = main-direct (HARD #0 exception).
