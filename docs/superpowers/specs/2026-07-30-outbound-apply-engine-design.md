# Outbound Apply Engine — 設計 SSOT (2026-07-30)

status: ACTIVE / 実装未着手 (P0 から番号順)
owner: Life Manager (canonical runtime = `/Users/operator/Projects/life-manager-main`)
関連 spec: `2026-07-19-anicca-one-repo-consolidation-spec.md` (repo layout / OSS 不変条件),
`.worktrees/job-profile-targets/docs/superpowers/specs/2026-07-28-job-search-loop-design.md` (Job pack)

---

## 1. Goal

Life Manager が **人間をループに入れずに「外に応募し続ける」** 単一エンジンを持つ。
対象は3つ、しかし **エージェントは3つではない。config が3つ**。

| pack | 何に応募するか | 個人固有の config |
|---|---|---|
| `events` | Luma / connpass のイベント参加 + **LT(登壇)枠** | 興味タグ・地域・登壇テーマ |
| `funders` | アクセラレータ / VC プログラム / 投資家 cold outbound | プロダクト・トラクション・応募 Q&A |
| `jobs` | 求人応募 + 面接調整 | 年収下限700万 / 中心1000万 / 勤務地 / 就労権 |

done (このspec全体):
```
done = "3 pack すべてが、実 side-effect の証拠(E1/E2/E3)付きで週次に成果を出し、
        Telegram に届き、週次 reflection が template を実際に書き換えた履歴が残る"
```

---

## 2. 現状実測 (2026-07-30、tool 実行結果に基づく。推測ゼロ)

### 2.1 Events (連結ループ) — 2実装、片方は偽物

| 事実 | 証拠 (file:line / log) |
|---|---|
| Loop A = `profitable-claude/skills/connector/connector_fill_gaps.sh`、launchd `ai.anicca.connector-fill-gaps` 07:50、log `~/.openclaw/logs/connector-fill-gaps.log` | `connector_fill_gaps.sh:21` |
| Loop A は **12日間ゼロ成果**。直近3回すべて `rc=1`。原因はログイン切れ | log `--- done ... rc=1 ---`、attempt stdout に `ログイン・新規登録` / `検索結果 (0件)`。ledger `skills/connector/state/applications.jsonl` 最終行 2026-07-18 |
| Loop A は嘘はついていない (evidence_gate.py / PNG magic-number / post-insert calendar verify あり) が、**死亡が報告されていない** | `event_apply_wrapper.py:147-155`、`register_and_calendar.py:143` |
| Loop A の 404 原因 = カレンダーの summary/description に `/join/complete/` (一発 POST 結果 URL) を入れている | `gcal_write.py:135`, `:140` |
| Loop B = `.openclaw/skills/anicca-meetup-talk-applier/scripts/connpass-lt-discover.py`、cron `connpass-lt-apply-daily` 09:30 | cron id `connpass-lt-apply-daily-1779342348769` |
| **Loop B は偽物**: 成功判定が DOM テキストの regex で、`キャンセル` を含む → 「キャンセルポリシー」に必ず当たり常に True | `connpass-lt-discover.py:166` |
| その未検証 bool のまま無条件でカレンダー作成 | `connpass-lt-discover.py:283`, `:302-307` |
| Loop B は subdomain を捕捉して捨て、404 URL を生成する | `:227` で捕捉 → `:239` で `https://connpass.com/event/<id>/` に再構築 |
| Loop B は一度も出力ファイルを作っていない (`data/connpass` ディレクトリが存在しない) | `:22` の DATA パスが未作成 |
| **QR / チケット取得・Telegram 画像送信は両方に存在しない** (未実装であってバグではない) | `grep -i 'qr|ticket|チケット|sendPhoto'` → 0 hit。`telegram_payload.py:28-30` はテキスト専用 |
| 確認メール検証器は存在するが **本番から誰も呼んでいない** | `registration_confirmation_classify.py` の呼び出し元 = docstring と自テストのみ |

### 2.2 Funders

| 事実 | 証拠 |
|---|---|
| `~/.openclaw/skills/apply-to-funder/` が唯一 cron 登録されている apply skill | `cron/jobs.json` job `accelerator-application-monthly-1777948324077`, `0 12 1 * *` JST, enabled |
| しかし **一度も走っていない** (`"state": {}`) | 同 job |
| 旧 `apply-to-yc/` は DEPRECATED 自己申告済 | `apply-to-yc/SKILL.md` 冒頭 |
| `opportunity-apply-vc` は cron 参照ゼロ = 死亡、`last_run: 2026-06-04` | `skills/opportunity-apply-vc/data/state.json` |
| 実績台帳 = `~/.openclaw/workspace/funders/funder-ledger.jsonl` 53行、最終 2026-06-10。Antler Japan / Techstars Tokyo / 500 Global / Plug and Play Japan / WiL / Samurai Incubate 等が SUBMITTED 済 | 同 file |
| **資産の中核** = `~/.openclaw/identity/application-kit/` (KIT.md, answers/q01..q10 × en/ja, deck, onepager, videos, submitted/INDEX.md)。最新提出 2026-07-22 | 同 dir |
| cold email cron 3本 enabled だが **state は 2026-06-09 で停止** = 静かな死 | `skills/anicca-corey-cold-email/state/sent-*.jsonl` |
| apply 系に **自己改善機構は1つも存在しない**。ledger を読んで prompt を書き換える経路ゼロ | grep 全域 |
| 拒否/返信を第一級 status として持つ state ファイルが無い (自由文の `reason`/`blocker` のみ) | `funder-ledger.jsonl` |

### 2.3 Jobs

worktree `anicca-project/.worktrees/job-profile-targets`。focused test 18/18 PASS、全203テストは中断。
未完: 全テスト再走 / 実環境 healthcheck / commit-push-PR-CI-merge / canonical runtime 反映 / 実 daily run での `700万未満 reject・1000万 target` 検証。
後続: 11D Guardian, 11E Lifecycle, 11F summary.v2, 実 Ashby/Workday 応募各1件, 面接メール→Calendar E2E。

### 2.4 既存の再利用可能資産

| 資産 | パス | 用途 |
|---|---|---|
| 雛形ループ (cloud まで通っている唯一の型) | `apps/life-manager/scripts/financial-report-boot.sh` → `lib/financial-report-runtime.js` → `lib/telegram.js` → `migrations/*.sql` → `*.test.js` → `scripts/install-financial-report-launchd.sh` | P0 はこれを丸ごと複製 |
| Telegram 送信 (cloud portable、chat_id は DB 由来) | `apps/life-manager/lib/telegram.js:19-20`、tenant 解決 `financial-report-runtime.js:49-50` (`lm_users.telegram_chat_id`) | 全 pack の報告 |
| Guardian / 死活監視 | `skills/self/healthcheck-runtime-loop.sh:50-54` (DEAD/STALE/OK)、`skills/self/self-fix.sh` | 「12日間死んでいた」の再発防止 |
| 自己改善の手本 | `~/.openclaw/skills/ai-entity-article-writer/scripts/self-improve.sh:352-416` (measure→learn→apply→keep/revert、`state/playbook.json`、7日未満は学習しない `:380`) | P4 の設計元 |
| eval harness | `apps/life-manager/eval/*.js` + `*.jsonl`、`npm run eval` | pack の qualify 判定を eval 化 |
| 証拠ゲート | `skills/connector/.../evidence_gate.py` (PNG magic-number + ≥5000 byte) | E2 に流用 |

---

## 3. アーキテクチャ

### 3.1 単一パイプライン (全 pack 共通、6段)

```
DISCOVER → QUALIFY → ACT → EVIDENCE GATE → TRACK → LEARN
```

| 段 | 責務 | 判断主体 |
|---|---|---|
| DISCOVER | source から候補を取る (Luma / connpass API / funder registry / job boards) | 決定的コード (provider adapter) |
| QUALIFY | 応募すべきか。denylist / 条件 / 重複 | **LLM 判断** (regex hardcode 禁止)、denylist のみ決定的 |
| ACT | 実際にフォーム送信 / RSVP / メール送信 | browser (CloakBrowser daily-driver) or API |
| EVIDENCE GATE | §4。証拠が揃わなければ **failed** | 決定的コード。**自己改善が書き換え不可** |
| TRACK | 返信・合否・面接日程を拾う (Gmail 実読) | LLM 分類 + 決定的 state 書き込み |
| LEARN | 週次 reflection、template 更新 | LLM (§6) |

### 3.2 配置 (consolidation spec §6.1 準拠)

| 層 | パス |
|---|---|
| エンジン | `runtime/loop/outbound/` |
| 冪等 / lease / receipt | `packages/job-protocol/` |
| provider I/O | `adapters/providers/{luma,connpass,gmail,cloakbrowser,form-filler}/` |
| config pack | `skills/life-manager/outbound/{events,funders,jobs}/` |
| 製品 entrypoint + test + eval | `apps/life-manager/{scripts,lib,test,eval}/` |
| durable state | Supabase (`adapters/state/supabase/`)。ローカル scratch は `~/.openclaw/state/outbound/` |
| spec | 本ファイル。証跡は `docs/evidence/outbound/` |

**repo に state を置かない** (OSS-3)。local と cloud は **同一 commit / 同一エンジン** (OSS-2)。

---

## 4. Evidence Contract (嘘を物理的に不可能にする層)

成功は **E1 ∧ E2 ∧ E3** が揃った時のみ。1つでも欠ければ `status=failed` + 理由を Telegram。

| # | 必須証拠 | 実装 |
|---|---|---|
| E1 | 外部システムの応答: HTTP 2xx receipt / **Gmail で実読した確認メール** / ticket ID | `registration_confirmation_classify.py` を本番配線 (現在は死にコード) |
| E2 | artifact: 確認画面 PNG (magic-number + ≥5000 byte) | 既存 `evidence_gate.py` 流用 |
| E3 | canonical URL が HEAD で 200。`/join/complete/` 系の一発 URL 禁止、subdomain 保持 | `gcal_write.py:135` と `connpass-lt-discover.py:239` の修正 |

禁止事項 (違反 = 即 revert):
- DOM テキストの文字列/regex マッチで成功を宣言する行を **1つも残さない** (`connpass-lt-discover.py:166` は削除)
- 自分が生成したテキストを自分で読んで成功と判定しない
- 証拠なしでカレンダー / ledger / Telegram に「完了」を書かない

**自己改善の書き込み権限**: template / targeting / cadence の config のみ。
`runtime/loop/outbound/evidence/**` は self-improve から **read-only**。
(報酬を「verified evidence 件数」にしても、ゲートを緩める方向の学習だけは構造的に禁止する)

---

## 5. QR / チケット配送 (Dais 要求の中核)

| 経路 | 取得方法 | 根拠 |
|---|---|---|
| Luma (主) | RSVP → 確認メール着信 → `gog gmail` で実読 → チケット QR (`g-` prefix の guest key を含む URL) → Telegram `sendPhoto` | help.luma.com/p/event-registration-process 「we send the guest a registration confirmation email with a calendar invite」 / p/external-check-in-integration 「All Luma check-in QR codes follow this format ... String starting with `g-` prefix」 |
| connpass (従) | 受付番号/QR はサイト上のみ → ログイン済 daily-driver でチケットページを screenshot → Telegram 画像送信 | connpass API v2 は全 GET、チケット object 無し |

**Dais 側の必要物 = Telegram のみ**。Luma アプリ / connpass アプリ / 認証情報の提供は不要。
カレンダーには canonical event URL (200 検証済) を入れる。

---

## 6. 自己改善層 (eval engineering)

報酬がスパースかつ遅延する (返信・合否が数週間後)。採用する機構:

| 出典 | 採用する仕組み |
|---|---|
| Anthropic「Writing effective tools for agents」 | 「Each evaluation prompt should be paired with a **verifiable response or outcome**」/「Simply **concatenate the transcripts** ... and paste them into Claude Code」/「We relied on **held-out test sets** to ensure we did not overfit」 |
| DSPy **GEPA** | 「uses LLMs to **reflect on structured execution traces** (inputs, outputs, failures, feedback) ... proposing a new instruction tailored to real observed failures」/「can leverage **any textual feedback**—not just scalar rewards」/「maintains a **Pareto frontier**」 |

実装:

```
trace 1行 = {ts, pack, segment, target, template_variant, sent_at,
             evidence{e1,e2,e3}, outcome, outcome_at, reply_text}

日次   : trace 追記のみ (jsonl → Supabase)
週次   : 勝ち trace + 負け trace + 返信本文の原文 を LLM に渡す
         → 出力 = 「次の1仮説 + template 差分」 (playbook.json と同型)
segment: YC系 / 日本VC / Luma LT / 海外remote求人 ... ごとに Pareto 保持
ガード : 7日分未満のデータでは学習しない / hold-out 20% は旧 template 維持
報酬   : verified evidence 件数 (返信率ではない)
```

Cold outbound の型 (実測 BP):
- TechCrunch (Kamps): 3段落・デッキ添付しない・「Good cold emailing is all about **targeting very carefully, not sending out hundreds**」
- OpenVC: 件名60字未満 / 本文1000字未満 /「the longer the email, the less reply you get」/ フォローアップは3〜7日空けて最大2回 / デッキ開封済で無返信なら「take the L and move on」

→ **量産しない。1日3〜5通の精密射撃 + 自動フォローアップ最大2回**。

---

## 7. 制約 (実測、隠さない)

| 事実 | 引用 | 設計への影響 |
|---|---|---|
| YC は締切後も受け付ける | ycombinator.com/apply 「we are still accepting late applications」/ FAQ 「We fund many companies that apply late every batch」 | **Fall 2026 に今すぐ出す**。P2 の1発目 |
| YC は1分の創業者動画必須 | YC library 6t 「it should be a minute long, all the founders should be in the video, and people don't do that」 | application-kit の videos/ を使う |
| connpass は API 以外の自動アクセスを禁止 | connpass.com/about/api/ 「提供されているAPI以外の手段（自動化の有無にかかわらず）で ... アクセスを行う、または試みる行為は、利用規約により禁止」 | 発見 = 公式 API (要 key, 1 req/sec)。RSVP = **人間速度**のブラウザ、Anicca 自身のアカウント。バースト禁止。**Luma を主・connpass を従** |
| Luma API は主催者側のみ | docs.luma.com 「programmatically manage **your** events and guests」/「you need a **Luma Plus** subscription」 | 参加側 RSVP は daily-driver ブラウザ一択 |
| LT枠は構造化フィールドが存在しない | connpass API に発表枠フラグ無し / Sessionize は read-only JSON API / PaperCall は公開 API 無し | LT 判定は本文を **LLM に読ませる** (regex 禁止) |
| MUFG 系は応募禁止 (Dais の勤務先) | mucap.co.jp のヘッダに MUFG ロゴ、フッタに三菱UFJ銀行 | denylist: `三菱UFJ` `MUFG` `MUCAP` `MUIP` `Mitsubishi UFJ`。加えて **プログラムのコーポレートパートナー名簿を提出前に毎回チェック** (1stRound 等は名簿未検証のため機械ゲート化) |
| 英語圏優先 | Dais 指示 | qualify の重み付けで en > ja、ただし ja も除外しない |

---

## 8. TODO 表 (順序の正本。番号順に着手、飛ばさない)

| # | P | タスク | done 条件 (これ以外を done と呼ばない) |
|---:|---|---|---|
| 1 | P0 | `runtime/loop/outbound/` エンジン骨格を financial-report から複製 (boot.sh / runtime.js / migrations / test / launchd installer) | `npm test` 緑 + launchd 登録 + heartbeat `~/.openclaw/state/.outbound-last-pass` 更新 |
| 2 | P0 | Evidence Contract E1/E2/E3 を独立モジュール化 (self-improve から read-only) | 単体テストで「証拠欠落 → failed」が3ケース PASS |
| 3 | P0 | Telegram 画像送信 (`sendPhoto`) を `lib/telegram.js` に追加 | Dais の Telegram にテスト画像1枚が実着弾 |
| 4 | P0 | Guardian 配線 (`healthcheck-runtime-loop.sh` 登録 + STALE で self-fix) | 意図的に止めて STALE 検出 → Telegram 警告が届く |
| 5 | P1 | Loop B の偽物判定を削除 (`connpass-lt-discover.py:166` の regex を廃棄、`:302` の無条件カレンダー書き込みを撤去) | grep で成功宣言の文字列マッチが 0 hit |
| 6 | P1 | URL バグ2箇所修正 (`gcal_write.py:135/140` を canonical event URL に、`connpass-lt-discover.py:239` の subdomain 保持) | 生成された URL 10件が全部 HEAD 200 |
| 7 | P1 | Luma provider adapter (discover + RSVP via daily-driver) | 実イベント1件を RSVP、確認メールを Gmail で実読 |
| 8 | P1 | QR パイプライン (確認メール → QR 抽出 → Telegram 画像) | **Dais の Telegram に実イベントの QR 画像が届く** |
| 9 | P1 | connpass: 発見を公式 API に移行 (API key 取得含む)、RSVP は人間速度・Anicca アカウント | API 経由の発見が動き、ToS 違反のバースト経路が消える |
| 10 | P1 | LT/CFP 優先ロジック (LLM が本文から登壇枠を判定、観客枠より優先) | LT 枠のあるイベント5件を正しく分類 (eval jsonl) |
| 11 | P1 | Loop A のログイン復旧 + events pack への統合、旧2実装の退役 | 12日ゼロだった状態が解消、1週間で ≥1 件の verified 登録 |
| 12 | P2 | funders pack: `application-kit` を SSOT に配線 + funder registry 再構築 | registry から1件を選んで下書きが生成される |
| 13 | P2 | MUFG denylist + パートナー名簿チェックゲート | denylist 対象に対して応募が機械的にブロックされるテスト PASS |
| 14 | P2 | **YC Fall 2026 に late application を実提出** (1分動画込み) | 確認画面 PNG + 確認メール + ledger 1行 + Telegram 報告 |
| 15 | P2 | cold outbound 蘇生 (1日3〜5通、件名60字/本文1000字、follow-up 最大2回) | 実送信 + 送信 receipt + 3日後 follow-up が自動発火 |
| 16 | P2 | 返信・拒否を第一級 status として TRACK (Gmail 実読 → outcome 更新) | rejection / reply / meeting が state に型付きで入る |
| 17 | P3 | Job loop: 全203テスト再走 → 実環境 healthcheck → PR → CI → merge → canonical 反映 | main に merge 済 + canonical runtime が新方針で1回実走 |
| 18 | P3 | Job loop: `700万未満 reject / 1000万 target` を実 daily run で検証 | 実ログで reject/accept の判定が仕様通り |
| 19 | P3 | Job loop 11D Guardian / 11E Lifecycle / 11F summary.v2 | 各機能のテスト + 実走証拠 |
| 20 | P3 | 実 Ashby / Workday 応募 各1件 + 面接メール→Calendar E2E | 応募 receipt + カレンダー実登録 |
| 21 | P4 | trace ledger + 週次 reflection + Pareto (segment別) + hold-out 20% | 2週分の trace で template が実際に1回書き換わり keep/revert が記録される |
| 22 | P5 | cloud 化: state を Supabase、chat_id を per-tenant、local/cloud 同一 commit SHA | Railway 上で同エンジンが別ユーザー分を回し、receipt に同一 SHA |

**進め方**: 1つずつ閉じる。P1 の #8 (QR が Telegram に届く) が真になるまで P2 に入らない。

---

## 9. 一般化 (製品としての意味)

| pack | 製品になった時の一文 |
|---|---|
| events | 「知らないイベントに勝手に登録され、QR だけが届く」 |
| funders | 「YC を知らない人の代わりに YC に出す」 |
| jobs | 「50代でも学生でも、応募と面接調整が終わっている」 |

エンジンが1つなので、CFO / 投資エージェントも同じ6段に載る
(DISCOVER=銘柄, ACT=発注, EVIDENCE=約定 receipt)。作り直しは発生しない。

---

## 10. 未検証 (見える穴として残す)

| 項目 | 状態 |
|---|---|
| ANRI / Plug and Play Japan の応募形態 | headless で取得できず未検証 |
| a16z speedrun が batch か rolling か | 未検証 |
| YC の AI 生成応募に関する公式見解 | **存在を確認できなかった**。「YC が AI 応募を禁止」は未検証として扱う |
| 1stRound 等のコーポレートパートナーに MUFG が含まれるか | 未検証 → #13 の機械ゲートで提出前に毎回確認する |
| VC 連絡先のオープンデータセット | 見つからず (OpenVC 等はゲート付き商用)。プログラム的一括取得は未検証 |
