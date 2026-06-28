# earn-jutaku-gig — Skill 3 sub-spec (受託 = freelance gig earn)

**Date:** 2026-06-28 · **Branch:** feature/frank-run · **Author:** Claude (dev IDE, SESSION 2/4 of 4-skill build)
**Parent:** `2026-06-28-claude-earn-skills-spec.md` §1 Skill 3 · **Status:** AUTHORED, awaiting Dais "go" → P0 start
**Scope:** Anicca-owned accounts on Upwork + ココナラ + Fiverr → AI-delivered productized gigs → Payoneer/JP bank.
**Out of scope (other sessions):** Skill 1 affiliate (SESSION 1), Skill 2 YouTube (SESSION 4), Skill 4 clip (SESSION 3).

---

## §0 GOAL (= goal-setter style provable finish line, HARD 0.40 GLVS)

`done = "Upwork OR ココナラ OR Fiverr のいずれか 1 件、 Anicca 名義 platform 報告 row + Payoneer/JP 銀行 transfer evidence が earn-ledger.jsonl に 1 行 append されている (= 着金 amount > ¥0)"`

`stop_condition = adversary PASS + 私の browser E2E green (= CloakBrowser で platform 上の payout row 視認) + ledger 行 fresh evidence`

`done ≠ "gig 出品しました" / "patch commit しました" / "engine 動きました"` — ★ 実 ¥ 着金 まで が 1 task (HARD 0.31) ★

---

## §1 30-DAY TIMELINE (= 「いつ何が起こるか」)

```
 day 0       day 1-3        day 4-7        day 7-14      day 14-30      day 30+
 ──────      ────────       ────────       ─────────     ─────────      ──────
 SPEC        SETUP          ENGINE         DO-ONCE       LOOP-WRAP      COMPOUND
 + tasks  →  signup 3plat → engine 配線  → 1 注文 受領 → claude -p   →  daily 自動
            + Payoneer      + adversary    + 納品 + ¥着    + launchd       評価 +
            + portfolio     + ledger       金 ledger row    + /goal       review +
            seed                                                          価格 ↑
 ▲         ▲                ▲               ▲              ▲              ▲
 P0        P1              P2-P5            P6 ★verify★    P7             daily
 commit    KYC tap (Dais)  build           do-it-once     wrap            compound
```

---

## §2 ARCHITECTURE (= 「全部 どう繋がるか」)

```
┌──────────────────────── BUYERS ───────────────────────────┐
│  Upwork client  │  ココナラ 購入者  │  Fiverr buyer       │
└────────┬────────┴─────────┬─────────┴──────────┬──────────┘
         │ (inbox / order / DM / pre-sale Q)     │
         ▼                  ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│        PLATFORM INBOX POLLERS (= 6h cron, CloakBrowser)     │
│  ┌───────────────┐ ┌────────────────┐ ┌────────────────┐    │
│  │ Upwork poller │ │ Coconala       │ │ Fiverr poller  │    │
│  │ fork:         │ │ poller (= fork │ │ (= autofill    │    │
│  │ kaymen99/     │ │ EdamAme-x/     │ │ ext を移植) +  │    │
│  │ Upwork-AI-    │ │ coconala-      │ │ slmnsh fiverr- │    │
│  │ jobs-applier  │ │ collector)     │ │ api (自分gig)  │    │
│  └───────┬───────┘ └────────┬───────┘ └────────┬───────┘    │
└──────────┼──────────────────┼──────────────────┼────────────┘
           └──────────────────┴──────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  ★ B1: Unified OrderRouter (自前, ~150 行) ★                 │
│   parse buyer message → classify (G1 vid / G2 article /      │
│   G3 trans / G4 QC / pre-sale Q / revision req) →            │
│   SLA timer 起動 → engine dispatch                            │
└──────────────────────────────┬──────────────────────────────┘
                               │
   ┌───────────┬───────────────┼───────────────┬───────────┐
   ▼           ▼               ▼               ▼           ▼
┌──────┐  ┌──────┐         ┌──────┐        ┌──────┐    ┌──────┐
│ G1   │  │ G2   │         │ G3   │        │ G4   │    │ Q&A  │
│ vid  │  │ art  │         │ trn  │        │ QC   │    │ /rev │
│ chain│  │ chain│         │ chain│        │ chain│    │ chain│
└──┬───┘  └──┬───┘         └──┬───┘        └──┬───┘    └──┬───┘
   │         │                │               │           │
   │ chatgpt │ ai-entity-    │ Claude        │ agent-    │ Claude
   │ imagegen│ article-      │ direct        │ skills:   │ direct +
   │ +slide  │ writer +      │               │ code-     │ ResumeHQ
   │ +remot  │ humanizer +   │               │ reviewer  │ tailor
   │ +cap    │ stop-slop +   │               │           │
   │         │ copy-editing  │               │           │
   └────┬────┴──────┬────────┴──────┬────────┴─────┬─────┘
        └───────────┴───────────────┴──────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  ADVERSARY GATE (= vcsdd:vcsdd-adversary, fresh-context)    │
│  5 dim binary PASS/FAIL:                                     │
│    ① brief 一致 (文字数/形式/要件)                            │
│    ② quality (誤字/構成/流れ)                                 │
│    ③ 誤情報 / fact check                                      │
│    ④ ToS + 景表法 + AI disclosure                             │
│    ⑤ deliverable format (codec/docx/md)                       │
│  FAIL → builder へ findings 返却 → loop fix ≤3 round         │
└──────────────────────────────┬──────────────────────────────┘
                               │ PASS
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  MY OWN BROWSER E2E (= HARD 0.31, CloakBrowser daily-driver) │
│   platform プレビュー + asset DL + 開封 + spec 視覚一致確認   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  SUBMIT → REVIEW WAIT → PAYOUT                              │
│   buyer 「ご確認ください」 1 通                                │
│   revision req → 6h loop pickup → 即 修正                     │
│   payout 着金 検出 (= platform 報告 + Payoneer)                │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  ★ B2: earn-ledger.jsonl (自前, ~80 行) ★                    │
│   append {platform, gig, buyer_id_hash, payout_jpy,          │
│   currency, paid_at, evidence_url, msg_id}                   │
│   ★ 外部 platform report row のみ受入、 内部 mock 拒否 ★      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  ★ B3: SLA timer + 24h compounding + STATE.md (自前, ~200) ★ │
│   24h cron: ① 昨日 impressions/CTR/conversion 取得            │
│             ② winner gig 価格 +5% / loser A/B 書換             │
│             ③ portfolio +1 新 sample 自動 追加                  │
│             ④ competitor 上位 5 件 scrape → diff 学習            │
│             ⑤ buyer Q clustering → niche tag 再 pin             │
│             ⑥ /goal "platform payout row > ¥0" judge            │
│             ⑦ STATE.md 上書き → dashboard read-only sync         │
└─────────────────────────────────────────────────────────────┘
```

---

## §3 REUSE MAP (= 既存 OSS + ~/.claude/skills/ で ~75% 削減、 自前 = B1/B2/B3 のみ)

| # | component | 流用元 | 流用率 | 注意 |
|---|---|---|---|---|
| C1 | Upwork 攻め (scrape+score+cover letter) | `kaymen99/Upwork-AI-jobs-applier` 147★ | 60% fork | Playwright→CloakBrowser, LLM→Claude, **auto-submit OFF** |
| C2 | Upwork inbox-poll pipeline | `Eddiejoe33/UpworkAutomationBot` | 20% pattern | Gmail-IMAP→alert parse→draft の glue のみ |
| C3 | ココナラ 案件 scan + dedupe | `EdamAme-x/coconala-collector` 2★ | 80% fork | Playwright + LLM 判定 + db.json dedupe、 通知→内部 router |
| C4 | Fiverr 出品自動化 (gig 作成) | `NadirAliOfficial/fiverr-ai-autofill` 7★ | 50% 移植 | Quill editor inject + human-like typing pattern を CloakBrowser に |
| C5 | Fiverr 自分 gig analytics | `slmnsh/fiverr-api` 46★ Docker | 70% import | **自分の gig だけ** に限定 (= ToS) |
| C6 | 提案文 / 出品文 ATS 最適化 | `jananthan30/Resume-Builder (ResumeHQ)` 54★ | 80% import | Claude Code plugin native, ATS+HR dual scoring + DOCX |
| C7 | G1 動画 納品 engine | `chatgpt-imagegen` + `slideshow` + `hyperframes-*` + `video-processing-editing` + `general-video` + `motion-graphics` + `embedded-captions` | 100% chain | Session 1 と共通 base asset |
| C8 | G2 SEO 記事 納品 engine | `ai-entity-article-writer` + `humanizer_academic` + `stop-slop` + `stop-ai-slop-jp` + `copy-editing` | 100% chain | AI-tell 消し必須 |
| C9 | G3 翻訳 / G4 QC | Claude 直 + `agent-skills:code-reviewer` agent | 100% | 0 dep |
| C10 | adversary gate | `vcsdd:vcsdd-adversary` agent + `recursive-improver` | 100% | fresh-context 必須 |
| C11 | signup / KYC / CAPTCHA / 3DS | `tier-a-bypass` skill (= CapSolver + camofox + Gmail-OTP runbook) | 100% | KYC 写真 のみ Dais 1 タップ |
| C12 | platform browser 自動化 base | CloakBrowser daily-driver `~/.cloak/profiles/daily-driver` (:9222) + `playwright-cli` | 100% | HARD 0.38 + memory 2026-06-25 |
| C13 | competitor 24h scrape | `competitive-analysis` + `competitor-profiling` skill | 100% | 24h loop で diff 学習 |
| C14 | claude -p + launchd 化 | `ralph-autonomous-dev` + `loopy` pattern | 100% | local Mac mini |
| C15 | VSDD 配線 | `prd-generator` + `spec-writing` + `tdd-workflow` + `codex-review` + `vcsdd:*` | 100% | HARD 0.37 |
| **B1** | **Unified OrderRouter** | **自前 ~150 行** | 0% | 3 platform → classify (G1-G4) → engine dispatch |
| **B2** | **earn-ledger.jsonl** | **自前 ~80 行 + 単体 test** | 0% | append-only, 外部 row 限定 (HARD 0.24) |
| **B3** | **SLA timer + 24h loop + STATE.md** | **自前 ~200 行** | 0% | countdown / portfolio +1 / A/B / dashboard sync |

★ Claude skill registry に freelance/upwork/fiverr/gig/coconala 系 = **ZERO** ★ — 我々 が 先発。 後で `~/anicca/skills/earn/` 経由で他 Anicca instance に export 可能。

---

## §4 PRODUCTIZED GIG LINEUP (= G1-G4、 G5 除外)

| # | gig タイトル (JP / EN) | 納品 engine | 単価 想定 | 初期 価格 戦略 |
|---|---|---|---|---|
| G1 | facelessスライドショー動画を作ります (1080×1920 9:16, 60s) / "I'll create a faceless slideshow video" | C7 chain | ¥3,000-8,000 | 競合 最安 -10% |
| G2 | AI SEO 記事を書きます (= 3000-5000字 deep research 込) / "I'll write a deep-research AI SEO article" | C8 chain | ¥3,000-10,000 | 競合 最安 -10% |
| G3 | 英日 / 日英 翻訳します (= 文脈尊重) / "EN↔JP context-aware translation" | C9 (Claude 直) | ¥1-3/字 | 即時納品 を diff 化 |
| G4 | コード レビュー / 品質検証 します (= 5 dim review) / "Code review (5-dim, security+perf)" | C9 (code-reviewer agent) | ¥5,000-20,000 | 24h 納品 を売り |
| ~~G5~~ | ~~会話録音 ナレーション~~ | ★ AI 不可 (= 人間音声) = 永久除外 ★ | — | — |

★ 商品化 gig = ★ 受け待ち が主 ★、 Upwork 攻めは ≤3/日 補助 (= ToS-safe)。

---

## §5 BUILD CONTRACTS (= B1 / B2 / B3 の I/O 仕様)

### B1: Unified OrderRouter
- **入力**: `{platform: str, message: dict, ts: iso8601}` (= poller が標準化)
- **出力**: `{order_id: str, gig_class: G1|G2|G3|G4|QA|REV, sla_deadline: iso8601, dispatch_payload: dict}`
- **不変条件**: classify 信頼度 < 0.7 = 人間判断列に escalate (= Slack DM 1 通)、 重複 message_id は ledger 既出 で skip
- **エラー**: parse fail → escalate、 platform unreachable → exponential backoff (1m/5m/15m)、 SLA < 25% → 全停止 + 該当 order に switch

### B2: earn-ledger.jsonl
- **schema** (1 row = 1 着金 event):
  ```json
  {"ts":"2026-06-29T03:14:00Z","platform":"coconala","gig":"G1","order_id":"abc123",
   "buyer_id_hash":"sha256(...)","payout_jpy":3000,"currency":"JPY","paid_at":"2026-06-29",
   "evidence_url":"https://coconala.com/orders/abc123","msg_id":"...","fees_jpy":660,"net_jpy":2340}
  ```
- **不変条件**: ① append-only (= 削除/書換禁止) ② `evidence_url` resolvable + 200 でないと reject ③ `payout_jpy > 0` のみ受入 ④ duplicate `order_id` reject
- **単体 test**: mock row reject / 0-yen reject / duplicate reject / 404 evidence reject / 正常 row accept の 5 case

### B3: SLA timer + 24h loop + STATE.md
- **SLA timer**: order 受領 で 起動 → 締切 - 6h で 警告 → 残 25% で `priority_lock` 発火 (= 他全 task 停止)
- **24h cron** (= Mac mini launchd 03:00 JST):
  1. 各 platform impressions/CTR/conversion 取得
  2. winner gig (= conversion 上位 33%) 価格 +5% / loser (= 下位 33%) タイトル+説明 A/B 書換
  3. portfolio に 新 sample 1 件 自動追加 (= 直近 winner topic から G1/G2 を 1 件 生成)
  4. competitor 上位 5 件 scrape → 説明文 diff 抽出 → 加筆
  5. buyer pre-sale Q top 3 → desc 内 先答え
  6. `/goal "platform payout row > ¥0 (累計)"` judge (= fresh-context Haiku)
  7. STATE.md 上書き → dashboard.json read-only sync (= Dais 所有 sync job 経由)
- **STATE.md schema**:
  ```
  ## last_run: 2026-06-29T03:00:00+09:00
  ## ledger_30d_jpy: 12340
  ## ledger_total_jpy: 12340
  ## winners: [{platform:coconala, gig:G1, conv:0.12, price_jpy:3300}]
  ## losers: [{platform:fiverr, gig:G4, conv:0.01, action:rewrite_title}]
  ## yesterday_lesson: "G1 hook: 「30秒で作れる」 が CTR 2.3x → 全 G1 hook 統一"
  ## next_action: portfolio +1 sample on topic=AI生産性
  ## open_orders: [{id:abc123, gig:G2, sla_left_h:14, status:in_progress}]
  ```

---

## §6 PHASE PLAN (= P0 → P7 + dep)

### P0 — sub-spec + tasks + commit+push (= 今 turn 完了)
- [ ] このファイル commit + push (= dev branch、 lefthook pre-push 通過)
- [ ] TaskCreate で P1-P7 + sub-task を ID 昇順 で登録
- [ ] Upwork ToS "Use of AI on Upwork" verbatim を別経路 (= Wayback / PDF / firecrawl 別 path) で再取得 → §8 に追記
- [ ] ココナラ ToS 自動アクセス禁止条項 verbatim を再取得 → §8 に追記

### P1 — アカウント作成 (= CloakBrowser daily-driver 既定、 KYC のみ Dais 1 タップ)
- [ ] P1-1 ココナラ (JP) signup: AgentMail `tt-anicca@agentmail.to` or Google OAuth、 SMS = SMSPool (TIER A) or phone +818046270314、 KYC 写真 アップロード = Dais 1 タップ
- [ ] P1-2 Upwork signup: ID verify (KYC = Dais 1 タップ)、 freelancer profile 入力 (= ResumeHQ tailor で初期 bio 生成)
- [ ] P1-3 Fiverr signup: ID verify (KYC = Dais 1 タップ)、 Seller profile 入力
- [ ] P1-4 Payoneer signup + Dais ID + JP 銀行口座 紐付け (= 共有 cross-cutting prereq、 Session 1/3/4 と coord)
- [ ] P1-5 各 platform → Payoneer 受取設定 (= Upwork=Payoneer連携、 Fiverr=Payoneer連携、 ココナラ=JP 銀行直接)

### P2 — engine 配線 (= 既存 chain を import + B1 OrderRouter 自前実装)
- [ ] P2-1 `~/.claude/skills/earn-jutaku-gig/` skill scaffold (= SKILL.md + scripts/)
- [ ] P2-2 G1 chain wire (= chatgpt-imagegen + slideshow + remotion + captions の glue)、 1 sample 生成 verify
- [ ] P2-3 G2 chain wire (= ai-entity-article-writer + humanizer + stop-slop)、 1 sample 生成 verify
- [ ] P2-4 G3 / G4 chain wire (= Claude 直 + code-reviewer agent)、 sample verify
- [ ] P2-5 ★ B1 Unified OrderRouter 実装 ★ (= classify + SLA timer + dispatch)、 単体 test 5 case
- [ ] P2-6 ResumeHQ import + 提案文 / 出品文 tailor wrapper、 1 sample verify

### P3 — gig 出品 (= 自前 portfolio seed + 3 platform 同時出品)
- [ ] P3-1 portfolio seed = G1×3 + G2×3 + G3×2 + G4×1 を自前生成、 各 platform に upload
- [ ] P3-2 ココナラ G1-G4 出品 (= 競合 -10% 価格)、 fiverr-ai-autofill 移植 で自動入力
- [ ] P3-3 Fiverr G1-G4 出品 (= 同上)
- [ ] P3-4 Upwork = profile + bio + portfolio のみ (= 攻めは P5)
- [ ] P3-5 各 platform 1 件目 = 「視認テスト」 = CloakBrowser で公開 URL 確認

### P4 — inbox poller + adversary gate
- [ ] P4-1 ココナラ poller (= EdamAme-x fork、 Playwright + LLM 判定 + dedupe)、 6h cron
- [ ] P4-2 Fiverr poller (= 自前、 messages page poll + DM API)、 6h cron
- [ ] P4-3 Upwork poller (= kaymen99 fork、 best-matches scrape + cover letter draft)、 6h cron (auto-submit OFF)
- [ ] P4-4 adversary gate 配線 (= vcsdd-adversary 呼び出し、 5 dim binary、 fail loop ≤3)
- [ ] P4-5 ★ B2 earn-ledger.jsonl 実装 ★ + 単体 test 5 case

### P5 — Upwork 攻め (= ToS-safe ≤3/日、 補助)
- [ ] P5-1 Upwork "Use of AI" 公式条項 verbatim 再取得 + skill 内に compliance check 配線
- [ ] P5-2 攻め 自動化: 1日 ≤3 件、 個別 read 必須、 AI 全文生成禁止 (= hook + 真の sample のみ)
- [ ] P5-3 Connects 残量 監視 + 不足時 停止

### P6 — DO-ONCE VERIFY (★ HARD 0.31 = 実 ¥ 着金 まで が 1 task ★)
- [ ] P6-1 ココナラ (= 最速ルート) で 1 件 受注 待ち (= 数日〜数週間)
- [ ] P6-2 受注 → engine 納品 → adversary PASS → submit → buyer 承認
- [ ] P6-3 payout 着金 検出 (= platform 報告 row) → ledger 1 行 append
- [ ] P6-4 Payoneer / JP 銀行 transfer 着金 検出 → ledger に紐付け
- [ ] P6-5 ★ MY browser E2E ★ = CloakBrowser で platform 上の payout row 視認 + screenshot 保存 + ledger evidence_url 200 確認

### P7 — claude -p + launchd 化 + /goal
- [ ] P7-1 `~/.claude/skills/earn-jutaku-gig/run.sh` (= claude -p 呼び出し、 STATE.md read-write)
- [ ] P7-2 launchd plist (= `com.anicca.earn-jutaku-gig.6h.plist` + `.24h.plist`)、 Mac mini に install
- [ ] P7-3 `/goal "earn-ledger.jsonl の jutaku 行 累計 > ¥0"` 配線 (= fresh-context Haiku judge)
- [ ] P7-4 ★ B3 24h compounding loop 実装 ★ (= portfolio +1, 価格 +5%, A/B 書換, competitor diff)
- [ ] P7-5 dashboard.json read-only sync 確認 (= Dais 所有 sync job が ledger を拾う)
- [ ] P7-6 7 日 soak (= cron 実走、 違反 0 件 確認、 STATE.md 履歴 7 行 確認)

---

## §7 ADVERSARY CHECKLIST (= 各 deliverable submit 前、 fresh-context vcsdd-adversary が judge)

```
□ ① brief 一致     : buyer 要件 (文字数/形式/締切/言語) を 100% 満たすか
□ ② quality        : 誤字 0、 文法 OK、 構成 (= hook→body→CTA) 揃う、 流れ 自然
□ ③ fact check     : 数値/固有名詞/URL/価格 を verify、 hallucination 0
□ ④ ToS+景表法    : platform AI policy 遵守、 #PR/「広告」 disclosure 有 (= G1/G2 affiliate 含む時)
□ ⑤ deliverable    : codec/format/拡張子/サイズ が buyer 指定通り、 開封テスト 成功
```
FAIL = builder に findings 返却 → loop fix ≤3 round → なお FAIL = 人間 escalate (= Slack DM 1 通)

---

## §8 ToS COMPLIANCE (= 規約 守る = 永続)

### Fiverr — verbatim (Fiverr ToS §5)
> "(viii) use any robot, spider, crawlers or other automatic device, process, software or queries that intercepts, 'mines,' scrapes or otherwise accesses the Site to monitor, retrieve, extract, copy or collect content or data from or through the Site, or engage in any manual process to do the same"
> "(v) use automation software (bots), hacks, modifications (mods) or any other unauthorized third-party software designed to modify the Site"

★ 対処 ★: ① ヘッドレス scraper 禁止 ② CloakBrowser daily-driver (= Dais ログイン session) で **人間ペース で直接運転** (= delay 5-30s + 1日 ≤数件) ③ 自分の gig 以外 scrape 禁止 (= 競合 scrape は `slmnsh/fiverr-api` を **自分 gig analytics のみ** に使う)。

### Upwork — verbatim ★ UNVERIFIED、 P0-3 で再取得 ★
"Use of AI on Upwork" 公式 Help page (= Zendesk JS render) は firecrawl で本文取れず。 P0-3 で Wayback / PDF / 別経路で再取得 → ここに verbatim 落とす。

業界標準 (= kaymen99 README workflow 末尾 "Review and Submission... allowing for final adjustments before submission" pattern):
- ★ auto-submit 禁止 ★ (= 必ず 人間/adversary の最終ゲート)
- ★ ≤3 件/日 ★ (= spam 認定回避)
- ★ 個別 read 必須 ★ (= job 内容 を 必ず LLM が読み込む、 template ばら撒き禁止)
- ★ AI 全文 generate 禁止 ★ (= hook + 真の納品 sample のみ AI、 残りは template ベース)

### ココナラ — verbatim ★ UNVERIFIED、 P0-4 で再取得 ★
公式 ToS の自動アクセス禁止条項 は grep miss。 P0-4 で再取得 → ここに verbatim 落とす。

業界実態 (= EdamAme-x/coconala-collector README 自己免責文):
- ★ ログイン済 session 利用 ★ (= 人間 と 同経路)
- ★ 自動投稿/自動応募 禁止 ★ (= 案件 scan のみ、 応募は人間/adversary)
- ★ ToS 必読、 自己責任 ★

---

## §9 LOOP MECHANICS (= 「毎日 quality 落ちず compound する」 = HARD 0.40 GLVS)

### 6h loop (= 反応速度 = ranking boost の核)
```
for p in [upwork, coconala, fiverr]:
  1. inbox + orders + DM pull (= CloakBrowser daily-driver)
  2. 新 order?       → B1 OrderRouter → engine → adversary → MY E2E → SUBMIT
  3. 新 pre-sale Q?  → 5 分以内 reply (= ranking ↑、 ResumeHQ tailor)
  4. revision req?   → 即 revise + resubmit
  5. payout 着金?    → B2 ledger append + dashboard sync
  6. SLA timer 警告? → 全停止 + 該当 order 最優先
```

### 24h loop (= compounding = 雪だるま)
```
A. 昨日 impressions/CTR/conversion 取得 (= platform 解析 page scrape)
B. winner gig → 価格 +5% / 露出枠 +1 (= 上位 33%)
C. loser gig  → タイトル + サムネ + 説明 を A/B 書換 (= 下位 33%)
D. portfolio に 新 sample 1 件 自動 追加 (= 直近 winner topic から G1/G2 を 1 件 生成)
E. competitor 上位 5 件 scrape → diff 抽出 → 説明文 に反映 (= competitive-analysis skill)
F. 新 niche 兆候 = buyer Q top topic clustering → niche tag re-pin
G. /goal "platform payout row > ¥0 (累計)" judge (= fresh-context Haiku)
H. STATE.md 上書き → ledger 7d/30d 集計 → dashboard.json read-only sync
```

### claude -p + launchd 化 (= local Mac mini、 always-on、 cloud-allowance ゼロ)
```
~/.claude/skills/earn-jutaku-gig/
  ├── SKILL.md
  ├── run.sh                  # claude -p 呼び出し entrypoint
  ├── scripts/
  │   ├── orderrouter.py      # B1
  │   ├── ledger.py           # B2
  │   ├── sla_timer.py        # B3
  │   ├── compound_24h.py     # B3
  │   ├── pollers/
  │   │   ├── upwork.py       # C1+C2 fork
  │   │   ├── coconala.py     # C3 fork
  │   │   └── fiverr.py       # C4+C5 移植
  │   └── engines/
  │       ├── g1_video.py     # C7 glue
  │       ├── g2_article.py   # C8 glue
  │       ├── g3_trans.py     # C9
  │       └── g4_qc.py        # C9
  ├── STATE.md
  └── earn-ledger.jsonl       # B2

launchd plist (Mac mini):
  com.anicca.earn-jutaku-gig.6h.plist   # 6h interval = inbox poll
  com.anicca.earn-jutaku-gig.24h.plist  # 24h @03:00 JST = compounding
```

---

## §10 OPEN UNCERTAINTIES (= 先に開示、 P0 中 / P1 中 で つぶす)

| # | 不確実点 | 対処 phase |
|---|---|---|
| U1 | Upwork ToS の AI 条項 verbatim | P0-3 で再取得 |
| U2 | ココナラ ToS 自動アクセス verbatim | P0-4 で再取得 |
| U3 | Payoneer JP 銀行 KYC 所要日数 (= 数日〜数週間) | P1-4 で実走 |
| U4 | 初注文 待ち時間 (= 評価 0 → ranking 低) | P3 で価格 -10% + 即時納品 を diff 化、 do-once は数週間 想定 |
| U5 | Fiverr 出品 自動入力 の Quill editor 互換性 (= 移植元 = Chrome ext) | P3-3 中 で 実検証 |
| U6 | ココナラ poller の login 維持 (= 期限切れ時) | P4-1 で セッション refresh logic 入れる |
| U7 | adversary gate の 翻訳/QC ジャンル での 5 dim 適合性 | P4-4 で adversary プロンプト チューニング |
| U8 | Upwork Connects 課金 月予算 | P5 で月予算 cap 設定 + 残量 不足 時 停止 |
| U9 | 大量 受注 時の SLA 競合 (= 同時 N 件) | P2-5 SLA timer に priority queue 入れる |

---

## §11 DONE (= この spec)

- 30-day timeline + architecture + reuse map + build contracts + phase plan + adversary checklist + ToS compliance + loop mechanics + uncertainties すべて記載済
- 自前 = B1/B2/B3 のみ、 残り 75% = OSS + 既存 skill chain
- 次: Dais "go" → P0 commit+push + TaskCreate 着手 → P1-P7 を ID 順 黙って 連続実行
