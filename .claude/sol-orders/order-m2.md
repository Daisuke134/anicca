# 発注: M-2 — claude-p marketing loop を slideshow → video 毎日1本に切替（launchd 常設）

正本: /Users/anicca/anicca-project/docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md
必読節: §9.2（配信: IG=既存 claude-p loop / TikTok=Postiz は M-3 で。launchd 常設・毎日・人手ゼロ）、§9.10 D（1 video = matrix 1行。①pain 実写 ②LM 発動の瞬間 ③報告文 punchline。機能一覧 video 禁止）、§9.10 A/B（脚本銀行 = 16行）、§10 9a 行（M-1 の生成パイプライン実績 = 実録音+whisper 字幕+stock+FFmpeg、render 42s、$0）。
役割: Sol = build+execute+verify+spec 更新+commit+push。質問 = bash ~/.agents/skills/agmsg/scripts/send.sh lm-p0 sol-m2 fable-main '<msg>'。
対象 repo: ~/profitable-claude（trunk に直 push 可の repo か実測して従う。worktree 不要ならその旨 PR 説明/commit に記す）。

## 現状（まず実読）
- 既存 loop: ~/profitable-claude/skills/life-manager/（launchd 10:15 JST、SELF-MARKETING、IG 実投稿）と skills/video/ + faceless-money-factory 系の生成経路。M-1 が使った生成 script は ~/anicca-project/.claude/sol-orders/out/m1/ 周辺と /tmp/sol-m1.log に痕跡。
- 重要: 既存 launchd loop の投稿経路（IG account、投稿方法）は**変えない** — 変えるのは「何を生成するか」だけ。

## やること
1. M-1 の生成パイプラインを skill 化: `~/profitable-claude/skills/video/`（または既存生成 skill 内、実読して自然な方）に「daily-lm-video」生成 script を置く。入力 = 脚本銀行（§9.10 の16行を jsonl 化して同梱: id/pain/moment/punchline/素材ヒント）から1行選択 → M-1 と同じ合成（実素材+whisper 字幕+stock+FFmpeg、$0）→ 9:16 mp4。
2. 行選択 rotation: state jsonl（used 記録）で未使用行を優先。全行消化後は self-improve 用に「伸びた行」優先（M-4 で計測が入るまでは単純 rotation でよい — 空実装の hook だけ置く）。
3. 既存 claude-p loop（launchd 10:15 の life-manager skill）の投稿 step を「slideshow 生成」→「daily-lm-video 生成」に差し替え。IG 投稿部はそのまま流用。
4. 検証: ①生成 script 単体実行で mp4 が出る（ffprobe 実測）②launchd job を `launchctl kickstart` で1回発火 → loop が video を生成し**実 IG 投稿**まで到達（投稿 URL 取得）。IG 投稿は loop の正規経路なので実投稿してよい（Dais 個人 account ではない、loop 専用 account）。
5. spec 更新: §10 の 9b/9c 行のうち今回閉じた分を実測値で更新（9b done 条件 = launchctl 実出力+2日連続なので、今日は「1日目実績」と正直に書く）→ commit+push（anicca-project spec と profitable-claude 両方）。

## 禁止
Dais 個人 SNS への投稿 / 既存 IG 投稿経路・account の変更 / slideshow 資産の削除（残す、使わないだけ）/ secret 出力。

DONE 報告: 生成 mp4 の ffprobe + launchd kickstart 実出力 + 実 IG 投稿 URL + spec commit hash。
