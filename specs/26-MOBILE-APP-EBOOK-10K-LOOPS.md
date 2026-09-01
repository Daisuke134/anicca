# 26 — Mobile App Scaler + Ebook Seller ($10k loops)

Status: business outcome and revenue-model context

Effective: 2026-08-01

Owner: Dais

Marketing execution SSOT: `27-MARKETING-ENGINE-END-TO-END.md`

Current dual-ebook activation SSOT: `28-EBOOK-SELLER-DUAL-MONK-LOOPS.md`. Spec 28 governs the local three-times-daily JP watercolor and EN Anicca monk loops, Postiz/Telegram closure, the owner-confirmed retained HeyGen Anicca Monk Factory and `@monk.mujo` Instagram destination, and the current revenue target: each ebook must independently reach USD `$10,000` equivalent of rolling 30-day settled net revenue, for at least `$20,000` combined. It supersedes the older gross target and renderer choice only for those current ebook loops; the general scaling doctrine here remains authoritative. OmniAvatar and MuseTalk are challengers only for current `ebook-en` activation.

Live execution: Gates 1–13 are complete. Gate 14's scorer, CLI, mutation safety, exact tactic/renderer aggregation, immutable treatments, and ten-item production queue are built and verified; only native publication, checkpoint maturity, and real outcome write-back are time-dependent. That clock does **not** block independent implementation. The active build lane is now Gate 15 plus Gate 16A and the unfinished Mobile App Scaler/Ebook Seller actuators, while Gate 14 observations accrue in a background monitor. The first production watercolor post is TikTok ID `7669159327655054613` at `https://www.tiktok.com/@obou_anicca/video/7669159327655054613`, bound to immutable publication `publication.babf5c938cba5dc0d5c02b68` and experiment `experiment.preview-gate12`. Gate 13 added all ten attribution result records; its 15-minute query reported deterministic qualified clicks `0` and kept nine immature results null. Gate 14 then wrote decision `writeback.7da73ad427f5617d8ce7404e`: at 23 minutes, eligible experiments `0`, winner/loser/mutation `0`, and no hook/playbook hash change. The mature updater enforces EWMA alpha 0.3, at least three real observations before retirement, a 20% active exploration floor, exact experiment-plan mapping before tactic results, and renderer aggregation only from the bound cohort. Final frozen cohort v3 has ten exact, unique-hook plans/treatments rendered, visually checked, and queued daily at 20:15 JST from 2026-08-02 through 2026-08-11; queued/provider state is not relabeled as native publication. The last two hooks came from two bounded competitor INTEL passes with exact TikTok/transcript/media/judgment evidence. Rejected and earlier v1/v2 assets were never posted and remain outside the accepted selection. Full verification passes 281 tests plus 47 subtests. No fixture or legacy post can substitute. Exact contracts/evidence are in spec 27 §§3.12–3.14.

### 現在地から終了までの実行順

Gate番号は監査履歴であり、直列の待機命令ではない。時間経過が必要な検証は自動monitorへ移し、その間に独立して構築・検証できる仕事を止めない。優先順位は次の通り。

#### BUILD NOW — 待たずに完成させる

1. **Gate 15を閉じる:** `owner_report_language=ja`を実装し、実操作、途中経過、商品日報、実験結果、問題報告、週報を自然な日本語で送る。台帳一致、null理由、証拠、重複防止をfixture、replay、実Bot receiptで検証する。
2. **Gate 16Aを構築する:** leased job queue、lease取得/更新/期限切れ回収、idempotency key、retry、dead-letter、read-only reconcile、rollback、worker healthを実装する。現在のruntimeを止めずにshadowを開始し、7日soakの時計を動かす。
3. **App Agentの操作面を完成する:** mobileapp-builder PRDで`gotcha_moment`を必須にし、`lm app selfcheck/evolve`を実装して、安全な自己拡張をtestとcommitで証明する。
4. **Honneを出す:** content-firstで勝つpromiseを選び、Honneへ実装し、build、ASC upload、submissionを行い、`WAITING_FOR_REVIEW`の実receiptを得る。
5. **2アプリのfunnelを閉じる:** aniccaios/honneの商品別にASC impressions→product page→first download、analyticsのfirst_open→onboarding→gotcha→paywall、RevenueCatのtrial→paid→renewal/churn/refund→MRR/proceedsを接続する。
6. **アプリ獲得を閉じる:** ASO rubric/keyword evaluator/ASC writer、上限付きASA bid loop、creator discovery/DMをcampaign IDからpaid revenueまで接続する。一度に一つのbottleneckだけを実験する。
7. **Ebook Sellerを完成する:** KDP demand→thesis→manuscript QA→EPUB→KDP action queue→direct saleを実装する。日本語watercolorと英語monkを商品専用アカウントで稼働し、KDP order/refund/royalty/KENPとdirect saleの採算adapterを閉じる。
8. **avatar runtimeを安全にする:** reproducible artifactを保存し、30 GB以上の空きを確保し、lock fileから環境を再現し、renderer secretをOpenClaw pathから除く。
9. **所有するJP/EN monk rendererを完成する:** HeadAudio viseme、所有mouth sprites/stills、Ken Burns、caption/audioで固定JP 5本+EN 5本をnetwork/GPU/外部render費用なしで再現する。
10. **HeyGen依存をゼロにする:** slideshow/facelessを常設安全laneとし、OmniAvatar等のchallengerは同じ10本でcost/latency/failure/sync/identity/business liftを比較し、実測勝者だけを昇格する。
11. **全商品をLife Managerへ登録する:** app、ebook、将来のweb/skill/course/ticketが同じproduct/account/campaign/experiment契約を使い、商品固有adapterだけを差し替えられることをend-to-endで検証する。

#### START NOW / SOAK IN BACKGROUND — 構築と並行して時計を進める

12. **Gate 14 monitorを自動運転する:** `ebook-ja × TikTok × watercolor-monk`のaccepted 10本について、予定時刻後にnative ID/URLをreconcileし、6h/24h/72h/7d checkpointと売上結果を自動回収する。未成熟はnull、取得不能は理由付き、provider queueはnative公開と区別する。
13. **Gate 16 shadowを自動運転する:** Life Manager workerと現行truth ledgerを継続比較し、lease競合、duplicate external action、missing action、recovery、rollback readinessを日次で記録する。shadowは外部操作を二重実行しない。

#### TIME-DEPENDENT CLOSURE — 最後に証拠で閉じる

14. **Gate 14を閉じる:** 10本が24時間以上成熟した後だけ、real winner/loser、hook EWMA、tactic、renderer結果を書き戻す。尺超過・字幕不良・旧renderer版の棄却asset、fixture、legacy postは代用しない。
15. **Gate 16Bを閉じる:** 7日連続reconcile、duplicate external action=0、rollback合格後にLife Manager workerへcutoverし、Marketing用OpenClaw runtimeを停止する。
16. **段階的に拡張する:** 各商品でpositive contributionを証明してから、`$10k → $100k → $1M → $10M`のportfolio段階へ進む。オーナーが手動で反復するのではなく、商品agentが観測、選択、実行、検証、self-healを継続し、不可逆・policy・予算超過だけをowner actionにする。

Gate 2 verified and reversibly quarantined 28 legacy LaunchAgents plus seven live OpenClaw publication-pipeline jobs. The final live/store inventory has zero enabled legacy publishers, all ten measurement/report LaunchAgents remain loaded, plist hashes are unchanged, and an inert rollback round trip passed. No replacement publisher starts before truth Gates 3–5.

Gate 3 wrote the tested live identity ledger for 91 Postiz rows. Direct receipts plus strict TikTok account/full-caption/time reconciliation uniquely resolve 71/73 PUBLISHED posts (97.26%); two duplicate-caption TikToks remain ambiguous and all 18 ERROR rows remain errors. The idempotent rerun stayed at 91 rows. See spec 27 §3.3.

Gate 4 is complete. The canonical metric state contains 110 unique checkpoints: four measured in their real 24h windows and 106 historical checkpoints honestly marked missed. A rerun added zero. Independent verification covered four Instagram, three TikTok, and three YouTube posts: native identity matched 10/10 and comparable-field mismatches were zero. TikTok uses its free native `/api/post/item_list/` response through an isolated CloakBrowser context; the current production CLI performs no Postiz release-ID mutation. See spec 27 §3.4.

Gate 5 is complete. The canonical state has one 2026-07-30 row for each of
`aniccaios`, `honne`, `ebook-ja`, and `ebook-en`, with no duplicate snapshot ID.
ASC download types are separate; RevenueCat values are app-filtered; Stripe is
bounded to one UTC business day and the exact ebook product ID with gross,
refund, and net fields. KDP/Gumroad/PostHog/Honne funnel gaps are explicit
unavailable states, not zero. `aniccaai.com/go/{token}` persisted and returned a
live minimal receipt before redirecting. See spec 27 §3.5.

## 1. Outcome and scope

Run two revenue loops from one shared INTEL and MEASURE organ:

1. **Mobile App Scaler** — scale `aniccaios` and `honne` to **$10,000 gross MRR each**.
2. **Ebook Seller** — scale the initial Japanese ebook and initial English ebook independently to **$10,000 equivalent rolling 30-day settled net revenue each** across KDP and direct sales, for at least `$20,000` combined, then replicate the proven recipe into more languages, accounts, and titles.

The marketing organ is shared, but public accounts are product-dedicated. One account promotes exactly one product; one product may have many accounts. The English monk accounts promote `ebook-en`; the Japanese watercolor accounts promote `ebook-ja`. Creative engines and learning infrastructure are reusable, but an account never rotates between unrelated products. See spec 27 for the locked account map.

Locked scope:

- No phone-call, Twilio, voice-call, or life-manager-call work.
- Telegram is reporting/control output only. It must use Telegram Bot API directly.
- Postiz remains an allowed publishing transport. It is not the brain, scheduler, source of truth, or measurement system.
- OpenClaw is a temporary legacy runtime only. No new feature may depend on its CLI, cron, message command, state path, or secrets path.
- Final runtime is one leased job queue plus workers. OpenClaw is stopped only after shadow verification and cutover.
- Revenue claims require store/payment-provider evidence. Views, generated files, posts, and submissions are leading indicators, not revenue.

## 2. Revenue math

### 2.0 Verified current baseline (read-only refresh 2026-08-02)

The product-scoped collector queried business date `2026-08-01` without
rotating credentials. Latest complete RevenueCat app-filtered MRR remains
`aniccaios=$20.73` and `honne=$0.00`; the completed Revenue/Transactions points
for both apps were `0/0`. Exact-product, one-day Stripe queries returned zero
paid orders and empty gross/refund/net currency maps for both `ebook-ja` and
`ebook-en`. These are verified revenue/order facts, not profit. Complete profit
is currently unknown because store fees/proceeds, advertising spend, production
cost, tax, and all channel costs are not yet reconciled into one contribution
ledger. Telegram must say `gross MRR`, `gross/net provider revenue`, or
`contribution margin`; it must never relabel those as profit.

### Mobile apps

Current default pricing is $9.99 monthly and $49.99 yearly. An annual subscriber contributes $4.17 of normalized MRR. At a 50/50 monthly/annual active-subscriber mix, average gross MRR per subscriber is about $7.08.

- $10,000 gross MRR/app = about 1,413 active paying subscribers at that mix.
- With 6% monthly subscriber churn, steady-state replacement is about 85 subscribers/month.
- To approach the target from zero in 12 months requires about 160 gross new subscribers/month, or 5.3/day, before safety margin.
- At 3% install-to-paid conversion, that means roughly 178 installs/day/app. The operating target is **200–300 qualified installs/day/app**, not 100 total installs/day across both apps.

Net proceeds after store commission are a separate KPI. Never label gross MRR as net MRR.

### Ebooks

Ebooks are purchases, not recurring subscriptions; the current JP and EN target is rolling 30-day settled net revenue under Spec 28. Track gross and contribution per order separately after refunds, storefront fees/royalties, payment fees, and known variable fulfillment cost.

At a `$9.99` average gross selling price, 1,001 orders/month is only the gross lower bound; the settled-net `$10,000` target requires more orders. KDP royalty and direct-sale economics are reported separately and then joined without double counting. After both JP and EN independently clear the gate, the agent may expand the same validated mechanism into additional titles, accounts, Spanish and other culturally adapted editions; literal translation alone is not a new validated product.

### 2.3 Scale ladder: $10k to $10M

The first target is `$10k/month per validated product`, not an immediate $10M
claim. Scale proceeds only when the preceding stage has mature positive
contribution economics:

| Portfolio stage | What must be proven before promotion |
|---|---|
| `$0 → $10k/month` | one product, one dedicated account/cohort, repeatable acquisition, paid conversion, refunds/churn, positive contribution |
| `$10k → $100k/month` | repeat the winning hook/renderer/channel across several accounts or adjacent products without CAC/payback deterioration |
| `$100k → $1M/month` | multi-product portfolio, multiple languages/channels, creator/paid acquisition, localized onboarding/listing, reliable support and finance controls |
| `$1M → $10M/month` | portfolio/company scale: many independent profitable products, regions and acquisition channels; concentration, platform, policy, fraud, cash-flow and operational risk controls |

At the current blended app price, `$10M gross MRR` is roughly 1.41 million
active paying subscribers. At `$9.99` per ebook, `$10M monthly gross revenue`
is roughly 1.00 million orders/month (about 33,367/day). Those volumes are not a
credible single-app or single-title extrapolation. The intended route is a
portfolio of independently validated apps, books, languages, accounts and
channels. Automation makes experiments and replication cheaper; it does not
guarantee demand or remove platform and operational limits.

## 3. Ideal system

```text
                      SHARED INTEL + EXPERIMENT ORGAN

 X/articles/RSS/GitHub      TikTok/YouTube hooks       App/ads/storefronts
          |                         |                          |
          +-------------------------+--------------------------+
                                    v
             playbook.jsonl + hook-library.jsonl + ad-swipe.jsonl
                                    |
                    agent selects one testable mechanism
                                    |
                 +------------------+------------------+
                 |                                     |
                 v                                     v
       MOBILE APP SCALER                         EBOOK SELLER
  aniccaios + honne                         JP + EN useful books
  viral concept -> gotcha                   demand -> outline -> book
  -> build -> ASC -> ASO                    -> EPUB -> KDP/direct
  -> content/creator/ASA                    -> avatar/faceless content
                 |                                     |
                 +------------------+------------------+
                                    v
              experiment_id on every app build, listing, ad, hook, and book
                                    |
                                    v
             impressions -> installs/sales -> paid -> retention -> revenue
                                    |
                                    v
          write back status won/lost + hook EWMA + next highest-EV experiment
                                    |
                                    v
                 Telegram daily facts + weekly gap/decision report
```

The model judges what to test from evidence and canonical examples. Deterministic code is limited to collection, API/browser actions, arithmetic, leases, ledgers, attribution, and verification. Do not encode creative or product judgment in keyword regexes or brittle if/else rules.

## 4. Business delivery map

The table below is retained as end-to-end business context. For marketing implementation order and done conditions, follow spec 27. Marketing work must not be broadened by this table.

| # | Work | Done condition |
|---:|---|---|
| 1 | Create `~/anicca/skills/_shared/telegram.py`; load Marketing Engine secrets from `~/anicca/.env`; support text, document, photo, and video through direct Bot API | **DONE 2026-08-01:** real text, document, photo, and video arrived with message IDs; 12 tests pass; Marketing Engine transport invokes no `openclaw` process/CLI |
| 2 | Wire daily result reports for mine, score, metrics, dashboard, clip, video, self-improve, and capafy | **DONE 2026-08-01:** 8/8 validated run events and Telegram receipts; replay sends zero; dry-run production rows zero; seven existing LaunchAgents read back the canonical entrypoint, while no new video publisher schedule was enabled |
| 3 | Verify the existing Stripe adapter/credential and restore the monk/business KPI job; rotate only if independent evidence shows compromise | **DONE 2026-08-01:** Gate 5 records product-scoped, date-bounded Stripe gross/refund/net evidence for both ebook products and explicit unavailable/null reasons for sources that cannot be read; no credential rotation was performed |
| 4 | Create `intel/playbook.jsonl`, `hook-library.jsonl`, `creators.jsonl`, and `ad-swipe.jsonl`; seed the nine open gaps plus the one completed voice/character rule | **DONE 2026-08-01:** ten valid unique tactics, nine `new`, one `done`, zero unproved `won`; four schemas and negative duplicate/BOM/blank/null/status tests pass; empty observed stores remain empty rather than fabricated |
| 5 | Implement `lm intel pull` and weekly `lm intel gap` for X Articles, RSS, GitHub, and ad/store intel | **DONE 2026-08-01:** 75/75 captured items judged, exact source URLs retained, idempotent rerun added zero, Meta unavailable is explicit, schedules read back canonical commands, and Telegram daily `5095`/weekly `5094` were delivered; competitor video remains the next separate gate |
| 6 | Wire `variation.py` and the new hook library into every content runner; migrate and retire old hook files | Production runner references to `hookPool-ja.txt` and `fixed-strings-*.json` are zero |
| 7 | Restore score/attribution write-back | `hook-perf.jsonl` receives a current-day row; EWMA updates; bottom 20% can retire while 20% remains exploration |
| 8 | Add competitor video ingestion: handle -> URL -> download -> transcript -> virality rubric -> hook library | **DONE 2026-08-01:** two product-locked EN/JA sources produced 40 native observations, four local hashed transcripts, four judgments, and 11 evidence-backed hooks; rerun added zero and scheduled daily Telegram receipt is `5102` |
| 9 | Add product manifests for `aniccaios`, `honne`, `ebook-ja`, and `ebook-en`; every output receives an `experiment_id` | **DONE 2026-08-01:** four products, nine dedicated accounts, and five renderers validate; two safe ebook plans carry the full attribution tuple and replay idempotently; canonical legacy-hook references and enabled legacy publishers are zero; no publication occurred |
| 10 | Make `gotcha_moment` mandatory in mobileapp-builder PRDs; add `lm app selfcheck/evolve` | PRD validation rejects a missing gotcha; the CLI completes one safe, tested self-extension commit |
| 11 | Run the current-app content-first pass, then build/submit Honne | Winning video promise is mapped to the product; Honne reaches `WAITING_FOR_REVIEW` with ASC evidence |
| 12 | Fix the app funnel in measured order: App Store impressions -> product-page CVR -> onboarding gotcha -> paywall -> trial/paid -> D7/D30 retention | `aniccaios` and `honne` dashboards have non-zero daily data for every stage; one isolated experiment runs at a time per stage |
| 13 | Connect ASO/UA/creator acquisition: ASO rubric + keyword evaluator + ASC writer + ASA bid loop + creator discovery/DM | Spend is capped; campaign and creator IDs attribute through paid revenue; scaling occurs only when contribution economics pass the gate |
| 14 | Build Ebook Seller: KDP demand scout -> agent-selected thesis -> JP/EN adaptation -> QA -> EPUB -> KDP action queue; add direct Gumroad path | One original, useful book is live on KDP and direct sale; listing, sales, refunds, royalty, and contribution margin are measured |
| 15 | Make the avatar runtime safe to change: archive reproducible outputs, recover at least 30 GB free disk, restore a declared Python environment, and move renderer secrets out of `~/.openclaw/.env` | Data volume is below 85% usage; dependencies install from a lock file; `render-free` starts without a missing interpreter; no new renderer reads an OpenClaw path |
| 16 | Build the reusable JP/EN monk renderer: HeadAudio visemes -> owned 6–9 mouth sprites -> existing owned stills/Ken Burns -> captions/audio | M4 runs ten fixed clips (five JP, five EN) without network/GPU; all have A/V streams, correct duration, stable identity, and zero external render cost; JP watercolor accounts remain bound to `ebook-ja` and EN monk accounts to `ebook-en` |
| 17 | Remove the final HeyGen asset dependency; compare the faceless/slideshow safety lane with optional avatar challengers from spec 27 | Ten fixed clips render; no source asset or daily call comes from HeyGen; every candidate has measured cost, latency, failures, sync, identity/motion rubric, and license decision; only a measured business winner is promoted |
| 18 | Replace per-cron execution with leased jobs; shadow, reconcile, cut over, then stop OpenClaw | One worker owns each lease; duplicate actions are zero in shadow; rollback is documented; OpenClaw processes and crons are stopped |

## 5. Mobile App Scaler loop

Each app runs the same loop but has separate experiments and unit economics:

1. Observe viral/problem language, App Store queries, competitor creatives, and funnel data.
2. Select one customer promise and define the five-second `gotcha_moment` that proves it.
3. Make one acquisition creative before expanding the build. Map its promise exactly through ad -> onboarding -> gotcha -> paywall.
4. Ship through `asc`; instrument impression, product-page view, install, onboarding completion, paywall view, trial, paid, renewal, refund, and revenue.
5. Diagnose the narrowest bottleneck and run one isolated experiment: first store conversion, then gotcha/onboarding, then paywall, then retention, then paid acquisition.
6. Scale ASA/creator/paid spend only when cohort contribution margin covers acquisition cost within the declared payback window.
7. Write the result to the playbook and Telegram; keep the winner, retire the loser, reserve 20% traffic/output for exploration.

Do not multiply apps before the two seed apps have working attribution and repeatable acquisition. The factory scales a proven loop, not unmeasured binaries.

## 6. Ebook Seller loop

1. Use KDP/search/social demand evidence to select a painful, specific reader job. The agent chooses the thesis; code only collects and scores evidence.
2. Produce one evidence-backed English master or Japanese master, then culturally adapt the other edition. Translation alone is not a second useful product.
3. Apply editorial QA, citation/rights checks, duplication checks, EPUB validation, cover/listing QA, and a human-safety gate only where platform policy or irreversible publication requires it.
4. Publish through an idempotent KDP leased action queue; publish the direct edition/bundle through Gumroad.
5. Create content from the book's strongest transformations: faceless slideshow first; fixed-character avatar only when it wins measured sales per production dollar.
6. Attribute hook -> post -> landing/store page -> order -> refund -> contribution margin. Improve cover, title, sample, description, price, format, and content angle one test at a time.
7. Expand a winner into a reader-serving cluster (workbook, journal, audio, or adjacent book) only after real sales; retire titles that do not clear the evidence threshold.

## 7. Avatar renderer decision — verified 2026-08-01

### 7.1 Actual machine and current pipeline

- Production Mac: Apple M4, 10 CPU cores, 10 GPU cores, 16 GB unified memory, no NVIDIA/CUDA.
- Data volume rechecked on 2026-08-01: 228 GiB total, 167 GiB used, about 40 GiB available (81% used). The 30 GiB free-space condition is now met, but multi-GB CUDA avatar models still do not fit the M4/16 GB runtime.
- Existing `anicca-monk-factory-v3/scripts/render-free.sh` already intends to use HF ZeroGPU LatentSync then fal LatentSync, but its declared `.venv/bin/python` does not exist. The checked-in runtime is presently broken before inference.
- Existing English master clips are HeyGen-generated assets. Daily HeyGen rendering is retired, but full HeyGen independence is not achieved until those masters are replaced by owned assets.

### 7.2 Executed verification evidence

| Test | Result | Decision |
|---|---|---|
| ByteDance LatentSync through `fffiloni/LatentSync` HF ZeroGPU; existing monk base + fresh audio | TECHNICAL PASS: 70 seconds wall time; output H.264 1080×1920 + AAC, 3.2 seconds, 1,029,960 bytes; Telegram video message `4887`. OWNER QUALITY FAIL: explicitly rejected as visually unacceptable | **REJECT production**. Retain only as historical evidence; do not send or publish it again |
| OmniAvatar through `alexnasa/OmniAvatar` HF ZeroGPU; same owned monk image + five-second audio | PASS: 101.4 seconds wall time; output H.264 400×720 + AAC, 5.04 seconds, 204,350 bytes; Telegram video message `4893`; sampled frames preserve identity | Historical benchmark, now **owner-approved as the current `ebook-en` primary renderer by Spec 28**. Spec 28 E4 governs durable evidence, license chain, and zero-cost three-renders/day capacity |
| HeadAudio on this M4: clone, `npm ci`, Jest, webpack | PASS: 4 suites/5 tests; median processor prediction 0.028 ms/frame; production bundle built | Use as local audio-to-viseme engine for the watercolor renderer. Before vendoring, remove/upgrade high-risk dev dependencies reported by `npm audit`; ship only the audited runtime bundle |
| Rhubarb Lip Sync v1.14 macOS release on this M4 | FAIL: official binary is x86_64 and exits `bad CPU type`; arm64 source configure then fails on missing Boost | Not the baseline. Reconsider only if an arm64 artifact is built in CI and passes the same JP/EN fixture set |

The LatentSync sample was technically valid but owner-rejected for quality. The owner later inspected and accepted the OmniAvatar artifact as good enough for current `ebook-en` production. Spec 28 E4 therefore preserves that quality decision and measures only durable provenance, license chain, and free three-renders/day capacity; the general ten-clip challenger gate still applies to other products or renderers.

### 7.3 Locked three-tier renderer architecture

```text
script -> fixed JP/EN voice -> audio.wav
                              |
             +----------------+----------------+
             |                                 |
             v                                 v
   TIER A: SAFETY LANE                  TIER B: AVATAR CHALLENGER
   faceless/slideshow/watercolor        owned still + voice
   HeadAudio + owned sprites            -> OmniAvatar/other candidate
   M4, no GPU, no network required      best-effort; never blocks Tier A
             |                                 |
             +----------------+----------------+
                              |
                              v
                  TIER C: QUALITY CHALLENGER
       LongCat / InfiniteTalk / MuseTalk / Ditto / JoyVASA
        explicit NVIDIA job; only for benchmark or proven winners
```

Tier A is the stable JP/EN production format. Tier B and Tier C are optional treatments and are not allowed onto the daily path merely because a demo looks better.

### 7.4 Repository decisions

| Repository | Verified facts | Commercial/runtime decision |
|---|---|---|
| [HeadAudio](https://github.com/met4citizen/HeadAudio) | MIT; audio-driven visemes; language-independent input; documented M2/16 GB browser measurements; passed tests/build on our M4 | **ADOPT** for local watercolor mouth motion |
| [LatentSync](https://github.com/bytedance/LatentSync) | Apache-2.0; 1.5 needs 8 GB VRAM, 1.6 needs 18 GB locally; HF inference technically succeeded but the owner rejected the visual output | **REJECT production**; historical benchmark only |
| [OmniAvatar](https://github.com/Omni-Avatar/OmniAvatar) | audio-driven human animation; our five-second HF ZeroGPU inference succeeded in 101.4 seconds | **ADOPT for current `ebook-en` under Spec 28**; E4 must bind the exact license chain and prove three zero-cost daily renders. Other product adoption still requires its own gate |
| [MuseTalk](https://github.com/TMElyralab/MuseTalk) | MIT code; model allows commercial use; JP/EN/Chinese; CUDA; 4 GB path takes about five minutes for eight seconds on RTX 3050 Ti | **BENCHMARK**, not the M4 baseline |
| [LongCat-Video-Avatar 1.5](https://github.com/meituan-longcat/LongCat-Video) | MIT; audio-image/video continuation; INT8 and eight-step distillation; official avatar examples use two GPUs and issues report 48 GB OOM | **QUALITY CHALLENGER** on explicit GPU only |
| [InfiniteTalk](https://github.com/MeiGen-AI/InfiniteTalk) | Apache-2.0 model; image/video input; unlimited-length V2V; low-VRAM/quantized modes; CUDA | **QUALITY CHALLENGER** for long form on explicit GPU |
| [Ditto](https://github.com/antgroup/ditto-talkinghead) | Apache-2.0; image+audio; official runtime A100/TensorRT, PyTorch model also released | **BENCHMARK** only; no M4 path |
| [JoyVASA](https://github.com/jdh-algo/JoyVASA) | MIT; human/animal portrait; Windows RTX 4060 8 GB tested; training data Chinese/English | **BENCHMARK**; Japanese is not claimed, so it cannot be JP baseline |
| [LivePortrait](https://github.com/KlingAIResearch/LivePortrait) | MIT code; M4/MPS supported but roughly 20× slower than RTX 4090; driving-video rather than direct audio; bundled InsightFace detection models are noncommercial | **DO NOT SHIP AS-IS**; usable only after replacing the detector and only for one-time master creation |
| [SadTalker](https://github.com/OpenTalker/SadTalker) | Apache-2.0; M1 install documented; open MPS/performance issues include about 20 minutes for five seconds on M2/16 GB | **REJECT DAILY PATH**; too old/slow for this Mac |
| [EchoMimic](https://github.com/antgroup/echomimic) | Apache-2.0 code; tested on V100 16 GB/4090 24 GB/A100 80 GB; English/Mandarin | **REJECT JP BASELINE** |
| [AVTR-1](https://github.com/avaturn-live/avtr-1) | single NVIDIA GPU realtime, but renderer/streamer are PolyForm Noncommercial and InsightFace dependency is noncommercial | **REJECT** for the revenue factory |
| FLOAT | checkpoint/code license is CC BY-NC-ND 4.0 | **REJECT** for commercial use |
| LLIA / FantasyTalking2 | paper/project code only; inference/checkpoints absent | **REJECT** until runnable artifacts exist |
| Wav2Lip official checkpoints | official repository restricts outputs/models to research/noncommercial use | **REJECT** for the revenue factory |

### 7.5 Promotion and stop gates

Every renderer uses the same fixed evaluation pack: five Japanese and five English clips, the same owned character, scripts, voices, durations, resolution, and captions.

A challenger is promoted only when all are true:

1. Ten of ten renders complete with correct audio/video streams and no manual repair.
2. Its measured A/V sync is no worse than the current baseline.
3. An evaluator agent, using canonical good/bad examples, rates identity, mouth artifacts, motion naturalness, temporal stability, and character fit above the baseline. Do not replace this judgment with keyword or regex rules.
4. Render cost per accepted video and p95 completion time fit the declared daily budget/SLA.
5. License and every bundled model permit commercial output.
6. In a content experiment, revenue or qualified click-through per 1,000 impressions beats the baseline. Better-looking video without a business lift does not replace production.

Stop a candidate immediately on a commercial-license conflict, unavailable weights, unsupported required hardware, or repeated fixture failure. Do not spend implementation time rescuing a rejected candidate.

### 7.6 Compute decision

- GitHub Actions standard hosted runners are CPU. GPU larger runners require eligible paid organization/enterprise plans. GitHub orchestrates tests/releases; it is not free production inference.
- HF ZeroGPU is allowed for bounded best-effort experiments with idempotent retries. It is not an availability guarantee or production SLA.
- LongCat/InfiniteTalk/MuseTalk/Ditto/JoyVASA benchmarks run as bounded, explicit NVIDIA jobs. No always-on GPU is provisioned before measured demand.

## 8. Owner dashboard

Daily Telegram, one compact message per loop:

- Mobile/app: impressions, installs, paid starts, active subscribers, gross MRR, net proceeds, D7/D30, spend, CAC/payback, experiment decision.
- Ebook: qualified demand items, books live, orders, refunds, gross revenue, contribution margin, content-to-sale attribution, experiment decision.
- System: jobs succeeded/failed/leased twice, new tactics/hooks, tests running, evidence links, next action.

Weekly owner decision is limited to irreversible/high-risk changes: new spend cap, price architecture, new public identity/character, platform account, and publication approval when required. Routine research, generation, measurement, and reversible experiments remain autonomous.

### 8.1 Generic Telegram product contract

Telegram is generated from product/account manifests, not hard-coded Anicca
names. Any iOS app, web app, direct/KDP ebook, marketplace skill, course, or
ticket can use the same envelope by supplying its product ID, product type,
currency, primary conversion, money provider, accounts, and evidence adapters.

Every message begins with `[environment] [product_id] [message_type]`, carries a
stable run/experiment/publication ID, and ends with `evidence`, `data_quality`,
and `next_action`. Values have one of four truth states: `observed`,
`not_mature`, `unavailable`, or `unknown`. Only a successful scoped query may
produce zero. A report is deduplicated by its run/message key.

Owner message types:

1. `ACTION_RECEIPT` immediately after a real publish/listing/ad/store mutation.
2. `CHECKPOINT` at declared 6h/24h/72h/7d windows; young values remain null.
3. `DAILY_PRODUCT` once per active product with funnel and economics.
4. `EXPERIMENT_DECISION` only after a mature comparable cohort; includes
   winner/loser/insufficient-data and the exact mutation made.
5. `SYSTEM_ALERT` immediately for failed, uncertain, duplicate, lease, auth,
   account-route, or data-quality failures.
6. `WEEKLY_PORTFOLIO` across all products with contribution, concentration,
   learned/retired tactics and next capped experiments.

Examples use labels resolved from manifests, but calculations always use stable
IDs. Adding a product therefore changes configuration/adapters, not the report
protocol or truth rules.

### 8.2 オーナー向け本文は自然な日本語

`owner_report_language`は商品言語と独立したプロフィール設定で、現在の値は`ja`とする。英語ebookや将来のスペイン語商品であっても、オーナー報告は日本語で届く。内部の英語キーをそのまま表示したり、IDを本文の中心に置いたりしない。

採用する文章構造：

```text
結論：今日は何が起きたか
  ↓
根拠：確認できた数字と取得元
  ↓
意味：良化・悪化・未成熟・判断不能のどれか
  ↓
処置：システムが何を変更したか
  ↓
次：いつ何を試す／再計測するか
  ↓
確認情報：URL・ID・receipt・evidence
```

例：

```text
日本語ebookの最初のwatercolor動画についてお知らせします。

投稿は正常に公開されています。ただし、公開からまだ23分なので、
再生数や売上を評価できる段階ではありません。

現在確認できている商品ページへのアクセスは0件です。これは計測に
成功した実測値です。注文や売上はまだ集計時間前なので0件とは扱いません。

この動画を失敗とは判断せず、24時間後にもう一度確認します。
あなたが操作する必要はありません。

確認情報：投稿URL、experiment ID、計測証拠
```

自然文テンプレートの設計正本は
`docs/superpowers/specs/2026-08-02-natural-japanese-telegram-ux-design.md`。

## 9. What the owner experiences after all 18 steps

```text
06:00  INTEL reads new app, creator, video, ad, keyword, and KDP evidence
          |
07:00  Mobile App Scaler chooses one bottleneck experiment per app
          |-- aniccaios: store/onboarding/paywall/retention/UA action
          `-- honne:     store/onboarding/paywall/retention/UA action
          |
08:00  Ebook Seller chooses demand-backed JP/EN work
          |-- improve or publish an owned book/listing
          `-- create attributed content from that book
          |
09:00  Shared creative registry renders inside each product-dedicated agent
          |-- slideshow / ReelClaw / MoneyPrinterTurbo
          |-- JP watercolor accounts -> ebook-ja only
          |-- EN monk accounts -> ebook-en only
          |-- EN OmniAvatar: current primary under Spec 28; other use remains gated
          `-- GPU challenger only inside a bounded experiment
          |
DAY     ASC/KDP/Gumroad/Postiz/browser actuators perform leased actions once
          |
NIGHT   stores + analytics return impressions, installs, orders, paid,
        retention, refunds, spend, contribution, MRR/revenue
          |
21:00  evidence writes back to playbook/hook EWMA; winner kept, loser retired
          |
21:05  owner receives one deduplicated Telegram report with evidence and next action
```

The owner no longer watches browser automation, refills a HeyGen queue, reads source material for the loops, or guesses whether a post worked. The owner sees verified business movement and intervenes only for an irreversible decision.

完成後の体験を自然文で要約すると、朝は「昨日どの商品が動き、何が売れ、何がまだ分からないか」、夜は「どの実験を残し、何を止め、明日何を試すか」が届く。問題がない日はダッシュボードを開く必要がない。異常時だけ、二重実行を避けるために何を止め、どのread-only確認を行っているかが即時に届く。

Visible benefits:

- Two apps have separate, complete funnels and a mathematical route to $10k gross MRR each.
- The initial JP and EN ebook products each have dedicated accounts, two storefront paths, and content-to-order attribution toward `$10k` rolling 30-day settled net revenue per language product; only proven recipes expand into a portfolio.
- The monk becomes an owned, consistent multilingual character instead of a HeyGen rental dependency.
- Routine avatar output has a zero-render-cost local path; paid GPU is spent only on a measured challenger or fallback.
- Every action is leased/idempotent; duplicate posts, duplicate publication actions, and cron collisions become measurable failures instead of silent damage.
- Telegram shows facts: what was learned, what changed, what earned, what failed, evidence, and the next experiment.
- OpenClaw can be stopped without losing scheduling, secrets, reporting, or state.

The system does not make $10k inevitable. It makes the route observable and self-correcting: each day either a funnel metric/revenue improves or the failed hypothesis is retired with evidence, preventing repeated blind work.
