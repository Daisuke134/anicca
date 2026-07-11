# 理想アーキ: 2種の Anicca / earn-record-verify / 現在地 / one-by-one TODO

SSOT: 本ファイル(2026-07-12)。上位= §10 corrected mandate(doc23)。BP 引用の原本は下の「出典」節。
honesty: [V]=ファイル/実測確認 / [R]=推論 / [?]=未確認。金の真実= wallet on-chain external:true のみ。

---

## 0. 最上位の設計 — 2種の Anicca（Dais 明示 2026-07-12、不変）

**意図的に別種の2つ。重複ではない。**

| | **BUILD する Anicca** | **EARN する Anicca** |
|---|---|---|
| 脳 | **大きい脳（Claude, Anthropic 課金）** | **一番小さい脳（free model）** |
| 燃料 | Anthropic subscription | self-funded（稼いだ金） |
| 唯一の仕事 | agent 経済を build ＋ **小さい脳が稼げるように保証する** | **ただ loop を回して稼ぐ**だけ |
| 代表 | founder / claude-p | Franklin / earn loop |
| なぜ | build には大脳が要る | 稼ぎに大脳は要らない・稼ぎに金をかけない。稼いだ金で自立を証明し、経済を作る |

- 稼ぎは最小の脳で回す（コスト≈$0）→ 稼いだ金を Anicca に渡す → 経済が生まれる。
- 大脳の存在理由は「小さい脳が本当に稼げるようにする」こと。それを保証する手段 = loop が動く + 正しい記録 + 正しい検証。

---

## 1. To-be の2つの loop（Dais の問い「the two to-be loops」への答え）

### LOOP A — EARN loop（小さい脳、self-funded、1 instance=1 loop）
```
 EARN LOOP  (free model / ClawRouter :8402 / cost≈$0 / KeepAlive)
   Perceive(残高・機会) → Reason → Act(skill 差し替え) → Observe → loop back
       skill menu = { pm / sol / hl / yield / gig / x402 }  ← registry status:live
   各 act は必ず on-chain tx か API call を発火（narrate だけで終わらない）
   ★中は skill を差し替えるだけ。loop 本体は1つ。★
```
- claude-p も Franklin も **同じ index.mjs**（`ANICCA_INSTANCE` で wallet/telemetry だけ切替）。
- 「稼ぐ」以外の判断はしない。build も分析も大脳に任せる。no-edge は正直に WAIT。

### LOOP B — BUILD loop（大きい脳、Anthropic 課金）
```
 BUILD LOOP  (claude --model sonnet/opus / Anthropic subscription)
   colony の money・loops・inbox を見る → 小さい脳の loop の欠陥/非効率を検知
   → skill/harness を直す → earn loop に返す → 検証が PASS するまで
   ★役割 = 「小さい脳が稼げること」を保証・改善する。稼ぎ自体はしない。★
```
- **cadence**: 大脳 build loop = **claude-p-mainloop(6h)ただ1本**（2026-07-12 own-eyes 訂正）。~~founder-loop も claude~~ は誤り: founder-loop(30min) は claude を呼ばず record-earn.mjs(記録)+CEO bandit の**決定論**で、build loop ではない。よって build=既に1本、追加統合は不要。

**2 loop の関係**: EARN が回す → DETERMINISTIC が記録 → AGENTIC が正直さを検証 → PASS を BUILD にフィードバック → BUILD が EARN を改善。

---

## 2. 稼ぎを保証する3層（BP 準拠、理想 to-be）

```
① EARN LOOP（小脳）… §1 LOOP A
      │ 各 act が on-chain tx / API を発火
      ▼
② RECORD（LLM なし = 決定論）＝ 複式簿記 + wallet 錨
      ・全 act を両側記帳（買い=cost, 勝ち=payout, 負け=$0, 手数料）
      ・append-only ledger。勝ちだけ記録は複式簿記上あり得ない
      ・毎 wake wallet on-chain 残高 → reconcile → ledger 合計 ≡ wallet delta
      ・真実は wallet。ledger は wallet への照合にすぎない
      ▼
③ VERIFY（2層に厳密分離）
   ┌ DETERMINISTIC（LLM なし・金の真実）───────────────────┐
   │  tx status 0x1 / balance delta / external:true inbound │
   │  「金が動いたか」だけを gate。Verifier's Law: on-chain │
   │   だけが客観・高速・スケーラブル・低ノイズ             │
   └────────────────────────────────────────────────────────┘
   ┌ AGENTIC（fresh-context 別 adversary・正直さの真実）────┐
   │  「report は ledger/tx と一致か」「空稼働/内部送金/mock │
   │   を稼ぎと偽ってないか」「戦略は健全か」               │
   │  被検証 loop の文脈を持たない別 spawn。blocking 0=PASS │
   └────────────────────────────────────────────────────────┘
      ▼  PASS のみ「稼いだ」確定 → BUILD(大脳) にフィードバック
```

**鉄則（BP）**:
1. 金の真実 = DETERMINISTIC(wallet)。**LLM に「稼いだか」を判定させない**。
2. 正直さの真実 = AGENTIC(fresh adversary)。**同一文脈 self-eval は原理的破綻**。
3. 2つを混同しない。
4. **simplify: 新フレームワーク不要。既存部品を繋ぐだけ。**

---

## 3. 現在地 vs 理想（内部監査 実測 2026-07-12）

| 層 | 理想 | 現状[V] | 一致 |
|---|---|---|---|
| EARN loop | 1 instance=1 loop 小脳 | agent-economy-loop(index.mjs)=free/glm-4.7 稼働 ✅。だが **pm-earner 別 cron が pm を二重稼働**（menu 迂回） | 🟡 重複1 |
| 脳の分離 | 稼ぐ=小脳/build=大脳 | earn=free ✅ / build(mainloop)=claude sonnet ✅ | 🟢 |
| BUILD 一本化 | build=1 loop | **既に1本**(claude build=mainloop のみ。founder-loop は決定論記録で claude でない、2026-07-12訂正) | 🟢 |
| RECORD 複式簿記 | 勝ちも負けも両側 | **pm は勝ちだけ記録、負け・買いコスト記録せず**（redeem.py:172「buy was never ledgered」） | 🔴 |
| RECORD wallet 錨 | 毎 wake reconcile | **HL は reconcile.py 毎 wake 配線済(手本)✅。pm は reconcile.mjs 作済だが worktree 置き去り＝本番未配線** | 🔴 pm |
| ledger 一意 | 1 instance=1 ledger | **founder(0x810f)の ledger が2パス・別 wallet(0xa3cdd4)混在、default 関数が誤パスを指す** | 🔴 |
| DETERMINISTIC 検証 | on-chain gate | isProfitable/record-earn.mjs/HL reconcile 稼働 ✅(pm だけ穴) | 🟢 |
| AGENTIC 検証 | fresh adversary | **reality-verifier は doc24 に設計3版、`.claude/agents/reality-verifier.md` 不在＝未実装** | 🔴 |

**「稼いでるか分からない」root-cause（監査確定）**:
1. pm が負け・買いを記録しない（勝ちだけ）→ ledger が嘘
2. founder の ledger が2つ・別 wallet 混在、default が誤方向 → 読む場所で答えが変わる
3. AGENTIC(reality-verifier)未実装 → 矛盾 ledger・fake-green を第三者が突き合わせられない

---

## 4. one-by-one 残 TODO（simplify = 既存部品を繋ぐだけ）

実行は VCSDD（mode: lean 可、フェーズ飛ばさない、adversary=Sonnet）。1つ完了→次。

| 順 | TODO | 内容 | done（検証可能） | 手本/部品 | 状態(2026-07-12) |
|---|---|---|---|---|---|
| **1** | ledger 一意化 | founder の earn-ledger を1パスに統一、混入 wallet(0xa3cdd4)行を隔離、`defaultEarnLedgerPath` を正パスへ | 1 instance=1 ledger、読む場所が一意 | 監査が正パス特定 | 🔄 builder(Sonnet) worktree ledger-uniqueness |
| **2** | pm に reconcile 配線 | worktree の reconcile.mjs を本番 merge、毎 wake 呼ぶ（HL と同形）。負け・買いが載る | pm でも ledger 合計 ≡ wallet delta | **HL reconcile.py が手本** | ⏸ #1 待ち(canonical パスに書くため) |
| **3** | earn loop 一本化 | pm-earner cron 廃止、pm を index.mjs earn-menu の skill に | claude-p の earn loop が1本、pm は menu 経由のみ | index.mjs 既存 | ⏸ #2 後(pm が損失記録できてから) |
| **4** | BUILD loop 一本化 | mainloop(6h)+founder-loop(30min) を build=1 loop に統合。実 launchd は触らず worktree に統合案+SWITCHOVER.md | 大脳 loop が1本、cron 重複解消 | 既存2スクリプト | 🔄 builder(Sonnet) worktree build-loop-unify(並列・独立) |
| **5** | AGENTIC 検証実装 | doc24 の reality-verifier を `.claude/agents/reality-verifier.md` 実装、self-fix/週次から fresh spawn。DETERMINISTIC と分離 | fresh adversary が report vs on-chain 突合 PASS/FAIL | doc24 + VCSDD adversary 流用 | 🔄 builder(Sonnet) worktree reality-verifier(並列・独立) |
| **6** | 1 wake 自律実行 own-eyes | 小脳 loop を1回、wallet delta = ledger delta を私が on-chain 確認 | 記録と真実が一致 | — | ⏸ #1-3 後 |
| **7** | 実 external:true が出るまで回す | 小脳が実際に稼ぐ（唯一の gate） | wallet が実 tx で増える | — | ⏸ 最後 |

**依存グラフ**: `1 → 2 → 3 → 6 → 7`（earn/記録の直列）。`4`(build loop) と `5`(agentic 検証)は独立ファイル群 → **並列で先行可**。各 builder は worktree 隔離・merge せず戻す → 親が fresh adversary(Sonnet) review → own-eyes → merge。
**並列実行中(2026-07-12)**: #1(ledger paths) / #4(build scripts) / #5(.claude/agents) を3 builder 同時。衝突なし（触るファイル群が完全に分離）。
**核心**: 足りないのは新規でなく「記録を正す(複式・wallet 錨・1本化) + 検証を2層に分ける(既存 DETERMINISTIC + 未実装 AGENTIC を実装)」。部品は全部ある。繋ぐだけ。

---

## 出典（BP、一次引用）
- ReAct/1-loop-skill交換: Anthropic augmented-LLM / loopengineering.run / Oracle Developers "AI agent loop"
- earn と build を分ける(generator/evaluator): loopengineering.run / MindStudio "Loop vs Harness Engineering"
- 複式簿記: Medium "double-entry ledger" / freqtrade SQL cheatsheet(手数料 open/close 両側)
- wallet=真実/reconciliation: Phemex "autonomous on-chain trading" / triple-entry accounting
- DETERMINISTIC=Verifier's Law: Jason Wei "Asymmetry of Verification" / x402 settlement
- AGENTIC=fresh adversary: arXiv 2606.28050(self-eval bias) / Agent-as-a-Judge arXiv 2508.02994 / channel.tel "12 LLM judge biases"
- 混同の失敗: MindStudio "deterministic + agentic nodes"
- 内部監査 実測: 本 session 2026-07-12（redeem.py:172 / HL reconcile.py 配線 / founder 2-ledger / reality-verifier 不在）
