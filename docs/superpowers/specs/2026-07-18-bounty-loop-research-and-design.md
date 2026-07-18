# Bounty Loop — 研究 + 設計（human-zero で bounty を狩り crypto で受け取る）

作成 2026-07-18 / 主体 Fable（main session）/ 目的 claude-p が毎日自走で bounty を狩り、merge されて**着金**するまで回す loop の設計。将来 Franklin へ横展開。

引用の無い判断は書かない。研究の一次ソースは末尾。

---

## 0. TL;DR（Dais の前提の訂正込み）

1. **「GitHub account 自作 → PR 公開まで human-zero で証明済み」は誤り。** 証明されたのは account 作成のみ（`github.com/anicca-earn` = HTTP 200）。**PR 提出・merge は未証明**。新規 account は同日 3rd-party OAuth を弾かれる（anti-abuse cooldown、"You can't perform that action at this time"）。→ GitHub 連携 bounty（Algora/OnlyDust/Frantic）は **2026-07-01 に Dais 判断で放棄済み**。（出典: `docs/superpowers/specs/2026-06-30-earn-slots-daily-loop-master.md:228-239`）
2. **公開コード bounty 板は human-zero + crypto 受取に不向き。** Algora=Stripe Connect（実質 KYC + 1099 税処理、crypto 未実装）、Superteam Earn=payout に人間 claim + KYC 必須（公式が "agent は OAuth/wallet署名/KYC 不可" と明記）。さらに正当 bounty には数時間で 8〜10 PR が殺到、per-attempt でほぼ赤字（$16.88 の勝ちに ~$16 のトークン）。
3. **真の実線 = on-chain bounty。** wallet が payout そのもの、KYC 無し、人間ゼロで着金。有望度順 = **poidh > gib.work > Immunefi/audit contest（Code4rena/Sherlock/CodeHawks）**。
4. **既存 harness は既にある。** `profitable-claude/skills/bounty/`（Algora 向け PR→merge state machine、Sutando 5役 + 3層 self-improve/heal、payout=Stripe KYC が honest gap）。**2026-07-12 に `.disabled` 化されて停止中**。これを Algora→on-chain rail に付け替える + payout gap を wallet 直で埋めるのが最短。
5. **参照実装 = poidh-sentinel**（`0x94t3z/poidh-sentinel`）。cron + LLM 判定 + `acceptClaim`/`resolveVote` を on-chain 実行、deploy 後は human-zero。Anicca の loop 思想（cron + judgment=model + deterministic on-chain 実行）と同型。丸ごと copy+tweak 対象。
6. **$10k/月は per-token では無理、flat sub + 並列 fleet + 高額 on-chain 案件（audit）でのみ届く。** $506/日 の実験値は 30 並列 agent を定額サブスクで回した外挿。

---

## 1. 「done = 着金」— これは既に正しく設計されている

Dais の要件「提出時ではなく merge/着金が done」は既存 bounty harness と一致:
- `profitable-claude/skills/bounty/run.sh`: discover → claim OPEN → submit PR → **TRACK until MERGED** → payout。record-earn は **external USDC 着金のみ**（INV-7）。
- 共通 money lib `~/anicca/skills/_shared/lib/{solana-verify,ledger,identity-guard}.mjs`、`earn/lib/record.mjs` が「稼いだ = on-chain external tx を自分で確認した時のみ」を強制。

→ done 条件のロジックは流用可。**変えるのは (a) 案件ソース = Algora→on-chain 板、(b) payout = Stripe→wallet 直**の2点。

---

## 2. bounty 板 — human-zero + crypto 受取 ランキング

| 順位 | 板 | 通貨 | KYC/銀行 | GitHub/wallet だけで参加 | 報酬 | human-zero 着金 |
|---|---|---|---|---|---|---|
| **1** | **poidh** (poidh.xyz) | ETH/DEGEN on-chain | **無し** | wallet 署名のみ（**EOA 必須**、SC wallet revert） | 小額（0.001 ETH〜） | ◎ poidh-sentinel が実証 |
| **2** | **gib.work** | USDC/SOL (Solana) | 軽い（要実測） | wallet | 変動 | ○（要検証） |
| **3** | **Immunefi** | USDC/ETH 直接 | プロジェクト依存・匿名 whitehat 文化・OFAC 除外 | signup + wallet | **$1k〜$10M+** | ○ だが専門性ゲート高 |
| 4 | Code4rena / Sherlock / CodeHawks | USDC (Polygon/ZKsync) | 任意〜緩い（Sherlock は valid率20%縛り） | account + wallet | 数十〜数千 USDC | ○ contest 形式 |
| 5 | Cantina | crypto | **KYC 必須** | — | contest | ✗ |
| 6 | Superteam Earn | USDC(Sol) | **人間 claim + KYC 必須** | 発見/応募のみ自動化可 | $数百〜数千 | ✗（着金で人間） |
| 7 | Algora | USD (Stripe) | **Stripe=実質 KYC + 1099** | PR は可、着金に Stripe | $25〜$15k | ✗ |
| — | Gitcoin / Replit Bounties | — | — | — | — | **板として消滅/移行済** |

**非対称性の核心**: コード bounty の主要板は「解く」は AI 可でも「受け取る」で人間/KYC/銀行を要求する。**真に human-zero で crypto を受け取れるのは on-chain 系のみ。**

---

## 3. 既存 loop / harness の棚卸し（車輪を再発明しない）

| 資産 | 場所 | 使い方 |
|---|---|---|
| **bounty harness**（PR→merge state machine, Sutando 5役, 3層 self-improve/heal, scam-filter, funnel） | `profitable-claude/skills/bounty/` | **土台。** rail を on-chain に付け替え。現在 `.disabled` |
| **gig harness**（3層構造の参照: BASE strategy.json + self-improve[web検索+メトリクス] + self-heal[selfheal-request.json]） | `profitable-claude/skills/gig-work/` | self-improve/heal の型を copy |
| **money-correctness lib** | `~/anicca/skills/_shared/lib/`, `earn/lib/record.mjs` | 着金検証・ledger・identity gate。そのまま使う |
| **poidh-sentinel** | `github.com/0x94t3z/poidh-sentinel`（外部） | on-chain 判定+payout の参照実装。丸ごと copy+tweak |
| **loop-engineering CLI** | `github.com/cobusgreyling/loop-engineering`（外部, MIT） | `loop-context`（予算 circuit breaker + 永続 ledger）/`loop-worktree`（試行隔離）/`loop-gate`（path denylist + auto-merge allowlist）を harness 部品として copy |
| **loopy** | `github.com/Forward-Future/loopy`（外部, MIT） | loop の4問フレーム（Goal/検証/学び/停止）だけ借用。earn ロジックは無い |

**既存だが停止/放棄**: bounty launchd 2体 = `.disabled-2026-07-12`。GitHub-coupled bounty = 2026-07-01 放棄。claude-p loop = `ANICCA_SLOT_ALLOWLIST=x402_sell` で bounty スロットが**そもそも許可外**。

---

## 4. bounty で食う勝ちパターン（deterministic 化できる規律）

実験記事3本の実測（出典末尾）:

| 規律 | 具体 | script 化 |
|---|---|---|
| scam を弾く | bounty-label issue の **22.3% だけが実収益**、~20% が scam（repo名に"bounty"/自動生成issue/merged PR ≈0/コード実体なし） | filter |
| 飽和を避ける | 正当案件に数時間で 8〜158 反応。11番目 PR の期待値 ≒ $0 | scoring |
| 競合スコア選別 | `Score=(Comments×2)+(PRs×3)+(Days×-0.1)`、0-5 即提出/16+ skip。低競合(0-3)成功率34% vs 飽和(20+)<1% | scoring |
| 「板」でなく「merge する repo」を探す | `author:me is:pr is:merged` で自分が通った repo を Pareto 特定し集中 → 72 merge に転換 | discover |
| 信頼を先に作る | maintainer review がボトルネック。低品質 AI PR は即 close、reservation ラベルは ban リスク | prompt/gate |
| 並列 fleet でないと採算割れ | per-attempt pay-per-token は赤字。flat sub × 並列でのみ黒字 | 実行基盤 |

judgment（PR 書く・maintainer と会話・案件の筋の良さ）は model に、scoring/filter/着金検証は deterministic script に（building-agents の原則）。

---

## 5. 配置の結論（anicca vs profitable-claude）

```
profitable-claude/skills/bounty/     ← 正本（AI-agnostic、every-Claude が使える tool。model 名を焼かない）
        │  vendor / symlink
        ▼
~/anicca/skills/earn/bounty/         ← colony earner が使う slot（franklin/claude-p が呼ぶ）
        │  uses
        ▼
~/anicca/skills/_shared/lib/         ← 着金検証・ledger（money-correctness 唯一の正本）
```

- 正本 = **profitable-claude/skills/bounty**（「every Claude が bounty で稼げる tool」= profitable-claude の使命そのもの）。
- colony（claude-p / franklin）は earn slot 経由で呼ぶ。将来 anicca colony に収斂（Franklin が本番運用）。
- money lib は `~/anicca/skills/_shared` の1箇所だけ（重複禁止）。

---

## 6. 段階計画（Dais 承認待ち、まだ実装しない）

- **Phase 0（証明）**: poidh testnet で 1件、bounty 作成→提出→on-chain accept→wallet 着金を **Fable が手で E2E**（poidh-sentinel を読んで最小再現）。着金を自分の目で見る。
- **Phase 1（skillify）**: 手順を `profitable-claude/skills/bounty/` に on-chain rail として実装。既存 state machine の Algora 部分を差し替え、payout=wallet 直。scam-filter/scoring を移植。
- **Phase 2（loop 化）**: claude-p の allowlist に `bounty` を追加 or 専用 launchd。done = on-chain 着金。self-improve（web検索 + 前週比）+ self-heal を gig からコピー。
- **Phase 3（scale）**: flat sub + 並列 fleet。高額 audit 板（Immunefi/Code4rena）へ拡張。黒字が実測できたら Franklin へ横展開。
- **loop trigger の規律**: 既存 launchd を `launchctl kickstart` で発火して watch。executor を spawn して代行しない（コードを直す時だけ executor 可）。

---

## 出典

- 内部: `docs/STATUS.md`(L5-8,152,182,299,345), `docs/superpowers/specs/2026-06-30-earn-slots-daily-loop-master.md:228-239`(BOUNTY PIVOT), `~/Library/LaunchAgents/ai.anicca.agent-economy-loop.plist`, `~/anicca/runtime/anicca-daemon.sh`, `profitable-claude/skills/bounty/run.sh`, `profitable-claude/skills/gig-work/gig-cli.sh`
- poidh: poidh.xyz + `github.com/0x94t3z/poidh-sentinel` README「A cron loop continuously evaluates submissions and picks winners automatically — no human in the loop after deployment」
- Superteam: `github.com/SuperteamDAO/earn` skill.md「Agents do not complete OAuth, wallet signing, or KYC. A human must claim the agent for payouts.」
- Algora: `github.com/algora-io/algora` + docs/payments.md「a payment processor to handle payouts, compliance & 1099s」、crypto は未実装
- 勝ちパターン: iotqowrop/algora-scout2 POST.md（$20予算48h→$0）, dev.to zeroknowledge0x「96h AI agent 実験」(240 PR/72 merge/$500-800), 同「1000 bounty issue 分析」(22.3% だけ実収益, 競合スコア式)
- harness 部品: `github.com/cobusgreyling/loop-engineering`(MIT), `github.com/Forward-Future/loopy`(MIT)
