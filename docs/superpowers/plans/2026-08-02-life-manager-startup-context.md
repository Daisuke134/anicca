# Life Manager Startup Context 実装計画

> **実行規則:** Superpowersの`executing-plans`と`test-driven-development`を使い、各taskをRED→GREEN→整理→spec更新→commit/pushの順で完了する。

**Goal:** 新規Fundraising artifactとREADMEをLife Manager正本から生成・検証し、旧Anicca product文脈を提出不能にする。

**Architecture:** `.agents/startup-context.json`がexact facts、`.agents/product-marketing-context.md`がsemantic positioningを所有する。Nodeの小さなloader/auditor/builderがschema・freshness・証拠・禁止値・PII・artifact hashを検証し、fundraising kitとapply-to-funder previewを同じcontextへ接続する。

**Tech Stack:** Node.js ESM、`node:test`、標準`fetch`/`crypto`/`fs`、Markdown、JSON。

---

## Task 1: Context contractとloader

**Files:** `.agents/startup-context.json`、`.agents/product-marketing-context.md`、`scripts/startup-context/lib.mjs`、`test/startup-context.test.mjs`

1. 存在しないfield、product/company混同、証拠なしclaimを拒否するtestを書く。
2. `node --test test/startup-context.test.mjs`でREDを確認する。
3. `loadStartupContext(path)`、`validateStartupContext(context)`、`contextDigest(context)`を最小実装する。
4. approved designのLife Manager factsとmarketing contextを追加する。private PIIは含めない。
5. testをGREENにする。
6. master specのO1C-00Aを実測内容付きで更新し、対象fileだけcommit/pushする。

## Task 2: Link freshnessとcontradiction audit

**Files:** `scripts/startup-context/lib.mjs`、`scripts/startup-context/audit.mjs`、`test/startup-context.test.mjs`、`.agents/startup-context.json`、`package.json`

1. canonical URL、stale timestamp、旧exact URL/name、unverified demo/videoを検出するtestを書く。
2. `auditStartupContext`とCLIを実装し、`npm run audit:startup-context`を追加する。
3. product/repository/Telegram/dashboardをlive readbackし、status・日時・evidenceを更新する。
4. demo/videoは実物を検証できない限り`unverified`のままにする。
5. testとauditをGREENにし、O1C-00Bの実測をmaster specへ反映してcommit/pushする。

## Task 3: README日英first-view

**Files:** `README.md`、`README.ja.md`、`test/startup-context.test.mjs`

1. 両READMEのfirst-viewにproduct名、3 organs、Telegram、local/cloud同一coreが必要なtestを書く。
2. 現状でREDを確認する。
3. 冒頭をLife Manager product storyへ書き換え、self-funding/x402をFinancial Organの技術能力として後段へ移す。
4. 実装済みと開発中を正確に分離し、収益保証をしない。
5. test GREEN後、O1C-00Cを更新してcommit/pushする。

## Task 4: Repository-owned application kit

**Files:** `fundraising/application-kit/{README.md,answers.en.md,answers.ja.md,deck.md,one-pager.md,assets.json}`、`scripts/startup-context/build-kit.mjs`、`test/startup-context.test.mjs`

1. 全artifactにcontext version/hash、Life Manager story、証拠付きclaimが必要なtestを書く。
2. old product/repository、PII、placeholderを入れたfixtureがfailするtestを書く。
3. contextからkitを再現可能にbuildするscriptと生成物を追加する。
4. 日英回答、deck、one-pagerを現行Life Manager事実だけで生成する。
5. testと再生成diffなしを確認し、O1C-00Dを更新してcommit/pushする。

## Task 5: apply-to-funder context gate

**Files:** `fundraising/funders/yc-fall-2026.json`、`skills/apply-to-funder/{SKILL.md,preview.mjs,lib/context.mjs,__tests__/context.test.mjs}`、`scripts/startup-context/export-openclaw.mjs`、`package.json`

1. context hash無し、旧product値、stale context、未検証video、preview/hash不一致を拒否するtestを書く。
2. canonical contextだけを読むfunder context compilerとpreviewを実装する。
3. YC configは質問・文字制約・program evidenceだけを持ち、company factsを複製しない。
4. OpenClaw互換exportは明示file allowlistとmanifestを使い、`submitted/**`を絶対に変更しない。
5. previewを生成し、actual submitはO1C-00F完了まで禁止する。
6. test GREEN後、O1C-00Eを更新してcommit/pushする。

## Task 6: Full regression gateと引継ぎ

**Files:** `test/startup-context.test.mjs`、`skills/apply-to-funder/__tests__/context.test.mjs`、master spec、`docs/evidence/fundraising/2026-08-02-startup-context-audit.json`

1. 関連する全node testを実行する。
2. `npm run audit:startup-context`でlive URLとartifact auditの証拠を保存する。
3. `npm run build:fundraising-kit`を2回実行し、2回目がclean diffであることを確認する。
4. `npm run preview:funder -- --funder yc-fall-2026`でcontext version/hashと全gate通過を確認する。
5. 秘密・PIIを出力していないことを確認する。
6. O1C-00Fを完了し、master specの現在地をO1B-25へ戻す。
7. 対象fileだけcommit/pushし、local HEADとorigin/main一致をreadbackする。

