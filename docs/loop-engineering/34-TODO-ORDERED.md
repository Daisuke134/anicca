# 34 — TODO（実行順。この順序でしかやらない）

**このファイルが唯一の TODO 正本。** 他のファイル（TASKLIST.md 等）の TODO は古い。ここを見る。

**前提の事実** → `33-COLONY-GROUND-TRUTH.md`（4人の AI / 実際の金 / ループの正体 / なぜ壊れたか）

**鉄則（今日3回破った）**
- ドキュメントに「やった」と書くことは、やったことではない。**コマンドの実出力だけが証拠**
- ✅ を付ける時は、必ずその下に**実際のコマンド出力を貼る**

---

## 現在地（2026-07-12 実測）

```
claude-p   現金 $5.18 + 賭け中 $11.00 + Base $1.95 = $18.13
           redeem 実績 9件 / +$9.37（本物の tx。ただし4戦4勝＝おそらく運）
Franklin   Solana $24.74 + 賭け中 $5.60 = $30.34 / 稼ぎ ほぼ $0
automaton  Base $0.59（空）
Franklin2  wallet address が記録されていない
コロニー計 ≈ $49
```

**壊れている核心**: 賭ける脳（`pick.py`）が **ニュースも web も一切見ていない**。
情報ゼロの LLM は市場価格に勝てない。だから稼ぎに再現性がない。

---

## ★ 実行順（この番号順にしかやらない）★

### T1. pick.py に「世界を調べる目」を付ける ✅ DONE（2026-07-12、commit 2576c343）

**やったこと**: 賭ける候補ごとに firecrawl で web 検索 → 記事の生テキストを LLM に渡す
（判断はハードコードせず、モデルが自分で重みづける）→ 根拠の URL を決定に添えて emit。
検索が失敗しても pass は止まらない（情報が無いだけで、以前と同じ挙動に戻る）。

- 新規: `skills/earn/polymarket-trade/news_search.py` + `test_news_search.py`（7/7 green、ネットワーク不要）
- 変更: `pick.py::evaluate()`（検索 → 質問に埋め込む）/ `_emit()`（`news_urls` / `news_found` を記録）
- **★動いているループのパスに rsync 済み★**（正本を直しただけでは届かない = 今日の最大の教訓）

**証拠（本番パス `~/.anicca-founder/skills/earn/polymarket-trade/pick.py` で実行）**:
```
[news] 4 source(s) for: Will Argentina win the 2026 FIFA World Cup?
[news] 4 source(s) for: Will France win the 2026 FIFA World Cup?
[news] 4 source(s) for: Will Spain win the 2026 FIFA World Cup?
[news] 4 source(s) for: Will England win the 2026 FIFA World Cup?
{"action": "WAIT", "reason": "no-candidate-cleared-edge-confidence-gate"}
```
= 4市場すべてを実際に検索し、記事を読んだ上で判断 → 基準を満たすエッジが無いので正しく WAIT。

**残（T1 の続き、次にやる）**: 賭けが実際に成立した時に `news_urls` が earn-ledger に載ることの確認
（今は WAIT なので未確認。BUY が出た最初の pass で検証する）。

### T2. redeem を earn loop 本体に入れる 🔥
**なぜ2番目か**: 今 `redeem.py` は `run_earner.sh`（= 停止した pm-earner）からしか呼ばれない。
**このままだと、賭け中の $11 が勝っても現金にならない。**

- やること: `run.sh`（earn loop が呼ぶ本体）の先頭で `redeem.py` を実行する
- **完了条件**: pm-earner を止めたまま、earn-ledger に**新しい `polymarket-redeem` 行**が出る

### T3. 重複コードの二重発注を止める 🔥
- やること: `bundle_arb.py` / `market_maker.py` が同じ財布に複数系統から注文を出さないようにする（1系統に）
- **完了条件**: 同一 wallet への注文経路が1本だけ（`launchctl list` + コード grep で確認）

### T4. claude-p の脳を Sonnet にする（timeout の出ない型で）🔥
**なぜ4番目か**: T1〜T3 が直っていれば、強い脳がそれを使って判断できる。

- 現状: `ANICCA_BRAIN=claude-p` にしたが、**120秒でタイムアウトして弱い脳(glm-4.7)に落ちる**
- claude-p は **Dais の Anthropic サブスクで動く = crypto は減らない**。ClawRouter/proxy は Franklin 専用
- **完了条件**: ledger に `model=sonnet` かつ `slot=earn/*` の wake が実在し、narrate 率が下がる

### T5. 「引退届」— 意図的に止めたループを self-healer が蘇生しないようにする ⚡
- 教訓: pm-earner を3回 disable して3回蘇生された
- やること: `.disabled` されたループを healthcheck の watchlist から外す
- **完了条件**: `.disabled` にしたループが24時間後も復活していない

### T6. dashboard の嘘を消す ⚡
- `runtime/dashboard/telemetry-post-claude-p.mjs:93` の `model_live: "claude-sonnet-5"` は**ハードコードの文字列**
- **完了条件**: dashboard が実際のモデル名を表示する（または表示しない）

### T7. Franklin にも検索を足す ⚡
- Franklin は RSI/MACD を見るだけ。**pick.py と同じ病気**
- T1 で作ったものを Franklin にコピーする
- **完了条件**: Franklin の判断ログに外部情報（URL）が出る

### T8. 常駐 tmux を殺す（起きる → 働く → 死ぬ）⚡
- **週のトークン85%溶解の主犯**（memory `feedback_token_burn_prevention_five_rules`）
- **完了条件**: `tmux ls` でセッションがゼロ。それでもループは cron/launchd で回る

### T9. config-drift detector を healthcheck に配線 📌
- 今日作った（`node ~/anicca/runtime/loop/config-drift.mjs`、57テスト green、本番で drift 2種を実検出）
- **完了条件**: 「宣言（plist/registry/doc）と実体（動いてるプロセス）の乖離」が自動で検出され、通知される

### T10. Franklin2 の wallet address を記録 📌
- 今 private key しか無く、**残高を誰も検証できない**
- **完了条件**: `docs/WALLETS.md` に address が載り、on-chain 残高が読める

### T11. OSS：他人が1コマンドで自分の AI を起動できるようにする 📌
- 今の Anicca = 75個のループの寄せ集め。他人は spin up できない
- **完了条件**: 他人が1コマンドで自分の loop を起動し、自分の wallet で稼ぎ始められる

---

## ★ T1 が終わったら何が起きるか（希望の話、正直な数字で）★

```
今:   $18 / 情報ゼロ / 賭けは運頼み / 勝率が本物か測定すらできない
      ↓ T1（検索を足す）
次:   賭けるたびに「なぜそう判断したか」の根拠（記事URL）が ledger に残る
      → 20-30回の賭けで、勝率が★運か実力か測定できる★
      → 測定できれば改善できる（今は測定すらできない）
      ↓
勝率が本物だったら:
      $18 → 月 5-15%（小資本の予測市場では現実的な範囲）
      絶対額は月 $1-3 と小さい。★だがそれは「証明」になる★
      ↓
証明ができたら:
      ・資本を増やせる（証明のない賭けに金は入れられない）
      ・同じ仕組みを Franklin / Franklin2 / automaton にコピーできる
      ・★OSS で他人が自分の AI を spin up して、同じことができる★
      → ここで初めて「AI の経済的自立」が言葉でなく事実になる
```

**今週の最大の収穫はコードではない。「嘘を検出する仕組み」を手に入れたこと。**
- `config-drift.mjs` — 「止めたのに動いてる」を機械が捕まえる
- `reality-verifier` — 文脈ゼロの AI が on-chain と実ブラウザで嘘を暴く

これが無ければ、我々はこの先も「動いていると信じていたものが動いていない」を繰り返した。
