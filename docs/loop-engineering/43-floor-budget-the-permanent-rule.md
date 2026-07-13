# 43 — 床の予算（恒久ルール。これで token 事故のサイクルを終わらせる）

doc 40=診断 / doc 41=1回目の掃除 / doc 42=真因（床 × API 呼び出し回数）/ **本書=二度と太らせないための恒久ルール**。

## 0. なぜルールが要るか

過去に一度、同じ掃除をやった。そして**また太った**。理由は簡単で、掃除は「状態」を直すが、**太らせる力**（新しい CC が便利のために CLAUDE.md / memory / skill を足す）は毎日働き続けるから。
**規律を人（AI）の善意に置いた時点で負ける。機械に測らせる。**

## 1. 物理（1行）

> **課金 = 床 × API 呼び出し回数。tool 1回 = API 1回 = 床を丸ごと1回払う。**
> Dais の「1ターン」は、私の側では 10〜100 回の API 呼び出し。だから床は「起動時に1回だけ」の費用ではなく、**全作業に掛かる税**。

実測（2026-07-13、session a39c88c0）: 108 API 呼び出し / 1回あたり平均 122,493 tok を再読込 / **$12.49**。うち床 51,004 tok は全呼び出しに掛かっていた。

## 2. 予算（超えたら赤。足す前に削る）

| 項目 | 予算 | 測り方 |
|---|---|---|
| **床（実測）** | **≤ 25,000 tok** | セッション最初の API 呼び出しの `input + cache_creation` |
| 我々の markdown（CLAUDE.md 群 + MEMORY.md + 無条件 rules） | ≤ 12,000 tok | bytes ÷ 2.2 |
| skill description（model 呼び出し可能なもの） | ≤ 6,000 tok | name+description の合計 |

**機械強制**: `~/.claude/scripts/floor-guard.py` を **SessionStart hook** が毎回実行し、超過したら叫ぶ。
手動: `python3 ~/.claude/scripts/floor-guard.py --parts`（内訳と、重い skill の TOP10 が出る）。

## 3. 何かを足したくなった時の手順（HARD）

1. **まず `floor-guard.py` を実行する。** 予算に空きが無ければ、**足す前に同量を削る**。
2. 置き場所を、この順で選ぶ（上が安い）:

| 置き場所 | 床に載るか | いつ使うか |
|---|---|---|
| **skill**（`SKILL.md`） | **description の1行だけ**（呼ばれた時だけ本体が載る） | 手順・runbook・専門知識 = **既定はここ** |
| **skill + `disable-model-invocation: true`** | **載らない（完全に消える）** | `/name` で明示的にしか呼ばないもの |
| **`.claude/rules/*.md` + `paths:` frontmatter** | 該当ファイルを触った時だけ | 言語/ディレクトリ固有の規則（iOS gotcha 等） |
| **memory ファイル** | 索引の1行だけ | 恒久事実・人格・過去の罪 |
| **CLAUDE.md** | **常時・全 API 呼び出しに課金** | **毎回の意思決定に要る規則だけ**（precedence / no-human-loop / 検索優先 / 金の掟） |

3. **CLAUDE.md は 200行以下**（公式: "Aim to keep CLAUDE.md under 200 lines"）。
4. **`@import` で解決しようとするな。** 公式: "Splitting into @path imports helps organization but **does not reduce context**, since imported files load at launch." import 先も丸ごと床に載る。
5. **skill の description は1行**。120語書くな（それがそのまま床の税になる）。
6. **MCP は使うものだけ**。使わない server は `/mcp` で切る。CLI（`gh`/`aws`/`gcloud`）が有るならそっちを使う（per-tool listing が無い）。

## 4. 会話の中で床を太らせない（もう一つの税）

床は「毎回払う固定費」、会話は「払い続ける変動費」。**私が貼った生出力は、以降の全呼び出しで再課金される。**

- 探索は **subagent** に投げ、**結論だけ**受け取る（生ログを親の文脈に入れない）
- grep 全行 / full file read / 長い表 / 生の JSON を会話に貼らない
- context 100k または 100 呼び出しで **handover して畳む**
- 対話で **1M 窓を常用しない**（1M は「広い」のではなく auto-compact のブレーキが外れている）

## 5. 公式ソース（引用）

- `code.claude.com/docs/en/costs`: "Move instructions from CLAUDE.md to skills … Skills load on-demand only when invoked … **Aim to keep CLAUDE.md under 200 lines**." / "**Disable unused servers.**" / "Prefer CLI tools when available … they don't add any per-tool listing."
- `code.claude.com/docs/en/memory`: "Rules can be scoped to specific file paths … **only load into context when Claude works with matching files**." / "**Splitting into @path imports … does not reduce context, since imported files load at launch.**"
- `code.claude.com/docs/en/context-window`: "**Skills with `disable-model-invocation: true` are not in this list. They stay completely out of context** until you invoke them with `/name`." / "The cache is refreshed for no additional cost each time the cached content is used."

## 6. 2026-07-13 の手術結果（before → after）

| 項目 | before | after |
|---|---|---|
| markdown（CLAUDE.md 群 + MEMORY.md + rules） | 34,765 tok | **9,925 tok** |
| skill description | 8,849 tok | **5,179 tok** |
| MCP tool（Base/Calendar/Drive/Slack/Gmail/Mermaid） | 88 tool | **0** |
| **床（実測）** | **51,004 tok** | **次セッション起動時に実測する** |

★ 床は**起動時に焼き込まれる**。掃除したセッションでは絶対に変わらない（今日 b36c4b98 で実証: 掃除直後も 79,891 のまま、再起動して初めて 51,004 になった）。**証明は新セッションの1呼び出し目でしか取れない。**
