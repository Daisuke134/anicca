# PLAN #45 ENGINE-BASE (B2) — marketing engine 汎用化の実証と2レーン明文化

発注: Fable(planner) → Sol(Codex builder, flow B)。2026-07-19。
前提 recon 済（再調査不要）: spawn-marketing-loop.sh は `SPAWN_FAKE_LLM=<file>` でLLM無しE2E可・出力は manifests/<slug>.manifest.sh のみ（--register 無しなら副作用ゼロ）。load_manifest.sh required 7変数。MKT_CONTENT_ADAPTER 許容値に slideshow 有り。poster.py は clip_upload のみ = reel 専用。

## Planner 決定（実装で曲げるな）

- **2レーン規律**: earner lane = agent 自己所有 account + instagrapi(poster.py) のみ。human-funded lane = Dais/human 資産（Postiz・Dais の Amazon tag aniccaai-22 等）可。slideshow(earn-affiliate-slideshow) は Amazon tag が Dais 資産なので **human-funded lane**。
- **carousel 投稿系統**: engine の earner lane は instagrapi 一系統を維持（instagrapi↔browser 併用 churn が poison 真因だった）。よって poster.py に album_upload を追加する。browser 系 ig-account-poster への委譲はしない。
- **live 発火なし**: 今日は dry/offline 検証まで。launchctl bootstrap・実投稿・account 作成は範囲外。

## 要件（全部 MUST）

### R1 — README 2レーン章（repo ~/anicca）
`marketing-engine/README.md` の invariants 章直後に `## Funding lanes` を新設:
- earner lane（agent 自己所有 account / poster.py instagrapi / Postiz・human credential 禁止）vs human-funded lane（Dais 製品: reelclaw/larry/honne 等、Postiz 可）
- MKT_CONTENT_ADAPTER × 投稿経路の対応表（faceless-video,clip-cut,slideshow,carousel → instagrapi reel or album）
- slideshow の lane 判定実例1行（Amazon tag = human 資産 → human-funded）

### R2 — poster.py carousel 対応（repo ~/anicca）
- `--images <comma-separated paths>`（2-10枚）を追加し `cl.album_upload` で投稿、成功 URL は `/p/{code}/`
- 既存 `--video`(clip_upload) 経路は不変。--video と --images は排他（両方/どちらも無し → usage error）
- 既存 guard（day<3 login 拒否、relogin 禁止、delay_range[1,3]、ACCOUNT GUARD fail-closed）が album 経路にも同様に効くこと
- テスト: mock client で album_upload 呼び出し検証 + 排他 error + day<3 refuse が album 経路でも発火する negative test。実 IG 接続なし

### R3 — spawn E2E（repo ~/anicca、offline）
- 8行 fixture file を作り `SPAWN_FAKE_LLM=<fixture> spawn-marketing-loop.sh slideshow "<説明>"`（--register 無し）を実行
- 生成された `manifests/slideshow.manifest.sh` が me_load_manifest validate を通ることを確認（MKT_CONTENT_ADAPTER=slideshow、MKT_BIO_LINK は Amazon affiliate landing 前提の placeholder 可）
- manifest 冒頭 comment に `# LANE: human-funded (Amazon tag = Dais asset). LIVE 発火は #30 day3 実証後 + Dais lane 確認後` を明記
- E2E の実行 log（コマンドと出力）を PLAN 横の `2026-07-19-45-engine-base-e2e.md` に貼る

### R4 — workflow
- 編集は worktree `/Users/anicca/anicca/.worktrees/engine-base-45/`（Fable が作成済みのものを使う。無ければ agmsg で報告して待て）
- git コマンド禁止（Fable が commit/merge/push）
- テストは `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest`。実 IG/browser/launchctl 副作用ゼロ

## Done 条件
1. pytest green（album 経路 negative test 含む）を Sol 自身が実行
2. manifests/slideshow.manifest.sh が validate 通過（実行 log 添付）
3. README に Funding lanes 章
4. agmsg で DONE + pytest 要約 + 変更 file 一覧（絶対 path）

質問/完了報告: `~/.agents/skills/agmsg/scripts/send.sh capafy sol-codex fable-main '<msg>'`
