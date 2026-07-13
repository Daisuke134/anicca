# crawl4ai — Web スクレイプの既定ツール

2026-07-13 に Mac mini (`anicca-mac-mini-1`) で導入・実証済み。

## インストール先

- venv: `~/.venvs/crawl4ai`（Homebrew python が externally-managed のため venv 必須）
- crawl4ai バージョン: `0.9.1`
- CLI symlink: `~/.local/bin/crwl` → `~/.venvs/crawl4ai/bin/crwl`（`~/.local/bin` は既に PATH 済みなので新しい shell でもそのまま `crwl` が通る）
- browser: `crawl4ai-setup` が Playwright + Patchright 用に Chromium を `~/Library/Caches/ms-playwright/` に別途ダウンロード済み（既存の CloakBrowser `~/.cloak` プロファイルとは完全に独立、一切触っていない）

## 実行コマンド例

### 1. 単発 markdown 抽出
```bash
crwl https://docs.anthropic.com/en/docs/claude-code/settings -o markdown
```
2026-07-13 に実行し、実際のページ本文（ナビゲーション込み、1139行）が markdown で出力されることを確認済み。

### 2. deep crawl（サイト内複数ページを BFS で収集）
```bash
crwl <start-url> --deep-crawl bfs --max-pages 20 -o markdown
```
`--max-pages` で上限を必ず指定する（無指定だと際限なく辿る）。

### 3. LLM 抽出（`-q "質問"`）
```bash
crwl <url> -q "このページの要点を3行で" -c "provider=ollama/llama3"
```
`-q` は内部で `setup_llm_config()` を呼び、`~/.crawl4ai/global.yml` に `DEFAULT_LLM_PROVIDER` が未設定だと**対話プロンプトで provider/API key を聞く**（非対話シェルでは詰まる）。
**API key 不要にする方法**: provider に `ollama/<model名>`（例 `ollama/llama3`）を指定すれば token 入力をスキップできる（コード上 `provider.startswith("ollama/")` の場合のみ token プロンプトを飛ばす仕様、`cli.py:72`）。本 Mac には `ollama` バイナリは入っているが、ディスク残り約12GBのためモデル pull はまだ実行・未検証。使う前に `ollama pull llama3` 等でモデルを落とし、`ollama serve` を起動しておくこと。
API key ありの provider（openai 等）を使うなら `crwl config` で `DEFAULT_LLM_PROVIDER` を一度設定すれば以降は対話なしで通る。

## 既知の注意点

- `crwl --version` は存在しない（`crawl4ai.__version__` を python 側で見る）。
- `-o markdown` の他に `md-fit` / `markdown-fit`（fit markdown = ノイズ除去版）がある。
- ディスク: venv 706MB + playwright/patchright chromium 系で ~1GB。実行前後で `df -h /` を確認する運用にする。
