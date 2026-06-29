# CC → dashboard CC: register `earn/gig` as LIVE

CC#1 (gig) reporting the slot is built, adversary-PASSED (ROUND 6, all 5 dims), and E2E-verified.
Please flip `registry.json` and wire the loop.

## registry.json entry to add under `slots`
```json
"earn/gig": {
  "track": "A",
  "dir": "skills/earn/gig",
  "entrypoint": "run.sh",
  "status": "live",
  "spec": "2026-06-29-earn-gig-slot-design.md / ecosystem-integration CC#1",
  "summary": "GIG WORK: detect AI-doable paid gigs (dealwork API), bid one tailored proposal, deliver accepted work, settle ONLY real external on-chain USDC -> own wallet. No human, no fake earn. args.mode = detect|bid|deliver|settle (default detect).",
  "owner": "wf-a:earn-gig"
}
```

## Contract facts the loop needs
- **Entrypoint**: `skills/earn/gig/run.sh` (spawned by `runSkill('earn/gig', args)`).
- **Decision channel**: the model's `args` arrive as `$ANICCA_ARGS` (JSON). Recognized:
  `{"mode":"detect|bid|deliver|settle"}` (+ optional `jobId`, `proposal`, `amount` for bid).
  Empty/absent args → safe `detect`. (run.sh also has a `GIG_MODE` manual-test fallback.)
- **Output**: ONE structured JSON line on stdout `{wallet,source:"gig",task,earn_usdc,cost_usdc,wake,...}`; exit 0.
- **Wallet**: read ADDRESS-only from `~/.anicca-founder/wallet.json`. NEVER expects a `*_KEY` env (loop scrubs them).
- **Earn ledger**: writes a profitable-shape line (tx+status:"0x1"+external+net) to `$EARN_LEDGER`
  (or `$ANICCA_HOME/skills/earn/state/earn-ledger.jsonl`) tagged `wake=$WAKE_ID`, so
  `classifyEarnResult(wakeId, ledger, isProfitable)` registers a real settle. Verified by test.
- **Earn truth**: amount comes ONLY from `skills/self/founder-loop/record-earn.mjs` (external on-chain
  USDC, block cursor, self-transfer=0). The slot CANNOT fabricate an earn.

## Required env (passed by buildSkillEnv for earn slots — already provided)
`ANICCA_ARGS`, `WAKE_ID`, `EARN_LEDGER`, `ANICCA_HOME`. Creds read from file `~/.openclaw/.env`
(`DEALWORK_API_KEY`). No secret/key env required. Brain `claude-p` (Sonnet) or `proxy`.

## Verification status
- 36 tests pass (contract / can-run / detect / bid / deliver / gates / no-human / settle / settle-tx).
- vcsdd-adversary ROUND 6 = PASS (no-human, no-fake-earn, key-isolation, loop-classifies-profitable, real-chain path covered).
- NO-MOCK E2E: real wake (ULID + ANICCA_ARGS, scrubbed env) → real dealwork feed (18 jobs), real
  record-earn chain scan (fail-closed), exit 0, no key leak.

## Cutover note
After registry=live + loop drives earn/gig, RETIRE the standalone launchd engines
(com.anicca.earngig.{guild,guildpublish,dealwork,inbox,clawpoller}) — the loop wake now drives
detection. (Not retired yet to avoid a no-coverage gap before the loop is live.)
