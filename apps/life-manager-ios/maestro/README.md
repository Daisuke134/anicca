# Life Manager real-provider Maestro harness

このディレクトリは、モックCalendar・fixture outbox・固定route payloadを使わないstaging E2E用です。Googleの同意/アカウント選択は外部ブラウザ面なのでMaestroの実行範囲に含めません。先に一度だけ実Google OAuthを完了し、同じiOS Keychainに保存されたセッションで以下のフローを実行します。

## 実行前の必須条件

1. Railwayの隔離staging APIへ向けてビルドされたLife ManagerをSimulatorまたはTestFlight相当の実機へインストールする。現在の隔離先は `life-call-staging-staging.up.railway.app`、Supabase refは `ulhsqqkyejzvqgoyjwte` です。
2. 外部ブラウザで実Google consent/account chooserを完了し、Calendar接続を保存する。MaestroのYAMLにはcallback URL、code、session tokenを入れません。
3. 実Calendarに、現在の時刻から18時間以内の移動先付き予定を1件だけ用意する。タイトル・場所・時刻・routeの各値はprovider readbackから取得し、YAMLへコピーしません。
4. profileにname、home、product localeを保存する。`phone`はnull、callsはdisabled、analysisはidleにする。`staging-seed-and-cleanup.sh seed`がこの状態をHTTP readbackで確認します。
5. `ROUTE_MESSAGE_ID`は、実analysis後に `/api/mobile/v1/chat` から読み取ったroute messageのopaque IDだけを指定する。推測したIDやfixture IDは使用しません。
6. `TRAVEL_RECEIPT_MESSAGE_ID`は、同じ実chat readbackで `semanticKey=chat.travel_block_confirmed` のmessageに付いた正確なopaque IDを指定する。failure flowだけを実行する場合は、`TRAVEL_FAILURE_MESSAGE_ID`に `semanticKey=chat.travel_block_not_added` の正確なIDを指定する。IDを生成・推測・fixtureからコピーしてはいけません。
7. cleanupでは、confirmed receiptの`args.providerEventId`と一致する`LM_TRAVEL_PROVIDER_EVENT_ID`、そのreceiptのID、実接続先の`LM_STAGING_CONNECTED_ACCOUNT_ID`を指定する。cleanupはそのprovider event IDだけをDELETEし、同じIDのGET 404を確認してからDB行を削除します。

`STAGING_SESSION_ID`、`TRAVEL_RECEIPT_MESSAGE_ID`、`TRAVEL_FAILURE_MESSAGE_ID`、`ROUTE_MESSAGE_ID`はMaestro実行時のプロセス環境から渡します。`LM_STAGING_BEARER_TOKEN`もseed/readbackプロセスの環境変数だけに置き、YAML、ログ、commitへ書きません。共有pre-authorizedアカウントのGoogle外部chooser/consentはMaestroの外側で一度だけ人間が完了し、MaestroはKeychainに保存済みの実sessionを使います。

アプリのKeychainを消去する `clearState` / `clearKeychain` は、pre-authorizedフローの実行コマンドにはありません。実行命令と説明コメントを混同しないよう、静的harnessはコメント行を解析対象から除外します。

## staging seed readback / cleanup

seedコマンドは「seedを作る」のではなく、実OAuth・実Calendar・実profileを読み戻して確認します。偽の成功状態は作りません。

```bash
export LM_STAGING_API_BASE_URL='https://life-call-staging-staging.up.railway.app/api/mobile/v1'
export LM_STAGING_SUPABASE_REF='ulhsqqkyejzvqgoyjwte'
export LM_STAGING_BEARER_TOKEN='(一時的なstaging session token。ファイルへ保存しない)'
export LM_STAGING_VERIFY_MODE=analysis
export LM_STAGING_EXPECTED_LOCALE=en
./staging-seed-and-cleanup.sh seed
```

route/chatのreadbackを確認するときは、analysis完了後に同じ隔離APIで実際のmessage IDを指定します。

```bash
export LM_STAGING_VERIFY_MODE=chat
export LM_ROUTE_MESSAGE_ID='(実chat readbackのroute message ID)'
export LM_TRAVEL_RECEIPT_MESSAGE_ID='(実chat readbackのconfirmed receipt message ID)'
./staging-seed-and-cleanup.sh seed
```

failure receiptだけをreadbackするときは、`LM_STAGING_VERIFY_MODE=failure` と `LM_TRAVEL_FAILURE_MESSAGE_ID`（`semanticKey=chat.travel_block_not_added` の実ID）を指定します。

cleanupは共有pre-authorized Composioアカウントをdisconnect/revoke/disableせず、confirmed receiptに記録されたprovider event IDだけを削除します。GET 404の狭いreadbackが取れなければ、DB行を削除せずfail closedします。mobile `/account`は呼ばず、production host/ref、別provider event ID、未指定の認証値を厳密に拒否します。

```bash
export LM_STAGING_CLEANUP_CONFIRM=DELETE_STAGING_ONLY
export LM_STAGING_API_BASE_URL='https://life-call-staging-staging.up.railway.app/api/mobile/v1'
export LM_STAGING_SUPABASE_REF='ulhsqqkyejzvqgoyjwte'
export LM_STAGING_BEARER_TOKEN='(temporary staging bearer; process environment only)'
export LM_STAGING_SUPABASE_URL='https://ulhsqqkyejzvqgoyjwte.supabase.co'
export LM_STAGING_DB_SERVICE_ROLE_KEY='(staging service-role key; process environment only)'
export LM_STAGING_UID='(exact isolated staging uid)'
export LM_TRAVEL_RECEIPT_MESSAGE_ID='(exact confirmed receipt message ID)'
export LM_TRAVEL_PROVIDER_EVENT_ID='(exact providerEventId from that receipt args)'
export LM_STAGING_COMPOSIO_API_KEY='(staging Composio key; process environment only)'
export LM_STAGING_CONNECTED_ACCOUNT_ID='(exact connected account ID; process environment only)'
./staging-seed-and-cleanup.sh cleanup
```

token、service-role key、Composio key、connected account IDは標準出力・YAML・commitに出しません。provider DELETEが失敗またはGET 404でない場合、DB cleanupは実行されません。

## Maestro flows

```bash
maestro test \
  -e STAGING_SESSION_ID='(opaque staging session id)' \
  -e ROUTE_MESSAGE_ID='(real route message id)' \
  -e TRAVEL_RECEIPT_MESSAGE_ID='(exact provider-confirmed chat message id)' \
  apps/life-manager-ios/maestro/preauthorized-bootstrap-chat.yaml

maestro test \
  -e STAGING_SESSION_ID='(opaque staging session id)' \
  -e TRAVEL_FAILURE_MESSAGE_ID='(exact real not-added chat message id)' \
  apps/life-manager-ios/maestro/preauthorized-travel-failure.yaml

maestro test \
  -e STAGING_SESSION_ID='(opaque staging session id)' \
  -e ROUTE_MESSAGE_ID='(real route message id)' \
  apps/life-manager-ios/maestro/english-onboarding-route.yaml

maestro test \
  -e STAGING_SESSION_ID='(opaque staging session id)' \
  -e ROUTE_MESSAGE_ID='(real route message id)' \
  apps/life-manager-ios/maestro/japanese-onboarding-route.yaml
```

`preauthorized-bootstrap-chat`はbootstrap復元、chat、route card、refresh、provider read-back後の `calendar.travelBlock.confirmed.<message-id>` receiptを確認します。`preauthorized-travel-failure`は、実readbackで取得したfailure message IDに対して `calendar.travelBlock.notAdded.<message-id>` が見えることを確認します。locale flowはphone skip → 実next-event analysis → route card → 詳細sheet → soft paywallのfree path → settingsまでを1シナリオとして確認します。英語flowでは日本語のgenerated chrome、日語flowでは英語のgenerated chromeを明示的に否定します。

## Push deep-linkの境界

APNs payloadの生成・送信はMaestroが代行しません。stagingの実outbox message ID、実device token、staging APNs environmentが揃った後、管理された外部手順で一度だけpayloadをdeliveryし、通知をtapしてからflowを起動します。flowはそのmessage IDがchatへ一度だけ現れ、refresh後も同じIDが残ることを確認します。payloadをYAMLへ埋めたり、client側へmessageをinsertしたりしません。

```bash
maestro test \
  -e STAGING_SESSION_ID='(opaque staging session id)' \
  -e PUSH_MESSAGE_ID='(real delivered message id)' \
  apps/life-manager-ios/maestro/push-deep-link.yaml
```

## 録画

real staging readbackが完了した後だけ、シミュレータ録画を生成します。出力はrepo外のprivate artifact directoryへ置き、実値を含む動画をcommitしません。

```bash
mkdir -p "$HOME/Library/Logs/life-manager-maestro"
maestro record --local \
  -e STAGING_SESSION_ID='(opaque staging session id)' \
  -e ROUTE_MESSAGE_ID='(real route message id)' \
  apps/life-manager-ios/maestro/english-onboarding-route.yaml \
  "$HOME/Library/Logs/life-manager-maestro/life-manager-english-route.mp4"

maestro record --local \
  -e STAGING_SESSION_ID='(opaque staging session id)' \
  -e ROUTE_MESSAGE_ID='(real route message id)' \
  -e TRAVEL_RECEIPT_MESSAGE_ID='(exact provider-confirmed chat message id)' \
  apps/life-manager-ios/maestro/preauthorized-bootstrap-chat.yaml \
  "$HOME/Library/Logs/life-manager-maestro/life-manager-travel-receipt.mp4"
```

録画の後続TestFlight gateでは、同じシナリオを実Google OAuth、実Calendar event、実Transit/Google route、production APNs、必要時の確認済みcallで実機再実行します。Maestro staging動画やコンパイル成功だけをTestFlight/App Storeの証跡に置き換えてはいけません。

## 受け入れ条件の境界

Googleのpasskey/consent/account chooserはMaestroの外部認証境界です。Maestroはprovider接続を作らず、共有pre-authorizedアカウントに保存された実sessionを使います。receiptのPASS条件は、実provider read-backで得たmessage IDを環境変数から受け取り、Swiftがbackendの `semanticKey` だけから成功/失敗の安定IDを表示することです。route cardやmessage本文だけからCalendar追加成功を推測してはいけません。
