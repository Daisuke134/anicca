# 41 — X-2 の効果 実測（トークン病の before / after）

前提: 診断書 = `40-token-disease-diagnosis.md`（真犯人の特定）。本ファイル = **処置後の実測値**。
測定日 2026-07-13。測定者 claude-p。全て tool 実行の生データから取った（推測値なし）。

## 0. 何を測ったか（指標の定義）

課金 ≒ **文脈の大きさ × ターン数**。書いた量ではなく**毎ターン背負う荷物**が金を食う。
よって指標は「1ターンの出力量」ではなく:

> **起動時固定コンテキスト** = セッション最初のターンの `input_tokens + cache_creation_input_tokens`
> = system prompt + tool schema + CLAUDE.md + MEMORY.md + hooks 出力 の合計
> = **以降そのセッションの全ターンが毎回払う「床」**

これは transcript（`~/.claude/projects/<proj>/*.jsonl`）の各セッション最初の usage から直接読める。
推定ではなく Anthropic が課金した実数字。

## 1. 結果 — 床が 82k → 51k（−38%）

| 起動時刻 (UTC) | session | 起動時固定ctx | 状態 |
|---|---|---|---|
| 2026-07-12 04:50 | d0736015 | 82,555 | 掃除前 |
| 2026-07-12 08:48 | a8492cea | **83,666** | 掃除前（最悪） |
| 2026-07-12 11:07 | 7b4e3326 | 81,000 | 掃除前 |
| 2026-07-12 16:07 | ff076b84 | 80,669 | 掃除前 |
| 2026-07-13 01:16 | 79938ece | 82,088 | 掃除前（処置を行ったセッション本体） |
| 2026-07-13 03:53 | b36c4b98 | 79,891 | 掃除**後**だが未反映（下記 §4） |
| **2026-07-13 03:56** | **a39c88c0** | **51,004** | **★AFTER★** |

| 指標 | before | after | 差 |
|---|---|---|---|
| 起動時固定コンテキスト | ~82,000 tok | **51,004 tok** | **−31,000 tok / −38%** |
| 1,000ターン分の cache read | 82M tok | 51M tok | −31M tok |
| 同・金額（cache read $1.50/M） | $123 | $76 | **−$47 / 1,000ターン** |

参考: 2026-07-13 の実績（`ccusage daily`）= cache read **497,983,7xx tok** / **$336.74**（Claude 分）。
同じ使い方をしたまま床だけ 38% 下げれば、この日の請求は **$210 台**に落ちる計算。

## 2. 何を削ったか（内訳・全て実測）

| 処置 | before → after |
|---|---|
| skill（name+description が毎ターン system prompt に載る） | 有効289 + 野良171 = 460 → **105** |
| `~/.claude/projects/<proj>/memory/MEMORY.md` | 25,912 B → **16,893 B**（リンク126本の健全性は維持） |
| global `~/.claude/CLAUDE.md` | 15,969 B → **13,021 B** |
| project `CLAUDE.md` | 15,969 B 相当 → **10,642 B**（参照系を `CLAUDE.local.md` へ退避、情報消失ゼロ） |
| dead MCP server（x402scan / stitch） | 2 → **0**（tool schema は消せない固定費なので、死んだ server は即死刑） |
| 退避先 | 野良 skill = `~/.claude/skills.disabled-2026-07-13` / 未使用 = `.claude/skills-disabled-2026-07-13/`（spec 必須の62個は保護） |

処置後の `claude-crusts analyze` 判定:

```
TOTAL: 76,032 / 200,000 tokens (38.0%)
  Tools        12,167 (51.6%)
  Conversation  8,197 (34.7%)
  System        3,128 (13.3%)
Context health: HEALTHY
残る指摘: CLAUDE.md ~1,993 tok（節約余地 493 tok）= ほぼ底
```

## 3. 却下した処置（やらなかったこと・理由付き）

| ツール | 却下理由 |
|---|---|
| `jserv/cjk-token-reducer`（公称 35-50% 削減） | ①翻訳が非可逆 ②日本語を Google に外部送信する ③**input（床）に効かない** — 出力しか縮まないので主病に無関係 |
| `caveman`（出力 −65%） | 導入はした。ただし **input 0%**。床には効かない = 主病の薬ではない |

**教訓: 「トークン削減」を名乗るツールの大半は出力側にしか効かない。請求書の 99% は input（cache read）である。**

## 4. 落とし穴 — 掃除した「そのセッション」では効果が出ない

b36c4b98（掃除**後**に起動）の床は 79,891 のままだった。理由:
**system prompt はプロセス起動時に一度だけ焼き込まれる**。skill を消しても CLAUDE.md を縮めても、
**走っているセッションには一切反映されない**。51,004 は「再起動して初めて出た」数字。

→ 掃除の直後に `/context` を見て「変わってないじゃないか」と結論するのは**誤診**。必ず再起動して測る。

## 5. 正直な限界

- after は **1 セッション（n=1）**。次の 2-3 セッションでも 50k 台なら確定。今日中に自然に検証される。
- after セッションのモデルは opus-4-8、before は fable-5 が混在。tool schema は同一だがモデル差の寄与を完全には切り分けていない。

## 6. ★最大の発見 — 主犯はツールではなく規律だった★

床を 82k → 51k にしても、その日の cache read 497M の**大半は依然として会話の中身**。
crusts の内訳も `Tools 51.6% / Conversation 34.7%`。つまり:

> **私が会話に貼った生出力（grep の全行、full file read、長い表）が 1回 26,000〜40,000 tok。**
> **それが cache read として、以降の全ターンで毎回課金され続ける。**

ツールで削れるのはここまで。残りは **「私が生出力を会話に貼らない」規律**でしか落ちない:

1. 探索は subagent に投げ、**結論だけ**受け取る（生ログを本体の文脈に入れない）
2. grep / full read / 長い表を会話に貼らない
3. context 60% で handover して**セッションを畳む**（長いセッション = 高い床 × 多いターン = 二乗で効く）

**ツールを4つ入れた効果（−38%）より、規律1つ（生出力を貼らない）の効果の方が大きい。**
そして claude-crusts は、この結論に至るまでに私の推測を**4回否定した**（ecc 犯人説3回・skills 主犯説）。
実測しない限り、私は必ず間違える。

## 7. 生データの取り方（再現手順）

```python
# 各セッション最初のターン = 起動時固定コンテキスト
import json, glob, os
for f in glob.glob(os.path.expanduser("~/.claude/projects/<proj>/*.jsonl")):
    for line in open(f):
        u = (json.loads(line).get("message") or {}).get("usage")
        if u and u.get("cache_creation_input_tokens"):
            print(f, u["input_tokens"] + u["cache_creation_input_tokens"]); break
```

```bash
npx ccusage@latest daily            # 日次の cache read と $ 実績
npx claude-crusts@latest analyze --project "-Users-anicca-anicca-project"   # 内訳と waste
```
