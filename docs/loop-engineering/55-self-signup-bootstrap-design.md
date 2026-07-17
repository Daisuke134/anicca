# 55 — self-signup bootstrap 設計（調査フェーズ、2026-07-17）

対象: spec §7.55（zero-config bootstrap 原則）の実装設計。#64。**このドキュメントは調査+設計のみ
— 実アカウント作成は一切行っていない**（各プラットフォームの signup ページを crwl で閲覧のみ、
フォーム送信ゼロ）。前回パス（profitable-claude commit `975e2e9`）で Substack のみ CDP 経由で1画面を
screenshot 実測したが、それも閲覧のみで submit していない。

## 1. ig-account-create から抽出した汎用骨格

`~/.openclaw/skills/ig-account-create/SKILL.md` + `scripts/` を読解した結果、以下が
プラットフォーム非依存の再利用可能な骨格（2026-06-29 に Instagram で email-only・電話なし・
CAPTCHA なしで E2E 実証済み）:

| 要素 | 実装 | 汎用性 |
|---|---|---|
| **一意な email 生成** | Gmail plus-address（`keiodaisuke+<tag>@gmail.com`）。Gmail は `+tag` を無視して同一受信箱へ配達するため無限に一意なアドレスを生成できる。disposable email provider（agentmail.to 等）は Instagram に自動 suspend されたため使用禁止（実例: @aiclipper.daily 死亡） | 100%汎用。`scripts/gen-plus-address.sh`（profitable-claude 側、commit `975e2e9`）として既に切り出し済み |
| **OTP/magic-link 自動読取** | `gog gmail search --account keiodaisuke@gmail.com "<query> in:anywhere newer_than:1h" --max 3 --plain`。SPAM フォルダに落ちることがあるため `in:anywhere` 必須 | 100%汎用。`GOG_KEYRING_PASSWORD` env が前提 |
| **孤立ブラウザコンテキスト** | `scripts/cdp_incognito.py`（raw CDP `Target.createBrowserContext`）。共有 daily-driver（CDP :9222）が既に別アカウントでログイン済みでも、新規 signup フォームを汚染せず表示できる | 100%汎用。IG 依存コードなし（読解で確認済み、profitable-claude commit `975e2e9` のコミットメッセージにも記録） |
| **CDP 操作プリミティブ** | `scripts/cdp.py`（new/nav/shot/eval/text/url/clicksel/clickxy/insert/key/close） | 100%汎用 |
| **judgment型のDOM操作** | ハードコードされた selector に頼らず、screenshot→目視確認→クリック/入力、を1ステップずつ繰り返す。カスタム combobox は trusted mouse click が必要、React input は native setter が必要、等の site-specific gotcha は都度発見して都度対応 | 設計思想は汎用だが、**site-specific gotcha の発見自体はサイトごとに反復探索が必要**（ig-account-create 自身の SKILL.md に複数の hard-won gotcha が書かれている） |

**結論**: インフラ（email生成・OTP読取・ブラウザ隔離・CDP操作）は完全に使い回せる。プラットフォーム
ごとに固有なのは「実際のDOM構造と個別の詰まり所」のみ。

## 2. プラットフォーム別 実現可能性表（実測、2026-07-17）

| プラットフォーム | signup 方式（実測） | 電話/CAPTCHAの壁 | API token発行 | 判定 |
|---|---|---|---|---|
| **note.com** | `note.com/signup/form` は**メールアドレス＋パスワード（8文字以上英数記号）のみ**の純粋なフォーム。電話番号欄なし。Google/X/Appleとのソーシャル登録も別途あり | 未確認（signupフォーム自体に電話/CAPTCHA欄は見えないが、送信後のフローは未探索） | note.comは公式APIなし。この project の既存パイプラインは email+password → camofox セッション cookie 方式（`publish-note.sh`のlogin_with_browser、既に稼働実績あり） | **可（壁なさそう）** |
| **Dev.to** | `dev.to/enter?state=new-user` は Apple/Facebook/GitHub/Google/MyMLH/X の OAuth **または** ネイティブ email+password。ネイティブ path なら他platformのOAuth身元は不要 | 未確認（emailネイティブpathの送信後フローは未探索。Forem製サイトで既知の攻撃的anti-bot事例は無し） | **確認済み**: Foremの公式API（developers.forem.com/api）は「設定ページからユーザー自身がAPI keyを発行」方式。OAuth app登録不要、ログイン後の設定画面操作のみ | **可（壁が最も低い可能性）** |
| **Substack** | `substack.com/explore?action=signup` は**単純なemailフォームではない**。実測（CDP screenshot、2026-07-17）で最初の画面は「トピックを3つ選択」というonboarding。emailステップは未到達（探索を意図的にここで停止）。ただし既存の**ログイン**は email magic-link + `gog gmail` で実証済み（Stripe接続確認時、spec §7.3 U3） | 未確認（topic-picker以降のフローが未探索） | Substack REST APIは公開されていない（`substack-publish.py`は非公式クライアントライブラリ経由）。API token相当は無し、cookie/sessionベース | **壁あり（onboardingフローが多段、探索コスト高いが電話/CAPTCHA兆候はまだ無し）** |
| **Zenn** | ★是正: 当初「GitHub OAuthのみ」と誤認していたが実測で訂正。`zenn.dev/dashboard/deploys`（未ログイン時のSign Inウォール）は「**Googleでログイン** または **メールアドレスでログイン**」の2択。GitHubは出てこない。GitHub連携は`zenn.dev/manual`の「GitHub連携について」という**別セクション**（Publicationやコンテンツ管理のオプション機能） | 未確認 | Zenn公式APIなし。**重要な区別**: アカウント作成自体はメール/Googleのみで可能。だがこのprojectの現行`publish-zenn.sh`は「published:trueをGitHubリンク済みリポジトリにpushした瞬間に公開される」というgit-push型デプロイを使っている（実装読解で確認）。つまり**アカウント作成は電話/CAPTCHA不要でtractable**だが、**このprojectの既存publish方式で使うにはAI自身のGitHubアカウント + repo linkageが別途必要** | **アカウント作成=可、既存publish方式との連携=GitHub bootstrap要（別依存）** |
| **X (Twitter)** | このタスクの調査対象外（team-lead指示で対象4platformから除外）。前回パス(#64初回)の判断を維持: `anicca-tt-account-create`（TikTok向け、SMSPOOL_API_KEY等のDais鍵待ちでSCAFFOLDED disabled中）と同格のanti-bot tierと推定 | 推定: 電話番号必須の可能性高い（未実測） | — | **既定deferred（今回調査対象外）** |

## 3. bootstrap スクリプト設計（ステップ列・env・graceful skip）

### 3.1 共通オーケストレータ設計

```
self-signup-bootstrap.sh --platform <note|devto|substack|zenn> [--dry-run]
  1. 対象platformの既存アカウント設定を確認（.env内の該当ACCOUNT変数が既に値を持つか）
     → 既に設定済みならこのplatformはSKIP（idempotent、既存Dais環境を壊さない）
  2. gen-plus-address.sh <platform> で一意email生成
  3. platform別 signup runbook（下記）を実行
     → 途中で電話番号/CAPTCHA要求を検知したら即座に中断し、
       「<platform>: 電話/CAPTCHA要求のため自動化不可、手動signupが必要」を記録して
       graceful skip（他platformの処理は継続、全体は失敗させない）
  4. 成功したら ~/.cloak/article-self-signup-<platform>.json に
     {platform, email, password, username, status:LIVE, created_at} を保存
  5. .env への書き込みはしない（§7.55: bootstrap成果物であってデフォルト値ではない）。
     生成された値をどの env var（NOTE_USER_ID等）にセットすべきかを標準出力で案内するのみ、
     実際のセットは人間 or 別の適用ステップが行う
```

### 3.2 platform別 runbook（未実装、設計のみ）

| platform | 想定ステップ | 必要env |
|---|---|---|
| note.com | ①`cdp_incognito.py new https://note.com/signup/form` ②email+password入力（native setter, IGと同じ手法） ③「同意して登録」クリック ④確認メール（`gog gmail`でOTP/確認リンク検索、query未確定=要探索） ⑤ログイン確認 | `GOG_KEYRING_PASSWORD`, `SELF_SIGNUP_GMAIL_BASE` |
| devto | ①`cdp_incognito.py new https://dev.to/enter?state=new-user` ②"OR"以下のネイティブemail/passwordフォームへ入力 ③確認メール読取 ④ログイン後、設定画面でAPI key発行（`developers.forem.com/api`記載の手順） | 同上 |
| substack | ①`cdp_incognito.py new https://substack.com/explore?action=signup` ②トピック3つ選択（適当な3つ、後で変更可能） ③（未探索）email入力ステップへ到達するまで探索継続 ④magic-link/OTP読取（既存login実装のquery パターンを流用） | 同上 |
| zenn | ①アカウント作成: `cdp_incognito.py new https://zenn.dev/enter`（要URL確定） ②「メールアドレスでログイン」を選択、新規登録フローへ ③（未探索）以降 ④**別ステップ**: GitHub bootstrap（AI自身のGitHubアカウント作成 — これ自体が別のself-signup対象で、既存publish-zenn.shのgit-push方式を使うなら必須）+ Zenn側でGitHub連携（`zenn.dev/zenn/articles/connect-to-github`の手順） | 同上 + （GitHub bootstrap用に別途 `GITHUB_*` 系） |

## 4. 未解決リスク（推測で埋めない）

| # | 未解決事項 | なぜ未解決か |
|---|---|---|
| 1 | note.com/Dev.to/Substack/Zennの各signupフォーム、email送信**後**のフロー（電話番号要求の有無、CAPTCHA有無、確認メールの正確な件名/送信元） | 今回は「signupページを見るだけ、submitしない」という明示指示のため、フォーム送信より先のステップは実測できていない |
| 2 | Substackの「トピック3つ選択」onboarding後、実際にemail入力欄が何ステップ後に出るか | 同上（探索を意図的に停止） |
| 3 | note.com/Dev.to/Substack/ZennそれぞれのToS上、自動化された（bot/script経由の）アカウント作成が明示的に禁止されているか | note.comのToSを"自動|bot|複数アカウント|不正"でgrep実測した限り、複数アカウント言及はポイント合算不可の文脈のみで明示的なbot禁止条項は発見できず。Dev.to Code of ConductはTerms of Serviceへの参照のみで本文grepでは該当条項未発見。Substack/Zennは未grep。**一般的にWebサービスのToSにはautomated meansでの登録を禁じる条文がしばしば存在するため、この「発見できず」を「許可されている」と解釈するのは誤り** — 各社ToS全文を人力で最終確認するまでグレーとして扱うべき |
| 4 | Zennの実際のsignup URL（`/enter`か`/signup`か等） | 複数URLパターンを試したが正規URLが404を返すケースがあり、SPAクライアントサイドルーティングのため静的crwlでは正確なパスを特定しきれなかった |
| 5 | note.comの確認メール/Dev.toの確認メールの`gog gmail`検索クエリ（件名・送信元ドメイン）の正確な値 | IGは"instagram in:anywhere"で確定済みだが、他platformは未確認 |

## 5. 結論・推奨

- **note.com / Dev.to は最有力候補**（signupフォーム自体に電話/CAPTCHA兆候なし、Dev.toはAPI key発行手順も確認済み）。次のライブ実装フェーズがあれば、この2つから着手するのが合理的。
- **Substack**はonboardingフローが多段で探索コストが高いが、既存login実装の資産（magic-link読取）を流用できる。
- **Zenn**は「アカウント作成」と「既存publish方式(GitHub連携)」を分離して考える必要がある。アカウント作成自体はtractableだが、GitHub bootstrapという別依存が生じる。
- **X**は今回調査対象外、既定deferredを維持。

実装フェーズ（次のTODO）は #64a(note) / #64b(devto) / #64c(substack) / #64d(zenn account) + 別途 GitHub self-signup、のように分割することを推奨（このドキュメントの§3.2がその設計叩き台）。
