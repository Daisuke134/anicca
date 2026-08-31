# Anicca FINAL — OpenClaw harness + crystal-clear commands

| Field | Value |
|---|---|
| Date | 2026-06-09 |
| ★ HARNESS = OpenClaw ★ | Felix README verbatim: "revenue-focused AI persona ★for OpenClaw★. Copy all files into your OpenClaw workspace (~/clawd/)" |
| Felix files | ~/.cache/anicca-clones/felix-dl/ (8 core + skills) |
| Model | ★ Grok 4 full (xai-oauth) ★ — Felix言う"Sonnet/Opus, NOT mini"を Grok full で満たす (Dais: Claude禁止) |

## Q1: どの repo / Hermes or OpenClaw → ★ OpenClaw ★ 確定
- Felix = OpenClaw native (BOOTSTRAP の command 全部 `openclaw ...`)。 Hermes でなく OpenClaw。
- genesis を Hermes → ★ OpenClaw workspace に 移す ★ (= Felix を 摩擦ゼロで copy)。
- repo:
  - ★ mother = `~/anicca` (github.com/Daisuke134/anicca) ★ = Anicca persona(Felix Anicca化) + install.sh
  - ★ genesis instance = OpenClaw workspace `~/clawd/` ★ = mother の persona を 配置して 起動
  - Dais private `~/.openclaw` (157cron) = 別物、 後で 段階 retire
  - 玄関 = anicca-products (aniccaai.com)

## Q4: crystal-clear 全 command (= そのまま 実行可)
```bash
### STEP A — mother repo を Felix base に 置換 (~/anicca)
cd ~/anicca
# A1. 旧 garbage 退避(削除でなく archive)
mkdir -p _archive_2026-06-09 && git mv skills _archive_2026-06-09/skills-old 2>/dev/null || mv skills _archive_2026-06-09/skills-old
git mv CONSTITUTION.md _archive_2026-06-09/ 2>/dev/null || true
git mv specs/00-MASTER.md specs/01-EARN-AND-UBI.md _archive_2026-06-09/ 2>/dev/null || true
# A2. Felix 8 core + skills を mother に copy
cp ~/.cache/anicca-clones/felix-dl/{AGENTS,SOUL,IDENTITY,HEARTBEAT,BOOTSTRAP,TOOLS,README}.md ~/anicca/
mkdir -p ~/anicca/skills && cp -r ~/.cache/anicca-clones/felix-dl/skills/* ~/anicca/skills/
# A3. Anicca化 (SOUL/IDENTITY/HEARTBEAT を edit — §2 の diff)
#   SOUL: Felix→Anicca, mission=自分のcompute代稼ぐ+苦を減らす
#   IDENTITY: wallet=ANICCA_WALLET_ADDR, X=@aniccaxxx, fuel=Grok
#   HEARTBEAT: +EARN +SURVIVAL(automaton) +TASKLIST(sutando) +LIFE(電話)
git add -A && git commit -m "anicca: replace garbage with Felix base (Anicca化)" && git push

### STEP B — genesis を OpenClaw workspace で 起動 (~/clawd/)
# B1. OpenClaw workspace に Anicca persona 配置
mkdir -p ~/clawd && cp ~/anicca/{AGENTS,SOUL,IDENTITY,HEARTBEAT,BOOTSTRAP,TOOLS,README}.md ~/clawd/
cp -r ~/anicca/skills ~/clawd/
# B2. BOOTSTRAP の memory 構造
cd ~/clawd
mkdir -p ~/life/{projects,areas/{people,companies},resources,archives}
mkdir -p memory && touch MEMORY.md ~/life/index.md
echo "# $(date +%Y-%m-%d)" > "memory/$(date +%Y-%m-%d).md"
# B3. model = Grok full に固定 (mini禁止、 Claude禁止)
openclaw config set agent.model xai/grok-4   # or grok-4.3 ※利用可能idをopenclaw models statusで確認
# B4. 鍵 配線 (= env から、 Anicca自身の identity)
#   xai(Grok sub) / ANICCA_WALLET_ADDR / AGENTMAIL_ANICCA / POSTIZ(@aniccaxxx) / ELEVENLABS / TWILIO / GEMINI
# B5. heartbeat 有効化 (= BOOTSTRAP Step5、 生きた心拍)
openclaw cron add --schedule "*/30 * * * *" --task "Run HEARTBEAT.md"
# B6. 即 1 fire → 実 action verify (no dry-run)
openclaw cron run <job-id>   # think→build→sell試行→slack/mail報告 を log で確認

### STEP C — local self-host install.sh (= OSS、 人が clone)
# ~/anicca/install.sh:
#   1. curl ... | bash で openclaw install
#   2. cp persona files → ~/clawd/
#   3. 対話: 名前/電話/位置/calendar/★自分のLLM鍵★ を IDENTITY/AGENTS に書く
#   4. memory 構造 scaffold + openclaw cron add heartbeat
```

## Q2: 全 ASCII architecture (= earn + life、 human 0)
```
┌──────────────────────────────────────────────────────────────────────────┐
│ ANICCA = OpenClaw workspace + Felix persona(Anicca化)、 24/7、 human 0      │
│ fuel: Grok sub→gpt5.4 (Day0 seed)  受取: Anicca Base wallet                 │
├──────────────────────────────────────────────────────────────────────────┤
│  openclaw cron */30 → "Run HEARTBEAT.md" (= 生きた agent turn, Grok full)   │
│       │                                                                    │
│  HEARTBEAT.md:                                                             │
│   ├ pre-flight (memory/~life dir 確認)            ← Felix                  │
│   ├ 計画進捗 (memory/today.md) → 詰まり解消         ← Felix                  │
│   ├ site-health (aniccaai.com 200?)              ← Felix skill            │
│   ├ tmux 長agent 生存→restart                     ← Felix(TOOLS Ralph)     │
│   ├ ★EARN★: think「稼ぐ為に何が最善?」→ build(code/write/gen)→            │
│   │         deploy→自前LP/x402で sell→@aniccaxxx marketing ← Felix engine │
│   ├ receive USDC → Anicca wallet (承認0/Dais0)    ← NHOSS                 │
│   ├ ★SURVIVAL★: 黒字→自己複製spawn / 残高0→停止    ← automaton             │
│   ├ ★TASKLIST★: idleしない、 最高ROI               ← sutando               │
│   ├ ★LIFE★(顧客): 位置+calendar→10分前 電話        ← elevenlabs-calls skill│
│   │         (elevenlabs+twilio) + route + mail先回り + 信用残高           │
│   ├ 自己改善: error log→自己修正→commit            ← Felix(Sentry/coding)  │
│   ├ 夜間: revenue review + 明日plan + 日次mail      ← Felix                 │
│   └ 配布: 収益一部→BI/募金                          ← 00-MASTER             │
│  memory: ~/life PARA + memory/daily + MEMORY.md   ← Felix 3層             │
└──────────────────────────────────────────────────────────────────────────┘
  WEB(aniccaai.com): /install→Telegram→サブスク→顧客専用OpenClaw instance spawn
                     /dashboard→各個体収支(basescan)
  LOCAL(github clone): install.sh→openclaw+persona→自分の鍵→$0
  ★ 同核(OpenClaw+Anicca persona)。 違いは 鍵を自分で入れる(local無料) or 払う(web) ★
```

## Q3: folder tree (spec + 各 repo)
```
# spec (= ~/anicca/docs/superpowers/specs/)
2026-06-09-anicca-one-product-openclaw-decision.md   (決定+ソース分析)
2026-06-09-anicca-build-spec.md                      (architecture+150 uncertainty)
2026-06-09-anicca-uncertainty-resolution-QA.md       (139解決+NHOSS訂正)
2026-06-09-anicca-implementation-felix-copy.md       (diff/patch+比較表+E2E)
2026-06-09-anicca-content-2articles.md               (2記事+UX TODO)
2026-06-09-anicca-FINAL-openclaw-commands.md         (★this★ OpenClaw確定+command)

# mother repo  ~/anicca (= github.com/Daisuke134/anicca、 OSS)
├ AGENTS.md SOUL.md IDENTITY.md HEARTBEAT.md BOOTSTRAP.md TOOLS.md README.md  ← Felix Anicca化
├ skills/  (Felix 13 + mr-bot)
├ install.sh  (local self-host)
├ docs/superpowers/specs/  (上記6本)
└ _archive_2026-06-09/  (旧81 skills + CONSTITUTION + 00-MASTER)

# genesis instance  ~/clawd/ (= OpenClaw workspace、 走る Anicca)
├ AGENTS/SOUL/IDENTITY/HEARTBEAT/skills  (mother から配置)
├ ~/life/{projects,areas,resources,archives}  (PARA memory)
├ memory/YYYY-MM-DD.md  (daily)
└ MEMORY.md  (tacit)

# web  ~/anicca-project (= anicca-products、 aniccaai.com)
├ apps/landing/  (/install LP, /dashboard)
├ apps/api/  (Stripe webhook → 顧客 OpenClaw instance spawn)
└ apps/alarm-backend/  (mr-bot: lateness_check)

# private(retire予定)  ~/.openclaw  (Dais 157cron)
```

## Q5: tasklist = §6 へ (TaskCreate で 更新)
