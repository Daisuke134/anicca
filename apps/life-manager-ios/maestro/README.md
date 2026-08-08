# Life Manager real-provider Maestro harness

このディレクトリは、モックCalendar・fixture outbox・固定route payloadを使わないstaging E2E用です。Googleの同意/アカウント選択は外部ブラウザ面なのでMaestroの実行範囲に含めません。先に一度だけ実Google OAuthを完了し、同じiOS Keychainに保存されたセッションで以下のフローを実行します。

## 実行前の必須条件

1. Railwayの隔離staging APIへ向けてビルドされたLife ManagerをSimulatorまたはTestFlight相当の実機へインストールする。現在の隔離先は `life-call-staging-staging.up.railway.app`、Supabase refは `ulhsqqkyejzvqgoyjwte` です。
2. 外部ブラウザで実Google consent/account chooserを完了し、Calendar接続を保存する。MaestroのYAMLにはcallback URL、code、session tokenを入れません。
3. 実Calendarに、現在の時刻から18時間以内の移動先付き予定を1件だけ用意する。タイトル・場所・時刻・routeの各値はprovider readbackから取得し、YAMLへコピーしません。
4. profileにname、home、product localeを保存する。`phone`はnull、callsはdisabled、analysisはidleにする。`staging-seed-and-cleanup.sh seed`がこの状態をHTTP readbackで確認します。
5. `ROUTE_MESSAGE_ID`は、実analysis後に `/api/mobile/v1/chat` から読み取ったroute messageのopaque IDだけを指定する。推測したIDやfixture IDは使用しません。

アプリのKeychainを消去する `clearState` / `clearKeychain` は、pre-authorizedフローの実行コマンドにはありません。旧Swift静的テストとの互換用コメントは実行命令ではありません。

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
./staging-seed-and-cleanup.sh seed
```

cleanupはstagingの使い捨てアカウントだけを対象にし、production host/refを厳密に拒否します。外部削除を行うため、実行時に明示的な確認値が必要です。

```bash
export LM_STAGING_CLEANUP_CONFIRM=DELETE_STAGING_ONLY
./staging-seed-and-cleanup.sh cleanup
```

tokenは標準出力・YAML・commitに出しません。productionのhost/ref、未指定のhost/ref、誤ったproject refはいずれもfail closedです。

## Maestro flows

```bash
maestro test \
  -e STAGING_SESSION_ID='(opaque staging session id)' \
  -e ROUTE_MESSAGE_ID='(real route message id)' \
  apps/life-manager-ios/maestro/preauthorized-bootstrap-chat.yaml

maestro test \
  -e STAGING_SESSION_ID='(opaque staging session id)' \
  -e ROUTE_MESSAGE_ID='(real route message id)' \
  apps/life-manager-ios/maestro/english-onboarding-route.yaml

maestro test \
  -e STAGING_SESSION_ID='(opaque staging session id)' \
  -e ROUTE_MESSAGE_ID='(real route message id)' \
  apps/life-manager-ios/maestro/japanese-onboarding-route.yaml
```

`preauthorized-bootstrap-chat`はbootstrap復元、chat、route card、refreshを確認します。locale flowはphone skip → 実next-event analysis → route card → 詳細sheet → soft paywallのfree path → settingsまでを1シナリオとして確認します。英語flowでは日本語のgenerated chrome、日語flowでは英語のgenerated chromeを明示的に否定します。

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
```

録画の後続TestFlight gateでは、同じシナリオを実Google OAuth、実Calendar event、実Transit/Google route、production APNs、必要時の確認済みcallで実機再実行します。Maestro staging動画やコンパイル成功だけをTestFlight/App Storeの証跡に置き換えてはいけません。

## 受け入れ条件の限界（未実装面を隠さない）

現在のnative mobile contractには、webのdaily loopが作る `[Travel]` Calendar blockを表示する専用chat messageまたは専用accessibility IDがありません。したがって、このMaestro sliceはroute card/detailをtravel routeの証跡として確認しますが、「auto-added travel block confirmation」をPASSとは主張しません。そこを実E2Eで完了するには、backendが実Calendarのinsert/readback結果をmobile outboxへ意味付きmessageとして返し、Swiftに専用の安定IDを追加した後、別flowを追加する必要があります。推測したroute cardやfixtureでこの穴を埋めることは禁止です。
