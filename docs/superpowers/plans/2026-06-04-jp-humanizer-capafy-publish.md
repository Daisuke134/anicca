# JP Humanizer → Capafy Subscription Publish — Implementation Plan

> ⚠️⚠️ **SUPERSEDED / 履歴 (2026-06-04)** — 本plan は初期案（Run Online subscription・cap40）。**実際の公開は Download $9.99・agent_id 3332784488 として status=1(under review) まで提出済**。理由: サブスクは我々のAnthropic鍵hosting必須だが口座$0.01・auto-reload off で不成立→Dais判断で Download に切替（master spec §3 / BP §6）。**cap40 は赤字ラインで未使用**（黒字=週$5.99×cap8）。本plan の subscription手順・cap40・record追記は**実行しない**。残作業は listing確認のみ=task `[7]#15`。TDD/NG語同期・実runtime検証の教訓は capafy-autopublish spec([2]#10) に引き継ぐ。以下は記録として残置。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 自前のオリジナル日本語Humanizerスキルを新規作成し、Capafyに **Run Online subscription（$5.99/週・Free Trial・message cap）** Agentとして公開する（Phase A = 最初の金）。

**Architecture:** 純プロンプトskill（外部有料API無し=base LLMのみ=BP F2準拠）。HARD RULE #17/0.18に従い、第三者MIT作(SuguruKun_ai/humanizer-ja)の逐語流用はせず、勝ちパターン（Capafy "Humanizer: Smart Rewriting" $5.99/wk・"AI Paper Humanizer" $19.99/mo の命名/構造）をcloneして文言fresh生成。出力は「書き換え文＋変更点diff」=手に取れる成果物（BP F3）。

**Tech Stack:** Claude (Sonnet 4.6) base LLM / capafy-publisher skill (`packager.py`) / camofox or agent-browser（Capafy web checkpoint駆動・Google login keiodaisuke@gmail.com）

**配置先:** `~/.openclaw/skills/jp-humanizer-pro/`（runtime store = HARD RULE #0 worktree例外・main直編集可。我々も運用しつつ公開する）

**Capafy Agent Card（BP F4/F5テンプレ適用）:**
- title: `Japanese Humanizer — Strip the AI Tells, Sound Human`
- short: `Use when your Japanese draft still reads AI-written. For bloggers, marketers, students, and PR teams: paste the text, get a human-sounding rewrite plus a diff of every AI tell that was removed.`
- mode: subscription / cycle=week / cyclePrice=$5.99 / Free Trial=ON / cycleMaxMessageCount=40（粗利防衛 BP §5）

---

## File Structure

| ファイル | 責務 |
|---|---|
| `~/.openclaw/skills/jp-humanizer-pro/SKILL.md` | オリジナルのhumanize指示（自前パターン表＋出力フォーマット定義）。Capafy runtime=claudeが読む本体 |
| `~/.openclaw/skills/jp-humanizer-pro/README.md` | Agent Card detailed description元（`# Title→What it does→出力例`） |
| `~/.openclaw/skills/jp-humanizer-pro/LICENSE` | 我々のMIT（自前著作・第三者帰属無し） |
| `~/.openclaw/skills/jp-humanizer-pro/test/sample_ai_ja.txt` | 検証用AIくさい日本語サンプル |
| `~/.openclaw/skills/jp-humanizer-pro/test/ng_phrases.txt` | 0件であるべきNG語リスト（検証アサーション） |
| `~/.openclaw/skills/jp-humanizer-pro/test/verify.sh` | サンプルにskillを適用→NG語0件をassertする自己検証 |

---

## Task 1: オリジナルSKILL.md を作成（fresh生成・逐語流用禁止）

**Files:**
- Create: `~/.openclaw/skills/jp-humanizer-pro/SKILL.md`

- [ ] **Step 1: skillディレクトリ作成**

Run:
```bash
mkdir -p ~/.openclaw/skills/jp-humanizer-pro/test
```
Expected: exit 0

- [ ] **Step 2: SKILL.md を自前の文言で執筆**

要件（全てMUST）:
- frontmatter: `name: jp-humanizer-pro` / `description`（"Use when..."形）/ `version: 1.0.0` / `author: Anicca` / `license: MIT`
- 本文: 我々独自の言い回しで、最低15のAIっぽさパターンを「NG→具体的な直し方」表で定義（SuguruKun版の例文・表現を写さない。概念は公知=WikiProject AI Cleanup由来でOKだが、例文・説明文は新規に書く）
- **出力フォーマット定義（BP F3=成果物）**: ①書き換え後の全文 ②`## 変更点` セクションで「除去したAI tell」を箇条書きdiff
- recursive-improver的な自己採点1パス（出力前にNG語残存をself-check）を指示に含める

実行: Write tool で SKILL.md を作成（内容は実行時に執筆）。

- [ ] **Step 3: humanizer skillとして triggerが立つか確認**

Run:
```bash
head -8 ~/.openclaw/skills/jp-humanizer-pro/SKILL.md
grep -c "NG" ~/.openclaw/skills/jp-humanizer-pro/SKILL.md
```
Expected: frontmatter表示 + NGパターン15件以上（grep count ≥ 15）

- [ ] **Step 4: 逐語流用が無いことを検証（IP安全）**

Run:
```bash
# SuguruKun版の特徴的例文が混入していないか
grep -F "申請処理が3日から4時間" ~/.openclaw/skills/jp-humanizer-pro/SKILL.md; echo "leak_check_exit=$?"
diff <(sort ~/anicca-project/.agents/skills/humanizer-ja/SKILL.md) <(sort ~/.openclaw/skills/jp-humanizer-pro/SKILL.md) | grep -c '^>'
```
Expected: `leak_check_exit=1`（該当なし=流用なし）。diff差分が大きい（ほぼ別物）

- [ ] **Step 5: Commit**

```bash
cd ~/.openclaw && git add skills/jp-humanizer-pro/SKILL.md && git commit -m "feat(jp-humanizer-pro): original JA humanizer skill for Capafy" 2>&1 | tail -2
```

---

## Task 2: 検証サンプル + 自己検証スクリプト（成果物の正しさ証明）

**Files:**
- Create: `~/.openclaw/skills/jp-humanizer-pro/test/sample_ai_ja.txt`
- Create: `~/.openclaw/skills/jp-humanizer-pro/test/ng_phrases.txt`
- Create: `~/.openclaw/skills/jp-humanizer-pro/test/verify.sh`

- [ ] **Step 1: AIくさいサンプル文を作成（RED素材）**

Write `sample_ai_ja.txt`（AI tellを意図的に多数含む段落・200-300字）。例: 「浮き彫りにしており」「今後の展開が注目されます」「多面的な」「〜ではないでしょうか」等を散りばめる。

- [ ] **Step 2: NG語リスト作成（アサーション定義）**

Write `ng_phrases.txt`（1行1NG語。SKILL.mdのNG表と一致させる）:
```
浮き彫りにしており
今後の展開が注目されます
多面的な
注目に値する
ではないでしょうか
重要な示唆を与えている
```

- [ ] **Step 3: verify.sh 作成（適用後NG語0件をassert）**

```bash
cat > ~/.openclaw/skills/jp-humanizer-pro/test/verify.sh <<'SH'
#!/usr/bin/env bash
# 使い方: humanize出力を /tmp/out.txt に置いてから実行
set -euo pipefail
OUT="${1:-/tmp/out.txt}"
NG=~/.openclaw/skills/jp-humanizer-pro/test/ng_phrases.txt
fail=0
while IFS= read -r p; do
  [ -z "$p" ] && continue
  if grep -qF "$p" "$OUT"; then echo "NG REMAINS: $p"; fail=1; fi
done < "$NG"
if [ "$fail" -eq 0 ]; then echo "PASS: 0 NG phrases"; else echo "FAIL"; exit 1; fi
SH
chmod +x ~/.openclaw/skills/jp-humanizer-pro/test/verify.sh
```

- [ ] **Step 4: RED確認（生サンプルはNG語が残る=テストが効く証明）**

Run:
```bash
cp ~/.openclaw/skills/jp-humanizer-pro/test/sample_ai_ja.txt /tmp/out.txt
bash ~/.openclaw/skills/jp-humanizer-pro/test/verify.sh /tmp/out.txt; echo "exit=$?"
```
Expected: `NG REMAINS: ...` 複数行 + `FAIL` + `exit=1`（生サンプルは落ちる=検証が機能）

- [ ] **Step 5: GREEN確認（skill適用後の出力はNG語0件）**

SKILL.mdの指示に従い、自分（Claude）が `sample_ai_ja.txt` をhumanizeして `/tmp/out.txt` に保存 → 再検証。
Run:
```bash
bash ~/.openclaw/skills/jp-humanizer-pro/test/verify.sh /tmp/out.txt; echo "exit=$?"
```
Expected: `PASS: 0 NG phrases` + `exit=0`。落ちたらSKILL.mdのパターン/出力指示を修正して再実行（systematic-debugging）。

- [ ] **Step 6: Commit**

```bash
cd ~/.openclaw && git add skills/jp-humanizer-pro/test && git commit -m "test(jp-humanizer-pro): self-verify harness (NG-phrase=0 gate)" 2>&1 | tail -2
```

---

## Task 3: README + LICENSE + Agent Card文面（BPテンプレ）

**Files:**
- Create: `~/.openclaw/skills/jp-humanizer-pro/README.md`
- Create: `~/.openclaw/skills/jp-humanizer-pro/LICENSE`

- [ ] **Step 1: LICENSE（自前MIT・Anicca著作）**

Write standard MIT, `Copyright (c) 2026 Anicca`.

- [ ] **Step 2: README.md（Agent Card detailed description元・BP F5構造）**

構造: `# Japanese Humanizer` → `## What it does`（誰向け→入力→出力）→ `## Example`（before/after の短い実例）→ `## How to use`（paste text → get rewrite + diff）。文言fresh。

- [ ] **Step 3: 検証（README構造）**

Run:
```bash
grep -E "^## (What it does|Example|How to use)" ~/.openclaw/skills/jp-humanizer-pro/README.md
```
Expected: 3セクション全て表示

- [ ] **Step 4: Commit**

```bash
cd ~/.openclaw && git add skills/jp-humanizer-pro/README.md skills/jp-humanizer-pro/LICENSE && git commit -m "docs(jp-humanizer-pro): README + MIT license" 2>&1 | tail -2
```

---

## Task 4: publish-init（subscriptionモードでファイル確認）

**Files:** none（CLI操作）

- [ ] **Step 1: publisher loginを確認**

Run:
```bash
cd ~/.openclaw/skills/capafy-publisher && python3 packager.py publish-list 2>&1 | head -30
```
Expected: 既存Agent一覧（4437197514含む）が返る = token有効。login errorなら `publish-login`（OTPはgog gmail自動read・ToS同意は自分で判断）

- [ ] **Step 2: publish-init 実行（単一skill指定）**

Run:
```bash
cd ~/.openclaw/skills/capafy-publisher && python3 packager.py publish-init \
  --env claude \
  --runtime-dir ~/.openclaw \
  --skill-dir ~/.openclaw/skills/jp-humanizer-pro 2>&1 | tee /tmp/pub_init.json
```
Expected: JSON に candidate(jp-humanizer-pro) + `review_url`（checkpoint 1）

- [ ] **Step 3: Web Checkpoint 1 を自分で駆動（no-human-loop）**

`review_url` を camofox/agent-browser で開く（Capafy = Google login keiodaisuke@gmail.com）。
- ファイル内容を確認（SKILL.md/README/LICENSE。test/ は除外でよい）
- **mode = Subscription（Run Online）を選択**
- 戻る

Run（確認）:
```bash
cd ~/.openclaw/skills/capafy-publisher && python3 packager.py publish-status 2>&1 | head -20
```
Expected: local stateにagent_id採番 + mode=subscription反映

---

## Task 5: publish-configure（secret scan・credential map）

- [ ] **Step 1: configure 実行（deep-scan付き=初回推奨）**

Run:
```bash
AID=$(python3 -c "import json;print(json.load(open('/tmp/pub_init.json')).get('agent_id',''))" 2>/dev/null)
cd ~/.openclaw/skills/capafy-publisher && python3 packager.py publish-configure --agent-id "$AID" --deep-scan 2>&1 | tee /tmp/pub_conf.json | head -40
```
Expected: 純プロンプトskillなので credential 検出 0。`needs_deep_scan` が返れば staging を補足scanし、無検出を確認後 `--deep-scan`無しで再実行。

- [ ] **Step 2: Web Checkpoint 2（credentials）**

`review_url` を開く。jp-humanizer-proは外部API/秘密無し → hosted credentials空で確認のみ。戻る。

- [ ] **Step 3: 検証**

Run:
```bash
cd ~/.openclaw/skills/capafy-publisher && python3 packager.py publish-status 2>&1 | grep -iE "configure|staged|secret|credential" | head
```
Expected: configure完了・credential 0件

---

## Task 6: publish-ship + 価格/Free Trial/cap設定 + submit

- [ ] **Step 1: ship 実行（package + upload）**

Run:
```bash
cd ~/.openclaw/skills/capafy-publisher && python3 packager.py publish-ship --agent-id "$AID" 2>&1 | tee /tmp/pub_ship.json | head -40
```
Expected: `status: shipped` + `review_url`（checkpoint 3）

- [ ] **Step 2: Web Checkpoint 3 を自分で駆動（価格設定＋submit）**

`review_url` を camofox/agent-browserで開く:
- billing: **Subscription / cycle=Weekly / price=$5.99**
- **Free Trial = ON**
- **message cap (cycleMaxMessageCount) = 40**（BP §5 粗利防衛）
- title/short/detailed を Agent Card フィールドへ貼付（本plan header の文面）
- **最終 Submit をclick**

- [ ] **Step 3: submit成立をverify（嘘禁止・0.12 verification gate）**

Run:
```bash
cd ~/.openclaw/skills/capafy-publisher && python3 packager.py publish-remote-status --agent-id "$AID" 2>&1 | head -20
```
Expected: `status:1`(under review) または `auditStatus:1/2`（審査中）。`status:0 & auditStatus:0` は draft=未submit → checkpoint3のSubmitを押し直す。**submit成立まで「公開した」と言わない**。

---

## Task 7: 公開成立の最終verify + 記録

- [ ] **Step 1: listing live を確認（審査通過後）**

Run:
```bash
cd ~/.openclaw/skills/capafy-publisher && python3 packager.py publish-remote-status --agent-id "$AID" 2>&1 | grep -iE "status|audit"
```
Expected: 最終的に `status:4`（listed）。審査中ならstatus:1のまま=次の手番でre-check。

- [ ] **Step 2: capafy-userで自分のlisting検索（買い手視点で実在確認）**

Run:
```bash
cd ~/Capafy-skills/capafy-user && CAPAFY_ACCESS_TOKEN="$(python3 -c "import json;print(json.load(open(__import__('os').path.expanduser('~/.openclaw/skills/capafy-publisher/config.json')))['access_token'])")" \
python3 - <<'PY'
import json,urllib.request,os
t=os.environ["CAPAFY_ACCESS_TOKEN"]
body=json.dumps({"query":"japanese humanizer ai tells","page":1,"pageSize":10}).encode()
r=urllib.request.Request("https://api.capafy.ai/agent/agents/search",data=body,method="POST",headers={"Authorization":f"Bearer {t}","Content-Type":"application/json"})
print(json.dumps(json.loads(urllib.request.urlopen(r).read())["data"]["list"],ensure_ascii=False,indent=1)[:800])
PY
```
Expected: 自分の `Japanese Humanizer — Strip the AI Tells` が検索結果に出る（listed後）

- [ ] **Step 3: BP docに実績を追記 + memory更新**

`2026-06-04-capafy-profit-playbook-BP.md` に「初公開実績: jp-humanizer-pro / agent_id / 価格 / 公開日」を追記commit。account-history的に記録。

---

## Self-Review

- **Spec coverage**: D1(per-skill rule)→subscription選択 ✓ / Phase A(clone勝ち型)→jp-humanizer ✓ / BP F2外部API無し ✓ F3成果物+diff ✓ F4/F5命名 ✓ F7価格$5.99/wk ✓ / HARD RULE #17逐語流用禁止→Task1 Step4で検証 ✓ / 0.12 verify gate→Task6 Step3 ✓
- **Placeholder scan**: SKILL.md/README本文は「実行時に執筆」と明記（純創作物のため逐語固定不可）だが、構造要件・検証アサーション・全CLIコマンドは具体 ✓
- **依存整合**: `$AID` は Task4 pub_init.json から取得しTask5-7で一貫使用 ✓ / verify.sh のNG語リストはSKILL.mdのNG表と一致させる（Task2 Step2）✓

---

## Open execution notes

- Capafy web checkpoint（mode/price/Free Trial/cap/submit）はCLIフラグでなくweb設定 → camofox/agent-browserで**自分で**駆動（HARD RULE #-2/#-1/#18: human-loop禁止）。実CAPTCHA描画時のみ例外。
- `--env claude_code`（runtime。`claude`は無効値だった＝実行時に判明し修正済）。
