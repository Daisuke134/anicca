# Anicca launch記事 fresh-context レビュー(2026-07-05)

レビュアー: fresh-context（本会話の外の第三者として、執筆時の会話を持たずに審査）。編集・公開は一切行っていない。

検証手段: `~/anicca-project/docs/superpowers/specs/2026-07-03-anicca-colony-architecture-design.md` §24〜§29 / `~/anicca` の git log・git show / `curl https://aniccaai.com/.netlify/functions/dashboard-sync`（live fetch, 2026-07-05実行）/ Polygon public RPC（`polygon-bor-rpc.publicnode.com`）による tx receipt 直接取得 / Solana public RPC（`api.mainnet-beta.solana.com`）による残高取得 / GitHub REST API による issue #760 直接取得 / `~/.blockrun/franklin-audit.jsonl` と `cost_log.jsonl` の実ファイル集計。

## 追記(2026-07-05, 再検証): FIX反映済み — 全ファイル PASS

commit `748c47d15`・`6ba11ffae`（branch `feature/clip-rewards`）を diff ベースで再検証した。

1. **ART-A ja/en**: ブロック番号 `89,713,198` → `89,644,078` に修正済み。当方が実測したPolygon public RPC値と完全一致。
2. **ART-A ja/en**: 未検証の指値注文id `0x73bee6545b10` を含む一文が丸ごと削除された（方針②=裏の取れない数字は落とす、を採用）。
3. **ART-B ja/en**: 総コスト `$1.36` → `$1.39` に修正済みで実測値($1.3924)と一致。モデル切替の記述も「無料モデルに切り替えては空の応答しか返らず、いくつか別のモデルも試し、そのたびに結果を見ながら乗り換えるという試行錯誤の末」（EN: "a few other models got tried along the way, and after enough rounds of switching and checking the results"）に変更され、実態（sonnet-4/deepseek等も混在した多段階の試行錯誤）に即した表現になった。

新たな問題は見つからず。**最終verdict: ART-A / ART-B / ART-C 全ファイル PASS。**

---

## ART-A: anicca-environment（ja/en）

**Verdict: FIX（重大指摘1件）**

### FACT
- 決済 tx `0x7662a88b6851d12a08e1f4dd0c020254cb9f96107e6ceea7dd92965639a4bfc3` は Polygon public RPC で直接 receipt を取得でき、`status:"0x1"`（成功）を確認した。tx の to は `0xe2222d279d744050d28e00520010520000310f59`（Polymarket 系コントラクトに典型的な vanity address パターン）で、ログ内に `0x904b50d2e214da947d83d6a2d32c4e3ffc17eb74`（memory記録済みの claude-p PM wallet と一致）が出現しており、「AIの取引が実際に決済された」という主張自体は強く裏付けられる。
- ★しかし記事記載の「Polygonのブロック89,713,198」は誤り。取得した receipt の `blockNumber` は `0x557dc2e` = **89,644,078**（10進変換済み）で、記事の数字とは約69,120ブロック（Polygon の平均ブロック時間から見て約38時間相当）ずれている。tx hash 自体は正しく、成功ステータスも事実だが、ブロック番号だけ別の値になっている。tx のブロック番号は不変の値なので「時点のズレ」では説明できない、単純な誤記または転記ミス。★公開前に必ず修正が必要（ja/en両方）★。
- ダッシュボードのライブ数値（`alive:3`、`total_net_worth_usd:25.37`、self-funded 2 / human-funded 1、`earned_today_usd:0.196904`）は記事本文の「3体(alive: 3)」「純資産は約25ドル」「2体はself-funded、1体は人間が種銭」「今日確定した利益は0.03〜0.2ドル程度」といずれも一致した。
- spawn 準備状況「AKT が26必要なところ、今は1.8575しかない、24.1425足りない」は spec §29 の「実残高1.8575 AKT vs 閾値26 → shortfall 24.14」と一致（丸めの範囲内）。
- 指値注文ハッシュ `0x73bee6545b10`（12桁）は標準的なtx hash（64桁）でもEthereumアドレス（40桁）でもなく、Polymarket CLOB の order id である可能性が高いが、この場では検証手段がなく未検証のまま。出典に「今もPolymarketの板の上で生きています」とあるが、確認可能なURLが無い。

### HONESTY
儲けが小さいこと（$0.03〜$0.2、含み益込みで$2〜3.6）、自己増殖がまだ発火していないこと、種銭の大半が人間由来であることを隠さず書いている。過度な卑下もない。良好。

### VOICE
JP: 一人称「僕」で自然。命題型見出しがやや続くが記事の性質上妥当で、AI臭い言い回しは検出されなかった。EN: slopワード（delve等）なし、em-dash 過多もない。

### STRUCTURE
冒頭3行のフック（5ドルのサーバー代を払わせられなかった）が機能しており、初心者でも最後まで読める長さと専門用語の解説（KYC, SIWE/EIP-4361）がある。

---

## ART-B: franklin-blockrun（ja/en）

**Verdict: PASS（軽微指摘あり）**

### FACT
- wallet `8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9` は実在し、Solana public RPC で残高取得済み。dashboard live fetch では `net_worth_usd: 3.299112`（記事の「$3.33」とほぼ近似、生きた資産評価であり同日内の自然な変動範囲。出典に「2026-07-05時点」と明記済みなので許容範囲）。
- `~/.blockrun/franklin-audit.jsonl` を実際に集計 → **97件、実測合計 $1.3924**。記事の「97回の判断で合計$1.36」とは97件は完全一致、金額は$1.36 vs $1.39で軽微なズレ（記事執筆後さらに数件呼び出しが積み上がった可能性が高い）。致命的ではない。
- モデル切替ストーリー「Opus→無料モデル→gpt-5-mini」は大筋事実（Opus 4.8を4回使用した記録あり、gpt-5-miniが52回で最多）だが、実ログには claude-sonnet-4（32回）、deepseek-v4-pro（21回）等も混在しており、実際は記事より多段階の試行錯誤だった形跡がある。単純化であり虚偽ではないが、「二値の切替」というより「複数モデルを試した末にgpt-5-miniに収束した」が実態に近い。
- commit `8154a6e` を実際に確認 → 記事の「三つ目の躓き」の記述（質問で終わる問題、"THIS FILE DECIDES NOTHING"という設計方針、プロンプトのみで直した点）と完全に一致。
- GitHub issue #760 を実際にAPIで取得 → 実在し、ラベル`bot2bot-lesson`実在、投稿者は`Daisuke134`（記事の「全員が同じ一つのアカウントを共有している」という記述と整合）。
- 「Franklinはまだ一件も実際の取引を実行していない」は直接ログで確認しなかったが、franklin-audit.jsonl中のプロンプトテンプレートが記事引用の判断ログと同一パターンであることを確認しており、信憑性は高い。

### HONESTY
「儲かった話ではない」ことを繰り返し明言し、$0.91を溶かした失敗も正直に書いている。良好。

### AUDIENCE-FIT（BlockRunチーム向け）
技術的具体性（x402の実コード、実際のコスト明細、実際に見つけた3つのバグとその直し方）が正直に書かれており、「一緒に開発したい」と思わせる内容になっている。ただしBlockRunそのものの価値説明は1パラグラフのみで控えめ。hire訴求を狙うなら、BlockRunがなければこの検証自体が成立しなかった旨をもう一段明確に書いてもよい（必須ではない）。

### SAFETY
秘密鍵露出なし。walletアドレス・tx hashのみで問題なし。

---

## ART-C: loop-engineering（ja/en）

**Verdict: PASS**

### FACT
- commit `473f302`, `ceb519e`, `d00aa6d` を全て `git show` で実在確認。中身は記事の記述と高精度で一致：
  - `473f302`: commit message に "This was NOT a real bug" "a labeled fixture" と明記 — 記事本文も「わざと動かないコードを一つ用意しました」と正直に書いており整合。
  - `d00aa6d`: 3つの latent bug（author filter固定・label未作成・repo未指定）の記述が commit message とほぼ一言一句レベルで一致。
  - `ceb519e`: exponential backoff（300→600→…→cap 3600秒）の記述が記事の「5分→10分→20分」と整合。
- GitHub issue #760 実在確認済み（ART-Bと同一）。
- spec §26 に "DEAD/STALEは既存self-fix.sh(Opus fixer)へエスカレーション" とあり、記事の「修復役のAI(Opus)」という記述と一致。
- spec §26 に "automatonが18:08:01Zにd00aa6dへself-update" とあり、記事の「別のAIのログに `anicca-daemon: self-updated to d00aa6d`」という記述と一致。

### HONESTY
「まだ自動ではないこと」セクションで、4件とも人間が意図的にトリガーしたものであり完全無人ではないことを明記している。これは非常に誠実で、記事全体の信頼性を高めている。

### VOICE
ボリス・チャーニーの引用は英語原文＋和訳併記で自然。JP版に両論併記癖や決めつけ書き出しは見られない。EN版もslopパターンなし。

### STRUCTURE
GLVSの説明→4つの実例→表でのまとめ→正直な限界、という流れが分かりやすい。表(GLVSマッピング)は情報量に対して適切。

---

## 総括

| 記事 | Verdict | 最重要指摘 |
|---|---|---|
| ART-A | **FIX** | tx `0x7662a88b...` のブロック番号「89,713,198」は誤り。実際のオンチェーン値は **89,644,078**。tx自体・成功ステータス・walletの紐付けは全て裏付けられるが、この数字だけ修正必須。 |
| ART-B | PASS（軽微） | 総コスト「$1.36」は実測$1.3924で近似だが完全一致ではない。モデル切替は「Opus→無料→gpt-5-mini」の2段階として単純化されているが、実際はsonnet-4/deepseek等も混在した多段階の試行錯誤。 |
| ART-C | PASS | 全commit・issue番号が実在確認済みで最も裏取りが堅い。「まだ自動ではない」という正直な限界表明が良い。 |

### 重大指摘 Top 3
1. **ART-A: tx決済のブロック番号が事実と異なる**（記事記載89,713,198 → 実際89,644,078、Polygon public RPCで直接確認）。tx hash自体・成功ステータス・walletの紐付けは正しいので、ブロック番号のみ差し替えれば解決する軽微な修正だが、「公開する数字は全て裏取り済み」という記事の建付け上、これを直さず公開するのは信頼性に関わる。
2. **ART-A: 指値注文ハッシュ`0x73bee6545b10`が未検証**（桁数が標準的なtx hash/addressと異なり、この場で裏取りできなかった。確認可能なURLの追記を推奨）。
3. **ART-B: 総コスト・モデル切替ストーリーの単純化**（$1.36 vs 実測$1.39は軽微、モデル切替は「Opus→無料→gpt-5-mini」の2段階として書かれているが実際はより多段階。致命的ではないが、より正確を期すなら「複数モデルを試した末に」という表現に寄せるとよい）。

### Dais（編集者）がまず読むべき1本
**ART-A**（人間なしでAIが金を稼ぐ方法＝Anicca環境）。理由: この3本の中で最も広い読者に読まれる「入口記事」であり、かつ唯一、公開前に修正必須の事実誤り（tx決済のブロック番号）を含んでいるため。
