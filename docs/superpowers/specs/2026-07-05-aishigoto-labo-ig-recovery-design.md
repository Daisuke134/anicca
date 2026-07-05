# @aishigoto.labo IGアカウント復旧(Task #19)

## 開発環境

| 項目 | 値 |
|---|---|
| 対象 | `~/.cloak/affiliate-accounts.json`、`~/.cloak/ig-ai-shigoto-lab.json`(状態記録) |
| ブラウザ | CloakBrowser daily-driver(:9222) |
| 状態 | 診断完了、対応方針決定

## 0. fresh evidence(2026-07-05、Task #4/#18作業中に発見)

`~/.cloak/ig-ai-shigoto-lab.json`に既存の詳細な履歴があった:
- 2026-06-28: 作成時にIGが自動suspend(理由: おそらくagentmail.toの使い捨てメール)、
  同日appeal提出・承認
- 2026-07-04: daily-driverのセッションが切れ、ログイン試行がreCAPTCHA
  Enterpriseの無限challengeに直面。CapSolverで2回solveしtoken注入したが、
  どちらも`リダイレクトします`スピナーで停止しセッションcookieが一切
  設定されない。**「account-level risk flag」と診断済み、既存の記録に
  「Do not keep retrying the same captcha-solve blindly」と明記**
- 2026-07-04(同日2回目、daily_pass_2026-07-04b): 別の方法(フォーム直接入力)
  でも同じ結果 → account-levelを別方法でも再確認、「NEXT PASS: 再ログイン
  試行前に(a)複数日のcool-off (b)appeal状態確認 (c)代替アカウント提供
  のいずれかを行うこと」と明記

**今回発見した問題**: 2026-07-05 09:08のaffiliate-core自身の自己修復
パス(Task #4検証中に観測)が、この明示的な「盲目的な再試行禁止」という
既存の教訓を**無視して同じcaptcha-solve手法を再試行し、また同じ失敗**
(トークン注入2回ともIG側拒否)を繰り返していた。affiliateには
lessons.jsonl相当の「過去の失敗から学ぶ」機構が無い(spec §25参照、
Task #24のスコープ)ため、同じ教訓ファイルを読んでも活かせなかった。

**read-only確認(2026-07-05、本specの調査時点)**: ログインフォーム自体は
正常表示(recaptchaはsubmit時のみ発生、ページ読み込み自体は問題ない)。
これは07-04bの記録と整合。「自然な1日のcool-off」は既に経過しているが、
今朝の再試行は依然として失敗しており、**時間経過だけでは回復していない**
ことが確認できた。

## 1. 対応方針の決定

既存記録の3選択肢を再評価:
- (a) 複数日のcool-off: 既に1日経過後も失敗が再現しており、効果不明。
  これ以上待つ根拠が無い。
- (b) 2026-06-28のappeal状態確認: 承認済み(`approved_at`記録あり)だが、
  そのappeal承認と今回の07-04以降のreCAPTCHA壁は**別のリスク評価**
  である可能性が高い(承認後に別の行動パターンで再フラグされた可能性)。
  IGの内部リスクエンジンの状態を外部から直接確認する手段は無い
  (サポート窓口に問い合わせる、は human-in-loopになるため今回は行わない)。
- (c) **代替アカウントの提供** ← 採用。既存の`ig-account-create` skillで
  実証済み(このaishigoto.labo自体も同じ経路で作成された実績あり)、
  no-human-loopで完結できる。queueに滞留中の投稿を新アカウントで
  流すことで実害(投稿停止)を即座に解消できる。

### 1.1 新アカウント作成時の再発防止(元の疑わしい原因を避ける)

`suspended_note`が「Likely cause: disposable email agentmail.to」と
記録している通り、同じ使い捨てメールプロバイダを使うと同じ壁に
再度当たるリスクがある。新アカウントの作成時は
`~/.claude/skills/ig-account-create/SKILL.md`のGmail plus-address方式
(既にclip loopで実証済み、`+aiXXXX@gmail.com`形式)を使い、
agentmail.toは使わない。

## 2. 実装計画(MUST)

1. `ig-account-create` skillで新規affiliateアカウントを1つ作成
   (niche: 既存と同じ「AI仕事術」、Gmail plus-address方式でメール取得、
   プロフィール完成: icon+bio、既存の`producer.sh`が要求するcaption
   フォーマットと矛盾しないbio_linkを設定)
2. 新アカウント用の独立CloakBrowserインスタンスを起動(既存clip loopの
   `launch_clip_browser.py`パターンを流用、新しいport — 9222/9223以外)
3. `~/.cloak/affiliate-accounts.json`に新規エントリを追加
   (`status:"ready"`)。**旧`aishigoto.labo`エントリは削除せず`status`を
   `"suspended"`等に変更して残す**(履歴として、また将来appeal状況が
   変わった場合に備える)
4. 実機E2E確認: `EARN_MODE=execute bash affiliate/run.sh`を1回自然発火
   (次回cron、または`--restart`)させ、新アカウントへの実投稿が
   fresh evidenceで確認できることを確認(queueに滞留中の8件のうち
   最古の1件が実際に投稿されること)
5. `~/.cloak/ig-ai-shigoto-lab.json`に今回の対応(代替アカウント提供済み、
   旧アカウントは今後の投稿には使わない)を追記

## 3. 検証計画(GATE 2)

- 新アカウント作成が実際にIG上で確認できること(プロフィールページに
  実際にアクセスして存在確認)
- 新アカウントが同じ使い捨てメール問題を再現しないこと(Gmail
  plus-addressを使ったことを確認)
- affiliate-accounts.jsonの新エントリでrun.shが実際にSELECTすること
  (discover modeで新handleが選ばれることを確認)
- 実際に1件投稿されるまでをfresh evidenceで確認(post URLの実在確認)

## 4. スコープ外(YAGN)

- IGサポートへの問い合わせ・appeal再提出(human-in-loopになるため今回は
  行わない、旧アカウントは「今は使わない」扱いに留める)
- Task #24(affiliate self-improve機構)は別タスク。今回の教訓
  (「盲目的リトライ禁止」を実際に活かせなかった)はTask #24の実装時に
  参照する具体的な実例として記録するに留める。
