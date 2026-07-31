# 発注: M-3 — TikTok 配信配線（Postiz、M-2 の daily video を二次配信）

正本: /Users/anicca/anicca-project/docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md
必読節: §9.2（TikTok = Postiz、channel id `cmp9txjdp01c8oh0yb6dhlarr`）。前提 = M-2 の daily-lm-video 生成 skill（~/profitable-claude/skills/video/ 側）。
役割: Sol = build+execute+verify+spec 更新+commit+push。質問 = bash ~/.agents/skills/agmsg/scripts/send.sh lm-p0 sol-m3 fable-main '<msg>'。

## やること
1. Postiz API の既存利用実績を repo 内 grep（~/.openclaw / ~/profitable-claude に既存 client があれば流用 — 車輪の再発明禁止）。
2. M-2 の生成 mp4 を Postiz 経由で TikTok channel `cmp9txjdp01c8oh0yb6dhlarr` に投稿する step を loop に追加（IG 投稿の直後、同 payload）。caption には landing への導線 1行（aniccaai.com/life-manager）。
3. 実投稿1本で検証: 実 TikTok 投稿 URL を取得し、ブラウザ相当で公開状態を確認。
4. spec §10 9c 行を実測値で更新 → commit+push。

## 禁止
Dais 個人 account への投稿 / Postiz 以外の TikTok 経路新設 / secret 出力。

DONE 報告: 実 TikTok 投稿 URL + loop 差分の要旨 + spec commit hash。
