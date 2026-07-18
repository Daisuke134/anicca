# PC repo 単一化インベントリ — claude-p 系全 loop の依存地図（gig 以外を含む）

作成: 2026-07-18 / 種別: READ-ONLY 地図（実装・移動・編集は一切していない）
Dais 裁定: **profitable-claude(PC) が human-funded(claude-p) loop の唯一の家。clone すれば earn loop が
単体で回る状態にする。anicca/openclaw への local 依存はゼロにする（OSS として他人がそのまま使える）。**
姉妹文書（gig 単体の詳細地図・移設レシピ）: `docs/superpowers/specs/2026-07-18-gig-migration-to-profitable-claude-inventory.md`
TO-BE 構成の正本: `docs/reference/2026-07-18-multi-loop-repo-structure-research.md`

**本文書は観測（実 tool_result）のみ。推測は「推測」と明記。全 path は絶対パス。**

---

## §0. エグゼクティブサマリ（結論を先に）

### loop 総数
human-funded（Dais の金/アカウントで動く）loop = **16 系統**、分析クラスタ = **10**。
self-funded（franklin1/franklin2、~/.blockrun・~/.franklin2-home、crypto wallet 燃料）は **対象外**として全除外。

- **移設済み・PC で live = 6**: bounty / affiliate / connector / explorer / life-manager（PC `bin/start-all.sh`
  が registry から起動）＋ article-writer（物理は PC 内だが launchd が scheduler ＝ registry で意図的に external）。
- **未移設（~/anicca / ~/anicca-project / ~/.openclaw に残存）= 10**: gig / clip / clip-promote / video(停止中) /
  reddit / capafy / claude-p-economy(x402) / aso / paywall / screenshot。

### PC repo は既に 90% 完成している（"新設" ではなく "拡張・整合"）
`~/profitable-claude/` は既に次を持つ（全て実測）:
- `config/loop-registry.json`（7.1K、**11 loop 登録**: live 6 = bounty/affiliate/gig/life-manager/explorer/connector、
  external 5 = capafy/article/pm/hl/sol）。article エントリの notes に「物理移設済みだが launchd が scheduler
  なので意図的に external」と明記済み。→ **後続 Task #12「registry 新設」は「既存 registry の拡張・整合」に修正すべき。**
- `skills.lock`（vendor manifest、5 entry、sha256 付き）→ **browser 共有基盤の vendor はこの仕組みに乗せる。**
- `install.sh`（article のみ wired の skeleton、他 loop は TODO）/ `.env.example`（21 キー、`GIG_KYC_CONFIRMED`
  `COCONALA_HANDLE` 等）/ deny-by-default `.gitignore`。
- `README.md` の "Repo Boundary": Promotion out（PC から出す）は「no installer credentials + no human-owned
  payout rail の時のみ」。**「graduate to anicca（skill を anicca へ戻す）」記述は存在しない**（grep 0）＝
  Dais 裁定「PC が正本・全吸収」と矛盾しない。破棄すべきテキストは無い。

### 最も危険な結合点 TOP 3（全て file:line 実測）
1. **claude-p の x402 seller コードが franklin(self-funded・対象外) と物理的に同一ファイル。**
   `~/anicca/skills/earn/x402-sell/` の `serve.mjs` / `serve-v2.mjs` / `watch-inflow.sh` を全 seller が直接 exec。
   `serve-claude-p-boot.sh:8` が DIR をハードコード、`franklin1 boot:24` も同 DIR、`watch-inflow.sh` は 3 plist が
   同一 .sh を共有。`seller-boot.sh` は `.anicca-founder` 版と `.blockrun` 版が **byte-identical**（diff 実測）。
   さらに `agent-economy-loop`(claude-p) / `franklin-loop` / `franklin2-loop` の 3 plist が全て同一
   `~/anicca/runtime/anicca-daemon.sh` を指し **ANICCA_HOME env だけで分岐**。→ **move 厳禁。claude-p 用に
   boot+serve を複製してから切替、franklin 側は不触。** 最難関、最後に着手（§4-G）。
2. **browser 共有基盤（cdp_*.py / session_vault.py / ensure_browser.sh）+ _shared を self-funded も literal 参照。**
   franklin1/2 の launcher（`.blockrun/skills/earn/{gig,clip,video}/*-cli.sh`, `self/reddit-loop`, `self-fix.sh`,
   `polymarket redeem.py:108`, `lib/spawn_pin.py`）が runtime で **literal `$HOME/anicca/skills/browser/
   ensure_browser.sh` と `_shared/lib/*.mjs` を直接呼ぶ**（両 HOME で grep 実測、franklin2 側 64 match / 19 files）。
   franklin は 6 browser script + _shared の物理コピーを自配下に持つが launcher が anicca literal のまま
   （移行途中の二重化、推測）。→ **move+anicca tombstone 不可。PC へ copy(vendor) + skills.lock 記録が確定方式**（§3）。
3. **capafy / article / reddit がスケジューラ多重化。**
   article は launchd 6本（PC を指す）で完結。capafy は launchd 3本 + openclaw cron `anicca-capafy-daily-publish`
   (enabled) + `~/.openclaw/skills/capafy-autopublish` の 4 系統に散在。→ 移設時に cron 側を潰さないと二重起動。
   **混同注意**: openclaw cron `anicca-backlink-reddit-weekly`(enabled) は reddit-loop ではなく **別 skill
   `anicca-backlink-builder`**（§4-E）。

---

## §1. human-funded loop 一覧表（launchctl/plist/diff 実測ベース、自己申告でない）

| # | loop | earn手段 / 何をする | code 現在地（絶対パス） | trigger（実測） | 稼働 | PC 状態 / 難易度 |
|---|---|---|---|---|---|---|
| 1 | **gig** | Coconala で受注・納品 | `/Users/anicca/anicca/skills/earn/gig/` | launchd 5本 + tmux core（healthcheck 300s 他） | LIVE | 未移設（②古い、姉妹 spec）/ 高 |
| 2 | **clip** | IG @aiclipsvault へ Reel 自動投稿 | `/Users/anicca/anicca/skills/earn/clip/` | launchd `clip-loop-aiclipsvault` **のみ有効**（21600s=6h, clip_pass.sh）。producer/proactive/healthcheck 5本は 2026-07-12 一斉 .disabled | LIVE | 未移設 / 中 |
| 3 | **clip-promote** | clip の拡散/promote 補助 | `/Users/anicca/anicca/skills/earn/clip-promote/` | clip 従属（単独 label 無し） | 補助 | 未移設（clip と同梱）/ 低 |
| 4 | **video** | faceless finance short + ChangeNOW affiliate | `/Users/anicca/anicca/skills/earn/video/`（SKILL.md 有） | **完全停止**（有効 plist ゼロ、healthcheck も 07-12 disabled。設計は tmux+cron 23 */4） | 停止中 | 未移設 / 低（練習台）|
| 5 | **reddit** | backlink/集客 marketing | `/Users/anicca/anicca/skills/self/reddit-loop/` | launchd 2本（daily 08:35 + healthcheck 300s） | LIVE | 未移設 / 高 |
| 6 | **capafy** | Capafy marketplace に skill 出品 | `/Users/anicca/anicca/skills/self/capafy-loop/` + `/Users/anicca/anicca/skills/earn/capafy-marketing/` + `/Users/anicca/.openclaw/skills/capafy-autopublish/` | launchd 3本（daily 08:10 / goal-monitor 09:00 / warmup 11:20）+ openclaw cron `anicca-capafy-daily-publish`(enabled 09:00) | LIVE | registry=external / **最高** |
| 7 | **claude-p-economy (x402 seller + founder runtime)** | x402 で API/research を売る（founder PM） | `/Users/anicca/anicca/runtime/anicca-daemon.sh` → `runtime/loop/index.mjs`（HOME=`/Users/anicca/.anicca-founder`）+ `/Users/anicca/anicca/skills/earn/x402-sell/serve-claude-p-boot.sh` | launchd `agent-economy-loop`(PID 12616, KeepAlive) + `x402-claude-p`(PID 644, :8412) + `x402-inflow-watch-claude-p`(cron :05/:35) | LIVE | **共有 runtime、複製方式で分離** / 高 |
| 8 | **bounty** | Algora bounty 発見/挑戦 | `/Users/anicca/profitable-claude/skills/bounty/` | PC `bin/start-all.sh`（registry live, daily 09:29） | 移設済 | **PC live**（self-contained） |
| 9 | **affiliate** | アフィリ carousel 日次投稿 | `/Users/anicca/profitable-claude/skills/affiliate/` | PC registry live, daily 08:41 | 移設済 | **PC live**（.openclaw/.cloak 強依存） |
| 10 | **connector** | 人脈/機会 intake→応募 | `/Users/anicca/profitable-claude/skills/connector/` | PC registry live, daily 07:35 | 移設済 | **PC live**（self-contained） |
| 11 | **explorer** | pain-point intake + 検証 | `/Users/anicca/profitable-claude/skills/explorer/` | PC registry live, daily 11:05 | 移設済 | **PC live**（self-contained） |
| 12 | **life-manager** | feedback/calendar/product レビュー | `/Users/anicca/profitable-claude/skills/life-manager/` | PC registry live, daily 10:15 | 移設済 | **PC live**（self-contained） |
| 13 | **article-writer** | build-in-public 記事を多媒体 publish | `/Users/anicca/profitable-claude/skills/article-writer/` | launchd **6本 全 LOAD 正常**（daily 06:00 / self-improve 22:30 / diary-digest 23:30 / audit Sun 22:00 / learn-whitelist Sun 03:00 / healthcheck 300s） | LIVE | **PC 内・依存刈りのみ** / 中 |
| 14 | **aso-loop** | iOS App Store 最適化（週次） | `/Users/anicca/anicca-project/.claude/skills/aso-loop/` | openclaw cron `aso-loop-weekly` = **enabled:false（無効）**。launchd/tmux 無し | 停止 | 未移設 / 低 |
| 15 | **paywall-ab** | RevenueCat paywall A/B | `/Users/anicca/anicca-project/.claude/skills/paywall-ab/`（openclaw 側に diff SAME コピー） | cron 現存せず（未セットアップ or 削除済み、推測）。launchd 無し | 手動 | 未移設 / 低 |
| 16 | **screenshot-ab** | App Store スクショ A/B | `/Users/anicca/anicca-project/.claude/skills/screenshot-ab/` | スケジューラ未登録（launchd/cron 両方なし、Slack 承認駆動の手動型、推測） | 手動 | 未移設 / 低 |

**除外した self-funded（対象外・実測で HOME が crypto wallet home）:**
`franklin-loop`(HOME=`/Users/anicca/.blockrun`) / `franklin2-loop`(HOME=`/Users/anicca/.franklin2-home`) /
`x402-franklin1` `x402-franklin2` `x402-inflow-watch-franklin1/2` / `sol-trade`(`sol-trade-earning-healthcheck`) /
`autohedge` / `sol-funding`(`com.anicca.sol-funding`) / registry の `pm`/`hl`/`sol` trade engines。

**要人間確認（推測を含む）**: PC の `config/loop-registry.json` に `pm`/`hl`/`sol` が `status:external-anicca` で
登録されているが、colony SSOT（`CLAUDE.md`）では trade 3 エンジン(PM/SOL/HL)は franklin(self-funded)の仕事。
**この 3 entry が claude-p founder のものか franklin のものか未確定** → SSOT に従い self-funded と見なし PC 単一化
からは除外を推奨（confirm 前に PC が pm/hl/sol を起動しないこと）。

---

## §2. 依存マトリクス（各 loop → local 依存、file:line 実測）

### 2-1. gig（詳細は姉妹 gig spec。代表のみ）
`gig_pass.sh:11,33,35` → browser 基盤 / `gig_daily_report.sh:6` → `~/.openclaw/.env`(Coconala creds) /
state=`~/gig/`(独立 repo `github.com/Daisuke134/anicca-gig`)。`~/loops/gig/` proactive。

### 2-2. clip（~/gig 参照ゼロ・gig と同族）
| 依存 | file:line 実測 |
|---|---|
| B browser 基盤 | `clip-cli.sh:33`（cdp_context_lease acquire clip）、`clip-cli.sh:38`（ensure_browser） |
| S _shared | `run.sh:34`（send-telegram）、`producer.sh:26`（load-instance-env） |
| O ~/.openclaw | `clip-healthcheck.sh:38-40`（heartbeat） |
| C ~/.cloak | `warm_step.py:41,135,152` |
| **state** | `~/clips/`（**実体 dir、移送対象**）+ `~/.openclaw/state/clip-earn-ledger.jsonl` + `~/.cloak/clip-*` |
| 同族自認 | `clip-cli.sh:52` に「ported from gig-cli.sh」 |

### 2-3. video（完全停止・~/gig 参照ゼロ）
| 依存 | file:line 実測 |
|---|---|
| B browser 基盤 | `video-cli.sh:32`（lease acquire video）、`video-cli.sh:37`（ensure_browser） |
| S _shared | `run.sh:13`（load-instance-env） |
| O ~/.openclaw | `run.sh:11`（`~/.openclaw/.env`） |
| C ~/.cloak | `onchain.py:30-37`（wallet） |
| **state** | `~/.cloak/earn-video-*` |
| 同族自認 | `video-cli.sh:51` に「ported from gig-cli.sh」 |

### 2-4. reddit
| 依存 | file:line / 実測 |
|---|---|
| B browser 基盤 | `reddit-loop-cli.sh:18` → `skills/browser/ensure_browser.sh` |
| C/camofox | `~/.cloak/reddit-accounts.json` + `~/.camofox/profiles/anicca/reddit1/` |
| O ~/.openclaw | `~/.openclaw/state/.reddit-loop-last-pass`（heartbeat）+ skill 内 `state/` |
| self-heal | `~/anicca/skills/self/self-fix.sh` + `~/anicca` git |
| **混同注意** | openclaw cron `anicca-backlink-reddit-weekly`(enabled) は reddit-loop ではなく **別 skill `anicca-backlink-builder`**。reddit-loop の cron ではない |

### 2-5. capafy（最も絡んだ束・4 系統）
| 依存 | 実測 |
|---|---|
| P vendored skill | `~/.openclaw/skills/capafy-autopublish/`（実処理・vendor CLI 内包、`scripts/daily_loop.sh` / `vendor/capafy-publisher/config.json`） |
| ~/anicca | `self/capafy-loop`（launchd daily）+ `earn/capafy-marketing`（goal-monitor / warm_jitter） |
| C/env | `~/.cloak` + `~/.openclaw/.env` |
| O state | `~/.openclaw/state/.capafy-loop-last-pass`, `.../capafy-loop-selfheal-request.json` |
| cron | openclaw cron `anicca-capafy-daily-publish`(enabled 09:00) |

### 2-6. claude-p-economy（x402 seller + founder runtime）★最難関★
| 依存 | file:line 実測 |
|---|---|
| R 共有 runtime | `agent-economy-loop.plist` = `~/anicca/runtime/anicca-daemon.sh` → `runtime/loop/index.mjs`（**franklin-loop / franklin2-loop と同一スクリプト**、3 plist 共有） |
| self-update 前提 | `anicca-daemon.sh:69` が起動毎に `~/anicca/skills/` を各 HOME へ **rsync コピー**、`:71` は node_modules を symlink、`:26` `REPO=$HOME/anicca`、`:108` `~/.openclaw/.env`、`:112` `resolve-identity.mjs` |
| P 共有 x402-sell | `serve-claude-p-boot.sh:8`（DIR ハードコード）→ 共有 `serve.mjs`。`serve-{franklin1,franklin2}-boot.sh` が同 dir。`watch-inflow.sh` は 3 plist が同一 .sh。`seller-boot.sh` は `.anicca-founder` 版と `.blockrun` 版が byte-identical（diff 実測） |
| 別 repo 依存 | `x402-monitor` / `x402-tunnel`（稼働中）は **第4のリポジトリ `~/anicca-oss/.worktrees/earn-x402/services/x402-endpoint/`** に依存 |
| state | `~/.anicca-founder`（wallet home、move しない） |
| env 分岐 | `ANICCA_HOME=/Users/anicca/.anicca-founder`, `ANICCA_BRAIN=claude-p`, `X402_PORT=8412`, `ANICCA_SLOT_ALLOWLIST=x402_sell` |

**要人間確認 2 つ:**
1. **wallet 二重**: claude-p の受取が `0x810F6D61...`（founder loop / `x402-seller-8412`）と `0x904B50d2...`
   （`serve-claude-p` / `inflow-watch`）の 2 系統混在。**移設時の取り違え注意。**
2. **`agent-economy-loop.plist` の `ANICCA_FUNDING=self` はコードと矛盾**（`brain.mjs:36` = claude-p is
   human-funded）。**funding 判定は plist の env でなく `ANICCA_BRAIN=claude-p` とコード（`brain.mjs:34`）で行う。**
   `x402-seller-8412` は exit 1 で停止中（`~/.anicca-founder/skills/...` の rsync コピーを exec する形）。

### 2-7. article-writer（PC 内だが self-contained でない・横断依存が残る）
| 依存 | file:line 実測 |
|---|---|
| creds | `~/.openclaw/.env`（note/substack/zenn creds、`publish-substack.sh:26-27`, `publish-note.sh:31-32`） |
| S _shared/telegram | `~/.openclaw/skills/_shared/venv-cloak` + `telegram-notify.sh`（`article-daily.sh:27,:149`） |
| B browser | `~/anicca/skills/browser/ensure_browser.sh`（`article-daily.sh:61`） |
| 素材源 | `~/anicca-project/docs`（diary-digest、`make-diary-digest.sh:122,:137,:167`） |
| C note/X 作業 | `~/.cloak/note-work`（`publish-note.sh:172,:267`）+ `~/.cache/anicca-clones/note-mcp`（`publish-note.sh:239`） |
| SEO 入力 | `~/.openclaw/skills/anicca-seo-rank-monitor/state`（`self-improve.sh:104,:238`） |
| X publish | CDP :9222 daily-driver 実セッション依存（`publish-to-x.sh:7`） |
| 公開ゲート | `article-daily.sh` 既定 DRAFTS ONLY、`ARTICLE_AUTOPUBLISH=1` で本公開（Dais decision #41）。state は全部 repo 内（`topics/queue`→`in-progress`→`done`、`state/articles.jsonl` 台帳） |
| 別系統（クラスタ外） | `~/.openclaw/skills/ai-entity-article-writer` = spec/doc 側（SKILL.md 95KB が runtime を片方向参照）。`auto-article-poster` / `substack-article` = launchd から呼ばれない手動 skill |

### 2-8. aso / paywall / screenshot（product growth skills・cron 単発型）
| loop | 依存 / 実測 |
|---|---|
| aso-loop | code=`~/anicca-project/.claude/skills/aso-loop/`; 依存=asc CLI のみ; cron `aso-loop-weekly` は **enabled:false**。⚠️ `~/.openclaw/skills/aso-loop` は **broken symlink**（実体は anicca-project 側のみ） |
| paywall-ab | 依存=RevenueCat MCP + `~/.openclaw/workspace/paywall-ab/apps.json`; `SKILL.md:216` が jobs.json を直 read/write + `/Users/anicca` ハードコード |
| screenshot-ab | 依存=asc CLI 0.48.0 + `~/.agents/skills/app-store-screenshots`; スケジューラ未登録 |

### 2-9. 移設済み PC loop の残依存
`bounty/connector/explorer/life-manager` = state 面 self-contained（OK）。`affiliate/article-writer` =
`~/.openclaw` / `~/.cloak` / `~/anicca` 強依存（外部参照 grep で PC skills 全体 116 files / 325 matches）。
**PC の telegram は `~/.openclaw/skills/_shared/scripts/telegram-notify.sh`**（anicca の `send-telegram.sh` とは
別物、混同するな）。

---

## §3. 共有基盤の PC 吸収案（実測で vendor(copy) 確定・move+tombstone 不可）

### 3-1. browser 6 script + _shared — **PC へ copy(vendor)、skills.lock に記録**
**参照元（anicca 内、実測）:** `earn/{clip,clip-promote,gig,video}`, `self/reddit-loop`, `self/self-fix.sh`,
`browser/SKILL.md`（browser 基盤）。`_shared` は上記に加え `earn/{polymarket-trade,sol-trade,self-improve,run.sh}`,
`economy/lending`, `anicca-life-manager`, `self/claude-p-mainloop.sh`, `self/coordinate`, `youtube-channel-creator`。

**self-funded の literal 参照（決定的・両 HOME で grep 実測）:**
`~/.blockrun/skills/earn/{gig,clip,video}/*-cli.sh`, `self/reddit-loop`, `self-fix.sh`,
`polymarket redeem.py:108`, `lib/spawn_pin.py` が **literal `$HOME/anicca/skills/browser/ensure_browser.sh` と
`_shared/lib/*.mjs` を直接呼ぶ**（franklin2 側 64 match / 19 files）。franklin は 6 script + _shared の物理コピーを
自配下に持つが launcher が anicca literal のまま（移行途中の二重化、推測）。加えて anicca 側
`_shared/lib/plist_render.py:50` が `proactive-loop.sh` のパスを plist に焼く ＝ **anicca_home 前提が全 loop に効く**。

→ **判定: browser 6 script + _shared を PC の `skills/_shared/`・`skills/browser/` へ COPY し、`skills.lock`
（既存の vendor manifest、sha256 付き）に entry を追加。anicca 側は当面 tombstone しない。**
理由: self-funded franklin の launcher が anicca の絶対パスを literal 参照しているため、anicca 側を消すと
franklin が壊れる。gig spec §6 の「anicca 残置」判断と一致。

**anicca tombstone の前提条件（PC 単一化と別トラックの後続作業として §5 に記載）:**
(a) franklin launcher の参照を自コピー（`$ANICCA_HOME/skills/...`）へ切替、
(b) anicca 側 `_shared/lib/plist_render.py` の anicca_home 前提を env 化。この 2 つが済むまで **二重化を許容**し、
registry と skills.lock に「どちらが正か」を明記する。

### 3-2. loop 個別の外部 state — registry path 契約で吸収（据え置き）
`~/gig`（gig）/ `~/clips`（clip、**実体 dir・移送判断が要る**）/ `~/.cloak/*`（clip/reddit/affiliate/video）/
`~/.openclaw/state/*`（*-last-pass・ledger）は「repo 外 state」。TO-BE（repo-structure §9）に従い **repo には
path 契約（`evidence_path`/`ledger_paths`）だけ書き、実データは `~/.profitable-claude/state/<loop>/` か既存 path を
env で指す**。move はせず据え置き参照が最安全（gig TOP3-3）。**例外は clip の `~/clips/`** = 実体 dir なので
移送 or env 参照を明示決定（clip/video 固有の罠5、§4-B/D）。

### 3-3. capafy-autopublish / telegram / self-fix — vendor か CLI か env 化
- `~/.openclaw/skills/capafy-autopublish/vendor/` は publisher CLI 内包 → PC `skills/capafy/vendor/` へ copy。
- telegram = `~/.openclaw/skills/_shared/scripts/telegram-notify.sh`（PC 用）を skills.lock で vendor。
- `~/anicca/skills/self/self-fix.sh`（reddit/gig の self-heal）を PC へ copy。
- `~/anicca/runtime/anicca-daemon.sh` は §4-G で env 駆動の起動体に複製（franklin 不触）。

---

## §4. loop ごと移設 TODO（gig spec §8 レシピ 0-8 の再利用 + 差分だけ）

gig の §8 レシピ = 「①→②同期(0) → 依存解決検証(1) → dry(2) → plist+tmux 原子切替(3) → tombstone(4) →
散在コピー処分(5) → 無停止検証(6) → registry/README(7) → OSS hygiene(8)」。各 loop はこの骨格を踏襲し、
**下記の差分だけ**を上乗せする。clip/video/gig は `*-cli.sh` に「ported from gig-cli.sh」の自認どおり同族＝
レシピ 0-8 がそのまま流用可能。

### §4-A. gig — 姉妹 gig spec が正本（差分なし）。先行実施（レシピ検証台）。

### §4-B. clip（gig 型・差分中）
- trigger は `clip-loop-aiclipsvault`(6h) の **1 plist のみ有効**（他 5本は 07-12 disabled）＝切替対象 1 本で gig より単純。
- browser 参照（`clip-cli.sh:33,38`）は §3-1 の copy 済み PC 基盤へ相対参照化。
- **state `~/clips/` は実体 dir。gig の「据え置き」と違い移送判断が要る**（下記 clip/video 固有の罠5）。
- `earn-clip-rewards` skill が `~/.claude/skills/` にも別在（feature/clip-rewards branch 由来）。二重化を確認。

### §4-C. clip-promote（clip 従属）
- clip とセットで同 dir 移設。単独 launchd label 無し。

### §4-D. video（完全停止・練習台）
- **有効 plist ゼロ＝live を壊すリスク無し。移設レシピの練習に最適。** browser 参照は clip と同型。
- 移設後 PC で再有効化するか別判断（設計は tmux+cron 23 */4、earn=faceless finance + ChangeNOW affiliate）。

### §4-B/D 共通「clip/video 固有の罠 5 つ」（差分に必ず載せる）
1. **別ツリー _shared + 固定 venv パス hardcode**: `~/.openclaw/skills/_shared/venv-cloak` を
   `launch_proxy_browser.py:16` が絶対パスで参照。PC 移設時は venv を PC 内に再構築 or env 化。
2. **cliproxy 依存**: `ANTHROPIC_BASE_URL=127.0.0.1:8317` + `CLIPROXY_KEY`（`clip_pass.sh` / `clip-cli.sh` /
   `video-cli.sh`）。`homebrew.mxcl.cliproxyapi.plist`(PID 691) 稼働前提。PC でも CLIProxyAPI 前提を .env.example に明記。
3. **STARTUP prompt 内の `/Users/anicca` 絶対パス大量 + 兄弟 skill 横断参照**（`ig-account-create` /
   `ig-reels-poster` / `self-improve` / `clip-promote` / `founder-loop/ceo`）。**clip の依存グラフは gig より広い** —
   兄弟 skill 群も一緒に vendor するか参照解決が要る。
4. **ポート台帳**: `9222`=Dais daily-driver への誤投稿地雷（`clip-cli.sh:18` に明記）。**9222/9223 回避規約を PC でも維持。**
5. **clip state `~/clips/` は実体 dir で移送対象**（gig の据え置きと異なる判断）。

### §4-E. reddit（gig 型・差分中）
- launchd daily + healthcheck 300s の 2 plist。browser 参照（`reddit-loop-cli.sh:18`）を PC 基盤へ相対化。
- state=`~/.cloak/reddit-accounts.json` + `~/.camofox/profiles/anicca/reddit1/`（camofox profile も依存、据え置き参照）。
- **混同注意**: openclaw cron `anicca-backlink-reddit-weekly`(enabled) は reddit-loop ではなく別 skill
  `anicca-backlink-builder`。reddit-loop 移設で touch しない。

### §4-F. capafy（cron 単発型・差分最大）
- **code が 3 箇所に散在**（`self/capafy-loop` + `earn/capafy-marketing` + `~/.openclaw/skills/capafy-autopublish`）。
  PC の 1 skill dir `skills/capafy/` に統合し vendor CLI を内部 copy（§3-3）。
- スケジューラ多重（launchd 3本 + openclaw cron `anicca-capafy-daily-publish`）を 1 本化。
- registry は現在 `status:external`。移設後 `live` + `skill_dir:skills/capafy` に更新。tmux core 無し。

### §4-G. claude-p-economy（x402 seller + founder runtime）★最難関・専用手順★
- **単純 move 厳禁**（runtime/x402-sell/serve.mjs/watch-inflow.sh を franklin と物理共有・byte-identical、§2-6/TOP1）。
- 取るべき道 = **複製方式**: claude-p 用に `boot`+`serve` を **複製**してから claude-p の 3 plist
  （`agent-economy-loop` / `x402-claude-p` / `x402-inflow-watch-claude-p`）だけを PC 版へ張替。
  **franklin の plist は anicca-daemon.sh を指したまま据え置く**（self-funded は対象外＝不触）。runtime コードは
  anicca/PC で二重化するが claude-p だけ PC 自己完結にできる（franklin を PC 依存にする案は Dais 裁定「anicca 依存
  ゼロ」と self-funded の独立性に反するので却下）。
- 罠: `serve-claude-p-boot.sh` は `~/.anicca-founder` 配下の state/wallet key を読む。PC 移設後も
  `ANICCA_HOME=~/.anicca-founder` を env で維持（wallet home は move しない）。
- **第4 repo 依存**: `x402-monitor`/`x402-tunnel` は `~/anicca-oss/.worktrees/earn-x402/services/x402-endpoint/`
  依存。この endpoint service を PC が抱えるか外部依存として env 契約にするか、設計判断が要る。
- wallet 二重（0x810F… / 0x904B50d2…）と `ANICCA_FUNDING=self` の矛盾（§2-6 要確認2）を移設前に解消。
- **この loop は他 9 loop と独立に、最後に着手**（共有 runtime の分離設計 review が要る）。

### §4-H. aso / paywall / screenshot（product growth skills・scope 判断が要る）
- tmux/launchd/browser 基盤 **無し**。code は `~/anicca-project/.claude/skills/` の iOS 製品運用 skill。
- 移設は (a)スケジューラ移植 + (b)依存パス解決 の 2 点に集約（tmux 無しで軽い）。
- aso cron は既に無効、paywall cron 現存せず、screenshot は手動 ＝ **現状ほぼ稼働していない**。
- **推奨（推測）**: これらは Anicca iOS 製品固有（asc/RevenueCat）で「clone で誰でも回る earn loop」と目的が
  異なる → **PC 単一化の対象外とし anicca-project に残置**。Dais 確認事項として明記。⚠️
  `~/.openclaw/skills/aso-loop` の broken symlink は掃除対象。

### §4-I. article-writer（PC 内・依存刈りのみ）
- code は既に PC(`skills/article-writer/`)。残作業は **§2-7 の横断依存（`~/.openclaw/.env` creds /
  `~/anicca/skills/browser` / `~/.cloak/note-work` / `~/.cache/anicca-clones/note-mcp` /
  `anicca-seo-rank-monitor/state` / CDP :9222）を PC 自己完結へ刈り込む**こと。registry は `status:external` を
  意図的に維持（launchd が唯一の scheduler、`bin/start-all.sh` に起動させない＝二重起動防止）。

### §4-J. bounty / affiliate / connector / explorer / life-manager（移設済み・微修正）
- 残作業は state の外部依存だけ（affiliate=`~/.openclaw`/`~/.cloak`）。registry path 契約は既にある（§3-2 で吸収）。

---

## §5. 実行順序の推奨（根拠付き）

| 順 | 対象 | 根拠 |
|---|---|---|
| 0 | **gig 先行完了**（姉妹 spec §8） | tmux core + healthcheck + browser 基盤 + state 外部の**全パターンを含む最難 gig でレシピを実証**。ここで browser 基盤 copy 手順(§3-1)を確立すれば clip/video/reddit が流用できる |
| 1 | **共有基盤 vendor**（browser 6 script + _shared を PC へ copy、skills.lock 記録、§3-1） | clip/video/reddit が全て依存。ここを PC に置かないと後続が動かない。self-funded 参照ありなので **copy（move 禁止）**、anicca tombstone は別トラック |
| 2 | **video**（完全停止、§4-D） | **有効 plist ゼロ＝live を壊さない安全な移設練習**。clip とほぼ同型 + 固有罠5を検証 |
| 3 | **clip + clip-promote**（§4-B/C） | browser 基盤 copy 済みなら差分小。ただし clip の依存グラフは広い（兄弟 skill 横断・~/clips 実体 dir・9222 地雷）。IG 収益 loop を PC 化 |
| 4 | **reddit**（§4-E） | browser 基盤依存を解消。cron 混同（backlink-builder）に注意 |
| 5 | **capafy**（§4-F） | 3 箇所散在の統合。cron 単発型なので tmux 無しで比較的安全だが依存4系統で最も絡む |
| 6 | **article 依存刈り**（§4-I） | code は既に PC。§2-7 の横断依存を PC 自己完結へ刈るだけ（launchd はそのまま） |
| 7 | **claude-p-economy(x402)**（§4-G、複製方式） | 共有 runtime + 第4 repo + wallet 二重の分離設計 review が要る最難関。他が済んでから慎重に |
| 8 | **aso/paywall/screenshot 判断**（§4-H） | scope 判断（推奨=anicca-project 残置）。Dais 確認。broken symlink 掃除 |
| 9 | **registry/skills.lock/README 整合**（TO-BE §10 + §0） | **既存 registry(11 loop) を「新設」でなく「拡張・整合」**。全 loop 分の entry + README 台帳表を正に。install.sh に per-skill section 追加 |
| — | **（別トラック）anicca tombstone 前提の解消** | §3-1 の (a) franklin launcher 自コピー化 + (b) plist_render の anicca_home 前提解消。PC 単一化完了後に着手 |

**壊れる順序リスク（機械的導出）**: 共有基盤(1)を移す前に clip/video/reddit(2-4)を移すと browser 参照が
解決せず即死。claude-p-economy(7)を先にやると runtime 共有の franklin を巻き添え。よって **gig(0)→共有基盤(1)→
安全な video(2)→clip系(3)→reddit(4)→capafy(5)→article 依存刈り(6)→最難関 x402(7)→scope 判断(8)→台帳整合(9)**
以外は不可。

---

## §6 決定記録（2026-07-18、team-lead 既定採用。Dais から異議があれば上書き）

| 論点 | 決定 | 根拠 |
|---|---|---|
| aso / paywall-ab / screenshot-ab の scope | **PC 対象外、anicca-project 残置** | iOS 製品運用 skill（earn loop でない、browser 基盤/tmux 不使用）。broken symlink（~/.openclaw/skills/aso-loop）だけ後日掃除 |
| registry の pm / hl / sol | **PC から除外（entry は external のまま凍結、PC は起動しない）** | SSOT 上 trade = franklin(self-funded) の領分 |
| 共有基盤の扱い | **vendor(copy) + skills.lock 記録。move/tombstone 禁止** | franklin launcher が runtime で literal $HOME/anicca を呼ぶ（§3 実測） |
| x402/economy の方式 | **方式(a): env 駆動起動体を PC 新設、franklin 側不触。実行順序は最後** | anicca-daemon.sh / serve.mjs の物理共有（§2 実測） |

### §6b 処遇3分類（2026-07-18 Dais 方針: 「self-funded もやれる skill は消さない、copy」）

| 処遇 | 対象 | 理由 |
|---|---|---|
| **MOVE**（anicca から実体ごと移す。跡地は tombstone） | gig / capafy-loop + capafy-marketing + capafy-autopublish / reddit-loop / aso・paywall・screenshot(残置先は anicca-project) | human の KYC・アカウント・製品に縛られる = self-funded には原理的に無用（SSOT: franklin の earn = trade 3エンジンのみ） |
| **COPY**（両 repo が持つ。fork drift は skills.lock で管理） | clip / clip-promote / video / browser 6 script / _shared lib 必要分 | self-funded も実行可能な稼ぎ方・基盤。franklin launcher が runtime 参照中（§3 実測）につき削除不可 |
| **STAY**（anicca に残る。PC は複製起動体のみ新設） | runtime/anicca-daemon.sh・loop framework / trade 3エンジン(PM/SOL/HL) / x402-sell の franklin 側 | self-funded citizen の生命維持装置。PC 側は claude-p 用に env 駆動起動体を複製（§6 方式(a)） |

COPY の同期規約: **upstream = PC（Dais 裁定: PC が正本）**。anicca 側は PC から vendor し、既存の
skills.lock 方式（source_repo/source_commit/sha256）で受ける。逆方向の編集は禁止（drift 防止、編集は PC で
行い anicca へ再 vendor）。franklin の literal $HOME/anicca 参照が生きている間は anicca 側 COPY を消さない
（Task #20 完了が削除の前提条件）。

### 実行進捗（2026-07-19 更新）
- **P1 gig 移設 = 完了**（step0-6、姉妹 spec §8-0〜8-7 に全記録。本番 = PC、初パス46分完走 + shuppin 2件）
- **P2 browser vendor = 完了**（PC commit `e43d821`）: 7ファイルを skills/_shared/browser/ へ byte 同一 copy
  （Fable diff 実測）、skills.lock に per-file sha256 + source_commit(6d12756) 記録、配線変更ゼロ、
  anicca 側無傷（status 0行）。VENDORED.md に再 vendor 手順。review は機械的 byte 同一性検証のため省略
  （意思決定として記録）。launcher の vendored 版への切替は各 loop 移設時
- 体制 = /flowa: Fable plan+verify / Sol xhigh execute / Sol fresh review

### TaskList との対応（実行順序 §5 ↔ Task ID）
gig(0)=#8-11 → 共有基盤 vendor(1)=#15 → video(2)+clip系(3)=#16 → reddit(4)+capafy(5)=#19 →
article 依存刈り+cron 8本廃止(6)=#18 → x402/economy(7)=#17 → 台帳整合(9)=#12 → OSS hygiene=#13 →
（別トラック）franklin launcher 収斂=#20。scope 判断(8)は本節で決定済み。

## 付録: 本 inventory 作成時の tool 非致命 exit（fablize gate 記録用）
- `plutil -extract StartInterval` / `StartCalendarInterval` が「Could not extract value」で exit 1 → **正常**
  （両キーは排他。存在しないオプションキーを引いた期待どおりの失敗）。
- `ls -d ...*/aso-loop`(anicca 側) が「no matches found」→ **正常**（aso-loop は anicca-project 側に在るため anicca に無い）。
- openclaw CLI（`openclaw cron list` 相当）は **gateway 起動でハングするので使わない**（kill 実測）。cron store は
  `~/.openclaw/cron/jobs.json`(277KB) を python で直接 read。dispatcher 方式（payload.message が
  `cron-bash.sh <skill>/...` を呼ぶ）。
いずれも実害なし・既知ベースライン。
