# Connector O1B-11 connpass API Application Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** connpass個人・コミュニティ向けAPIを正確な利用内容で申請し、key発行まではconnpass自動アクセスをコードとruntime stateの両方で禁止する。

**Architecture:** 公式v2 API以外のbrowser/scrape railを持たない。pure access policyはkey欠落時にdisabled、keyがあってもHTTPS `connpass.com/api/v2/events/`へのGET、5秒以上の間隔、Tokyo限定scheduled cacheだけを許可する。申請はDais本人専用のOSS local利用として行い、第三者操作によるreal-time call、公開key、全件収集を行わない。

## Constraints

- 公式フォーム・API help・API規約の現在値を根拠にする。
- API key、Google session、個人情報をrepo/evidence/logへ保存しない。
- key取得前にAPI requestを試さない。
- connpass browser login、scrape、RSVP自動操作は再有効化しない。
- 審査結果待ちはactive taskを止めず、申請receiptをdoneとする。

### Task 1: Access policy (TDD)

- [x] keyなし、非API rail、5秒未満、Tokyo以外、real-time user triggerを拒否するREDを追加。
- [x] scheduled cache用のexact v2 GET descriptorだけを許可する。
- [x] production configにconnpass capabilityをまだ追加しない。

### Task 2: Submit official application

- [x] 公式フォームの設問と規約を再読出しする。
- [x] truthfulなpersonal/OSS・self-only・daily cache内容で一度だけ送信する。
- [x] formResponse navigationと公式configured confirmationをsecretなしで証拠化する。

### Task 3: SSOT and delivery

- [x] live cron/launchdが全disabledのまま、正本workerにconnpass capabilityがないことを再確認する。
- [x] O1B-11完了、残数126件へspecを更新する。
- [ ] 回帰、commit、pushを完了する。
