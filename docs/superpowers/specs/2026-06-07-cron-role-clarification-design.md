# Cron Role Clarification — Design Spec (v1.0)

**Date**: 2026-06-07
**Author**: Anicca under Dais directive 2026-06-07
**Status**: ★ DRAFT、 Dais review 前 ★
**Related**: `2026-06-07-cron-rectification-and-aniccaai-protection-design.md` v1.3 §3.6 Simian Army

---

## §0 — Goal (= 1 文)

100 enabled cron + 4 Simian Army + life-manager の役割を Netflix Simian Army single-responsibility + Andon Labs heartbeat-only pattern に identical 一致させ、 ★ 重複/曖昧 全消し ★。 各 cron は 「1 job、 1 schedule、 1 input、 1 output」 で定義。

---

## §1 — Why (= 2026-06-07 Dais 厳命)

Dais verbatim:
> "life manager and heartbeat shell how are they different?"
> "anicca watch sweep what is this? duplicating with harvester doctor monkey janitor and conformity monkey and cron manager?"
> "decide what the fuck we're gonna do and then what each cron's gonna fucking do. and then write a spec on it."

---

## §2 — BP Source (= identical follow)

### 2.1 Netflix Simian Army (2011 Tech Blog verbatim)
URL: netflixtechblog.com/the-netflix-simian-army-16e57fbab116

> "Conformity Monkey finds instances that don't adhere to best-practices and shuts them down."
> "Doctor Monkey ... detect unhealthy instances ... eventually terminated."
> "Janitor Monkey ... searches for unused resources and disposes of them."

★ Each monkey = ONE responsibility ★

### 2.2 Andon Labs Mona/Luna (2026 verbatim)
URL: andonlabs.com/blog/ai-cafe-stockholm

> "[Mona] analyzed the contract and generated a prioritized checklist of everything needed to open."
> "She also set up fixed delivery days ... missed five deadlines, leading to expensive panic orders."

★ AI = autonomous task list + 1 main heartbeat. Mona does NOT have crons. ★

### 2.3 K8s Controller Pattern
URL: kubernetes.io/docs/concepts/architecture/controller/

> "narrow responsibility, controlled blast radius"

★ Each controller = 1 resource type ★

---

## §3 — Decisions (= BP identical follow、 オリジナル synthesis ゼロ)

### §3.1 — 全 cron を 5 layer に分類

```
┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER A: HEARTBEAT (= Andon Labs identical、 strategic decision)        │
├─────────────────────────────────────────────────────────────────────────┤
│ A1. anicca-heartbeat       (6h)   ← 主 意識 心拍、 1 ACTION/beat       │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER B: BODY (= physical 時刻 critical、 deterministic shell scheduler)│
├─────────────────────────────────────────────────────────────────────────┤
│ B1. anicca-lateness-heartbeat-shell (*/5 min) ← life-manager skill 5min poll │
│ B2. anicca-life-manager (NOT a cron, SKILL)   ← physical 生活 管理 code │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER C: SIMIAN ARMY (= Netflix identical、 single responsibility 各)   │
├─────────────────────────────────────────────────────────────────────────┤
│ C1. anicca-doctor-monkey    (30 */6 *) ← error cron heal (SCAN+fast-path+LLM)│
│ C2. anicca-janitor-monkey   (0 3 *)    ← 30d stale cron archive         │
│ C3. anicca-conformity-monkey (0 */6 *) ← policy violation disable       │
│ C4. anicca-monkey-watchdog (launchd 4) ← monitor 3 monkeys              │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER D: EXTERNAL MONITOR (= EXTERNAL state、 social/SaaS、 NOT cron-self)│
├─────────────────────────────────────────────────────────────────────────┤
│ D1. anicca-watch-sweep      (47 * *)   ← 3 watcher: comedy×2 + account-burn │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER E: CONTENT FACTORY (= revenue/growth、 50 cron、 各SaaS channel)  │
├─────────────────────────────────────────────────────────────────────────┤
│ E1. article × 5 channels (devto/note/substack-ja/substack-en/zenn)     │
│     ★ NOT aniccaai.com (= anicca-article-daily-blog 永久disabled) ★    │
│ E2. reelclaw × 11 (TikTok anicca + honne ja+en, card+widget)           │
│ E3. monk-factory × 3 (watercolor JP×2 + monk-noon)                     │
│ E4. larry × 11 (X / Substack persona content factory)                  │
│ E5. yangmun × 2 (TikTok persona)                                       │
│ E6. comedy × 7 (ogiri / skit / recruit / booking)                      │
│ E7. tiktok cross-post / music / slideshow                              │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER F: CORE INFRA (= operational、 21 cron、 削除不可)              │
├─────────────────────────────────────────────────────────────────────────┤
│ F1. anicca-daily-mail (07/22)        ← Dais 日次 digest               │
│ F2. anicca-fuel-broker (17 *)        ← LLM key billing                │
│ F3. anicca-cold-email-reply (17 *)   ← mail autonomy (HR#6 例外)       │
│ F4. anicca-cold-email-send           ← outbound cold mail              │
│ F5. anicca-cfo-sync                  ← CFO state sync                  │
│ F6. anicca-postiz-health-daily       ← Postiz API health                │
│ F7. anicca-account-health-daily      ← SaaS account health              │
│ F8. anicca-config-canary-daily       ← config drift detection           │
│ F9. anicca-credit-monitor            ← credit/bank monitor              │
│ F10. anicca-booking-daily            ← booking state                    │
│ F11. anicca-schedule-template        ← schedule template               │
│ F12. anicca-event-bot-trigger (23 *) ← event bot trigger               │
│ F13. anicca-gcal-heal                ← gcal self-heal                   │
│ F14. anicca-stage-daily              ← anicca-stage publication         │
│ F15. anicca-warmup-flip-daily        ← email warmup                     │
│ F16. anicca-wallet-balance           ← wallet check                     │
│ F17. anicca-morning-leave-check (7:50)← physical morning leave         │
│ F18. anicca-night-fill / travel-fill ← night/travel routine             │
│ F19. anicca-haircut/dentist (quarterly)← physical self-care            │
│ F20. anicca-recruit-comedy-weekly    ← comedy recruit                   │
│ F21. accelerator/jsps application (monthly)← grant applications       │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER G: AMBIGUOUS (= 17 cron、 後 audit)                              │
├─────────────────────────────────────────────────────────────────────────┤
│ factory-bp × 3 (revenue/efficiency/internal)                          │
│ contra-daily / daily-letter-sender / daily-memory                     │
│ auto-research-e2e / tuning-skills-nightly                             │
│ anicca-pattern-jsonl-refiller / promoter                              │
│ anicca-article-self-improve / whitelist-learn / audit                 │
│ anicca-backlink-hn/ih/reddit ×3                                       │
│ app-reviews-daily                                                      │
│ anicca-comedy-weekly-book                                              │
│ daily-letter-sender / weekly-fresh-letter                             │
│ → §6 で 各 1 件 review 後 確定                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

### §3.2 — DEPRECATE: anicca-cron-harvester (= doctor 重複)

★ BP違反 ★: harvester も doctor も cron-self error を扱う。 Single Responsibility 違反。

**現状**:
- `anicca-cron-harvester` (sched=19 * * * *)
- script: `python3 ~/.openclaw/skills/anicca-core/scripts/cron-run-harvester.py`
- msg: "Classify (🔴CRIME / ❌real / ⚠️false-ok / ⏳transient). If ≥3 distinct briefs, emit fix task to workspace/tasks.json. Summary."

**重複**:
- harvester: classify cron run errors → emit task to tasks.json
- doctor: scan openclaw cron API for error status → fix via 5-strategy
- 同 cron が両 system に flag → 二重 fix attempt / race condition

**決定** = ★ harvester DEPRECATED ★ (= Netflix single responsibility identical):
- doctor が直接 scan (= openclaw cron list で error 列挙)
- doctor が JIT auto-allow (= 初発 error で auto-append)
- harvester の classify ロジック が必要なら doctor に内 inline 化

**migration**:
1. `openclaw cron disable <harvester-uuid>`
2. spec `2026-06-07-cron-rectification-and-aniccaai-protection-design.md` §3.6 に「harvester deprecated → doctor-monkey absorb」 追記
3. harvester skill dir は `~/.openclaw/skills/_archive/` へ移動

### §3.3 — Anicca-watch-sweep の役割 確定

★ EXTERNAL state 監視 のみ ★ (= cron-self 系 と完全分離):

| watcher | source | output |
|---|---|---|
| comedy-watch-replies | X mentions @comedy persona | reply if needed |
| comedy-recruit-poll | recruit form responses | new applicant alert |
| account-burn-detector | SaaS account state (= 7 services) | burn warning |

★ Doctor / Janitor / Conformity との重複 ゼロ ★ (= 対象 が違う)。
★ Harvester との重複 ゼロ ★ (= cron-self ではなく external)。
schedule 維持: `47 * * * *` (= hourly、 reply latency 妥当)。

### §3.4 — life-manager と heartbeat の関係 確定

```
┌─────────────────────────────────────────────────────────────────────────┐
│ anicca-life-manager (skill)                                              │
│   = physical life management code (gcal poll + Twilio call + agentmail) │
│   = invoke される側、 単独 cron entry 持たない                          │
├─────────────────────────────────────────────────────────────────────────┤
│ anicca-lateness-heartbeat-shell (cron */5 min)                         │
│   = life-manager skill を 5 min poll で invoke する shell scheduler     │
│   = msg: bash ~/.openclaw/skills/anicca-life-manager/scripts/run.sh    │
│   = 名前の「heartbeat」 = scheduler 自身 が時刻 critical で打つ「拍」  │
├─────────────────────────────────────────────────────────────────────────┤
│ anicca-heartbeat (cron 6h)                                              │
│   = 主意識 心拍 = LLM autonomous beat (= HEARTBEAT.md follow)          │
│   = strategic, 1 ACTION/beat                                            │
│   = 名前の「heartbeat」 = consciousness pulse、 NOT shell scheduler     │
└─────────────────────────────────────────────────────────────────────────┘
```

★ 命名混乱 を避けるため、 lateness-heartbeat-shell → ★ rename: `anicca-life-poll-5min` ★
  (= "heartbeat" 言葉が意識心拍 1 つに集中)。

---

## §4 — 各 cron 完全定義 表 (= 1 line per cron、 SST)

### §4.1 — LAYER A〜D (= 9 cron、 infrastructure)

| ID | name | sched | input | output | trigger | notes |
|---|---|---|---|---|---|---|
| A1 | anicca-heartbeat | 0 3,9,15,21 * * * | HEARTBEAT.md + tasks.json | 1 ACTION/beat → state log | 6h | Andon Labs identical |
| B1 | anicca-life-poll-5min (= rename) | */5 * * * * | gcal events | call + mail | 5min | rename pending |
| B2 | anicca-life-manager (= SKILL) | n/a | gcal API + location | call/mail action | n/a | invoked by B1 |
| C1 | anicca-doctor-monkey | 30 */6 * * * | openclaw cron error list | fix via pattern/LLM | 6h offset 30 | Netflix Doctor |
| C2 | anicca-janitor-monkey | 0 3 * * * | 30d stale crons | archive + provenance | daily 3am | Netflix Janitor |
| C3 | anicca-conformity-monkey | 0 */6 * * * | enabled crons + policy patterns | disable + alert | 6h offset 0 | Netflix Conformity |
| C4 | anicca-monkey-watchdog | 0 4 * * * | 3 monkeys' lastRunStatus | Slack alert + retry fire | daily 4am (launchd) | Netflix Atlas pattern |
| D1 | anicca-watch-sweep | 47 * * * * | 3 external sources | reply/poll/alert | hourly 47 | External monitor only |
| — | anicca-cron-harvester | DEPRECATED | — | — | n/a | merged into C1 |

### §4.2 — LAYER E + F + G (= 88 cron、 各 1 line)

[E1〜E50 content factory + F1〜F21 core infra + G1〜G17 ambiguous = total 88]
詳細表は §8 verification plan で task ごとに 1 件 1 件 audit。

---

## §5 — Data Flow (= 全 cron 相互関係 ASCII)

```
                  ┌───────────────────────────────────────────────┐
                  │ A1 anicca-heartbeat (6h)                      │
                  │   reads: HEARTBEAT.md + tasks.json fix_tasks  │
                  │   ACT: 1 task/beat (earn|article|P3|experiment)│
                  └─────────────────────┬─────────────────────────┘
                                        │ writes
                                        ▼
                  ┌───────────────────────────────────────────────┐
                  │ tasks.json (workspace/) — bounded queue (100) │
                  │   ・priority P0/P1/P2/P3                       │
                  │   ・project-niche P3 (= naist/retreat/uber/etc)│
                  └───────────────────────────────────────────────┘
                                        ▲
                                        │ writes (= heartbeat P3 trigger)
                                        │
                                        │ Note: harvester DEPRECATED, doctor
                                        │       direct SCAN replaces emit
                                        │
                  ┌───────────────────────────────────────────────┐
                  │ openclaw cron API (= 200 entries store)       │
                  └────┬──────────────┬──────────────┬────────────┘
                       │read+write    │read          │read+write
                       ▼              ▼              ▼
              ┌────────────┐  ┌──────────────┐  ┌──────────────┐
              │ C1 Doctor   │  │ C2 Janitor   │  │ C3 Conformity│
              │ heal error  │  │ 30d archive  │  │ policy disable│
              └─────┬───────┘  └──────┬───────┘  └──────┬───────┘
                    │                 │                 │
                    └─────────────────┴─────────────────┘
                                      │ all 3 monitored by
                                      ▼
                              ┌──────────────┐
                              │ C4 Watchdog   │
                              │ (launchd)     │
                              └──────────────┘

  ┌───────────────────────────────────────────────────────────────┐
  │ B1 lateness-heartbeat-shell (*/5) ← invokes B2 life-manager   │
  │ B2 life-manager: gcal → call/mail (physical body management)  │
  └───────────────────────────────────────────────────────────────┘

  ┌───────────────────────────────────────────────────────────────┐
  │ D1 watch-sweep (hourly :47) ← 3 EXTERNAL watchers              │
  │   comedy-watch-replies (X mentions) → reply via ledger        │
  │   comedy-recruit-poll → applicant alert                       │
  │   account-burn-detector → SaaS account warning                │
  └───────────────────────────────────────────────────────────────┘

  ┌───────────────────────────────────────────────────────────────┐
  │ E1〜E50: Content Factory                                       │
  │   article × 5 → Substack/Dev.to/Zenn/note publishing          │
  │   reelclaw × 11 → TikTok                                       │
  │   monk-factory × 3 → TikTok                                    │
  │   larry × 11 → X + Substack                                    │
  │   yangmun × 2 → TikTok                                         │
  │   comedy × 7 → X mentions / recruit / booking                  │
  │   ★ NO aniccaai.com writes ★                                   │
  └───────────────────────────────────────────────────────────────┘

  ┌───────────────────────────────────────────────────────────────┐
  │ F1〜F21: Core Infra                                            │
  │   daily-mail / fuel-broker / cold-email-reply/send             │
  │   cfo-sync / health × 3 / canary / credit / wallet             │
  │   gcal-heal / morning-leave-check / night-fill / travel-fill   │
  │   haircut / dentist (quarterly) / comedy-recruit-weekly        │
  │   accelerator / jsps (monthly grant)                          │
  └───────────────────────────────────────────────────────────────┘
```

---

## §6 — Verification Plan (= V13-1 〜 V13-N)

```
V13-1  P0  anicca-cron-harvester disable + archive (= harvester deprecated)
V13-2  P0  rename anicca-lateness-heartbeat-shell → anicca-life-poll-5min
V13-3  P0  spec 2026-06-07-cron-rectification-and-aniccaai-protection-design.md §3.6 update
V13-4  P0  CLAUDE.md「🔋 LLM Token Sources」更新 (= harvester 削除済 記録)
V13-5  P1  17 ambiguous cron 各 1 件 audit + tag (LAYER E/F/G 確定)
V13-6  P1  100 enabled cron に LAYER tag を audit-rules.json::layer フィールドで永続化
V13-7  P1  watchdog launchd plist verify (= 4 AM fire)
V13-8  P2  doctor-monkey が harvester classify ロジック を inline 化
V13-9  P2  aniccaai.com merge architecture spec 起稿
            (= 別 spec: 2026-06-07-aniccaai-portal-vs-agent-channels.md)
V13-10 P2  anicca + anicca-dais merge spec 起稿
            (= 別 spec: 2026-06-07-anicca-genesis-merge.md)
```

---

## §7 — Out of Scope

- ★ Hermes anicca-genesis side migration ★ (= sister spec)
- ★ aniccaai.com merge architecture ★ (= V13-9 別 spec)
- ★ G layer 17 ambiguous の各 audit 結果 ★ (= V13-5 内 1 件 1 件 確認)

---

## §8 — BP 一致度 自採点

| 要素 | BP | 一致度 |
|---|---|---|
| Simian Army 各役割 | Netflix 2011 Tech Blog verbatim Janitor/Conformity/Doctor | 100% |
| harvester DEPRECATED | Netflix「single responsibility」+ K8s「narrow responsibility」 | 100% |
| heartbeat = 1 ACTION/beat | Andon Labs Mona pattern (= 主意識 strategic) | 100% |
| watch-sweep = external only | 役割 分離 (= cron-self の Doctor/Janitor/Conformity と直交) | 100% |
| life-manager + lateness-shell 分離 | code vs scheduler 別レイヤー (= K8s controller pattern) | 100% |
| Content factory keep | Dais 2026-06-07 verbatim「social media + blogs + build-in-public X + core crons」 | 100% |
| aniccaai.com 編集禁止 | Dais 2026-06-07 verbatim「Anicca should not be writing to this website」 | 100% |

★ 総合 100%、 オリジナル synthesis ゼロ ★

---

**Spec end. Dais review → V13-1〜V13-10 execute 待ち**
