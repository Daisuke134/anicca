# Connector O1B-11 connpass API Application and Access Gate Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

> Status: 実装中。

**Goal:** connpass公式v2 APIの個人・非商用利用を正直な用途で申請し、key受領まではconnpassへの全自動accessをcodeで禁止する。

**Architecture:** connpassはLumaでcoverageできない日のread-only discovery候補に限定する。公式v2 APIはGET discoveryだけで参加申込みendpointを持たず、現行connpass規約は公式API以外の自動crawler/scraper等を禁止するため、Life Managerはconnpass browser自動申込みを行わない。ローカル個人keyを将来の商用Webへ転用せず、Web版は企業契約または別の許諾済みsourceを使う。

## Verified official facts (2026-08-01)

- API v2は全endpointで`X-API-Key`必須、keyごとに1秒1request。
- 個人・コミュニティは審査制・無料・key 1本、申請審査は約5営業日。
- 個人申請は非商用同意が必須。企業利用は月額297,000円または年額3,564,000円。
- v2 referenceにevent join/apply endpointはなく、events/groups/users等のGETだけ。
- API以外の自動crawler/scraper/other accessはconnpass利用規約で禁止。
- 公式: `https://help.connpass.com/api/`, `https://connpass.com/about/api/v2/`, `https://connpass.com/term/`。

## Constraints

- 個人申請の用途はDais本人のローカル21日event discoveryだけ。第三者提供・商用利用と書かないのではなく、実際に行わない。
- event metadataを保存するならフォームへ`はい`と正直に回答する。
- key、form response edit token、account cookieをrepo、spec、logへ保存しない。
- key受領前はconnpass API、page crawl、browser registrationを0件にする。
- key受領後もAPI GET discoveryだけ。browser自動申込みは実装しない。
- O1B-20〜22のconnpass fallbackは「API discoveryのみ」へ訂正し、予約完了sourceには数えない。

### Task 1: Fail-closed API client

- [ ] keyなし、v1、非API URL、POST、1秒未満連続requestをRED→GREENで拒否する。
- [ ] v2 events GETだけを`X-API-Key` secret headerで実行するclientを追加する。
- [ ] connpass page/browser自動化が正本runtimeに無いことをauditする。
- [ ] Commit and push.

### Task 2: Truthful personal application

- [ ] Gmail/local account evidenceからconnpass usernameを特定し、connpass page自動accessをしない。
- [ ] 個人・趣味/学習、ローカル本人専用、非商用、metadata保存ありで公式Google Formを提出する。
- [ ] 提出完了pageまたはconfirmation mailをreceipt化し、form内容と照合する。
- [ ] Commit and push.

### Task 3: Pending-key state

- [ ] key受領監視はGmail read-onlyに限定し、約5営業日の審査中状態をledgerへ保存する。
- [ ] key未受領でclientが実network 0件になるlive testを行う。
- [ ] O1B-11を`submitted / awaiting_key`として完了し、O1B-12へ進む。
- [ ] Commit and push.
