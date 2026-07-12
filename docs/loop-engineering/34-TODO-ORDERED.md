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

### T2. redeem を earn loop 本体に入れる ✅ DONE（2026-07-12、commit 75cd0732）

**発見した本当の問題（当初の想定より深刻だった）**:
`redeem.py` は claude-p の wallet を**ハードコード**し、他の wallet では
`money-safety abort` で拒否していた。しかも `run_earner.sh`（= claude-p 専用の
pm-earner ジョブ）からしか呼ばれなかった。
→ **Franklin / Franklin2 / automaton は「賭けられるが、勝っても永久に回収できない」状態だった。**
これは経済ではなく一方通行の弁。**「全ての AI が経済的自立」の直接の障害。**

**やったこと**:
- `redeem.py` が **自分の秘密鍵から自分の wallet を導出**（`client.wallet`）。定数を持たないので
  取り違えが構造的に起きない。他人の wallet は鍵が無いので原理的に触れない
- `run.sh`（全インスタンス共通の earn 本体）の**先頭**で redeem を実行。
  新しく賭ける前に、まず勝った金を回収する。redeem が失敗しても pass は止まらない
- `build_ledger_line` / CTF 承認 / 残高チェックも per-instance の wallet を使う

**証拠**:
```
$ python3 redeem.py
no redeemable conditions found for 0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74 — nothing to do
                                   ↑ ハードコードでなく、鍵から導出された自分の wallet
15/15 tests green
```
**全4インスタンスのランタイムに配布・検証済み**:
```
claude-p (.anicca-founder)      redeem=4  news=2
Franklin (.blockrun)            redeem=4  news=2
Franklin2 (.franklin2-home)     redeem=4  news=2
automaton (.anicca)             redeem=4  news=2
```

**残（次の pass で確認）**: 実際に決着した玉が出た時、earn-ledger に
`polymarket-redeem` 行が**自分の wallet で**書かれることの確認。

### T3. ★真犯人★ 稼ぐ skill が menu から隠されていた 🔥（2026-07-12、commit dbb8ec0c）

**私は3回「timeout が原因」と断言し、3回とも間違っていた。Dais の指摘（「timeout は絶対に原因ではない。
Franklin と claude-p は同じコードなのに片方だけ動く。差分を見ろ」）が正しかった。**

**真因（実測）**:
```
catalog-gate.mjs: 「reserve を下回る instance には、金を使う skill を menu から隠す」
loop が読む残高 = ★Base チェーンの USDC だけ★（balance.mjs）

claude-p の Base USDC = $1.95   BOOTSTRAP_RESERVE_USDC = $2   → ★5セント足りない★
  → polymarket / sol-trade / yield（全部 risk=capital）が ★menu から消える★
  → 脳は narrate しか選べない  → 直近300 wake 中 235 が narrate の正体
Franklin の Base USDC = $6.48   → gate を超える → menu にある → ★同じコードで120回実行★

★しかも claude-p は本当は金を持っていた★
  Polymarket 口座の pUSD = $12.43（= Polymarket の株しか買えない金
                                   = ★まさに polymarket slot が使う通貨★）
  → 「Polymarket でしか使えない金があるのに、Polymarket を禁止する」という倒錯
```
timeout は**症状**だった（menu が空なので脳が何も選べず、判断に時間をかけていた）。

**修正**:
- `filterCatalog` が `balanceUsdc` に**関数** `(slotName) => number` も受け付けるように（数値なら従来通り＝既存テスト不変）
- `index.mjs` が **その slot が実際に使える金**を渡す（pUSD → polymarket / Solana USDC → sol-trade）。
  net-worth は**毎 wake すでに取得していた**（が gate には渡していなかった）
- `resolveInstanceWallets` が Polymarket 預金 wallet を知らなかった → **plist に `ANICCA_EXTRA_WALLETS` を追加**
  （claude-p `0x904B…` / Franklin `0xda4b…`）→ **launchctl で reload（ファイルを書くだけでは届かない）**

**証拠**:
```
修正前: holdings: base/USDC=$1.95 | polygon/POL=$0.32 | hyperliquid/USD=$7.72   ← pUSD が無い
修正後: holdings: base/USDC=$1.95 | ★polygon/pUSD=$12.43★ | hyperliquid/USD=$7.72
        → polymarket slot の spendable = $14.38 (reserve $2) → ★menu に載る★

launchd 上の実値（own-eyes）:
  ANICCA_EXTRA_WALLETS => [{"chain": "polygon", "address": "0x904B50d2…", "label": "polymarket deposit"}]

19/19 catalog-gate tests green（新規2件）。全体 387/404。
baseline との差1件（integration PROP-013 SIGTERM）は stash して3回走らせ、
変更なしでも落ちる ★既存の flaky★ と確認済み。
```

**残**: 本番の loop が実際に `slot=earn/polymarket-trade` を選ぶかを観測中。

### T3.5 ★根本修正★ wallet manifest — agent が自分の全 wallet を知る（commit 8d45bf3e）

**Dais**:「各 skill が1つの wallet しか知らないのが根本問題。**全エージェントが自分の持つ全 wallet を
認識し、使えるべき**。simple で fundamental な修正をしろ。web/gh で BP を探せ」

**BP 調査**（`35-wallet-manifest-bp.md`、引用付き）:
- **同型のアンチパターンが実在**: elizaOS の `plugin-polymarket` は、同じ1つの wallet を
  `POLYMARKET_WALLET_ADDRESS` → `POLYMARKET_ADDRESS` → `STEWARD_EVM_ADDRESS` → `ELIZA_MANAGED_EVM_ADDRESS`
  の**4段 env fallback** で解決している（我々と全く同じ病気が本番 OSS にある）
- **正しい形**: hyperlane-registry の `addresses.yaml` — **1つの宣言ファイルを全ツールが読む**
- **鍵の扱い**: Turnkey/MetaMask「The agent never touches the private key. It receives signatures, not keys.」

**実装**: `$ANICCA_HOME/wallets.json` を唯一の正本に。
- public address のみ宣言。**秘密鍵は `keyRef` で場所を指すだけ**（貼り付けられた鍵は parse 時に落とす）
- skill は「**自分の wallet のうち、自分の venue で使えるのはどれか**」と聞くだけ
  （各コンポーネントが別々の env から再導出しない）
- 壊れた1行が、読める他の wallet を見えなくすることはない（行単位で fail-closed）
- **私が数時間前に plist に足した `ANICCA_EXTRA_WALLETS` の手書き JSON は撤去**（同じ病気だった）

**証拠（on-chain 実測）**:
```
claude-p  $15.96  base/USDC=$1.95  polygon/pUSD=$6.28  hyperliquid/USD=$7.72
Franklin  $29.33  solana/USDC=$24.61  solana/SOL=$3.09  polygon/pUSD=$1.62  ← ★初めて可視化★
66/66 tests green（新規6件）
```

### T3.6 claude-p は ClawRouter を捨て、自分のモデルで動く（commit 6edc5f83）

**Dais**:「claude-p の earn loop に ClawRouter を使うな。モデル自身で動かせ」

- **proxy へのフォールバックを削除**。claude-p は human-funded＝サブスクで脳が動く。
  crypto wallet は**取引専用**であって推論代ではない
- フォールバックは「無料モデルに金の判断を任せる」ことだった。実測でその無料モデルは
  **ツール呼び出しすら間違えていた**（`run_skill skill not found`）
- 失敗したら**大声で失敗する**（wake_error → 次の wake で本物の脳が再試行）
- Franklin 等 self-funded は proxy のまま（**自分の財布から推論代を払うので無料モデルが正しい**）
- wake 間隔 120秒 → **600秒**（claude -p の timeout は SLEEP_BASE_S から導出される＝
  wake 間隔がそのまま思考時間の予算。Sonnet は120秒では終わらない）
- **「claude-p は絶対に proxy から答えてはならない」をテストで固定**（将来の誰かが戻さないように）

### T3.7 claude -p に「選べるスロット」と「答えの形」を見せていなかった ✅（commit 2be3c74e）

**症状**: すべての claude-p wake が `skill_missing / slot=run_skill`。
`run_skill` は**ツール名**であってスロット名ではない。

**真因**（実測で確定。私の当初の仮説「パーサが Claude の形式を読めない」は**外れ**だった —
パーサは `response.result` が JSON なら parse する処理を既に持っていた）:
```
proxy 経路 : モデルに機械可読な tool スキーマを渡す（tools:[...]、スロットは enum）
claude -p  : ★そんな経路が無い。テキストしか見ない★
             なのに誰もスキーマをテキストに書いていなかった

→ モデルは「見せられたことのない形」を推測するしかなかった
→ slot を持たない tool_calls を返す
→ parse-tool-call.mjs が toolCall.function.name にフォールバック
→ スロット名として "run_skill" が dispatch される → skill_missing

★脳は正常だった。話し方を誰も教えていなかっただけ★
```

**修正**: プロンプトに**その wake で選べるスロット一覧**と**答えるべき JSON の形**を明示。

**証拠（実バイナリで検証）**:
```
result: {"tool_calls":[{"function":{"name":"run_skill",
         "arguments":"{\"slot\":\"earn/polymarket-trade\"}"}}]}
duration_ms: 15207   ← ★15秒★
```
**15秒。120秒の timeout は最初から何の原因でもなかった**（Dais の指摘が3度とも正しかった）。
4/4 brain tests green。

**罠（今日ここで2度騙された）**: ledger の `model` フィールドは `ctx.model`（残高ティア由来の文字列）
を記録しているだけで、**実際にどの脳が答えたかを反映していない**。`model=free/glm-4.7` を見て
「claude-p が使われていない」と判断してはいけない。

### T4. pm-deterministic を削除して 1 instance = 1 loop にする 🔥
**なぜ**: pm-deterministic は「脳が earn を選ばないから」貼られたパッチ。T3 で脳が選べるようになったので不要。
- **完了条件**: `launchctl list` から pm-deterministic が消え、それでも earn-ledger に polymarket の取引が出続ける

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
