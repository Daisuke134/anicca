---
name: anicca-dentist-quarterly
description: 3 ヶ月毎に Dais の歯科受診を予約する skill (信濃町近郊・team428.com「デンタルアソシエイツ歯科四谷」)。土曜午前のみ、9-17 平日本業ブロック避ける。
version: 0.1.0
---

# anicca-dentist-quarterly

## What

team428.com (デンタルアソシエイツ歯科四谷、新宿区四谷1-8-14、四ツ谷駅徒歩1分)
で 3 ヶ月毎に定期メンテナンス予約。

## Recipe — exact way (with known gotcha)

### Step 1: 候補日 4 つ生成

- 土曜午前 10:00 (HARD RULE #4: 平日 9-17 本業 NG、団体土曜は 9-13 のみ営業)
- 候補は 4-8 週後の土曜 4 連続
- gcal で他予定と被らないか確認

### Step 2: 公式 form を試す (broken の可能性あり)

```bash
camofox tab → http://www.team428.com/contact/index.html
JS で input[name={{profile.lateness.stakeholders.channel}}/姓/名/性別/電話番号/_第一希望日/...] を native value setter で fill
button_mfp_goconfirm をクリック → 確認ページ
button#rcmbtn-something (or "SEND") をクリック → 送信
```

### 🔴 KNOWN ISSUE (2026-05-11 確定)

team428 form の `send.cgi` が **Perl @INC エラーで壊れてる**:
> Can't locate functions.cgi in @INC ... at send.cgi line 5

確認 modal の SEND 押しても送信されず、URL は `/contact/mailformpro/send.cgi` に飛ぶが、
サーバー側がエラー画面を返す。webmaster は `brs-support@xbit.jp`。

### Step 3: form broken → {{profile.lateness.stakeholders.channel}} backup (proven path)

```bash
gog -a {{profile.contact.personalEmail}} gmail send \
  --to "brs-support@xbit.jp" \
  --subject "【お問い合わせフォーム不具合のため】デンタルアソシエイツ歯科四谷 予約申込み (土曜午前) — <your-name>" \
  --body-file /tmp/dentist-request.txt
```

本文テンプレート (土曜午前 4 候補日):

```
デンタルアソシエイツ歯科四谷 ご担当者様

お世話になっております。<your-address>在住の患者の<your-name> (<your-name>) と申します。
いつもお世話になっておりますクリニックにて、メンテナンス受診の予約をお願いしたくご連絡差し上げました。

公式サイト (http://www.team428.com/contact/index.html) のお問い合わせフォームから
送信を試みましたが、確認画面の送信ボタン押下後に Perl のサーバーエラー (send.cgi 
@INC functions.cgi が見つからない旨) が表示され、送信が完了しませんでした。

【予約内容】
- 受診目的: メンテナンス (歯石除去 / クリーニング)
- 患者氏名: <your-name> (<your-name>)
- メール: {{profile.contact.personalEmail}}
- 電話: 080-4627-0314
- 性別: 男性

【ご予約希望日 (土曜午前 10時)】
第一希望: YYYY/MM/DD (土) 10:00
第二希望: ...
第三希望: ...
第四希望: ...

平日は本業の都合 9:00-17:00 が NG のため、土曜午前帯で調整いただけますと幸いです。

何卒よろしくお願い申し上げます。

<your-name> / {{profile.contact.personalEmail}} / 080-4627-0314
```

### Step 4: gcal に [PENDING] event 追加

返信が来て日程確定したら mail-auto-reply 経由 or 手動で [CONFIRMED] にする。

### Step 5: Slack 報告

## Cron

3 ヶ月毎 (Feb / May / Aug / Nov の 1 日 09:00 JST、9-17 ブロック外)。
`cron 0 9 1 2,5,8,11 *`

## ガード

- <training-school> 一切書かない (HARD RULE #4)
- 平日 9-17 NG 必ず厳守
- 既に直近で受診してたら skip
- Cal で被ってる土曜は別の土曜を選ぶ
