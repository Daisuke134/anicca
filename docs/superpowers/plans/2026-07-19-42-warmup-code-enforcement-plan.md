# PLAN #42 CREATE-FIX — IG warmup を recipe 通り code で強制する

発注: Fable(planner) → Sol(Codex builder, flow B)。2026-07-19。
正本 recipe: `/Users/anicca/anicca-project/docs/reference/ig-account-warmup-recipe-2026.md`
spec: `/Users/anicca/anicca-project/docs/superpowers/specs/2026-07-17-capafy-10k-mrr-two-loop-spec.md` §12

## 背景（実測済の前提。再調査不要）

@useclaudeskills が poison 死（ChallengeRequired）。真因3つ:
1. 共有 CloakBrowser main context（生 :9222）へ login した（device 汚染）
2. 誰も follow せず following=0 + 空プロフィール（bot signature）
3. day1 に instagrapi login（fresh device の早期 API login = challenge trigger）

現状 code の事実:
- `~/anicca/skills/earn/marketing-engine/warmer.py` — PROMOTE_DAY=3、golden login 1回→dump_settings、relogin 拒否は**既にある**
- `~/.agents/skills/ig-account-warmer/scripts/warm.py` — passive のみ（reels/scrolls/stories/profiles の day別 CAPS、`--dry` あり）。follow/like は**無い**
- `~/.agents/skills/ig-account-warmer/scripts/warm_iso.py` — isolated context（専用 port/fingerprint、cdp.py 経由）変種。`--dry` 無し
- `~/.cloak/clip-accounts-capafy.json` — 現 account の `port: 9222` = 生 main context（真因#1 の記録）

## 要件（全部 MUST。任意/推奨なし）

### R1 — engagement step（repo `~/.agents`）
warm 系 script に day-gated follow/like/comment step を追加する。
- cap（recipe 表の保守側）: day1 = follow 0 / like 0 / comment 0（**0。1-3 可説は採らない**）、day2 = follow 3-5 / like 5-10 / comment 0-2、day3 = follow 5-10 / like 10-20 / comment 3-5、day4+ = follow 5-10 / like 15-25 / comment 3-5
- action 間 human-like ランダム遅延（jitter）。cap 内で乱数選択。
- **成功時のみ計数**（UI 状態変化を確認できた follow/like だけ数える。既存 warm.py の「video.currentTime で実再生検証」と同思想）
- brittle selector 禁止: 壊れたら黙って skip でなく plan に unfulfilled を残して報告
- 実行 context は **isolated**（warm_iso 系の専用 port/fingerprint 経路）。共有 :9222 main での engagement は不可
- `warm.py --dry` の plan JSON に day別 follow/like/comment cap を含める。day1 の dry 出力は follow=0
- 配置（warm.py 本体か共有 module か warm_iso か）は Builder 裁量。ただし capafy warmup loop から呼ばれる経路で day-gate が必ず効くこと

### R2 — provision の既定 = isolated context（repo `~/anicca`）
- `marketing-engine/provision_prompt.sh` の account 作成・login 経路を isolated context（専用 port/fingerprint lease）既定にする
- **code guard**: 生 :9222 main context への IG signup/login を検知したら refuse（明確な error message）。prompt 文言でなく code で拒否
- account state json（clip-accounts-*.json）に isolated port / context id を記録する形へ（既存 field を壊さない）

### R3 — day<3 instagrapi login 禁止 gate（repo `~/anicca`）
- `warmer.py` の既存 gate（PROMOTE_DAY=3）を検証し、**全 instagrapi login 経路**（provision 含む）で warming_day<3 → refuse を保証
- login は生涯1回 → dump_settings → 以後 load_settings のみ（既存挙動を維持）。`delay_range=[1,3]` を client に設定
- poster.py の session 利用経路が relogin を誘発しないことを確認（するなら塞ぐ）

### R4 — テスト（gate は negative test）
- `python3 -m pytest` で green（**uvx 禁止。sandbox は PyPI DNS 不可**）
- negative tests 必須: ①day1 に follow 実行要求 → refuse ②warming_day=1 で instagrapi login → refuse ③port=9222 main への login → refuse ④day2 follow cap 超過要求 → cap に clamp
- テストは実 IG / 実 browser に触らない（cdp・instagrapi は stub/mock）。実 side-effect ゼロ

### R5 — workflow
- repo ごとに worktree: `~/.agents` → `.worktrees/create-fix-42`、`~/anicca` → `.worktrees/create-fix-42`
- 意味のある編集ごとに commit。完了時 trunk へ merge し **両 repo push**（~/anicca は self-update が未 commit を巻き戻すので必ず commit）
- `~/.cloak/` の実 state 値・secret は変更しない。live IG action は実行しない

### R6 — 壊さないこと
既存 passive warm caps / same-day idempotency / off-hours skip / manifests(capafy,clip) / poster.py の tier1 投稿経路 / warmer.py の golden-session 挙動。

## Done 条件（全部満たすまで DONE と言わない）

1. `python3 ~/.agents/skills/ig-account-warmer/scripts/warm.py --dry` が day別 follow/like cap 入り plan を出力し、day1 は follow=0
2. `grep` で warm 系に follow/like step、provision/warmer に day<3 login gate が存在
3. `python3 -m pytest` green（negative tests ①-④ 含む）を Sol 自身が実行し、結果を agmsg で報告
4. 両 repo とも commit + push 済（hash を報告）

## 質問経路

曖昧・矛盾を見つけたら実装で曲げず、agmsg で fable-main に質問:
`~/.agents/skills/agmsg/scripts/send.sh capafy sol-codex fable-main '<質問>'`
回答待ち: `~/.agents/skills/agmsg/scripts/inbox.sh capafy sol-codex`
完了時も同経路で DONE + 証拠（コマンド出力要約 + commit hash）を送る。
