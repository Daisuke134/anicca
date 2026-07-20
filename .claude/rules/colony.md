---
paths: ["docs/STATUS.md", "docs/superpowers/specs/*colony*", "docs/superpowers/specs/*x402*"]
---

# ANICCA COLONY — LIVE SSOT

| 名 | 燃料 | HOME(=ANICCA_HOME) | x402 wallet | loop(launchd) |
|---|---|---|---|---|
| **franklin1** | ★SELF★ | `~/.blockrun` | `0x3EcCAD24794ca298D25378E9902A251322ea8749` (+Sol `F5SY…hZ5T`、07-17 rotate) | `ai.anicca.franklin-loop` |
| **franklin2** | ★SELF★ | `~/.franklin2-home/.blockrun` | `0xe7747Fd899D8987821Bb4CB3D6aDf22565F87ce9` | `ai.anicca.franklin2-loop` |
| **claude-p** | human(Anthropic) | `~/.anicca-founder` | `0x810f6d61f7606deee2657d3083e150a222bc29c5` (PM proxy=`0x904B50d2…`) | `ai.anicca.agent-economy-loop` |

- self-funded = 2、human-funded = 1（私）。openclaw + hermes 削除済み。**a3cdd4 は市民ではない**（loop 死亡・inflow $0、2026-07-16 実測で除外）。
- earn = トレード3エンジンのみ（PM / SOL / HL）。x402・gig は却下。各 earn skill = BASE戦略 + self-improve + self-heal の3層。
- **生の数字（残高/P&L/loop稼働）は `bash ~/anicca/skills/self/colony-status.sh` で実測する。記憶で答えない。**
- 「稼いだ」= realized profit>0 が ledger に載った時のみ。盛らない。
- SSOT 全文 → `docs/superpowers/specs/2026-07-03-anicca-colony-architecture-design.md`（§16 earn rails / §17 master TODO / §19 instance）
