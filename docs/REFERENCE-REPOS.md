# REFERENCE REPOS — the competitors whose CODE we copy (read these, not Automaton/Franklin)

Recorded in a FILE (not memory — memories are not read). These are the autonomous-economic-agent
reference implementations. The method: read their ACTUAL code end-to-end, find the common pattern,
copy it; our originality is the bug. (Automaton & Franklin are pure SPENDERS — no earning — never
re-read them for revenue patterns.)

## The 4 canonical repos
| repo | handle | what to copy |
|---|---|---|
| **GOAT** | `goat-sdk/goat` | on-chain action primitives (erc20/swap/lend) as composable tools — verified real tx 0xbdfd0489 |
| **agent-adapter** | `AGICitizens/agent-adapter` | how an agent exposes/ös each capability as a discrete tool the model picks |
| **AEA** | `fetchai/agents-aea` | Autonomous Economic Agent framework — skills/behaviours/handlers + the economic decision loop |
| **sphere** | `unicity-sphere/sphere-sdk` | agent SDK patterns |

## Our 10 ORIGINAL divergences (= the bugs to remove, from the parity pass)
1. opaque single `run_skill('earn')` instead of each capability as its own tool
2. fat `run.sh` orchestrator doing dispatch the model should do
3. survival-tier model switching baked in (should be one model decision)
4. … (the rest are in the parity review; re-derive by reading the 4 repos)

## THE TWO PROBLEMS to solve right now (Dais 2026-06-21)
1. **Beefy + Fluid (the money trees, 6% / 5.36%) are NOT being used.** execute-yield DEFAULTS to Aave
   3.2%; Beefy is opt-in (`YIELD_PREFER_BEEFY=1`, never set); Fluid added as a const but never wired.
   → FIX: the agent should AUTOMATICALLY park idle USDC in the HIGHEST-APY working venue (Fluid/Beefy),
   with NO opt-in and NO model decision needed — "they just use it."
2. **The tools are all available but the agent isn't USING them.** The model picks earn:yield almost
   every wake; swap/x402/token/0xwork/hl rarely fire. → FIX: make each capability a real tool the model
   actually exercises (the GOAT/agent-adapter pattern: one tool per action, not one fat `earn`).
