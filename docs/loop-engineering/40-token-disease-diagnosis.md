# 40 — トークン浪費の診断書（2026-07-13、全て実測。推測は明記）

**主訴**: 「1分で1%」= 200k窓が約2,000 tok/分で埋まる。1日 403.7M tok / $240.61。
**診断法**: 症状（cost）でなく病巣（何が context を占めるか）を、ファイル実測とツール実測で切り分ける。

---

## 0. バイタル（実測・ccusage 2026-07-13）
| 指標 | 値 | 意味 |
|---|---|---|
| 総トークン | 403.7M | — |
| **cache read** | **99%** | 毎ターン同じ文脈を読み直す分 |
| **output** | **0.6%** | 実際に生成した分 |
**確定所見**: 課金 ≒ **文脈の大きさ × ターン数**。**書いた量ではなく、毎ターン背負う荷物**が金を食う。
病気は「出力が多い」ではなく「**文脈が重い × セッションが長い**」。

---

## 2つの病気を分けて診る（混同が今までの誤診の元）

## 病気A: 床が高い（固定・毎ターン課金）— 実測 ≈ 75k tok/ターン
| 病巣 | 実測 tok/ターン | 測り方 |
|---|---|---|
| **project `.claude/skills`(258個)** | **22,652** | SKILL.md の name+desc を実集計 |
| **personal `~/.claude/skills`(171個)** | **17,562** | 同上 |
| 有効プラグイン12個(157 skill) | 12,867 | 同上 |
| **MEMORY.md(365件の見出し)** | **6,478** | 25,912 bytes、★毎ターン全文ロード★ |
| CLAUDE.md(global+project) | ~7,200 | 29KB |
| rules/ | ~8,700 | 35KB |
| **床 合計** | **≈ 75,000** | × 500ターン = 37.5M tok |

### 誤診の記録（claude-p、2026-07-13。同じ罪を3回）
- ★誤診★「`ecc`(790 skills) が最大の荷物」と3回 Dais に報告 → **実測で `ecc` は enabledPlugins に無い＝system prompt に載っていない＝0 tok**。
  ディスク上の SKILL.md を数えただけで断定した。**有効化されているかを見れば5秒で分かった**。
  → memory `feedback_assume_i_am_wrong_search_before_asserting` を焼いた直後に再犯。

### 真犯人（実測で確定）
1. **我々自身が作った skill 429個（project 258 + personal 171）= 40,214 tok/ターン**。プラグインより遥かに重い。
2. **2つの skills フォルダを両方ロードしている（重複111個）**。しかも **中身は別実体**（agent-memory/asc-cli-usage を diff → differ）。
   = 同じ名前の skill が2バージョン、両方 system prompt に載っている。**片方は要らない**。
   - project `.claude/skills` = git 管理下(608 files)、repo の正本
   - personal `~/.claude/skills` = git 管理外、ローカルにだけ在る野良コピー
3. **MEMORY.md を毎ターン全文（6.5k tok）preload している**。365件の見出しの大半はそのターンと無関係。
   → 正しくは「必要時に検索して引く（retrieval）」。preload をやめれば −6.5k/ターン。

## 病気B: 膨張（会話履歴・増え続ける）= 「1分で1%」の直接原因
**claude-p が会話に貼る生出力**（ファイル全読み・コマンド出力・ccusage の表）。
**一度入れたら、そのセッションの残り全ターンで再課金**（1回 15k tok が 30ターン残れば 450k tok）。
- ★これはツールでは直らない。claude-p の規律の問題★
- 今日 claude-p は ccusage の表・grep 生出力・ファイル全読みを何度も会話に貼った＝自傷

---

## ウイルス（根本原因は1つ）
**「実測せずに断定する」＝ 病気A の誤診も、病気B の自傷も、二重 spawn も、spec 破りも、全部これ。**
Dais は毎回正しく、claude-p の推測が毎回外れる（memory `feedback_assume_i_am_wrong_search_before_asserting`）。
「覚えていられる/分かっている」という思い上がりが、記録を怠らせ、実測を飛ばさせる。

---

## 処方（効果を実測で確認できる形。推定と実測を分ける）
| # | 処置 | 病巣 | 削減 | 効果測定 |
|---|---|---|---|---|
| X-2e-1 | **2つの skills フォルダを1つに統合**（personal の野良を消し project 正本に寄せる。重複111解消）| A-2 | **推定 −15〜18k** | 統合後 `/context` |
| X-2e-2 | **未使用 skill を無効化**（直近使用0を退避、削除でなく移動でいつでも戻す）| A-1 | **推定 −20〜30k** | 同上 |
| X-2e-3 | **MEMORY.md preload をやめ claude-mem(retrieval) に移す**（`thedotmack/claude-mem` 86.9k★、SQLite FTS5、progressive disclosure、OpenClaw対応。README実確認）| A-3 | **推定 −6.5k** | 同上 |
| X-2b | **claude-crusts**(83★、offline)で重複tool schema/肥大CLAUDE.md/未使用MCPを検出削減 | A | 推定 −5〜10k | analyze 実出力 |
| X-2c | **cjk-token-reducer**(51★)で日本語2.12倍を削る | A（床全部）| 推定 35-50% | 導入後実測 |
| X-2d | **SessionStart hook で床を実測→閾値超過で停止** + ccusage日報(09:15) | 再発防止 | — | hook 発火 |
| （規律）| 探索=subagentに投げ結論だけ受取る/生出力を貼らない/context60%でhandover | B | — | セッション毎 |
| ~~X-2a~~ | ~~ecc削除~~ | — | **0 tok**（無効なので）| ディスク72MB回収のみ |

### ★handover が必須の理由（再掲・重要）★
plugin/skill/memory の変更は **system prompt が起動時に組まれるため、再起動しないと反映されない**。
→ **今のセッションで掃除 → handover → 新セッションで `/context` の before/after 実測**、が唯一正しい順序。
今のセッションでいくら消しても、このセッションは最後まで重いまま。

---

## ★実データによる大訂正（2026-07-13、claude-crusts で実セッション測定）★
`npx claude-crusts@latest analyze/waste/optimize` を今セッション(765msg)に実行した実データが、
上の**推定を複数否定**した。claude-p はまた実測せず断定していた（ecc・skills・MEMORY で計4回）。

| claude-p が断定 | claude-crusts の実測 |
|---|---|
| 「skill説明が53k tok/ターン」 | 実際の context 内訳 = **Tools 56.8%(37,242) / Conversation 39.9%(26,141) / System 3.3%(2,133) / State-Memory 0.0%** |
| 「MEMORY.md が6.5k tok/ターン」 | **State/Memory = 0 tokens**（この1M Opusモデルには載っていない） |
| 「CLAUDE.md が7.2k tok」 | **実測 1,993 tok**（削減可能は -493 のみ） |
| 「床が最大の問題」 | **cache read 94.8%** が真の負荷。内訳の主犯は Tool schema(42 loaded/13 used=9,055tok) と **会話に貼った生出力(26k)** |

**確定した真犯人（実測）**:
1. **Tool schema 42個中29個未使用**（作業に要る組込ツール中心なので大半は削れない）
2. **会話 39.9% = claude-p が貼った生出力**（病気B。「1分で1%」の本体。1M窓の1%=10k tok）
3. モデルが **Opus 4.8(1M)** に切替済（`/model`）＝ Fable より高単価

**実際に効く処置（claude-crusts が指したもの）**:
- 死んだ MCP `x402scan`/`stitch` を settings から削除（schema節約0だが dead config 一掃）→ ✅実施
- CLAUDE.md 1,993→<1,500 tok（-493、参照系を CLAUDE.local.md へ）→ 実施中
- **最大の効き = claude-p が生出力を貼らない規律**（探索は subagent／貼らない／60%で handover）。ツールでなく規律
- ~~cjk-token-reducer~~ = **却下**（翻訳が非可逆＋日本語プロンプトをGoogleに外部送信＋床に効かない。README実読で判明）
- skills統合/退避(X-2e-1/2) は害はないが、**skill数はclaude-crustsの内訳では主犯でなかった**（優先順位を実データで決めるべきだった）

## 効果の確定方法（盛らない）
上の推定の多くは claude-crusts で否定された。**確定値は claude-crusts analyze の実測 or 新セッションの `/context`**。
処置ごとに measure → 効いてなければ戻す（memory `feedback_no_flipflop_run_before_concluding`）。
**教訓: 診断は最初に claude-crusts を回すべきだった。claude-p は推測で優先順位を決め、実データが毎回否定した。**
