# PLAN #37 MONEY-LINE (B3) — landing click 代理 attribution の配線

発注: Fable(planner) → Sol(Codex builder, flow B)。2026-07-19。
前提 recon 済: capafy API は sales/recentSales/rating のみで UTM/click/per-listing 粒度を返さない。landing は静的 JS ゼロ（CSP default-src 'none'）。click 計測は完全未実装。`.netlify/netlify.toml` の [functions] は空で待機。SKILL.md が参照する x_attribution.py 等は実在しない（幻参照）。site publish dir = capafy-marketing/site。

## Planner 決定（曲げるな）
- 代理指標 = **redirect click counter**: landing の各 card link を同 site 内 `/go/<agent_id>` に変え、Netlify Function が click を数えて capafy.ai へ 302。JS/beacon は使わない（CSP 不変更）。
- 計数 store = **Netlify Blobs**（無料枠、外部 SaaS/credential 追加なし）。
- 取得線 = 既存 daily pass に統合: `ig_metrics.py` 実行後に click counts を Function の read endpoint から pull し `~/.openclaw/state/capafy-attribution.jsonl` へ追記（date, agent_id, clicks, sales snapshot join）。
- SKILL.md の幻参照（x_attribution.py / x_post.py / x_metrics.py）は削除または「未実装」明記に是正。

## 要件（MUST）
R1: `site/netlify/functions/go.mjs`（または netlify.toml functions dir 指定）— `/go/:agent_id` で Blobs counter increment → 302 `https://capafy.ai/agent/<agent_id>?utm_source=instagram_bio&utm_medium=bio_link&utm_campaign=capafy_marketing`。未知 agent_id は count せず capafy.ai トップへ 302。
R2: read endpoint `/go-stats`（JSON: {agent_id: clicks}）。書込系 method は 405。
R3: `build_landing.py` の card link を `/go/<agent_id>` に変更（UTM は Function 側で付与）。netlify.toml に functions dir + `/go/*` redirect 設定。
R4: `scripts/pull_attribution.py` 新規 — `/go-stats` を fetch し capafy sales snapshot（既存 capafy_http 経由 GET /agent/agents）と join、`~/.openclaw/state/capafy-attribution.jsonl` へ1行/日 追記。daily script の ig_metrics 行の直後に non-fatal で呼び出し追加。
R5: SKILL.md 幻参照の是正。
R6: テスト: pytest（Function は node なので logic を薄く、python 側 pull/join を mock urllib でテスト + build_landing の /go/ link 生成テスト）。deploy は Fable が行う（netlify deploy は Sol 禁止 — git 同様 Fable 担当）。実 IG/実 deploy 副作用ゼロ。
R7: worktree `/Users/anicca/anicca/.worktrees/money-line-37/`（Fable 作成済）。git/netlify コマンド禁止。

## Done
1. pytest green（Sol 実行）2. build_landing.py 出力 html の link が /go/ 形式（fixture で確認）3. agmsg DONE + pytest 要約 + 変更 file 一覧。
質問: send.sh capafy sol-codex fable-main。
