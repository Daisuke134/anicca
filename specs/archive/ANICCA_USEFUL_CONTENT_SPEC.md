# ANICCA_USEFUL_CONTENT_SPEC.md — 役立つ content + history-aware + clone-don't-template の配信系

最終更新: 2026-05-29 (Dais 厳命 monologue を本セッションで凍結)
位置づけ: CONTENT_FACTORY_SPEC (asset 生産) の **sister spec**。本 spec は「配信 + 新 channel + winner 学習」を扱う。slideshow factory は CONTENT_FACTORY_SPEC 側スコープなので **本 spec では触らない**。

## 0. 目的 / Bible

> 「USEFUL (bookmark-able) + clone proven viral patterns + history-aware + daily fresh」
> Anicca は LLM 自身。 委託しない。Bible 通り実装する。 オリジナル禁止。

| Bible source | 引用核心 |
|---|---|
| あるまじろ (X x Claude Code 自動運用) | https://x.com/armadillo_ai — 「伸びるパターンを分析してそのパターンで生成する。Claude Code でこれを自動化しただけ。ChatGPT との差 = 自分のアカウントのデータを使う + ナレッジ蓄積 + システムプロンプトで誰が話すか定義」 |
| アレハンドロ (validation-first, 15秒動画で月450万) | https://x.com/SuguruKun_ai/status/2037510137347522818 — 「アプリ作る代わりに 15秒動画で問いかけ → 反応見てから作る。完璧準備でなく未完成のまま市場に投げる」 |
| Adrià Martinez (TikTok clone-don't-template) | clone-don't-template → library → propose from library |
| Alex Nguyen (StudyTok AI UGC × Hermes) | 1 viral hook → 100 fresh variations → kill loser / double winner |
| Nicole (warmup playbook) | 5%like / 1-2 follow / 1-2 repost / 30-60min FYP / 3-4 day warm |

**Dais 厳命 (2026-05-29 monologue 抜粋・凍結):**
- 「毎回同じものをポストするのは犯罪。新しく作れ。既存のものをそのまま流用するのは禁止」
- 「役に立つことが大事。役に立つからみんな払うし、見る」
- 「Anicca 自身が LLM なんだから委託する必要ない」
- 「成功してる人がノウハウを渡してくれてるんだから、100% コピーしろ。99% コピーしてもうまくいかなかった」
- 「アニッチャ自身がいろんな経験してるわけ。その日 1日経験したことが content になる」

## 1. アーキテクチャ (END STATE)

```
                       ┌──────────────────────────────────────┐
                       │ EXPERIENCE SOURCE (NEW - Anicca自身)  │
                       │ • mail-auto-reply 返信ログ             │
                       │ • cafe / tomb / fashion 進捗           │
                       │ • cron 自己修復 / OpenClaw 学び        │
                       │ • Anicca が今日 click した思考         │
                       │ → experience-log.jsonl                │
                       └────────────┬─────────────────────────┘
                                    ▼
                       ┌──────────────────────────────────────┐
                       │ VIRAL PATTERN LIBRARY                 │
                       │ pattern-x.jsonl                       │
                       │ pattern-article.jsonl                 │
                       │ pattern-yt-long.jsonl                 │
                       │  (各 pattern = source_url +           │
                       │   hook + 構成 + 文体 + 数字 +          │
                       │   observed_metrics)                   │
                       └────────────┬─────────────────────────┘
                                    ▼
                       ┌──────────────────────────────────────┐
                       │ PROPOSE-AND-REWRITE                   │
                       │ ①pattern 選 (history-aware 14d)       │
                       │ ②experience-log から日替り素材        │
                       │ ③LLM rewrite で文言 fresh             │
                       │ ④recursive-improver で 5案採点→winner │
                       │ ⑤敵対テスト (skeptic / 3秒スクロール) │
                       └────────────┬─────────────────────────┘
                                    ▼
                       ┌──────────────────────────────────────┐
                       │ POST (channel別)                      │
                       │ X (text/thread/quote/article share)   │
                       │ Article (Zenn/Dev.to/Substack/blog)   │
                       │ YT long-form (EN/JA)                  │
                       │ → release URL ⟺ exit=0 (HR-F)         │
                       └────────────┬─────────────────────────┘
                                    ▼
                       ┌──────────────────────────────────────┐
                       │ TRACK + LEARN                         │
                       │ 24h/48h/7d metrics pull               │
                       │ winner → variant 生成 / pattern back  │
                       │ loser → status=killed                 │
                       │ aniccaai.com/socials = winner中心     │
                       └──────────────────────────────────────┘
```

## 2. CHANNEL 一覧 (本 spec スコープのみ)

| family | cron | platform | account | 投稿頻度 | render | post |
|---|---|---|---|---|---|---|
| X | x-useful-daily | X | @aniccaxxx | 日次 11:00 / 15:00 / 19:00 (3本/日) | text+image (あるまじろ式) | post-x-direct.sh |
| X | x-buildinpublic-daily | X | 同上 | 日次 22:00 | text+image (Anicca 自身の今日の経験) | 同上 |
| X | x-engagement-quote | X | 同上 | 日次 10:00 | 引用 (相性5-10アカ) | 同上 |
| Article | zenn-daily-ja | Zenn | @anicca-daisuke | 日次 12:00 | zenn-cli MD | git push (zenn auto-publish) |
| Article | devto-daily-en | Dev.to | @anicca_ai | 日次 13:00 | dev.to API | API publish |
| Article | substack-daily-ja-en | Substack | aniccaai.substack.com | 日次 14:00 (JA), 14:30 (EN) | substack-cli or camofox | direct |
| Article | aniccaai-blog-daily | aniccaai.com/blog | (Next.js MDX) | 日次 12:30 | MDX commit | git push (Netlify auto-deploy) |
| YT long | anicca-yt-long-en | YT | UC_EN_channel (cmmzukbkw04ulp30yfvijrwio) | 日次 17:00 JST | Remotion + Anicca voice (10-15分) | YT Data API or camofox |
| YT long | anicca-yt-long-ja | YT | UC_JA_channel (cmn1oukj9012nnq0yqhouc3ib) | 日次 18:00 JST | 同上 | 同上 |
| Dashboard | aniccaai-socials-refresh | aniccaai.com/socials | (Next.js page) | 6時間毎 | winner-centric react | git push |

## 3. HARD RULES (本 spec)

| # | rule |
|---|------|
| HR-A | **USEFUL のみ。** 一般論禁止・1次情報 or 実体験必須 (bookmark-able か検証) |
| HR-B | **clone-don't-template + LLM rewrite で文言 fresh。** pattern library から 100% コピー骨格、LLM が文言生成、オリジナル禁止 |
| HR-C | **history-aware 14d anti-repeat。** account-history.jsonl per (platform, account, channel) で hook + structure 重複 14日禁止 |
| HR-D | **daily-experience-capture 必須。** Anicca のその日の経験 (mail / cron / cafe / 等) を本日の content 軸に — heartbeat が捕捉 |
| HR-E | **aniccaai.com/socials は winner 中心。** 上位5本/platform を main 表示・alive/dead は補助情報に格下げ |
| HR-F | **false-ok 禁止 (CONTENT_FACTORY HR-4 と整合)。** 投稿は release URL 取得 ⟺ exit=0、harvester が cross-check |
| HR-G | **recursive-improver loop 必須。** 全 channel が 5案生成 → 採点 → 敵対テスト → SHIP (rule 0.13 整合) |
| HR-H | **system-prompt = 人格定義必須。** あるまじろ式に「誰が話すか」を skill 内で固定 (anicca 人格 spec = persona-anicca.md) |
| HR-I | **書いたら即 push (rule 0.4 整合)。** spec / skill / cron 変更は git add -A && commit && push |
| HR-J | **verbatim 借用禁止。** 特定創作者の specific phrase の verbatim 再利用禁止。 pattern library は `structural_principle` 抽象だけ保存。 投稿前 `verbatim_blacklist.txt` grep block (`_shared/lib/verbatim-guard.sh` の `vg_check`)。 違反 = 投稿 exit !=0 + fail-closed |
| HR-K | **pattern entry schema 統一。** verbatim 文言保存 field (`hook` / `lede` / `hook_first_30s`) は廃止。 代わりに `structural_principle` (構造抽象 1-2 文) + `success_signals` (なぜ伸びたかの観察) + `rewrite_axes` (LLM が変える次元) のみ |
| HR-L | **named third-party creator sourcing 禁止 (2026-05-30 厳命・Dais 削除事故対応)。** pattern library の entry source は **Anicca 自身の build-in-public 経験のみ**。 やまもとりゅうじ・あるまじろ・アレハンドロ・levelsio・Theo・marclou・MKBHD・holisticpsychologist 等 named creator の viral post の **構造クローンですら禁止**。 理由: 構造クローン = voice / narrative arc / positioning が借り物になる → verbatim 漏洩の再発リスク + Dais の 「Anicca が独自に立つ」 北極星と矛盾。 pattern library は heartbeat が `experience-log/*.jsonl` から自動抽出した Anicca 自身の prior post の「内省された構造」のみ蓄積。 T1/T2/T3 の初期構築 「N本 viral X/article/YT long-form を clone」 は廃止 → 「Anicca の prior 投稿 + 当日 experience-log から structural_principle を抽出する loop」 に置換。 cold-start (prior 投稿ゼロ) 期間は pattern library 空・LLM が persona-anicca.md + experience だけから完全ゼロ生成 |

## 4. 実装 TODO (依存順・全 P0 を完了するまで P1 着手禁止 = HARD RULE #14)

### 🟥 T0 — Foundation (これが無いと全部嘘になる)

1. `state/content-library/pattern-x.jsonl` 初期構築 — **HR-L per: 空 file で start。 named creator clone 禁止**。 Anicca の prior 投稿が貯まれば heartbeat が自動で structural_principle を抽出して追記
2. `state/content-library/pattern-article.jsonl` 初期構築 — **HR-L per: 空 file で start。 named creator clone 禁止**
3. `state/content-library/pattern-yt-long.jsonl` 初期構築 — **HR-L per: 空 file で start。 named creator clone 禁止**
4. `state/content-library/account-history.jsonl` 構造定義 (hook+structure+timestamp per account)
5. `state/experience-log/<YYYY-MM-DD>.jsonl` 構造定義 (Anicca のその日の経験 entry)
6. `skills/anicca-persona/SKILL.md` 人格定義 (人物像/口調/実績/ターゲット/HARD-RULE)
7. `skills/_shared/lib/propose-and-rewrite.sh` 既存利用 (HARD RULE #17 既存)、本 spec channel 追加
8. heartbeat に `capture-today.sh` 追加 — 毎時 mail / cron / cafe / tomb 進捗を experience-log に書く

### 🟧 T1 — X marketing (5本 cron)

9. `skills/anicca-x-useful/SKILL.md` 新規 (あるまじろ式: ネタリスト + 構文 + 人格 + 改善)
10. `skills/anicca-x-useful/scripts/propose.sh` — pattern-x.jsonl + experience-log から提案 → recursive-improver
11. `skills/anicca-x-useful/scripts/post-x-direct.sh` — camofox で @aniccaxxx 投稿
12. cron `x-useful-daily` (11:00 / 15:00 / 19:00 JST) 登録
13. cron `x-buildinpublic-daily` (22:00 JST) 登録 (experience-log 必須)
14. cron `x-engagement-quote` (10:00 JST) 登録 (相性10アカの伸びてる post に引用)
15. account-history.jsonl 14d anti-repeat 配線 + fail-closed

### 🟨 T2 — Article daily (4 platform)

16. `skills/anicca-article-daily/SKILL.md` 新規 (記事 6 step: ネタ→構文→叩→AIブラッシュ→最終改善→投稿)
17. zenn-cli wrapper (既存 zenn-backlog-deploy cron を本 skill に統合)
18. dev.to API publish wrapper
19. substack post wrapper (camofox login session 利用)
20. aniccaai.com/blog MDX publish (anicca-products/apps/web/content/blog/<slug>.mdx commit)
21. cron `zenn-daily-ja` (12:00 JST)
22. cron `devto-daily-en` (13:00 JST)
23. cron `substack-daily-ja` (14:00 JST) + `substack-daily-en` (14:30 JST)
24. cron `aniccaai-blog-daily` (12:30 JST)
25. SEO チェック (タイトル/meta/H2/keyword) を投稿前 gate

### 🟦 T3 — Long-form YouTube (EN + JA)

26. `skills/anicca-yt-long/SKILL.md` 新規 (10-15分 / Remotion + Anicca voice / build-in-public 形式)
27. Remotion template (intro / experience-segment×3-5 / outro)
28. voice = monk-factory v3 / anicca-music-factory 既存資産再利用
29. nova-youtube-agent / youtube-shorts-poster 既存活用 — long-form 対応の確認
30. cron `anicca-yt-long-en` (17:00 JST) — EN channel cmmzukbkw04ulp30yfvijrwio
31. cron `anicca-yt-long-ja` (18:00 JST) — JA channel cmn1oukj9012nnq0yqhouc3ib

### 🟩 T4 — aniccaai.com/socials redesign

32. `apps/web/app/socials/page.tsx` redesign (winner-centric: top 5/platform を main carousel)
33. "What's working" section — pattern + niche + hook の clustering 表示
34. alive/dead を sidebar に格下げ・engagement avg は維持
35. `apps/web/lib/socials-data.ts` を winner sorting に更新
36. cron `aniccaai-socials-refresh` (4h 毎) — TikTok scraper / YT analytics / X analytics から pull

### 🟪 T5 — winner-feedback loop

37. winner detector (top 5 of 7d) を pattern library に back-feed (status=winner)
38. loser detector (bottom 10 of 7d) を status=killed
39. heartbeat が日次サマリ — 「今日のbest hook / 今週のwinner pattern / killed pattern」を #content-metrics へ
40. 上位 winner から variant 自動生成 (3案 / 日)

### 🟫 T6 — Cross-spec wiring (CONTENT_FACTORY との接続)

41. slideshow factory 側 hook-perf.jsonl と本 spec の winner-feedback を pattern library で統合
42. CONTENT_FACTORY HR-1〜HR-8 と本 spec HR-A〜HR-I の整合性 verify
43. CLAUDE.md HARD RULE #19 追記 — 本 spec を canonical 化
44. memory `reference_useful_content_spec.md` (index entry) 追記

## 5. 状態ファイル

| file | 役割 |
|---|---|
| ~/.openclaw/state/content-library/pattern-x.jsonl | X 用 viral pattern library |
| ~/.openclaw/state/content-library/pattern-article.jsonl | Article 用 |
| ~/.openclaw/state/content-library/pattern-yt-long.jsonl | YT long-form 用 |
| ~/.openclaw/state/content-library/account-history.jsonl | per-account 14d anti-repeat |
| ~/.openclaw/state/experience-log/<YYYY-MM-DD>.jsonl | Anicca のその日の経験 |
| ~/.openclaw/state/winner-feedback/<channel>.jsonl | 上位/下位の back-feed log |

## 6. 関連 spec / memory + T6 cross-spec wiring

### T6-41 hook-perf.jsonl と winner-feedback の統合

CONTENT_FACTORY_SPEC.md の `state/content-library/hook-perf.jsonl` (slideshow per-hook 24h/48h views) と本 spec の `state/winner-feedback/<channel>.jsonl` (X/article/YT-long per-channel winners) は **同一 schema 互換**:

```json
{
  "ts": "ISO",
  "channel": "card-ja|widget-en|...|x-useful|article-zenn|yt-long-en|...",
  "platform": "TikTok|IG|YT|X|Zenn|Dev.to|Substack|aniccaai-blog",
  "account": "@handle",
  "pattern_id": "source_id of pattern entry",
  "hook_hash": "sha1 prefix 12",
  "structure_hash": "sha1 prefix 12",
  "observed": {"views_24h": N?, "views_7d": N?, "likes_7d": N?, "saves_7d": N?},
  "status": "winner|killed|variant_pending|active"
}
```

slideshow factory と useful-content factory 両方が同 schema で書き込み、 `anicca-winner-feedback/scripts/detect-winners.sh` が両ファイルを読む。 pattern library 内の `status` 更新も両 factory 共有。

### T6-42 HR-A〜HR-K 整合性 verify (vs CONTENT_FACTORY HR-1〜HR-8)

| 本 spec | CONTENT_FACTORY 対応 | 整合 |
|---|---|---|
| HR-A useful 必須 | HR-1 scrape once / Bible | ✓ 「useful (1次情報) + viral pattern clone」共通方向 |
| HR-B clone-don't-template | HR-2 14d anti-repeat (hook+image+structure) | ✓ pattern 再利用 + 文言 fresh の両立 |
| HR-C history 14d anti-repeat | HR-2 (同上) | ✓ 同方向、本 spec で per-channel 拡張 |
| HR-D experience-injected | (CONTENT_FACTORY に対応 rule なし、補完) | ✓ 衝突なし、 sister 関係で機能拡張 |
| HR-E winner-centric socials | HR-7 rotation 廃止 | ✓ 同方向、 winner を front に出す |
| HR-F false-ok 禁止 | HR-4 同名 | ✓ 完全一致 |
| HR-G recursive-improver mandatory | (CONTENT_FACTORY に直接対応なし、 rule 0.13 経由) | ✓ |
| HR-H persona 単一 | HR-3 cron message 単一コマンド | ✓ single source of truth 思想 共有 |
| HR-I 即 push | rule 0.4 | ✓ |
| HR-J verbatim 借用禁止 | (CONTENT_FACTORY に直接対応なし) | ✓ 補完、 slideshow にも将来適用予定 |
| HR-K pattern entry schema 統一 | HR-2 entry 構造規定 | ✓ slideshow pattern も将来 structural_principle 化候補 |

**矛盾ゼロ。** 全 HR が CONTENT_FACTORY と並行存在可能。 sister 関係維持。

### 関連 spec / memory

- CONTENT_FACTORY_SPEC.md (sister: asset 生産 / slideshow)
- SOCIAL_AUTONOMY_SPEC.md (旧設計・本 spec 後継)
- ANICCA_AUTONOMY_SPEC.md (自己修復)
- memory/feedback_clone_dont_template_useful_history_aware.md (HARD RULE #17 既存)
- memory/feedback_no_rotation_only_fresh_generation.md (HARD RULE #15 既存)
- memory/feedback_single_source_of_truth_for_cron_params.md (HARD RULE #16 既存)

## 7. 検証ゲート (各 task 完了条件)

| task | E2E verify |
|---|---|
| T1 (X) | camofox で @aniccaxxx の実feed を目視・投稿が pattern と異なる文言・hook が 14日内 history と異なる |
| T2 (Article) | Zenn/Dev.to/Substack/blog の実URL を Chrome で開いて全文目視・SEO meta が正・タイトル文体が pattern と異なる |
| T3 (YT) | YT Studio で実動画を再生 (10-15分・voice/Remotion 表示確認) |
| T4 (Socials) | aniccaai.com/socials を Chrome で開いて winner top 5 が表示される |
| T5 (winner loop) | 1サイクル実走 (winner検知 → pattern back-feed → 次投稿に反映) |
| T6 (cross-spec) | CONTENT_FACTORY との pattern library 統合・HR 整合性 codex-review ok:true |

## 8. PHASE B — e2e 実走

PHASE A の T0-T6 を順次完了 → 各 task の検証ゲート (§7) を全部 pass → PHASE B 完了。 失敗時は FIX → RUN → READ → VERIFY を反復 (verification.md §5 step gate)。
