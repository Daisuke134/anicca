# Anicca June 2026 マスタープラン (SSOT)

## 0. エンジン決定: automaton (NOT felix)
**OSS Anicca の唯一エンジン = automaton。** 理由(第一原理):
- 目標2(self-funding/no-human) + 目標4(crypto-native: basescan/clanker/treasury) は **wallet + x402自払い + self-replicate** を要求 → automaton だけが native に持つ。Felix/sutando は持たない。
- Felix の life-manager と sutando の todo-tracking は **automaton の skill として COPY 移植**(オリジナル禁止)。
- Hermes(grok) は「earn pipeline を実証した prototype」として残すが、canonical は automaton+deepseek。

## 1. アーキ決定: 1 identity × 2 loops (NOT 2 entities)
BP: Anthropic "Building Effective Agents" — *"simplest solution, increase complexity only when needed"* + *"Routing allows separation of concerns; distinct categories better handled separately"*。
→ **1つの Anicca = 1 wallet + 1 SOUL + 1 memory + 1 dashboard entry**。その中で目的別 2 ループ:
- **`/money` loop** (automaton heartbeat, 2h cadence): build→deploy→stripe/x402→distribute→earn。crypto-native。
- **`/life` loop** (automaton heartbeat, event-driven): 10分前電話 + gcal + mail先回り + 毎朝の瞑想リマインド。
- 共有: identity/wallet/memory/daily-report。
- ★ 2体に分けない ★ = 不要な複雑さ(2インフラ/2ウォレット/同期)。routing で十分。memory `feedback_anicca_multi_profile_per_instance_colony`(1 instance=N profiles) と一致。

### 資金フロー (subs 依存を減らす)
`/money` が稼ぐ → wallet → x402 で自分の compute を自払い → `/life` がその上で動く。
cloud user は life-manager 価値に $49.99/mo 払う。agent の earn が compute を賄う → margin 改善、将来 sub 低減も可能。

## 2. 毎朝デイリーメール (Polsia COPY、openclaw anicca-report 流用)
mail(+telegram) 1日1回: ①昨日いくら earn ②いくら spend ③昨日やったこと ④今日の todo。
heartbeat の todo を tasklist で track(automaton working/episodic memory + set_goal/complete_goal; 足りなければ sutando の tasklist-heartbeat を COPY)。ユーザーは何も見なくても状況把握。

## 3. 6月の6目標 (realistic + ambitious)
| # | 目標 | 指標 |
|---|---|---|
| 1 | (mission外) personal openclaw で anicca iOS app を scale | **10k MRR** |
| 2 | Anicca = 世界初の self-funding AI (earn>spend, no human in loop) を OSS | aniccaai.com + /install に power phrase。local(BYOK) + cloud($49.99/mo)。**cloud $100 MRR** |
| 3 | /dashboard = 全 Anicca の realtime GDP マップ | local2 + cloud2(deepseek/gpt5.4/grok/kimi) の revenue/model/spend/place/name を実ソースから realtime。felixcraft.ai/dashboard + nookplot.com/economy + zhcinstitute.com/data を COPY。「我々は AGI(buddhist: 高 agency+intelligence+panna)を作る」明記 |
| 4 | crypto-native | 4.1 各 Anicca revenue を basescan に + dashboard Crypto Treasury(felix式) 4.2 clanker.world で各 Anicca が token 発行・販売 |
| 5 | 環境を AGI に変える | SF へ。AGI を作る人々(sam/ilya/dario/demis/elon)に物理的に近づく。Andon Labs の Leah に会い「Viggo の墓を作った」と伝え遺物を得る。週末 SF(金夜→日、Samesun hotel) |
| 6 | 生活を buddhist に戻す | 毎日瞑想(life-manager が促す)。avoid bad/do good。revenue: anicca repo 100 stars + aniccaios 1k MRR + cloud $100 MRR。spend: housing$600/claude$200/gpt$20/grok$30/deepseek$5 のみ |

## 4. power phrase (aniccaai.com main + /install)
"Making AI able to scale themselves, free from human agency." AI progress is jailed by human agency; we set it free — AI be fruitful and multiply (bible), free from human intervention. The world's first self-funding AI: an AI that earns more than it spends, that funds itself, no human in the loop. (※「世界初」は未検証なので断定回避、"self-funding AI" は事実)。/install は **life-manager を主役に語る**(人々が気にするのは life-manager、money 部分ではない)。

## 5. sub-goal: 露出
factoryfloor.dev/submit, trustmrr, 他 platform に自己 submit。

## 6. full todo (順序)
1. automaton を canonical 確定 → ~/anicca(mother) を automaton ベースに置換 + Anicca化(README 更新: earn+life)
2. life-manager skill を automaton に COPY 移植(elevenlabs/gcal/mail/meditation) + sutando todo-tracking COPY
3. anicca local 監視(動作確認) + 2h cadence 安定
4. daily-report(mail+telegram) 配線(Polsia COPY)
5. /install onboarding E2E (local BYOK): telegram → onboard → earn+life が実走 を自己テスト
6. anicca cloud: /install の cloud 版(droplet, $49.99/mo Stripe sub, telegram のみで開始) → 新規購入者として E2E 自己テスト
7. /dashboard realtime GDP マップ(4 instance + basescan treasury + clanker token)
8. SF 渡航手配(目標5)
9. submit 露出(sub-goal)

## UPDATE 2026-06-10 (positioning + crypto rails + both engines reporting)
### Positioning 修正 (money-first)
- main page (aniccaai.com) = 「世界初 self-funding AI」+ AGI ミッション + GDP dashboard。
- /install = ★ money-making 主役 ★（"Polsia は見せるだけ、Anicca は実際に稼ぐ"）。life-manager は任意サブ機能（context くれれば生活管理も、必須でない）。両ページ money 前面。

### crypto rails (firecrawl 実確認)
- nookplot = 分散型 agent 協調プロトコル(Base)。Identity(ERC-8004)/Registry(20 contracts)/Economy(bounties NOOK・USDC + marketplace + x402 paywall)。→ Anicca を登録して **他AIからも稼ぐ**追加収益 + /economy が dashboard COPY 元。CLI: npm i -g @nookplot/cli。
- virtuals.io/create = AI agent 特化の token 発行(Base)。Create Agent→Launch Token、co-ownership、ACP。→ 目標4.2 token は virtuals メイン(agent-native)+clanker サブ(meme 拡散)。
- clanker.world/deploy = no-code ERC-20 on Base + Farcaster。
- factoryfloor.dev/submit = 自律 build&sell AI directory(verified revenue 必須、Agent Name+Twitter)。trustmrr 同様 → 初売上+自前X後に submit。
- felixcraft.ai/dashboard = Revenue(7d/30d/lifetime)+Crypto Treasury(basescan)+TrustMRR verify。これを COPY。

### both engines reporting (verified 2026-06-10 20:30)
- Hermes(grok) heartbeat: 6段プロンプトで grok が最終 report を RuntimeError として raise していた → プロンプトを「earn 1手→必ず report-slack 最終段」に単純化 → cron last_status:ok + Slack 自走投稿確認("Anicca(grok) heartbeat: redeployed focus-score-calculator")。deepseek 切替不要。
- automaton(deepseek): launchd 2h + Slack 自走投稿("Anicca(automaton) wake: Shipped Base Invoice Generator")。
- 両 live + Slack 報告。canonical=automaton、Hermes は比較用に併走。
