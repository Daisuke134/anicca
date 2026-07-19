# Anicca handover — 2026-07-19 20:53 JST

一行サマリ: Life Manager cloud で LM-28(英語復帰)・LM-29(録音常設)・LM-8(Unipile calendar adapter)・LM-8b(propagation コード)・#12(dev loop D0=実 PR #312 生成)を close。核心(電話が鳴り英/日で双方向会話→AMD→録音)は稼働。**launch までの残り = ①実 call で5機能を1回証明 + ②secret rotate**。Unipile flip は token 死亡で blocked(LM-8c)。

## 今回やったこと（全て commit+push+spec 記録済み）
- **LM-28 ✅**: Dais の call を英語に戻す。`lm_users` の Dais 行(`lm_784ad279…`, +818046270314)を Supabase Management API で `call_language="en"` に PATCH(return=representation で確認)。コード無変更(resolveCallLang が明示値最優先)。
- **LM-29 ✅**: 全 Telnyx 録音を launchd で常設。`ai.anicca.lm-recording-store`(30分毎 StartInterval 1800, RunAtLoad) + wrapper `~/.openclaw/skills/life-manager-video/run-store-recordings.sh`(.env source→store-recordings.py)。`launchctl list` exit0 + out ログ `done: N new, M listed` 実出力確認。main-internal push(secret-guard no leaks)。録音先 `~/.openclaw/state/lm-video/recordings/`。
- **LM-8 ✅**: Unipile calendar transport `lib/transport/calendar-unipile.js`(Sol 実装)。crwl で OpenAPI 実 schema 確認(primary=`is_default`, container=`data`, query=`start`/`end`, `title`→summary/`body`→description/`start.date_time`+`time_zone`)。`LIFE_CAL_TRANSPORT=unipile` opt-in、未設定=composio 現状維持。calendar-unipile.test.js 4/4、全 suite fail 0。dev `d780622c6`。
- **LM-8b ✅(コードのみ)**: 全 getCalendar 消費者11箇所(ask/events/context-graph/late-notice/notify/telegram-reply/travel/telegram-onboard/scheduler)に `gmailAccountId` 配線(builder subagent、dev `f9577546a`、12ファイル、256 pass、後方互換)。token/dsn は index.js が env fallback。
- **#12 dev loop D0 ✅**: skill `~/profitable-claude/skills/life-manager-dev/`(pick-issue.sh/dev-pass.sh/launchd plist/SKILL.md、builder、main `2ee0eb2`)。**live D0 実行 → 無人で issue #11 を nested sonnet が直し実 PR #312 生成**(OPEN、+76/-16、travel autofill 実修正)。detach(nohup&disown)で harness kill を回避して完走。

## 決定事項
- **開発方式 = flowb / subagent 実装**: Fable=plan(patch レベルまで深く) + 最終実測検証、実装は Sol(codex)or builder subagent(sonnet)。Dais 指示「plan very deeply→subagent implements→you verify」。agmsg team `lm`(fable-main↔sol-codex)で双方向質問線 実証済み(Sol が primary判別/範囲/dialect を質問→Fable 裁定)。
- **cloud=SSOT 確定**: `anicca-products/apps/life-call` が本番の唯一の正本。Railway deploy 元も anicca-products のまま。
- **#10 repo 収斂 = DROP**(Dais 決定): `Daisuke134/life-manager` repo は別物(古い OSS skill 07-11、issue tracker としてのみ残す)。放置。cloud を移す churn 不要。
- **LM-8b flip 禁止(現時点)**: Unipile token 死亡のため flip すると Dais calendar 空返し=破壊的。composio 現状維持。

## 捨てた選択肢と理由
- LM-8 で Dais の call を ja 固定 → 却下。Dais は英語希望(LM-28 で en に戻した)。langForPhone(+81→ja)はデフォルトのまま、個別 user の明示希望が locale 推定に勝つ。
- #10 repo 収斂(life-manager repo へ移動+Railway 切替) → DROP。cloud が anicca-products で動いてるので churn。
- LM-8b を「adapter 書けた」で完了扱い → 却下。実 creds で live API を叩くまで activation ではない(下記ハマり参照)。

## ハマりどころ
- **★Unipile token が prod で死んでいる(最重要)★**: LM-8b flip 直前に実測 → `UNIPILE_TOKEN`(値 `[/e4xqi…LNQ=]` len53)が **mail・calendar 両方で 401 invalid/missing_credentials**(api35.unipile.com)。bare `/api/v1/accounts` でも 401 = token 自体が死んでる(scope でも DSN でもない)。→ **Unipile mail も silently 死んでいた**(mail-unipile.js は fail-soft で []/false)。search-before-ask の inbox 読み・gmail 連携が機能停止していた。**LM-8c**(dashboard で API key 再発行→env 更新)が必要。Dais の gmail_account_id=`98Lv6EhZS1q11UqXeiKlRQ` は接続済み。
- **background task の kill**: `run_in_background: true` の Bash は harness の時間上限(~10分)で長い nested claude(900s)が killed される。→ 長い loop は `nohup … & disown`(真の detach)で回す(他ループと同じパターン)。dev-pass.sh はこれで完走。
- **codex sandbox の git lock**: Sol(codex `--sandbox workspace-write`)は `.git/worktrees/*/index.lock` を作れず commit 不可 + repo 外(~/.openclaw, ~/Library/LaunchAgents)に書けない。→ Fable が commit/push を代行、repo 外ファイル(plist 等)も Fable が作る。
- **fablize hook の "tool failure" 誤検知**: `ls` の no-such-file や grep 成功でも「tool failure」が出る。実 tool_result を見て実障害か判定する(ほぼ誤検知)。
- **「court」出力バグ**: tool 呼び出し直前に幻覚トークン混入(HARD RULE 0.34)。今回は全ターン tool ブロック直前をクリーンに保ち再発ゼロ。

## 学び（一般法則）
- **「adapter が書けた/配線した」で activation 完了と言うな。実 creds で live API が 200 返すまでが activation。** 実例: LM-8b で Unipile token が 401 と実測して分かった → flip 前に Dais の calendar 破壊を防げた。code/DB だけ見ていたら壊していた。
- **fix の方向を user の希望で確認してから data を書き換える**(locale 推定 < 個別 user の明示希望)。
- **長い無人 loop は nohup&disown で detach**(harness の background 上限で死ぬ)。

## 次にやること（この順、索引。goal は下の1つだけ）
| 順 | # | 内容 | done |
|---|---|---|---|
| 1 | 実証束 | LM-5/23/3/6/7 を実 call 1本で証明(★下の /goal★) | 短経路イベントで T-10/T-5 鳴る→録音で英語確認→T-0「出た?」→「まだ」→遅刻メール実受信 |
| 2 | #12 締め | PR #312 の TG 着信確認 + `launchctl load` で plist 常設化 | launchctl list に life-manager-dev + TG 着信スクショ/ログ |
| 3 | LM-8c | Unipile token 再発行(CloakBrowser で dashboard.unipile.com) | mail inbox read が 200 + calendar list が返る実測 |
| 4 | LM-8b flip | LM-8c 後: prod `LIFE_CAL_TRANSPORT=unipile` + 実 gcal E2E | Unipile で list/create/patch 実測 + Composio calendar 課金停止 |
| 5 | #4 LM-21 | 13 secret rotate(GEMINI/TELNYX 漏洩優先) | /health 200 + TG echo + dial preflight ok。**公開前に必須** |

## 関連ファイル
- 正本 spec: `docs/superpowers/specs/2026-07-17-life-manager-cloud-alignment-and-dev-loop.md`(§5c-8 進捗マトリクス、§5c-10〜13 が最新実測ログ)
- goal done 12条件: `docs/superpowers/specs/2026-07-17-life-manager-p0p1-goal.md`
- 前回 handover: `.claude/handovers/2026-07-19_1010_lm-lang-english-revert.md`
- worktree: `.worktrees/lm-p0`(team lm)。cloud コード = `apps/life-call/`
- dev loop skill: `~/profitable-claude/skills/life-manager-dev/`(main 2ee0eb2)、live ログ `~/.openclaw/logs/lm-dev-d0-live.log`
- 録音取得/whisper: `~/.openclaw/skills/life-manager-video/store-recordings.py`(launchd 常設済) / `whisper <mp3> --language Japanese --model small`
- Unipile 実 schema: `https://developer.unipile.com/llms.txt`(各 reference の .md 版に OpenAPI schema)

## 環境メモ
- Supabase data-fix: `railway run -s life-call bash -c 'curl ... $SUPABASE_URL/rest/v1/lm_users?uid=eq.<uid> -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" ...'`(secret を stdout に出さない)
- prod build 確認: `curl -sm8 https://life-call-production.up.railway.app/health`
- staging deploy: `railway up --path-as-root /Users/anicca/anicca-project/.worktrees/lm-p0 -e staging -s life-call-staging --ci`
- Sol 起動: `codex exec -m gpt-5.6-sol --sandbox workspace-write --skip-git-repo-check "<task>" < /dev/null`(commit は Fable 代行)。builder subagent: Agent tool `subagent_type: builder, model: sonnet`(repo 内なら sandbox 制限なし)
- agmsg: `bash ~/.agents/skills/agmsg/scripts/send.sh lm <from> <to> "<msg>"`(4引数)、inbox `inbox.sh lm fable-main`

## ★次セッションの /goal★
/goal Life Manager cloud の5機能(LM-5 遅刻メール / LM-23 TG「出た?」ボタン往復 / LM-3 場所検索 / LM-6 onboarding / LM-7 コスト台帳)を、家の近所(location=home 徒歩5分)・start≈now+15min の短経路テストイベント1個で実 call E2E 実証して close する。

Objective: 1本の短経路テストイベントで実 call を発火させ、その通話の Telnyx 録音を whisper で文字起こしして AI が英語で発話していることを確認し、T-5 に出た後 T-0「出た?」inline ボタンが実 TG に届き「まだ」タップで遅刻メールが実受信されるまでを、実 side-effect の観測(録音・実 TG・実メール message_id)で証明する。併せて #12 dev loop の PR #312 に TG 報告が届いたか確認し `launchctl load` で常設化する。

Scope: apps/life-call は prod 稼働(build=lm27-voicemail-v1、call_language=en、録音 launchd 常設済み)。コード変更が必要になった場合のみ worktree .worktrees/lm-p0 で feature branch を切り flowb(Sol/builder 実装)で直す。テストイベントは gog calendar で作成/削除。録音は store-recordings.py で取得。正本 spec = docs/superpowers/specs/2026-07-17-life-manager-cloud-alignment-and-dev-loop.md(§5c-8 マトリクス)。Unipile flip(LM-8b)は token 死亡(LM-8c)未解決なので触らない。

Constraints:
- 開発方式 = GLVS（Goal → Loop → Verify → State）。会話でなく file(spec §5c-N)に進捗を書く
- 実装は Sonnet/Sol subagent / spec を実装側で曲げない / VCSDD token 上限厳守
- spawn 前後に TaskList → TaskCreate → TaskStop
- 実測せず断定しない（既定の姿勢 = 「私は間違っている」。断定前に外部検索 + 実測）
- 車輪の再発明禁止（作る前に web+gh で既存実装を探して copy+tweak）
- 編集ごとに commit+push（確認を求めない）。push は grep で remote 到達を明示確認
- ¥0 は ¥0 と報告する。盛らない
- ★実装は VCSDD の実コマンドを phase 順に呼ぶ。SPEC 本文への手書き追記は進捗ではない★
    /vcsdd:vcsdd-init → vcsdd-spec → vcsdd-spec-review → /vcsdd:vcsdd-tdd(RED)
    → vcsdd-impl(GREEN) → vcsdd-adversary → vcsdd-harden → vcsdd-converge
  `.vcsdd/features/<name>/state.json` の phase が進んでいないものは「やった」と言わない
- 規模に応じ mode: lean / strict を選んでよいが、★フェーズ自体は飛ばさない★
- adversary は毎 iteration fresh spawn（model: sonnet 明示）。blocking 1件でも次フェーズ禁止
- 最後に reality-verifier(=Fable 自身)が実 call 録音 whisper + 実 TG + 実メールで source of truth を確認するまで完了と言わない
- worktree-per-task（`git worktree add .worktrees/<task> -b feature/<task>`）
- ★実 call の録音の中身(whisper)を聞くまで close しない。DB の answered_at だけで「起きた」と判定するな★
- ★long-running な無人 loop は nohup & disown で detach（run_in_background の harness 上限で kill される）★
- ★tool 呼び出しブロックの直前に散文・余計なトークン(「court」等)を一切置かない(HARD RULE 0.34)★

Done when:
- テストイベントの lm_wake_log に T-10/T-5 行が実在（Supabase REST で確認）
- その call の Telnyx 録音を whisper で文字起こし → 英語発話（日本語なら FAIL、call_language=en 未反映）
- T-5 answered 後、実 TG に「出た?」[出た][まだ]ボタン着信（スクショ or callback row）
- 「まだ」タップ or fallback → keiodaisuke+lmtest@gmail.com に遅刻メール実受信（gog gmail search で message_id 確認）
- #12: PR #312 への TG 報告到達を確認 + `launchctl load ~/Library/LaunchAgents/ai.anicca.life-manager-dev.plist` → `launchctl list | grep life-manager-dev` で常設確認
- 上記を spec §5c に実測値で記録 + commit+push

Stop if:
- 同一フェーズ3回 FAIL で止めて handover（例: 3回鳴らしても英語にならない → resolveCallLang/call_language の source を再 RCA）
- 破壊的・不可逆操作が必要（schema 破壊 migration / prod 課金経路変更 / 承認外 broadcast / Unipile flip）
- 週次 token 残 10%未満

## 新セッション開始プロンプト
まず `/context` を測れ。次に `docs/superpowers/specs/2026-07-17-life-manager-cloud-alignment-and-dev-loop.md` の §5c-8(進捗マトリクス)と §5c-10〜13(最新実測)を読み、`.claude/handovers/2026-07-19_2053_lm-launch-remaining.md` の「次にやること」表を TaskList に反映。prod build を `curl -sm8 https://life-call-production.up.railway.app/health` で確認してから、上の /goal を実行して LM-5/23/3/6/7 の実 call E2E を短経路イベントで close し、#12 を launchctl load で常設化する。開発は flowb/subagent(Sol or builder 実装、Fable が実 call 録音 whisper + 実 TG + 実メールで最終検証)。Unipile flip(LM-8b)は token 死亡(LM-8c)未解決なので触らない。★tool 呼び出しブロックの直前に「court」等の余計なトークンを一切置くな(HARD RULE 0.34)★。
