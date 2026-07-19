# Handover 2026-07-19_1041 — Capafy 応急復活 完了 → 次は汎用 marketing engine 抽出（#31→#35）

## 今回やったこと（flowa: Fable plan / Sol implement / Fable 実測 verify、no-human-loop）

### 閉ループ確立（全て自分で実測検証、Sol 自己申告は不採用）
- #27 IG marketing loop を launchd 登録（3日ゼロ投稿の真因）/ #24 loop 自走を kickstart 実証 / #26 CLIP_POSTER_OVERRIDE 修正(52+8 test green) / #23 SHARED-2 poster canonical / #20 landing 公開(capafy-skills-daily.netlify.app, HTTP200 21card) / #11 telegram SSOT / #8 ig_reflect self-improve。

### 戦略変更（Dais 2026-07-19）— marketing engine 全体
- **day-1 投稿 → day3 投稿に revert**。fresh IG account は day1-2 warmup のみ、day3 で100%投稿。day-1 投稿が account を poison した（memory: marketing-engine-warm-2days-post-day3-never-day1）。capafy gate `-ge 3`、clip は既に day3 floor。
- **poison 真因 = ephemeral browser-sessionid 保存→context 閉じたら死亡→brick**。@useclaudeskills が手動作成でこれを踏んだ。clip の fix = durable golden session（instagrapi `Client().login` + `get_timeline_feed` 検証）。

### #29/#30 self-heal（merged origin/main 26dc69b3）
- goal-monitor が instagrapi verify-only で poison 検知 → cooked marker → marketing が投稿 skip。
- **capafy が fresh account を loop 自身で自作**: handle を account state から解決(hardcode 廃止)、cooked/no-account で PROVISION STEP（clip pattern copy、durable session）。
- **実測**: resolver が poisoned useclaudeskills を除外(handle=none)、`provision_reason=cooked-marker`。kickstart で loop が `provision_needed=yes` 発火 → loop 自身が fresh account 作成を実行中（browser signup、telegram 報告予定）。

## 核心発見（次セッション必読）
**「共有 marketing engine」はまだ存在しない。** 実測: clip と capafy が共有してるのは `clip/scripts/instagrapi_post.py`（poster）**1ファイルだけ**。warmup/provision/reach/reflect/ledger/landing は全部複製。だから clip の教訓（durable session・day3）が capafy に伝わらず poison した。
→ spec §11 + §11.1 に AS-IS/TO-BE を記録済み。**#31 でこれを本当に共有化する。**

## 次にやること（one by one、flowa + VCSDD、Strangler Fig で稼働壊さない）
1. **#31 marketing-engine core 抽出** — `~/anicca/skills/earn/marketing-engine/` に provision/warmer/poster/reach/reflect/ledger/telegram を1実装。clip と capafy を1つずつ config で載せ替え、test green 維持。教訓を1箇所に baked。
2. **#32 product manifest schema** — loop 毎に変わる唯一の物 = manifest(persona/problem/product/content/account/niche/cadence)。capafy/clip を manifest 化。
3. **#33 new-marketing-loop generator** — manifest→launchd 登録→稼働。
4. **#34 README** — 「loop の作り方 = persona/problem/product/content の4項目だけ。engine を再発明するな」。
5. **#35 meta-loop** — product prompt→manifest 自動生成→loop scaffold = true takeoff。
6. **#12 OSS** — profitable-claude へ engine 移設（14日安定後）。
- 並行の非ブロッカー: #1 A1 reject 自動 resubmit / #21 funding(Dais 決定) / #9 A5 売れ筋 selector。
- **loop 稼働中**: capafy-loop-daily 08:10(build) / capafy-ig-marketing-daily 16:00(今 provision 中、day3 投稿) / warmup / goal-monitor 09:00。全 telegram 報告。

## 関連ファイル
- spec(SSOT): `docs/superpowers/specs/2026-07-17-capafy-10k-mrr-two-loop-spec.md`（§9/§10/§11/§11.1）
- clip 担当共有: `docs/earn/2026-07-18-shared-marketing-engine-plan-for-clip-agent.md`
- engine 正解実装（抽出元）: `~/anicca/skills/earn/clip/warm_step.py`（day3 warm）/ `clip_pass.sh`（provision+durable session）/ `scripts/instagrapi_post.py`（poster）
- capafy: `~/anicca/skills/earn/capafy-marketing/`（account_state.sh に resolver、capafy-ig-marketing-daily.sh に PROVISION）

## 次セッションの /goal

```
/goal
Objective: clip と capafy が共有する generalized marketing-engine を抽出し（#31）、任意の product を manifest 1枚で marketing loop 化できる状態（#32/#33）まで到達する。engine を1回直せば全 loop に効く構造にし、車輪の再発明を構造的に不可能にする。

Scope:
- #31 marketing-engine core 抽出: ~/anicca/skills/earn/marketing-engine/ に provision/warmer/poster/reach/reflect/ledger/telegram を1実装。clip の warm_step.py(day3)+clip_pass.sh(provision+durable session)+instagrapi_post.py を正解実装として吸収。clip と capafy を1つずつ engine に載せ替え、各 loop の既存 test green を維持（Strangler Fig、稼働を壊さない）
- #32 product manifest schema(persona/problem/product{name,source,listing_url,bio_link}/content{adapter,hint}/account{state_file,handle_prefix}/niche/cadence)確定 + capafy/clip を manifest 化
- #33 new-marketing-loop generator(manifest→launchd 登録→engine で稼働)
- 途中で capafy の fresh account provision が telegram 報告で完了してるか確認(loop がやる、goal-monitor 09:00 が監査)

Constraints:
- 開発方式 = GLVS。会話でなく file に進捗を書く。spec = docs/superpowers/specs/2026-07-17-capafy-10k-mrr-two-loop-spec.md §11 が正本
- flowa: 私(Fable) plan / Sol one-shot implement / 私が実測 verify。Sol の自己申告は証拠でない、自分で test 再実行・resolver 実行・logged-out curl で確認
- ★実装は VCSDD phase 順: vcsdd-init→spec→spec-review→tdd(RED)→impl(GREEN)→adversary→harden→converge。SPEC 手書きは進捗でない
- Strangler Fig: 抽出中も clip/capafy loop が壊れない。1つずつ載せ替え、都度 test green
- 「loop にやらせろ」= 既存 launchd を kickstart、executor 代行しない。account 作成は loop がやる
- 車輪の再発明禁止（clip の実装を吸収、新実装を増やさない）
- 編集ごと commit+push（~/anicca は即 commit、self-update が未 commit を巻き戻す）。~/anicca は main で稼働 = feature branch は merge して反映
- day-1 投稿禁止(day3)。durable session(browser sessionid 保存禁止、Client().login+get_timeline_feed)。¥0 は ¥0

Done when:
- ~/anicca/skills/earn/marketing-engine/ に共有 core が存在し、clip と capafy が両方それを呼ぶ（grep で複製が poster 以外も共有に変わった事を実測）
- capafy と clip の既存 test が全 green（自分で再実行）
- manifest 1枚で新 loop の pipeline が dry green になる（capafy.yaml/clip.yaml で engine.sh が動く実測）

Stop if:
- 同一フェーズ3回 FAIL で止めて handover
- 破壊的・不可逆操作 / 金の外部流出(OpenRouter top-up 等は Dais の funding源決定) / 週次 token 残 10%未満
- 抽出で稼働 loop の test が red になり戻せない → 止めて handover
```

## 新セッション開始プロンプト
まず `/context` を測れ。spec §11/§11.1 を読んで AS-IS(poster 1個だけ共有)/TO-BE(marketing-engine 抽出)を把握。次に上の `/goal` を flowa で実行。capafy loop は稼働中(provision→warmup→day3 投稿)なので壊さない。
