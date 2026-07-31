# 発注: M-2 rescue — daily Life Manager video loop を実 IG 投稿まで完遂

> **HOLD — 起動禁止。** 正本§10のCORE 8d-hが先行gate。8d-hのL3とFable裁定が揃った後にだけ本発注を再読・現状へrebaseして起動する。

正本: `/Users/anicca/anicca-project/docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`
先行発注: `/Users/anicca/anicca-project/.claude/sol-orders/order-m2.md`
停止ログ: `/tmp/sol-m2.log`

## 役割と最終状態

あなたは実行担当 Sol。Fable は実装・実行しない。既存 M-2 の未commit差分を安全に回収し、daily Life Manager video generator を本番 daily loop に組み込み、launchd の正規経路から実 MP4 を生成して専用 IG account に実投稿し、公開 URL をlogged-outで確認する。実装・execute・verify・spec更新・commit・push・agmsg DONE 報告をすべてあなたが行う。

Done means:

1. TDD RED→GREEN の履歴を保ち、対象 unit/wiring tests と関連 full suite が fresh PASS。
2. 実素材を使った fresh MP4 が生成され、ffprobe で 1080×1920 / H.264 / AAC / 20–40秒、full decode exit 0。
3. `ai.anicca.life-manager-daily` を正規の launchd 経路で kickstartし、生成した exact MP4 が既存 IG 投稿経路から投稿される。
4. 実 IG URL を cookie-less session で公開確認し、ledger に `creative_id` と `creative_output` が一致する実 row がある。
5. `profitable-claude` の M-2対象差分と `anicca-project` の spec 更新が対象パス限定で commit/push 済み。
6. §10 9b は2日連続生成が未達なら `in_progress (day 1)` と正直に記録し、doneにしない。§10 9c はIG実URLを記録し、TikTokはM-3待ちと明記する。

## 最初に読むもの

1. `/Users/anicca/anicca-project/AGENTS.md`
2. `/Users/anicca/.codex/RTK.md`
3. 正本 spec の §9.2、§9.10、§10、§10.0、§10.2
4. 先行発注 `order-m2.md`
5. `/tmp/sol-m2.log` の最後150行
6. `/Users/anicca/profitable-claude/AGENTS.md` と、存在する場合は隣接 skill/rules

## 現在の実測ベースライン

- 旧 M-2 process は消失。ログは `collab: Wait` で終了し、DONE報告なし。
- `/Users/anicca/profitable-claude` には M-2 owned changes が未commit:
  - `skills/life-manager/README.md`
  - `skills/life-manager/life-manager-daily.sh`
  - `skills/video/SKILL.md`
  - `skills/video/daily-lm-video/`
  - `skills/video/tests/test_daily_lm_video.py`
  - `tests/lm/test_life_manager_daily_video_wiring.sh`
- fixture tests は旧ログで GREEN (`ALL DAILY-LM-VIDEO TESTS PASSED`, wiring `9/9 passed`)。これはL1のみで、fresh再実行が必要。
- `~/.openclaw/state/lm-video/daily/` は未作成、実MP4なし、M-2動画のIG URLなし。
- launchd は 10:15 dailyでloadedだが、最新runはM-2前の静止画投稿。
- 同じ `profitable-claude` main worktreeでarticle-writerの別Solが稼働しており、article系dirty changesが混在する。絶対に触らない。

## 実行規律

1. **内部subagent/collaborationを使わない。** あなた自身が直列で最後まで実行する。`collab: Wait` で停止しない。
2. 最初に `pgrep` と `git status` を実測し、article-writer担当の変更を一覧化する。article系をstash/reset/checkout/stage/commitしない。
3. `git fetch origin` 後、最新 `origin/main` から isolated worktree/branch `sol/lm-m2-rescue` を作る。既存main dirty treeから上記M-2 owned pathsだけを移植する。`git add -A` 禁止。
4. 旧実装を正しい前提と見なさない。最危険仮説は「fixture GREENでも実素材/default path/launchd環境では失敗する」。これを最初に検証する。
5. 必要なら追加RED testを先に書き、RED確認後に最小GREEN。slideshow資産は削除しない。
6. 既存 IG account / CloakBrowser投稿経路 / credentials / logged-out verification を変更しない。Dais個人SNSには投稿禁止。投稿対象は既存loop専用 `anicca.affirms2`。
7. 実投稿前に identity を hard-check。誤account投稿を発生させない。
8. secretをstdout/log/spec/gitに出さない。
9. `profitable-claude` はM-2対象だけcommit。fetch/rebaseして最新origin/mainへfast-forward可能な形でpush。root main worktreeのarticle変更を混ぜない。
10. spec repoも現在のdirty rootを使わず、最新 `origin/feature/clip-rewards` からisolated worktreeを作り、正本specだけをcommit/pushする。handoverや他変更を混ぜない。
11. 失敗時は同一手法を反復せず、最大3つの異なる手法。3手法同一atomic FAILならfalse hypothesisと証拠を§10に記録し、agmsgで報告する。

## 必須検証

- `rtk test /opt/homebrew/bin/python3 skills/video/tests/test_daily_lm_video.py`
- `rtk test bash tests/lm/test_life_manager_daily_video_wiring.sh`
- repoの実際のtest runnerを読んで関連full suiteをfresh実行
- generator default引数で実素材からfresh render
- `ffprobe` machine-readable結果 + `ffmpeg -v error ... -f null -` exit 0
- launchctl `print` before/after、kickstartのrun増分、daily log増分
- marketing ledger exact row
- 実IG URLをfresh cookie-less browserで確認
- 両repo `git status`、commit hash、remote branch/head一致

## Working method (non-negotiable)

> Working method (non-negotiable):
> 1. Restate the goal in one sentence + a "done means" criterion before acting.
> 2. Read the actual files before forming opinions; verify every path/function you reference exists in this project.
> 3. Name your riskiest assumption and check it first, while it is cheap.
> 4. The diff is a claim; execution is evidence. Run the project's build/lint/tests and report their real output.
> 5. Label claims VERIFIED (ran it) / REASONED (read it) / ASSUMED (unchecked) — never upgrade one silently.
> 6. Before finishing: re-read the original request; every requirement met, nothing promised-but-undone.

## 報告

開始・重要な状態変化・DONEを次で送る:

```bash
bash ~/.agents/skills/agmsg/scripts/send.sh lm-p0 sol-m2-rescue fable-main '<message>'
```

最終報告には、fresh test結果、ffprobe/full decode、launchctl run増分、実IG URL、ledger rowの非secret要約、両repo commit hashとpush先、§10の状態を含める。
