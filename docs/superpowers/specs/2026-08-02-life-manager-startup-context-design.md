# Life Manager Startup Context 正本化設計

status: APPROVED
owner: Dais / Life Manager
created: 2026-08-02 JST
parent: `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`

## 1. 目的

Fundraising agentが旧Anicca製品、旧repository、旧13-product pitchを新規応募へ混入させる経路を閉じる。
新規のREADME、応募回答、deck、one-pager、Telegram報告は、repository-ownedなLife Manager startup
contextから生成し、提出前に同じ検証器を通す。過去提出物は監査履歴として不変に保つ。

Life Managerの製品定義は次で固定する。

> Life Managerは、身体・心・お金を管理し、委任された現実行動を実行してTelegramへ証拠付きで報告する
> personal managerである。

会社名を明示的に要求された時だけAniccaを会社名として答える。製品名は常にLife Managerである。

## 2. 権限モデル

```text
                         repository-owned source
              ┌────────────────────────────────────┐
              │ .agents/startup-context.json       │
              │ exact facts / links / evidence     │
              │ freshness / forbidden exact values │
              └────────────────┬───────────────────┘
                               │ validate + resolve
              ┌────────────────▼───────────────────┐
              │ .agents/product-marketing-context.md│
              │ audience / pain / positioning /     │
              │ differentiation / voice / objections│
              └────────────────┬───────────────────┘
                               │ semantic adaptation
              ┌────────────────▼───────────────────┐
              │ fundraising/application-kit/       │
              │ answers / deck / one-pager / assets│
              └────────────────┬───────────────────┘
                               │ deterministic gate
              ┌────────────────▼───────────────────┐
              │ apply-to-funder preview / submit   │
              └────────────────────────────────────┘
```

`startup-context.json`がURL、名称、状態、検証日時、証拠参照の機械的事実の正本である。
`product-marketing-context.md`は顧客、課題、語り方、差別化の意味的正本であり、変動する数値やURLを
複製しない。応募先固有の回答はこの2層と応募先公式ページのfresh evidenceから生成する。

## 3. データ契約

### 3.1 機械的事実

`.agents/startup-context.json`は最低限、次を持つ。

- `schema_version`、`context_version`、`updated_at`
- `product.name`、`company.legal_name`、両者の利用条件
- `product.one_liner`と3 organの定義
- `links.product`、`links.repository`、`links.telegram`、`links.dashboard`
- demo / founder videoの`status`、URL、最終検証日時。未検証はURLを推測せず`unverified`
- user数、revenue、動作実績などのclaimと、それぞれの証拠参照・検証日時
- 新規提出で禁止する旧product名、旧repository、旧homepageのexact values
- 秘密・個人情報を生成物へ混ぜないための公開field allowlist

数値claimは証拠参照が無い限り応募回答へ出さない。「世界中を億万長者にする」「必ず儲かる」などの
結果保証はvisionとしても外部提出文へ書かず、測定可能な支出削減、収入機会、純資産推移を扱う。

### 3.2 意味的文脈

`.agents/product-marketing-context.md`は次を持つ。

- Product Overview
- Target Audience
- Core Pain / Job to Be Done
- Physical / Mental / Financial organs
- Differentiation: assistantではなく、委任範囲で実行して証拠を返すmanager
- Alternatives / Competition
- Objections and truthful responses
- Customer language
- Brand voice
- Current proof and explicit unknowns
- Fundraising goals

外部copyではユーザーの切実さを保ちつつ、罵倒や投資収益保証には変換しない。

## 4. 生成と提出の境界

モデルが担当するもの:

- 応募先の公式説明を読み、Life Managerとの適合を判断する
- 文字数と質問意図に合わせて回答を構成する
- deck / one-pager / READMEの説明を読み手に合わせて編集する
- 過去結果から次回pitchの仮説を改善する

決定的コードが担当するもの:

- JSON schema、必須field、URL形式、freshnessの検査
- exactな旧product値・旧repository・旧homepageの遮断
- artifactに含めたcontext version/hashと生成日時の記録
- claimの証拠参照、秘密・個人情報の混入、未置換placeholderの検査
- previewとsubmitが同一artifact hashを使うことの照合

keywordの一致だけで応募先やpitchを判断しない。固定値検査は、旧URLや製品名のように意味解釈を
必要としない禁止値に限定する。

## 5. Repository layout

```text
.agents/
├── startup-context.json
└── product-marketing-context.md
fundraising/
├── application-kit/
│   ├── README.md
│   ├── answers.en.md
│   ├── answers.ja.md
│   ├── deck.md
│   ├── one-pager.md
│   └── assets.json
└── funders/
    └── yc-fall-2026.json
scripts/startup-context/
├── lib.mjs
├── audit.mjs
├── build-kit.mjs
└── export-openclaw.mjs
test/
└── startup-context.test.mjs
```

repository内を編集正本とする。`~/.openclaw/identity/application-kit`は互換export先に降格し、直接編集・
直接提出しない。`submitted/**`は過去証跡なので書換・削除しない。exportは対象fileをmanifestとhashで
限定し、履歴directoryを対象に含めない。

## 6. Linkとevidenceの扱い

2026-08-02に確認済みの初期canonical set:

- product: `https://aniccaai.com/lm`
- repository: `https://github.com/Daisuke134/life-manager`
- Telegram start: `https://t.me/LifeManagerBotbot?start=lp`
- authenticated dashboard entry: `https://aniccaai.com/dashboard`

backend health URLはhomepageにしない。demoとfounder videoは実物、アクセス権、内容をreadbackするまで
`unverified`とし、応募へ添付しない。live HTTP auditはネットワーク障害と内容不一致を分けて記録する。

## 7. READMEと応募kitのUX

README日英版の最初の画面は次の順で揃える。

1. Life Manager = body / mind / moneyを管理するpersonal manager
2. Telegramで使い、何を実行したかを人間向けの文で証拠付き報告
3. local self-hostとcloud productは同じcore
4. 現在実在する能力と開発中の能力を分離
5. self-funding / x402 / agent economyはFinancial Organの技術的能力として後段へ置く

応募kitは「一つの万能文章」を全programへ貼らない。共通factsは固定し、質問意図とprogram evidenceに
応じてmodelが回答し、最終artifactをgateする。

## 8. Failure policy

- contextがstale、矛盾、証拠不足ならsubmitしない。理由と修復taskをledgerへ残す。
- 旧Anicca product値を含む新規artifactはfail-closeする。
- 会社名として正当にAniccaが必要なfieldは、field purposeが`company_legal_name`の時だけ許可する。
- linkが落ちている時に別URLを推測して代用しない。
- private email、電話、住所、credential、非公開Calendar情報をpublic artifactへ出さない。

## 9. 移行とrollback

1. 旧current kitとactive funder configをread-only inventory化しhashを保存する。
2. repository正本とvalidatorを先に導入する。
3. READMEと新kitを生成し、旧current kitとのpreview diffを検査する。
4. apply-to-funderをcontext hash必須へ変更する。
5. 新previewが全gateを通った後だけ互換exportする。
6. 不具合時は新submitを停止し、履歴を改変せずrepository commitをrevertできる。

実応募はO1C-00Fがgreenになるまで行わない。green後はmaster specのO1B-25へ戻り、その後O1C-01から
実応募を再開する。

## 10. 完了条件

- repository-ownedな事実と意味的文脈があり、相互参照が検証される
- README日英first-viewとkitがLife Managerを同じ製品として説明する
- canonical URLがlive readbackされ、demo/videoの未知が正直に表現される
- 新規artifactに旧製品値、秘密、PII、未証明claim、placeholderが入るとtestが失敗する
- apply-to-funder previewがcontext version/hashを持ち、古いsourceから直接submitできない
- tests、audit、preview、master spec更新、commit、pushが揃う

