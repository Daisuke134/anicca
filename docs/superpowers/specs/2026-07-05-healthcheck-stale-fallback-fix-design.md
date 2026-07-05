# healthcheck.shのSTALE検知フォールバックを修正(Task #18)

## 開発環境

| 項目 | 値 |
|---|---|
| 対象repo | `~/anicca`(git管理) |
| ブランチ | `feature/healthcheck-stale-fallback-fix`(メインツリー直接、worktree不使用) |
| 対象ファイル | `skills/{earn/clip,earn/clip-promote,earn/video,human-funded/bounty,human-funded/affiliate,human-funded/gig}/*-healthcheck.sh`(6ファイル) |
| 状態 | GATE 1(spec)作成中 |

## 0. なぜこれをやるか(2026-07-05、Task #4調査中に発見、spec §24.5-24.9参照)

`2026-07-04-openclaw-claude-p-merge-design.md` §24.5で確認した実際のインシデント:
affiliate/bountyのtmuxセッションが2026-07-04 17:36の起動以来15時間以上、
一度も完了パスが無い状態のまま、healthcheck.shのSTALE自動restartが一度も
発火しなかった。`--restart`で手動復旧して初めて両loopとも正常にmail報告・
実処理が確認できた(spec §24.6-24.7)。

## 1. 根本原因(fresh grep確認済み、2つの異なる誤った実装が併存)

`.{name}-core-last-start`(healthcheckが起動時刻の目安に使うマーカー、
cli.sh自身がtmux起動直前にtouchする設計)が何らかの理由で消失した場合
(disk cleanup等でstate配下のdotfileが巻き込まれた可能性が高い、
fresh確認: affiliate/bounty/gig/videoいずれも`.{name}-core-last-start`が
本セッション開始時点で不在だった)、healthcheck.shの`START_AGE`計算が
2つの異なる、共に問題のあるフォールバックを行っていた。

### 1.1 パターンA(clip/clip-promote/video/bounty/affiliate、5ファイル共通)

```bash
START_MTIME="$(stat -f %m "$START" 2>/dev/null || date +%s)"
```
マーカー不在時に**現在時刻**へフォールバック → `START_AGE`が常に0分と
計算される → `STALE_MIN`(26h等)を**永久に超過しない** →
自動restartが二度と発火しない(今回のaffiliate/bounty incidentの直接原因)。

`clip-healthcheck.sh:82-84`のコメントが経緯を示している:
> 「NOTE: if $START itself is missing... fall back to "now" (age=0) instead
> of epoch-0 — epoch-0 made START_AGE ~30M minutes and triggered an
> immediate false restart (caught same session).」

つまりこの「現在時刻へのフォールバック」は**意図的な過去の修正**であり、
以前は下記1.2のepoch-0パターンを使っていて、それが引き起こした
別の実インシデント(健全なセッションを誤って即restartしてしまった)を
避けるために導入された。**しかし今回、その「修正」が今度は逆方向の
実インシデント(検知が永久に働かない)を引き起こした**ことが確認された。

### 1.2 パターンB(gigのみ)

```bash
START_AGE="$(( ($(date +%s) - $(stat -f %m "$HOME/gig/.last-start" 2>/dev/null || echo 0)) / 60 ))"
```
マーカー不在時に**epoch 0(1970年)**へフォールバック → `START_AGE`が
約2900万分 → 即座に`STALE_MIN`(90分)を超過 → **毎回restartが発火する**。
これがまさに1.1のコメントが言及する「immediate false restart」の原因
パターンそのもの(gigは今回はたまたま`.last-start`が存在していたため
問題が顕在化しなかっただけで、同じ潜在バグを持つ)。

### 1.3 結論: 両方とも「マーカー不在」を勝手に推測する設計自体が誤り

パターンA(現在時刻)は「検知が無効化される」方向に倒れ、パターンB
(epoch-0)は「健全なセッションを誤爆する」方向に倒れる。どちらも
「マーカーが無い」という不確実な状態を**憶測で埋めようとしている**のが
問題。正しい設計は「マーカーが無ければ、今この瞬間を起点として
マーカーを再設置し、次回のhealthcheck実行時(5分後)から正しく
計測し直す」という**自己修復的な第三の選択肢**であるべき。

## 2. 修正設計(REQ)

### REQ-1: マーカー不在時は「憶測しない」— reseedして次回に委ねる

```bash
elif [ ! -f "$HB" ]; then
  if [ ! -f "$START" ]; then
    # $START自体が無い場合(外部cleanupで消失 or このhealthcheckバージョン以前に
    # 起動したセッション)、現在時刻/epoch-0どちらのフォールバックも過去に実
    # インシデントを起こした(前者=検知が永久disable、後者=健全セッション誤爆
    # restart)。憶測せず、今このタイミングでマーカーを再設置し、次回
    # healthcheck実行(5分後)から正しく計測を再開する。本当に詰まっている
    # セッションはSTALE_MIN以内に次のhealthcheckで検知される。
    touch "$START"
    echo "$(date '+%F %T') <name>-core: .last-start marker missing -- reseeded now, will re-check next pass" >> "$LOG"
  else
    START_MTIME="$(stat -f %m "$START")"
    START_AGE="$(( ($(date +%s) - START_MTIME) / 60 ))"
    if [ "$START_AGE" -ge "$STALE_MIN" ]; then
      restart "<name>-core ALIVE but no completed pass in >=${START_AGE}min since start (never fired)"
    else
      echo "$(date '+%F %T') <name>-core ALIVE (first pass pending, ${START_AGE}min since start)" >> "$LOG"
    fi
  fi
elif ...(既存のHBベースSTALE判定、変更なし。$HBはこの分岐に来る時点で
  存在確認済みのため`|| date +%s`フォールバックは到達しない安全なdead code
  だが、一貫性のため同様に素のstatへ変更する)
```

### REQ-2: 6ファイル全てに同一修正を適用

対象: `clip-healthcheck.sh`(85行目付近)、`clip-promote-healthcheck.sh`
(69行目付近)、`video-healthcheck.sh`(54行目付近)、`bounty-healthcheck.sh`
(51行目付近)、`affiliate-healthcheck.sh`(52行目付近)、
`gig-healthcheck.sh`(56行目、epoch-0パターンから同じreseed方式に統一)。

### REQ-3: 既存のDEAD/backoff/lock機構は変更しない

このタスクのスコープは「STALE検知のマーカー不在フォールバック」のみ。
`restart()`関数のbackoff(5回/60分)、`mkdir`アトミックlock、
`.{name}-core-selfheal-request.json`生成ロジックは無変更。

## 3. 検証計画(GATE 2)

- 単体テスト(bash、`tests/test_healthcheck_stale_fallback.sh`新規、
  6 healthcheck.sh共通ロジックとして1つのテストで代表確認 + 各ファイルへの
  適用差分をgrepで機械確認):
  1. `$HB`存在・fresh → 何もしない(既存動作、非退行)
  2. `$HB`不在・`$START`不在 → reseedのみ、restartしない(false-positive防止)
  3. `$HB`不在・`$START`存在・`STALE_MIN`未満 → 何もしない(既存動作)
  4. `$HB`不在・`$START`存在・`STALE_MIN`以上 → restart呼び出し(既存動作)
  5. reseed後、`$START`が実際に`touch`されたことを確認(次回runで正しく
     計測されることの前提)
- 全6ファイルに`bash -n`構文チェック
- 実機確認: affiliate-healthcheck.shを一時的に`.last-start`を`rm`した状態で
  1回実行し、reseedされること(restartされないこと)をfresh evidenceで確認、
  その後`STALE_MIN`を一時的に極小値に変えたテスト実行で実際にrestartが
  発火することも確認(本番の`STALE_MIN`値は変更しない、テスト時のみ上書き)

## 4. スコープ外(YAGNI)

- `skills/self/{capafy-loop,reddit-loop,life-manager-loop}`の同種
  healthcheck.sh(存在確認済み、同じパターンの疑いあるが、Dais指示は
  「every earn loop」であり対象外。ただし同じ根本原因を抱えている可能性が
  高いため、Task #18完了後にNext Actionsとして記録するに留める)
- healthcheckの実行頻度(launchd `StartInterval`)自体の変更は行わない
