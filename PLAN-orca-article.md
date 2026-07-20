# PLAN — Orca 記事執筆（lane A récit、codex Sol executor）

## 成果物

`docs/articles/2026-07-20-orca-phone-coding-jp.md` — 完成した記事 markdown 1 本。

- タイトル: `ノートPCを返却しました。今日からiPhoneだけでAI開発します`
- 副題: `Orca という Agent IDE で、スマホが自宅マシンのリモコンになる。セットアップと初日の正直な所感`
- 価格帯 ¥1,000 の explainer。無料部 ≈2,500 字（[1]〜[4] 末尾まで）、有料部 = [5][6][7]。

## 素材（全部読み込むこと。捏造禁止 — ここに無い事実は書かない）

1. カード（構成 [1]-[7] + Dais 生所感の原文）: `/Users/anicca/profitable-claude/skills/article-writer/topics/in-progress/orca-phone-coding-setup.md`
2. セットアップ実録（実測の正本）: `docs/reference/orca-mac-mini-mobile-setup.md`
3. リサーチ結果（競合地図・分類軸・Tailscale 検証・Orca 残量表示・Cmux）: `docs/articles/2026-07-20-orca-phone-coding-research.md`（これが [2] と [6] の唯一の材料）

## 不変条件（破ったら FAIL）

- **lane A récit**: Dais 一人称（「私」）。verdict box（[0] 概要ブロック）無し、冒頭は [1] フックから。アニッチャ CTA 無し。Fable/Sol モデル分業の話は一切入れない。
- 所感ブロック [5] はカードの引用 4 行をほぼ原文で使う。ただし「（ターミナルはこちらがすごくわかりにくかった）」の一文は指示対象が曖昧なので**落とす**。
- `##` は章タイトルのみ（7 個前後）。`###` は 1 個も使わない。サブポイントは **太字**。
- 全角ダッシュ（— ― ──）を本文に 1 個も使わない。命題型 H2（「AIは世界を変える」形の断定見出し）禁止。名詞句 or 個人の判断形（「〜が一番…だった」）のみ。
- ですます調。自然な日本語。「いかがでしたでしょうか」等のスロップ定型禁止。記事が記事自身について語る文（「この記事でわかること」等）禁止。
- 数値・事実は素材 1-3 にあるものだけ。リサーチ MD に「未確認」とある事項は断定しない（書くなら「未確認」と明示 or 落とす）。
- 各章 spine 1 文で言えること。図が要る章: [3] に mermaid 1 枚（```mermaid、flowchart TD、**6 node 以下の縦 chain**、subgraph 禁止、ラベル短く）。[2] と [6] に markdown 比較表 各 1 枚（列は 4 列以下、セル短く）。
- 記事末に `## 出典` 1 ブロック（本文中の inline 出典禁止）。リサーチ MD と カード sources の実 URL のみ列挙。
- 構成: [1] フック（MacBook 返却、手元は iPhone だけ）/ [2] 選択肢の地図（リサーチの分類軸で。表）/ [3] Orca とは（mermaid）/ [4] セットアップ実録（brew 罠・Tailscale・QR 配送。ここまで無料 ≈2,500字）/ [5] 初日の所感（引用ベース）/ [6] cloud 案との本質差（Tailscale 検証結果を踏まえ、表）/ [7] おすすめする人・しない人 + 「1 週間後に追記する」予約。
- 見出しに [1] 等の番号を出さない（内部構成番号は見出し文字列に含めない）。

## done 条件

- [ ] `docs/articles/2026-07-20-orca-phone-coding-jp.md` が存在し、上記不変条件を全部満たす
- [ ] 素材に無い事実・URL・数値がゼロ（各段落の事実は素材 1-3 のどれかに遡れる）
- [ ] `grep -c '###'` = 0、全角ダッシュ 0
- [ ] 文字数: 全体 6,000〜9,000 字、[4] 末尾までで 2,300〜2,800 字

完了したら agmsg で DONE 報告: `~/.agents/skills/agmsg/scripts/send.sh orca-article sol-codex fable-main 'DONE <全体文字数>'`
質問がある場合も同経路: `~/.agents/skills/agmsg/scripts/send.sh orca-article sol-codex fable-main '<質問>'` のあと `~/.agents/skills/agmsg/scripts/inbox.sh orca-article sol-codex` で回答を待つ。
