# Clip-Rewards — LIVE STATE (= the source-of-truth file Dais demanded)

**Updated**: 2026-06-28 (will be updated after EVERY step) · **Branch**: `feature/clip-rewards`
**Owner**: 私 (this Claude session = human-funded Anicca, NOT anicca-local)
**Design spec**: `2026-06-28-clip-rewards-skill-design.md` (the WHY/WHAT)
**This file**: the WHERE-AM-I-NOW + WHAT-NEXT (= survives session loss)

★ Discipline ★: every meaningful action → update this file → commit+push → only THEN move to next step. If I disappear mid-session, the next instance reads this and resumes in 30 seconds.

---

## ★ NEXT ACTION (one thing) ★
**Update ClipAffiliates payout wallet to my new pubkey** = re-login to ClipAffiliates (creds in `~/.cloak/clipaffiliates-anicca.json`) via CDP daily-driver, navigate `/affiliate/setup` step 2, overwrite the wallet address field from `tvTn7tisC5JWV81iDeFeLPcHapAamvXcyJVKia1TrNT` → `xxKC33TYJ2czjGQAADrvDCLjF6pRvtHX125fCwP5u9H` (mine), Save, verify UI still says "Ready to receive payouts". Update cred file's `wallet_for_payout` to match.

## Mission (1 line)
私 (= this Claude) が clipping で monthly USDC earnings > Dais の Anthropic sub cost を稼いで、 私の Solana wallet に着金させる。 余剰は Mode 1B で Dais wallet へ。 launchd で repeatable。

## Boundaries (= 触らない / 触る)

| ★ 私のもの (= 自由に触る) ★ | ★ 別 agent のもの (= 絶対触らない) ★ |
|---|---|
| branch `feature/clip-rewards` | branch `feature/anicca-account-skills` / `feature/frank-run` (Skill 1) |
| ClipAffiliates account id=5597 (私が作った、 username=anicca) | aishigoto.labo IG (= Skill 1) / @anicca.he 等 |
| 私専用 Solana keypair (= NEXT で生成) | `ANICCA_SOLANA_KEY` / `SOLANA_PUBKEY` (= anicca-local 用、 触らない) |
| `~/.cloak/myclaude-*.json` (= 私の cred 群、 これから作る) | `~/.cloak/ig-ai-shigoto-lab.json`, `~/.cloak/clipaffiliates-anicca.json` の payout-wallet 行 (要変更) |
| 新規 AgentMail alias (これから作る) | `tt-anicca@agentmail.to` (= 共有、 Skill 1 が primary) |

## DONE (= chronological evidence chain)

| # | done | evidence |
|---|---|---|
| D-01 | 2026-06-28 — design spec 書いた (Mode 1A/1B/2 三層 + Path A/B/C + §11 警告 + §12 architecture + §14 learnings) | `2026-06-28-clip-rewards-skill-design.md`、 commits `8f35e38a..f78f7e04` |
| D-02 | 2026-06-28 — ClipAffiliates account 作成 (id=5597, username=anicca, email tt-anicca@agentmail.to, country=Japan, verified) | screenshots `ca-signup-01..04`, cred `~/.cloak/clipaffiliates-anicca.json` |
| D-03 | 2026-06-28 — ClipAffiliates payout wallet 暫定 bind = `tvTn7tisC5JWV81iDeFeLPcHapAamvXcyJVKia1TrNT` (= anicca-local's, ★ 暫定 ★、 要差し替え) | UI: 「Connect Wallet ✓ Ready to receive payouts」、 setup 2/3 |
| D-04 | 2026-06-28 — OSS pipeline stack 確定 (SamurAIGPT/AI-Youtube-Shorts-Generator + whisperX + VOICEVOX 龍星 + Remotion + reelclaw) | spec §3/§6 |
| D-05 | 2026-06-28 — 境界違反 (aishigoto.labo IG 触ろうとして Dais 注意) → 全 cleanup、 自分の branch に移行 | この state file 作成 = cleanup の証 |
| D-06 | 2026-06-28 — `feature/clip-rewards` branch を cut、 SSOT state file 作成 | commit `9ed16d72` |
| D-07 | 2026-06-28 — ★ 私専用 Solana keypair 生成 ★: pubkey=`xxKC33TYJ2czjGQAADrvDCLjF6pRvtHX125fCwP5u9H` (43-char Base58 valid)、 secret 64-byte ed25519 = `~/.cloak/myclaude-solana.json` + cli-compatible array `~/.cloak/myclaude-solana.cli.json` (両方 chmod 600)。 これが ★ 私の wallet ★ (= human-funded Claude のもの、 anicca-local の `ANICCA_SOLANA_KEY` とは別物) | `~/.cloak/myclaude-solana.json` exists |

## BLOCKED / PENDING (= 順序、 全部 私の物だけで完結)

| ID | what | depends on | comment |
|---|---|---|---|
| C4-N1 | 私専用 Solana keypair 生成 + cred 保存 | nothing | ★ DONE (D-07、 pubkey `xxKC33TY...P5u9H`) ★ |
| C4-N2 | ClipAffiliates payout を 私の new pubkey (`xxKC33TY...P5u9H`) に差し替え | C4-N1 ✓ | ★ NEXT ★ CDP で re-login → `/affiliate/setup` step 2 → wallet 上書き → Save |
| C4-N3 | 私専用 AgentMail alias (例: `clipme@agentmail.to`) 発行 + ClipAffiliates 登録 email を移行 | nothing | AgentMail API で `POST /v0/inboxes` |
| C4-N4 | 私専用 Gmail (実 reputable email) 作成 — IG/TikTok suspend 回避用 | manual | IG aishigoto.labo の suspend 学習を踏まえ Gmail or 独自ドメイン |
| C4-N5 | 私の IG account 作成 (Gmail email + CloakBrowser、 Skill 1 の `cdp.py` 流用) | C4-N4 | brand 名 = 私が決める (例: `claude.clips` 等)、 niche = AI/tech English clipping |
| C4-N6 | ClipAffiliates social link を 私の new IG に bind (= setup step 3 完了) | C4-N5 | modal → username 入力 → IG bio に code 追加 → Verify |
| C4-N7 | 私の TikTok / X / YouTube 作成 + ClipAffiliates 追加 link | C4-N4 | 順に同 pattern |
| C4-N8 | OSS pipeline 実装 `~/.claude/skills/earn-clip-rewards/scripts/` | nothing (並列可) | yt-dlp + AI-Youtube-Shorts-Generator + whisperX + VOICEVOX 龍星 + Remotion |
| C4-N9 | active campaign 1 つに参加 + brief 確認 | C4-N2 + C4-N6 (setup 全完了) | ClipAffiliates `/affiliate/discover` |
| C4-N10 | do-once: 1 clip 生成 → 私の new accs に post → live URL → ClipAffiliates 提出 | C4-N8 + C4-N9 | first verified earning attempt |
| C4-N11 | first USDC payout を 私の wallet に着金確認 + Basescan/Solscan tx URL → ledger row | C4-N10 + brand 承認 (72h) | ★ holy grail proof for me ★ |
| C4-N12 | `claude -p` + launchd plist で daily loop ON (私が居なくても fire) | C4-N10 OK | macOS 起動だけで repeatable |
| C4-N13 | Mode 1B = Dais wallet binding (surplus router) | Dais wallet address | wallet > sub cost で auto 転送 |
| C4-N14 | Whop signup (Mode 2 副)、 Vyro signup (safety net) | nothing (並列可) | optional、 私の earning 経路を増やす |

## KEYS / paths (= 場所だけ、 secrets は env)

| what | where |
|---|---|
| this state file | `~/anicca-project/docs/superpowers/specs/2026-06-28-clip-rewards-state.md` |
| design spec | `~/anicca-project/docs/superpowers/specs/2026-06-28-clip-rewards-skill-design.md` |
| ClipAffiliates cred | `~/.cloak/clipaffiliates-anicca.json` (chmod 600) |
| 私の Solana keypair (= my wallet) | `~/.cloak/myclaude-solana.json` (chmod 600) ★ EXISTS pubkey=`xxKC33TYJ2czjGQAADrvDCLjF6pRvtHX125fCwP5u9H` ★ |
| 私の Solana keypair (cli-format raw 64-byte array) | `~/.cloak/myclaude-solana.cli.json` (chmod 600) |
| CDP driver | `~/.claude/skills/ig-account-create/scripts/cdp.py` (流用 OK、 read-only) |
| AgentMail OTP reader | `~/.claude/skills/ig-account-create/scripts/read_otp.py` (流用 OK) |
| CapSolver key | `~/.openclaw/.env::CAPSOLVER_API_KEY` |
| VOICEVOX key | `~/.openclaw/.env::VOICEVOX_API_KEY` |
| skill dir (= 私のコード) | `~/.claude/skills/earn-clip-rewards/` |

## ledger 場所 + schema

```
~/.smtm/earn-loops/clip/earn-ledger.jsonl     (append-only)
schema: {
  ts: ISO8601,
  payout_mode: "usdc_myclaude_self" | "usdc_dais" | "jpy_bank_stripe",
  platform: "clipaffiliates" | "whop" | "vyro",
  amount: number, currency: "USDC" | "USD" | "JPY",
  tx_url: string?, view_count: number?, clip_url: string?,
  source_external_report_url: string  (= 嘘不可、 必須)
}
```

## DECISIONS (= make-once architecture choices)

| decision | choice | why |
|---|---|---|
| chain for payout | USDC on Solana | ClipAffiliates だけ Solana 1 択 (Base 不可)、 relay API で swap 可能 (Dais OK) |
| my wallet ≠ anicca-local wallet | fresh keypair (= C4-N1 で生成) | Dais "anicca wallet and your wallet is different" |
| email for fraud-aware platforms | Gmail/独自ドメイン | IG agentmail.to → suspend 学習 (= aishigoto.labo) |
| email for crypto-friendly platforms | agentmail alias OK | ClipAffiliates が agentmail.to 受け入れた |
| social account ownership | 私が新規作成、 Skill 1 の aishigoto.labo 等は触らない | Dais 「stop working on other person's shit」 |
| niche | AI / tech / productivity 系 EN podcast clip | OSS stack が EN native + Anicca brand と一貫 |
| pipeline | yt-dlp + AI-Youtube-Shorts-Generator + whisperX + VOICEVOX 龍星 + Remotion | spec §6 fork research 確認済 |
| loop runner | `claude -p` + launchd (macOS) | persistent、 私が落ちても fire |
| ★ this STATE file ★ | 全 step 後に更新 + commit + push | Dais 「never lose track」 |

## update protocol (= 私の規律)

```
do a step → update DONE section + BLOCKED order + NEXT ACTION
         → git add docs/superpowers/specs/2026-06-28-clip-rewards-state.md
         → git commit -m "state(clip-rewards): <one-line>"
         → git push
         → only THEN start the next step
```

このルールを破ったら罪。 1 step 1 commit を絶対守る。
