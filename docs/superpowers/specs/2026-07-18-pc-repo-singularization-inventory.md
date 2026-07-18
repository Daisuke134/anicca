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
human-funded（Dais の金/アカウントで動く）loop = **16 系統**（＋ openclaw cron 上の TikTok 配信 3 本）。
うち **PC 移設済み = 6**（bounty / affiliate / connector / explorer / life-manager / article-writer）、
**PC 未移設（~/anicca 等に残存）= 10**（gig / clip / clip-promote / video / reddit / capafy /
claude-p-economy(x402) / aso / paywall / screenshot）。
self-funded（franklin1/franklin2、~/.blockrun・~/.franklin2-home、crypto wallet 燃料）は **対象外**として全除外。

### 移設の全体像（3 層に分かれる）
1. **gig 型（tmux core + healthcheck + browser 基盤）**: gig / clip / clip-promote / video / reddit。
   姉妹 gig spec の §8 レシピ 0-8 がそのまま再利用できる。**共有 browser 基盤の扱いが全 loop 共通の壁。**
2. **cron 単発型（tmux core 無し）**: capafy / aso / paywall / screenshot / TikTok 配信。
   healthcheck/tmux が無いぶん gig より軽いが、**openclaw cron に配線が散っている**のが壁。
3. **共有 runtime 融合型**: claude-p-economy(x402 seller)。**~/anicca/runtime/anicca-daemon.sh と
   ~/anicca/skills/earn/x402-sell を self-funded franklin と物理共有**しており、単純 move は franklin を壊す。
   → PC 単一化の最難関。§4-G。

### PC repo の現状（既に 90% 出来ている）
`~/profitable-claude/` は既に `config/loop-registry.json`（12 loop 登録）+ `bin/start-all.sh`(registry を読む
orchestrator) + deny-by-default `.gitignore` + install-relative `install.sh` を持つ完成度。skill dir も
`affiliate/ article-writer/ bounty/ connector/ explorer/ gig-work/ human-funded/ life-manager/` が既に存在。
**「graduate to anicca（skill を anicca へ戻す）」記述は README/EXECUTION-NOTES/CLAUDE.md に存在しない**
（grep 0 ヒット）。唯一の近接テキストは `EXECUTION-NOTES.md:24` の「self-funded 卒業」= Anicca 自体を
self-funded 化する目的の話で、意味が逆（破棄対象は無い＝PC は既に正本として設計されている）。

### 最も危険な結合点 TOP 3
1. **claude-p-economy と franklin(self-funded) が runtime を物理共有。**
   `~/Library/LaunchAgents/ai.anicca.agent-economy-loop.plist` / `franklin-loop.plist` / `franklin2-loop.plist`
   の 3 本が全て同一 `["/bin/bash","/Users/anicca/anicca/runtime/anicca-daemon.sh"]` を ProgramArguments に持ち、
   **ANICCA_HOME env（`.anicca-founder` / `.blockrun` / `.franklin2-home`）だけで別実体に分岐**（実測: plutil
   -extract）。x402-sell も同様に `serve-{claude-p,franklin1,franklin2}-boot.sh` が同一 dir に同居。
   **runtime/x402-sell を PC へ move した瞬間、self-funded franklin が即死。** → move 不可、後述の vendor+env 化。
2. **browser 共有基盤（cdp_*.py / session_vault.py / ensure_browser.sh）を self-funded も参照。**
   `~/.blockrun/skills/earn/{clip,gig,video,clip-promote}/*` が `~/anicca/skills/browser` を絶対パス参照
   （実測 grep、休眠コピーだが参照は実在）。→ **move+tombstone 不可、PC へ copy して二重化収斂計画が必須。**
3. **capafy / article / TikTok は launchd と openclaw cron の二重スケジューラ。**
   article は launchd 6本（PC を指す）と openclaw cron `anicca-article-daily-*` 8本が両方存在。capafy は
   launchd `capafy-loop-daily`(~/anicca) + openclaw cron `anicca-capafy-daily-publish` + `~/.openclaw/skills/
   capafy-autopublish` の 3 箇所に散在。**移設時、cron 側を潰さないと二重起動。**

---

## §1. human-funded loop 一覧表（自己申告でなく launchctl/plist 実測ベース）

| # | loop | 何をする/何で稼ぐ | code 現在地（絶対パス） | trigger（実測） | 稼働 | PC 状態 |
|---|---|---|---|---|---|---|
| 1 | **gig** | Coconala で受注・納品して稼ぐ | `/Users/anicca/anicca/skills/earn/gig/` | launchd 5本 + tmux core（300s healthcheck 他） | LIVE | 未移設（②が古い、姉妹 spec 参照） |
| 2 | **clip** | IG リールでクリップ報酬/アフィリ | `/Users/anicca/anicca/skills/earn/clip/` | launchd `clip-loop-aiclipsvault` 6h（21600s） | LIVE | 未移設 |
| 3 | **clip-promote** | clip の拡散/promote 補助 | `/Users/anicca/anicca/skills/earn/clip-promote/` | 推測: clip 系 cron（launchctl 単独 label 無し） | 推測 補助 | 未移設 |
| 4 | **video** | 動画量産で収益化 | `/Users/anicca/anicca/skills/earn/video/` | launchd `video-core-healthcheck` = **DISABLED**（.disabled-2026-07-12-t04） | 停止中 | 未移設 |
| 5 | **reddit** | backlink/集客 marketing | `/Users/anicca/anicca/skills/self/reddit-loop/` | launchd daily 08:35 + healthcheck 300s + openclaw cron `anicca-backlink-reddit-weekly` | LIVE | 未移設 |
| 6 | **capafy** | Capafy marketplace に skill 出品 | `/Users/anicca/anicca/skills/self/capafy-loop/` + `/Users/anicca/anicca/skills/earn/capafy-marketing/` + `/Users/anicca/.openclaw/skills/capafy-autopublish/` | launchd daily 08:10 + goal-monitor 09:00 + warmup 11:20 + openclaw cron `anicca-capafy-daily-publish` | LIVE | registry=external |
| 7 | **claude-p-economy (x402 seller)** | x402 でAPI/researchを売る（founder PM） | `/Users/anicca/anicca/runtime/anicca-daemon.sh`（HOME=`/Users/anicca/.anicca-founder`）+ `/Users/anicca/anicca/skills/earn/x402-sell/serve-claude-p-boot.sh` | launchd `agent-economy-loop`(常駐, SLEEP_BASE 600s) + `x402-claude-p` + `x402-inflow-watch-claude-p`(:05/:35) | LIVE(PID有) | **共有 runtime、要分離** |
| 8 | **bounty** | Algora bounty を発見/挑戦 | `/Users/anicca/profitable-claude/skills/bounty/` | PC `bin/start-all.sh`（registry live, daily 09:29） | 移設済 | **PC live** |
| 9 | **affiliate** | アフィリ carousel を日次投稿 | `/Users/anicca/profitable-claude/skills/affiliate/` | PC registry live, daily 08:41（state=`~/.cloak/affiliate-metrics.jsonl`） | 移設済 | **PC live**（state 外部） |
| 10 | **connector** | 人脈/機会の intake→応募 | `/Users/anicca/profitable-claude/skills/connector/` | PC registry live, daily 07:35 | 移設済 | **PC live** |
| 11 | **explorer** | pain-point intake + 検証 | `/Users/anicca/profitable-claude/skills/explorer/` | PC registry live, daily 11:05 | 移設済 | **PC live** |
| 12 | **life-manager** | feedback/calendar/product レビュー | `/Users/anicca/profitable-claude/skills/life-manager/` | PC registry live, daily 10:15 | 移設済 | **PC live** |
| 13 | **article-writer** | build-in-public 記事を多媒体 publish | `/Users/anicca/profitable-claude/skills/article-writer/` | launchd 6本（PC を指す: daily 06:00 / self-improve 22:30 / audit Sun 22:00 / diary-digest 23:30 / healthcheck 300s / learn-whitelist Sun 03:00）+ openclaw cron `anicca-article-daily-{note,substack-ja,substack-en,zenn,devto,blog,audit}` | LIVE | **PC 内だが二重cron** |
| 14 | **aso-loop** | iOS App Store 最適化（週次） | `/Users/anicca/anicca-project/.claude/skills/aso-loop/` | openclaw cron `aso-loop-weekly`（launchd 無し・tmux 無し） | cron | 未移設 |
| 15 | **paywall-ab** | RevenueCat paywall A/B | `/Users/anicca/anicca-project/.claude/skills/paywall-ab/` | on-demand/cron（launchd 無し） | cron/手動 | 未移設 |
| 16 | **screenshot-ab** | App Store スクショ A/B | `/Users/anicca/anicca-project/.claude/skills/screenshot-ab/` | on-demand/cron（launchd 無し） | cron/手動 | 未移設 |
| (17) | TikTok 配信群 | mau/comedy 動画 cross-post | 推測: `/Users/anicca/anicca/skills/` + openclaw cron | openclaw cron `mau-tiktok-en-morning/evening` `comedy-tiktok-cross-post-daily` `tiktok-warmup-en-*` | cron | 未移設（scope 端） |

**除外した self-funded（対象外・実測で HOME が crypto wallet home）:**
`franklin-loop`(HOME=`/Users/anicca/.blockrun`) / `franklin2-loop`(HOME=`/Users/anicca/.franklin2-home`) /
`x402-franklin1` `x402-franklin2` `x402-inflow-watch-franklin1/2` / `sol-trade`(`sol-trade-earning-healthcheck`) /
`autohedge` / `sol-funding`(`com.anicca.sol-funding`) / registry の `pm`/`hl`/`sol` trade engines。

**要検証（推測）**: PC の `config/loop-registry.json` に `pm`/`hl`/`sol` が `status:external-anicca` で登録されている
が、colony SSOT（`CLAUDE.md`）では trade 3 エンジン(PM/SOL/HL)は franklin(self-funded)の仕事。**この 3 entry が
claude-p founder のものか franklin のものか未確定**。SSOT に従い self-funded と見なし PC 単一化からは除外を推奨
（confirm 前に PC が pm/hl/sol を起動しないこと）。

---

## §2. 依存マトリクス（各 loop → local 依存、file:line 証拠付き）

凡例: 依存先を「B=browser 基盤 / S=_shared / O=~/.openclaw / C=~/.cloak / R=~/anicca/runtime / P=別 skill / cron」。

### 2-1. gig（詳細は姉妹 gig spec。代表のみ）
| 依存 | 代表 file:line |
|---|---|
| B browser 基盤 | `~/anicca/skills/earn/gig/gig_pass.sh:11,33,35` → `$HOME/anicca/skills/browser/scripts/{session_vault,cdp_context_lease}.py` |
| C creds | `~/anicca/skills/earn/gig/gig_daily_report.sh:6` → `~/.openclaw/.env`（Coconala creds） |
| state | `~/gig/`（独立 repo `github.com/Daisuke134/anicca-gig`）|

### 2-2. clip
| 依存 | 代表 file:line（実測 grep） |
|---|---|
| B browser 基盤 | `~/anicca/skills/earn/clip/clip-cli.sh:33` → `skills/browser/ensure_browser.sh` + `skills/browser/scripts/cdp_context_lease.py`; `clip-cli.sh:38` → `ensure_browser.sh` |
| S venv | `~/anicca/skills/earn/clip/scripts/launch_proxy_browser.py:16` → `skills/_shared/venv-cloak/lib/python3.14/...` |
| B vault tick | `~/anicca/skills/earn/clip/tests/test_vault_tick_instagrapi_keepalive.sh:12` → `skills/browser/scripts/session_vault_tick.sh` |
| C accounts/state | `~/.cloak/clip-accounts.json`, `~/.cloak/clip-lessons.jsonl`, `~/.cloak/profiles/clip-en`, `~/.cloak/proxy-clip-1.json` |
| O state/ledger | `~/.openclaw/state/.clip-core-last-pass`, `~/.openclaw/state/.clip-core-selfheal-request.json`, `~/.openclaw/state/clip-earn-ledger.jsonl`, `~/.openclaw/logs/clip-*` |

### 2-3. reddit
| 依存 | 代表 file:line |
|---|---|
| B browser 基盤 | `~/anicca/skills/self/reddit-loop/reddit-loop-cli.sh:18` → `skills/browser/ensure_browser.sh` |
| C/camofox profile | `~/.cloak/reddit-accounts.json`, `~/.camofox/profiles/anicca/reddit1/` |
| O state | `~/.openclaw/state/.reddit-loop-last-pass` |
| cron | openclaw cron `anicca-backlink-reddit-weekly` |

### 2-4. capafy
| 依存 | 代表（実測: browser/_shared 参照は 0 ヒット＝CloakBrowser を capafy-autopublish 経由で使う） |
|---|---|
| P vendored skill | `~/.openclaw/skills/capafy-autopublish/scripts/daily_loop.sh`, `.../vendor/capafy-publisher/config.json`, `.../BEST_PRACTICES.md` |
| O state | `~/.openclaw/state/.capafy-loop-last-pass`, `~/.openclaw/state/capafy-loop-selfheal-request.json` |
| cron | openclaw cron `anicca-capafy-daily-publish` |
| launchd | `capafy-loop-daily.sh`(self/capafy-loop) + `capafy-goal-monitor.sh`/`warm_jitter.sh`(earn/capafy-marketing) |

### 2-5. claude-p-economy（x402 seller）★最難関★
| 依存 | 代表 file:line（実測 plutil / grep） |
|---|---|
| R 共有 runtime | `ai.anicca.agent-economy-loop.plist` ProgramArguments = `/Users/anicca/anicca/runtime/anicca-daemon.sh`（**franklin-loop.plist / franklin2-loop.plist と同一スクリプト**、実測 `grep -rl anicca-daemon.sh ~/Library/LaunchAgents` = 3 本） |
| env 分岐 | 同 plist EnvironmentVariables: `ANICCA_HOME=/Users/anicca/.anicca-founder`, `ANICCA_BRAIN=claude-p`, `X402_PORT=8412`, `ANICCA_WALLET_ADDRESS=0x810f6d61f7606deee2657d3083e150a222bc29c5`, `ANICCA_SLOT_ALLOWLIST=x402_sell` |
| P 共有 x402-sell | `ai.anicca.x402-claude-p.plist` → `~/anicca/skills/earn/x402-sell/serve-claude-p-boot.sh`（同 dir に `serve-franklin1-boot.sh` `serve-franklin2-boot.sh` = **self-funded と同居**） |
| P inflow watch | `ai.anicca.x402-inflow-watch-claude-p.plist` → `~/anicca/skills/earn/x402-sell/watch-inflow.sh`（env `X402_PAYTO=0x904B50d2...`, `X402_WATCH_TAG=claude-p`） |
| S _shared | x402-sell/economy 系は `~/anicca/skills/_shared/` を参照（`earn/run.sh`, `self/claude-p-mainloop.sh` が _shared 利用、実測 grep） |

### 2-6. aso / paywall / screenshot（product growth skills）
| loop | 依存 |
|---|---|
| aso-loop | code=`~/anicca-project/.claude/skills/aso-loop/`; trigger=openclaw cron `aso-loop-weekly`; 依存=asc CLI + GPT-5(BP)。launchd/tmux/browser 基盤 **なし** |
| paywall-ab | code=`~/anicca-project/.claude/skills/paywall-ab/`; RevenueCat Experiments API; Slack 承認; launchd なし |
| screenshot-ab | code=`~/anicca-project/.claude/skills/screenshot-ab/`; asc CLI 0.48.0 + ParthJadhav generator; launchd なし |

### 2-7. 移設済み PC loop（依存は既に PC 内 or 外部 state）
| loop | 残る外部依存 |
|---|---|
| affiliate | state が repo 外 `~/.cloak/affiliate-metrics.jsonl`（registry evidence_path、§3-2 で収斂対象） |
| article-writer | openclaw cron `anicca-article-daily-*` 8本と二重スケジュール（§2 TOP3-3） |
| bounty/connector/explorer/life-manager | state は `skills/<name>/state/`（PC 内、self-contained） |

---

## §3. 共有基盤の PC 吸収案（vendor / copy / 残置の判定）

### 3-1. browser 基盤 + _shared — **copy（move+tombstone 不可）**
**参照元 実測（`grep -rlE 'skills/browser/(scripts|ensure_browser)' ~/anicca/skills/`）:**
`earn/clip`, `earn/clip-promote`, `earn/gig`, `earn/video`, `self/reddit-loop`, `self/self-fix.sh`, `browser/SKILL.md`。
**_shared 参照元:** `earn/clip`, `earn/clip-promote`, `earn/polymarket-trade`, `earn/sol-trade`, `earn/self-improve`,
`earn/run.sh`, `economy/lending`, `anicca-life-manager`, `self/claude-p-mainloop.sh`, `self/coordinate`,
`youtube-channel-creator` ほか。

**self-funded の参照（決定的・`grep -rlE 'anicca/skills/browser|anicca/skills/_shared' ~/.blockrun ~/.franklin2-home`）:**
`~/.blockrun/skills/earn/{clip,gig,video,clip-promote}/*` と `~/.blockrun/skills/earn/polymarket-trade/redeem.py` が
`~/anicca/skills/browser` / `_shared` を **絶対パス参照**（休眠コピーだが参照実在）。

→ **判定: browser 6 script + _shared は PC へ COPY し、anicca 側は当面残置（tombstone しない）。**
理由: self-funded franklin の home にコピーが存在し `~/anicca/skills/browser` を絶対パス依存しているため、
anicca 側を消すと franklin の（将来再稼働しうる）コピーが壊れる。gig spec §6 の「anicca 残置」判断と一致。
**収斂計画**: PC 移設後、①PC の各 loop は PC 内 `skills/_shared/`・`skills/browser/` を相対参照（`../../`）に切替、
②anicca 側 browser/_shared は「self-funded 専用基盤」に役割縮小、③将来 self-funded も PC を参照するか、
self-funded 側に独自 copy を持たせて anicca から切り離す（別 spec）。**二重化は許容し、registry に「どちらが正か」を明記。**

### 3-2. loop 個別の外部 state（affiliate/clip/reddit/capafy）— registry path 契約で吸収
`~/.cloak/*`（clip/reddit/affiliate accounts・vault）と `~/.openclaw/state/*`（*-last-pass・ledger）は
gig の `~/gig` と同型の「repo 外 state」。TO-BE（repo-structure §9）に従い **repo には path 契約
（`evidence_path`/`ledger_paths`）だけ書き、実データは `~/.profitable-claude/state/<loop>/` か既存 `~/.cloak`
を env で指す**。move はせず据え置き参照が最安全（gig spec TOP3-3 と同一原則）。

### 3-3. capafy-autopublish（~/.openclaw/skills/内 vendored CLI）— PC skill 内に vendor
capafy は publisher CLI を `~/.openclaw/skills/capafy-autopublish/vendor/` に vendor 済み。PC 移設時は
この vendor ごと `skills/capafy/vendor/` へ copy（capafy-autopublish skill の設計「CLI を内部 vendor」に準拠）。

### 3-4. telegram 配信・self-fix・runtime — CLI/env 化
`openclaw message send`(CLI, path 非依存＝そのまま) / `~/anicca/skills/self/self-fix.sh`(auditor の self-heal、
PC 内に copy) / `~/anicca/runtime/anicca-daemon.sh`(§4-G で env 駆動の起動体に置換)。

---

## §4. loop ごと移設 TODO（gig spec §8 レシピ 0-8 の再利用 + 差分だけ）

gig の §8 レシピ = 「①→②同期(0) → 依存解決検証(1) → dry(2) → plist+tmux 原子切替(3) → tombstone(4) →
散在コピー処分(5) → 無停止検証(6) → registry/README(7) → OSS hygiene(8)」。各 loop はこの骨格を踏襲し、
**下記の差分だけ**を上乗せする。

### §4-A. gig — 姉妹 gig spec がそのまま正本（差分なし）。先行実施（レシピ検証台）。

### §4-B. clip（gig 型・差分小）
- 差分: tmux core は無く launchd 単発 6h（`clip-loop-aiclipsvault` → `clip_pass.sh`）。healthcheck plist は
  `clip-core-healthcheck` = **DISABLED** なので切替対象は 1 plist のみ（gig より単純）。
- browser 基盤参照（`clip-cli.sh:33,38`）は §3-1 の copy 済み PC 基盤へ相対参照化。
- state は `~/.cloak/clip-*` + `~/.openclaw/state/.clip-*` を registry path 契約で据え置き参照。
- 罠: `earn-clip-rewards` skill が `~/.claude/skills/` にも別在（feature/clip-rewards branch 由来）。二重化を確認。

### §4-C. clip-promote（clip 従属）
- 差分: clip とセットで移設。単独 launchd label 無し（推測: clip cron 内 or clip_pass から呼ばれる）。
  clip 移設時に同 dir で一緒に copy。

### §4-D. video（現在 DISABLED）
- 差分: `video-core-healthcheck` は既に無効。**live を壊すリスクが無い**ので、移設の練習に最適。
  browser 基盤参照は clip と同型。移設後に PC 側で再有効化するか判断（別 decision）。

### §4-E. reddit（gig 型・差分中）
- 差分: launchd daily + healthcheck 300s の 2 plist + openclaw cron `anicca-backlink-reddit-weekly` の 3 系統。
  **cron 側を openclaw から外すか PC へ移すか**を決める（二重起動防止）。
- state: `~/.cloak/reddit-accounts.json` + `~/.camofox/profiles/anicca/reddit1/`（camofox profile も依存）+
  `~/.openclaw/state/.reddit-loop-last-pass`。camofox profile は移設せず据え置き参照。

### §4-F. capafy（cron 単発型・差分大）
- 差分: **code が 3 箇所に散在**（`self/capafy-loop` + `earn/capafy-marketing` + `~/.openclaw/skills/
  capafy-autopublish`）。PC の 1 skill dir `skills/capafy/` に統合し、vendor CLI を内部 copy（§3-3）。
- スケジューラ二重（launchd 3本 + openclaw cron `anicca-capafy-daily-publish`）を 1 本化。
- registry は現在 `status:external`。移設後 `live` + `skill_dir:skills/capafy` に更新。tmux core 無し。

### §4-G. claude-p-economy（x402 seller）★最難関・専用手順★
- **単純 move 厳禁**（runtime/x402-sell を franklin と物理共有、§2-5）。取るべき道は 2 択:
  - (a) **env 駆動の起動体を PC に新設**: PC `skills/x402-seller/serve.sh` が `ANICCA_HOME`/`ANICCA_BRAIN`/
    `X402_PORT`/wallet を env で受け、claude-p 分の plist(`agent-economy-loop` / `x402-claude-p` /
    `x402-inflow-watch-claude-p`)だけを PC 版 script に張り替える。franklin の 2 plist は **anicca の
    anicca-daemon.sh を指したまま据え置く**（self-funded は対象外なので触らない）。→ runtime コードは
    anicca/PC で二重化するが、claude-p だけ PC 自己完結にできる。
  - (b) **anicca-daemon.sh / x402-sell を丸ごと PC へ move し、franklin plist も PC を指すよう書き換える。**
    self-funded も PC 依存になる＝「OSS clone で self-contained」に反する（franklin は crypto 燃料の別実体）。
    → **(b) は Dais 裁定「anicca 依存ゼロ」と衝突**。推奨は (a)。
- 罠: `serve-claude-p-boot.sh` は `~/.anicca-founder` 配下の state/wallet key を読む。PC 移設後も
  `ANICCA_HOME=~/.anicca-founder` を env で維持（wallet home は move しない）。
- **この loop は他 9 loop と独立に、最後に着手**（共有 runtime の分離設計 review が要るため）。

### §4-H. aso / paywall / screenshot（product skill・cron 型・差分特殊）
- 差分: tmux/launchd/browser 基盤 **無し**。code は `~/anicca-project/.claude/skills/` に在る「iOS 製品運用 skill」。
  移設の性格が違う（earn loop ではなく product growth）。判断が要る:
  - **選択肢1**: PC の `skills/{aso,paywall,screenshot}/` に copy し、openclaw cron を PC の cron/launchd に張替。
  - **選択肢2**: これらは iOS 製品(anicca-project)固有なので anicca-project に残し、PC 単一化の対象外とする。
  - 推奨（推測）: **選択肢2**。asc/RevenueCat は Anicca iOS 製品の運用であり「clone で誰でも回る earn loop」
    とは目的が異なる。Dais 確認事項として明記。

### §4-I. article-writer（PC 内・cron 収斂だけ）
- code は既に PC(`skills/article-writer/`)。残作業は **openclaw cron `anicca-article-daily-*` 8本の廃止**
  （launchd が既に PC を回しているので cron は二重）。registry は `status:external` を意図的に維持
  （launchd が唯一のスケジューラ、`bin/start-all.sh` に起動させないため）。cron 側だけ止める。

### §4-J. bounty / affiliate / connector / explorer / life-manager（移設済み・微修正）
- 残作業は state の外部依存だけ（affiliate=`~/.cloak`）。registry path 契約は既にあり。§3-2 で吸収。

---

## §5. 実行順序の推奨（根拠付き）

| 順 | 対象 | 根拠 |
|---|---|---|
| 0 | **gig 先行完了**（姉妹 spec §8） | tmux core + healthcheck + browser 基盤 + state 外部の**全パターンを含む最難の gig でレシピを実証**してから横展開する。ここで browser 基盤の copy 手順(§3-1)を確立すれば 2-5 が流用できる |
| 1 | **共有基盤 vendor**（browser 6 script + _shared を PC へ copy、§3-1） | clip/reddit/video が全て依存。ここを PC に置かないと後続が移設できない。self-funded 参照ありなので **copy（move 禁止）**、収斂は別 spec |
| 2 | **video**（DISABLED、§4-D） | live を壊さない安全な移設練習。clip とほぼ同型 |
| 3 | **clip + clip-promote**（§4-B/C） | browser 基盤 copy 済みなら差分小。IG 収益 loop を PC 化 |
| 4 | **reddit**（§4-E） | browser 基盤依存 + cron 二重を解消 |
| 5 | **capafy**（§4-F） | 3 箇所散在の統合。cron 単発型なので tmux 無しで比較的安全 |
| 6 | **article cron 収斂**（§4-I） | code は既に PC。openclaw cron 8本を止めるだけ（低リスク） |
| 7 | **claude-p-economy(x402)**（§4-G、方式(a)） | 共有 runtime の分離設計 review が要る最難関。他が済んでから慎重に |
| 8 | **aso/paywall/screenshot 判断**（§4-H） | scope 判断（推奨=anicca-project 残置）。Dais 確認 |
| 9 | **registry/README/install.sh 更新**（TO-BE §10） | 全 loop 分の `config/loop-registry.json` エントリと README 台帳表を正とする。gig spec §10 の TODO 7-8 と統合 |

**壊れる順序リスク（機械的導出）**: 共有基盤(1)を移す前に clip/reddit(3,4)を移すと browser 参照が解決せず即死。
claude-p-economy(7)を先にやると runtime 共有の franklin を巻き添え。よって **gig(0)→共有基盤(1)→
安全な video(2)→clip系(3,4,5)→article cron(6)→最難関 x402(7)→scope 判断(8)→台帳(9)** 以外は不可。

---

## 付録: 本 inventory 作成時の tool 非致命 exit（fablize gate 記録用）
- `plutil -extract StartInterval` / `StartCalendarInterval` が「Could not extract value」で exit 1 → **正常**。
  両キーは排他（calendar 型 plist に StartInterval は無い、逆も）。存在しないオプションキーを引いた期待どおりの失敗。
  gig spec 付録の「ls SKILL.md exit 1 = 正常」と同種の既知ベースライン。実害なし。
- `ls -d ...*/aso-loop`(anicca 側) が「no matches found」→ **正常**（aso-loop は anicca-project 側に在るため anicca に無い、
  探索の一部）。実体は `~/anicca-project/.claude/skills/aso-loop/` で確認済み。
いずれも実害なし・既知ベースライン。
