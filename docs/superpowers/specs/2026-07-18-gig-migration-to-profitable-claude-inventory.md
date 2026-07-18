# gig loop 移設 参照網インベントリ（~/anicca → ~/profitable-claude）

作成: 2026-07-18 / 種別: READ-ONLY 地図（実装・移動・編集は一切していない）
目的: gig work loop を `~/anicca`(OSS public) から `~/profitable-claude`(private) へ無停止移設するため、
「何を触れば何が壊れるか」を file:line 単位で全部洗い出す。前回この loop を不用意に動かして本番を壊し
revert した事故の再発防止。**この文書は観測（実 tool_result）のみ。推測は「推測」と明記。**

---

## 0. エグゼクティブサマリ（結論を先に）

- **これは "新規移設" ではなく "半分終わった移設" の途中状態。** 移設先 `~/profitable-claude/skills/gig-work/`
  に既に skill のコピーが存在し、`hf-gig-*` 接頭辞の plist も置いてある。**が、実際に launchd にロード
  されている 5 本の gig plist は全て旧配置 `~/anicca/skills/earn/gig/` を指したまま。** つまり
  「置いたが切り替えていない」。移設先コピーは旧配置と **中身が乖離している**（§5 の diff 参照）。
- **skill のコピーは合計 4 箇所に散在**（§4）: ①`~/anicca`(LIVE) ②`~/profitable-claude`(移設先, 未配線)
  ③`~/.openclaw/skills/anicca-earn-gig`(実体 dir) ④`~/.anicca-founder/skills/{earn,economy}/gig`。
- **state `~/gig/` は独立 git repo**（`github.com/Daisuke134/anicca-gig`）で、**data と実行スクリプトが混在**
  （`dd-keepalive-healthcheck.sh` / `dd-keepalive.py` が loaded plist に参照される実行体として state dir の中にいる）。
- **browser helper（cdp_context_lease.py / cdp_default_tab.py / session_vault.py / cdp_tab_gc.py / scout.py /
  ensure_browser.sh）は gig 専用ではなく earn/clip・earn/video・session-vault.plist と共有**。移設で move すると
  clip/video が壊れる。→ anicca に残して path 参照 or read-only vendor する。

### 参照総数
- LIVE launchd 参照: **6 plist**（gig-auditor / gig-core-healthcheck / gig-daily-report / gig-proactive /
  gig-selfimprove-verify + 共有 session-vault）＋ dd-keepalive-healthcheck（state dir 内スクリプトを参照）。
- gig skill → 外部 `~/` パス参照: **15 種**（§3B の表）。うち **browser/scripts への参照 = 10 行以上**（§3A）。
- skill → `~/gig` state 参照: **20+ 行**（scripts 群 + RUNBOOK prompt 本文）。
- 逆方向 anicca→gig の配線点: **1 本**（`runtime/loop/earn-slot.mjs` の `earnSkillRelPath('earn/gig')`）
  ＋ brain.mjs のコメント参照2箇所。
- 重複コピー: **4 箇所**（うち LIVE=1、未配線=3）。

### 最も危険な結合点 TOP 3
1. **LIVE plist × tmux core × healthcheck の三角形が全て絶対パス `/Users/anicca/anicca/skills/earn/gig/` と
   `~/gig/` にハードコード。** self-heal 自体（`gig-healthcheck.sh:31` が `~/anicca/skills/earn/gig/gig-cli.sh
   --restart` を叩く）も旧パス束縛。300 秒ごとに healthcheck が走るので、skill dir を動かした瞬間、
   healthcheck が旧パスで復活させ続ける or FAIL し続ける。**原子的に全 5 plist 差し替え＋tmux kill＋新 gig-cli で
   再起動しないと必ず二重起動 or 死ぬ。**
2. **共有 browser/scripts。** `session_vault.py` `cdp_context_lease.py` `cdp_default_tab.py` `cdp_tab_gc.py`
   `scout.py` `ensure_browser.sh` は earn/clip・earn/video・session-vault.plist が同時に使う（§6 で実証）。
   move すると clip/video 即死。copy すると二重コピーが分岐する。
3. **state `~/gig/` の混在。** 独立 repo(anicca-gig) かつ実行スクリプト(dd-keepalive)混入かつ **RUNBOOK の
   prompt 本文中に `~/gig/...` が20+箇所ハードコード**。state path を動かすと prompt も全書き換えになる。
   state は現地据え置き・参照が最も安全。

---

## 1. LIVE launchd（`~/Library/LaunchAgents/`）— 実測ロード済み

`launchctl list | grep -iE 'gig|vault'` 実測でロード確認済みの Label:
`ai.anicca.gig-core-healthcheck` / `gig-selfimprove-verify` / `session-vault` / `gig-daily-report` /
`gig-auditor` / `gig-proactive`（＋無関係 `clip-loop-aiclipsvault`）。

| plist (Label) | 参照先 絶対パス（ProgramArguments） | 起動間隔 | stdout/err |
|---|---|---|---|
| ai.anicca.gig-auditor | `/bin/bash /Users/anicca/anicca/skills/earn/gig/auditor.sh` | 毎時 :45 | `~/.openclaw/logs/gig-auditor.{out,err}.log` |
| ai.anicca.gig-core-healthcheck | `/bin/bash /Users/anicca/anicca/skills/earn/gig/gig-healthcheck.sh` | 300s (throttle 60) | `~/.openclaw/logs/gig-core-launchd.{out,err}.log` |
| ai.anicca.gig-daily-report | `/bin/bash /Users/anicca/anicca/skills/earn/gig/gig_daily_report.sh` | 毎日 09:07 | `~/.openclaw/logs/gig-daily-report.{out,err}` |
| ai.anicca.gig-proactive | `/bin/bash /Users/anicca/anicca/skills/_shared/proactive-loop.sh gig` | 300s (RunAtLoad=false) | `~/.openclaw/logs/gig-proactive.{out,err}` |
| ai.anicca.gig-selfimprove-verify | `/bin/bash /Users/anicca/anicca/skills/earn/gig/scripts/gig_selfimprove_verify.sh` | 3600s | `~/.openclaw/logs/gig-selfimprove-verify.{log,err.log}` |
| ai.anicca.session-vault ★共有★ | `/bin/bash -lc 'bash $HOME/anicca/skills/browser/scripts/session_vault_tick.sh'` | 1800s (RunAtLoad=true) | `~/.openclaw/logs/session-vault.log` |
| ai.anicca.dd-keepalive-healthcheck ★state内★ | `/bin/bash /Users/anicca/gig/dd-keepalive-healthcheck.sh` | (未 dump) | (未 dump) |

注意点:
- **gig-proactive は gig 専用スクリプトではなく `_shared/proactive-loop.sh` に引数 `gig` を渡す形**。同じ
  `_shared/proactive-loop.sh` を他 loop も使う（推測: clip/video も同様の proactive plist を持つ）。移設で
  `_shared` を動かすのは厳禁。
- **session-vault は gig の一部ではない**（browser 共有基盤）。gig 移設で touch しない。
- **dd-keepalive-healthcheck.plist は state dir `~/gig/` 内のスクリプトを ProgramArguments に持つ**（§7 参照）。
  gig plist 群と別扱いだが state 移設時に連動する。

---

## 2. tmux core（実 earn プロセス）

- socket: `/tmp/anicca-gig-tmux.sock` / session: `anicca-gig-core`（`gig-cli.sh:16-17`）。
  `tmux -S ... list-sessions` 実測で **1 window 稼働中**（created Sat Jul 18 09:16:19 2026）。
- 起動コマンドライン（`gig-cli.sh:57-58` = 実 pane_start_command 実測一致）:
  ```
  tmux -S /tmp/anicca-gig-tmux.sock new-session -d -s anicca-gig-core -c $HOME \
    "exec /Users/anicca/.local/bin/claude --name anicca-gig-core --model sonnet \
     --dangerously-skip-permissions --add-dir /Users/anicca \
     -- \"$(cat '/Users/anicca/gig/.startup-prompt.txt')\""
  ```
- 起動する側 = `gig-cli.sh`。呼ぶのは:
  - `gig-healthcheck.sh:31` → `bash "$HOME/anicca/skills/earn/gig/gig-cli.sh" --restart`（heartbeat
    `~/gig/.last-pass` が 90 分 stale で restart）。
  - `run.sh:16` → `bash "$HERE/gig-cli.sh"`（main-loop 経由の idempotent start）。
- startup prompt は `~/gig/.startup-prompt.txt`（`gig-cli.sh:42,44` が state dir に書き出す。tmux の
  command length 制限回避のためファイル経由）。**core は claude を `--model sonnet` で回す**（Luna/proxy ではなく
  素の sonnet, `~/.local/bin/claude`）。

---

## 3A. gig skill → browser/scripts（共有基盤）への参照（file:line）

| 参照元 file:line | 参照先 path |
|---|---|
| `gig_reality_verify.sh:205` | `$HOME/anicca/skills/browser/scripts/session_vault.py` |
| `gig-cli.sh:36` | `$HOME/anicca/skills/browser/ensure_browser.sh` |
| `gig_pass.sh:11` | `B="$HOME/anicca/skills/browser/scripts"`（以降 `$B/...` で参照） |
| `gig_pass.sh:31` | `$HOME/anicca/skills/browser/ensure_browser.sh` |
| `gig_pass.sh:33` | `$B/session_vault.py restore` |
| `gig_pass.sh:35,36` | `$B/cdp_context_lease.py gc / acquire` |
| `gig_pass.sh:30`（trap） | `$B/cdp_context_lease.py release` |
| `GIG_PASS_RUNBOOK.md`（prompt 本文, 多数） | `~/anicca/skills/browser/scripts/{cdp_default_tab,cdp_context_lease,cdp_tab_gc,session_vault,scout}.py`, `ensure_browser.sh` |

→ RUNBOOK は prompt テキストなので **文字列としてハードコード**。skill を移設しても RUNBOOK 内の
`~/anicca/skills/browser/scripts/...` は browser 基盤を anicca に残す限り書き換え不要（同じ絶対パスで解決する）。
browser 基盤ごと動かすなら RUNBOOK 全文の書き換えが必要。

## 3B. gig skill → その他外部 `~/` パス（file:line は §1/§2/§3A/§3C に既出以外を列挙）

| 外部 path | 用途 | 代表 file:line |
|---|---|---|
| `~/.openclaw/.env` | Coconala creds（COCONALA_EMAIL/PASSWORD, APPLE_ID 等）source | `gig_daily_report.sh:6`, RUNBOOK 本文, `gig_pass.sh:21` |
| `~/.cli-proxy-api-key` | CLIProxyAPI(:8317) キー | `gig_reality_verify.sh:246`, `gig-cli.sh:51` |
| `~/.cloak/profiles/daily-driver` | CloakBrowser profile | `scripts/cdp_daily_driver_guard.sh:23` |
| `~/.cloakbrowser/chromium-*` | Chromium bin | `scripts/cdp_daily_driver_guard.sh:65` |
| `~/.local/bin/claude` | claude CLI（core / judge spawn） | `gig-cli.sh:18`, `gig_reality_verify.sh:29`, `gig_pass.sh:12` |
| `~/.openclaw/logs/*` | 全 plist の stdout/err + 内部ログ | 各 plist, `gig-healthcheck.sh:13` |
| `~/.openclaw/state/.gig-core-selfheal-request.json` | self-heal 要求ファイル | `auditor.sh:80` |
| `~/anicca/skills/self/self-fix.sh` | self-heal 実行体 | `auditor.sh:81` |
| `~/loops/gig/` | proactive 観測 state + task-request-map.jsonl | `run.sh:22`, RUNBOOK 本文 |
| `~/anicca/skills/_shared/` (proactive_observe) | main-loop 観測 shim | `run.sh:21` (`SHARED_DIR=$HERE/../../_shared`) |
| `~/anicca-project/docs/earn/gig-coconala-playbook.md` | best-practice source | RUNBOOK 本文 |
| `openclaw message send`(CLI) | telegram 日報配信 | `gig_daily_report.sh:34` |
| `gh`(CLI) → `Daisuke134/anicca` | gig-lesson issue 共有 | RUNBOOK 本文 |
| env: `GIG_REPORT_CHAT` | telegram chat id | `gig_daily_report.sh` |
| env: `CLIPROXY_KEY / ANTHROPIC_AUTH_TOKEN / ANTHROPIC_BASE_URL=127.0.0.1:8317` | judge spawn 経路 | `gig_reality_verify.sh:246-249`, `gig-cli.sh:51-54` |

**重要:** `run.sh:21` の `SHARED_DIR="$HERE/../../_shared"` は **skill の相対位置に依存**。移設先
`~/profitable-claude/skills/gig-work/run.sh` からは `../../_shared` = `~/profitable-claude/skills/_shared` を
指す。profitable-claude 側に `_shared`（lib.proactive_observe 含む）が無いと `PL_JSON` は空 fallback になる
（`|| echo '{}'` で crash はしないが観測が死ぬ）。→ 移設先 `_shared` の有無を要確認（§8 手順で検証）。

## 3C. gig skill → `~/gig` state 参照（主要 file:line）

| file:line | 参照 |
|---|---|
| `gig-healthcheck.sh:12` | `HB="$HOME/gig/.last-pass"` (heartbeat, 90min stale で restart) |
| `gig-healthcheck.sh:14,36,51` | `~/gig/.restart-log`, `.last-start` |
| `auditor.sh:13` | `G="$HOME/gig"; AUDIT="$G/audit.jsonl"` |
| `scripts/cdp_daily_driver_guard.sh:24` | `~/gig/.cdp-guard.lock` |
| `scripts/gig_single_instance.sh:15` | `~/gig/.pass.lock` |
| `scripts/cdp_lock.sh:24` | `~/gig/.cdp-9222.lock` |
| `scripts/gig_selfimprove_verify.sh:8,25` | `~/gig/`（pass-report.jsonl, gig-funnel.jsonl, .selfimprove-todo.json） |
| `scripts/{cdp_snapshot,cdp_nav_snapshot}.py` | `~/gig/trajectory/<pass_id>/` |
| `scripts/gig_reality_gate.py:15,39,71,101` | `~/gig/trajectory`, `~/gig/audit-reality.jsonl` |
| `gig_funnel.py:6,15-20` | `~/gig/{applied,lessons,earnings,shuppin,gig-funnel}.jsonl` |
| `gig_daily_report.sh:10` / `run.sh:28` | `G=os.path.expanduser("~/gig")` |
| `GIG_PASS_RUNBOOK.md`（prompt 本文, 20+） | `~/gig/{applied,shuppin,lessons,earnings,pass-report,strategy,playbook}.jsonl/.json`, `~/loops/gig/state/task-request-map.jsonl` |

→ **state path `~/gig` は移設先を変えず据え置きが最善**。RUNBOOK prompt に文字列固定 + scripts に散在 + 独立 repo。

---

## 4. skill コピーの所在（4 箇所）と分類

| # | path | 状態 | 種別 |
|---|---|---|---|
| ① | `~/anicca/skills/earn/gig/` | **LIVE**（全 plist が指す・tmux core が回る） | 現行本番 |
| ② | `~/profitable-claude/skills/gig-work/` | 移設先。skill コピー有 + `launchd/hf-gig-*.plist` 有だが **launchd 未ロード**。中身が①と乖離（§5） | 移設ターゲット（未配線・古い） |
| ③ | `~/.openclaw/skills/anicca-earn-gig/` | 実体 dir（symlink ではない）。①とほぼ同構成の別コピー | 用途不明の重複（要確認） |
| ④ | `~/.anicca-founder/skills/earn/gig/` + `~/.anicca-founder/skills/economy/gig/` | founder 側コピー（economy/gig は mcp-server.mjs/SKILL.md 構成で別物） | 別実体（economy 版は x402 系, 別物） |

- ①②③④いずれにも **`SKILL.md` は無い**（①②で ls 実測 = 無し）。この skill は SKILL.md 駆動ではなく plist/tmux 駆動。
- ③④が LIVE ①と同期しているかは未検証（推測: drift している）。移設で ①→② を正とするなら ③④の扱いを別途決める必要。

---

## 5. 移設先②の中身と① LIVE の diff（file 名ベース, 実測）

`~/profitable-claude/skills/gig-work/` に **存在するが① LIVE に無い** もの:
- `archive/`（旧 mjs bid/deliver/settle 一式 + tests）, `artifacts/5121769/ppt_sample.pptx`
- `funnel.py`, `funnel_report.py`（①は `gig_funnel.py`。**名前が違う = リネーム済みの別実装**）
- `__tests__/` が大幅増（test_cold_start_pure / test_dedupe / test_feasibility_fillforward / test_funnel* /
  test_gig_run_shim_* / test_listing* / test_listings_* / test_passprep_new_fields ...）
- `launchd/ai.anicca.hf-gig-auditor.plist`, `hf-gig-core-healthcheck.plist`

**① LIVE に有るが移設先②に無い**（＝移設先が古い/未同期の証拠）:
- `gig_pass.sh`（★per-step claude sub-call の心臓部）, `gig_judge.py`, `gig_reality_verify.sh`,
  `GIG_PASS_RUNBOOK.md`（★prompt 本文 SSOT）, `gig_daily_report.sh`, `gig_funnel.py`,
  `GIG-STRATEGY-PROMPT-UPGRADE-SPEC.md`, `launchd/ai.anicca.gig-{auditor,core-healthcheck}.plist`,
  `scripts/{cdp_nav_snapshot.py, cdp_snapshot.py, gig_reality_gate.py}` ほか（diff 出力の後半は truncate。
  完全一覧は移設実行前に `diff <(find ①) <(find ②)` を再実行して取得すること）。

移設先②の plist（`hf-gig-*`）内容:
- `hf-gig-auditor` → `/Users/anicca/profitable-claude/skills/gig-work/auditor.sh`, 毎時:45,
  ログは **旧と同じ** `~/.openclaw/logs/gig-auditor.{out,err}.log`。
- `hf-gig-core-healthcheck` → `.../gig-work/gig-healthcheck.sh`, 300s, ログ **旧と同じ**
  `~/.openclaw/logs/gig-core-launchd.{out,err}.log`。
- **Label が `hf-gig-*`（旧 `gig-*` と別 Label）＝同時 load すると 2 本の healthcheck が並走し tmux core を
  奪い合う。** 移設は「旧 unload → 新 load」を原子的に。ログパス共有なのでログも混線する。
- **移設先②に `gig-daily-report / gig-proactive / gig-selfimprove-verify` の plist は無い**（2本だけ）。
  移設完了には残り3系統の plist 化も必要。

---

## 6. 共有依存の分類（copy / 残置参照 / 重複注意）

| 依存 | 現在地 | 使う loop（実測） | 移設判断 |
|---|---|---|---|
| `cdp_context_lease.py` | `~/anicca/skills/browser/scripts/` | gig, clip, video, session-vault | **anicca 残置＋path 参照**（move 厳禁） |
| `cdp_default_tab.py` | 同上 | gig, （seller-area 駆動） | **anicca 残置** |
| `session_vault.py` / `session_vault_tick.sh` | 同上 | gig, clip, **session-vault.plist** | **anicca 残置**（plist が独立で回る） |
| `cdp_tab_gc.py` | 同上 | gig, （clip 推測） | **anicca 残置** |
| `scout.py` | 同上 | gig（RUNBOOK） | 共有 or gig 専用か要確認、暫定 **残置** |
| `ensure_browser.sh` | `~/anicca/skills/browser/` | gig, clip, video | **anicca 残置** |
| `_shared/proactive-loop.sh` + `lib.proactive_observe` | `~/anicca/skills/_shared/` | gig-proactive.plist, （他 proactive plist） | **anicca 残置**（gig-proactive は引数 `gig` を渡すだけ） |
| `self-fix.sh` | `~/anicca/skills/self/` | auditor.sh:81 の self-heal | **anicca 残置＋path 参照** |
| telegram-notify | `openclaw message send`(CLI) | gig_daily_report | CLI なので path 非依存、**そのまま** |

実証（grep 実測, gig 以外で browser/scripts を参照する file）:
`earn/clip/clip-cli.sh`, `earn/clip/tests/test_vault_tick_instagrapi_keepalive.sh`,
`earn/video/video-cli.sh`, `browser/scripts/session_vault_tick.sh`, `browser/SKILL.md`。

**コピーすべきもの**（gig 専用・移設先へ持っていく）: `gig_pass.sh` `gig-cli.sh` `gig-healthcheck.sh`
`auditor.sh` `gig_reality_verify.sh` `gig_judge.py` `gig_funnel.py` `gig_daily_report.sh` `passprep.py`
`monitor.sh` `run.sh` `strategy.default.json` `GIG_PASS_RUNBOOK.md` `NO_HUMAN.md` `SLOT_CC.md`
`scripts/{gig_single_instance.sh, gig_selfimprove_verify.sh, gig_reality_gate.py, cdp_lock.sh,
cdp_daily_driver_guard.sh, cdp_snapshot.py, cdp_nav_snapshot.py, coconala/APPLY_RUNBOOK.md}`。
ただし **これらの中の `~/anicca/skills/browser/...` 参照は書き換えない**（browser を anicca に残すため）。

---

## 7. state `~/gig/`（独立 repo）の内訳

- git remote: `https://github.com/Daisuke134/anicca-gig.git`（branch main）。**skill repo とは別 repo**。
- data（jsonl/lock/trajectory 等）と **実行スクリプトが混在**:
  - `~/gig/dd-keepalive-healthcheck.sh`（loaded plist `dd-keepalive-healthcheck` の ProgramArguments）
  - `~/gig/dd-keepalive.py`（`dd-keepalive-healthcheck.sh:22` が `~/.openclaw/skills/_shared/venv-cloak/bin/python3`
    で nohup 起動）
- state を動かすと: ①RUNBOOK prompt 本文の `~/gig/...` 全書換 ②scripts 20+行の書換 ③別 repo の移設 ④
  dd-keepalive plist 連動 が全部発生 → **state は現地据え置きが最善**。移設は skill(コード)だけにし、
  state path `~/gig` はそのまま参照する。

---

## 8. 移設手順ドラフト（未実行 / 番号順・無停止指向）

前提: state `~/gig` と browser 基盤 `~/anicca/skills/browser` と `_shared` は **動かさない**。動かすのは
gig 専用のコード（skill）と plist の指す先だけ。移設先は `~/profitable-claude/skills/gig-work/`。

0. **凍結スナップショット**: `diff <(cd ~/anicca/skills/earn/gig && find . -type f|sort)
   <(cd ~/profitable-claude/skills/gig-work && find . -type f|sort)` を完全取得し、① LIVE を正として
   ②へ **rsync（①→②で上書き, ただし②固有の archive/artifacts/新 tests は温存判断）**。名前違い
   (`gig_funnel.py` vs `funnel.py`) は①を正に統一。SKILL.md 不要。→ ここは private repo なので commit。

   **DONE 2026-07-18** — PC commits: `d5d5e24`(rsync sync + gig-cli STARTUP を detached 起動化), `6eb8d22`(gig self-ref path rewrite → gig-work、earn/gig grep=0 launchd除く). exit proof E1-E4 全 green（① vs ② diff = ②固有温存物のみ・①only=0／全 .sh bash -n green／全 .py py_compile green／gig-cli に run_in_background・timeout600000 の旧起動形式 0、detached nohup×2）. ★実測訂正: `funnel.py`(②82行) と `gig_funnel.py`(①167行) は SequenceMatcher 類似度 **0.038 = 完全な別実装**（改名ではない。②の funnel.py+funnel_report.py+4テストは独立サブシステム）。よって「①名へ git mv 改名」は不成立 → rename せず**両方温存**し、runtime は①の gig_funnel.py に統一（gig_pass.sh が呼ぶ）。②の funnel サブシステムを①へ統合するか破棄するかは step1-2(#9)で lead 判断。detached 起動は macOS に setsid が無いため `nohup … >/dev/null 2>&1 </dev/null & disown` で実装。
1. **移設先で browser 参照が解決するか検証**: ②の `run.sh` から `../../_shared` = `~/profitable-claude/skills/_shared`
   に `lib.proactive_observe` があるか確認。無ければ①の `_shared` を②へ copy（clip/video と共有なら別途整理）。
   `~/anicca/skills/browser/...` の絶対パス参照はそのまま解決するので触らない。
2. **dry 検証（no side-effect）**: ②の `gig-cli.sh --status` 等を **tmux socket/session 名を一時変更した状態で**
   単発実行し、browser 基盤・`~/gig` state・`~/.openclaw/.env`・`:8317` に届くか確認。**この時点で本番 tmux
   `anicca-gig-core` は絶対 kill しない**（前回事故の原因）。
3. **plist を原子的に切替**（ここが唯一の停止リスク点、手早く）:
   a. 旧 5 plist を `launchctl bootout`（gig-auditor / gig-core-healthcheck / gig-daily-report /
      gig-proactive / gig-selfimprove-verify）。**session-vault と dd-keepalive は触らない**。
   b. ②の新 plist（`hf-gig-*` を全 5 系統ぶん用意＝現状 2 本しかないので daily-report/proactive/
      selfimprove-verify の plist を追加作成）を `~/Library/LaunchAgents/` へ配置し `bootstrap`。
      ログパスは旧と共有だと混線するので新パスに分けるか許容を明記。
   c. 旧 tmux core を `gig-cli.sh --restart` 相当で **新 gig-cli 経由に一度だけ張り替え**（socket 名を
      変えるなら旧 session を kill→新 session 起動を1コマンドで。heartbeat `~/gig/.last-pass` は共有なので
      新旧 healthcheck が二重に見ないよう a→c を連続実行）。
4. **旧配置を tombstone**（削除ではなく無効化）: `~/anicca/skills/earn/gig/` は OSS public repo に残るが、
   plist から参照されなくなったことを確認後、README/NO_HUMAN に「moved to profitable-claude」を記す
   （実削除は別 PR、参照 0 を grep 実測してから）。
5. **③ `~/.openclaw/skills/anicca-earn-gig` と ④ founder コピーの扱いを決定**（本 inventory 対象外の別判断。
   同期していないなら delete か再 vendor）。
6. **無停止検証**: 切替後 300s 以内に新 healthcheck が heartbeat を維持し、`~/gig/.last-pass` が更新され、
   `audit.jsonl` に verdict が載り、telegram 日報が届くまで watch。旧 Label が二度と起きないことを
   `launchctl list | grep gig` で確認。

**壊れる順序リスク（機械的導出）**: plist 切替(3) より先に skill を①から削除すると healthcheck が
旧パスで即 FAIL ループ。逆に skill だけ②へ置いて plist を旧のまま放置すると①が回り続け②は死蔵（＝現状）。
browser/`_shared`/`~/gig` を先に動かすと gig 以外(clip/video/session-vault)が巻き添え。よって順序は
**「②へ同期(0) → 依存解決検証(1) → dry(2) → plist+tmux 原子切替(3) → tombstone(4)」以外は不可**。

### 8bis. 移設時に同時に直すべき既知欠陥（本 inventory では未実装・記載のみ）

**欠陥: B1/PROFILE の mid-pass kill（確定真因）。**
- 現象: 長いパス（B1 nurture 全トークルーム sweep / PROFILE 画像生成+upload）が途中で殺され、
  reality-verifier が「claim と実画面が不一致」を検出して self-heal が走る。
- 確定真因: **gig-core agent が `gig_pass.sh` を Claude Code の background Bash 子プロセスとして起動しており、
  その Bash tool は timeout 上限 600000ms（= 10分）で kill される。** 10分を超えるパスは harness timeout に
  殺され、B1/PROFILE のような重いステップが未完で落ちる。gig_pass.sh 自体は各ステップを bounded sub-call に
  分割している（`gig_pass.sh:4` のコメント参照）が、**親の `gig_pass.sh` 呼び出しそのもの**が 10分枠に収まらない。
- 該当 file:line（起動箇所, 2 か所とも同一行の STARTUP 文字列内）:
  - `~/anicca/skills/earn/gig/gig-cli.sh:21` の `STARTUP='...'` 内、CronCreate の `prompt=` に埋め込まれた
    hourly:27 パス起動: `run bash ~/anicca/skills/earn/gig/gig_pass.sh`
  - 同 `gig-cli.sh:21` 内、起動直後の即時パス: `THEN run ONE full pass now: bash ~/anicca/skills/earn/gig/gig_pass.sh`
  - （この STARTUP 文字列は `gig-cli.sh:44` で `~/gig/.startup-prompt.txt` に書き出され、tmux core が読む）
- 耐久修正案（移設先②の `gig-cli.sh` STARTUP を書き換える際に同時適用。**本 inventory では未実装**）:
  agent が gig_pass.sh を **detached 起動**するよう prompt を変更し、harness の 10分 timeout から切り離す:
  ```
  setsid nohup bash ~/<新パス>/gig_pass.sh >/dev/null 2>&1 & disown
  ```
  （fire-and-forget 化。完了確認は従来どおり `tail -3 ~/gig/pass-report.jsonl` を後続 tick で読む形へ。）
- 移設との結合: STARTUP 内の `~/anicca/skills/earn/gig/gig_pass.sh` は移設で新パスへ書き換える対象なので、
  **パス書き換えと detached 化を同じ編集で行うのが最小コスト**（②の gig-cli.sh:21 相当行）。この修正は
  移設手順 (0) の「①→②同期」時点で②側の gig-cli.sh に折り込む。関連 TaskList: #7 gig_pass detached 起動化。

---

## 8-0 結果記録（2026-07-18）: step0 DONE + 2段レビュー完了

commit `d5d5e24`（profitable-claude）。spec 準拠レビュー ✅（E1-E5 全 PASS、①無変更実証）、品質レビュー
**Approved（step0 範囲）**。レビューが出した cutover 前提条件（#9/#10 で必ず消化。放置=重複応募事故）:
- **C1（Critical）**: gig_pass.sh:27 の stale lock 回収閾値 1800s < 最悪 pass 90分。detached 化で長時間 pass が
  生存するようになった結果、次の hourly tick が生存 pass の lock を回収し2パス同時運転 → 実マーケットに重複応募。
  修正 = 閾値 7200s 化（①を直して②へ再同期）
- **I1**: ②の gig_pass.sh:11,13（G=/RB= が①を指す）、gig-healthcheck.sh:31（①の gig-cli を restart）、
  gig_judge.py:152 の retarget が cutover 必須（放置すると #10 切替後に旧 STARTUP が無言復活）
- **I2**: ②launchd/ に①由来 plist 2本が混入し hf-gig-* と二重 → archive/ へ
- **I3**: sync が②固有ゲート2点を消した — GIG_KYC_CONFIRMED gate（§7.55）と registry_enforce_or_exit gig
  （REQ-CEO-009）。②へ再折込必須（OSS hygiene と CEO 制御の生命線）
- **M2**: STARTUP 内 `& disown .` のピリオド隣接 → スペース挿入

## 8-0bis 結果記録（2026-07-18）: step1-2（#9）DONE — レビュー発見の消化 + dry 検証

PC commit `1d361de`、anicca commit `fc651ef7`（① C1）。本番（① tmux `anicca-gig-core`・plist・~/gig state）は
全作業後も無傷（前後で has-session ALIVE 実測）。②はまだ launchd 未配線なので切替は #10 のまま。

- **C1 DONE**: ①②両方の `gig_pass.sh:28`（実測行。spec は :27 と書いていたが実物は 28 行目）を `-gt 1800`
  → `-gt 7200`（>120min）へ。①は未 commit だと self-update に巻き戻されるため即 commit（`fc651ef7`、実測で巻き戻し1回発生→再適用済み）。
- **I1 = step0 で既に完了していた（訂正）**: gig_pass.sh:11,13 / gig-healthcheck.sh:31 / gig_judge.py:152 は
  step0 の commit `6eb8d22` で既に gig-work へ retarget 済み（grep 実測: ② の `~/anicca/skills/earn/gig` 自己参照 =
  archive 除き 0 hit、browser 参照 `~/anicca/skills/browser` は仕様どおり残存）。#9 での追加変更は不要。
- **I2 DONE**: ①由来 plist 2本を `archive/launchd/` へ git mv（rename 記録）。`launchd/` は hf-gig-* 2本のみ残存。
- **I3 DONE**: 現行②（LIVE 同期版）の gig-cli.sh に KYC opt-in gate（GIG_KYC_CONFIRMED、§7.55）と
  `registry_enforce_or_exit gig`（REQ-CEO-009、fail-open）を再折込。配置は `--status`/`--restart` と
  idempotent alive-check の**後**（gig-cli.sh:40 と :60-62）＝ status 照会と稼働中 core を壊さず、fresh spawn のみ gate。
  dry で GIG_KYC_CONFIRMED 未設定→spawn 拒否（tmux 起動ゼロ）を実測。
- **M2 = 既に充足だった（訂正）**: d5d5e24/6eb8d22 とも occurrence1 は `disown`+SPACE(0x20)+PERIOD(0x2e)+SPACE
  の hexdump 実測で、reviewer が想定した「ピリオド隣接（スペース無し）」ではない。追加編集不要。
- **dry 検証4点 green**（本番接触ゼロ、temp socket `/tmp/gig-dry-test.sock`/session `gig-dry-test` の sed コピー、
  終了時 kill-server+rm で掃除・不在確認）: (a) browser 基盤 6 script py_compile OK (b) ~/gig state 読取 OK
  (c) ~/.openclaw/.env 読取 OK 743行 (d) :8317 CLIProxyAPI HTTP 200。
- **既知ベースライン**: 掃除後の `tmux -S <temp> ls` が socket 不在で非ゼロ exit（"error connecting ..."）＝
  temp socket 除去成功のシグナル。副作用ゼロ、fablize gate 用に記録。

## 8-1,2 結果記録（2026-07-18）: step1-2 実装済み、品質レビュー Not Approved → fix 中

実装 = ① `fc651ef7`（C1 7200s）/ ② `1d361de`（C1/I2/I3）/ spec `d89728e32`（dry 4点 green 記録）。
spec 準拠レビュー ✅。品質レビュー **Not Approved**、以下が #10 cutover の blocking 前提:
- **C-1（Critical）**: `GIG_KYC_CONFIRMED=1` が live 環境のどこにも未設定（~/.openclaw/.env・plist・zshrc 全 grep 0）
  なのに ② gig-cli.sh:39 のコメントは「live Dais instance が設定済み」と虚偽。このまま切替えると②の全起動
  経路が KYC gate で exit 0 = gig loop 無音恒久停止。fix = コメント是正 + ② gig-cli.sh が ~/.openclaw/.env を
  source する配線 + .env に GIG_KYC_CONFIRMED=1 追記
- **I-1**: ② の snapshot test `tests/ceo/test_prompt_integrity_snapshot.sh` が 14/17 RED — step0 rsync が
  ②の snapshot 準拠版 gig-cli.sh（effective-cron/gig.txt 読み + COCONALA_HANDLE 等の STARTUP パラメータ化）を
  ①旧版で上書きした結果。I3 再折込が KYC/registry だけで不完全。fix = snapshot 版の機能を detached 起動と
  合成して再折込、test 17/17 green まで
- **I-2**: KYC gate の onboarding メッセージが読まれない3変数を指示（I-1 の再折込で解消）
- M-1（非 blocking、将来堅牢化として台帳記録）: lock mtime は mkdir 時のみ。120min 超 pass は依然誤 reap。
  heartbeat 方式（各 step で touch $LOCKD）が真の解。M-2: registry fail-open は set -e 非依存が前提（bounty と同形）。

**FIX 完了（2026-07-18、team-lead 直接実装、commit `ac28be7` PC main push 済み）**: C-1 = gig-cli.sh が
~/.openclaw/.env を source（gate 前）+ .env に GIG_KYC_CONFIRMED=1 と識別子3キー追記（追記のみ・実測:
クリーン env から KYC=1/HANDLE=mtdc/REPO 解決）+ 虚偽コメント是正。I-1/I-2 = STARTUP に識別子3変数の
interpolation 復活 + cron ハードコードを state/effective-cron/gig.txt 読みに置換。snapshot fixture は
**意図的に再採取**（pass 本体は gig_pass.sh + RUNBOOK へ移行済みの新建築が正。task-request-map/passprep/
funnel 機構の存在を grep 実測してから採取）。test_prompt_integrity_snapshot **17/17** +
test_registry_enforce_core **12/12**（回帰なし）。quality re-review 待ち。

## 8-3 結果記録（2026-07-18 20:2x JST）: 原子切替 DONE（cutover 完了、gig は PC が本番）

実行 = Sol one-shot（/flowa 体制: Fable plan+verify / Sol execute）。パス走行中を避け lock 解放後に実施。
- bootout 旧5 Label → 全滅を launchctl 実測 / 旧 plist 5本は `~/Library/LaunchAgents.disabled-gig-migration-20260718/`
  へ退避（rollback = 戻して bootstrap）/ hf-gig 4本 bootstrap（**proactive は意図的に作らず** — restart map は
  2026-07-06 から空で no-op だった、step3_recipe.py:218 実測）
- tmux 張り替え → 新 core ALIVE、新 STARTUP（identifier interpolation + effective-cron 読み + detached driver）
  で始動し、即座に新パスが ②の gig_pass.sh で実走開始（lock 実測）。旧 core は最終パス全 step 完走で退役
- Sol の「ABORT」出力は最終検証 grep の基準誤り（新 STARTUP 先頭300字に repo パスが無いのは設計通り。
  切替シーケンス自体は完遂していた）— one-shot の自己申告を Fable が実測で上書きした実例
- 残検証は §8-4,5,6（#11）: 300s healthcheck 維持・次毎時パス完走・tombstone

## 8ter. Dais 裁定による方針更新（2026-07-18、§6 の「anicca に残して参照」を上書き）

裁定: **PC (profitable-claude) が claude-p loop の唯一の家。clone すれば単体で回る self-contained を最終形とする。
「graduate to anicca」は破棄（README にもその記述は元々無い、実測済み）。**
よって §6 の「browser 基盤は anicca に残して path 参照」は**中間形**に格下げ。最終形 = browser 6 script + _shared
必要分を PC の skills/_shared へ **vendor(copy) + skills.lock 記録**（PC に既存の vendor manifest 方式に乗せる）。
move は不可: franklin1/2 (self-funded) の launcher が runtime で literal `$HOME/anicca/skills/browser/...` を
直接呼んでいる（両 HOME grep 実測）。anicca 側 tombstone の前提条件 = franklin launcher の自コピー参照化 +
plist_render.py の anicca_home 前提解消（別トラック）。全 loop の依存地図 =
`2026-07-18-pc-repo-singularization-inventory.md`（作成中）が正本。

## 9. OSS 公開時の私密データ保存規約（TO-BE、2026-07-18 追記）

原則: **repo = code のみ。私密データは全て data home `~/.profitable-claude/` に置き、repo には path 契約
（env 名と既定値）だけを書く。** これで clone した誰でも（追加パッケージなしで）同じ path で動く —
既定値は `$HOME` 相対だから万人共通、上級者は env で上書き可能。既存実例の踏襲: `~/.blockrun`
`~/.openclaw` と同型（app-specific data home パターン）。install.sh が mkdir + chmod する。

| 私密データの種類 | 例（gig loop 実物） | 置き場（TO-BE） | 権限 |
|---|---|---|---|
| ログインセッション/cookie | Coconala/Google session、CloakBrowser vault | `~/.profitable-claude/vault/`（当機は既存 `~/.cloak` を `PC_VAULT_DIR` で指す） | 700 |
| API キー/トークン | telegram bot token, CLIProxyAPI, blockrun | `~/.profitable-claude/.env`（repo には `.env.example` のみ） | 600 |
| loop state（業務データ） | applied.jsonl / shuppin.jsonl / lessons.jsonl | `~/.profitable-claude/state/<loop>/`（当機の gig は既存 `~/gig` を `GIG_STATE_DIR` で指す＝据え置き、§TOP3-3 準拠） | 700 |
| 金の台帳 | earnings.jsonl / ledgers | `~/.profitable-claude/state/<loop>/` 同上（横断は `~/.profitable-claude/ledgers/`） | 700 |
| 個人/KYC 情報 | 口座・電話番号・本人情報 | vault のみ。repo/docs/commit 本文にも書かない | 700 |
| ログ | pass ログ, healthcheck ログ | `~/.profitable-claude/logs/<loop>/` | 755 |

path 解決の契約: 各 loop は `PC_HOME`（既定 `$HOME/.profitable-claude`）起点で解決。当機のような既存
配置は env 上書きで無改修吸収。plist は install.sh が env を焼き込んで生成（絶対パス手書き禁止）。
`.gitignore` は deny-by-default（`*` + allowlist）で、state/vault/env の混入を構造的に不可能にする。

## 10. TO-BE tree と残 TODO の最終形（§8 と整合、2026-07-18 時点）

TO-BE tree = `docs/reference/2026-07-18-multi-loop-repo-structure-research.md` の TL;DR に §9 を合成
（skills/gig-work/ 自己完結 + config/loop-registry.json + 私密は ~/.profitable-claude/）。

残 TODO（順序厳守。番号は §8 と対応、TaskList 登録済み）:
0. ①→② rsync 同期 + gig-cli.sh に detached 起動と新パスを同時折込（§8bis）
1. ②の browser/_shared 依存解決検証
2. dry 検証（本番 tmux は kill しない）
3. plist 5本 + tmux の原子切替（唯一の停止リスク点）
4. 旧配置 tombstone
5. 散在コピー③④の処分判断
6. 無停止検証（300s heartbeat + 旧 Label 復活ゼロ）
7. config/loop-registry.json + README 台帳表の新設
8. OSS 公開前 hygiene: §9 の保存規約実装（install.sh / .env.example / deny-by-default .gitignore / secret 混入 grep 監査）

---

## 付録: 本 inventory 作成時の tool 非致命 exit（fablize gate 記録用）
- `diff <(find①) <(find②)` が exit 1 → **正常**（差分ありで 1 を返す仕様）。
- `ls SKILL.md` が exit 1 → **正常**（両コピーに SKILL.md が無いことの確認、期待どおり）。
- 逆参照 grep が 4530 files 9831 matches → over-broad パターンによるノイズ（worktrees/vcsdd findings/
  node_modules を含んだため）。§3/§8 の配線点は `runtime/loop/` 限定 grep で isolate 済み。
いずれも実害なし・既知ベースライン。
