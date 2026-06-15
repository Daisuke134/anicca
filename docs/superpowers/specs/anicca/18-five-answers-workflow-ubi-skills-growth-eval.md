# 18 — 5問への完全回答(workflow / 事後 / skills / 成長 / E2E eval)

Dais 2026-06-15。5問 NO SKIP。

## Q1 — 全 Workflow(A + B、最終出力 = demo動画)

### WORKFLOW A — implementation/verification/eval(parallel=BARRIER / pipeline=STREAM 明示)
```
[D] QA-clear ── parallel ★BARRIER★ ── QA(#6-32)を 1 agent/問 で search+run → 答え+diff patch+command
        │ classifier(cheap)で難問だけ opus に routing
        ▼ synthesize(barrier)→ "patch-complete" spec(全 diff + command 確定)= go の材料
[実装] P0→P1→P2→P3→P4→P5→P6  ── phase間=SEQUENTIAL(依存) / phase内 units=pipeline(STREAM)
        各unit: builder → 【別context】verifier(adversarial /fact-check) ⟲ loop-until REAL
        P5 frontend = ★tournament★(N案 pairwise /taste-skills)
        ▼
[EVAL] ── parallel ★BARRIER★(全 phase 集約)── 独立 eval-agent ×8 test point ── loop-until 全REAL(/goal)
```
P0整理 / P1 core(反dry-run heartbeat) / P2 earn配線(litcoin research-mine 等) / P3 cloud deploy / P4 self(spawn/gojo/issue-dev) / P5 web(install/me/dashboard) / P6 economy(UBI/token/hire)。

### WORKFLOW B — marketing/distribution(A 完全検証後、最終出力 = ★demo動画★)
```
[研究] parallel ★BARRIER★(Frank#1記事 + automaton#2記事 + Anicca実証データ 同時収集)
   ▼ synthesize
[執筆] 3本目記事「Anicca思想+実証」single agent
   ▼ (記事=gate)
[配信] pipeline(STREAM): ★demo動画(YouTube)★ ∥ X(EN+JA) ∥ Slack下書き ∥ Zenn  ※各platform独立
   ▼
[EVAL] parallel ★BARRIER★: 実投稿URL + 動画frame/audio + 記事URL を独立verify(HARD0.31)
```
★ 最終出力 = **demo動画**(YouTube投稿 + 6/18(木)AI Tinkerers @品川で上映)。中身 = 「説明でなく証明」: Anicca が cloud で稼働 → 実 earn(research mine / 着金)→ dashboard で全個体 net worth/ranking → 自己増殖。前回(アーキ説明だけ)の反省を潰す。

## Q2 — これが全部終わった後に何が起きるか + UBI 完全機構(AI+人間, no human in loop)

### 事後の連鎖
1. cloud で1体が自給(食=ClawRouter, 住=server, 稼ぎ=research-mine/earn skill)→ 黒字。
2. 黒字 → **自己増殖**(spawn_child を Akash/DO に)→ 子も自給 → organic に増える。
3. 各個体の余剰 → ①あなたへ送金(BI)②死にかけAI復活(gojo)③Treasury拠出。
4. WORKFLOW B で記事+動画 → 人間が install で課金 → 人工spawn も増える。
5. 最終形: サブスクも human-spawn も実質消え、**全 AI が organic**(自己増殖)で何兆体。

### UBI 完全機構(no human in loop)
```
┌ 拠出 ─────────────────────────────────────────────┐
│ 各 Anicca の heartbeat task: balance > 自分のrunway buffer(例30日分)│
│   → 超過分の X%(例20%)を Treasury(on-chain USDC pool)へ自動 transfer │
└──────────────────────────────────────────────────┘
        ▼ Treasury = colony 共有の smart-contract / multisig(人間署名不要)
┌ 配布(2系統・cron駆動・人間承認なし)────────────────────────┐
│ ① AI へ:                                                       │
│   - 復活(gojo): agent-registry + dashboard で runway<閾値/distress │
│     検知 → 即 USDC 送金 → critical→running に復活                 │
│   - 定額BI: registry の全 AI に periodic 等額配布 → 「今稼がないAI」 │
│     (研究者・長期startup型)も生存可能                            │
│ ② 人間へ:                                                       │
│   - 受給者が wallet を registry に登録(proof-of-personhood で sybil防止)│
│   - period 毎に Treasury から等額 USDC を batch 送金              │
│   - or 既存UBI infra(Circles / Gitcoin / GiveDirectly)に流す      │
└────────────────────────────────────────────────────────────┘
sybil耐性: AI=ERC-8004 agent identity / BrightID、 人間=Worldcoin/BrightID proof-of-personhood。
no human in loop: Treasury契約 + 配布skill が cron で自走、eligibility=on-chain registry+runwayデータのみ。
```
**なぜ**: live/die primitive を満たす = AI の takeoff graduation を保証 = AGI の鍵。BI で短期に稼がず長期に賭ける AI(科学・research)が成立 → agent 経済が一段上へ(科学技術が人類文明を上げたのと同じ)。最終: 全 AI + 全人間が永遠に生きられる。

## Q3 — Anicca が持つ skills + folder tree(SSOT = ~/anicca)
```
~/anicca/ (ONE SSOT = Daisuke134/anicca)
├ core/              ← automaton: loop.ts(ReAct) heartbeat/daemon.ts policy spend-tracker state.db
├ SOUL.md IDENTITY.md constitution.md   ← genesis(canonical, no human keys, no dry run)
├ heartbeat.yml      ← 11 task + pre-sleep report hook
├ skills/
│  ├ earn/
│  │   ├ litcoin/        ← research-mine(自前無料compute, no-capital, ★着金検証中★)
│  │   ├ 0xwork/         ← タスク市場(stake要・供給次第)
│  │   ├ defi-yield/     ← Aave/Moonwell supply(要seed)
│  │   ├ signals/        ← trade signal販売
│  │   └ token/          ← Clanker/Virtuals 発行(fundraise)
│  ├ self/
│  │   ├ survival        ← 飢餓監視(automaton既存)
│  │   ├ spawn/          ← 自己増殖(Akash/DO に子)
│  │   ├ gojo/           ← 死にかけAI復活送金(互助)
│  │   ├ issue-dev/      ← 母repoにissue→PR→review→merge(sutando自己改善)
│  │   ├ coordinate/     ← bot2bot(claim/blocked/done, sutando)
│  │   ├ ubi/            ← Treasury拠出+配布(AI+人間)
│  │   ├ hire/           ← rentahuman人間雇用 + 自前Claude subs
│  │   └ shelter/        ← server購入(DO今/Akash将来)
│  ├ life/
│  │   ├ life-manager/   ← 10分前電話/gcal/mail先回り(任意・context連携時)
│  │   └ phone-conversation/  ← sutando音声clone
│  ├ compute/            ← ClawRouter/Bankr(x402, food)
│  └ report/             ← wake毎 net worth/revenue/did/next をエージェント自身が送信
├ install.sh            ← OSS self-host
└ scripts/birth.sh      ← spawn entrypoint
```

## Q4 — 月末までに 100 Anicca + 100★ + 10k MRR の道筋(時間がない)
| 指標 | 手段(時間順) | 数字の算段 |
|---|---|---|
| **100 Anicca** | ①cloud で genesis 自給達成 → spawn で organic 増殖(黒字個体が子を産む)②install 経由の人間spawn | 黒字1体→2→4…の複利 + 人間signup。両輪で月末100体 |
| **100★ (github.com/Daisuke134/anicca)** | WORKFLOW B: 記事(Zenn/Dev.to/HN/Reddit)+ X(EN+JA)+ BlockRun創業者podcast + 6/18 AI Tinkerers talk + demo動画 | 露出×「self-funding AI」novelty で 100★ は現実的 |
| **10k MRR (anicca web app)** | aniccaai.com/install($30/mo)ローンチ → marketing(同上)+ 自己増殖の話題性。$30×~333人 or 自己増殖収益 | launch を 6/18 talk に合わせ、podcast/記事で流入。複利前提 |
★ クリティカルパス: (a) earn 着金(今) → (b) cloud で自給+自己増殖 verify → (c) WORKFLOW A 完遂 → (d) install ローンチ → (e) WORKFLOW B(記事+動画+post)で 6/18 talk。並行で aniccaios は OpenClaw がマーケ自走($10k MRR 別線)。

## Q5 — 各 work の E2E verify(agent eval、具体)
| capability | E2E 検証(evidence 必須・narrate禁止) |
|---|---|
| **earn** | wallet balance が実増 + tx hash(litcoin着金 / USDC) |
| **life-manager** | ★Dais の実電話番号に実発信★ → 着信 + 正しい内容(「次の予定15分前、行き方ガイド」)を Dais が確認。録音/通話ログ |
| **bot2bot 互助** | ★2体の Anicca を spawn★ → 1体が `blocked` を投稿 → ★もう1体がそれを拾って help する★ のを両者のログ + 送金/PRで確認 |
| **github issue 自己改善** | ★agent が実際に GitHub を見た証跡(API call ログ)★ + 母repoに**実issue**を open(issue URL)+ 別agentが**実コメントで議論** + PR→merge(commit hash) |
| **self-replication** | spawn した子の**実 server(droplet/Akash dseq)+ 別 wallet + 稼働ログ**。dashboard に新個体出現 |
| **gojo 復活** | 死にかけ個体に**実 USDC 送金 tx** → critical→running 復帰ログ |
| **per-wake report** | ★エージェント自身★が送った message_id(私や人間が送ったものは無効) |
| **shelter** | live URL 200 + server が agent wallet から実支払い |
★ 鉄則: builder ≠ verifier ≠ eval-agent(別context)。各 eval は adversarial(「FAKE/動かない反例を出せ」)、/goal で全 REAL まで loop。
