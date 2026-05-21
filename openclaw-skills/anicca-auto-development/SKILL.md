# Anicca Auto-Development（検索 → 報告 → spec → Codex Review → Codex 実装 → 検証 → 報告）

Anicca が「**x-research** と Firecrawl で深掘り」「**OpenClaw / Anicca の最新ユースケース・GitHub のスキル・プラグイン**を調べる」「#metrics に調査結果と実装予定を報告」「spec を書く → **Codex Review でレビューして完璧な spec にする** → Codex に worktree で実装させる（**TDD 必須**）→ **実装も Codex Review** → 自分で E2E 検証して結果を報告」まで回すスキル。**開発まわりに限定**。

## 検索でやること（x-research 必須）

- **X で深掘る時は必ず x-research スキルを使う。** 文章だけの調査でなく、**OpenClaw / Anicca OpenClaw の最新ユースケース**を調べる。GitHub のスキル・プラグイン・「こういう風に使っている人がいる」といった具体例を優先して取ってくる。
- **Low-hanging fruit を優先:** すぐダウンロードして使えるスキル、セーフに使えるプラグイン、「これめちゃくちゃ使える」と判断したものを #metrics で報告する。具体が書いてない記事も参考として取るが、**GitHub のスキル・プラグインなど「実際に使えるもの」があれば必ず含める。**

## 役割分担

| 役割 | 担当 | やること |
|------|------|----------|
| マネージャー | Anicca | 検索・学習・#metrics 報告（調査結果＋実装予定）・spec 作成・**spec の Codex Review 依頼**・レビュー済み spec を Codex に渡す・**実装の Codex Review 依頼**・E2E 検証・結果報告 |
| レビュアー（spec） | **codex-review スキル**（VPS） | spec をレビューして ok: true になるまで反復。**完璧な spec** にしてから実装に回す。 |
| プレイヤー | Codex / Claude Code | レビュー済み spec どおりに **worktree で** 実装・**TDD でテスト完全パス**。main は触らない。**dev から生やした worktree** で作業。 |
| レビュアー（実装） | **codex-review スキル**（VPS） | 実装を再度検証。コード・品質を codex-review で ok: true になるまで通す。 |

## 流れ（必須ステップ）

| ステップ | やること |
|----------|----------|
| 1. **検索** | **x-research** と **Firecrawl** で深掘り。OpenClaw / Anicca の最新ユースケース、GitHub のスキル・プラグインを集める。grok-context-research があれば先に実行し `data/context-research/` の .md を読む。 |
| 2. **調査結果 → #metrics 報告** | 「こんなユースケースが見つかった」「こんなスキル・プラグインが使えそう」を **workspace/anicca-auto-development/survey_YYYY-MM-DD-HH.json** に書き、**Slack #metrics に同じ内容を投稿**する。その上で「これからこれを実装する」「このプラグインを入れる」「これをダウンロードする」を明記する。 |
| 3. **簡単なら自分でやる** | コマンドを叩くだけ・プラグインを入れるだけなら **Anicca が自分でやる**（自分でやった方が早い）。その場合も結果は JSON に書き Slack に投稿する。**複雑な場合は spec を書いて Codex に任せる。** |
| 4. **spec 作成** | 採用するものを決め、**実装用の spec** を書く。**spec は必ず Anicca プロジェクトの dev ブランチ上で、新しい空の .md ファイルとして作成する**（例: `.cursor/plans/` やプロジェクトの plans フォルダ）。 |
| 5. **Codex Review（spec）** | **codex-review スキル**（VPS）で spec をレビュー。ok: true になるまで修正して **「完璧な spec」** にする。 |
| 6. **実装依頼** | その **レビュー済み spec** を **Codex（mac-codex）** に渡す。「**必ず worktree で開発すること**」「**TDD（/tdd-workflow スキル）に従い、テストを完全にパスさせること**」と指示する。 |
| 7. **Codex Review（実装）** | Codex が実装・テストを終えたら、**codex-review スキル**で実装を再度検証。ok: true になるまで通す。Codex に「codex-review が通るまで完了させろ」と指示する。 |
| 8. **E2E 検証** | **Anicca が自分で** 実装したスキル・プラグイン・コードを**取り込んで試す**。「できた／できなかった」を必ず確認する。**自分で試して「できました」が出るまで完全にやり切る。** 失敗した場合は原因を記録する。 |
| 9. **結果報告** | **workspace/anicca-auto-development/result_YYYY-MM-DD-HH.json** に書き、**Slack #metrics に同じ内容を投稿**する。内容は下記「結果報告のフォーマット」に従う。 |

## 結果報告のフォーマット（JSON と Slack で必須）

次の項目を **必ず** JSON に書き、Slack #metrics に同じ内容を投稿する。要約禁止。

1. **使用 worktree**（どの worktree で実装したか）
2. **実装内容の詳細**（どんな記事・ユースケースに基づき、何を実装したか／どのスキルをインストールしたか）
3. **MUST: テスト結果**（この実装により、どのテストを実行し、すべてパスしたか。TDD で必須。）
4. **マージ時の留意点**（main にマージする際に気をつけること）
5. **自分で試した結果**（Anicca が実際にそのスキル・実装を取り込んで試した結果。「できました」または「できませんでした（原因: …）」を明記。実装したが試していないは禁止。）

成功・失敗どちらでも、**何が原因で失敗したか**をきちんと記録する。

## 出力 JSON の保存先（2 種類）

| 種類 | パス | 内容 |
|------|------|------|
| 調査結果・実装予定 | `workspace/anicca-auto-development/survey_YYYY-MM-DD-HH.json` | どんなユースケース・スキル・プラグインが見つかったか、これから何を実装するか・何をインストールするか。全文。 |
| 結果報告 | `workspace/anicca-auto-development/result_YYYY-MM-DD-HH.json` | 使用 worktree、実装内容の詳細、テストパス結果、マージ時の留意点、自分で試した結果。全文。 |

どちらも **Slack #metrics に投稿する内容と完全に一致**させる。JSON に保存していないことを Slack にだけ書かない。

## 制約（絶対）

- **main にはマージしない。** 作業は dev から生やした worktree のみ。マージはユーザーがチェックしてから。
- **spec は Codex Review を通してから** Codex 実装に渡す。**実装も Codex の codex-review で再度検証**してから E2E に進む。
- **Codex には TDD（/tdd-workflow）に従い、テストを完全にパスさせるよう指示する。**
- **API キーが必要なら**「自分では取れないので、あなたが取ってほしい」と報告に含める。
- **コストが高いなら** それも報告に含める。

## 使うスキル・ツール

- **x-research**: X 検索・スレッド・プロフィール。**X で深掘る時は必ず使う。**
- **Firecrawl / web fetch**: ドキュメント・記事の深掘り。`~/.openclaw/.env` に `FIRECRAWL_API_KEY` を書いておく。
- **grok-context-research**: 利用可能なら先に実行し、`data/context-research/` の .md を検索・報告の材料に使う。
- **codex-review**（VPS）: spec と実装のレビューゲート。Anicca が呼び出す。ok: true になるまで修正してから次へ。
- **Slack**: #metrics（チャンネル ID: `C091G3PKHL2`）。調査結果と結果報告の両方を必ず投稿する。

## Slack 報告

**【絶対】** 上記 2 種類（調査結果・実装予定 / 結果報告）を、それぞれ JSON に保存したうえで Slack #metrics に**同じ内容を全文**投稿する。成功でも失敗でも必ず投稿する。

## トリガー

- **12 時間ごと**の cron で「調査 → 調査結果報告」「実装があれば spec → Codex → 検証 → 結果報告」を実行する。時刻は jobs.json で 2 本に分けてもよい。
- ユーザーや Slack からの依頼で「〇〇について調べて → よければ spec 書いて Codex に依頼して」をその都度実行。

## 仕様書の置き場

spec は **Anicca プロジェクトの dev ブランチ上で、新しい空の .md ファイル**として作成する（例: `.cursor/plans/` やプロジェクトの plans フォルダ）。Codex に渡す際は「この spec のパス」と「worktree で開発すること」「TDD でテスト完全パス」を伝える。
