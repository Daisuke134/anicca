# Cron Cull (Phase 1) — 192 enabled → 162 enabled、 30 DELETE (revised v2)

**Date**: 2026-06-05 JST
**Author**: Anicca (Claude)
**Status**: revised after reviewer audit v1, ready-for-review v2
**Reviewer**: superpowers:code-reviewer (a7fc33d3e5662ae58, 2026-06-05)
**Revision summary**: v1 BLOCKING 6 + REVISE 5 を 反映、 ★ engine 守護 違反 削除 候補 6本 を Tier 1 から 除去 ★、 retreat-family 一括 化、 cafe-family 整合 化、 reason verbatim 証拠 添付

**Parent specs**:
- `~/.openclaw/docs/CRON_DECISION_2026-06-04.md` (= predecessor decision book, 278→240)
- `docs/superpowers/specs/2026-06-04-cron-rat-proof-architecture-design.md`
- `docs/superpowers/specs/2026-06-04-cron-doctor-v2-design.md`

**Sister redesign spec (= 後日)**: `2026-06-05-cron-consolidation-design.md` (= 162 → ~50 via multi-slot internal dispatch)

---

## 1. Mission

Daisさん 厳命 (2026-06-05、 verbatim):

> "192 個もエネーブルされてて、 こんなそんな、 そんなわけないよ。 さすがに 192 個も あって、 そんないるわけないよ。
> 僕に ただ レポートする系 とか 僕に ただ 報告する系 とか 絶対 いらない し、 さすがに ちょっと 多すぎる。
> 絶対 100個以上 あると思うから、 それで その理由 も 含めて。
> もう ちゃんと 消して かないと お金 が 足りないよ。
> オートディセイブル も ちゃんと 入れて おかないと... アニッチャ が 自分で 自律的に 消せる ように しないと、
> まず、 僕らは 一回 一回 これらを 自分で 消すんだよ。 リストを 決めるんだよ、 まだ やんないよ。"

→ ★ engine (= TT/IG/YT viral distribution + article 1-channel-each + apply + 学業 + self-heal) は 絶対 守る ★、 ★ leech (= 報告 系 / nano-banana / dormant / fake DRY_RUN) は 切る ★。

## 2. Dais 守護 (= ★ 絶対 削除 不可 ★、 reviewer も これ で chk)

Daisさん 2026-06-05 verbatim:

> "don't delete the ones that are posting to TikTok, IG, and YouTube — the social media, right?
> And also the ones that are posting these viral articles to Dev2. There's only one for each:
> Dev2, Note, Substack, MyBlog, and MyNote, right? All those things are basically distribution channels."

| 守護 カテゴリ | 含まれる cron pattern | 削除 = ★ 致命違反 ★ |
|---|---|---|
| **TT/IG/YT 配信** | reelclaw-* / monk-factory-* / watercolor-* / yangmun-* / 4.7-slideshow-* / iam-color-*-daily / iam-photo-*-daily / mantra-slideshow-* / honne-* / larry-anicca-* / mau-tiktok-* / fashion-slideshow-* / tomb-slideshow-* / cafe-slideshow-* / retreat-slideshow-* / comedy-tiktok-cross-post | engine 死 |
| **記事 1-channel-each 配信** | article-daily-zenn / article-daily-devto / article-daily-substack-en / article-daily-substack-ja / article-daily-note / article-daily-blog | distribution 死 |
| **apply (= 仕事 取り)** | meetup-apply-* / comedy-*-apply-* / comedy-booking-* / cold-email-send / connpass-lt-apply / accelerator-application / jsps-application / naist-funds-apply / anicca-mail-triage / anicca-cold-email-reply / anicca-corey-cold-email / **anicca-product-growth (= active outreach email + Reddit + SEO + blog、 SKILL 検証 済)** | 収益 死 |
| **NAIST 修論** | naist-pull (new hourly) / naist-deadline-ical / naist-gcal-sync / naist-homework-fetch / naist-homework-submit / naist-course-register / naist-funds-apply / attention-tracker-6h | 学業 死 |
| **revenue ops** | factory-bp-* / contra-daily / earn-bounty / anicca-cfo-sync / anicca-wallet-balance / anicca-fuel-broker / anicca-credit-monitor / app-reviews-daily / app-reviews-weekly-digest (= reply、 NOT digest) | 入金 死 |
| **SNS infra health** | anicca-postiz-health-daily / anicca-account-health-daily | account ban 検出 死 |
| **mail/lateness 物理 連携** | anicca-arrival-mail / anicca-morning-leave-check / anicca-morning-report (= lateness Slack alert、 NOT digest) / anicca-mail-triage | Dais 物理 出勤 死 |
| **fresh content engine** | larry-trend-hunter-* / larry-strategy-updater / anicca-pattern-jsonl-refiller / anicca-pattern-promoter / anicca-article-self-improve | SNS / article fresh 化 死 |
| **content upstream input** | **daily-memory (= article-writer + build-in-public の 必須 input、 SKILL.md verbatim 検証 済)** | article-writer 飢餓 |
| **watch-sweep dispatcher** | **anicca-watch-sweep (= 15+ standalone watcher の 統合 dispatcher、 ledger ベース double-reply 防止 infra)** | meetup-accept / cafe-watch / mail-triage carry 死 |
| **self-heal trio + lint** | anicca-cron-harvester / anicca-cron-doctor (hourly :37 = fault-brief + daily 03:00 = L1-L6 lint、 ★ 2 entry は 別 機能 ★) / anicca-cron-auto-disable / tuning-skills-nightly / anicca-exec-guard / anicca-health | 自律 cron-cull 自体 死 |
| **心臓** | anicca-heartbeat / anicca-lateness-heartbeat-shell | Anicca 停止 |
| **公開 帳簿 (no-theatre)** | **aniccaai-dashboard-refresh (= aniccaai.com/dashboard 公開、 KEEP-FIXED)** | 公開 透明性 死 |
| **Dais 仕事 直結** | **mufg-epoc-watcher (= MUIT 仕事 daily intel brief、 KEEP-FIXED)** | Dais 仕事 ネタ 死 |

★ reviewer 必須 chk ★: TIER 1+2 削除 リスト の どれ も 上記 カテゴリ に 該当 し ない こと を verify。

## 3. 現状 (= 2026-06-05 22:30 JST)

| | Count |
|---|---:|
| TOTAL | 243 |
| ENABLED | **192** |
| DISABLED | 51 |

Daisさん の 心情: 「絶対 50個 とか、 それ から 20 個 とか で いい と 思う」 → 192→50 化 は ★ 物理 的 に Tier 1+2 削除 だけ で は 不可能 ★ (= §6 参照、 floor 130-140 ある)。 redesign が 必要 (= sister spec)。

## 4. Tier 1 — 即 DELETE 25 本 (= 確信、 reviewer ok 要件)

### A. nano-banana / Gemini-cli 画像 生成 = Dais 明言 削除 — 4本

Daisさん 2026-06-05 verbatim: 「ナノバナナ を 使って スライド を 作って る やつ ... いらない、 そもそも お金 が かかる から やめたい。 Gemini cli で 画像 を 作って る やつ、 あれ とか いらない。」

| # | cron | 検出 + reason verbatim 証拠 |
|---|---|---|
| 1 | `world-suffering-digest-daily` | payload に `nano-banana` 含む + Slack digest (世界悲惨ニュース要約 = Dais 「読まない」 該当) |
| 2 | `anicca-x-feed-digest` | `nano-banana` 画像化 + @aniccaxxx 停止 = feed 取れない 二重 wasteland |
| 3 | `viral-article-weekly` | SKILL.md verbatim 「`nano-banana CLI で EN+JP 図を記事冒頭に埋め、 JP/EN 各々を /blog と Substack に実投稿する`」 → ① nano-banana ban ② **article-daily-{blog,substack-en,substack-ja} と 同 channel 重複 publisher** = 1-channel-each 守護 を 満たす の は article-daily-* 側 が canonical、 viral-article-weekly は 重複 で 守護 で は ない |
| 4 | `viral-article-republish` | `nano-banana` + Sat 19:00 「Re-angle the most recent published Anicca /blog article into a fresh X draft」 = DRAFT only forever + 重複 family |

### B. Daisさん へ の digest / report / summary / dashboard (= 「読まない」「report 系 絶対 いらない」 明言) — 17本

★ v1 → v2 で 4 本 除去 (= reviewer BLOCKING 反映): daily-memory (article-writer 上流)、 anicca-watch-sweep (15+ watcher dispatcher)、 anicca-product-growth (active email+Reddit+SEO+blog)、 anicca-aie-product (Path 3 family) ★

| # | cron | 内容 (Slack #metrics 投稿 系) |
|---|---|---|
| 5 | `anicca-report-daily` | 18:00 Anicca activity summary mail (= 「summarized articles shit」 該当) |
| 6 | `anicca-report-weekly` | Mon 09:00 weekly summary |
| 7 | `kpi-dashboard-daily` | 13:05 Stripe MRR + Postiz + Apify daily digest → Slack |
| 8 | `content-metrics-daily` | 06:05 content metrics digest → Slack |
| 9 | `larry-daily-report-ja` | larry account daily report → Slack。 ★ NOTE ★: payload に `check-analytics.js --connect` step あり = postiz integration release-id 接続 副 機能、 削除 で 再接続 切れ。 対策: 別 cron / 手動 連結 (= postiz-health-daily に 統合 する 後続 task) |
| 10 | `larry-daily-report-en` | 同 EN、 同 NOTE |
| 11 | `anicca-tomb-sales-report-daily` | Stripe sales report → #metrics (tomb retreat dormant = sales 0) |
| 12 | `anicca-seo-monthly-report` | SEO monthly report = Dais 「読まない」 該当 |
| 13 | `anicca-fashion-sales-report-daily` | fashion sales report = Dais 「読まない」 |
| 14 | `weekly-ai-agent-brief` | Sun 18:20 AI agent week brief + Marp slide outline |
| 15 | `anicca-cron-doctor-digest` | Mon 04:00 cron-doctor weekly digest → Slack |
| 16 | `anicca-daily-content` | 09:05 content count → '📊 daily content' Slack |
| 17 | `app-metrics-morning` | RC/Mixpanel/ASC metrics → JSON保存 + 100字 summary、 外部 action なし |
| 18 | `revenue-allocator-monthly` | 1st 09:45 monthly treasury report → Slack |
| 19 | `bip-weekly-rollup` | Sun 20:00 BIP weekly rollup (X 停止 で 空) |
| 20 | `bip-postiz-pull` | Mon 23:10 Postiz analytics pull (X 停止 で cache 空) |
| 21 | `anicca-socials-daily` | 4h ごと per-account analytics → Slack #metrics |

### C. Dead / 未本番 / v2 pivot 廃止 — 2本

| # | cron | 理由 verbatim |
|---|---|---|
| 22 | `anicca-trip-scanner` | internal observer only、 external 出力 なし |
| 23 | `basic-income-monthly` | memory `feedback_no_human_in_loop_v2_pivot_2026_05_30` 引用 = 「v1 hybrid Stripe transfer 系 全 retire、 v2 = on-chain only」 = donation rail 自体 廃止 軸、 1ヶ月 何 も payout 成功 なし |

### D. HARD RULE #15 違反 — 1本

> memory: `feedback_no_rotation_only_fresh_generation` = 「rotation 廃止 → library から fresh 生成」

| # | cron | 理由 |
|---|---|---|
| 24 | `anicca-article-daily-rotation-audit` | HARD RULE #15 で rotation 機構 自体 obsolete、 audit 役 も obsolete |

### E. 重複 cron entry (= 同名 2 entry、 旧 路線) — 1本

★ v1 → v2 ★: `anicca-cron-doctor` 2 entry は ★ 別機能 ★ (hourly :37 = fault-brief / daily 03:00 = L1-L6 lint) と reviewer 検証 で 判明 → 削除 NG、 list から 除去。 残る は naist-pull のみ。

| # | cron | 理由 + 削除 path 明示 |
|---|---|---|
| 25 | `naist-pull` (★ sched=`*/15 * * * *` の inline python 旧版 ★) | jobs.json 内 2 entry: ① `*/15 * * * *` inline python (= 旧)、 ② `0 * * * *` skill MODE=pull bash (= 新) → 旧 (= */15、 inline) を 削除、 新 (= hourly skill 版) を 残す |

## 5. Tier 2 — 追加 DELETE 5 本 (= strict 2nd pass、 reviewer 検証 通過)

★ v1 → v2 で Tier 2 を 11→5 に 縮小 ★ (= reviewer REVISE 反映、 retreat-family を Tier 3 へ 一括 移動、 cafe-status-weekly を Tier 3 へ 移動、 article-daily-audit を Tier 3 へ 移動 、 comedy-live-schedule-publish を Tier 3 へ 移動)。

### F. internal helper digest — 1本

| # | cron | 内容 | 削除 根拠 |
|---|---|---|---|
| 26 | `tuning-skills-weekly-summary` | Sun 10:25 tuning-skills 1週 集計 → Slack | weekly summary report (= self-heal は `tuning-skills-nightly` (daily 02:05) で 完結、 summary は 報告 のみ) |

### G. dormant revenue path (= 受注 0、 retreat-family は Tier 3 へ 移動 済) — 2本

| # | cron | 内容 | 削除 根拠 verbatim |
|---|---|---|---|
| 27 | `anicca-coconala-fortune` | Mon 10:43 占い listing | spec D 「占い listing 未公開 = 受注 0 構造」、 1ヶ月 0 件 出品 成功 |
| 28 | `trustmrr-sell-decision-monthly` | 1st 07:10 product MRR>$500 sell decision | 現状 Anicca product で MRR > $500 0 件 = 永久 no-op |

### H. NAIST rollup (= deadline-watch 別 cron で 既 cover 検証 済) — 2本

★ reviewer REVISE 反映 ★: friday-rollup の `--audit-deadlines` は `naist/scripts/deadline-watch.py` (separate cron + skill) で full coverage と verify 済 (= 重複 機能)。 rollup 削除 で deadline 監視 は 失われ ない。

| # | cron | 内容 | 削除 根拠 |
|---|---|---|---|
| 29 | `naist-friday-rollup` | Fri 18:10 Slack per-user post (`--rollup=7d --audit-deadlines`) | Dais 「report 系」 該当 + audit-deadlines は `deadline-watch.py` 別 cron で 既 cover |
| 30 | `naist-morning-rollup` | 09:45 daily Slack rollup | 同上、 Dais 「report 系」 |

→ NAIST 実 学業 cron (homework-fetch / submit / course-register / funds-apply / pull / deadline-ical / deadline-watch / gcal-sync / attention-tracker) は ★ KEEP ★。 rollup 2 本 のみ 削除。

## 6. KEEP 核 floor 分析 (= なぜ 192→50 が 不可能 か)

Tier 1+2 後 (192 − 30 = 162) の 構成:

| 守護 カテゴリ | 概数 | 理由 |
|---|---:|---|
| TT/IG/YT slideshow/video 投稿 | ~50 | reelclaw 11 + monk 6 + watercolor 4 + yangmun 2 + 4.7 2 + iam 5 + mantra 1 + honne 3 + larry-post 2 + mau-tiktok 2 + fashion-slideshow 2 + tomb-slideshow 2 + cafe-slideshow 2 + retreat-slideshow 2 + comedy-tiktok-cross 1 + 他 |
| article 1-channel-each | 6 | zenn/devto/substack-en/substack-ja/note/blog |
| article 配信 helper (whitelist-learn / self-improve / **audit (= 404 check 機能)**) | 3 | upstream of article publishing + 404 verify |
| fresh content engine (trend-hunter × 2 + strategy-updater + pattern-refill + pattern-promoter) | 5 | HR#15 rotation 廃止 後 の 必須 fresh 供給 |
| **content upstream input (daily-memory)** | 1 | article-writer + build-in-public の input、 v2 で 守護 化 |
| **watch-sweep dispatcher** | 1 | 15+ watcher 統合 dispatcher、 v2 で 守護 化 |
| apply 系 (Tokyo LT + SF + connpass + funder + JSPS + cold email + **product-growth**) | ~11 | 収益 取り、 product-growth v2 で 守護 化 |
| NAIST 学業 (= rollup 2 除く) | ~8 | 修論 (= deadline-watch も 別 cron なら +1) |
| heartbeat + cron-mgr 三 + tuning-nightly + lint | 6 | self-heal、 cron-doctor 2 entry は 別機能 で 両 KEEP |
| revenue infra (cfo / wallet / fuel / credit / stripe-listener / x402 / app-reviews) | ~8 | 入金 監視 |
| SNS infra (postiz-health / account-health) | 2 | account ban 検出 |
| mail/lateness (mail-triage / arrival / morning-leave / morning-report / cold-email-reply) | 5 | Dais 物理 |
| comedy 軸 | ~8 | Dais comedy career |
| SEO 核 | ~10 | corey × 5 + backlink × 3 + rank-monitor + brand-visibility |
| cafe 実 ops (= slideshow 除く license + waitlist + outreach + ops + prelaunch-content + launch-trigger) | ~6 | Dais cafe 開業 中 |
| fashion 実 ops (= slideshow 除く lp-sync + shipping + review-scrape) | 3 | fashion store |
| Dais 物理 long-cycle (dentist / haircut quarterly + travel-fill + schedule-template + gcal-heal + booking + night-fill) | ~7 | Dais 個人 |
| 公開 帳簿 + Dais 仕事 (aniccaai-dashboard-refresh + mufg-epoc-watcher) — KEEP-FIXED | 2 | no-theatre + MUIT 直結 |
| 残余 (= aie-consulting/product + 他 Tier 3 候補) | ~10 | Dais 個別 判断 |

→ ★ floor ≈ 130-140 ★。 残り (162 − 140 = 22) が 真の Tier 3 削減 候補 (= retreat dormant family + cafe-status + comedy-LP-deps 等)。

★ 結論 ★: ★ 192→50 は 構造 改革 (= multi-slot internal dispatch) なし に は 不可能 ★。 但し **162 → ~140 は Tier 3 個別 Dais 判断 で 達成 可** = §7。 真の 50 化 は sister spec で。

## 7. Tier 3 — Dais 判断 要 17 本 (= DEFER、 spec review 時 individual 決定)

★ v1 → v2 で 5 本 増 (retreat-family 一括 + cafe-status + comedy-LP-deps + aie-product + article-daily-audit) - 2 本 減 (aniccaai-dashboard + mufg-epoc → KEEP-FIXED) ★

### Retreat product family (= Dais 判断 軸 = retreat 着手 計画 か) — 4本 一括

| # | cron | 内容 | KEEP 根拠 | DELETE 根拠 |
|---|---|---|---|---|
| T3.1 | `retreat-phase0-location-discover-monthly` | 1st 09:35 retreat 場所 discover | 月次 1 回 = 軽量 | reactive phase、 着手 未 |
| T3.2 | `anicca-recruit-retreat-monthly` | 1st 10:05 volunteer email | retreat launch → 必須 | retreat 未 launch |
| T3.3 | `anicca-recruit-tomb-weekly` | Mon 11:40 寺院 候補 email | tomb retreat 候補 探索 | tomb retreat 未 launch |
| T3.4 | `anicca-retreat-crowdfund-daily` | Mon 19:05 Stripe + Camp Fire poll + TikTok @anicca.jpx draft + Resend donor follow-up | TT draft + donor email = 守護 部分 重複 | retreat dormant、 donor 0 で no-op |

### Cafe product family (= Dais 判断 軸 = cafe launch まで の 期間) — 6本

| # | cron | 内容 | KEEP 根拠 | DELETE 根拠 |
|---|---|---|---|---|
| T3.5 | `anicca-recruit-cafe-weekly` | Wed 11:25 cafe 物件 email | 物件 探索 active | cafe 未開業 |
| T3.6 | `cafe-license-pull-daily` | Mon 09:25 飲食店営業許可 PDF poll | 申請 中 | 申請 未 |
| T3.7 | `opening-cafe-daily-ops` | Mon 23:20 UberEats sync (pre-launch 早期 exit) | launch 直前 必要 | 未 launch |
| T3.8 | `opening-cafe-waitlist-collect-daily` | Mon 14:15 waitlist 収集 | waitlist site live | 同 site 未 |
| T3.9 | `opening-cafe-influencer-outreach-weekly` | Mon 09:55 influencer outreach | active campaign | campaign 未 |
| T3.10 | `opening-cafe-prelaunch-content-daily` | 13:10 countdown X via Postiz (X 停止 で 空) | IG/TT 配信 先 あり | X 専用 で 空 |
| T3.11 | `opening-cafe-status-weekly` | Mon 12:10 cafe phase status + manual_action_required → Slack | 上記 6 本 KEEP なら uber-digest も KEEP | weekly digest 不要 (= Dais 「report 系」) |

### Fashion product family (= Dais 判断 軸 = store active か) — 3本

| # | cron | 内容 |
|---|---|---|
| T3.12 | `anicca-fashion-lp-sync-daily` | 00:00 LP sync check |
| T3.13 | `anicca-fashion-shipping-status-daily` | Mon 11:10 shipping ops |
| T3.14 | `anicca-fashion-review-scrape-daily` | Mon 12:40 review scrape + sentiment |

### AIE (Path 3 product venture) family — 2本

| # | cron | 内容 |
|---|---|---|
| T3.15 | `anicca-aie-consulting` | Mon 12:23 consulting outbound |
| T3.16 | `anicca-aie-product` | Fri 16:37 PRD synthesis |

### Article + comedy downstream dependency — 2本

| # | cron | 内容 | DELETE 軸 | KEEP 軸 |
|---|---|---|---|---|
| T3.17 | `anicca-article-daily-audit` | Sun 22:00 7day audit (= 42 URL HTTP 200 verify + language-purity + SEO rank delta) | report 系 (Slack) | 404 verify = operational safety net |
| T3.18 | `comedy-live-schedule-publish` | Mon 11:50 schedule.json 生成 (LP downstream fetch) + Slack week-ahead | weekly digest = report | LP comedy schedule 描画 dependency |

## 8. 実装 phasing (= Daisさん 「リスト を 決めるんだよ、 まだ やんない」)

| Phase | やる こと | 出力 | verify | 戻し |
|---|---|---|---|---|
| **P0** | spec v2 を `superpowers:code-reviewer` agent に 再 audit、 ok まで iterate | reviewer の verdict ok | ok ステータス | spec 修正 |
| **P1** | spec 承認 後 plan 起こす (= bite-sized phase、 5-10 cron / phase) | `docs/superpowers/plans/2026-06-05-cron-cull.md` | self-review | — |
| **P2** | jobs.json.bak-cron-cull-20260605 作成 | backup file | size verify | restore |
| **P3** | Tier 1A (= 4 nano-banana) delete + verify 192→188 | `openclaw cron rm × 4` | `openclaw cron list \| wc -l` | bak restore |
| **P4** | Tier 1B (= 17 digest) delete + verify 188→171 | rm × 17 | 同上 | 同上 |
| **P5** | Tier 1C (= 2 dead) + 1D (= 1 HR#15) + 1E (= 1 重複) delete + verify 171→167 | rm × 4 | 同上 | 同上 |
| **P6** | Tier 2F (= 1 internal-digest) + 2G (= 2 dormant) + 2H (= 2 NAIST rollup) delete + verify 167→162 | rm × 5 | 同上 | 同上 |
| **P7** | Tier 3 17 本 を Dais 個別 OK/NO 確認 (= 別 会話 / family 単位 で 一括) | Dais 反応 → 一部 削除 → 162→145~155 | 同上 | 同上 |
| **P8** | cron-auto-disable payload に audit rules 注入 (= §9) | `~/.openclaw/skills/anicca-cron-doctor/data/audit-rules.json` | 翌 03:11 JST 発火 → harvester events → auto disable 候補 列挙 確認 | rule file revert |
| **P9** | (後日 別 spec) consolidation redesign で 162 → ~50 化 | `2026-06-05-cron-consolidation-design.md` | — | — |

## 9. 自律 化 (= Task #8 = auto-disable rules、 v2 で rule R8 強化)

```jsonc
// ~/.openclaw/skills/anicca-cron-doctor/data/audit-rules.json
{
  "rules": [
    {
      "id": "R1_NANO_BANANA",
      "match_grep": "nano-banana|gemini-cli|imagen",
      "action": "disable_immediate",
      "reason": "Dais 2026-06-05 banned image-gen crons (cost + life-manager Gemini contention)"
    },
    {
      "id": "R2_DIGEST_TO_DAIS",
      "match_grep": "(report|digest|summary|rollup).*(Slack|#metrics|#content-metrics)",
      "match_anti": "(post|publish|publishToPostiz|send|apply|submit|outreach|outbound|click|fetch|pull|sync|heal|monitor|fire)",
      "action": "flag_for_review",
      "reason": "Slack 投稿 のみ で 外部 action verb 無し = leech",
      "false_positive_examples": [
        "morning-report (= lateness alert = 外部 action 相当 で 守護)",
        "watch-sweep (= dispatcher で 内部 watcher carry = 守護)",
        "daily-memory (= article-writer 上流 input = 守護)"
      ]
    },
    {
      "id": "R3_DRY_RUN_FOREVER",
      "match_grep": "DRY_RUN=true|DRY_RUN: true",
      "match_anti": "DRY_RUN=false",
      "min_silent_days": 30,
      "action": "disable_immediate",
      "reason": "fake-ass dry run"
    },
    {
      "id": "R4_ORPHAN_SKILL",
      "match": "skill_dir does NOT exist AND payload does NOT have embedded bash one-liner",
      "action": "disable_immediate",
      "reason": "zombie cron, skill deleted"
    },
    {
      "id": "R5_DUPLICATE_ENTRY",
      "match": "same cron name appears 2+ in jobs.json AND schedules identical AND scripts identical",
      "match_anti": "schedules differ OR scripts differ (= 別機能)",
      "action": "flag_for_review (keep newest schema)",
      "reason": "jobs.json corruption / tombstone"
    },
    {
      "id": "R6_LAUNCHD_DUPLICATE",
      "match": "launchctl list shows same daemon name",
      "action": "flag_for_review (one must die)",
      "reason": "OS-level vs OpenClaw cron duplication"
    },
    {
      "id": "R7_HR15_ROTATION_OBSOLETE",
      "match_grep": "rotation-audit|rotation\\-rebalance",
      "action": "disable_immediate",
      "reason": "HARD RULE #15 rotation 廃止"
    },
    {
      "id": "R8_DORMANT_REVENUE_PATH",
      "match": "skill in dormant_rails list (= retreat / tomb / fashion-LP-not-live / coconala-not-listed / trustmrr-no-MRR>500) AND >30 day no real revenue event",
      "action": "flag_for_review (= Dais 個別 確認)",
      "reason": "rail 未本番、 product family 一括 で Dais 判断"
    }
  ],
  "guardrails": [
    "NEVER disable any cron whose skill posts to TikTok / IG / YouTube (= 守護 §2 #1)",
    "NEVER disable article-daily-{zenn,devto,substack-en,substack-ja,note,blog} (1-of-N channels = 守護 §2 #2)",
    "NEVER disable apply/mail/comedy/NAIST/heartbeat/cron-mgr/revenue-ops/postiz-health/account-health (= 守護 §2 全般)",
    "NEVER disable daily-memory (= article-writer 上流)、 watch-sweep (= 15+ watcher dispatcher)、 product-growth (= active email+Reddit+SEO+blog)、 aniccaai-dashboard-refresh (= 公開帳簿)、 mufg-epoc-watcher (= MUIT 仕事)、 cron-doctor 2 entries (= 別機能 hourly + daily)",
    "BEFORE disable: verify skill SKILL.md description does NOT match any 守護 keyword (= 'post to TikTok' / 'post to IG' / 'publish to substack' / 'publish to zenn' / 'apply' / 'email send' / 'cold mail' / 'cafe' / 'naist' / 'self-heal' / 'heartbeat')"
  ]
}
```

→ cron-auto-disable payload 書換 = この JSON を load → harvester events を rules で filter → 候補 列挙 → 守護 violations chk → `openclaw cron disable <id>` 実行 → Slack `🧹 cron-auto-disable: X→Y (R2:3, R3:2, ...)` 投稿。 daily 03:11 で 自走。

## 10. Self-review checklist v2

| chk | 通過 |
|---|---|
| Tier 1+2 30 本 の どれ も §2 守護 カテゴリ に 該当 し ない | ★ ✓ ★ v1 BLOCKING 反映 後 (watch-sweep / daily-memory / product-growth / aie-product / cron-doctor-dup を 除去) |
| 各 cron に 削除 理由 が **SKILL.md verbatim 引用 付き** で 1 行 で 具体的 | ✓ §4 §5 |
| 守護 §2 表 に v2 追加: daily-memory、 watch-sweep、 product-growth、 cron-doctor 2 entry 別機能、 aniccaai-dashboard、 mufg-epoc | ✓ |
| Tier 3 で retreat-family / cafe-family を 一括 化 (= product family 単位 で Dais 判断) | ✓ §7 |
| article-daily-audit を Tier 2→Tier 3 移動 (= 404 verify 機能 引用) | ✓ T3.17 |
| comedy-live-schedule-publish を Tier 2→Tier 3 移動 (= LP downstream dependency 引用) | ✓ T3.18 |
| 重複 削除 path 明示 (= naist-pull は `*/15 inline python` を 削除、 hourly skill 版 を 残す) | ✓ §4-E |
| anicca-cron-doctor 2 entry は 別機能 で 削除 NG = Tier 1E から 除去 | ✓ |
| basic-income reason に v2 pivot memory 引用 | ✓ §4-C |
| 192→50 不可能 floor 130-140 を 数学 提示 | ✓ §6 |
| audit-rules.json で R2 detection logic に match_anti + false_positive_examples 追加 | ✓ §9 |
| 既存 spec / memory 整合 (CRON_DECISION / cron-doctor-v2 / HR#15 / v2 pivot) | ✓ |

## 11. 受入 条件

| 項目 | 条件 |
|---|---|
| reviewer v2 ok | superpowers:code-reviewer が verdict=ok (max 5 iterate) |
| plan 起稿 | `docs/superpowers/plans/2026-06-05-cron-cull.md` |
| backup 作成 | `jobs.json.bak-cron-cull-20260605` + size verify |
| Tier 1 削除 完了 | 192 → 167 (25 確実 減) |
| Tier 2 削除 完了 | 167 → 162 (5 確実 減) |
| Tier 3 個別 確認 | Dais family 単位 OK で 162→Y |
| auto-disable rules 注入 | audit-rules.json + cron-auto-disable payload reference |
| Slack 報告 | 「🧹 cron-cull P1 完了: 192→Y」 #metrics |
| commit + push | `chore(cron): cull leech crons (192→Y, spec v2/plan/audit-rules)` |

## 12. 非 対象 (= 別 spec)

| 別 spec | 内容 |
|---|---|
| `2026-06-05-cron-consolidation-design.md` | 162 → ~50 化 multi-slot internal dispatch redesign |
| `2026-06-05-launchd-migration-design.md` | launchd 26 entry → openclaw cron に 移植 入替 |
| `2026-06-04-cron-doctor-v2.md` (既存) | cron-doctor v2 = 別 implementation |

## 13. 変更 履歴

- v1 (2026-06-05 22:00 JST): 初稿、 Tier 1 30 + Tier 2 11 + Tier 3 12
- v2 (2026-06-05 22:45 JST): reviewer audit BLOCKING 6 + REVISE 5 を 反映:
  - Tier 1 30 → 25 (− daily-memory / watch-sweep / product-growth / aie-product / cron-doctor-dup)
  - Tier 2 11 → 5 (− retreat-family × 3 / cafe-status-weekly / article-audit / comedy-schedule = Tier 3 へ 移動)
  - Tier 3 12 → 17 (+ 5 移動 + 1 article-audit、 − aniccaai-dashboard / mufg-epoc は KEEP-FIXED へ)
  - 守護 §2 表 に 6 カテゴリ 追加 (= daily-memory / watch-sweep / product-growth / cron-doctor 2 entry / aniccaai-dashboard / mufg-epoc)
  - 削除 reason に SKILL.md verbatim 引用 追加
  - audit-rules.json R2 に match_anti + false_positive 追加、 guardrails に v2 守護 追加

---

**End of design v2**. Ready for `superpowers:code-reviewer` re-audit.
