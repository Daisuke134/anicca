# OpenClaw Self-Heal Engine — Design Spec

- **Date**: 2026-07-01
- **Author**: Claude Code (dev IDE) with Dais
- **Status**: DESIGN — awaiting review
- **Subsystem**: A of 2 (A = Self-Heal / この spec, B = Self-Improve / 別 spec)
- **Target code location**: `~/.openclaw/` (LIVE runtime, branch `main-internal` trunk)
- **Method**: Superpowers spec-driven + VCSDD (fresh-context adversary) + GLVS harness

---

## 1. Problem (grounded in REAL incidents observed 2026-07-01)

人間（Dais）が今 loop の中にいる。障害の検知器が Dais 本人になっている:
`[障害発生] → Dais が Telegram で気づく → Claude に伝える → Claude が直す`。
これを消す。目標:
`[障害発生] → watchdog が ground truth を検知 → 自動修復 → green 検証 → 詰まった時だけ Dais に1通 escalate`。

### 1.1 実測した失敗タクソノミ (evidence, not hypothetical)

| # | 失敗クラス | 実例 (2026-07-01) | 既存対応の欠陥 |
|---|---|---|---|
| F1 | **Config invalid → CLI 起動不能** | `plugins.entries.hivemind: dist/index.js not found` が config 全体を invalid にし `Could not start the CLI` | in-scheduler の `anicca-health` cron は scheduler が起動しないと fire しない。**監視者が被監視対象と共に死ぬ** |
| F2 | **依存欠落 crash-loop** | `agentmail-webhook`: `ERR_MODULE_NOT_FOUND: Cannot find package 'express'` ×189 → err log 62MB | プロセスを restart するだけで npm 依存を入れない → **無限 crash loop** |
| F3 | **バイナリ欠落 crash-loop** | `clip-core`: `tmux: command not found` → 5分毎 `DEAD → restarting` 無限 | restart するが tmux を install しない → **永久ループ** |
| F4 | **Scheduler / heartbeat 停止** | heartbeat session が N分以上更新されない / gateway プロセス消失 | 外部からの liveness 検知が無い |
| F5 | **Disk 逼迫** | `df < 10GB` / err log 肥大 (F2 が 62MB) | `anicca-disk-hourly` はあるが log 肥大を root cause に遡らない |
| F6 | **Provider / model 障害** | pinned free model が 402/403 / 無応答 | failover 経路が散在 |
| F7 | **健全に見えるcronの副次破壊（silent collateral damage）** | 2026-07-04: `disk-janitor`(10分毎、`lastRunStatus=ok`)の `find workspace -name 'reelclaw*' -mtime +2 -exec rm -rf` が **永続アセット庫** `workspace/reelclaw-assets/`（reelclaw 6 family全部が参照する video seed/music/hooks symlink）を丸ごと削除。当のcronは「成功」のまま。実際の失敗（`FATAL: src-final not found`）は依存先の別cronが**数時間後**発火するまで顕在化しない | 既存 doctor-monkey の SCAN は `lastRunStatus=error` のみ検知 → **成功したcronが他のcronの前提を壊すクラスは一切監視されない**。同一 glob が独立した2箇所（`skills/disk-janitor/run.sh` と `~/scripts/disk-cleaner.sh`、後者は git 管理外）にコピペされており、DRY違反が同一バグの二重発生を招いた |

### 1.2 既存 self-heal 資産（= 断片化 かつ **未配線**。統合対象）

現状 `~/.openclaw/cron/jobs.json` に散在する health/heal 系 cron（統合前）:
`anicca-health` (毎時) / `anicca-disk-hourly` (10分、2026-07-04 disk-cleaner.sh v9 に統合済み disable) / `anicca-cron-doctor` (日次) /
`anicca-gcal-heal` / `anicca-account-health-daily` / `anicca-postiz-health-daily` /
`monk-factory-en-recovery` / `anicca-credit-monitor` / `agentmemory-mcp-cleanup` 他。

★ 2026-07-04 追加発見 ★: Netflix Simian Army 型の **`anicca-doctor-monkey` / `anicca-janitor-monkey` / `anicca-conformity-monkey`** は SKILL.md + scripts が **完全に実装済み**（5-strategy escalation、`pin_to_infra: true`、`do_not_delete: true` 明記）だが、**`cron/jobs.json` に一度も登録されたことがない**（`git log -S` で確認、ヒット0件）。これを監視する `anicca-monkey-watchdog`（launchd、10分毎相当）は 2026-06-23 から毎日 `DOWN: 全3体 missing` を検知し続けているが、① alert先の Slack channel は死んでいる（他211 cronは既に Telegram へ移行済みなのにこのwatchdogだけ取り残された）② 「missing」ケースへの自己修復ロジックが無い（stale/error のcronは`openclaw cron run --wait`で再実行するが、missingは検知して終わり）。**= 自己修復システムを監視する仕組みが、11日間ずっとアラートを鳴らし続けながら誰にも聞こえず、修復アクションも取らずにいた。これが「なぜ自分でエラーを直せないのか」の直接の答え。**

問題: ① 統一タクソノミ無し ② 共有 remediation playbook 無し ③ 盲目 restart（F2/F3）④ 監視者が scheduler 内（F1 の盲点）⑤ **設計・実装済みの自己修復資産が配線されずに死蔵**⑥ **監視者の監視者が無い（alertが死んだchannelに落ちて誰も拾わない）**⑦ **同一 remediation ロジックがDRY違反で複数箇所にコピペされ、片方だけ直しても再発する（F7）**。

---

## 2. Goal (provable finish line — GLVS)

`done` = **注入した各失敗クラス F1–F6 を、人間介入ゼロで検知→修復→green 検証まで自律実行できることを、実障害注入テストで実証**する。

具体的 verifiable condition:
1. **F1 注入**: `openclaw.json` に不正 plugin entry を注入 → watchdog が N 分以内に検知・除去・`openclaw config validate` = valid・CLI 復帰。
2. **F2/F3 注入**: 依存/バイナリを外す → watchdog が「restart でなく root-fix（`npm install` / `brew install`）」を実行し、プロセスが green（実 side-effect 確認）に戻る。restart だけで終わらない。
3. **F4 注入**: gateway を kill → 外部 liveness probe が検知・再起動・heartbeat 復活。
4. **F5 注入**: ダミー巨大 log 生成 → 検知・rotate/truncate・root cause（どの process か）を記録。
5. **F6 注入**: model を無効 key に → failover が次 free model に切替、cron が再稼働。
6. **F7 注入**: 保護対象ディレクトリを模した使い捨てディレクトリ名を作り disk cleanup 系スクリプトを走らせる → asset-integrity probe が「削除される前に」保護 list と照合し除外することを実証。かつ既存の2箇所（`skills/disk-janitor/run.sh`, `~/scripts/disk-cleaner.sh`）が単一の保護パス manifest を参照する（コピペ2重管理の廃止）ことを確認。
7. **Escalation**: agent tier が N 回試行しても直せない人工障害 → Dais に**1通だけ** Telegram（洪水でなく）。
8. **VCSDD**: 上記を fresh-context adversary が disk から検証 PASS + 私が実障害注入 E2E を実走して green。

## 2.0 Phase 0 — 即実行（既存の死蔵資産を配線するだけ、新規実装ではない）

★ 下記は「設計済み・実装済みだが配線されていないだけ」なので、TIER 0-3 の本格実装を待たず **今すぐ** 着手する ★:

1. `anicca-doctor-monkey` / `anicca-janitor-monkey` / `anicca-conformity-monkey` を `cron/jobs.json` に登録（各 SKILL.md 記載のスケジュール通り）。doctor-monkey 自身の安全プロトコル通り `SHADOW=1` で1回 bootstrap fire → 検証 → `SHADOW=0` に切替。`pin_to_infra`/`do_not_delete` を janitor-monkey 自身の allowlist からも保護。
2. `anicca-monkey-watchdog` の「missing」ケースに自己修復アクションを追加（該当 monkey の cron を自動再登録）。alert 先を死んだ Slack channel から Telegram（他211 cron と同じ経路）へ移行。
3. F7 remediation: 単一の「保護パス manifest」（例: `~/.openclaw/state/protected-paths.json` または同等）を新設し、`skills/disk-janitor/run.sh` と `~/scripts/disk-cleaner.sh` の両方がそこを参照するようリファクタ（現状は同一 glob が2箇所に手書きコピーされておりDRY違反 = 再発の温床）。`~/scripts/`（現在 git 管理外）を version control 下に置く。
4. Phase 0 完了後、fresh-context adversary で「本当に3体が稼働しているか」「watchdogのmissingケースが実際に自己修復するか」を disk から検証。

## 2.1 Non-goals (この spec の外)

- Subsystem B（Self-Improve = 各アカウント metrics 改善ループ）は**別 spec**（`2026-07-02-openclaw-self-improve-design.md` 予定）。
- 新機能追加・アーキ刷新は含まない。既存 runtime の信頼性層のみ。

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  TIER 0: EXTERNAL WATCHDOG (OpenClaw の外 = launchd / 独立 process)│
│  ★ 被監視対象と一緒に死なない ★ (F1 の盲点を塞ぐ)                  │
│  - probe: `openclaw config validate` / gateway pid / heartbeat鮮度 │
│  - config invalid or scheduler dead → TIER 1 の deterministic fix  │
│    を OpenClaw 非依存で直接実行 → 復帰後は TIER 2 へ委譲            │
└───────────────┬─────────────────────────────────────────────────┘
                │ (OpenClaw が生きている限り)
                ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 1: DETERMINISTIC PROBES + PLAYBOOK (self-heal engine 1本)   │
│  10個の散在 cron を 1 engine に統合。probe→remediate→VERIFY→retry  │
│  失敗クラス→修復の決定表 (下 §3.2)。restart は必ず root-fix 付き   │
└───────────────┬─────────────────────────────────────────────────┘
                │ (未知 / 決定表に無い失敗)
                ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 2: AGENT REMEDIATION (LLM + tools in a loop)               │
│  未知失敗を model が診断 (ground truth を読む) → 修復案 → 実行     │
│  → probe 再実行で green 検証。N 回で打ち切り                       │
└───────────────┬─────────────────────────────────────────────────┘
                │ (TIER 2 も N 回失敗)
                ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 3: ESCALATE — Dais に Telegram 1通 (last resort, 洪水禁止)  │
│  「F# を自動修復できなかった。試したこと: …。今の状態: …」         │
└─────────────────────────────────────────────────────────────────┘
```

### 3.1 設計原則 (実測から導出)

| # | 原則 | 導出根拠 (実例) |
|---|---|---|
| P1 | **監視者は被監視対象の外で動く** | F1: config 死ぬと in-scheduler health cron も死ぬ → TIER 0 は launchd |
| P2 | **restart でなく root-cause fix。修復後は必ず probe 再実行で green 検証** | F2 express欠落 / F3 tmux欠落 の crash loop = 盲目 restart の証拠 |
| P3 | **全ループに上限 + escalation（無限ループ禁止）** | F2 が 62MB = unbounded loop。BP「stopping conditions」 |
| P4 | **log/output 肥大は first-class probe** | 62MB err log = 症状。cap + root cause 追跡 |
| P5 | **判断は model、決定表に載る既知修復のみ deterministic** | building-effective-ai-agents.md: judgment は model、tool/算術/台帳のみ deterministic。regex 分類禁止 |

### 3.2 Deterministic remediation 決定表 (TIER 1)

| 失敗クラス | probe (ground truth) | deterministic remediation | verify (green条件) |
|---|---|---|---|
| F1 config invalid | `openclaw config validate` | invalid entry を特定し plugins.entries から除去（doctor --fix は cron model override を巻き戻すので不使用、手術的除去）| validate = valid & `openclaw status` 起動 |
| F2 依存欠落 | process err log に `ERR_MODULE_NOT_FOUND` | 該当 package を `npm install`（該当 dir）| process が再起動後 err 無しで稼働 + 実 side-effect |
| F3 バイナリ欠落 | `command -v <bin>` 失敗 | `brew install <bin>`（既知: tmux 等）| bin 存在 & process green |
| F4 scheduler dead | gateway pid 無 / heartbeat > N分 | gateway 再起動 | heartbeat session 鮮度 < N分 |
| F5 disk/log | `df` / log size | disk-hygiene cleanup + log rotate/truncate | df > 閾値 & log < cap |
| F7 asset破壊 | cron fire 前に、その cron が依存する既知アセットdir(保護パスmanifest記載)の存在+非空を probe | manifest にある全パスを全 cleanup script が共通参照(除外)。誤って消えていたら直近の git/履歴 run から復元を試みる | 依存元cronの `[[ -f ]]` 系 precondition が実行前にPASS |
| F6 model 障害 | pinned model へ ping | 次 free model へ failover | cron session が再稼働 |

**判断が要る部分（P5）**: 「この失敗はどのクラスか / 決定表に無い未知失敗をどう直すか」は TIER 2 の model が ground truth（log・status・df 出力）を読んで決める。ハードコードした regex 分類器は作らない。決定表は「既知・機械的形式の一致（`ERR_MODULE_NOT_FOUND` という固定文字列、`command -v` の exit code）」にのみ使う。

### 3.3 State (会話の外の SSOT)

- `~/.openclaw/state/self-heal-ledger.jsonl` — 1行=1修復イベント（timestamp / 失敗クラス / probe出力 / 実行した remediation / verify結果 / tier / escalatedか）。
- これが「本当に自己修復しているか」を後から監査する ground truth。dashboard-sync が拾える形。

---

## 4. Verification plan (VCSDD — 「本当に self-heal する」を証明)

BP: 完了 = 「cron が存在する」ではない。**実障害を注入して復旧を実走観測**する。

1. **RED**: F1–F6 各々に対し「注入スクリプト + 期待復旧」の failing test を先に書く（例: 不正 entry 注入 → まだ watchdog 無い → CLI 死ぬ = RED）。
2. **GREEN**: watchdog + engine を最小実装で各 test を green に。
3. **ADVERSARY (fresh context)**: `vcsdd:vcsdd-adversary` が disk のみから検証。特に「restart だけで verify してないか」「ループ上限あるか」「TIER 0 が本当に OpenClaw 非依存か」を binary PASS/FAIL。
4. **NO-MOCK E2E (私が実走)**: 実際に hivemind 型 entry を注入 → watchdog が除去 → `openclaw status` 起動を私が目視。F2 は実際に node_modules を消して npm install 復旧を観測。fake/dry run 禁止（HARD 0.24）。
5. **DONE** = 4-D 収束（spec ✓ test ✓ impl ✓ verification ✓）+ adversary PASS + 私の E2E green。

---

## 5. Rollout (L1 → L2 → L3, Loop Engineering)

| 段 | モード | 内容 |
|---|---|---|
| L1 | report-only | watchdog は検知して ledger + Telegram 報告のみ（修復せず）。誤検知を炙り出す |
| L2 | assisted | deterministic 決定表（TIER 1）の修復だけ自動、未知は報告 |
| L3 | unattended | TIER 2 agent 修復も自動、Dais は TIER 3 escalation のみ受ける（= 目標状態） |

各段の昇格条件 = 前段で N 日間 false-positive ゼロ & 修復成功率 X%。

---

## 6. Open questions (実装前に spec 内で解消する。Dais に投げない)

- N（heartbeat 鮮度閾値・retry 回数・escalation 間隔）の具体値 → §5 L1 の実観測データで決定（今は placeholder 禁止のため暫定: heartbeat 15分 / retry 3 / escalation は同一失敗24hに1通）。
- TIER 0 の実体 = launchd plist（macOS native, OpenClaw 非依存）を第一候補。実装 plan で確定。
- 既存10 cron の統合 = engine 完成後に段階的に置換（いきなり全削除しない）。

### 6.1 TIER 2/3 実装時に追加した安全設計（2026-07-04 追記、HARD RULE 0.21 準拠）

TIER 1 実装中に実発見: `openclaw cron list --all --json` で 200 cron 中 70 が error 状態だが、
その大半（Larry/Comedy/Life-call 等の content-posting/distribution cron）は "配信を実投稿でテスト
するな = cron の仕事" (memory `feedback_never_test_by_direct_posting`) の対象そのもの。TIER 2 (agent
診断) / F6 (model failover) の**修復後 verify** を TIER 0/1 と同じ「即 `openclaw cron run --wait` して
確認」でやると、content-posting cron を手動発火 = 実際に投稿/送信してしまう重大違反になる。

★ 追加ルール ★:
1. TIER 2 の診断 agent 呼び出しは **read-only 診断 + infra-level fix のみ**（gateway restart 等）を
   許可。cron 自身の payload（投稿/送信/生成タスク）を実行させることは prompt で明示的に禁止する。
2. 修復後の verify は、対象 cron が content-posting/distribution 種別（payload に
   post/publish/send/投稿 等のキーワードが含まれる、または該当 skill が公開系）の場合 ★ 強制発火し
   ない ★。ledger の `verify_result` は `pending_next_scheduled_run`（+ 次回 schedule 時刻）とし、
   TIER 2 の**次回サイクル**でその cron の `consecutiveErrors`/`lastRunAtMs` が実際の自然発火後に
   改善したかを事後確認する（forced-fire ではなく wait-and-observe）。
3. F6 (model failover) も同様: pinned model 変更後の verify は、対象 cron が content-posting なら
   同じ「次回自然発火を待って確認」パターンに従う。非 posting 系（health-check 系等）は従来通り
   `openclaw cron run --wait` で即時 verify して良い。

---

## 7. Next

この spec を Dais レビュー → `writing-plans` で bite-sized 実装 plan → worktree → TDD 実装 → adversary → E2E。
その後 Subsystem B（Self-Improve）の spec に着手。
