# Handover 2026-07-19_0050 — Capafy 閉ループ成立（毎日 publish + 毎日 market + bio landing）

## 今回やったこと（flowa: Fable plan / Sol execute / Fable 実測 verify）
Capafy two-loop を「人手ゼロで日次稼働する閉ループ」にした。全て自分で実測検証（Sol 自己申告は不採用）。

| # | item | 証拠 |
|---|---|---|
| #27 GAP | IG marketing loop が **launchd 未登録**（3日ゼロ投稿の真因）→ plist 作成・登録 | `launchctl list` に `ai.anicca.capafy-ig-marketing-daily`、plutil OK、16:00 JST daily。commit 3a0f8068 |
| #25 SHARED-4 | day-1 投稿 gate（`-ge 1`）+ reach ヘルス自己判定 | gate boundary test PASS |
| #24 SHARED-3 | **loop 自走投稿を実証** | 23:50 kickstart で本物の launchd loop が自走: metrics→day-1 live 判定→cadence no-op（executor ゼロ）。実 publish は 07-19 16:00 tick で自動 |
| #26 FIX | CLIP_POSTER_OVERRIDE 未配線（3 test FAIL）→ run.sh:195 seam 配線 | 自分で 8 shell + 52 pytest 再実行 green。commit 9055cc18 |
| #23 SHARED-2 | instagrapi_post.py canonical 共有 poster | 既に account-agnostic(--handle)、hardcode 0件、docstring 宣言 |
| #20 landing | 全skill bio 着地ページ | https://capafy-skills-daily.netlify.app HTTP200 21card 21UTM、日次再生成配線。commit a8bc4f23。netlify auth は launchd 非対話で生存確認済 |
| #11 telegram SSOT | 全 loop→Dais | build STEP5 / marketing STEP7 / goal-monitor 全て 8547730585 報告（実測） |
| #8 self-improve | ig_reflect.py（勝ち post 模倣） | baseline-only 正直出力（捏造なし）、STEP2 が読む。commit 11bf62f8 |

## 閉ループの姿（人手ゼロ）
- **毎日 publish**: `ai.anicca.capafy-loop-daily` 08:10 JST（build、稼働中、telegram 報告）
- **毎日 market**: `ai.anicca.capafy-ig-marketing-daily` 16:00 JST（登録済、自走証明済、@useclaudeskills へ instagrapi 投稿）
- **段階自己管理**: day-1 非商用投稿→reach 実測→`.capafy-ig-reach-healthy` marker を loop 自身が書く→商用（bio に landing URL + soft CTA）
- **bio 着地**: netlify landing（21 skill、日次再生成）
- **監視**: `ai.anicca.capafy-goal-monitor` 09:00 daily telegram
- **warmup**: `ai.anicca.capafy-marketing-warmup`（並走、別 launchd）

## 決定事項 / 捨てた選択肢
- web composer(post_reel.py/ig-reels-poster) は IG silent-drop の dead-end → 全削除。poster = instagrapi_post.py 一本（SHARED-1）
- 同日2本目は撃たない（20h cadence gate + day-1 account の burst 死回避）。実 publish は次 tick 自動
- #21 auto-funding は**やらない**: OpenRouter top-up = 金の外部流出 = Dais の funding-source 決定が要る STOP 点。A2 の key-health gate が dead-key 浪費は既に防止

## ハマりどころ / 学び
- **3日ゼロ投稿の真因 = script 完成なのに launchd 未登録**。「動いてる物」の launchd 登録簿を最初に引くべきだった
- clip 担当の別 CC と engine 共有 → status メール（message_id 19f75aefab14bc4f）で boundary 合意（instagrapi_post.py は additive seam のみ変更、衝突ゼロ）

## 次にやること（優先順）
1. **07-19 16:00 JST の初回自走 publish を確認**（logged-out reel URL + telegram 着弾）。goal-monitor 09:00 が自動監査もする
2. #21 funding: Dais に funding-source を確認（AI wallet か Dais カードか）。alert 型（低残高で telegram）は安全に実装可
3. #9 A5 売れ筋 selector（Capafy ranking→次 skill 選定、build 品質）
4. #1 A1: rejected 4件の Capafy 外部 review 結果を待って resubmit
5. 14日安定後 → #12 profitable-claude OSS 移設

## 関連ファイル
- spec(SSOT): `docs/superpowers/specs/2026-07-17-capafy-10k-mrr-two-loop-spec.md` §6 SHARED表 + §9/§10
- loop: `~/anicca/skills/earn/capafy-marketing/capafy-ig-marketing-daily.sh` / `capafy-goal-monitor.sh`
- build: `~/anicca/skills/self/capafy-loop/capafy-loop-daily.sh`
- poster: `~/anicca/skills/earn/clip/scripts/instagrapi_post.py`（canonical 共有）
- landing: `~/anicca/skills/earn/capafy-marketing/scripts/build_landing.py` + `site/`
- reflect: `~/anicca/skills/earn/capafy-marketing/scripts/ig_reflect.py`

---

## 次セッションの /goal

```
/goal
Objective: Capafy 閉ループの初回自走 publish を確認し、残る Dais ゲート項目(#21 funding)と build 品質(#9 A5)を進め、10k MRR へ向けて毎日 publish+market が壊れず回り続ける事を保証する。

Scope:
- 07-19 16:00 JST の capafy-ig-marketing-daily 初回自走 publish を検証（logged-out で reel 公開確認 + telegram 着弾 + ledger 記録）。失敗なら真因を実測して直す
- #21 OpenRouter funding: Dais に funding-source を1問確認し、alert 型（低残高 telegram）を安全実装（auto-charge は Dais 承認まで実装しない）
- #9 A5 売れ筋 selector（Capafy ranking→次 publish skill 選定）を VCSDD で実装
- #1 A1 rejected 4件の Capafy review 結果を確認し通れば resubmit

Constraints:
- 開発方式 = GLVS（Goal → Loop → Verify → State）。会話でなく file に進捗を書く
- 実装は Sol/Luna executor（flowa）。spec を実装側で曲げない / VCSDD token 上限厳守
- ★実装は VCSDD の実コマンドを phase 順に呼ぶ。SPEC 本文への手書き追記は進捗ではない★
    /vcsdd:vcsdd-init → vcsdd-spec → vcsdd-spec-review → vcsdd-tdd(RED) → vcsdd-impl(GREEN) → vcsdd-adversary → vcsdd-harden → vcsdd-converge
- spawn 前後に TaskList → TaskCreate → TaskStop
- 実測せず断定しない（既定 = 「私は間違っている」。断定前に実測）。Sol の自己申告は証拠でない、自分で再実行検証
- 「loop にやらせろ」= 既存 launchd を kickstart、executor で代行しない
- 車輪の再発明禁止（作る前に web+gh で既存を探す）
- 編集ごとに commit+push（~/anicca は即 commit、self-update が未 commit を巻き戻す）
- ¥0 は ¥0 と報告。盛らない。「稼いだ」= 実 subscriber or status=4 の時のみ
- 金の外部流出(top-up 等)は Dais の funding-source 決定が要る STOP 点

Done when:
- 16:00 tick の reel が logged-out で公開確認でき、telegram に届き、ledger に記録されている（machine-checkable: curl 公開URL 200 + ledger grep + telegram message_id）
- #21 alert が低残高で telegram を撃つのを実測（閾値を一時下げて発火確認）
- #9 A5 selector が Capafy ranking を読んで次 skill を決定的に選ぶのを実測（state.json phase converge）

Stop if:
- 同一フェーズ3回 FAIL で止めて handover
- 破壊的・不可逆操作 / 金の外部流出 / 週次 token 残 10%未満
```

## 新セッション開始プロンプト
まず `/context` を測れ。次に上の `/goal` を実行。spec = `docs/superpowers/specs/2026-07-17-capafy-10k-mrr-two-loop-spec.md` を読んで現実を把握してから着手。flowa（Sol execute / Fable verify）で回す。
