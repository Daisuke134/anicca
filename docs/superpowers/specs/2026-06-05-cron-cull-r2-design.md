# Cron Cull Round 2 — 162 enabled → 157、 5 DELETE + 4 corey payload fix + 1 skill restore (v2 revised)

**Date**: 2026-06-05 JST
**Author**: Anicca (Claude)
**Status**: revised after reviewer v1 audit, ready-for-review v2
**Reviewer**: superpowers:code-reviewer (a54bb0509898dac4c)
**Revision summary**: v1 BLOCKING 7 反映 (corey 4 zombie 誤判定 → payload fix path、 retreat-crowdfund + fashion-lp-sync 救出 fabricated → DELETE 移動、 night-fill skill MISSING → restore task 追加)

**Parent specs**:
- `docs/superpowers/specs/2026-06-05-cron-cull-design.md` (R1: 192→162、 30 DELETE)

---

## 1. Mission (= unchanged v1 §1、 Dais 2026-06-05 verbatim)

life-manager (C) を 「ANY-TIME on-time + self-improve」 に 拡大、 apply-and-fill-and-remind chain (D) を 「lead-to-ideal-self loop」 に 拡大。

## 2. R1 守護 §2 + R2 拡大 (v2 で 修正)

★ v2 追加 ★: 守護 (I) fresh content engine + LP edit + git push 軸 に 「**~/.openclaw/skills/anicca-corey-{prog-seo,schema-markup,page-cro,seo-audit,ai-seo}** = LP HTML 編集 + git push + GitHub issue + Slack alert」 を 明示 行 追加 (= reviewer NEW CONSIDER C2 反映)。

| カテゴリ | 含まれる cron | v2 追加 |
|---|---|---|
| (A) TT/IG/YT 配信 | reelclaw-* / monk-factory-* / watercolor-* / yangmun-* / 4.7-slideshow-* / iam-color-* / iam-photo-* / mantra-slideshow-* / honne-* / larry-anicca-* / mau-tiktok-* / fashion-slideshow-* / tomb-slideshow-* / cafe-slideshow-* / retreat-slideshow-* / comedy-tiktok-cross-post / anicca-music-daily / anicca-music-stockmusic-batch-daily | — |
| (B) article 1-channel-each | anicca-article-daily-{zenn,devto,substack-en,substack-ja,note,blog} | — |
| (C) life-manager call infra | anicca-lateness-heartbeat-shell (/5) / anicca-arrival-mail (/5) / anicca-morning-leave-check / anicca-morning-report / anicca-night-fill / anicca-event-bot-trigger / anicca-heartbeat / anicca-gcal-heal / anicca-travel-fill / anicca-schedule-template / anicca-haircut-quarterly / anicca-dentist-quarterly / anicca-booking-daily | — |
| (D) apply-and-fill-and-remind chain | connpass-lt-apply-daily / anicca-meetup-apply-{tokyo,sf}-* / anicca-meetup-discover-daily / comedy-{tokyo-mic,sf}-apply-* / anicca-comedy-weekly-book / comedy-booking-en-dais-SF-monthly / comedy-live-discover-monthly / comedy-live-schedule-publish / accelerator-application-monthly / jsps-application-monthly / anicca-cold-email-send / anicca-corey-cold-email-daily / anicca-mail-triage / anicca-cold-email-reply / anicca-product-growth / anicca-recruit-{cafe,retreat,tomb,comedy}-* / opening-cafe-prelaunch-content-daily (= L 端) | ★ v2 で retreat-crowdfund-daily と fashion-lp-sync-daily を 除去 (= 救出 fabricated 訂正) ★ |
| (E) NAIST 修論 | naist-pull / naist-deadline-ical / naist-gcal-sync / naist-homework-fetch / naist-homework-submit / naist-course-register / naist-funds-apply / attention-tracker-6h / latest-papers / auto-research-e2e | — |
| (F) revenue ops | factory-bp-* / contra-daily / anicca-earn-bounty / anicca-cfo-sync / anicca-wallet-balance / anicca-fuel-broker / anicca-credit-monitor / app-reviews-daily / app-reviews-weekly-digest / daily-letter-sender / weekly-fresh-letter / anicca-capafy-daily-publish | ★ v2 で retreat-crowdfund-daily 除去 (= 救出 fabricated 訂正) ★ |
| (G) SNS infra health | anicca-postiz-health-daily / anicca-account-health-daily | — |
| (H) self-heal + heartbeat | anicca-cron-harvester / anicca-cron-doctor (= 2 entry 別機能) / anicca-cron-auto-disable / tuning-skills-nightly / anicca-exec-guard / anicca-health / anicca-pattern-promoter / anicca-pattern-jsonl-refiller / anicca-disk-hourly | — |
| **(I) fresh content engine + LP edit + git push 軸 (v2 で 拡大)** | larry-trend-hunter-en/ja / larry-strategy-updater / anicca-article-self-improve / anicca-article-daily-whitelist-learn / copy-viral-format-factory-3day / **~/.openclaw/skills/anicca-corey-{prog-seo,schema-markup,page-cro,seo-audit,ai-seo}** (= ★ v2 で 5 本 一括 KEEP、 4 本 は payload path 修正 ★) | ★ v2 で 4 本 zombie 誤判定 訂正 + payload fix path に 移行 ★ |
| (J) content upstream + dispatcher | daily-memory / anicca-watch-sweep / oss-repo-observer-daily / anicca-backlink-{reddit,hn,ih}-* | — |
| (K) KEEP-FIXED | aniccaai-dashboard-refresh / mufg-epoc-watcher | — |
| (L) cafe SNS posting | opening-cafe-cross-post-daily / anicca-cafe-slideshow-daily / anicca-cafe-slideshow-ja-daily / opening-cafe-prelaunch-content-daily | — |
| (M) seasonal/rare physical | anicca-haircut-quarterly / anicca-dentist-quarterly | — |

## 3. 現状 (= 2026-06-05 01:30 JST、 R1 完了 + R2 v2 spec 起稿 中)

| | Count |
|---|---:|
| ENABLED | **162** |

## 4. R2 v2 Tier 1 — 即 DELETE 5 本 (= v1 9本 → v2 5本、 reviewer ok 想定)

### A. Internal observer + Slack report のみ (= 外部 action verb ゼロ) — 4本

| # | cron | sched | 内容 verbatim | 根拠 |
|---|---|---|---|---|
| 1 | `anicca-seo-competitor-monitor-monthly` | 1st 06:00 | Calm/Headspace/Insight Timer/IAm App/Bond AI top 20 keywords を Firecrawl scrape → competitor-YYYY-MM.json + Slack top 5 keyword opportunities | ★ 月次 report + state JSON のみ ★、 守護 (I) は 別 5 corey skill で cover |
| 2 | `winner-analyzer-weekly` | Mon 04:30 | winner-analyzer dispatcher → Slack 報告 | 守護 (I) fresh content engine は pattern-promoter / pattern-jsonl-refiller で cover、 winner-analyzer は report only |
| 3 | `trustmrr-list-weekly` | Mon 06:20 | trustmrr.com に MRR>0 product list、 但し Anicca product で 現状 MRR>0 ゼロ で 出品 0 = browser action 空回り | ★ 永久 no-op ★、 復活 condition (= product MRR>$0 達成) memory に 記載 |
| 4 | **anicca-retreat-crowdfund-daily** | Mon 19:05 | 実 script `00-daily-report.sh` verbatim 4 step: ①Stripe poll ②Camp Fire status ③update progress.json ④Slack #metrics | ★ R1 で T3.4 救出 試行 した が reviewer 検証 で 「TT draft / Resend donor は script に 存在 し ない」 fabricated と 判明 ★、 純 observer + Slack daily report = leech |

### B. Pure LP observer (= LP 編集 しない、 docstring 明示) — 1本

| # | cron | sched | 根拠 verbatim |
|---|---|---|---|
| 5 | **anicca-fashion-lp-sync-daily** | 00:00 daily | 実 script `lp-sync-daily.py` docstring verbatim: ★ 「This cron is informational by design: it does NOT auto-edit the LP because /fashion/page.tsx is hand-tuned... Slack alert + diff is emitted so a human can update the LP intentionally」 ★ | R2 v1 で 救出 「script posts directly = LP 更新」 と 主張 したが、 「posts directly」 = Slack post を 指す と reviewer 検証 で 判明、 純 observer |

## 5. R2 v2 — payload fix path (= NOT DELETE) で KEEP 5 本

★ reviewer v1 audit で zombie 誤判定 と 判明 ★ — `~/.agents/skills/` を 探索 不足 (= IBA HARD RULE 違反) で 削除 提案 した が、 `~/.openclaw/skills/anicca-corey-<X>/` 配下 に 実 skill EXISTS + 実 外部 action 確認 済。 削除 で は なく ★ payload path 修正 ★ で 復活。

| # | cron | 現 payload | 修正 後 payload | 守護 該当 + 実 action 確認 |
|---|---|---|---|---|
| 1 | `anicca-corey-prog-seo-weekly` | `~/.agents/skills/programmatic-seo/SKILL.md` MISSING | `~/.openclaw/skills/anicca-corey-prog-seo/scripts/run-weekly.sh` EXISTS | SKILL.md verbatim「generates 10-100 static HTML pages... drops in apps/landing/public/<slug>/index.html, git commits + push → Netlify auto-deploy」= 守護 (I) + LP HTML edit + git push 真 |
| 2 | `anicca-corey-schema-markup-cron` | `~/.agents/skills/schema/SKILL.md` MISSING | `~/.openclaw/skills/anicca-corey-schema-markup/scripts/...` EXISTS | SKILL.md verbatim「Monthly Schema.org JSON-LD injection across all aniccaai.com pages」= 守護 (I) + HTML JSON-LD inject 真 |
| 3 | `anicca-corey-page-cro-cron` | `~/.agents/skills/cro/SKILL.md` MISSING | `~/.openclaw/skills/anicca-corey-page-cro/scripts/...` EXISTS | SKILL.md verbatim「Audits LP... opens GitHub issues for top 1」= 守護 (I) + (D) GitHub issue 開 真 |
| 4 | `anicca-corey-seo-audit-cron` | `~/.agents/skills/seo-audit/SKILL.md` MISSING | `~/.openclaw/skills/anicca-corey-seo-audit/scripts/...` EXISTS | SKILL.md verbatim「Brave Search API to check our rank on 20+ keywords, validates Schema.org markup, checks meta tags, runs Lighthouse if available」= 守護 (I) SEO health input 真 |
| 5 | `anicca-corey-ai-seo-cron` | 既 `~/.openclaw/skills/anicca-corey-ai-seo/` EXISTS | (= 修正 不要) | ★ NC1 反映 ★ v2 単独 verify: 現 payload は 「Pick today's page to optimize. Rotate through `~/anicca-project/apps/landing/public/*/index.html` SEO pages」 verbatim = ~/.openclaw/skills/ 直接 参照 で 守護 (I) HTML 編集 真。 修正 不要 |

## 6. R2 v2 — Tier 3 DEFER に 移動 (= reviewer REVISE 反映) 2 本

| cron | reviewer 指摘 | 新 status |
|---|---|---|
| `anicca-seo-brand-visibility-daily` | 9 keyword Firecrawl は corey-ai-seo / prog-seo の input source 可能性 | Tier 3 DEFER (= input chain 救出 余地) |
| `anicca-article-daily-audit` | 7-day 42 URL 404 verify = article 6 channel publish 失敗 検出 operational safety net | Tier 3 DEFER (= R1 spec T3.17 で 既 「KEEP 軸 = 404 verify」 認め て いた) |

## 7. R2 v2 — 緊急 skill restore タスク 1 件

★ reviewer NEW CONSIDER C5 反映 ★

| skill | 状態 | 影響 | 修復 |
|---|---|---|---|
| `~/.openclaw/skills/anicca-night-fill/` | ★ MISSING ★ | 守護 (C) life-manager の 「14日先 19:00+ empty slot fill」 chain 不可、 night-fill cron は HEARTBEAT.md §2 dual-arrow 実装 を LLM agent に 委ねて 動作 中 だ が skill dir 復元 で 安定 化 | P3 で skill dir + SKILL.md + scripts/run.sh stub 作成 (= R2 別 phase) |

## 8. R1 Tier 3 から 救出 した 5 本 (v2 で 7→5 に 縮小、 fabricated 救出 2 本 撤回)

| # | cron | R1 status | R2 v2 救出 根拠 |
|---|---|---|---|
| 1 | `anicca-recruit-retreat-monthly` | Tier 3 retreat family | SKILL: 「phase2-discover-and-email.sh retreat-volunteers」 = D apply email |
| 2 | `anicca-recruit-tomb-weekly` | Tier 3 retreat family | SKILL: 「phase2 tomb-temple email send」 = D apply |
| 3 | `anicca-recruit-cafe-weekly` | Tier 3 cafe family | SKILL: 「phase2 cafe-property email」 = D apply |
| 4 | `opening-cafe-prelaunch-content-daily` | Tier 3 cafe family | SKILL: 「Posts countdown to X via Postiz」 = L cafe SNS posting (★ X account 健全 chk pending、 reviewer REVISE R4 反映 ★) |
| 5 | `comedy-live-schedule-publish` | R1 Tier 3 | SKILL: 「data/schedule.json 生成 + Slack week-ahead alert」 = D apply chain (★ LP downstream 主張 取下げ、 reviewer REVISE R3 反映 ★) |

★ v1 → v2 で 撤回 した 救出 ★:
- ~~anicca-retreat-crowdfund-daily~~ → Tier 1 DELETE 移動 (= §4 #4)
- ~~anicca-fashion-lp-sync-daily~~ → Tier 1 DELETE 移動 (= §4 #5)

## 9. R2 v2 — Tier 3 残 13 本 (= R1 18 - 救出 5 - DELETE 移動 2 + DEFER 新規/移動 2 = 13)

★ R1 Tier 3 = T3.1〜T3.18 = 18 本 (R1 §7 完全 list 数 verbatim)。 R2 v2 で 救出 5 (= T3.2 + T3.3 + T3.5 + T3.10 + T3.18) + DELETE 移動 2 (= T3.4 + T3.12) + DEFER 移動/新規 2 (= brand-visibility KEEP→DEFER + goal-learner 新規 DEFER) = 18 − 5 − 2 + 2 = **13 本**。
★ article-daily-audit (= T3.17) は R1 で 既 Tier 3、 R2 v1 で DELETE 主張 → reviewer REVISE で R2 v2 Tier 3 stay (= ±0) ★

| family | 本数 | cron |
|---|---:|---|
| Cafe ops | 5 | opening-cafe-daily-ops / opening-cafe-waitlist-collect-daily / opening-cafe-influencer-outreach-weekly / cafe-license-pull-daily / opening-cafe-status-weekly |
| Fashion ops | 1 | anicca-fashion-shipping-status-daily |
| Fashion review | 1 | anicca-fashion-review-scrape-daily |
| AIE Path 3 | 2 | anicca-aie-consulting / anicca-aie-product |
| Retreat phase0 | 1 | retreat-phase0-location-discover-monthly |
| Article audit (= R1 T3.17 留任) | 1 | anicca-article-daily-audit |
| anicca-goal-learner (= R2 v2 新規) | 1 | (Mon 09:30 internal goal review → Slack only) |
| ★ R2 v2 KEEP→DEFER 移動 ★ | 1 | anicca-seo-brand-visibility-daily (= keyword input chain 救出 余地) |

→ **合計 = 5 + 1 + 1 + 2 + 1 + 1 + 1 + 1 = 13 本** (算術 整合 確認 済)

## 10. 削減 数値 (= 3 scenario count、 v2 更新)

| シナリオ | 削除 計 | 残 enabled |
|---|---:|---:|
| R2 v2 Tier 1 のみ (= 5 confident) | −5 | **157** |
| R2 v2 + Tier 3 全 KEEP | −5 | 157 |
| R2 v2 + Tier 3 半 削減 (= cafe 3 + fashion 1 + AIE 2 + retreat 1 + goal 1 = 8 本) | −13 | **149** |
| R2 v2 + Tier 3 全 削除 (= 13 本 全部) | −18 | **144** |

★ 半 削減 8 本 内訳 (= NR1 反映、 個別 cron 明示) ★:
- Cafe ops 5本 中 3 削減 候補: opening-cafe-daily-ops / opening-cafe-influencer-outreach-weekly / opening-cafe-status-weekly (= report-shape の 3 本)
- Fashion ops 1 削減: anicca-fashion-shipping-status-daily
- AIE 2 全 削減
- Retreat phase0 1 削減
- goal-learner 1 削減
- 半 削減 維持: cafe-license-pull-daily (= 申請 中 chk)、 opening-cafe-waitlist-collect-daily (= 顧客 接点)、 anicca-fashion-review-scrape-daily (= customer support 端)、 article-daily-audit (= 404 safety net)、 brand-visibility (= SEO input)

## 11. 実装 phasing (v2 更新)

| Phase | やる こと | verify |
|---|---|---|
| P0 | spec v2 を reviewer に audit、 ok まで iterate | reviewer ok |
| P1 | plan 起稿 → `2026-06-05-cron-cull-r2.md` | self-review |
| P2 | backup `jobs.json.bak-cron-cull-r2-<ts>` 作成 | size verify |
| **P3** | ★ Corey 4 本 の payload path 修正 (= `openclaw cron edit <id> --message "新 message"` × 4) ★ — ★ NR2 反映 ★: openclaw harness の lookup 経路 = cron payload message を 「LLM agent への 自然 言語 命令」 と して 渡す (= skill SKILL.md frontmatter triggers 経由 で は ない、 message 内 で 直接 bash entrypoint path を 指定 する 方式)。 修正 = message 文字列 内 の `~/.agents/skills/<X>/` を `~/.openclaw/skills/anicca-corey-<X>/scripts/<entry>.sh` に 置換 + skill SKILL.md 読込 命令 も 同 path に 統一。 | 162 維持 + payload verify (= openclaw cron get <id> で 新 message 確認) |
| **P4** | ★ anicca-night-fill skill dir restore (= SKILL.md + scripts/run.sh stub 作成) ★ | dir + file 存在 verify |
| P5 | R2 Tier 1 削除 × 5 (= competitor-monitor / winner-analyzer / trustmrr-list / retreat-crowdfund / fashion-lp-sync) | 162→157 |
| P6 | Slack 中間 報告 (= 162→157 + payload fix 4 + skill restore + Tier 3 14 family chk question) | post 確認 |
| P7 | (Dais 反応 後) Tier 3 個別 削除 | 157→Y |
| P8 | audit-rules.json 更新 (= R2 知見 反映: R4 false-positive 「payload path mismatch」 例 追加、 R8 dormant condition 強化) | rules diff verify |
| P9 | commit + push、 sister consolidation spec trigger | git log |

## 12. Self-review checklist v2

| chk | 通過 |
|---|---|
| R2 v2 削除 5 本 の どれ も 守護 §2 A-M 違反 し ない (= reviewer v1 BLOCKING 4 corey 訂正 済) | ★ ✓ §4 (= 5 本 全 守護 該当 なし、 retreat-crowdfund/fashion-lp-sync は 実 script docstring 検証 で leech 確定) ★ |
| Corey 4 を 削除 で なく payload fix path で KEEP | ★ ✓ §5 (= reviewer NEW BLOCKING B1-B4 反映) ★ |
| 救出 5 本 の どれ も 実 script verbatim 引用 で 検証 済 | ★ ✓ §8 (= retreat-crowdfund / fashion-lp-sync 救出 撤回、 reviewer NEW BLOCKING B5-B6 反映) ★ |
| Tier 3 family 軸 整合 (= 13 本) | ✓ §9 |
| scenario count 訂正 (= 157 / 149 / 144) | ✓ §10 |
| skill restore task 追加 (= anicca-night-fill MISSING) | ✓ §7 §P4 |
| audit-rules.json R4 false-positive 「payload path mismatch」 例 追加 | ✓ §P8 |
| corey 5 ファミリー 整合 (= cold-email + 4 SEO 全 KEEP) | ✓ §5 §6 |

## 13. 受入 条件 (v2 更新)

| 項目 | 条件 |
|---|---|
| reviewer v2 ok | superpowers:code-reviewer (= 5 iterate 内) |
| plan 起稿 | `2026-06-05-cron-cull-r2.md` |
| Corey payload fix | 4 cron payload に `~/.openclaw/skills/anicca-corey-<X>/scripts/...` 反映 |
| night-fill skill restore | `~/.openclaw/skills/anicca-night-fill/SKILL.md` + `scripts/run.sh` 存在 |
| R2 Tier 1 削除 | 162 → 157 (5 本) |
| Tier 3 個別 | Dais family 単位 OK で 157→Y |
| audit-rules.json 更新 | R4 false-positive 例 + R8 dormant condition 強化 |
| Slack 報告 | `🧹 cron-cull R2 完了: 162→Y + corey 4 fix + night-fill restore` |
| commit + push | `chore(cron-cull-r2): 5 deleted + 4 payload fix + 1 skill restore (162→157)` |

## 14. 変更 履歴

- R1 (同日 早朝): 192→162 完了
- R2 v1 (同日): 162→153 主張、 但し reviewer audit で BLOCKING 7 + REVISE 5
- R2 v2 (同日 訂正): reviewer v1 BLOCKING 7 + REVISE 5 + CONSIDER 5 全 反映 (= 削除 9→5、 153→157)
- **R2 v3 (同日 再訂正)**: reviewer v2 NEW BLOCKING NB1 + NR1/NR2 + NC1 反映:
  - §9 Tier 3 算術 矛盾 訂正 (= 14 → 13 本、 R1 Tier 3 = 18 起点 + 救出 5 + DELETE 2 + DEFER 移動 2 = 13)
  - §10 半 削減 内訳 8 本 個別 cron 明示 (= NR1 反映)
  - §11 P3 openclaw cron edit lookup 経路 1 文 付記 (= NR2 反映)
  - §5 #5 corey-ai-seo v2 単独 verify 文 追加 (= NC1 反映)

---

**End of R2 design v3**. Ready for `superpowers:code-reviewer` re-audit.
