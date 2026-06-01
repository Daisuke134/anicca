# CONTENT_FACTORY_SPEC.md — Anicca 全 social content の最終設計

最終更新: 2026-05-29 (Dais 厳命 + 今セッション学習を凍結)

## 0. 目的 / Bible
> 「scrape once → analyze structure → store as pattern in library → generate fresh forever」
> 出典:
> - Adrià Martinez (TikTok content workflow): clone-don't-template → library → propose from library (URL不要)
> - Alex Nguyen (StudyTok AI UGC × Hermes Agent): 1 viral hook → 100 fresh variations → views feedback → kill loser / double winner
> - Nicole (warmup playbook): 5%like / 1-2 follow / 1-2 repost / 30-60min FYP / 3-4 day warm before post
>
> 我々のオリジナル禁止。Bible 通り実装する。

## 1. アーキテクチャ (END STATE)

```
                       ┌──────────────────────────────────────┐
                       │  EXTERNAL signal sources             │
                       │  • TikTok scrape (riyagoelrs/pytok)  │
                       │  • RevenueCat (subs/trial)           │
                       │  • Anicca product (RC events)        │
                       └────────────┬─────────────────────────┘
                                    ▼
        ┌────────────────────────────────────────────────────┐
        │ LIBRARY (~/.openclaw/state/content-library/)       │
        │  pattern-card-ja.jsonl   (structural clones)       │
        │  pattern-card-en.jsonl                             │
        │  pattern-widget-ja.jsonl                           │
        │  pattern-widget-en.jsonl                           │
        │  pattern-4.7-ja.jsonl  / pattern-4.7-en.jsonl      │
        │  pattern-iam.jsonl     / pattern-mantra.jsonl      │
        │  pattern-larry-ja.jsonl/ pattern-larry-en.jsonl    │
        │  pattern-honne.jsonl                               │
        │   →  each entry =                                  │
        │       { source_url, hook, structure, niche_tags,   │
        │         emotion, image_refs, cta_position,         │
        │         observed_views, observed_likes }           │
        │  hook-perf.jsonl (per-cron, per-hook 14d windows)  │
        │  account-history.jsonl (per-account posted ids)    │
        └────────────┬───────────────────────────────────────┘
                     ▼
        ┌────────────────────────────────────────────────────┐
        │ PROPOSE-FROM-LIBRARY (no scrape per run)           │
        │  • 14d anti-repeat (hook + image + structure)      │
        │  • niche-rotation (untouched 30d preferred)        │
        │  • image-fit selection (real source photos)        │
        │  • recursive-improver で hook 5案採点→winner       │
        └────────────┬───────────────────────────────────────┘
                     ▼
        ┌────────────────────────────────────────────────────┐
        │ RENDER (deterministic shells)                      │
        │  reelclaw card:    create-ugc-reel.sh + DanSUGC    │
        │  reelclaw widget:  create-video-reel.sh + template │
        │  4.7 / iam / mantra: slideshow render shells       │
        │  monk: HeyGen pipeline (existing run-daily.sh)     │
        │  watercolor: existing pipeline                     │
        └────────────┬───────────────────────────────────────┘
                     ▼
        ┌────────────────────────────────────────────────────┐
        │ POST (camofox 直接 / no Postiz)                     │
        │  post-tt-direct.sh  (multi-account session 切替)   │
        │  post-ig-direct.sh  (reCAPTCHA 対策)               │
        │  post-yt-direct.sh  (YT Studio upload)             │
        │  post-x-direct.sh   (x.com tweet)                  │
        │  → release URL を返す。返らなければ exit !=0       │
        └────────────┬───────────────────────────────────────┘
                     ▼
        ┌────────────────────────────────────────────────────┐
        │ TRACK + LEARN (24/48h views/likes/saves/shares)    │
        │ • tiktok-scraper で per-post metric pull           │
        │ • RC で per-post subs CVR (post時刻+24-72h window) │
        │ • hook-perf.jsonl 更新                             │
        │ • winner → 3日後に variant 自動生成                │
        │ • loser → library から status=killed               │
        └────────────────────────────────────────────────────┘
```

## 2. CRON × END STATE 表 (全 26 cron)

| family | cron | platform | account | 投稿頻度 | render | post |
|--------|------|----------|---------|----------|--------|------|
| reelclaw | ja-card-1 | TT+YT | @anicca.jp8 / @anicca-jp | 12:15 | UGC reel + fresh hook | direct |
| reelclaw | ja-card-2 | TT+IG+YT | @anicca.jp8 / @anicca.video / @anicca-jp | 21:20 | 〃 | direct |
| reelclaw | en-card-1 | TT+IG | aniccaen2 / anicca.ai | 12:45 | 〃 EN | direct |
| reelclaw | en-card-2 | TT+IG | aniccaen2 / anicca.ai | 21:30 | 〃 EN | direct |
| reelclaw | ja-widget-1 | TT+IG+YT | @anicca.jp8 / @anicca.video / @anicca-jp | 08:05 | widget reel | direct |
| reelclaw | ja-widget-2 | TT+IG+YT | 〃 | 18:20 | 〃 | direct |
| reelclaw | en-widget-1 | TT+IG | aniccaen2 / anicca.ai | 09:30 | widget EN | direct |
| reelclaw | en-widget-2 | TT+IG | 〃 | 19:00 | 〃 | direct |
| reelclaw | honne-ja-1 | TT | honne_reveal | 10:10 | honne demo | direct |
| reelclaw | honne-en-1 | TT | honnevideo | 07:00 | honne demo EN | direct |
| reelclaw | honne-en-2 | TT | honnevideo | 19:30 | 〃 | direct |
| monk-en | 0800 | TT+IG | @anicca_cemetery / @monk.anicca | 08:00 | HeyGen | direct |
| monk-en | 2100 | TT+IG | 〃 | 21:00 | HeyGen | direct |
| watercolor | jp-0700 | TT+IG | @obou_anicca / @obou.anicca | 07:00 | existing | direct |
| watercolor | jp-2000 | TT+IG | 〃 | 20:00 | existing | direct |
| 4.7 | ja-morning | TT+IG | @anicca.jp / @anicca.jp1 | 10:15 | slideshow JA | direct |
| 4.7 | en-morning | TT+IG | aniccaen2 / anicca.ai | 09:00 | slideshow EN | direct |
| iam | photo-en | TT+IG | aniccaen2 / anicca.ai | 月水金 07:35 | photo slot | direct |
| iam | photo-ja | TT+IG | @anicca.jp / @anicca.jp1 | 火木土 08:35 | 〃 | direct |
| iam | color-en | TT+IG | aniccaen2 / anicca.ai | 月 13:35 | color slot | direct |
| iam | color-ja | TT+IG | @anicca.jp / @anicca.jp1 | 月 14:35 | 〃 | direct |
| mantra | ja | TT+IG | @anicca.jp / @anicca.jp1 | 月水金 20:35 | mantra slide | direct |
| larry | ja-1 | TT+IG | @anicca.jpx / @anicca.bochi | 16:30 | larry slide JA | direct |
| larry | en-1 | TT+IG | aniccaen2 / anicca.ai | 16:35 | larry slide EN | direct |
| X | (5本) | X | @aniccaxxx | (再設計後 復活) | text+image | direct |

## 3. HARD RULES (横断)

| # | rule |
|---|------|
| HR-1 | scrape は library 構築の 1回のみ。日次は library から generate (Bible #1) |
| HR-2 | 14日 anti-repeat: hook + image + structure 全てに適用 (per-account) |
| HR-3 | cron message は `bash <run.sh> [args]` 1コマンド原則・LLM curl 組立禁止 |
| HR-4 | post step は exit=0 ⟺ platform URL 取得済。「posted」だけの自己申告禁止 (false-ok 即 ERROR) |
| HR-5 | harvester は Postiz/camofox の release-URL cross-check で false-ok 検知 |
| HR-6 | 翌朝 06:00 health-check cron が昨日の URL 全て curl 200 verify |
| HR-7 | rotation 廃止 (rotation = 同じ素材 N日サイクル) ⇄ regeneration (毎日 library から fresh) |
| HR-8 | DRY_RUN/fake/mock 全 cron 禁止 (HARD RULE #14 既存) |

## 4. 実装 TODO (依存順)

### 🟥 T0 — content cron が「実際に出る」を回復 (Postiz経路でOK)

1. reelclaw 9 cron pure-bash orchestrator 化 + cron message 張替 (1/9 完了)
2. monk 3→2 + agent-wait + dup 防御
3. 4.7-en / iam ×4 / mantra cron enable + 1回手動 fire で動作確認
4. 4.7-ja slide-1 文字はみ出し修正 (テンプレ CSS)
5. **JA card overlay 重なり修正** (text+image 位置 bug・widget は OK)
6. Daily Affirmation YT cron params 調査・修正
7. tiktok-warmup-en-anicca-monk-2 DRY_RUN → 実モード
8. harvester に false-ok cross-check 追加
9. HARD RULE #15 (rotation 廃止) memory + CLAUDE.md 追記

### 🟧 T1 — ★ CONTENT QUALITY (variety/no-slop) — library + scrape + propose

> Dais 最終指示 (本セッション最終 chat):「the first job is to set these posting strategies super good. MAKING CONTENT GOOD. then we get into the other shit」
> = まず content を良くする (Postiz 経路でいい)。camofox 直接化は その後。

10. tiktok-scraper / Apify skill 導入 (variety + no-slop source)
11. niche 別 1回 scrape → library 初期構築 (Bible: scrape ONCE)
12. 構造解析 → pattern-<family>.jsonl
13. account-history.jsonl per-account (14d anti-repeat)
14. propose-card-{ja,en}.sh
15. propose-widget-{ja,en}.sh
16. propose-4.7/iam/mantra-*.sh
17. propose-larry/honne/monk-*.sh
18. reelclaw card create-ugc-reel.sh per-run render (DanSUGC keep)
19. reelclaw widget create-video-reel.sh per-run render

### 🟨 T2 — Postiz完全廃止 → camofox 直接化 (TT先 → YT → IG の順)

> Dais 指示:「once all that is confirmed, we scale the TikTok posting manual to every cron and then go do the YT and IG stuff manually, to completely replace Postiz」

20. post-tt-direct.sh (TikTok から先に migrate)
21. post-yt-direct.sh (YT 次に)
22. post-ig-direct.sh (IG 最後・reCAPTCHA 対策)
23. 17 アカ camofox 初回ログイン + session 永続
24. 全 cron message を camofox 経路に張替 (Postiz API 全削除)
25. release URL + 翌朝 06:00 health-check cron

### 🟩 T3 — track + learn (views feedback)

27. per-post views/likes/saves/shares を post 後 6h/24h/48h で pull
28. RC subs CVR cross-ref (post時刻+24-72h window)
29. hook-perf.jsonl 更新
30. winner→ variant 自動生成 / loser→ status=killed
31. heartbeat が日次サマリを #metrics へ

### 🟦 T4 — warmup 全アカ自動化

32. warmup-tiktok / warmup-instagram / warmup-youtube を camofox 化
33. Nicole playbook 実装 (5%like / 1-2 follow / 1-2 repost / 30-60min FYP scroll)
34. per-account warmup state (days_complete / shadowban check)
35. warmup verify cron (fingerprint 健全性)

### 🟪 T5 — X 5本再設計 + 100アカ factory

36. grok-x-research 再設計 (toxic AI-slop 防止)
37. viral-article-republish (週1 blog→X thread・毎週違う角度)
38. anicca-x-marketing-daily-info (役立ち情報 DM形式)
39. sao-content-factory-daily (SAO autonomous AI 業界深堀り)
40. donation-x-daily (受給者ができたら復活)
41. post-x-direct.sh
42. tiktok-account-factory を camofox 化 (物理iPhone要件撤廃)
43. persona JSON 100件 + 各 persona: 作成→7日 warmup→post→views 学習 autonomous
44. account health monitor (shadowban 検知 + 自動 rotation)

### 🟫 BACKLOG (既存 #1-48 中 pending)

43. #12 旧 yangmun-monk / watercolor-monk skill 削除
44. #13 VOICE JP pipeline (voice_id 8cjRZwLoPS7Sl0oRIZWL)
45. #25 politician 12本 決着
46. #28 停止実験 daily 系 復活
47. #31 cron 統合 (corey×6→1 / naist×11→3-4 / factory-bp×3→1)
48. #47 CFO コスト追跡 (HeyGen / OpenAI / voice / Anthropic / Postiz)
49. #48 cron 自律整理 (heartbeat self-cleanup)
50. Clipspal 手動 DL → post (clipspal.com/dashboard/mission-control camofox login)

## 5. 状態ファイル一覧

| file | 役割 |
|------|------|
| ~/.openclaw/state/content-library/pattern-*.jsonl | scrape済 viral 構造ライブラリ |
| ~/.openclaw/state/content-library/hook-perf.jsonl | hook別 24h/48h views |
| ~/.openclaw/state/content-library/account-history.jsonl | per-account posted ids/structures |
| ~/.openclaw/state/posted-urls/<cron>/<date>.jsonl | 配信成立 URL 永続 |
| ~/.openclaw/state/warmup/<account>.json | warmup 進捗 |
| ~/.openclaw/state/personas/<id>.json | factory persona |

## 6. 関連 memory / spec

- SOCIAL_AUTONOMY_SPEC.md (本spec 移行前)
- ANICCA_AUTONOMY_SPEC.md (自己修復)
- memory/feedback_no_rotation_only_fresh_generation.md (新規作成予定)
- memory/feedback_reinvention_of_the_wheel_is_a_sin.md (Bible 通り実装ルール)
- memory/reference_social_account_mapping.md (Postiz integration ID マップ)
- memory/feedback_post_manually_not_api_zero_views.md (camofox 直接の根拠)
