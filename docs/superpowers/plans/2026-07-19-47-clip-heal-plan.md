# PLAN #47 CLIP-HEAL (B4) — clip loop の投稿ゼロ恒常化を修理

発注: Fable(planner) → Sol(Codex builder, flow B)。2026-07-19。
前提 recon 済（再調査不要）: aiclipsvault は state に無い retire 済み handle。`clip_pass.sh:129` が bio_step を `--handle aiclipsvault` で hardcode（症状A の正体）。`run.sh:58` は status=="ready" のみ投稿対象だが ready へ昇格させる仕組みが clip loop に無い。`clip_pass.sh` の usable カウンタ ok() は ready|warming のみで warming_day1 を除外（07-18 の provision 無限 timeout の正体）。engine `warmer.py` は day3 golden session 成功時に status="ready" へ昇格させる（capafy は専用 warmup plist で毎日呼んでる）。現 clip accounts: aiclips_world_hq2(warming_day1, instagrapi, 07-17 作成=今日が day3) / aiwealth.pulse(warming, browser, 07-19)。

## Planner 決定（曲げるな）
- 車輪の再発明禁止: 昇格は engine `warmer.py` をそのまま使う（clip 用に新 warmer を書かない）。
- relogin 禁止規律は不変: tier3/pw login の挙動・cooldown に一切触るな。
- aiclipsvault の ~/.cloak file 群は削除禁止（credential 保全）。hardcode だけ外す。
- 投稿対象 = ready のみ（run.sh の既存判定は正しい。緩めるな）。直すのは「ready に到達する道」。

## 要件（MUST）
R1: `clip_pass.sh` BIO step の handle hardcode を廃止 — state file（clip-accounts.json）から active handle を resolve（engine account_state.sh の resolver を source。capafy 側と同じ流儀）。valid session が無ければ今まで通り honest skip。
R2: `clip_daily.sh`（または clip_pass.sh の pass 冒頭）に WARM step 追加 — 全 warming 系 account に対し engine の `warmer.py` を呼ぶ（capafy warmup loop と同じ呼び方を engine から確認して踏襲）。day3 到達 + golden session ok → warmer が status=ready へ昇格（既存挙動）。non-fatal。
R3: `clip_pass.sh` の ok() usable 判定を engine 語彙に統一: status が ready* または warming*（warming_day1 含む）かつ非 poisoned = usable。判定 logic は可能なら account_state.sh の既存関数を使う（新規 regex を書かない）。
R4: status 語彙の SSOT を engine README に1段落追記: warming_day1/warming = 育成中(usable, 投稿不可) / ready = 投稿可 / poisoned = 除外。provision カウンタと投稿選択の使い分けを明記。
R5: テスト: (i) bio_step handle resolve（fixture state file で active handle が返る/空なら skip）(ii) ok() が warming_day1 を usable と数える (iii) relogin 経路に変更が無いこと（poster.py の tier3 発火条件のテストが既存なら流用確認のみ）。PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest + bash -n。実 IG/実 browser 副作用ゼロ。
R6: worktree `/Users/anicca/anicca/.worktrees/clip-heal-47/`（Fable 作成済）。git コマンド禁止（Fable 担当）。

## Done
1. pytest green + bash -n 全 sh PASS（Sol 実行）
2. grep で aiclipsvault hardcode が clip_pass.sh から消滅（コメント/実績例文中は残してよい）
3. agmsg で DONE + pytest 要約 + 変更 file 一覧（絶対 path）
質問: send.sh capafy sol-codex fable-main（宛名に #47 と書け）。
