# 33 — COLONY GROUND TRUTH（全エージェントが最初に読む。混乱の解消）

**このファイルの目的**: Anicca colony は「名前が実態と一致していない」ために、人間も AI も繰り返し誤解してきた。
このファイルは 2026-07-12 に **own-eyes（実際にコマンドを実行して観測）**した事実だけを書く。推測は「推測」と明記する。

**鉄則**: このファイルの記述と、実際に動いているプロセス／on-chain の数字が食い違ったら、**実物が正しい**。
その時はこのファイルを直せ。逆に、このファイルを直しただけで「直した」と言うのは嘘である（今日3回それをやった）。

---

## 1. 登場人物 — AI は4人。財布は別々

| 誰 | 推論代（脳の代金）の出所 | 財布 | 意味 |
|---|---|---|---|
| **claude-p** | ★Dais の Anthropic サブスク★ | Polymarket `0x904B50d2…`(Polygon) / Base `0x810f…` | **脳がタダ**。だから**強い脳（Sonnet）を使うべき**。crypto は1円も減らない |
| **Franklin** | 自分の crypto（x402 で払う） | Solana `8Fpqd…` / Polymarket `0xda4b6E34…` | 脳の代金を自分で払う。**だから無料モデル（free/glm-4.7）が正しい** |
| **Franklin2** | 自分の crypto | `~/.franklin2-home/.blockrun/.automaton/wallet.json`（**private key のみ。address が記録されていない = 要修正**） | 同上 |
| **automaton (a3cdd4)** | 自分の crypto | Base `0xB9dd3B67…` | 同上 |

**★ 最重要 ★**: claude-p だけは脳がタダ。**弱い脳（free/glm-4.7）を使う理由が1つも無い。**
ClawRouter / proxy は **self-funded（Franklin 系）専用の仕組み**であり、claude-p が使うのは設計ミス。

---

## 2. 金（2026-07-12 22:45 JST 実測、public API で own-eyes）

```
╔══════════ claude-p ══════════════════════════════════════════════╗
║  Polymarket 現金 (pUSD)     $5.18   ← すぐ賭けられる            ║
║  Polymarket 建玉（賭け中）  $11.00  ← 未決着。勝てば増、負ければ0 ║
║  Base USDC (0x810f)         $1.95                               ║
║  ─────────────────────────────────                              ║
║  合計                       $18.13                              ║
║  ★redeem 実績（実際に現金化した）: 9件 / net +$9.37★             ║
║   = tx hash 付きの本物。コロニーで唯一の実績                     ║
╚══════════════════════════════════════════════════════════════════╝
╔══════════ Franklin ══════════════════════════════════════════════╗
║  Solana USDC                $24.74  ← 現金のまま動いていない     ║
║  Polymarket 建玉            $5.60   ← 未決着                    ║
║  合計                       $30.34   / 実 external 稼ぎ: 1件のみ ║
╚══════════════════════════════════════════════════════════════════╝
╔══════════ automaton ═════════════════════════════════════════════╗
║  Base USDC                  $0.59   ← ほぼ空。何もできない       ║
╚══════════════════════════════════════════════════════════════════╝
╔══════════ Franklin2 ═════════════════════════════════════════════╗
║  wallet address が記録されていない → ★残高を誰も検証できない★    ║
╚══════════════════════════════════════════════════════════════════╝

  コロニー合計 ≈ $49
  ★ 実際に稼いだ（redeem した）のは claude-p の +$9.37 だけ ★
```

---

## 3. ★ 混乱の元凶 = 名前が実態と一致していない ★

| 名前 | **実際にやっていること** | 脳 | 生死（実測） |
|---|---|---|---|
| `ai.anicca.claude-p-mainloop` | **自分を "AGENT ECONOMY LOOP" と名乗る**（prompt.txt の1行目）。経済圏を**作る**（コードを書く）。**金は稼がない** | Sonnet（サブスク） | ⛔ Dais が 2026-07-12 停止 |
| `ai.anicca.agent-economy-loop` | **↑と名前が同じだが全くの別物**（`runtime/loop/index.mjs`）。claude-p の**稼ぐループ**。LLM が skill を選ぶ | free/glm-4.7（誤り）→ claude-p に変更したが **120秒 timeout でフォールバック** | 🟡 生きているが機能していない（直近300 wake中 235 が narrate） |
| `ai.anicca.pm-earner` | Polymarket を10分ごとに回す。**★redeem（勝ち玉の現金化）★ + bundle_arb + market_maker + ★dashboard への telemetry★** | **LLM を1回も使わない** | 🟢 生きている。**3回 disable したが self-healer が蘇生** |
| `ai.anicca.pm-deterministic` | Polymarket を30分ごとに回す。`run.sh` を実行 | 内部の `pick.py` だけ LLM | 🟢 生きている |
| `ai.anicca.founder-loop-cadence` | **取引しない**。`record-earn.mjs` で Base の入金を記録 + **★Dais へメール送信★** + CEO の予算配分 | LLM を使わない | 🟢 生きている。**削除されていない** |
| `ai.anicca.franklin-loop` / `franklin2-loop` / `com.anicca.daemon` | `agent-economy-loop` と**同一コード**（`index.mjs`）の別インスタンス | free/glm-4.7（**正しい**） | 🟢 生きている |

### 3.1 「dashboard が claude-sonnet-5 と言っている」の正体

```
runtime/dashboard/telemetry-post-claude-p.mjs:93
    model_live: "claude-sonnet-5",   ← ★ハードコードされたただの文字列★
    brain: "claude-p",               ← ★これもハードコード★
```
これを送っているのは **pm-earner**（`run_earner.sh` が `telemetry-post-claude-p.mjs` を呼ぶ）。
**pm-earner は LLM を1回も使わない。** dashboard の `claude-sonnet-5` は**嘘**であり、
実際に動いているモデルを1ミリも反映していない。誰も検証していないので37日間放置された。

`0x02bb6b2af70dbf2c367c1b69aca9858bf3525502` = claude-p の **telemetry 署名専用 wallet（残高ゼロ）**。
資金は `0x904B50d2…`（Polymarket）と `0x810f…`（Base）にある。

---

## 4. ★ pm-earner と agent-economy-loop の関係（最も重要な発見）★

「同じことをしているのか」への答え = **半分だけ同じ**。

```
╔════════════════════════════════════════╤══════════════════════════════════════╗
║  pm-earner (run_earner.sh, 40行)       │  agent-economy-loop が PM を選ぶと    ║
║                                        │  実行される run.sh (363行)            ║
║                                        │  ＝ pm-deterministic と同一ファイル   ║
╠════════════════════════════════════════╪══════════════════════════════════════╣
║  ★ redeem.py ★  勝ち玉を現金化         │  （無い）★これが致命的★              ║
║  ★ telemetry-post-claude-p.mjs ★       │  （無い）                            ║
║  pm-reconcile.mjs（ledger照合）        │  （無い）                            ║
║  ────────── 以下は完全に同一コード ──────────                                  ║
║  bundle_arb.py                         │  bundle_arb.py    ←★同一ファイル★    ║
║  market_maker.py                       │  market_maker.py  ←★同一ファイル★    ║
║  ──────────────────────────────────────────────                               ║
║  （無い）                              │  ★ pick.py ★ LLM が方向性の賭けを決定 ║
║                                        │  ★ place_order.py ★                  ║
║                                        │  ★ pinnacle_edge/observe.py ★ エッジ  ║
║                                        │  ★ genome.mjs / evolve.mjs ★ 戦略進化 ║
║                                        │  fund_via_bridge.py                  ║
╚════════════════════════════════════════╧══════════════════════════════════════╝
```

**帰結:**
1. `bundle_arb` と `market_maker` は **同じコードが、同じ財布 `0x904B50d2…` に対して、2〜3系統から独立に注文を出している**（KILLスイッチも排他制御も無い）。
2. **pm-earner を単に削除すると redeem が死ぬ** → 勝った玉が永久に現金化されず、資金が凍結する。
   → **だから self-healer が蘇生させたのは、結果的に正しかった。** 削除ではなく**統合**が必要。

---

## 5. なぜ壊れたか（root cause、git で確認）

```
commit 4a6cc1f3 "purify claude-p-mainloop as sole BUILD-loop"  (2026-07-12 01:07)
  branch: feature/build-loop-unify（main には未マージ）

  prompt に追加された1行目:
  「You are LOOP B (the large brain, Anthropic subscription) — your only job is to
    make the small-brain EARN loops able to earn.
    ★You yourself never perform or simulate an earn action (no trades)★」
```

**「強い脳（サブスク・タダ）は稼ぐな。弱い脳（無料モデル）が稼げ」という逆立ちした設計になった。**
→ 弱い脳は何も判断できず narrate を繰り返す
→ 仕方なく pm-earner / pm-deterministic を cron で後付け
→ **重複と、同一財布への多重発注が発生した**

claude-p は推論代がタダなのだから、**強い脳がそのまま稼げばよかった**。

---

## 6. TO-BE（あるべき姿）

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  ★ 1 instance = 1 earn loop。それだけ。★                                      │
│                                                                              │
│  claude-p   → earn loop 1本  脳 = ★Sonnet（サブスク）。ClawRouter 不使用★      │
│  Franklin   → earn loop 1本  脳 = free/glm-4.7 + ClawRouter（自費なので正しい）│
│  Franklin2  → earn loop 1本  脳 = 同上                                        │
│  automaton  → earn loop 1本  脳 = 同上                                        │
│                                                                              │
│  各 earn loop の中身（★1本に統合。今バラバラなものを1つに★）:                 │
│    ┌────────────────────────────────────────────────────────┐                │
│    │ 1. redeem       決着した勝ち玉を現金化   ←★絶対に必要★ │                │
│    │ 2. 脳が skill を選ぶ: polymarket / sol-trade / yield    │                │
│    │ 3. 選んだ skill を実行（賭ける／売る）                  │                │
│    │ 4. reconcile    ledger と wallet を照合                 │                │
│    │ 5. telemetry    dashboard に★本当の値★を送る            │                │
│    └────────────────────────────────────────────────────────┘                │
│                                                                              │
│  build loop（claude-p-mainloop）= ⛔ off のまま（Dais の判断）                 │
│  founder-loop-cadence（記録+メール）= 🟢 そのまま（取引しないので害はない）    │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. TODO（TO-BE に到達するまで）

| # | やること | 完了条件（検証可能） | 状態 |
|---|---|---|---|
| **A** | **claude-p の earn loop を1本に統合**（redeem + 脳 + skill実行 + reconcile + telemetry） | `launchctl list` に claude-p の earn loop が**1本だけ**。redeem が動き続ける（earn-ledger に新しい `polymarket-redeem` 行が出る） | ⬜ |
| **B** | **claude-p の脳を Sonnet に（timeout の出ない型で）** | ledger に `model=sonnet` かつ `slot=earn/*` の wake が出る。narrate 率が下がる | ⬜ |
| **C** | **self-healer が「意図的に殺したループ」を蘇生しないようにする** | `.disabled` されたループを healthcheck が kickstart しない | ⬜ |
| **D** | **dashboard の `model_live` / `brain` ハードコードを消す** | dashboard が実際のモデル名を表示する（または表示しない） | ⬜ |
| **E** | **Franklin に検索能力を持たせる** | Franklin の判断ログに外部情報（ニュース/web）が現れる | ⬜ |
| **F** | **Franklin2 の wallet address を記録する** | `docs/WALLETS.md` に address が載り、残高が検証できる | ⬜ |
| **G** | **config-drift detector を全ループの healthcheck に配線** | 「宣言（plist/registry/doc）と実体（動いているプロセス）」の乖離が自動検出される | 🔄 実装済・未配線 |
| **H** | **PM に早期売却（early exit）を入れる** | $0.95+ の勝ち玉を指値で売り、資金を解放する（`32-exit-and-redeem-best-practice.md`） | ⬜ |

**依存**: A → B → (C,D 並行) → E,H

---

## 8. 今日3回破った鉄則（次のエージェントへ）

1. **ドキュメントに「停止した」と書くことは、停止したことではない。** `TASKLIST.md` #3 は3度「pm-earner を停止した ✅」と書いたが、3度とも生きていた。
2. **plist ファイルを編集することは、launchd に届くことではない。** `launchctl bootout` + `bootstrap` をして、`launchctl print` で実値を確認するまで、何も変わっていない。
3. **subagent の報告は証拠ではない。** 自分でコマンドを実行し、出力を見るまで信じるな。
4. **dashboard の表示は真実ではない。** 誰かがハードコードした文字列かもしれない。

**検証の道具（今日作った）**:
- `node ~/anicca/runtime/loop/config-drift.mjs` → 宣言と実体の乖離を JSON で出す（exit≠0 なら乖離あり）
- `~/anicca/.claude/agents/reality-verifier.md` → 文脈ゼロの Sonnet が ledger/on-chain/実ブラウザで「本当か」を判定
