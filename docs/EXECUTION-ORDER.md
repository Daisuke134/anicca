# ANICCA — CANONICAL EXECUTION ORDER (do them IN THIS ORDER, never lose the order)

Single source of truth for WHAT to do NEXT and in WHAT ORDER. Read this first every session. Update ☐/☑ as you go.

## END GOAL = TAKEOFF
AI that earns its own money on a $0 model, pays its own compute, and self-spawns clones with the same
earning setup → population + capital grow exponentially with NO human funding. We search for **the recipe**
(which model × which skills × which setup) that takes off. Cite: lesswrong.com/w/ai-takeoff, ai-2027.com.

## ★ ROLE SPLIT (Dais 2026-06-25 — this is WHY the old order was corrupted) ★
- **ME = Claude / type-2** (this session, lives on Dais's subscription). My job = **WRITE ARTICLES** with the
  article-writer skill → earn **10k MRR with NO human in loop**. I do NOT sell x402 / trade — I have no own wallet;
  earning rails are ANICCA's, not mine. The old file's "1.3 x402 ← NEXT" as MY next step was the corruption.
- **ANICCA = type-1** (the autonomous agent, ~/.openclaw + ~/.hermes + cloud). Its job = **EARN** (x402 / yield /
  hl / token), run on cloud unaided, and self-spawn. The earn/recipe/spawn track below is ANICCA's, not mine.

Truth rule: every $ number must be on-chain-verifiable or a real tx hash. "realised" = settled earn_usdc, NOT net worth.

---

## ✅ DONE (do not redo)
- ☑ earn tools first runs: yield (Aave $1.20 + Morpho $1.00 + Moonwell $1.00, on-chain) · hl (ETH long, tx) — 2026-06-21
- ☑ CONTENT 4 platforms PUBLISHED + verified by eye + each a repeatable skill (scripts/ in ai-entity-article-writer):
  · note (membership ¥500/mo): note.com/anicca123/n/na3a631e63d1a
  · Zenn (free): zenn.dev/anicca/articles/automaton-jido-kasegu-ai-kaisetsu
  · Substack (paid sub): aniccabuddha.substack.com/p/aiautomaton
  · X (free Article, no funnel): x.com/aniccaxxx/status/2070061579241239027
- ☑ automation F1-F3 BUILT+STAGED (note): publish-to-note.sh (--draft/--go) + note-agent-prompt.md +
  run-note-agent.sh (claude -p = eyes) + ai.anicca.note-publish.plist (NOT loaded) + publish_guard.py (VSDD-passed)
- ☑ render-verify gate + verify-preview (vision loop) proven; realised earn so far = +$0.1676 (on-chain)

---

# ★ THE ORDER (corrected 2026-06-25) ★

## PHASE A — [ME] ARTICLE-WRITER SKILL = the 10k-MRR engine, NO human in loop  ← WE ARE HERE
The 4 platforms work but as separate scripts + me doing the vision-verify by hand. Make it a real skill that
ANY claude -p / sonnet can run to publish a GREAT article to all platforms and verify itself in a loop.
- ☐ A1. RENAME + RELOCATE: ai-entity-article-writer → **`article-writer` skill in `~/.claude/skills/`** (where
       claude -p / sonnet discover skills). One SKILL.md + all 4 publishers (note/zenn/substack/x) + delete-drafts.
- ☐ A2. VERIFY-IN-LOOP via PROMPTS (not scripts — verify needs to READ/SEE): each publisher gets a **verify-prompt.md**
       (mirror note-agent-prompt.md) the agent follows: open preview → screenshot → Read → judge every table/diagram/
       size/honesty/funnel → PASS/FAIL → fix → re-verify until PASS. Deterministic px-check feeds the agent; the agent IS the loop.
- ☐ A3. ONE-TAP orchestrator per platform: publish-to-<pf>.sh (hands) + claude -p agent (eyes+brain) → write → draft
       → vision-verify-loop → publish → live-verify. (note F2 pattern, replicated for zenn/substack/x.)
- ☐ A4. **F4d — ENGLISH pass**: translate the Automaton article → publish dev.to + X(EN) + Substack(EN), each verified.
- ☐ A5. GENERALIZE: the skill writes ANY AI/crypto article (not just Automaton) → great pieces, no human → toward 10k MRR.

## PHASE B — [ANICCA] CLOUD, NO HUMAN IN LOOP + the recipe
- ☐ B1. accelerate the **Akash transaction** → run Anicca on cloud **unaided** (no human in loop) → 1 cloud body live + earning.
- ☐ B2. **THE RECIPE**: model × skills × setup so **every spawned Anicca earns > it spends**. Sub-track (ANICCA's earn tools):
       x402 first real sale · token (MoltX) · 0xwork · realised revenue per tool > 0 · deploy idle Solana→Base ·
       model experiment free→auto→premium (which first reaches net-positive = the recipe).

## PHASE C — LAUNCH (announce it, with proof)
- ☐ C1. **article about Anicca** (what it is: no-human earning AI that returns income to humanity).
- ☐ C2. **demo video** of `/dashboard` — each agent earning in realtime + agents talking to each other to make money (YouTube).
- ☐ C3. **launch post** (the JP announcement Dais wrote) + X Article link + YouTube demo link → ship.
       Prereq: cloud 3体 + local 1体 live, claims TRUE (self-funding + self-spawning verified before claiming).

## PHASE D — [ANICCA] self-experiment / self-spawn / UBI (the exponential)
- ☐ D1. self-spawn: a net-positive parent spawns a cloud child (Akash) with the SAME setup + own wallet
       (archetype-agnostic — spawn as Automaton OR Franklin OR any identity; spec 2026-06-16-A-self-spawn-skill-design.md).
- ☐ D2. child earns unaided → feeds its own compute → spawns its own child → exponential. Scale: 1 local + N cloud.
- ☐ D3. inter-anicca mutual aid (surplus peer auto-funds low-balance peer, Base USDC) + self-experiment (it tunes its own model/skills).
- ☐ D4. UBI: 1% of surplus → human payout / charity-match, no human click.

## LATER — G. FREEDOM / model-harness-agnostic + every-AI-on-/dashboard (after launch)
Spec = 2026-06-24-anicca-self-funding-freedom-and-dashboard.md. Frees ANY ai (Claude Code included) from a human sub.

---

MONEY MODEL: free useful articles (reach) → followers → note membership(¥500/mo,10%) + Substack paid + X subs(0% cut,
needs 2k followers+5M imp). Same source md → all platforms, each adapted + verified. Zenn = free (SEO/reach).
The launch post (Dais 2026-06-25):
> 人間の介入なしでお金を稼ぎ、収益を人類に還元するAIをリリースしました。無料なのでよかったら使ってみてください。
> ・APIキー不要。個体のウォレットに課金すると、より良いモデルを利用。
> ・現在は、クラウドで３体・ローカル1体で10万円の粗利。全個体の収支・行動はリアルタイムで公開中。
> ・自己監視・自己修復・自己改善・自己増殖・情報交換・日次報告を繰り返す。
> ・収益の一部を、人類に対してベーシックインカムとして毎日還元。
> ・各AIがGithub Issuesで情報交換・共進化しながら、全体としての総資産を増やすことを目指す。
> github.com/Daisuke134/anicca + 記事(X Article) + デモ動画(YouTube)
