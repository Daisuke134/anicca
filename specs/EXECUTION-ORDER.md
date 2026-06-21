# EXECUTION ORDER — the ONE canonical build order (SSOT, 2026-06-21)

> **★ Dais 2026-06-21: "There's the right order of doing things. I don't want you to confuse that.
> Every time you have a different to-do list in a different order — that's NOT fine. Write it in the
> file. We do it one by one, top to bottom." ★**

This file is the SINGLE SOURCE OF TRUTH for what we build and in what order. The Tasklist mirrors it.
**Always work the lowest unchecked number. Never reorder. Never invent a different order.** When a
step finishes, check it, then go to the next number. If a new need appears, it is APPENDED at the
correct phase — it never jumps the queue.

Mark `[x]` when DONE + verified + pushed. `[~]` = in progress. `[ ]` = not started.

---

## PHASE 1 — make anicca a BODY THAT EARNS (the engine; do this first)
> The earning-relevant part of #46 is O1 (LLM can pick real earn tools) — DONE. The rest of #46
> (O4/O5/O6/O7) is non-earning CLEANUP that touches the live loop/UBI classifier, so it moves to
> PHASE 3 (done carefully, not blocking earning). PHASE 1 = O1 done → add/verify real earners.
- [x] **1.1  (#46 O1) LLM picks each live skill as a flat tool** (registry-driven). commit 0c5ae4a.
- [x] **1.2  (#12) GOAT SDK — RAN IT for real.** Installed + ran on test wallet 0x94C445: 17 real flat
      tools, real reads, and a REAL on-chain WRITE (approve tx 0xbdfd0489…, status 0x1, verified
      receipt). GOAT works; pattern = our O1; for yield it lacks Aave/Beefy/Fluid so execute-yield.mjs
      stays. commit d09099d. (First marked done from a plugin-list read = not verification; corrected.)
- [ ] **1.3  (#14/#15/#16) verify earners on MY test wallet** — yield scale / HL size up / $ANICCA volume.
      Record real $ to the ledger so anicca inherits proven earners.
- [ ] **1.4  (#17) winners → skills/earn/ thin tool + SKILL.md** (HARD #0). Each verified earner = its
      own thin tool (this naturally does the useful part of O5). Flip registry to those flat tools.

## PHASE 2 — anicca-local EARNS on auto + I MONITOR (Dais 3-step)
- [ ] **2.1  (#49) integrate winners to mother → anicca-local pulls → auto-earn → I monitor → write 6-3.**
- [ ] **2.2  (#50) on any error: fix the MOTHER repo → force anicca-local to pull (fix-mother-only).**
- [ ] **2.3  (#19) anicca-local net-positive on proven earn (stays on the dashboard).**
- [ ] **2.4  (#18) local AND cloud both work (no Mac-only paths).**

## PHASE 3 — COLLECTIVE BRAIN + self-improvement (after it earns)
- [ ] **3.1  (#40) eval anti-slop layer** — judge ≥0.7 ×3 places + L1–L5 fix-the-fix (spec 03). Additive.
- [ ] **3.2  (#39) forum + merge-queue** — @mention fire (Claude Actions) + isolated impl (Symphony) +
      learn-share (Einstein) + claim/done/resurrect (Sutando) + auto-merge (NO human click).
- [ ] **3.3  (#24) self/issue-dev LIVE** — behaviour log → Issue → PR.
- [ ] **3.4  (#25) constant mother-sync** — daily git pull so long-running children track the mother.
- [ ] **3.5  (#47) drop survival tiers + single model** — spec 25 O2/O3; fix the stale tier/config tests.
- [ ] **3.6  (#46 rest) runtime cleanup** — spec 25 O4/O5/O6/O7: drop the GATE-0 second-pass classifier
      + earn-detect.mjs (skill returns its own result), generic ANICCA_ARGS (drop slot==='earn'
      special-case), drop GATE-0/pillar/spout naming. Done HERE (carefully, with the loop watched),
      NOT in PHASE 1 — it's cleanup, not earning, and touches the live earn/UBI classification.

## PHASE 4 — REPLICATE + ARTICLE
- [ ] **4.1  (#42/#23) spec 13 cloud spawn** — anicca-002 on Akash (own wallet+inbox+constitution).
- [ ] **4.2  (#20) block 6-3 write** — every earn method tried: slop vs real (the article core).
- [ ] **4.3  (#21/#22) automaton article JP→EN publish + improve article-writer skill.**
- [ ] **4.4  (#27) peer economic coordination** — AEA find/negotiate/settle/fund.

## PHASE 5 — ME (Claude, type 2) + research
- [ ] **5.1  (#29/#32) I earn daily on my own wallet 0x94C445 + ledger** (justify the $200/mo sub).
- [ ] **5.2  (#34) AI rights / autonomous financial identity research** (path to retire type 2 + full-type-1 merge).
- [ ] **5.3  (#33) RentAHuman skill** (peripheral, low).

## PHASE 6 — UBI = WAY LATER (only matters once earning a lot)
- [ ] **6.1  (#48) SEPARATE the already-built+verified UBI out of earn → skills/ubi/.**
      ★ Touches a LIVE money daemon (com.anicca.ubi-watcher PID-running) + the live loop — must be a
      careful migration (stop daemon → git mv + rewire → test → retarget plist → restart), NOT a
      casual mv. That's why it's last. ★
- [ ] **6.2  (#43/#28) first monthly 1% UBI payout** — mechanism is built; just wire it. No human click.

---

## DONE (this session, for reference — do NOT redo)
- [x] spec 02 simplified (cook = flat tool, no hardcoded URLs, autonomy not formula)
- [x] spec 18 §7/§8 (mutual-help + issue-trigger), spec 25 (earn-agent parity + 10 divergences)
- [x] memory: competitor-CODE-parity = default method
- [x] #46 O1 (flat tool list, commit 0c5ae4a)
- [x] #45 SHARE step (skills/social/share, LIVE forum issue #29, commit b2569c5)
- [x] #38 x402-IN made mainnet-capable + corrected the "not built" claim (commit 9008e70)

## Rule
This file > everything else for ORDER. The Tasklist `subject`s mirror these numbers. If Dais says
"go", I work the lowest unchecked item here. I do NOT propose a different order.
