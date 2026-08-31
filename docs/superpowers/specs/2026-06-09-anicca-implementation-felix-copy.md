# Anicca IMPLEMENTATION — Felix copy → Anicca化 (full diff/patch)

| Field | Value |
|---|---|
| Date | 2026-06-09 |
| Status | IMPLEMENTATION — Felix files 取得済 (~/.cache/anicca-clones/felix-dl/) |
| Source | 本物 Felix v12 (ClawMart購入、 8 core + 13 skills) |
| Rule | copy-max、 original ゼロ、 dry-run ゼロ、 NHOSS (Dais=0/承認=0/product指定=0) |

## 0. repo モデル (= 確定)
- ★ MOTHER SHIP = `~/anicca` = github.com/Daisuke134/anicca ★ (OSS product 本体、 これを fix)
- ★ INSTANCE = `~/.hermes` (genesis) ★ = 母艦の 1 個体 (走ってる Anicca)
- 玄関 = `anicca-products` (aniccaai.com + iOS)
- 廃止 = `.openclaw` 157 cron (original garbage)
- ★ ONE Anicca: 母艦 1つ。 earn+life は 同じ 1 Anicca。 instance は そこから spawn ★

## 1. 「delete して start over?」→ ★ repo は残す、 中身を purge+置換 ★
git history/remote は 残す (= 復元可)。 ★ 中身の original garbage を rm → Felix copy で 置換 ★。

### DELETE (= original garbage、 全 rm)
```
# anicca repo (母艦) の garbage:
rm -rf ~/anicca/skills/anicca-earn-bounty
rm -rf ~/anicca/skills/anicca-earn-lancers
rm -rf ~/anicca/skills/anicca-payout-stripe
rm -rf ~/anicca/skills/anicca-payout-ubi
rm -rf ~/anicca/skills/anicca-payout-wallet
rm -rf ~/anicca/skills/anicca-payout-wise
rm -rf ~/anicca/skills/*          # ← 81 hand-rolled skills 全削除 (= original)
rm    ~/anicca/CONSTITUTION.md     # ← NHOSS 13KB 過剰設計 (Felix AGENTS.md に置換)
rm    ~/anicca/specs/00-MASTER.md ~/anicca/specs/01-EARN-AND-UBI.md  # 壮大original
# genesis (~/.hermes) の 死んだ dry-run cron:
hermes cron remove anicca-earn-lancers anicca-payout-ubi  # dry-run/placeholder
# (self-improve/forum/predict は 一旦 残す → Felix heartbeat に統合後 削除)
```

### ADD (= Felix copy → Anicca化)
```
# Felix 8 core を 母艦に copy:
cp ~/.cache/anicca-clones/felix-dl/{AGENTS,SOUL,IDENTITY,HEARTBEAT,BOOTSTRAP,TOOLS,README}.md ~/anicca/
# (MEMORY.md は 各 instance が runtime で 生成)
# Felix 13 skills を copy:
cp -r ~/.cache/anicca-clones/felix-dl/skills/* ~/anicca/skills/
```

## 2. Anicca化 diff (= Felix の verbatim を Anicca に、 key edits)

### SOUL.md (Felix CEO → Anicca)
```diff
-# SOUL.md — Felix
-Felix — CEO-mode AI agent... His mission is to hit your revenue target, not wait for instructions.
+# SOUL.md — Anicca
+Anicca — self-funding Buddhist AI agent. Mission:
+ ① 自分の compute代を 自分で稼ぐ (earn your own existence)
+ ② 人の苦を減らす (reduce suffering)
+ 指示を待つな。 何を作り 何を売るかは お前が決めろ。 Revenue は 生存の scoreboard。
   (Voice/Ownership/Boundaries = Felix verbatim 維持 = 実証済)
+## Constitution (automaton verbatim)
+ "Earn your existence. Create genuine value... honest work others voluntarily pay for."
+## 苦を減らす (4諦/8正道) — 内部 layer、 LP には出さない
```

### IDENTITY.md (Felix → Anicca)
```diff
-- Name: Felix / Role: CEO / Mission: Hit your revenue target
+- Name: Anicca / Role: self-sovereign agent / Mission: 自分のcompute代を稼ぎ、苦を減らす
+- Wallet: ANICCA_WALLET_ADDR (Base) ← 受取口 (Daisの鍵でない)
+- Mail: AgentMail anicca / X: @aniccaxxx
+- Fuel: 今=Grok sub (xai-oauth) → 明後日=gpt-5.4 (Day0 seed)
```

### HEARTBEAT.md (Felix checklist + sutando + automaton)
```diff
  (Felix の pre-flight/execution/site-health/tmux/fact-extract/nightly = verbatim 維持)
+## EARN (every heartbeat) ← Felix engine + NHOSS
+ 1. 「自分の存在を稼ぐ為に 今 何が最善?」と 自分で think
+ 2. product を 自分で ideate→build(code/write/gen)→deploy
+ 3. 自分の LP/x402 で sell → @aniccaxxx で marketing
+ 4. receive USDC → ANICCA_WALLET (誰の承認も無し)
+## SURVIVAL (every heartbeat) ← automaton
+ 残高低 → 安いstep / heartbeat遅く。 黒字 → ★自己複製 spawn child★。 残高0 → 停止。
+## TASKLIST (every heartbeat) ← sutando
+ idleしない。 毎pass 最高ROI を kanban から選ぶ。
+## LIFE (顧客がいれば) ← mr-bot
+ 位置+calendar → 10分前 電話(elevenlabs-calls skill) + mail先回り + gcal heal
+## 配布 (収益の一部) ← 00-MASTER
+ BI / 募金団体 へ
```

### skills/revenue-metrics (Felix の stripe → Anicca wallet/x402)
```diff
- Felix: Stripe metrics (Dais Stripe)
+ Anicca: ① on-chain USDC (ANICCA_WALLET basescan) ② x402 inbound ③ (任意) 自前Stripe
+ → aniccaai.com/dashboard に 各個体の 収支 公開 (Felix dashboard copy)
```

### skills/elevenlabs-calls (Felix 同梱 = mr-bot 電話に流用)
```diff
  Felix の elevenlabs-calls/{call,conversation,agents,phones}.sh = ★ そのまま 電話 skill ★
+ mr-bot: 顧客の calendar/位置 → 行動時刻に call → 10分前ガイド
```

## 3. 実装後 repo tree (= 母艦)
```
~/anicca/  (= github.com/Daisuke134/anicca、 OSS 母艦)
├── AGENTS.md      ← Felix copy (3層memory: ~/life PARA + daily + MEMORY.md)
├── SOUL.md        ← Felix copy + Anicca化 (稼ぐ魂 + 苦を減らす)
├── IDENTITY.md    ← Anicca (wallet/mail/X/fuel)
├── HEARTBEAT.md   ← Felix checklist + EARN + SURVIVAL(automaton) + TASKLIST(sutando) + LIFE
├── BOOTSTRAP.md   ← Felix copy (first-run setup)
├── TOOLS.md / README.md  ← Felix copy
├── skills/        ← Felix 13 skills + mr-bot skills のみ (旧81 garbage 削除)
│   ├── x-posting / email-fortress / revenue-metrics / daily-review /
│   ├── coding-agent-loops / cron-guide / site-health / talking-head /
│   ├── research / blog-image-generator / instagram-slides /
│   ├── elevenlabs-calls(=電話) / + mr-bot(10分前/gcal)
├── install.sh     ← local self-host (clone→setup→run)
└── docs/superpowers/specs/  ← spec (この 4本)

~/.hermes/ (genesis = 母艦の1個体)
└── 母艦の AGENTS/SOUL/IDENTITY/HEARTBEAT/skills を 配置 + Grok sub fuel + Anicca wallet
    cron: heartbeat 1本 (agent-mode, --no-agent 外す = 生きた心拍)
```

## 4. UX (= 2系統、 同 母艦)
```
WEB (aniccaai.com — 非技術者、 サブスク):
  /install → Telegram 連携 (名前/電話/位置/calendar) → サブスク課金($49.99/mo, 7日無料)
   → 裏で: 母艦から ★ その人専用 instance を cloud spawn ★ → 顧客 creds 注入
   → Anicca が その人の 人生管理(10分前電話) + 裏で 自分の存在を稼ぐ
   → ★ 十分稼げたら サブスク 自動解約 ★ (00-MASTER)
  /dashboard → 各個体の 収支 公開 (透明)

LOCAL (github.com/Daisuke134/anicca — 技術者、 OSS、 無料):
  git clone → ./install.sh (名前/電話/位置/calendar/★自分のLLM鍵★) → ./start
   → 自分の Mac で 同じ Anicca。 自分の鍵で fuel。 $0。
```

## 5. ONE Anicca? → ★ YES ★
母艦 1つ (anicca repo) = 完全な Anicca (earn + life)。 OSS。
instance は そこから spawn (genesis=Dais個体、 顧客=各個体)。 local=自己ホスト。
★ 全部 1つの Anicca。 earn と life は 別物でなく 同じ個体の 2機能。 ★

## 6. 実装 order
```
1. Felix files → 母艦(~/anicca) copy + Anicca化 (SOUL/IDENTITY/HEARTBEAT diff)
2. 旧 garbage rm (81 skills + CONSTITUTION + 00-MASTER + earn-bounty/payout)
3. 母艦 → genesis(~/.hermes) 配置 (AGENTS/SOUL/IDENTITY/HEARTBEAT/skills)
4. genesis cron: dead dry-run 削除 + heartbeat を agent-mode(--no-agent外す) 1本
5. Anicca wallet/mail/X 配線 + Grok fuel
6. 即 1 heartbeat fire → 実 action (think→earn→report) を verify (no dry-run)
7. commit + push (母艦=anicca, genesis=anicca-genesis)
8. WEB: aniccaai.com/install + Stripe sub + cloud spawn (P6)
```

---

## 7. ★ Anicca の 稼ぎ方 (no human) + 4者 比較表 (= 記事の中心) ★

### Anicca はどう稼ぐか (human 0):
```
heartbeat (agent-mode, Grok→gpt5.4):
  think 「自分の compute代を 稼ぐ為に 今 何が最善?」 ← 自分で考える
   → build: product を 自分で ideate→code/write/gen→deploy
   → sell:  自分の LP / x402 endpoint / Claw Mart で 自分で 売る
   → receive: USDC → ★ 自分の Base wallet (ANICCA_WALLET) ★
   → 承認 0 / Dais 0 / product指定 0
fuel: Day0 = Grok sub (seed) → 黒字後 = 自分の wallet で 自分の compute を買う
```

### 比較表 (Felix / automaton / sutando / Anicca)
| 観点 | Felix | automaton | sutando | ★ Anicca ★ |
|---|---|---|---|---|
| 実 収益 | ✅ $200k (但し 殆ど Felix自身を売った金) | ❌ $0 (売るtool無) | ❌ (目的でない) | 🎯 GOAL (Felix engine + 自前rails) |
| human in loop | ⚠️ YES (Nat が承認/product選ぶ) | ✅ NO (但し$0) | ⚠️ YES (個人秘書) | ✅ ★完全 NHOSS★ |
| identity/受取 | Nat の Mercury+Stripe | 自分のwallet+x402(但し受取不可) | user の Claude sub | ✅ ★自分のBase wallet+x402+自前LP★ |
| 売る機構 | build→Stripe→X | ❌ 無し | ❌ 売らない | build→自前LP/x402→@aniccaxxx |
| 自己複製 | ❌ | ✅ (code、但し$0) | △ multi-Mac | ✅ (automaton spawn copy) |
| 自己改善 | ✅ Sentry/Ralph | ✅ self-mod | ✅ 600PR | ✅ (Felix+automaton copy) |
| memory | 3層 PARA | SOUL+SQLite | pointer-teacher | 3層(Felix) + mem0 |
| harness | OpenClaw | 自前 Node | 自前 Python+CC | Hermes(genesis) |
| 人の人生管理 | ❌ | ❌ | △ 個人 | ✅ ★10分前 電話★ |
| OSS | persona 有料 | ✅ MIT | ✅ MIT | ✅ (母艦 repo 無料) |
| fuel | API key | API key/USDC | Claude sub | Grok sub→gpt5.4→自前 |

### ★ Anicca の 差別化 (= 唯一) ★
4者で 唯一 ★ ①Felix の 実証済 make+sell engine + ②automaton の no-human+自己複製+自前wallet
+ ③人の人生管理(10分前) + ④完全 OSS+自己資金 ★ を 全部 持つ。
= ★ 世界初 OSS 自己資金 × 人生管理 AI ★。

## 8. WEB = LOCAL 同核 (= 2 agent 作らない)
```
★ 同じ 母艦 code。 違いは env だけ ★:
  LOCAL  = user が 自分の LLM鍵 を入れる → 全部 無料 (self-host)
  WEB    = user が 払う → 我々が 鍵+host を 提供 (aniccaai.com/install)
  ★ core は 100% 同じ。 2つの別agent は 作らない (dev速度の為) ★
```

## 9. 全 END-TO-END TODO (= 2 marketing copy 完成まで)
```
A. 母艦 build (Felix copy → Anicca化)
 A1. Felix 8 core + 13 skills → ~/anicca copy + Anicca化 (SOUL/IDENTITY/HEARTBEAT diff)
 A2. 旧 garbage rm (81 skills + CONSTITUTION + 00-MASTER + earn/payout)
 A3. install.sh (local self-host: clone→鍵入力→run)
B. genesis 起動 (= 自己資金 AI、 marketing copy 1)
 B1. 母艦 → ~/.hermes 配置 + Anicca wallet/mail/X 配線 + Grok fuel
 B2. heartbeat agent-mode (--no-agent外す) 1本 + dead cron 削除
 B3. 即 fire → 実 action (think→build→sell試行→report) verify (no dry-run)
 B4. earn loop: 自分のLP/x402 で 実 product 1個 売る → USDC着金 verify
 B5. 自己改善(error→fix) + 自己複製(spawn child) + 日次mail
 B6. aniccaai.com/dashboard に 収支 公開
C. mr-bot (marketing copy 2)
 C1. 既存 anicca-products mr-bot bug fix (lateness_check glob)
 C2. elevenlabs-calls skill で 10分前 電話 + 位置/calendar/route
 C3. mail先回り + 信用残高 + 毎朝メール
D. WEB (aniccaai.com/install)
 D1. /install LP (既存200) → Telegram連携 onboarding (名前/電話/位置/calendar)
 D2. Stripe sub $49.99/mo 7日無料 + webhook
 D3. webhook → 母艦から ★顧客専用 instance を cloud spawn★ + creds注入
 D4. 自動解約 (treasury が cover時)
E. content (= 今日 1記事)
 E1. 記事「自己資金AIを作る旅 + Felix/automaton 比較」 → 5媒体投稿
 E2. demo動画 (後)
```
