# 発注: Phase 2 M-1 — launch demo video 1本（MoneyPrinterTurbo 方式 PoC 兼 launch 素材）

正本: /Users/anicca/anicca-project/docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md
必読節: §9.2（video loop 決定）、§9.10 D（変換公式: ①pain 実写 ②LM 発動の瞬間 ③報告文 = punchline。機能一覧 video 禁止）、§10.1 U6（MPT は faceless-money-factory の代替レンダラーとしてのみ）。
役割: Sol = build+execute+verify+報告。質問 = bash ~/.agents/skills/agmsg/scripts/send.sh lm-p0 sol-m1 fable-main '<msg>'。

## 何を作るか
launch 用 demo video 1本（9:16、20-40秒、日本語 or 英語は素材に合わせ判断して報告）。
- 題材 = §9.10 matrix A の「T-10/T-5 call」行（実証済みの核）。
- ★本物素材のみ★: 実 call 録音（~/.openclaw/state/lm-video/recordings/ に whisper 済み mp3 あり — 例 2026-07-19T23-40-35-932b3fad….mp3 は英語双方向）+ 実 TG スクショ（LM bot チャットの実メッセージ。Telethon で撮る or 既存 screenshot）。fake UI/演出モック禁止。
- 生成 backend: まず既存 ~/profitable-claude/skills/ の faceless-money-factory / video 系 skill の生成経路を実読し、その backend として MoneyPrinterTurbo 型合成（MoviePy/FFmpeg、Edge TTS、$0）を流用。全置換しない。
- 出力: mp4 をローカル（~/anicca-project/.claude/sol-orders/out/ など）+ 生成コマンド・所要時間・コストを記録。

## 検証
mp4 が実在し、ffprobe で 9:16・音声トラックあり・長さ 20-40s を実測。内容の final check は Fable（俺は投稿しない — X/Slack 用は Dais 納品、IG は後続 M-2 の loop が投稿）。

## 禁止
実投稿（どこにも投稿するな — 納品まで）/ 架空の画面・数字の合成 / Dais 個人 account 操作。

DONE 報告: mp4 path + ffprobe 実出力 + 使用素材リスト + 生成時間/コスト。
