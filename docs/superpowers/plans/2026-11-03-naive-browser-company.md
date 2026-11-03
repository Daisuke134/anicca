# Naïve browser company Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans。primaryが単独実装し、最後にfresh read-only reviewを使う。

**Goal:** Naïve自身のbrowserをLLMが操作して既存の会社業務を完走する。
**Architecture:** 標準pi agentの外部操作はbrowser、Computer read/writeは作業メモと成果物に使い、判断は自然言語promptへ置く。APIは基盤設定/実行/証拠読取に限定する。
**Tech Stack:** Naïve標準agent/session/browser、JSON設定。追加依存なし。
**Spec:** docs/superpowers/specs/2026-09-25-life-manager-unified-ssot.md の Naïve browser company 節。

## Global Constraints
- 既存owner・共有profile・既存6agent/cronを変更しない。
- 専用cap月0.50USD/max_task0.50USD、追加入金なし。
- 秘密値はSSOTとproviderの専用credential経路のみ。modelへ値を送らない。
- business script/APIはagentへ与えない。scopeはbrowserによる画面操作。

## Review Focus
- deny defaultでもask-default toolが残るため既知の追加能力を明示disableする。
- config/終了文だけを成功にせずbrowser tool eventと遷移後の画面を確認する。
- agent/session/Computerの所有者と保存状態を区別する。
- 応答消失時は同じ外部操作を繰り返さず状態を読む。
- 認証と共有writerの未照合は具体的な不足境界として残す。

## Tasks
- [x] BROWSER01: config/naive-browser-company.jsonと正本specを作成、JSON/権限/予算assert・fresh review・push/CI/main統合。
- [ ] BROWSER02: merged mainの固定revisionから専用agentを適用。公式readback後に有限sessionを起動し、browserの観測/click/type結果と実費を取得。
- [ ] BROWSER03: 既存credential/本人担当の回答を照合。loginの前に専用identityを確定し、browserが閉じたComputerから空contextを作り、agent id限定grantを設定する。context_nameとpersist_context:trueの新versionをmainから適用し、同identityでsessionを開始してprovider専用login経路で認証する。一業務の実画面結果を公式readback。
- [ ] BROWSER04: 同担当の保存/再開を確認し、対象のwriterを重複させずhosted継続運転へ接続。

## Decisions and evidence
- Daisは質問なしで最後までの実行を指示しているため、skillの対話/再承認要求は実行停止にしない。
- Astra専用経路は親model/effortを観測できず、指定旧modelは現toolに無い。UI選択を変更せず通常の単独実装とread-only reviewを使う。
- source acceptanceは最小JSON/schema/権限assertとprovider readback。固定JSONの写経テストや新しいagent loopは作らない。

- Review修正: 公式ask-default既知16toolを明示disable/denyし、login前の空context/identity/grant準備をBROWSER03へ移す。初回BROWSER02は未認証の画面操作だけなのでcontext_name無しの定義を使う。

- 実測修復: 画像返却直後のvalidation_failed、画像無し試行のsession cap停止を別の失敗として保持。月cap維持でmax_taskを0.50へ変更し、Computerのread/writeによる作業メモを追加する。外部操作はbrowserのみ、shell/APIは引き続きdeny。
