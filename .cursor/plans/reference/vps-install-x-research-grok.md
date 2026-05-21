# VPS インストール手順: x-research-skills (grok-context-research)

**目的:** Anicca VPS に https://github.com/HayattiQ/x-research-skills をインストールし、OpenClaw から `grok-context-research` として使えるようにする。

**前提:** VPS に SSH できること（例: `ssh anicca@46.225.70.241`）。本手順は **VPS 上で実行**する。

---

## 1. クローン

```bash
mkdir -p /home/anicca/.openclaw/skills
cd /home/anicca/.openclaw/skills
# 既に x-research-grok がある場合は pull、なければ clone
if [ -d x-research-grok ]; then
  cd x-research-grok && git pull && cd ..
else
  git clone https://github.com/HayattiQ/x-research-skills.git x-research-grok
fi
```

---

## 2. 依存（tsx）

```bash
cd /home/anicca/.openclaw/skills/x-research-grok
# package.json が無ければ初期化
if [ ! -f package.json ]; then
  npm init -y
fi
npm install tsx
```

---

## 3. 環境変数

`/home/anicca/.openclaw/.env` に以下があることを確認する。無ければ追加。

```bash
# 確認
grep -q '^XAI_API_KEY=' /home/anicca/.openclaw/.env && echo "XAI_API_KEY exists" || echo "XAI_API_KEY missing"
```

無い場合は手動で追加（値は伏せる）:

```
XAI_API_KEY=...
```

任意で:

```
XAI_BASE_URL=https://api.x.ai
XAI_MODEL=grok-4-1-fast-reasoning
```

---

## 4. 動作確認

```bash
cd /home/anicca/.openclaw/skills/x-research-grok
export $(grep -v '^#' /home/anicca/.openclaw/.env | xargs)
npx tsx scripts/grok_context_research.ts --topic "test" --locale ja
```

成功時は `data/context-research/` に `.md` / `.json` / `.txt` が生成される。

---

## 5. OpenClaw に登録

`/home/anicca/.openclaw/openclaw.json` の `skills.entries` に以下を追加する（既存キーと重ねずに）。

```json
"grok-context-research": { "enabled": true }
```

編集例（jq で追加）:

```bash
# バックアップ
cp /home/anicca/.openclaw/openclaw.json /home/anicca/.openclaw/openclaw.json.bak
# skills.entries に grok-context-research を追加（構造は既存に合わせる）
# 手動編集する場合は openclaw.json を開き "grok-context-research": { "enabled": true } を entries に追加
```

Gateway を再起動して設定を読み込ませる（必要に応じて）:

```bash
systemctl --user restart openclaw-gateway.service || true
```

---

## 6. 実行コマンド（運用）

Anicca が「今日の X コンテキストを取れ」と指示したときの実行例:

```bash
cd /home/anicca/.openclaw/skills/x-research-grok
export $(grep -v '^#' /home/anicca/.openclaw/.env | xargs)
npx tsx scripts/grok_context_research.ts --topic "Anicca 習慣化アプリと OpenClaw" --locale ja
```

出力は `x-research-grok/data/context-research/YYYYMMDD_HHMMSSZ_context.md`。この .md を検索の軸・#metrics 要約・spec のネタに使う。

---

## 受け入れチェック

| # | 確認項目 |
|---|----------|
| 1 | `/home/anicca/.openclaw/skills/x-research-grok` に clone 済み |
| 2 | `npm install tsx` 済みで `npx tsx scripts/grok_context_research.ts --topic "test" --locale ja` で .md が生成される |
| 3 | `openclaw.json` の `skills.entries` に `grok-context-research` が追加されている |

---

**参照:** `.cursor/plans/reference/grok-context-research-spec.md`
