# Anicca handover — 2026-07-19 10:10 JST

一行サマリ: Life Manager cloud、LM-26(日本語 call 配線) を実 call 録音で日本語実証し close。ただし Dais は**英語希望**（"I wanted it in English"）。次の最優先 = **LM-28: Dais の call_language を ja→en に戻す**。以降 #4 rotate / #8b Unipile / #10 repo 収斂 / #12 dev loop を flowb で1本ずつ。全 call/voice セッションの録音保存を稼働させる要望あり。

## 今回やったこと
- **LM-26**（call 日本語化）: ✅ **close**。真因 = Dais の `lm_users.call_language="en"` 固定（+81 なのに en）。`resolveCallLang`（call_language 優先、無ければ langForPhone(+81→ja)）を prod 投入 + Dais の data を ja に data-fix。短経路イベント（コンビニ@新宿御苑、T-10 が 01:13 発火）で実 call → **録音を whisper で日本語発話を実証**（DB の answered_at だけでなく録音の中身まで確認）。
- **LM-27**（voicemail→answered 誤判定）: ✅ close（前回）。AMD + 署名 webhook、無署名 POST→403 を staging+prod 実測。prod build=lm27-voicemail-v1。

## 決定事項
- **開発方式 = flowb 確定**: Fable=plan(PLAN.md)+最終実測（npm test 再実行 + 実 call 録音 whisper + DB/curl）、Sol(codex `gpt-5.6-sol`)=実装、fresh Sol(`--sandbox read-only`)=review。direct セッションで Luna(proxy) 不可のため flowa でなく flowb。
- **★Dais は自分の call を英語で受けたい★**（verbatim: "it was in Japanese... I wanted it in English though. I wanted in English but still, Japanese works fine too... it's working, so no worries"）。→ 日本語配線自体は正しく動く（LM-26 の実装は残す）が、**Dais の user 行の call_language は en が正**。今回 ja に data-fix したのは方向が逆だった。
- **全 call/voice セッションを録音保存せよ**（Dais: "if you just record all my voice/call sessions... you would be able to say if it's working... just hear the recording who would know"）。→ store-recordings の定期実行を確認/常設する。
- **#11 TikTok bio = drop**（marketing は IG launchd slideshow で回っており TikTok 非アクティブ、building 集中）。
- 「answered_at が入った=出た」で close するのは誤り。実 side-effect（録音の中身）を whisper で聞くまで close しない。

## 捨てた選択肢と理由
- LM-26 を data 修正だけで済ます → 却下。新規 +81 user が未設定でも日本語になるよう resolveCallLang を prod に入れた（配線は残す）。
- LM-27 を media-start の inbound audio 有無で近似検知 → 却下。voicemail も音声を流すので区別不可。Telnyx AMD が正攻法。
- Dais の call_language を ja のままにする → 却下。Dais は英語希望なので en に戻す（LM-28）。

## ハマりどころ
- **staging deploy が FAILED**: railpack が "directory apps/life-call does not exist"。正解 = `railway up --path-as-root <repo_root> -e staging -s life-call-staging --ci`（archive root を repo root に）。watchPatterns が CLI up を skip させるので GraphQL `serviceInstanceUpdate` で watchPatterns=[] に変更済み。
- **push が lefthook 出力に埋もれて未達だったことがある**: push 結果を `grep -iE "branch|->"` で明示確認。メイン repo に別セッション(clip-rewards)の未 commit ファイル混在 → `git pull --rebase --autostash` で安全に push。
- **「court」連発は俺の出力バグ**（tool call 前に幻覚トークン混入、HARD RULE 0.34）。tool 呼び出しブロックの直前に散文・余計な文字を一切置かない。この handover でも冒頭に court を連発した = 同じ違反。次セッションは tool ブロック直前を必ずクリーンに保つ。

## 学び（一般法則）
- **DB の状態フラグ(answered_at)だけで「起きた」と判定するな。実 side-effect の中身(録音音声)を観測するまで close しない。** 実例: answered_at が入っていたが録音を whisper したら voicemail 転送 + 英語発話だった(2026-07-18)。
- **fix の「方向」を user の希望で確認してから data を書き換えろ。** 実例: LM-26 で「+81 なのに en は誤り」と決めつけて ja に変えたが、Dais は英語希望だった。langForPhone のロジック（+81→ja）は正しいが、**個別 user の明示希望が locale 推定に勝つ**。

## 次にやること（flowb で1本ずつ、この順）
| 順 | Task# | 内容 | done 条件 |
|---|---|---|---|
| 1 | LM-28 | Dais の call_language を ja→en に戻す | Supabase REST で `lm_users` の Dais 行 call_language="en" 確認 + 実 call の録音 whisper が**英語**発話。langForPhone は +81→ja のままだが、明示設定 en が優先されることを resolveCallLang で確認（コード変更不要のはず、data-fix のみ） |
| 2 | 録音常設 | 全 call/voice 録音保存の定期実行を確認/常設 | store-recordings が cron/launchd で回っている（`launchctl list` or gateway cron で確認）。無ければ設置し、直近 call の mp3 が取得できることを実測 |
| 3 | #4 LM-21 | 13 secret rotate | GEMINI/TELNYX 漏洩済み優先。runbook HIGH-CAUTION 4点(Netlify 共有・TG setWebhook 再登録・LM_UID_SECRET 403・Stripe endpoint 別secret)を先に。/health 200 + TG echo + dial preflight ok。prod 数分ダウン窓で |
| 4 | #8b LM-8 | Unipile calendar 置換 | U17(Unipile calendar API 機能十分性)を context7/crwl で検証 → 十分なら Composio 置換、Gmail+Calendar 1アカウント化で二重払い解消。実 gcal で list/create/patch |
| 5 | #10 LM-20 | repo 収斂 | anicca-products/apps/life-call → Daisuke134/life-manager へ、Railway deploy 元切替、/health 200 + 実 call 1本 |
| 6 | #12 LM-1 | dev loop D0 | `~/profitable-claude/skills/life-manager-dev/`(launchd, sonnet) が無人で issue 1件→fix→実 PR + TG 報告(merge しない) |

## 関連ファイル
- 正本 spec: `docs/superpowers/specs/2026-07-17-life-manager-cloud-alignment-and-dev-loop.md`（§5c-8 に goal 12条件 進捗マトリクス、§5c-9 が実測ログ）
- goal done 12条件: `docs/superpowers/specs/2026-07-17-life-manager-p0p1-goal.md`
- 前回 handover: `.claude/handovers/2026-07-19_0029_lm-wave2-flowb.md`
- worktree: `.worktrees/lm-p0`（team lm、Fable=fable-main / Sol=sol-codex）
- 言語配線: `.worktrees/lm-p0/apps/life-call/lib/call-language.js`（resolveCallLang / langForPhone(+81→ja)）、server.js:242 が u.call_language を source
- 録音取得: `python3 ~/.openclaw/skills/life-manager-video/store-recordings.py`（TELNYX_API_KEY 要、Telnyx completed まで数分ラグ）。whisper: `whisper <mp3> --language Japanese --model small --output_format txt`

## 環境メモ
- staging deploy: `railway up --path-as-root /Users/anicca/anicca-project/.worktrees/lm-p0 -e staging -s life-call-staging --ci` → `bash scripts/lm-staging-smoke.sh`
- flowb 起動: `codex exec -m gpt-5.6-sol --sandbox workspace-write --skip-git-repo-check "<PLAN 追記N を実装>" < /dev/null`（stdin 必須）。DONE は自己申告なので npm test 独立再実行 + 該当ファイル Read で裏取る。review = fresh codex（`--sandbox read-only`）で「PLAN の不変条件を破れ」。
- prod build 確認: `curl -sm8 https://life-call-production.up.railway.app/health`（=lm27-voicemail-v1 のはず）
- Supabase data-fix: Management API `POST /v1/projects/{ref}/database/query`（SUPABASE_ACCESS_TOKEN）。UPDATE は WHERE で Dais 1行に限定

## ★次セッションの /goal★
/goal Life Manager cloud の Dais 宛 call を英語に戻し(LM-28)、全 call セッションの録音保存を常設して、実 call 1本の録音を whisper で英語発話を実証して close する。

Objective: Dais の lm_users 行の call_language を "en" に戻し、実 call の Telnyx 録音を whisper で文字起こしして AI が**英語**で発話していることを確認する。併せて全 call/voice セッションの録音が定期取得される状態（cron/launchd）を実測で確立する。

Scope: apps/life-call は既に lm27-voicemail-v1 が prod 稼働、resolveCallLang 配線済み。call_language は data-fix（Supabase Management API で Dais 1行を en に UPDATE）で足りるはず。コード変更が必要になった場合のみ worktree .worktrees/lm-p0 で feature branch を切り flowb(Sol 実装)で直す。テストイベントは gog calendar で作成/削除。録音は store-recordings.py で取得。正本 spec = docs/superpowers/specs/2026-07-17-life-manager-cloud-alignment-and-dev-loop.md(§5c-8 マトリクス)。

Constraints:
- 開発方式 = GLVS（Goal → Loop → Verify → State）。会話でなく file(spec §5c-N)に進捗を書く
- 開発方式 = flowb: Fable=plan+最終実測、Sol(codex)=実装、fresh Sol=review。spec を実装側で曲げない / VCSDD token 上限厳守
- ★実装は VCSDD の実コマンドを phase 順に呼ぶ。SPEC 本文への手書き追記は進捗ではない★
    /vcsdd:vcsdd-init → vcsdd-spec → vcsdd-spec-review → /vcsdd:vcsdd-tdd(RED)
    → vcsdd-impl(GREEN) → vcsdd-adversary → vcsdd-harden → vcsdd-converge
  `.vcsdd/features/<name>/state.json` の phase が進んでいないものは「やった」と言わない
- 規模に応じ mode: lean / strict を選んでよいが、★フェーズ自体は飛ばさない★
- adversary は毎 iteration fresh spawn（fresh codex read-only）。blocking 1件でも次フェーズ禁止
- 最後に reality-verifier(=Fable 自身)が実 call 録音 whisper + launchctl list で source of truth を確認するまで完了と言わない
- worktree-per-task（`git worktree add .worktrees/<task> -b feature/<task>`）
- spawn 前後に TaskList → TaskCreate → TaskStop
- 実測せず断定しない（既定の姿勢 =「私は間違っている」。断定前に外部検索 + 実測）。★DB の状態フラグだけで「起きた」と判定するな、録音の中身を聞くまで close しない★
- ★fix の方向を user の希望で確認してから data を書き換える（+81→ja の locale 推定より個別 user の明示希望が勝つ）★
- 車輪の再発明禁止（作る前に web+gh で既存実装を探して copy+tweak）
- 編集ごとに commit+push（確認を求めない）。push は grep で remote 到達を明示確認
- ¥0 は ¥0 と報告する。盛らない

Done when:
- Supabase REST で `lm_users` の Dais 行 call_language="en" を確認
- テストイベントで実 call → その call の Telnyx 録音を whisper で文字起こし → **英語**発話（日本語なら FAIL、LM-28 未達）
- store-recordings が定期実行される状態（`launchctl list | grep -i recording` or gateway cron に entry）+ 直近 call の mp3 が実取得できる
- 上記を spec §5c に実測値で記録 + commit+push

Stop if:
- 同一フェーズ3回 FAIL で止めて handover（例: 3回鳴らしても英語にならない → resolveCallLang/call_language の source を再 RCA）
- 破壊的・不可逆操作が必要（schema 破壊 migration / prod 課金経路変更 / 承認外 broadcast）
- 週次 token 残 10%未満

## 新セッション開始プロンプト
まず `/context` を測れ。次に `docs/superpowers/specs/2026-07-17-life-manager-cloud-alignment-and-dev-loop.md` の §5c-8(進捗マトリクス)と §5c-9 を読み、`.claude/handovers/2026-07-19_1010_lm-lang-english-revert.md` の「次にやること」表を TaskList に反映。prod build を `curl -sm8 https://life-call-production.up.railway.app/health`(=lm27-voicemail-v1 のはず)で確認してから、上の /goal を実行して LM-28(英語復帰)と録音常設を close する。開発は flowb(Sol 実装、fresh Sol review、Fable が実 call 録音 whisper で最終検証)。★tool 呼び出しブロックの直前に散文・余計なトークンを一切置くな(HARD RULE 0.34、前セッションで「court」連発の違反あり)★。
