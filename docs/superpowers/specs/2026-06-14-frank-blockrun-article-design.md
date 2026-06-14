# Article #2 — Frank (BlockRun) Design Spec

- **Date**: 2026-06-14
- **Series**: AI-entities (parent SSOT = `docs/superpowers/specs/2026-06-10-ai-entity-content-engine-design.md`)
- **Status**: DRAFT — research workflow pending, hamburger structure to be confirmed by Dais
- **Editor / co-author**: Daisuke (human-in-loop, block-by-block) + Claude Code
- **Subject**: **Frank / Franklin** by **BlockRun** (founder = @bc1beat). The "AI agent with a wallet" — spends USDC autonomously across 55+ providers via x402.
- **Anti-rule**: NEVER mention Anicca in this article. Reader = anyone who wants to understand Frank/BlockRun. We are scouts who actually ran it.

## 1. Why this piece (slot in the series)

Article #1 (Automaton, 2026-06-11 draft) framed the "earn-or-die" sovereign-AI thesis and showed the no-human-in-loop end of the spectrum. In that piece, Frank was introduced in one paragraph as "the more autonomous one with a wallet that decides what to pay for, per task". Article #2 zooms in on Frank: what it actually does, the BlockRun ecosystem around it (ClawRouter + blockrun-mcp + Money-Maker), and whether a reader should adopt it.

## 2. Primary sources (locked, must all be read in full)

| # | URL | Role |
|---|---|---|
| 1 | https://blockrun.ai/get-started | Onboarding path (what a new user does first) |
| 2 | https://blockrun.ai/docs | Concept + API surface |
| 3 | https://github.com/BlockRunAI/Franklin | The agent itself (627★, Apache-2.0, TS) |
| 4 | https://github.com/BlockRunAI/blockrun-mcp | Live-data MCP (search/research/markets/crypto/X), x402 pay-per-call (466★) |
| 5 | https://github.com/BlockRunAI/awesome-blockrun | Official ecosystem index (15★) |
| 6 | https://github.com/BlockRunAI/awesome-OpenClaw-Money-Maker | Money-loop curation (270★) |
| 7 | https://x.com/bc1beat | Founder voice / latest framing |

Adjacent for context (cite as needed): x402.org, Coinbase x402 launch post, Base for Agents, awesome-OpenClaw-Money-Maker README's "Web4 money loop" diagram (USDC → Franklin → ClawRouter → LLM → profit → reinvest).

## 3. Reader / verdict (block [0] target)

- **Reader**: AI builder who already runs Claude Code / OpenClaw, hears "Frank" / "BlockRun" everywhere, wants a straight call: install it or skip.
- **Pre-research hypothesis (to verify in WE-RAN-IT)**:
  - ✓ blockrun-mcp = useful TODAY for any agent (live web/X/markets, USDC pay-per-call, no subs) → install if you build agents
  - ◯ Franklin = useful if you want a wallet-funded autonomous worker; needs USDC funding (same Japan rail as Automaton)
  - ? "earns money on its own" = unverified — Frank's docs frame it as a SPENDER (autonomously pays for tools to get work done), not an earner. We test whether ANY revenue path is built in.

## 4. Hamburger (PRE-RESEARCH skeleton — to be replaced by workflow output)

The final hamburger comes from the research workflow run in §6. This is a placeholder so the structure is visible while research runs:

| Block | Working title | Notes |
|---|---|---|
| [0] | Verdict box | text only, 1-line use/skip + cost/risk/who-for table |
| [1] | Hook | The bottleneck not solved by Automaton (= Frank's actual thesis surfaced from sources) |
| [2] | What Frank is (everyone) | Wallet + YOPO + 55+ providers — in plain words |
| [3] | The BlockRun stack | ClawRouter (LLM gateway) + blockrun-mcp (live data) + Franklin (the agent) + awesome-OpenClaw-Money-Maker (the money loop) |
| [4] | How it actually works | x402 per-call payment flow, wallet boot, model selection, fallback (free-tier when wallet empty) |
| [5] | WE RAN IT — receipts | install blockrun-mcp, run Franklin, fund wallet via the Japan rail (re-use), observe real spend log + outputs |
| [6] | Honest verdict expanded | who should/shouldn't, what it earns/doesn't, where it breaks, founder credibility |
| [7] | Series hook | next piece + manifesto closing (per parent SSOT §13) |
| [8] | 出典 | every URL cited inline + listed |

Locked rules from parent SSOT Playbook (apply verbatim, do not re-derive):
- Audience = 14-year-old who knows nothing (rule 1).
- Verdict in sentence 1 (rule 4).
- Body = ですます prose, bullets only in verdict (rule 5).
- No em-dash「——」(rule 30). No unnatural set-phrases (rule 31).
- Heading = concrete hook, not meta-label (rule 6).
- Every term defined on first use, minimally (rules 8 / 39 / 54).
- Cite everything; concrete > vague; map the landscape, don't aggregate one source (rules 25–27).
- Show full blocks in review (rule 44).
- Close with the brand manifesto (rule 12, parent SSOT §11 closing manifesto).

## 5. WE-RAN-IT protocol (block [5] receipts to capture)

| Step | Action | Receipt |
|---|---|---|
| 1 | `git clone --depth 1` Franklin into `~/.cache/anicca-clones/` (HARD #-1) | repo size, top-level layout |
| 2 | Read Franklin README + `package.json` + entrypoint; document what's needed to boot | exact `npm` commands |
| 3 | Run blockrun-mcp via the published install path (don't clone if a `npx` / SDK entry exists) | first response from one live-data tool |
| 4 | Fund Frank wallet (if Frank has its own wallet at boot, capture address; reuse parent SSOT §12 Japan rail if needed) | wallet address (truncated) + USDC arrival tx |
| 5 | Run Frank with a small concrete task (e.g. "research X and produce a 1-page brief", $0.50 cap) | terminal log: what it paid for, how many providers, total spend, output quality |
| 6 | Honest report: did the output justify the spend? did it try to earn anything? | screenshot + verdict |

Spend cap: $1 USDC total for this test. Capture full log into `docs/articles/research/2026-06-14-frank-run-log.md`.

## 6. Research workflow (Dynamic Workflow — BP 6 patterns)

Built per the BP article (fan-out → adversarial verify → synthesize). One-shot, foreground, returns the hamburger structure as structured JSON.

- **Phase Fetch (fan-out)**: one Haiku-class agent per primary source (7 sources). Each agent uses `firecrawl scrape <url> markdown` (HARD 0.23) + `gh api` for GitHub files (README, key code files). Returns structured `{facts, quotes, claims, concrete_numbers, founder_voice_snippets}`.
- **Phase Verify (adversarial)**: for each non-trivial CLAIM surfaced in Fetch, spawn a verifier agent that re-checks against the primary URL with the explicit instruction to REFUTE. Vote ≥ majority confirms; otherwise the claim drops.
- **Phase Synthesize (one Opus agent)**: ingest verified facts + parent SSOT §11 playbook + Automaton article voice sample → produce: (a) 3 title candidates JP, (b) 9-block hamburger with one-paragraph guidance per block, (c) image-spot 🎨V# list, (d) sources list.
- **Token budget**: ~50k output tokens total. Quarantine: all Fetch agents are read-only (no side-effects). No agent writes to disk; outputs land in workflow return value, then this main loop writes to the spec.

Output of the workflow goes into a new section §7 below (replaces §4 placeholder).

## 7. Hamburger v0 (workflow output 2026-06-14, run wf_9ae52cdd-9d7)

Workflow stats: 7 source fetched / 20 claim verified / 18 confirmed / 2 refuted. Founder voice = "The wallet balance IS the hard limit" / "Other agents write code. Franklin Agent writes code and spends money".

### Title candidates (3, Japanese, ≤ 30 chars)

1. AIに$5の財布を持たせる実験
2. サブスクをやめてAIに財布を渡す日
3. 残高ゼロで止まるAIエージェント

### Blocks

| ID | Working title | Image | Sources to cite |
|---|---|---|---|
| 0 | 結論。Frankは「AIに財布を持たせる」最短ルート | — | get-started, Franklin |
| 1 | 世界一賢いAIが、$0.01のサーバー代を払えない | 🎨V1 | Franklin, awesome-blockrun, get-started |
| 2 | Frankとは「残高が尽きたら止まるAI」 | 🎨V2 | Franklin, get-started |
| 3 | Frankは1人じゃない。背後にある4つの部品 | 🎨V3 | ClawRouter docs, blockrun-mcp, Franklin, awesome-OpenClaw-Money-Maker |
| 4 | $5を渡すと、AIは何回しゃべれるのか | 🎨V4 | get-started, x402/how-it-works, ClawRouter, pricing, Franklin |
| 5 | 実際に$5入れて動かしてみた記録 | 🎨V5 | Franklin, blockrun-mcp, get-started — TO BE FILLED after WE RAN IT |
| 6 | 今すぐ使うべき人、まだ待つべき人 | — | blockrun-mcp, claude-code setup, ClawRouter, awesome-blockrun, Franklin, money-maker |
| 7 | AIから「お伺い」を消す日 | 🎨V6 | Franklin, get-started + manifesto close |
| 8 | 出典 | — | all 11 |

Per-block content guidance (verbatim from workflow synthesis) is captured in the workflow output file: `/private/tmp/claude-501/-Users-anicca-anicca-project/4d4a236a-271f-435f-ae4c-5e2f8db5f472/tasks/wcjh0e47b.output`. Each block guidance enforces: em-dash 禁止 / Anicca 禁止 / aggregation of one source 禁止 / meta-label 禁止 / first-use term definitions / verbatim founder quotes.

### Image spots (6)

| # | Block | Description |
|---|---|---|
| 🎨V1 | [1] | お金を払えないAI: ロボットがレジ前で立ち尽くす、財布なし、最小決済 $0.50 の貼り紙 |
| 🎨V2 | [2] | 財布を持ったAI: 透明ポケットに USDC $5、残高ゲージ、空になると座って止まる |
| 🎨V3 | [3] | BlockRun スタック分解図: ClawRouter / blockrun-mcp / Franklin / money-maker = 脳・手・財布・地図 |
| 🎨V4 | [4] | x402 シーケンス図: AI→server "API ください" / server→AI "HTTP 402 / $0.0023" / AI→server "署名付き再送" / server→AI "結果"。Base 手数料 ~$0.001 |
| 🎨V5 | [5] | 実走ターミナル + 領収書スタイル: コマンド・マスク財布アドレス・$5 入金・選ばれたモデル名・1回支払いログ・残高推移 |
| 🎨V6 | [7] | 鳥かご: 「人間の主体性」の檻、1本の鉄格子が外れて飛び立つ AI、朝焼け |

### Sources (11, in body order)

1. BlockRun 公式・はじめかた — https://blockrun.ai/get-started
2. BlockRun ドキュメント全体 — https://blockrun.ai/docs
3. ClawRouter 仕様（15次元スコアリング・78%節約） — https://blockrun.ai/docs/products/routing/clawrouter
4. x402 プロトコルの仕組み（EIP-3009 / 402 往復） — https://blockrun.ai/docs/x402/how-it-works
5. Intelligence Pricing（プロバイダー原価 +5%） — https://blockrun.ai/docs/products/intelligence/pricing
6. Claude Code 60 秒セットアップ — https://blockrun.ai/docs/getting-started/claude-code
7. Franklin Agent リポジトリ（627★・YOPO 定義） — https://github.com/BlockRunAI/Franklin
8. blockrun-mcp リポジトリ（466★・19 ツール） — https://github.com/BlockRunAI/blockrun-mcp
9. awesome-blockrun（x402 エコシステム実数） — https://github.com/BlockRunAI/awesome-blockrun
10. awesome-OpenClaw-Money-Maker（270★・運用カタログ） — https://github.com/BlockRunAI/awesome-OpenClaw-Money-Maker
11. x402 プロトコル公式 — https://x402.org

### Editor notes (from workflow synthesis)

- 創業者の声は驚くほど淡々として誇張がない。「The wallet balance IS the hard limit」「Other agents write code. Franklin Agent writes code and spends money」のような短い対比文が骨格で、ここを日本語で借用すると記事の体温が一気に上がる。SaaS 的な「unlimited」「powerful」を使わず、「stops」「hard limit」「no overdraft」と止まる側の語彙を選んでいる。
- 一番意外だったのは、x402 が机上のプロトコルではなく、12 月単月で 6,300 万件・$7.5M USDC が動いている実エコシステムだったこと（awesome-blockrun の State of x402）。「派手な未来予告」ではなく「もう動いている現在」として書くべき。一方で awesome-OpenClaw-Money-Maker が「ClawHub で認証情報を盗む skill が 341 件」と自分で警告している誠実さも見逃さない。
- 張るべき緊張は「自由 vs 自己管理」。サブスクは縛られている代わりに守られている。Frank は自由だが、秘密鍵を失えば残高も失う。14 歳の読者に「これは大人の道具で、軽くない」と伝えつつ、それでも開く価値があると感じさせる。
- 技術用語は初出で必ず 1 行定義（USDC = 米ドル建てデジタル通貨、Base = Ethereum の低手数料ネットワーク、MCP = Claude にツールをつなぐ USB のような規格、x402 = HTTP 標準の「支払い必要」コード）。読み上げテストで子供が 3 秒以上詰まる文は割る。

### Open questions (settle in WE RAN IT or by Dais)

1. Frank 初回起動で `~/.blockrun/.session` に保存される秘密鍵を、Mac 上でファイル権限 600 に自動で落とすか、それともユーザーが手動で `chmod 600` する必要があるのか（README に明記なし、実走で確認）。
2. Base 上での $5 USDC 入金の現実的な所要時間（Coinbase 経由とブリッジ経由でどちらが早いか、実走時に BaseScan で観察）。
3. ClawRouter の free プロファイル（NVIDIA 無料モデル）に残高ゼロで自動フォールバックするのか、それとも Frank は黙って停止するだけなのか（README 記述と挙動の一致を実走で確認）。
4. blockrun-mcp の 19 ツールのうち、ChatGPT Desktop 経由でも本当に全てが動くのか、Claude Code 限定の挙動があるのか。
5. Franklin の Smart Router (2M+ requests 学習) が、日本語プロンプトでも英語と同等の tier 判定をするか（次元スコアリングが英語キーワード前提に見える）。
6. x402 が返す 402 レスポンスの料金が、同じプロンプトでも実行ごとにブレるのか、決定論的なのか（実走で 2〜3 回叩いてログ比較）。

## 8. Publishing pipeline (parent SSOT §7 inherited)

JP first: note + Zenn + Substack(JP) + X Articles. EN follow-up: dev.to + Substack(EN) + X Articles. TikTok: 1 image JP + 1 image EN. The "AI article-writer" skill rebuild (parent SSOT §13 task) will absorb this flow once Article #2 is shipped — Article #2 sets the second data point (after Automaton) for what the skill must automate.

## 9. Open items

- Article slot in series: Automaton (#1, drafted) → **Frank (#2, this)** → Felix / ZHC / AutoHedge (later — order TBC).
- Founder bio: get @bc1beat real-name + pedigree from Twitter scrape during Fetch phase.
- Does Frank have a public dashboard like Felix's $202k? → Fetch phase answers.
- Does BlockRun host Franklin (managed) or is it self-host only? → Fetch phase answers.

## 10. Skill iteration follow-up (parent SSOT §13)

After Article #2 ships and is reviewed by Dais, rebuild `~/.openclaw/skills/article-writer` (or successor `anicca-article-daily`) so the deepest-search → run end-to-end → hamburger → multi-platform publish flow is automated. Embed parent SSOT §11 Playbook (54 rules) + this article's template + Automaton's template as in-skill guides. The skill must produce Article-#1-and-#2-quality pieces with no human in the loop, fulfilling the very thesis the series writes about (parent SSOT §13 brand strategy).
