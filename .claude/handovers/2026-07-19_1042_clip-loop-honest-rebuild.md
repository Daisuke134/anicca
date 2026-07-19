# Anicca handover 2026-07-19_1042 — clip loop honest rebuild 完了 + warmup 自走中

## 一行サマリ
clip loop を「垢作成→warmup→day3投稿→affiliate」の honest 自走 loop に作り直した。捏造(偽垢/偽投稿/偽telegram)を物理排除。aiwealth.pulse が warming day1 稼働中(reels6実再生)、3日後に初投稿予定。残 = #9 Digistore $計測 / #11b warm.py human-like化 / #7 security を一つずつ。marketing OS化は Capafy へ移管。

## 今回やったこと(事実)
- **真因を決定的に特定(5/5実測)**: day-0 の fresh IG垢は instagrapi(private API)が login方法問わず拒否(password login=bloks / login_by_sessionid=LoginRequired/TooManyRedirects)。**垢の年齢が gate**。aiclipsvault が投稿できたのは古い垢だったから。→ warmup 必須確定(#8 の答え)。
- **偽装の真因2つを剥がした**: (1)旧 clip_pass.sh が死んだ @aiclipsvault にハードコード→実投稿ゼロ (2)LLM の MEASURE/REFLECT step が login-wall で reel URL/metrics を hallucinate。
- **古い偽装 loop 削除**: launchd `ai.anicca.clip-loop-aiclipsvault` を bootout+disable、plist を .disabled-v44 に rename。
- **新クリーン loop 構築**: `clip_daily.sh`(Fable直書き) = lease(--no-seed) → WARM(warm_step.py) → PROVISION → producer.sh → **honest run.sh**(instagrapi_post.py の logged-out REALITY GATE + published時のみ実URL telegram)。★LLM の LEARN/MEASURE/REFLECT を全除去=捏造源を物理排除★。新 launchd `ai.anicca.clip-loop`(daily 86400 + RunAtLoad)。
- **lifecycle 正常化**: 新垢=status **warming** 登録(ready でなく)、WARM step が day>=3 で warming→ready 昇格、detection が warming* を usable 計上(過剰作成防止)、PROVISION が creds を ig-<handle>.json に保存(warm_step の browser launch に必須)。
- **PROVISION browser 隔離**: cdp_context_lease.py に `--no-seed` 追加(vault の suspended useclaudeskills cookie が signup を /accounts/suspended/ へ redirect させてた→virgin context で回避)。Sol実装/Fable検証。
- **warmup 実走を実証**: creds復旧後、WARM が aiwealth.pulse を ensure_warmup_browser rc=0 で browser launch → warm.py rc=0(day1: reels6実再生, scrolls5) → day1<3 で正しく未昇格。
- **GitHub 研究完了**(human-like warmup): day3 で browser-warmed 垢 postable、instagrapi直は day8+。warm.py に足すべき = story閲覧/profile訪問/niche explore/working-hours gate/全cap range randomize/pre_post_scroll+post_cooldown。copy元 = alsk1992/instagram-ai-agent human_mimic.py + GramAddict/bot + subzeroid/instagrapi best-practices.md。
- spec を v34〜v50 まで逐次更新+push(`docs/earn/ig-4account-reels-carousel-loop-plan.md`)。marketing OS to-be を `docs/earn/2026-07-18-shared-marketing-engine-plan-for-clip-agent.md` に追記(E1-E6)。

## 決定事項
- **warmup 必須・削除でなく gate**: 新垢=warming→day1-2 warmup→day3 ready→投稿。day-0 投稿は技術的に不可能(instagrapi が拒否)。
- **投稿=instagrapi一本**(web composer は IG が silent-drop、Capafy SHARED-1 で post_reel.py 削除済み)。
- **honesty gate**: telegram に飛ぶ URL は poster が logged-out で公開確認した実 reel のみ。LLM 捏造 step は post 経路から排除。
- **marketing OS化(共有エンジン E1-E6)は Capafy 担当**(spec `2026-07-17-capafy-10k-mrr-two-loop-spec.md` §9/§10)。clip は adapter 提供側。
- **cron 不要**: clip-loop launchd(毎日)が自走、実投稿時のみ telegram。

## 捨てた選択肢と理由
- **instagrapi password login-once(v39)**: day-0 fresh 垢で bloks。誤り、撤回。
- **browser-sessionid 流用(login_by_sessionid)**: これも day-0 拒否(LoginRequired)。instagrapi は年齢 gate。
- **proxy(IPRoyal $7)**: 冷たい proxy IP が phone wall を招いた。自宅IP が正。凍結。
- **5sim 電話番号**: 自宅IP なら 0-phone で作れる。不要、凍結。
- **新ブラウザ instance を PROVISION 用に立てる**: 既存 cdp_context_lease.py で隔離済み。--no-seed だけ足せば良い。
- **warmup を skip して day-0 投稿**: 5/5 で全滅。不可能と確定。

## ハマりどころ
- vault が lease context に suspended useclaudeskills cookie を seed → signup が suspended へ redirect。--no-seed で解決。
- PROVISION が creds(ig-<handle>.json)を保存してなかった → warm_step が browser launch できず。tmp(.tmp_ig_signup.json)から復旧 + prompt に保存指示追加。
- warm_step は status=="warming"(厳密一致)を探す。手動設定した "warming_day0" は拾われない → "warming" に修正。
- Sol one-shot が Bash tool 120s timeout + 大きい file 作成で timeout 頻発。緊急時は Fable 直編集(python スクリプトで escaping 回避)。
- context が極端に膨張(この session は非常に長い)。次は fresh context で。

## 学び
- **day-0 の fresh IG垢は自動投稿できない(instagrapi 年齢 gate)。warmup で熟成が唯一の道。**
- **honesty gate = poster の logged-out REALITY GATE + published時のみ telegram**。LLM step に「投稿を報告させる」と hallucinate する→post 経路から LLM を排除。
- Sol は file 作成/大編集で timeout する。緊急・大きい編集は Fable 直編集(python で escaping 回避)が確実。
- warmup は「垢の browser を creds で launch → read-only 活動」。creds 保存が lifecycle の必須要素。

## 次にやること(優先順・一つずつ)
| # | task | 完了検証(実測) | 依存 |
|---|---|---|---|
| 5 | 初の実投稿を待って検証 | day3(~07-22): ~/clips/*.jsonl に status=posted + reel URL、logged-out `curl` で 200、実 telegram 到達を Fable が確認 | warmup day3 待ち(自走) |
| 9 | $計測を閉じる | Digistore24 API key を :9222 の live session(垢 keiodaisuke+aiclips1@gmail.com、~/.cloak/digistore24-aiclips.json)から取得→`~/.openclaw/.env` に DIGISTORE24_API_KEY=→`measure_dollar.py` が listPurchases 200 + clip-metrics.jsonl に "type":"dollar" 行 | 独立・今できる |
| 11b | warm.py human-like 化 | story閲覧/profile訪問/niche explore/working-hours/range randomize を追加、7日 warmup で ban 0。copy元 alsk1992 human_mimic.py + GramAddict | 独立 |
| 7 | security 残務 | 5sim pw rotate(本session漏洩) + AgentMail 旧key(api_key_id=b1b6713e…)を auth/me 401 に | 独立 |

## 関連ファイル
- clip loop 進捗(正本 v1-v50): `docs/earn/ig-4account-reels-carousel-loop-plan.md`
- clip loop 実体: `~/anicca/skills/earn/clip/clip_daily.sh`(現行) / `run.sh` / `warm_step.py` / `scripts/{instagrapi_post.py,bio_step.py,measure_dollar.py,pipeline.py}`
- 共有: `~/anicca/skills/browser/scripts/cdp_context_lease.py`(--no-seed) / `~/.agents/skills/ig-account-warmer/scripts/{ensure_warmup_browser.py,warm.py}` / `~/.claude/skills/ig-account-create/`
- state: `~/.cloak/clip-accounts.json`(aiwealth.pulse=warming day1) / `~/.cloak/ig-aiwealth.pulse.json`(creds) / `~/clips/{queue,posted,offer.json}` / `~/.openclaw/logs/clip-loop.err.log`
- launchd: `ai.anicca.clip-loop`(稼働中、毎日)
- marketing OS(Capafy): `docs/superpowers/specs/2026-07-17-capafy-10k-mrr-two-loop-spec.md` §9/§10 + `docs/earn/2026-07-18-shared-marketing-engine-plan-for-clip-agent.md`(E1-E6)

## ★次セッションの /goal(本体・1つだけ)★

```
/goal
Objective: clip loop の $計測を閉じる — Digistore24 affiliate 売上を measure_dollar.py が実際に読めるようにする(#9)。これで「投稿→bio link→売上」の money loop が計測可能になる。

Scope:
- IN: (1) :9222 の CloakBrowser に live 認証済みの Digistore24 session(AI所有垢 keiodaisuke+aiclips1@gmail.com、~/.cloak/digistore24-aiclips.json、affiliate_id keiodaisukeaiclips1f031)がある。そこから API settings ページを開き API key を生成/コピー。(2) key を ~/.openclaw/.env に DIGISTORE24_API_KEY= として直結(DOM→file、stdout に echo しない)。(3) `~/.cache/instagrapi-venv/bin/python`(不要、system python)で `python3 ~/anicca/skills/earn/clip/scripts/measure_dollar.py` を1回実行し listPurchases が 200 を返し ~/clips/clip-metrics.jsonl に "type":"dollar" 行が載ることを確認。
- OUT: warm.py human-like化(#11b)、security(#7)、初投稿検証(#5、day3 自走待ち)、marketing OS(Capafy)。
- :9222 は Capafy も使う共有ブラウザ。新 tab で Digistore を開き、他 tab を触らない/閉じない。

Constraints:
- 開発方式 = GLVS（Goal → Loop → Verify → State）。会話でなく file に進捗を書く
- 実装は Sonnet subagent / spec を実装側で曲げない / VCSDD token 上限厳守
- spawn 前後に TaskList → TaskCreate → TaskStop
- 実測せず断定しない（既定の姿勢 = 「私は間違っている」。断定前に外部検索 + 実測）
- 車輪の再発明禁止（作る前に web+gh で既存実装を探して copy+tweak）
- 編集ごとに commit+push（確認を求めない）
- ¥0 は ¥0 と報告する。盛らない
- secret(API key/pw/sessionid)を stdout/chat に出さない。DOM→file 直結。漏洩したら即 rotate
- subagent は research/search 専用。plan と execution(edit/commit/E2E)は Fable が直接やる
- ★実装は VCSDD の実コマンドを phase 順に呼ぶ。SPEC 本文への手書き追記は進捗ではない★
    /vcsdd:vcsdd-init → vcsdd-spec → vcsdd-spec-review → /vcsdd:vcsdd-tdd(RED)
    → vcsdd-impl(GREEN) → vcsdd-adversary → vcsdd-harden → vcsdd-converge
  `.vcsdd/features/<name>/state.json` の phase が進んでいないものは「やった」と言わない
- 規模に応じ mode: lean/strict を選んでよいが、★フェーズ自体は飛ばさない★
- adversary は毎 iteration fresh spawn（model: sonnet 明示）。blocking 1件でも次フェーズ禁止
- 最後に reality-verifier が実ブラウザ/実コマンド出力で source of truth を確認するまで完了と言わない
- worktree-per-task（git worktree add .worktrees/<task> -b feature/<task>）

Done when:
- ~/.openclaw/.env に DIGISTORE24_API_KEY が存在(値は echo しない、`grep -c DIGISTORE24_API_KEY ~/.openclaw/.env` が 1)
- `python3 ~/anicca/skills/earn/clip/scripts/measure_dollar.py` の stdout JSON が listPurchases API 200 を示し、~/clips/clip-metrics.jsonl に "type":"dollar" の行が1つ以上 append される(売上0でも "type":"dollar" 行は載る=接続確認)
- spec `docs/earn/ig-4account-reels-carousel-loop-plan.md` の新 version に実測値で記録 + push

Stop if:
- 同一フェーズ3回 FAIL で止めて handover
- 破壊的・不可逆操作(垢削除、:9222 の Capafy tab kill、他loop の browser 介入)
- 週次 token 残 10%未満
- Digistore の API key 取得に推測アクセス/不正が要る(捏造/不正になる)→止めて Dais に確認
```

## 新セッション開始プロンプト
```
まず /context を測れ。次に handover `.claude/handovers/2026-07-19_1042_clip-loop-honest-rebuild.md` と spec `docs/earn/ig-4account-reels-carousel-loop-plan.md` の v44〜v50 を読め。clip loop は honest に作り直し済みで aiwealth.pulse が warming 自走中(3日後 day3 に初投稿予定、cron 不要=launchd 自走)。俺の担当は clip loop のみ(marketing OS化は Capafy)。残タスクを一つずつ: まず上の /goal(#9 Digistore $計測、独立で今できる)を実行。次に #11b(warm.py human-like化)、#7(security)。#5(初投稿)は day3 の自走を待って logged-out curl で URL 実在を確認。実測せず断定しない、編集ごと commit+push、subagent は research専用で execution は自分でやる。
```
