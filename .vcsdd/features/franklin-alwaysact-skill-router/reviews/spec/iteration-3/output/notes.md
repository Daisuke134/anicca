# Non-blocking observations — iteration 3

These are NOT blocking findings (per the anti-leniency rule, listed here only because they are genuinely
minor/deferrable, not because they are being softened):

1. **`isMarketRiskFree`'s behavior for a menu slot missing the `risk` field entirely is fail-closed only by
   accident of the equality check, never stated as an explicit design decision.** `isMarketRiskFree(slot,
   riskTagOf) = riskTagOf(slot) === 'safe'` (verification-architecture.md:45-49) happens to treat
   `undefined`/`null` as "not safe" (excluded from reroute targets) purely because `undefined === 'safe'` is
   `false` — this is the SAME fail-closed convention `catalog-gate.mjs` already uses (REQ-503's edge case:
   "untagged slot ⇒ treated as capital-risking"), but REQ-506/verification-architecture.md never says so
   explicitly for the NEW `risk` field this feature introduces. Not blocking (the pure predicate's own
   definition already fails closed regardless), but Phase 2b's implementer should not need to re-derive this
   from first principles — a one-line edge case would remove the ambiguity.

2. **FIND-101/102/103 are all genuinely, verifiably resolved in this revision** — independently re-derived,
   not merely re-read:
   - FIND-101: `skills/registry.json` (read directly this iteration, lines 71-224) confirms the claimed
     per-slot `risk` values byte-for-byte: `risk:"safe"` for `economy/gig`, `economy/lending`, `x402_sell`,
     `earn/clip`, `earn/clip-producer`, `earn/video` (6 slots) and `risk:"capital"` for `yield`, `hl_trade`,
     `token_launch`, `earn/sol-trade`, `earn/polymarket-trade` (5 slots) — exactly the 11-slot always-act menu,
     exactly matching behavioral-spec.md:92-96's claim and REQ-506's "6 of 11 ... risk:safe" framing
     (behavioral-spec.md:316).
   - FIND-102: swept every "think() call" / "2 total" / "extra call" mention across both files
     (behavioral-spec.md:258-259, 266-268, 378-382 [REQ-511 EARS], 424-433; verification-architecture.md:40,
     58-61, 106 [PROP-505a], 136 [PROP-511a]) — all now consistently state a single shared budget of 1 extra
     call, 2 total, never 3. No remaining "2 beyond baseline" framing anywhere.
   - FIND-103: REQ-513 (behavioral-spec.md:475-509) exists, correctly makes `index.mjs:402-416`'s sleep
     branch conditional on `!ctx.alwaysActEngaged`, routes fabricated `'sleep'`/off-menu slots into REQ-505's
     bounded reprompt path, and is reflected in the Purity Boundary Map's Effectful Shell section
     (verification-architecture.md:85-90) with `isRejectableSleepOrOffMenu` added to Pure Core (lines 53-57)
     and PROP-513a added (line 139). (See FIND-201 for the residual gap this fix's own reference-set choice
     introduces against REQ-506's reroute-narrower schema.)

3. Ground-truth spot-check performed independently this iteration (not merely re-trusting iteration-2's own
   notes): `runtime/loop/index.mjs:382-416,440-456,450` (full read), `runtime/loop/brain.mjs` (full read,
   lines 63/92 confirmed), `runtime/loop/prompt.mjs` (full read, `getToolDefinitions`/`SLEEP_TOOL`/line 171
   confirmed, no `opts` parameter exists yet — correctly described by the spec as a needed addition),
   `runtime/loop/parse-tool-call.mjs` (full read, confirms the scavenge-parser evidence underlying both
   FIND-103 and this iteration's FIND-201), `runtime/loop/context.mjs` (full read, confirms `WakeContext` is
   assembled once per wake with no per-attempt mutation API — the ground-truth basis for FIND-201),
   `runtime/loop/earn-slot.mjs` (full read, `isEarnSlot`/`EARN_ACTION` confirmed), `skills/registry.json`
   (full read, all 21 slot entries, `risk`/`status` fields confirmed as claimed).
