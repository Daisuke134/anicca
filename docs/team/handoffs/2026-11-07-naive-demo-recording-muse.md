# Naïve Autonomous Company Hackathon handoff

## 目的と募集条件

Naïve SDKで作ったエージェントが実際の会社業務を行い、成果・判断・人の介入箇所をデモする。ユーザー共有の募集文では「全チームNaïve SDKを使用」が必須で、会場でlive demoを行う。全業務をNaïve Computer上にhostするとは書かれていない。外部runtimeが許可されるとも書かれていないため、正確な線引きは「SDK必須、host場所は募集文で未規定」。Naïve Computerは任意のmanaged execution resource。

Mac Mini上のChromeはNaïve UIの表示・録画端末として使える。実際の業務をNaïve SDK agentが実行するなら、録画場所とbusiness runtimeは別物。確実性を高める構成としてNaïve SDK agentから業務を実行し、必要な作業にNaïve Computerを使う。会場でのlive demoがイベント文面の明示条件。YouTube動画はユーザーから依頼された追加成果で、募集文で必須とは確認できていない。

基本の構造は `Naïve Agent (model + 指示 + tools + budget) → Naïve Session (実行) → 必要なら agent所有のNaïve Computer (shell/filesystem、browserは任意)`。ComputerはAgentの複数session間で共有される作業VM。イベントはNaïve SDKの利用を必須にするが、全処理をComputerに置くとは指定していない。Mac Mini ChromeはNaïveのAgent/Session画面を見せて録画する端末であり、事業処理を行う実行機ではない。Naïve agentが作業していない録画をハッカソン実演として見せない。

## 検証済み状態

- Repo: `Daisuke134/life-manager`
- Worktree: `/Users/anicca/Projects/life-manager-main/.worktrees/naive-x402-payapi-20261107`
- Branch: `docs/naive-x402-payapi-20261107`
- Canonical TODO: `docs/superpowers/specs/2026-09-25-life-manager-unified-ssot.md`, section `Naïve大会専用lane`; cursor LC60.
- Naïve agent `naive-capafy-cloud-operator` (`agt_y3zd3mkztbr079xc7xsg7wq5c7`) is v6, DeepSeek V4.1 Flash, monthly budget $3 and per-task cap $1. Its enabled tools are `ls/read/write/browser/web_search`.
- Agent-owned Computer `cmp_01a1b658564571ad9854c1c89c549e03` has the target agent bound. It was paused at the earlier readback; the newer session successfully wrote files to its filesystem.
- Latest session `ses_v5m6p0nc6ge45vbpzvrwc10ma` is idle, references that Computer, and has `identity_id=null`. It used Naïve filesystem and managed browser/web_search tools, but did not publish a product. Browser calls timed out seven times at 30 seconds. The session is not running now.
- Newer session `ses_dkqvna4xsce5y6a12njby7aep2` used the same Naïve agent, assigned Computer, and agent-owned identity. Provider readback after official interrupt: `idle / interrupted`, `last_seq=501`, `structured_output=null`, `$0.268339` consumed of `$0.50` task budget. It wrote a research draft and run log to `/home/naive/deliverables/telegraph-ready-body.txt` and `/home/naive/run-log.md` on the Naïve Computer. The managed browser entered a Telegraph title, but author/body actions failed and subsequent browser calls timed out. No article URL, public post, customer order, revenue, or video exists. Do not count this research draft as the Life Manager product demo.
- Agent month-to-date spend is $0.289065. Naïve organization credit balance is $19.56. These are operating resources/cost, not revenue.
- Identity `idn_75df9rsb9ehyym3z92sjwz5wat` has an active inbox owned by the target agent. The existing agent tool config does not include `email.inboxes` or `email.read`; add those before a signup flow needs agent email. The prior session did not use the identity.
- CAPAFY is excluded for this demo: its publisher certification has a $0.99 fee and identity-verification requirements. No CAPTCHA/KYC bypass, signup, fee, listing, sale, or delivery was performed.
- Screenity 4.7.2 is available in the isolated local Chrome profile and recorded a 29-second x402 endpoint clip. That clip is not a Naïve run and is not the requested demo. No valid Naïve demo has been recorded or uploaded.

## 次の作業（正本は上記spec）

1. LC60: 前払い・人間の本人確認を要求しない、利用規約上agent利用可能な公開先を一つ選び、条件を確認する。CAPAFYは再試行しない。
2. signupが必要なら既存のagent identityをsessionの`identity`に渡し、Naïveの`email.inboxes`/`email.read`を追加してagent inboxを利用可能にする。人間のcredentialsを使わず、CAPTCHA/KYCは迂回しない。
3. Naïve SDK agentで一つの実成果を作成・公開し、provider readbackでURLと内容を確認する。公開物は売上と混同しない。
4. LC60a: その後、独立顧客の注文・支払・settlement・納品が確認できる事業経路を実証する。Naïve creditsは費用。
5. LC61: 公開成果と同じNaïve SDK runをScreenityでMac MiniのNaïve UIから録画し、YouTubeで公開後URLを確認する。Mac Miniは画面表示・録画だけに使う。
6. LC62: イベントが求めるlive demoを再現できる状態にする。追加の動画提出先は公式readbackできた場合のみ記録する。

## Resume context

No valid Life Manager business artifact, customer revenue, delivery receipt, or Naïve run video exists yet. Current cursor remains LC60: choose one legitimate no-upfront route that can produce a customer-valued public deliverable, then execute it with a new Naïve SDK session. The interrupted Telegraph field-note session is resumable but has a field-note output schema; do not reuse it for the business run. Preserve the local x402 clip as unrelated historical evidence. Update this file and the canonical spec after every verified milestone.
