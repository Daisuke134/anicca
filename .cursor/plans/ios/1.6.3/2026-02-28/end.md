  ---                                                                                                                                     
  全回答
                                                                                                                                          
  Q1: RC Offering 作成に必要な情報                                                                                                      

  Dais が手動でやること = RC ダッシュボードで新プロジェクト作成のみ。 それ以降は全自動。

  ┌────────────────────────────┬──────────────┬─────────────────────────────────────────────────────────────────────┐
  │          ステップ          │     誰が     │                              やること                               │
  ├────────────────────────────┼──────────────┼─────────────────────────────────────────────────────────────────────┤
  │ ① RC プロジェクト作成      │ Dais（手動） │ RC ダッシュボードで新プロジェクト作成                               │
  ├────────────────────────────┼──────────────┼─────────────────────────────────────────────────────────────────────┤
  │ ② URL をエージェントに渡す │ Dais         │ https://app.revenuecat.com/projects/XXXXXX/overview を貼る          │
  ├────────────────────────────┼──────────────┼─────────────────────────────────────────────────────────────────────┤
  │ ③ 以降全自動               │ エージェント │ URL から project_id 抽出 → Offering 作成 → Package → Product 紐付け │
  └────────────────────────────┴──────────────┴─────────────────────────────────────────────────────────────────────┘

  エージェントが URL から project_id を抽出する方法:

  入力: https://app.revenuecat.com/projects/976e8639/overview
  抽出: 976e8639
  変換: proj976e8639
  → これが MCP の project_id

  ---
  Q2: エージェント用コピペコマンド集（思考不要）

  エージェントはこれをそのまま叩くだけ。変数を埋めるだけ。

  A. RevenueCat Offering 作成（MCP 4コマンド）

  # 変数（Dais が渡す URL から抽出）
  RC_PROJECT_ID=proj976e8639
  APP_NAME=SleepRitual
  MONTHLY_PRODUCT_ID=com.anicca.sleepritual.monthly
  ANNUAL_PRODUCT_ID=com.anicca.sleepritual.annual

  # STEP 1: 既存確認
  RC_list_offerings: { "project_id": "${RC_PROJECT_ID}" }

  # STEP 2: Offering 作成
  RC_create_offering: {
    "project_id": "${RC_PROJECT_ID}",
    "lookup_key": "${APP_NAME}_default",
    "display_name": "${APP_NAME} Default"
  }
  → 返却値から offering_id を取得

  # STEP 3: Package 作成（月額 + 年額）
  RC_create_package: {
    "project_id": "${RC_PROJECT_ID}",
    "offering_id": "${OFFERING_ID}",
    "lookup_key": "$rc_monthly",
    "display_name": "Monthly"
  }
  → 返却値から package_id を取得

  RC_create_package: {
    "project_id": "${RC_PROJECT_ID}",
    "offering_id": "${OFFERING_ID}",
    "lookup_key": "$rc_annual",
    "display_name": "Annual"
  }
  → 返却値から package_id を取得

  # STEP 4: Product 紐付け
  RC_attach_products_to_package: {
    "project_id": "${RC_PROJECT_ID}",
    "package_id": "${MONTHLY_PKG_ID}",
    "products": [{"product_id": "${MONTHLY_PRODUCT_ID}", "eligibility_criteria": "all"}]
  }

  RC_attach_products_to_package: {
    "project_id": "${RC_PROJECT_ID}",
    "package_id": "${ANNUAL_PKG_ID}",
    "products": [{"product_id": "${ANNUAL_PRODUCT_ID}", "eligibility_criteria": "all"}]
  }

  B. サブスク価格一括設定（CLI 1コマンド）

  # 変数
  SUB_ID=6759916378  # monthly
  APP_PRICE=999      # $9.99

  # 基準価格ポイント取得 → 等価価格 → 全テリトリー設定
  BASE_PP=$(asc subscriptions price-points list --id $SUB_ID --territory USA 2>&1 | python3 -c "
  import json,sys
  for p in json.load(sys.stdin)['data']:
    if str($APP_PRICE) in str(p): print(p['id']); break
  ")
  asc subscriptions prices add --id $SUB_ID --price-point $BASE_PP --territory USA

  C. サブスクローカライズ一括（CLI 1ループ）

  SUB_ID=6759916378
  NAME="Monthly Premium"

  for locale in ar-SA ca cs da de-DE el en-AU en-CA en-GB en-US es-ES es-MX fi fr-CA fr-FR he hi hr hu id it ja ko ms nl-NL no pl pt-BR
  pt-PT ro ru sk sv th tr uk vi zh-Hans zh-Hant; do
    asc subscriptions localizations create --subscription-id $SUB_ID --locale "$locale" --name "$NAME"
  done

  D. サブスクグループ用スクショ（CLI 1コマンド）

  asc subscriptions images create --subscription-id $SUB_ID --file "./paywall-screenshot.png"

  E. App Privacy 宣言（CLI 5ステップ）

  APP_ID=6759916261

  # ① Web セッションログイン（初回のみ）
  asc web auth login --apple-id "your@email.com"

  # ② 現在の宣言を取得
  asc web privacy pull --app $APP_ID --file privacy-current.json

  # ③ privacy.json を編集（収集データを宣言）

  # ④ 差分確認
  asc web privacy plan --app $APP_ID --file privacy.json

  # ⑤ 適用 + 公開
  asc web privacy apply --app $APP_ID --file privacy.json
  asc web privacy publish --app $APP_ID

  ---
  最終テーブル（更新版）

  ┌─────┬────────────────────────────┬──────────────────────────────────────────────────────┬────────────────────────┐
  │  #  │           タスク           │                       コマンド                       │         自動化         │
  ├─────┼────────────────────────────┼──────────────────────────────────────────────────────┼────────────────────────┤
  │ 1   │ App Privacy 宣言           │ asc web privacy apply + publish                      │ ✅ 可能（web session） │
  ├─────┼────────────────────────────┼──────────────────────────────────────────────────────┼────────────────────────┤
  │ 2   │ サブスク月額/年額価格      │ asc subscriptions prices add ループ                  │ ✅ 可能                │
  ├─────┼────────────────────────────┼──────────────────────────────────────────────────────┼────────────────────────┤
  │ 3   │ サブスクローカライズ       │ asc subscriptions localizations create ループ        │ ✅ 可能                │
  ├─────┼────────────────────────────┼──────────────────────────────────────────────────────┼────────────────────────┤
  │ 4   │ グループローカライズ       │ asc subscriptions groups localizations create ループ │ ✅ 可能                │
  ├─────┼────────────────────────────┼──────────────────────────────────────────────────────┼────────────────────────┤
  │ 5   │ App Store スクショ         │ asc screenshots upload                               │ ✅ 可能                │
  ├─────┼────────────────────────────┼──────────────────────────────────────────────────────┼────────────────────────┤
  │ 6   │ サブスクグループ用スクショ │ asc subscriptions images create --file               │ ✅ 可能                │
  ├─────┼────────────────────────────┼──────────────────────────────────────────────────────┼────────────────────────┤
  │ 7   │ RC Offering 作成           │ MCP 4ステップ（上記）                                │ ✅ 可能                │
  ├─────┼────────────────────────────┼──────────────────────────────────────────────────────┼────────────────────────┤
  │ 8   │ RC プロジェクト作成        │ RC ダッシュボード                                    │ ❌ Dais 手動のみ       │
  └─────┴────────────────────────────┴──────────────────────────────────────────────────────┴────────────────────────┘

  Dais が手動でやること = RC プロジェクト作成 + URL をエージェントに渡すだけ。あとは全部 CLI/MCP で自動。