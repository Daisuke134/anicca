# ANICCA_AUTONOMY_SPEC — 自己修復 + ログ + cron アーキ統合 仕様書（マスター）

最終更新: 2026-05-25 / 上位ドキュメント。`SELF_HEALING_SPEC.md`(exec-policy/lateness) を内包し全体を束ねる。

---

## 0. 完成の定義（THE GATE・全 workstream に例外なく適用）

> **「コードを書いた」は完成ではない。「実装 → e2e 実走 → 失敗したら直す → 実 e2e が通る」まで回して初めて完成。**
> これが 100% 動く事を保証する唯一の方法。fresh evidence 無しの「done」は嘘（verification.md / HARD RULE #8）。

```
各タスクのループ:
  1. IMPLEMENT  実ファイルに実装
  2. RUN E2E    本物の入力で端から端まで実走（dry-run/fake 禁止）
  3. READ       出力全部 + exit code + 生成物を自分の目で検証
  4. 失敗 → FIX → 2 に戻る（実 e2e が通るまでループ）
  5. CLAIM      evidence 付きで初めて完了宣言 + #metrics 報告
```
- DRY_RUN / "would post" / stub / mock は成功でなく **失敗**。
- 社会投稿系は「投稿 URL を開いて表示確認」まで。動画は ffmpeg で全フレーム目視まで。

---

## 1. アーキテクチャ（自己修復の閉ループ）

```
 cron/beat 実行
   └▶ run-logger + event_log : 各stepの WHY を span-log + 構造化JSONL に残す  [W1]
        └▶ cron-doctor(detector✅) + CRIME検知 : exit≠0 も fake(dry-run/would post)も「故障ブリーフ」化 [W2]
             └▶ open-problems registry（単一の真）
                  └▶ heartbeat §3.5(✅) : 偽ok判定 → 文脈+コード読んで根本修正（LLM・非ハードコード） [W3]
                       ├ self-diagnose : 自分のログを引用付き物語化       [W3]
                       ├ regression-search : いつ/どのコミットで壊れたか    [W3]
                       ├ 直せない → claude-router : 別モデル(codex/gemini)に委譲 [W3]
                       ├ 別Mac死亡 → peer-revive(✅) : fund/restart/reassign/revive
                       └ 人間必須 → hire-human : 人を雇って実行            [W7]
                  └▶ push前に consensus検証（誤修復防止）                  [W2]
        └▶ friction-detector : 溜まる問題を気づく前に検知（proactive）      [W3]
 最外殻: launchd watchdog(✅化必要) : heartbeat/gateway 自身が死んでも蘇生   [W4]
 可視化: 内部 dashboard : cron健全性/エラー/修復履歴/CRIME件数/MRR を1画面    [W5]
 駆動: HEARTBEAT.md を claude-p + openclaw の2体が同じ記憶で30分ごと(dual-harness✅)
```

---

## 2. Workstream（各 §0 ゲートを必ず通す）

### W1 — ログ土台（#21）【最優先・他全部の前提】
- **新規** `~/.openclaw/skills/_shared/run-logger.sh`: trace-id log + `rl_run` で step span-log full捕捉 + `rl_fail` が末尾15行(WHY)を引用 + EXIT trap(kill/ハングでも1通)。
- **新規** `~/.openclaw/skills/_shared/event_log.py`: sutando port。`$ANICCA_HOME/state/events/events-YYYY-MM-DD.jsonl` に `{ts,node,kind,...}`。`log_event("cron.failed",cron=,step=,why=)`。
- **修正** `~/.openclaw/skills/anicca-monk-factory-v3/scripts/run-daily.sh:24`: `$(render-submit|grep)` を span-log保存→cat→ファイルからgrep に。
- **e2e**: run-daily を実走 → render-submit が失敗した場合に FATAL行 + exit が run-log と #metrics 両方に出る事を確認。成功時は PROJECT_URL が取れる事を確認。

### W2 — fake/CRIME 検知 + 誤修復防止（#33）
- **修正** `~/.openclaw/skills/anicca-core/scripts/cron-doctor.sh`(現 detector-only): payload正規表現 `(_DRY_RUN=true|--dry-run|\[would-run\])` と run-log `(would post|should work|mocked|stubbed|fake)` を CRIME としてブリーフに 🔴 タグ追加。
- **修正** `HEARTBEAT.md §3.5`: CRIME は「成功でなく失敗」として本番化 or hire-human or 削除。修復を push する前に self-verify or claude-router 2nd opinion(consensus)。
- **e2e**: politician dry-run cron を1本走らせ → cron-doctor が 🔴CRIME としてブリーフに出す事を確認。

### W3 — Sutando 自己修復5機能 port（#36）
SOURCE `~/.research/self-improving-agents/sutando/`:
| 機能 | source | target |
|---|---|---|
| self-diagnose narrate | skills/self-diagnose/ | ~/.openclaw/skills/self-diagnose/ |
| regression-search | skills/regression-search/scripts/{find-regression,diagnose-call}.py | ~/.openclaw/skills/regression-search/ |
| claude-router/codex/gemini | skills/{claude-router,claude-codex,claude-gemini}/ | 同名 |
| friction-detector | src/friction-detector.py | ~/.openclaw/skills/anicca-core/scripts/ |
| event_log | src/event_log.py | W1 と一体 |
- 既存(✅): peer-revive(別Mac蘇生) / dual-harness。
- **e2e**: 故障を1件仕込み → self-diagnose がそれを引用付きで物語化 → heartbeat が拾って直す → 直った事を検証、を1周。

### W4 — launchd watchdog（#37）【NO LATER】
- pfangueiro/claude-code-agents 方式。`~/Library/LaunchAgents/ai.anicca.watchdog.plist` KeepAlive。heartbeat/gateway/agent-api の `.alive` stale or プロセス無を検知→再起動。snapshot-protected(設定drift復元)。
- **e2e**: gateway を kill → watchdog が再起動する事を確認。

### W5 — 内部 dashboard（#38）
- sutando `src/dashboard.py` port。event_log JSONL を集計し cron健全性/直近エラー/修復履歴/CRIME件数/MRR を1画面。
- **e2e**: 故障を1件起こす → dashboard に赤で出る → 直る → 緑になる、を確認。

### W6 — heartbeat 脳化 + 文脈整合（#34, #30）
- **新規** `~/.openclaw/skills/_shared/watch-sweep.sh`: watcher を1パスで。返信前に `state/interaction-ledger.jsonl`(誰/thread/既返信/保留) を必ず読む→二重返信/誤爆/文脈外し排除。
- **修正** `HEARTBEAT.md §2`: watch-sweep を追加。watch/poll 18 cron を削除。
- **e2e**: 既知の未読メールで watch-sweep を実走→文脈に合った返信が1度だけ出る事を確認。

### W7 — hire-human primitive（#35）
- **新規** `~/.openclaw/skills/hire-human/scripts/dispatch.sh "<task>" "<budget>" "<deadline>"`: Upwork/Contra/ボランティアに投稿→支出ゲート(L1≤$5自動/L2 $5-50 #metrics/L3 >$50承認)→納品検証→返す。
- **e2e**: 小さな実タスク($5以内)を1件実発注→納品受領→検証、を1周（または安全に検証可能な範囲で）。

### W8 — monk factory 無人化（#22, #23, #24, #17, #12, #13）
- #22 render-submit 死因特定(W1で見える)→堅牢化 / #23 手動IG を CloakBrowser で実装→Postiz廃止 / #24 monk-en cron×3 delivery修正→1本統合。
- **e2e**: monk-en cron を実走 → TikTok+IG 両方に投稿 → 両 URL を開いて動画再生確認。失敗したら直して再走（通るまで）。

### W9 — TikTok warm-up（#32）
- warm-up skill（camofox で human-like 運転: FYP寄せ/like率5%/micro-influencerフォロー/repost）+ warm-up-verify(following/repost カウント→#metrics)。
- **e2e**: warm-up を1日分実走→verify が「温まってる」を返す事を確認。

---

## 3. cron 大掃除（208 → 約60）

| バケツ | 本数 | 方針 |
|---|---|---|
| KEEP | ~45 | 壁時計必須(wake/投稿peak) + 重pipeline + 本業インフラ |
| DELETE | ~55 | §3.1 + §3.2 |
| → HEARTBEAT 吸収 | ~18 | watch/poll(W6) |
| SIMPLIFY 統合 | 25→8 | corey×6→1 / larry×7→2 / naist×11→3-4 / factory-bp×3→1 / reelclaw-card×4→2 |

### 3.1 DELETE — テスト/today/TEMPLATE/smoke 残骸（#27・~13本）
`naist-today-test` / `tuning-skills-today-test` / `*-today-2026-05-15`(music/sao) / `TEMPLATE-test-slideshow-en/ja` / `monk-factory-TEST/TEST2/TODAYRUN` / `anicca-recruit-tomb-smoke-today` / `today-iam-color-en-1115` / `today-iam-color-ja-1120` / `today-iam-photo-en-1105` / `today-iam-photo-ja-1110` / `today-mantra-ja-1125` / `anicca-tomb-slideshow-ja-today-2026-05-21`

### 3.2 ⚠️ 停止実験 daily系（#28）— 削除しない・1本ずつ調査→直して復活
**方針転換 2026-05-25: 削除禁止。Dais が実使用中(IAM はドライブで稼働)。** 各 cron を「なぜ止めたか」調査→価値あれば直して再enable→実走確認。Dais が各々の要否を知るまで削除保留。
対象(disabled・正味29本): iam系4 `anicca-iam-color-en/ja-daily` `anicca-iam-photo-en/ja-daily`(使用中) / `anicca-mantra-slideshow-ja-daily` / `reelclaw-honne-en-1/2` / auto-research個別5 `auto-research-experiment/grant/hypothesise/literature/write` / donation3 `donation-monthly/annual-rollup/x-daily` / 旧monk `yangmun-monk-evening/noon` `watercolor-monk-noon` / `anicca-x-cold-dm-daily` `anicca-x-painpoint-daily` / `opening-cafe-cross-post-daily` `skill-fixer` `skill-for-you-daily/weekly` `autonomy-check` `anicca-meeting-pre-check-hourly` `anicca-retreat-slideshow-daily`
※完全dead(スキル実体無)候補 `copy-viral-format-factory-3day` `virality-copy-factory-weekly` のみ別途要確認。

### 3.3 DELETE — 重複（#29）
`comedy-booking-jp-dais-weekly 2aa3abbc`（`e782937e` と完全同一・`channel:last`でエラー中）。

### 3.4 決着が要る
- **politician 12本（#25）**: read-only5(monitor/news/bill_tracker/opensecrets/receptive)は POLITICIAN_DRY_RUN外して即LIVE。action7はDRY_RUN廃止→hire-human(W7)で登録/PAC/treasurerをアンロック→本番。署名偽造禁止。
- **trustmrr（#26）**: cron パスを `anicca-trustmrr-lister` → `trustmrr` に修正。`trustmrr-list-weekly`/`trustmrr-sell-decision-monthly` 復活→自律出品・売却。
- **trustmrr-list-weekly** はスキル実体 `~/.openclaw/skills/trustmrr/scripts/list-products.sh` を指す事。

---

## 4. 既に DONE（別エージェント実装・2026-05-25）
- 別エージェント分: `exec-policy-guard.sh`(exec=full保証) ✅ / `cron-doctor.sh` detector化 ✅ / `anicca-peer-revive`(別Mac蘇生) ✅ / dual-harness ✅ / `SELF_HEALING_SPEC.md` ✅spec
- このセッション(2026-05-25 Claude)分 — 全て実走検証 + private-backup push 済:
  - W1 `_shared/run-logger.sh` + `_shared/event_log.py` ✅ / #22 `render-submit.sh` avatar-default fix ✅
  - #39 `anicca-core/scripts/cron-run-harvester.py`(全208cron→event_log・CRIME検知誤検知ゼロ) ✅
  - #36 `self-diagnose/`(gather+narrate) ✅ / `regression-search/find-regression.py` ✅ /
        `claude-router`+`claude-codex`+`claude-gemini`(codex委譲・auth=.env OPENAI_API_KEY) ✅ /
        `anicca-core/scripts/friction-detector.py` ✅
  - #37 `anicca-core/scripts/watchdog.sh` + launchd `ai.anicca.watchdog`(5min・live) ✅
  - #38 `anicca-core/scripts/dashboard.py`(internal+redacted public) ✅
  - HEARTBEAT.md §2/§3.5 に harvester/friction/self-diagnose/regression/claude-router 全配線 ✅
  - cron掃除: #26 trustmrr パス修正 ✅ / #27 today・test残骸17本削除(latest-papers保護) ✅ /
    #29 重複comedy-booking削除 ✅ / monk-en×3 delivery修正 ✅  → 208→190 jobs
- 🔶 残(全てDais判断待ち): #34 watch/poll18本→heartbeat畳み(live cron無効化) / #25 politician決着 /
  炙り出したdry-run18本の本物化or停止 / #23 手動IG(Safari) / #31 統合 / #28 停止実験復活 /
  aniccaai.com/dashboard公開デプロイ / #40 両ハーネスe2e(観測で確定)

## 5. 着手順
`W1(#21)✅ → W2(#33)✅ → W3(#36)✅ → W4(#37)✅ → W5(#38)✅ → [Dais判断] W6(#34) → W8(monk) → §3残り → §3.4(#25) → W9(#32)`

## 6. 関連
SELF_HEALING_SPEC.md / anicca_core_sutando_infra(memory) / cron_autofix_heartbeat_loop(memory) / exec_policy_lockout_incident(memory) / verification.md(HARD RULE #8)
