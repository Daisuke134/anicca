# 重要: VPS を本番唯一とする

**fix の適用は VPS 上のファイルを直接編集して行う。** ローカルは参照用のみとし、sync で「ローカル → VPS を上書きする」運用にしない。正しい状態は VPS にしかない形にする。

- エージェントが `ssh anicca@46.225.70.241` で VPS に接続し、`~/.openclaw/cron/jobs.json` や `~/.openclaw/skills/<スキル名>/SKILL.md` を VPS 上で編集する。
- 必要に応じて gateway 再起動は VPS 上で実行する。

**絶対禁止（違反しないこと）:** (1) 「VPS にアクセスできません」「SSH できません」と言い切ること (2) ユーザーに「VPS に反映してください」「このコマンドを実行してください」と言うこと (3) ローカルで編集しただけで「直りました」で終わること（VPS に反映して初めて完了） (4) ローカルだけで確認して「VPS も同じはず」とすること。詳細: `.cursor/rules/openclaw-vps-absolute.md`

VPS のフォルダ構成・スキル出力パス・削除リスト・各スキル説明は **`.cursor/plans/reference/vps-folder-and-skills-reference.md`** にまとめた。


---

## 【絶対】-today は「今日だけ」＝日付指定 1 回。毎日 cron 禁止

**-today ジョブは「今日 1 回だけ」の試験用である。** 毎日 cron（`分 時 * * *`）で登録すると nextRunAtMs が狂い、翌年などに飛ぶ不具合が出る。**必ず「日・月」を指定した 1 回 cron にする。**

| 正 | 誤 |
|----|-----|
| `25 20 15 2 *` = 2月15日 20:25 の **1 回のみ** | `25 20 * * *` = **毎日** 20:25（today には使わない） |

app-nudge-morning-today などが「2月15日 15:30 のみ」で発火しているのは、この **日付指定 1 回** だから。同じ方式で -today を登録する。

---

## 今日だけのやり直しスケジュール（20:25 開始・5 分刻み・8 本・Today で登録）

次の 8 本を **2月15日のみ** の 1 回実行で登録する（expr は `分 時 15 2 *` = 15日 2月 のみ）。app-nudge・roundtable-standup・roundtable-initiative・autonomy-check・daily-memory は含めない。

| 時刻 (JST) | ジョブ ID | cron 例（今日だけ） |
|------------|-----------|----------------------|
| 20:25 | trend-hunter-5am-today | `25 20 15 2 *` |
| 20:30 | trend-hunter-5pm-today | `30 20 15 2 *` |
| 20:35 | suffering-detector-today | `35 20 15 2 *` |
| 20:40 | x-poster-morning-today | `40 20 15 2 *` |
| 20:45 | x-poster-evening-today | `45 20 15 2 *` |
| 20:50 | tiktok-poster-morning-today | `50 20 15 2 *` |
| 20:55 | tiktok-poster-evening-today | `55 20 15 2 *` |
| 21:00 | anicca-auto-development-today | `0 21 15 2 *` |

**廃止・停止で含めないもの:** roundtable-memory-extract-today, hookpost-ttl-cleaner-today, sto-weekly-refresh-today, および app-nudge 3 本・roundtable-standup・roundtable-initiative・autonomy-check・daily-memory。

---

# 0. 今回の MD で 3 つの問題がどう治るか

| 問題 | 治し方（この MD のどこで直すか） |
|------|----------------------------------|
| ① hook の **imageUrl が空**（TikTok はメディア必須） | **tiktok-poster** が hooks の **imagePrompt** を読んで **FAL で画像生成**し、得た URL を imageUrl として使ってから投稿する（修正 #5）。trend-hunter は imagePrompt を書くだけ。画像生成は **tiktok-poster がやる**。 |
| ② スキル内の **Blotato API エンドポイントが間違っている**（api.blotato.com → 正しくは backend.blotato.com） | **tiktok-poster** の SKILL に「呼び出す API は `https://backend.blotato.com/v2/...`」と明記し、実装・runbook の api.blotato.com を backend.blotato.com に変更（修正 #6）。 |
| ③ **hooks/YYYY-MM-DD.json に slot=9pm のみで 9am がない**（9am 用エントリがないため朝投稿不可） | **trend-hunter** の保存先を **slot 別フォルダ**に変更。`hooks/9am/YYYY-MM-DD.json` と `hooks/9pm/YYYY-MM-DD.json` に**別ファイルで**書き、マージしない（修正 #1）。x-poster / tiktok-poster は `hooks/9am/` または `hooks/9pm/` のファイルを読む（修正 #3, #4）。 |

---

# 0.1 画像は誰が作るか・FAL の指示（tiktok-poster に書くこと）

| 役割 | 担当 | やること |
|------|------|----------|
| **imagePrompt を書く** | **trend-hunter** | hooks の TikTok 用エントリに **caption** と **imagePrompt**（FAL 用英文プロンプト）を**必ず**入れる。**imageUrl はプレースホルダーでキーだけ用意し、空文字でよい**（tiktok-poster が FAL で生成してから投稿時に使う）。 |
| **画像生成（FAL）と投稿** | **tiktok-poster** | hooks/9am または 9pm の JSON を読む。**imageUrl が空なら、同じエントリの imagePrompt を FAL API に渡して画像を生成し、返ってきた URL を imageUrl として使ってから** Blotato で TikTok に投稿する。 |

**tiktok-poster 用の明示指示（SKILL と cron message に書く）：**

- 読むパス: `~/.openclaw/workspace/hooks/9am/YYYY-MM-DD.json`（morning）または `~/.openclaw/workspace/hooks/9pm/YYYY-MM-DD.json`（evening）。YYYY-MM-DD は今日の日付（Asia/Tokyo）。
- その JSON 内の TikTok 用エントリ（platform: "tiktok"）の **caption** と **imageUrl** を参照する。
- **imageUrl が空または無い場合:** 同じエントリの **imagePrompt** を必ず参照する。その **imagePrompt の全文**を FAL の画像生成 API に渡し、生成された画像の URL を取得する。その URL を imageUrl として Blotato に渡して TikTok に投稿する。
- FAL の呼び方（API キー・エンドポイント）は VPS の .env やスキル内 runbook に従う。プロンプトは **hooks に書かれた imagePrompt を 1 文字も変えずに** FAL に渡す。

---

# 0.2 tiktok-poster の画像 verify ループ（必須）

**「画像を 1 回生成して終わり」にしない。** 次のプロトコルを tiktok-poster の SKILL に書く。

1. **生成**: hooks の imagePrompt で FAL を呼び、画像 URL を取得する。
2. **検証（verify_content）**: 生成した画像を自分で確認する（サムネイルとして適切か・不適切な内容がないか）。基準（閾値）を満たすか判定する。
3. **ループ**: 基準を満たさない場合は、**imagePrompt を改善した文言で FAL を再実行**する。または手順で許容する範囲でプロンプトを微調整して再生成する。**基準を満たすまで繰り返す。**
4. **投稿**: 基準を満たした画像 URL で Blotato に post_tiktok する。

Slack 報告には「再生成した回数」「採用した imagePrompt（全文）」を含める。

---

# 0.3 jobs.json の登録の仕方（具体例）

OpenClaw の cron は **jobs.json** の `jobs` 配列に 1 ジョブ 1 オブジェクトで登録する。各ジョブの形は次のとおり（実際の id をそのまま使用）。

**例: trend-hunter-5am（5:00 JST 毎日）**

```json
{
  "id": "trend-hunter-5am",
  "agentId": "anicca",
  "jobId": "trend-hunter-5am",
  "name": "trend-hunter-5am",
  "schedule": {
    "kind": "cron",
    "expr": "0 5 * * *",
    "tz": "Asia/Tokyo"
  },
  "sessionTarget": "isolated",
  "wakeMode": "now",
  "payload": {
    "kind": "agentTurn",
    "message": "Execute trend-hunter skill. ... (スキル実行の指示全文)"
  },
  "delivery": {
    "mode": "announce",
    "channel": "slack",
    "to": "channel:C091G3PKHL2"
  },
  "enabled": true
}
```

- **schedule.expr**: cron 式（分 時 日 月 曜）。`0 5 * * *` = 毎日 5:00、`0 21 * * *` = 毎日 21:00。
- **payload.message**: エージェントに渡す文言。ここに「hooks/9am/YYYY-MM-DD.json を読め」など書く。
- **delivery**: 実行後に Slack #metrics に結果を投稿する設定。

**例: tiktok-poster-evening（21:00 JST 毎日）**

```json
{
  "id": "tiktok-poster-evening",
  "agentId": "anicca",
  "jobId": "tiktok-poster-evening",
  "name": "tiktok-poster-evening",
  "schedule": { "kind": "cron", "expr": "0 21 * * *", "tz": "Asia/Tokyo" },
  "sessionTarget": "isolated",
  "wakeMode": "now",
  "payload": {
    "kind": "agentTurn",
    "message": "Execute tiktok-poster skill. Read ~/.openclaw/workspace/hooks/9pm/YYYY-MM-DD.json for today. If imageUrl is empty, use imagePrompt from that file and call FAL to generate image, then use the returned URL as imageUrl. Post caption and imageUrl to TikTok via backend.blotato.com. CRITICAL: After you finish, post summary to Slack #metrics (C091G3PKHL2)."
  },
  "delivery": { "mode": "announce", "channel": "slack", "to": "channel:C091G3PKHL2" },
  "enabled": true
}
```

今日だけやり直す場合は、本 MD 冒頭の **「今日だけのやり直しスケジュール（20:00 開始・8 本のみ）」** に従い、該当時刻に手動トリガーまたは臨時 cron で実行する。通常の本番 cron は各ジョブの schedule のまま。

---

# 0.5 daily-memory 修正（AGENTS.md 参照やめ・セッション履歴のみ・出力先を workspace に揃える）

daily-memory は **AGENTS.md を読まない**。学びの元は **セッション履歴**（今日の cron 実行結果・standup・他スキルの出力）のみ。OpenClaw のデフォルトファイル（AGENTS.md, SOUL.md, USER.md 等）は削除せず残す。出力先を **workspace/daily-memory/** に揃える（OpenClaw の「メモリは workspace 内」に合わせる）。

## Before（現状）

| 対象 | 内容 |
|------|------|
| **SKILL.md** | 手順 1 で「`/home/anicca/.openclaw/workspace/AGENTS.md` を読む。存在しなければセッション履歴から…」。必須 tools に「AGENTS.md の読取」。失敗時「workspace/AGENTS.md が無い場合はセッション履歴等から」。禁止事項に「AGENTS.md の読取元は workspace/AGENTS.md のみ」。 |
| **jobs.json message** | 「Read /home/anicca/.openclaw/workspace/AGENTS.md (bootstrap copy; do NOT read memory/anicca/AGENTS.md). If missing, extract learnings from session history. Append ... lessons-learned.md ... diary ...」 |
| **出力先** | `~/.openclaw/memory/anicca/lessons-learned.md` と `~/.openclaw/memory/anicca/diary-YYYY-MM-DD.md` |

## After（適用後）

| 対象 | 内容 |
|------|------|
| **SKILL.md** | **AGENTS.md の読取を一切やめる。** 手順は「1. 今日のセッション履歴・**standup の結果・cron の成功/失敗**を入力とし、学びを抽出する。2. 学びを 1〜3 行でまとめ、`~/.openclaw/workspace/daily-memory/lessons-learned.md` に追記する。3. 今日の日記を `~/.openclaw/workspace/daily-memory/diary-YYYY-MM-DD.md` に書く。」**入力に standup・cron 結果を含め、lessons-learned と diary に書く旨を SKILL に明記する。** 必須 tools から「AGENTS.md の読取」を削除。失敗時・禁止事項から AGENTS.md 関連の記述を削除。 |
| **jobs.json message** | 「Execute daily-memory skill. Extract today's learnings from **session history, roundtable-standup の結果、および今日の cron の成功/失敗**. Do NOT read AGENTS.md. Append to ~/.openclaw/workspace/daily-memory/lessons-learned.md. Write today's diary to ~/.openclaw/workspace/daily-memory/diary-YYYY-MM-DD.md (use today's date). CRITICAL: Post execution summary to Slack #metrics (C091G3PKHL2).」 |
| **出力先** | `~/.openclaw/workspace/daily-memory/lessons-learned.md` と `~/.openclaw/workspace/daily-memory/diary-YYYY-MM-DD.md` |

VPS で既に `memory/anicca/` に書いている場合は、必要なら **初回のみ** 既存の lessons-learned.md / 直近の diary を `workspace/daily-memory/` にコピーしてから、以降は新パスのみ使う。

---

# 1. 修正リスト（どのスキルをどこで直すか）

| # | スキル | 問題 | 修正内容 |
|---|--------|------|----------|
| 1 | **trend-hunter** | hooks を上書きして 9am が消える | 保存先を **slot 別フォルダ** に変更。`trends/9am/YYYY-MM-DD.json`, `trends/9pm/YYYY-MM-DD.json`, `hooks/9am/YYYY-MM-DD.json`, `hooks/9pm/YYYY-MM-DD.json` に書き、マージはしない。 |
| 2 | **trend-hunter** | パス・参照の記述が古い | 上記に合わせて「保存先」「出力形式」「x-poster / tiktok-poster の読むパス」をすべて slot 別パスに更新。 |
| 3 | **x-poster** | 読むパスが 1 ファイル前提 | hooks を **`hooks/{slot}/YYYY-MM-DD.json`** から読むと明記（例: morning → `hooks/9am/YYYY-MM-DD.json`）。 |
| 4 | **tiktok-poster** | 同上 | 同上。**`hooks/9am/` または `hooks/9pm/`** の YYYY-MM-DD.json を読むと明記。 |
| 5 | **tiktok-poster** | imageUrl が空で TikTok 投稿できない | **imageUrl が空なら imagePrompt を読み、FAL で画像生成 → 得た URL を imageUrl として使ってから投稿する** と SKILL に手順として書く。Blotato は画像 URL 必須。 |
| 6 | **tiktok-poster** | Blotato のベース URL が誤り | 呼び出す API は **`https://backend.blotato.com/v2/...`** であると SKILL に明記（api.blotato.com は使わない）。実装や runbook で api.blotato.com を参照している箇所があれば backend.blotato.com に変更。 |
| 7 | **x-poster** | Slack 投稿内容が不定形 | 下記「x-poster 用 Slack フォーマット」を SKILL の Slack 報告にそのまま書く。 |
| 8 | **tiktok-poster** | 同上 | 下記「tiktok-poster 用 Slack フォーマット」を SKILL の Slack 報告にそのまま書く。 |
| 9 | **trend-hunter** | Slack で要約ではなく全文出したい | 下記「trend-hunter 用 Slack フォーマット」を SKILL の Slack 報告に書く（slot 別パスに合わせてパス表記を修正）。 |
| 10 | **suffering-detector** | Slack 投稿形式が未定義 | 下記「suffering-detector 用 Slack フォーマット」を SKILL の Slack 報告に書く。 |
| 11 | **daily-memory** | AGENTS.md 参照・出力先が OpenClaw 設計とずれている | 上記 **0.5** のとおり。AGENTS.md を読まない。学びはセッション履歴のみ。出力先を `workspace/daily-memory/` に変更。SKILL と jobs.json の message を Before/After に合わせて修正。 |

画像生成は **tiktok-poster でやる**想定がよいです。trend-hunter は「imagePrompt を書く」までにして、**「imageUrl が空なら FAL で画像生成してから投稿」は tiktok-poster の責務**にすると、役割が分かりやすく、安いエージェントでも動かしやすいです。

---

# 2. フォルダ構成（slot 別サブフォルダ）

- **trends**:  
  `~/.openclaw/workspace/trends/9am/YYYY-MM-DD.json`  
  `~/.openclaw/workspace/trends/9pm/YYYY-MM-DD.json`
- **hooks**:  
  `~/.openclaw/workspace/hooks/9am/YYYY-MM-DD.json`  
  `~/.openclaw/workspace/hooks/9pm/YYYY-MM-DD.json`

これで「その slot のファイルに書くだけ」にでき、マージや上書きの考慮が不要になります。

---

# 3. 各スキルで Slack に出す「 exact format」（SKILL.md に貼る用）

以下をそのまま各 SKILL の「Slack 報告」に書いて、「cron がヒットしたら必ずこの形式で投稿する」と指定するとよいです。

---

## x-poster（X 投稿）

```
【Slack #metrics に必ず以下の形式で投稿する。要約禁止。】

1. スキル名と結果
   x-poster ({slot}) — :white_check_mark: 投稿成功 / :x: 失敗

2. 日時
   日付と投稿実行時刻（例: 2026-02-15 15:10 JST）

3. 内容（省略禁止）
   投稿したツイート全文をそのまま貼る。1文字も省略しない。

4. X の投稿リンク
   投稿後の URL（例: https://x.com/username/status/1234567890）

5. 備考（あれば）
   スキップ理由・エラー・手動トリガー等
```

---

## tiktok-poster（TikTok 投稿）

```
【Slack #metrics に必ず以下の形式で投稿する。要約禁止。】

1. スキル名と結果
   tiktok-poster ({slot}) — :white_check_mark: 投稿成功 / :x: 失敗

2. 日時
   日付と投稿実行時刻（例: 2026-02-15 21:00 JST）

3. 内容（省略禁止）
   - キャプション: 投稿した caption の全文をそのまま貼る。
   - imagePrompt: 使用した画像生成プロンプトの全文をそのまま貼る。

4. TikTok の投稿リンク
   投稿後の URL（Blotato 等から取得したリンク）

5. 備考（あれば）
   スキップ理由・imageUrl 空で FAL 生成した等
```

---

## trend-hunter

```
【Slack #metrics に必ず以下の形式で投稿する。要約禁止。】

1. スキル名と結果
   trend-hunter ({slot}, {date}) — :white_check_mark: 完了 / :x: 失敗

2. 日時
   実行日付と時刻（例: 2026-02-15 05:00 JST）

3. ソース結果（そのまま）
   X / TikTok / Reddit の取得件数・スキップ理由を省略せず書く。

4. 保存ファイルの内容（全文）
   - trends/{slot}/{date}.json の内容を整形してそのまま貼る（全トレンドの hook, source, trendContext, pattern, analysis）。
   - hooks/{slot}/{date}.json の内容を整形してそのまま貼る（X の postText、TikTok の caption, imageUrl, imagePrompt, reasons）。省略しない。

5. 備考（あれば）
   Apify/Reddit エラー等
```

（slot 別フォルダにしたあとで、パスを `trends/9am/`, `hooks/9pm/` などに合わせてください。）

---

## suffering-detector

```
【Slack #metrics に必ず以下の形式で投稿する。要約禁止。】

1. スキル名と結果
   suffering-detector — :white_check_mark: 完了（検知N件） / :x: 失敗 / :rotating_light: SAFE-T 発動

2. 日時
   実行日付と時刻（例: 2026-02-15 06:05 UTC）

3. 結果（そのまま）
   - 検知件数と各 severity（例: 検知3件、max severity 0.4）
   - crisis 検出の有無（SAFE-T 要/不要）
   - workspace/suffering/findings_YYYY-MM-DD.json の内容を整形してそのまま貼る（全文。要約・省略禁止）

4. 備考（あれば）
   スキップ理由・エラー等
```

---

# 4. まとめ

- **trend-hunter**: slot 別フォルダ（9am/9pm）に変更し、保存・参照パスをすべてそれに合わせる。Slack は上記 trend-hunter フォーマットで「全文出す」と明記。
- **x-poster / tiktok-poster**: 読むパスを `hooks/{9am|9pm}/YYYY-MM-DD.json` に変更。tiktok-poster で「imageUrl が空なら imagePrompt で FAL 生成してから投稿」と Blotato は **backend.blotato.com** と明記。Slack は上記の x-poster / tiktok-poster フォーマットをそのまま SKILL に書く。
- **suffering-detector**: Slack 報告に上記フォーマットをそのまま書く。

Anicca が小さい修正を入れていても、上記の「フォルダ構造・読むパス・Slack フォーマット・Blotato URL・画像生成の責務」を SKILL.md に揃えておけば、cron がヒットするたびに同じ desirable な形で Slack に出るようになります。



以下、cron の書き換え案と全スキル用の Slack exact formatをまとめます。
1. X / TikTok 用 cron の読むパス（4 本）
x-poster-morning の message を次のようにする:
現行: Read ~/.openclaw/workspace/hooks/YYYY-MM-DD.json for today, slot 9am. Post the 9am postText to X now.
変更後: Read ~/.openclaw/workspace/hooks/9am/YYYY-MM-DD.json for today (replace YYYY-MM-DD with today's date in Asia/Tokyo). Post the postText from that file to X now.
x-poster-evening の message:
変更後: Read ~/.openclaw/workspace/hooks/9pm/YYYY-MM-DD.json for today (replace YYYY-MM-DD with today's date in Asia/Tokyo). Post the postText from that file to X now.
tiktok-poster-morning の message:
変更後: Read ~/.openclaw/workspace/hooks/9am/YYYY-MM-DD.json for today (replace YYYY-MM-DD with today's date in Asia/Tokyo). Post the caption and imageUrl (or generate image from imagePrompt via FAL if imageUrl empty) to TikTok now.
tiktok-poster-evening の message:
変更後: Read ~/.openclaw/workspace/hooks/9pm/YYYY-MM-DD.json for today (replace YYYY-MM-DD with today's date in Asia/Tokyo). Post the caption and imageUrl (or generate image from imagePrompt via FAL if imageUrl empty) to TikTok now.
（既にある「CRITICAL: After you finish...」の一文はそのまま残す。）

2. 全スキル用 Slack exact format（SKILL.md に貼る用）
trend-hunter
【Slack #metrics に必ず以下の形式で投稿する。要約禁止。】1. スキル名と結果   trend-hunter ({slot}, {date}) — :white_check_mark: 完了 / :x: 失敗2. 日時   実行日付と時刻（例: 2026-02-15 05:00 JST）3. ソース結果（そのまま）   X / TikTok / Reddit の取得件数・スキップ理由を省略せず書く。4. 保存ファイルの内容（全文・省略禁止）   - trends/{slot}/{date}.json の内容を整形してそのまま貼る（全トレンドの hook, source, trendContext, pattern, analysis）。   - hooks/{slot}/{date}.json の内容を整形してそのまま貼る（X の postText、TikTok の caption, imageUrl, imagePrompt, reasons）。5. 備考（あれば）   Apify/Reddit エラー等

suffering-detector
【Slack #metrics に必ず以下の形式で投稿する。要約禁止。】1. スキル名と結果   suffering-detector — :white_check_mark: 完了（検知N件） / :x: 失敗 / :rotating_light: SAFE-T 発動2. 日時   実行日付と時刻（例: 2026-02-15 06:05 UTC）3. 結果（そのまま）   - 検知件数と各 severity（例: 検知3件、max severity 0.4）   - crisis 検出の有無（SAFE-T 要/不要）   - workspace/suffering/findings_YYYY-MM-DD.json の内容を整形してそのまま貼る（全文。要約・省略禁止）4. 備考（あれば）

x-poster
【Slack #metrics に必ず以下の形式で投稿する。要約禁止。】1. スキル名と結果   x-poster ({slot}) — :white_check_mark: 投稿成功 / :x: 失敗2. 日時   日付と投稿実行時刻（例: 2026-02-15 09:00 JST）3. 内容（省略禁止）   投稿したツイート全文をそのまま貼る。1文字も省略しない。4. X の投稿リンク   投稿後の URL（例: https://x.com/username/status/1234567890）5. 備考（あれば）   スキップ理由・エラー・手動トリガー等
tiktok-poster

【Slack #metrics に必ず以下の形式で投稿する。要約禁止。】1. スキル名と結果   tiktok-poster ({slot}) — :white_check_mark: 投稿成功 / :x: 失敗2. 日時   日付と投稿実行時刻（例: 2026-02-15 21:00 JST）3. 内容（省略禁止）   - キャプション: 投稿した caption の全文をそのまま貼る。   - imagePrompt: 使用した画像生成プロンプトの全文をそのまま貼る。4. TikTok の投稿リンク   投稿後の URL（Blotato 等から取得したリンク）5. 備考（あれば）   スキップ理由・imageUrl 空で FAL 生成した等

app-nudge-sender
【Slack #metrics に必ず以下の形式で投稿する。要約禁止。】1. スキル名と結果   app-nudge-sender ({slot}) — :white_check_mark: 完了 / :x: 失敗2. 日時   実行日付と時刻（例: 2026-02-15 09:00 JST）3. 結果（そのまま）   - API 応答（success/error）   - workspace/nudges/decisions_YYYY-MM-DD.json の内容を整形してそのまま貼る（全文。要約・省略禁止）4. 備考（あれば）   エラー・スキップ理由等

roundtable-standup
【Slack #metrics に必ず以下の形式で投稿する。要約禁止。】1. スキル名と結果   roundtable-standup — :white_check_mark: 完了 / :x: 失敗2. 日時   実行日付と時刻（例: 2026-02-15 09:00 JST）3. 結果（そのまま）   - workspace/roundtable-standup/run_YYYY-MM-DD.json の内容を整形してそのまま貼る（全文。要約・省略禁止）4. 備考（あれば）

roundtable-memory-extract
【Slack #metrics に必ず以下の形式で投稿する。要約禁止。】1. スキル名と結果   roundtable-memory-extract — :white_check_mark: 完了 / :x: 失敗2. 日時   実行日付と時刻（例: 2026-02-15 08:55 JST）3. 結果（そのまま）   - workspace/roundtable-memory-extract/run_YYYY-MM-DD.json の内容を整形してそのまま貼る（全文。要約・省略禁止）4. 備考（あれば）

roundtable-initiative-generate
【Slack #metrics に必ず以下の形式で投稿する。要約禁止。】1. スキル名と結果   roundtable-initiative-generate — :white_check_mark: 完了 / :x: 失敗2. 日時   実行日付と時刻（例: 2026-02-15 09:05 JST）3. 結果（そのまま）   - workspace/roundtable-initiative-generate/run_YYYY-MM-DD.json の内容を整形してそのまま貼る（全文。要約・省略禁止）4. 備考（あれば）

hookpost-ttl-cleaner
【Slack #metrics に必ず以下の形式で投稿する。要約禁止。】1. スキル名と結果   hookpost-ttl-cleaner — :white_check_mark: 完了 / :x: 失敗2. 日時   実行日付と時刻（例: 2026-02-15 03:00 JST）3. 結果（そのまま）   - archived / deleted / failed の件数（数値で明記）   - workspace/hookpost-ttl-cleaner/run_YYYY-MM-DD.json の内容を整形してそのまま貼る（全文。要約・省略禁止）4. 備考（あれば）

sto-weekly-refresh
【Slack #metrics に必ず以下の形式で投稿する。要約禁止。】1. スキル名と結果   sto-weekly-refresh — :white_check_mark: 完了 / :x: 失敗2. 日時   実行日付と時刻（例: 2026-02-16 03:00 JST、日曜）3. 結果（そのまま）   - workspace/sto-weekly-refresh/run_YYYY-MM-DD.json の内容を整形してそのまま貼る（全文。要約・省略禁止）4. 備考（あれば）

autonomy-check
【Slack #metrics に必ず以下の形式で投稿する。要約禁止。】1. スキル名と結果   autonomy-check — :white_check_mark: 合格 / :x: 不合格 / :warning: 要対応2. 日時   実行日付と時刻（例: 2026-02-15 03:00 JST）3. 結果（そのまま）   - 合否判定と理由（規約違反・DLQ 滞留・失敗率等を具体的に）   - workspace/autonomy-check/audit_YYYY-MM-DD.json の内容を整形してそのまま貼る（全文。要約・省略禁止）4. 備考（あれば）   違反検出時は Slack 通知済みか等

daily-memory
【Slack #metrics に必ず以下の形式で投稿する。要約禁止。】1. スキル名と結果   daily-memory — :white_check_mark: 完了 / :x: 失敗2. 日時   実行日付と時刻（例: 2026-02-15 23:00 JST）3. 結果（そのまま）   - lessons-learned に追記した該当部分の内容をそのまま貼る（全文。要約・省略禁止）   - diary-YYYY-MM-DD.md の内容をそのまま貼る（全文。要約・省略禁止）4. 備考（あれば）

ops-heartbeat
【Slack #metrics に必ず以下の形式で投稿する。要約禁止。】1. スキル名と結果   ops-heartbeat — :white_check_mark: 完了 / :x: 失敗2. 日時   実行日付と時刻（例: 2026-02-15 09:10 JST）3. 結果（そのまま）   - 更新した heartbeat_state.json / proposals.json の内容を整形してそのまま貼る（全文。要約・省略禁止）4. 備考（あれば）

mission-worker
【Slack #metrics に必ず以下の形式で投稿する。要約禁止。】1. スキル名と結果   mission-worker — :white_check_mark: 完了 / :x: 失敗 / queue_empty2. 日時   実行日付と時刻（例: 2026-02-15 09:10 JST）3. 結果（そのまま）   - 実行した step の stepKind と id   - 成功/失敗と、output または error をそのまま貼る（全文。要約・省略禁止）   - キューが空の場合は「queue_empty」と明記4. 備考（あれば）

moltbook-interact
【Slack #metrics に必ず以下の形式で投稿する。要約禁止。】1. スキル名と結果   moltbook-interact — :white_check_mark: 完了 / :x: 失敗2. 日時   実行日付と時刻（例: 2026-02-15 12:00 JST）3. 結果（そのまま）   workspace/moltbook-interact/run_YYYY-MM-DD.json の内容を整形してそのまま貼る（全文。replies[] と createdPost を含む新形式。要約・省略禁止）4. 備考   なし（特記事項があればその内容）

anicca-auto-development
【実行は 12 時間ごと。以下 2 種類の出力をそれぞれ JSON に保存し、Slack #metrics に同じ内容を投稿する。】
(1) 調査結果・実装予定（survey）: workspace/anicca-auto-development/survey_YYYY-MM-DD-HH.json の内容を整形してそのまま貼る（全文）。Slack には「どんなユースケース・スキル・プラグインが見つかったか」「これから何を実装するか・何をインストールするか」を書く。
(2) 結果報告（result）: workspace/anicca-auto-development/result_YYYY-MM-DD-HH.json の内容を整形してそのまま貼る（全文）。Slack には「使用 worktree」「実装内容の詳細」「テスト完全パス」「マージ時の留意点」「自分で試した結果（できた/できなかった・原因）」を書く。どちらも要約禁止。

---

# 5. 共通ルール（Slack 報告の JSON / ファイル出力）

**保存先パスだけ書くのではなく、必ず「そのファイルの内容を整形して全文貼る」こと。** 要約・省略は禁止。中身が空なら「空」と明記する。

---

# 5.5 廃止・停止するジョブ（VPS の jobs.json から削除する）

| ジョブ ID | やること |
|-----------|----------|
| **roundtable-memory-extract** / **roundtable-memory-extract-today** | VPS の jobs から該当ジョブを削除する。daily-memory の入力に standup・cron 結果を含め、lessons-learned / diary に書く旨を SKILL か指示に明記する。**スキルフォルダは残す。** |
| **hookpost-ttl-cleaner** / **hookpost-ttl-cleaner-today** | VPS の jobs から該当ジョブを削除する。**スキルは残す。** |
| **sto-weekly-refresh** / **sto-weekly-refresh-today** | VPS の jobs から該当ジョブを削除する。**VPS の `~/.openclaw/skills/sto-weekly-refresh/` スキルフォルダも削除する。**（UserStoModel は Backend DB にも VPS にも存在しない。） |

**UserStoModel について（結論）:** Backend の Prisma schema を確認した結果、**UserStoModel テーブルは存在しない。** したがって sto-weekly-refresh が「更新する」対象は現状ない。

---

# 5.6 ops-heartbeat 完全仕様（役割・出力 JSON・Slack）

## 役割
閉ループの制御プレーン。5 分ごとに cron で起動し、以下を行う。

1. **読む:** `workspace/ops/heartbeat_state.json` と `workspace/ops/proposals.json`
2. **評価:** trigger / reaction / recovery のロジックを実行し、次にやる Proposal / Step を決定する
3. **書く:** 結果を `heartbeat_state.json` に上書き。新規提案があれば `proposals.json` に追記。**実行すべき step があれば `workspace/ops/steps.json` に 1 件追加する（ここに追加するのは ops-heartbeat のみ。mission-worker がこのキューを読んで 1 件ずつ実行する）**
4. Railway の heartbeat API は呼ばない

## 出力 JSON（必須形）

**heartbeat_state.json（上書き保存）**

```json
{
  "ok": true,
  "lastRun": "2026-02-15T04:00:00Z",
  "elapsed": "< 1s",
  "triggers": [],
  "reactions": [],
  "insights": [],
  "stale": [],
  "status": "nominal",
  "consecutiveOk": 4
}
```

| フィールド | 型 | 必須 | 説明 |
|------------|-----|------|------|
| ok | boolean | 必須 | 実行成功なら true |
| lastRun | string (ISO8601) | 必須 | 今回の実行時刻 |
| elapsed | string | 必須 | 処理時間（例: "< 1s"） |
| triggers | array | 必須 | 発火したトリガー一覧 |
| reactions | array | 必須 | 実行した反応一覧 |
| insights | array | 必須 | 得た洞察一覧 |
| stale | array | 必須 | ステール回復した件 |
| status | string | 必須 | "nominal" 等 |
| consecutiveOk | number | 必須 | 連続成功回数 |

**proposals.json（追記時のみ更新）**

```json
{
  "proposals": [],
  "lastUpdated": "2026-02-15T03:30:00Z"
}
```

**steps.json（step を追加するときだけ ops-heartbeat が更新。中身の形式は mission-worker が読む形）**

```json
{
  "steps": [
    { "id": "uuid", "stepKind": "post_x", "payload": { ... }, "createdAt": "..." }
  ],
  "lastUpdated": "2026-02-15T04:05:00Z"
}
```

## Slack 報告（必ずこの形）

```
【Slack #metrics に必ず以下の形式で投稿する。要約禁止。】

1. スキル名と結果
   ops-heartbeat — :white_check_mark: 完了 / :x: 失敗

2. 日時
   実行日付と時刻（例: 2026-02-15 09:10 JST）

3. 結果（そのまま）
   - 更新した heartbeat_state.json の内容を整形してそのまま貼る（全文。要約・省略禁止）
   - 更新した proposals.json の内容を整形してそのまま貼る（全文。要約・省略禁止）
   - steps.json に追加した step があればその id / stepKind を明記

4. 備考（あれば）
```

**誰が steps.json に step を追加するか:** **ops-heartbeat のみ。** 他に steps.json を書くジョブはない。VPS で確認したところ、現状 steps は常に空（heartbeat が step を 1 件も積んでいない）。

---

# 6. JSON 保存仕様（Slack の Single Source of Truth）

**Anicca が改善し続けるのは「自分たちの JSON」から。** Slack は人が把握する用であり、Slack に書く内容の正本は workspace の JSON（または保存ファイル）である。

| ルール | 内容 |
|--------|------|
| **正本は JSON** | 各スキルが「保存先」としている JSON に、Slack に出すべき情報を**すべて**含める。Slack に投稿する内容は、必ずその JSON（または該当ファイル）から取れるようにする。 |
| **逆は禁止** | **JSON に保存していない情報を Slack にだけ書いてはいけない。** 「Slack に投稿できるが JSON には無い」はありえない。 |
| **足りない場合は JSON を直す** | 情報が足りていないと判明したら、Slack フォーマットの修正だけでなく、**そのスキルの「出力 JSON のスキーマ・必須フィールド」を SKILL.md またはこの MD で定義し直す。** |

## 6.1 確認済み（VPS 2026-02-15）

- **roundtable-standup/run_YYYY-MM-DD.json**: `date`, `type`, `generatedAt`, `summary`, `sections.yesterday/today/blockers/metrics/nextActions` がすべて入っている。Slack のサマリー・ブロッカー・メトリクスはこの JSON から取得可能。**情報は足りている。**
- **roundtable-memory-extract/run_YYYY-MM-DD.json**: （ジョブは 5.5 で削除。スキルは残す。）`date`, `extractedAt`, `source`, `memories[]`（id, category, content, confidence, actionable, tags）, `summary` が入っている。**情報は足りている。**

他のスキル（nudges, suffering, trend-hunter, hooks 等）も、Slack に「全文貼る」としている部分が対応する JSON に含まれていることを、適用後に確認すること。

---

以上が、cron の読むパス（X / TikTok の 4 本）と、全スキル用の Slack exact format です。
cron は jobs.json の該当 4 件の payload.message を上記の文言に差し替え、各スキルはそれぞれのブロックをそのスキルの SKILL.md の「Slack 報告」に貼れば、毎回同じ形式で Slack に出せます。


**適用のやり方:** fix は VPS 上のファイルを直接編集して適用する。エージェントが SSH で VPS に接続し、jobs.json や各 SKILL.md を VPS 上で編集する。ローカルは参照用のみとし、sync で「ローカル → VPS を上書きする」運用にしない。daily-memory は 0.5 のとおり、AGENTS.md を読まず standup・cron 結果を入力とし、出力先は workspace/daily-memory/ とする。

---

# 8. fix を「VPS だけ本番」で適用するときのやり方

**方針:** 修正の正本は「VPS 上の OpenClaw」だけにする。ローカルは参照用とし、sync で上書きしない。

**手順:**

1. エージェントが `ssh anicca@46.225.70.241` で VPS に接続する（ユーザーに「VPS に接続してください」「コマンドを叩いてください」と言わない。エージェントが SSH を実行する）。
2. 修正内容（ジョブ削除・追加、SKILL 文言、cron 時刻など）を、**VPS 上のファイル**に直接反映する。
   - 例: `~/.openclaw/cron/jobs.json` を編集してジョブを削除・追加する。
   - 例: `~/.openclaw/skills/<スキル名>/SKILL.md` を編集する。
3. 必要なら gateway 再起動なども **VPS 上で** 実行する（例: 利用している起動スクリプトや systemd があればそれに従う）。

ローカルの `openclaw-skills/` や本 MD は「やること一覧・仕様のメモ」として参照するだけ。**適用は VPS に対して行う。** 結果として「正しい状態は VPS にしかない」形にし、二重管理や「ローカルだけ直して VPS に反映し忘れ」を防ぐ。移行時は VPS から必要なファイルをまとめて取得すればよい。

---

# 9. Todo：ここをやれば fix と完全に一致する（追加しないといけない内容）

以下をすべて実施すれば、本 MD の fix が完全に反映された状態になる。実施は **VPS に SSH で接続し、エージェントが上記の編集・削除を VPS 上で行う** 形で行う。

| # | 項目 | やること |
|---|------|----------|
| 1 | **今日だけのやり直し** | 20:00 スタートで、上記 8 本（trend-hunter 2・suffering・x 2・tiktok 2・anicca-auto-development）だけを Today で登録する。 |
| 2 | **roundtable-memory-extract** | VPS の jobs から該当ジョブを削除する。daily-memory の入力に standup・cron 結果を含め、lessons-learned / diary に書く旨を SKILL か指示に明記する。スキルは残す。 |
| 3 | **hookpost-ttl-cleaner** | VPS の jobs から該当ジョブを削除する。スキルは残す。 |
| 4 | **sto-weekly-refresh** | VPS の jobs から該当ジョブを削除する。スキルも削除する。 |
| 5 | **VPS を本番唯一に** | fix の適用は VPS 上のファイルを直接編集して行う。ローカルは参照用のみとし、sync で「上書きする」運用にしない。 |
| 6 | **（必要なら）ops-heartbeat / mission-worker** | 「steps に積んで順にやる」流れを有効にする場合は、heartbeat が steps に 1 件ずつ積む条件と、mission-worker の cron を有効にすることを別途 Todo に書く。本 Todo の必須完了には含めない。 |