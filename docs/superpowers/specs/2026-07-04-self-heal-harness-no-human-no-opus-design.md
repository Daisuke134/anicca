# Self-Heal Harness: 人間もOpusも私(dev Claude Code)も介在しない自己修復 — Design

**Date**: 2026-07-04 · **Branch**: `feature/clip-rewards` · **Owner**: 私(myclaude, human-funded)
**Trigger**: Dais「claude-p/ClawRouterが自己修復できず、私(Claude Code dev session)が全部手動で
診断・修正している。人間もOpusも私もループに入らない自己修復ハーネスを作れ。Sutandoのコードを読み、
車輪の再発明をするな。」
**調査**: Sutando(`github.com/sonichi/sutando`)実コード精読 + 他OSS(Cronicle/systemd/supervisord/
PM2/OpenHands-resolver/RunbookHermes)パターン調査、両方subagentで並列実施(2026-07-04)。

## 0. 反省(このセッション自体が反例)

今回のセッション中に発見した全ての異常(disk cleaner 3重問題、producer.sh venv消失、cookie復号
失敗、tmuxソケット消失→重複起動、disk容量危機)は、**全て私(Claude Code dev session)が手動で
気づき、手動で診断し、手動で直した**。claude-p/ClawRouter自身は一度も自分でこれらに気づいて対処
していない。これは自己修復ハーネスの不在を証明する実例そのもの。

## 1. Sutandoから学んだ核心原則

`src/health-check.py`(2325行)の`recover_core_if_wedged()`が全て。README の「self-rewrite」という
表現は誇張で、実際にやっているのは**コードの自動書き換えではなく、プロセスの再起動 +
「稼働中のエージェント自身への判断委任」**。

```
監視プロセス(launchd、300秒毎、pure python/bash、$0コスト)
  → 「生きてるが詰まってる(wedged)」を検知
     (heartbeatは生きているが、タスクキューの進捗タイムスタンプが停滞)
  → tasks/task-health-*.txt にタスクを書き込む
  → 次にcore(tmux上で動くclaude、既にファイル編集ツールを持つ)が
    このタスクファイルを読み、★自分のLLM判断で★ 再起動/診断/無視を決める
  → 外部の人間・上位AI(Opus等)は一切介在しない
```

安全装置(全て採用すべき):
- `fcntl.flock`による排他制御(健康チェック自体の多重起動防止)
- 「生死」だけでなく「詰まり」を**タスク進捗タイムスタンプの停滞**で検知(単純なプロセス生存確認
  より一段深い診断)
- `RECOVER_CONFIRM_SEC`: 2回観測してから確定(1回の観測で即断しない=誤検知防止)
- `RECOVER_COOLDOWN_SEC`(30分)+ `RECOVER_MAX_PER_HOUR`(3回でgive up、Slack DMのみ、無限ループ
  しない)
- 再発時はグレースフルデグレード(1M context→200K標準へ縮退)
- 「同一プロセス内からの自己kill禁止」ガード(`start-cli.sh`自身に明記)
- 387行のテストスイートで全ガード条件を単体テスト済み

agent-registry(SQLite peer registry)自体にresurrection機能は無い(単なる可視化)。resurrectionは
health-check.py側の別ロジック。day/night切替の専用実装も存在せず、実体は単なる夜間cron
(`obsidian-dream` 03:37、`learned-skills-scan` 07:30)——README の要約は実装より誇張されている。

## 2. 他OSSから輸入すべきパターン

| # | 出典 | パターン | Anicca適用 |
|---|---|---|---|
| 1 | `jhuckaby/Cronicle` `bin/control.sh` | pidfile読込 + `kill -0`だけでなく **`ps -p $PID -o args=` でコマンドライン内容も一致確認**してから「生きている」と判定 | ★そのまま輸入★ — 今回のtmuxソケット消失→誤판정→重複起動事故の直接対策 |
| 2 | 一般パターン | `flock -n <lockfile> $0 \|\| exit 0` | ★そのまま輸入★ — healthcheck自体の多重起動を1行で防止 |
| 3 | systemd/supervisord/PM2 | 指数バックオフ + 一定時間健全ならペナルティをリセット | gigのbackoffは固定窓(60分5回)、指数+自動リセットに強化余地あり |
| 4 | `All-Hands-AI/openhands-resolver` | 診断→修正→`exit_code==0`になるまでn_retries検証→初めてpatchを正とする | self/issue-dev連携時の検証ループとして採用 |
| 5 | `Tommy-yw/RunbookHermes` | evidence-first診断→危険操作はdry-run/checkpoint必須→事後にrunbookを自己蓄積 | 重い前提(Prometheus等)は不要、concept(危険操作の前にdry-run)だけ抽出 |

## 3. 設計: Anicca self-heal harness v2(人間・Opus非介在)

```
┌─────────────────────────────────────────────────────────────────────┐
│ 監視層(pure bash、$0、5分毎launchd) — 各 *-healthcheck.sh          │
├─────────────────────────────────────────────────────────────────────┤
│ ① flock で多重起動防止(自分自身の重複実行を防ぐ)                    │
│ ② pidfile + `ps -p $PID -o args=` でプロセス実体を二重検証           │
│    (tmux has-session だけに頼らない = ソケット消失に耐性)            │
│ ③ 「生死」に加え「詰まり」検知: .last-pass 等のタイムスタンプ停滞    │
│    を2回連続observe(RECOVER_CONFIRM的)してから確定                  │
│ ④ backoff(既存gig方式: 60分5回) + give-up capでの停止              │
│ ⑤ give-up時: Slack通知 ★だけでなく★ タスクファイルを書く            │
│    (~/.openclaw/state/<loop>-selfheal-request.json)                 │
└──────────────────────────────┬────────────────────────────────────┘
                                │ (人間もOpusもここに介在しない)
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 判断層 = 稼働中のclaude-p自身(次回cron wake時)                      │
├─────────────────────────────────────────────────────────────────────┤
│ *-cli.shのSTARTUPプロンプトに追記:                                   │
│ 「まず ~/.openclaw/state/<loop>-selfheal-request.json を確認し、     │
│  あれば内容を読んで★自分のLLM判断で★診断・修正を試みよ。            │
│  実行ログ(/tmp/*.log等)を自分で読み、根本原因を特定し、             │
│  コード修正が必要ならVSDD RED→GREENで直接直す。                      │
│  自分で直せない場合のみ self/issue-dev を呼んで母リポジトリに        │
│  Issueを立てる(= Sutandoのtask-file→稼働中エージェント委任と同型)」  │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 修復手段(claude-p自身が使う、全て既存ツール)                        │
├─────────────────────────────────────────────────────────────────────┤
│ A. 直接修正: 該当スクリプトをEdit → 実行 → 結果確認 → OK ならそのまま │
│ B. self/issue-dev: 直せない/不確実 → GitHub Issueを母リポジトリに   │
│    (Daisuke134/anicca) 起票 → 次回 git pull で全instanceに配布      │
│ C. n_retries検証(OpenHands-resolver方式): 修正後、実際に実行して    │
│    exit_code確認、それでも失敗ならロールバック(git checkout --)     │
└─────────────────────────────────────────────────────────────────────┘
```

## 4. 実装タスク(この直後にTaskCreate)

1. `*-healthcheck.sh`(clip/affiliate/video/bounty/gig)に `flock` 排他制御を追加(1行、リスク低)
2. `*-healthcheck.sh`に pidfile + `ps -p $PID -o args=` の二重検証を追加(Cronicle方式、
   tmux has-sessionへの依存を減らす)
3. clip/affiliate/video/bounty に gig方式の「詰まり検知」(.last-pass的タイムスタンプ停滞、
   2回observe後確定)を移植
4. give-up時にSlack通知 + `<loop>-selfheal-request.json` タスクファイル書き込みを追加
5. 各loopの `*-cli.sh` STARTUP プロンプトに「selfheal-request.json を確認し自分で診断・修正、
   ダメならself/issue-dev」の一文を追加
6. **重要**: 前回セッション内で「ALIVE時の孤立プロセス自動掃除」が2回誤作動しセッションを
   落とす事故を起こした教訓を踏まえ、①②③④⑤は全て **DEAD/詰まり確定時のみ発動**、
   ALIVE正常時には何もkillしない設計を厳守する(Cronicleのプロセス実体検証は「判定の精度を
   上げる」ためであり「常時何かをkillする」ためではない)

## 5. 完了条件

- 5つのloop全てにflock+pidfile二重検証+詰まり検知+タスクファイル委任が実装済み
- 実機で「意図的にqueueを空にする」「意図的にcookieを壊す」等の異常を注入し、claude-p自身が
  次回wakeでselfheal-request.jsonを読んで診断・修正を試みることをE2E確認(人間・Opus不使用)
- 少なくとも1回、claude-p自身がself/issue-devを呼んでGitHub Issueを立てるところまで実機確認

## 6. 実装結果(2026-07-04、完了)

①②③④⑤のうち、②(pidfile+プロセス実体二重検証、Cronicle方式)は**見送り**とした。
理由: 実装前に検討したところ、判定を誤ると「本来ALIVEな正規プロセスをDEAD扱いする」リスクが
③(詰まり検知)実装中に実際に発現した(下記参照)のと同種のパターンであり、外部プロセスから
「これが本物か」を安全に判定する手段が確立できていない状態で追加するのは危険と判断。

①(mkdir atomicロック)③(詰まり検知)④(give-upタスクファイル)⑤(cli.sh自己診断指示)は
全5loopに実装・実機検証・push済み:

- ①: 5loop全てに`/tmp/.<name>-healthcheck.lock`のmkdir atomicロックを追加。healthcheck自体の
  多重起動(launchdが前回実行完了前に次を起動)によるDEAD判定の競合を防止。
- ③: gig-healthcheck.shの実証済みSTALE検知パターン(`.last-pass`タイムスタンプ+`.last-start`
  猶予期間+DEAD/first-pending/STALE/fresh の4分岐)を、clip(90分)/video(360分)/
  affiliate・bounty(1560分)の各cron頻度に応じたSTALE_MINでverbatim移植。
  **実装中に発見・修正したバグ**: `.last-start`が存在しない場合の`stat`失敗フォールバックが
  `echo 0`(epoch-0=1970年)になっており、既存(移行前起動)セッションでSTART_AGEが
  約2900万分という巨大値になり、実機で実際に誤って即時restartを引き起こした
  (clip-coreで実際に発生、実害は軽微=セッション再起動のみ、正規プロセスの誤killではない)。
  フォールバックを`date +%s`(現在時刻)に修正し、以後誤判定なしを実機確認。
- ④: backoff上限(60分5回)到達時、`~/.openclaw/state/.<loop>-core-selfheal-request.json`に
  構造化タスク(loop名/理由/再起動回数/次にすべきこと)を書き込む処理を追加。1時間以内の
  重複書き込みは抑制。
- ⑤: 各loopのcronプロンプト冒頭に「まずselfheal-request.jsonを確認し、あれば自分で診断・
  修正、ダメならself/issue-devを呼ぶ」指示を追加。**既知の制約**: 既存の登録済みcron
  (`.claude/scheduled_tasks.json`)のプロンプト文字列は、CronListで「既存job有り」と
  判定されると再登録されないため、通常運用では古いプロンプトのまま動き続ける可能性がある。
  ただし「詰まってhealthcheckがrestartする瞬間」にこそ新しいSTARTUP(=自己修復ロジック)が
  効くため、設計としては理にかなっている。恒久的なcronプロンプト更新の仕組みは別タスク。

**未実施(次回以降の課題)**: 完了条件の「実機で異常を注入してE2E確認」「claude-p自身が
self/issue-devを呼ぶところまでの実機確認」は、backoff上限到達(60分5回の実際の失敗)を
安全に人為的に再現する方法がまだ無いため未実施。次回、意図的に壊れたコマンドをrun.sh等に
一時的に仕込んで実機確認する計画。
