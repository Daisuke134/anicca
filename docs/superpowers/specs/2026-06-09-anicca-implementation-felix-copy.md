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
+## LIFE (顧客がいれば) ← life-manager
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

### skills/elevenlabs-calls (Felix 同梱 = life-manager 電話に流用)
```diff
  Felix の elevenlabs-calls/{call,conversation,agents,phones}.sh = ★ そのまま 電話 skill ★
+ life-manager: 顧客の calendar/位置 → 行動時刻に call → 10分前ガイド
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
├── skills/        ← Felix 13 skills + life-manager skills のみ (旧81 garbage 削除)
│   ├── x-posting / email-fortress / revenue-metrics / daily-review /
│   ├── coding-agent-loops / cron-guide / site-health / talking-head /
│   ├── research / blog-image-generator / instagram-slides /
│   ├── elevenlabs-calls(=電話) / + life-manager(10分前/gcal)
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
