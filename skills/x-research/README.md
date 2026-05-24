# x-research（OpenClaw / Anicca 用）

**中身はコピーしない。VPS で公式リポを clone する。**

X (Twitter) 公式 API で生ツイート・スレッドを取るスキル。[rohunvora/x-research-skill](https://github.com/rohunvora/x-research-skill) がそのまま OpenClaw 対応。

## セットアップ（VPS で実行）

```bash
# trend-hunter が参照する ~/.openclaw/skills に clone
mkdir -p ~/.openclaw/skills
cd ~/.openclaw/skills
git clone https://github.com/rohunvora/x-research-skill.git x-research
cd x-research && bun install
```

1. **Bun** が入っていなければ入れる:
   ```bash
   curl -fsSL https://bun.sh/install | bash
   ```

2. **X API Bearer Token** を設定:
   - [X Developer Portal](https://developer.x.com/) で取得。
   - **環境変数はすべて `~/.openclaw/.env` に書く。** ここに:
     ```
     X_BEARER_TOKEN=your-token-here
     ```
   コミット・ログに出さないこと。

3. **openclaw.json** の `skills.entries` に `x-research` を追加し、gateway を再起動。

**X_BEARER_TOKEN が無い場合:** x-research の X 検索は使えない。代わりに **Firecrawl** で Web スクレイピング（例: Oliver & Larry 等の URL を指定して取得）する。`~/.openclaw/.env` に `FIRECRAWL_API_KEY` を書いておけば OpenClaw の web fetch で Firecrawl が使える。anicca-auto-development の「検索」は Firecrawl のみで深掘り可能。

詳細は公式: [rohunvora/x-research-skill](https://github.com/rohunvora/x-research-skill)

## Anicca での使い方

- 検索・スレッド・プロフィールはすべて `skills/x-research` 内で `bun run x-search.ts ...`。
- 開発の「深いネタ」取り → 結果を anicca-auto-development の報告・spec に渡す。  
このリポの `openclaw-skills/x-research/SKILL.md` は Anicca 向けの「いつ使うか・例」だけ。CLI の全オプションは clone したリポの README / SKILL を参照。
