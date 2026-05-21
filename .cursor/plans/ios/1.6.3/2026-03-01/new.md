 ### パッチ1: ralph.sh.template のデフォルトを 20→10                                                              
                                                                                                                  
 ファイル: .claude/skills/mobileapp-builder/ralph.sh.template                                                     
 行10                                                                                                             
                                                                                                                  
 ```                                                                                                              
   旧: MAX_ITERATIONS="${1:-20}"                                                                                  
   新: MAX_ITERATIONS="${1:-10}"                                                                                  
 ```                                                                                                              
                                                                                                                  
 なぜ直る: テンプレートから新しい ralph.sh がコピーされる時、デフォルトが10になる。                               
                                                                                                                  
 ────────────────────────────────────────────────────────────────────────────────                                 
                                                                                                                  
 ### パッチ2: mobileapp-factory/SKILL.md で引数を渡さない                                                         
                                                                                                                  
 ファイル: ~/.openclaw/skills/mobileapp-factory/SKILL.md                                                          
 行78                                                                                                             
                                                                                                                  
 ```                                                                                                              
   旧: './ralph.sh 20'                                                                                            
   新: './ralph.sh'                                                                                               
 ```                                                                                                              
                                                                                                                  
 なぜ直る: ralph.sh のデフォルト（パッチ1で10に修正）に任せる。変更したい時は ralph.sh.template                   
 の1箇所だけ変えればいい。                                                                                        
                                                                                                                  
 ────────────────────────────────────────────────────────────────────────────────                                 
                                                                                                                  
 ### パッチ3: CLAUDE.md.template 133-163行を全削除→ポインタに                                                     
                                                                                                                  
 ファイル: .claude/skills/mobileapp-builder/CLAUDE.md.template                                                    
 行133-163（31行を削除して以下に置換）                                                                            
                                                                                                                  
 ```                                                                                                              
   ## 環境変数（必須）                                                                                            
   全ての `asc` コマンド実行前に `export ASC_BYPASS_KEYCHAIN=true` を設定すること。                               
   未設定だと asc CLI が macOS Keychain にアクセスしてハングする。                                                
                                                                                                                  
   ## US別詳細手順（SSOT = references/us-XXX.md）                                                                 
   各USの実行時は必ず対応する `references/us-XXX.md` を読むこと。                                                 
   この CLAUDE.md には概要を書かない。詳細は全て references が正本。                                              
   CLAUDE.md と references が矛盾する場合、references が常に優先。                                                
                                                                                                                  
   ## WAITING_FOR_HUMAN                                                                                           
   progress.txt に書いて passes: false にする。ralph.sh が検知して Slack に通知する。                             
   WAITING_FOR_HUMAN が発生する場面:                                                                              
   1. `asc apps create` の 2FA コード（Apple ID 認証に毎回必要）                                                  
   2. RevenueCat SK key（手動でプロジェクト作成後に返してもらう）                                                 
   詳細は `references/us-005-infra.md` に書いてある。                                                             
                                                                                                                  
   ## 禁止事項                                                                                                    
   - Dais に APP_ID 作成を頼むことは禁止。`asc apps create` を自分で実行すること。                                
   - `revenuecat MCP` は使わない。RC API v2（curl）を使うこと。手順は `references/us-005-infra.md` Step 7。       
   - `asc web auth login` は US-005 では使わない。US-009（App Privacy apply）でのみ使う。                         
 ```                                                                                                              
                                                                                                                  
 なぜ直る:                                                                                                        
 - RC MCP の古い指示が消える                                                                                      
 - ASC 2FA不要の嘘が消える                                                                                        
 - ASC_BYPASS_KEYCHAIN が明記される                                                                               
 - 全詳細は references にポインタ                                                                                 
 - Dais に APP_ID を頼むな、が明記される                                                                          
                                                                                                                  
 ────────────────────────────────────────────────────────────────────────────────                                 
                                                                                                                  
 ### パッチ4: SKILL.md 40-55行（RC 手動作業セクション）                                                           
                                                                                                                  
 ファイル: .claude/skills/mobileapp-builder/SKILL.md                                                              
 行40-55を以下に置換                                                                                              
                                                                                                                  
 旧（Daisに3つのキーを頼む長いセクション）→ 新:                                                                   
                                                                                                                  
 ```                                                                                                              
   ## Slack Interaction (US-005, 1回のみ)                                                                         
                                                                                                                  
   WAITING_FOR_HUMAN は2箇所:                                                                                     
   1. **2FA コード** — `asc apps create` に毎回必要。Dais が iPhone の 6桁コードを Slack で返信。                 
   2. **RC SK key** — Dais が RC でプロジェクト作成 → SK key を Slack で返信。                                    
                                                                                                                  
   詳細手順: `references/us-005-infra.md` Step 5（ASC）と Step 7（RC）を参照。                                    
 ```                                                                                                              
                                                                                                                  
 なぜ直る: 古い3つのキー手順が消える。正本は us-005-infra.md のみ。                                               
                                                                                                                  
 ────────────────────────────────────────────────────────────────────────────────                                 
                                                                                                                  
 ### パッチ5: us-005-infra.md Step 5（ASC アプリ作成）書き直し                                                    
                                                                                                                  
 ファイル: .claude/skills/mobileapp-builder/references/us-005-infra.md                                            
 行74-106を以下に置換                                                                                             
                                                                                                                  
 ```                                                                                                              
   ## Step 5: ASC App Creation（Apple ID 認証 — 2FA 毎回必要）                                                    
                                                                                                                  
   **重要:**                                                                                                      
   - `export ASC_BYPASS_KEYCHAIN=true` 必須（ないとハング）                                                       
   - `asc apps create` は API Key では動かない。Apple ID + パスワード + 2FA が必要。                              
   - パスワードと Apple ID は `.env` から読む。2FA コードは Dais に Slack で聞く。                                
                                                                                                                  
   ### 5.1: アプリ作成                                                                                            
   \```bash                                                                                                       
   export ASC_BYPASS_KEYCHAIN=true                                                                                
   source .env                                                                                                    
                                                                                                                  
   # 2FA コードが .env にあるか確認                                                                               
   if [ -z "$TWO_FACTOR_CODE" ]; then                                                                             
     cat >> progress.txt << 'MSG'                                                                                 
   WAITING_FOR_HUMAN: 2FA code needed                                                                             
   📱 iPhone に届く 6桁の Apple 2FA コードを Slack で返信してください。                                           
   ⚠️ コードの有効期限は数分です。受信後すぐに返信してください。                                                  
   MSG                                                                                                            
     exit 0                                                                                                       
   fi                                                                                                             
                                                                                                                  
   APP_RESULT=$(asc apps create \                                                                                 
     --name "<app_name>" \                                                                                        
     --bundle-id "<bundle_id>" \                                                                                  
     --sku "<slug>" \                                                                                             
     --platform IOS \                                                                                             
     --apple-id "$APPLE_ID" \                                                                                     
     --password "$APPLE_PASSWORD" \                                                                               
     --two-factor-code "$TWO_FACTOR_CODE" \                                                                       
     --output json 2>&1)                                                                                          
                                                                                                                  
   APP_ID=$(echo "$APP_RESULT" | jq -r '.data.id')                                                                
   if [ "$APP_ID" != "null" ] && [ -n "$APP_ID" ]; then                                                           
     echo "APP_ID=$APP_ID" >> .env                                                                                
     # 使い捨て 2FA コードを .env から削除                                                                        
     sed -i '' '/TWO_FACTOR_CODE/d' .env                                                                          
     echo "✅ ASC App created: $APP_ID"                                                                           
   else                                                                                                           
     echo "❌ ASC App creation failed: $APP_RESULT"                                                               
     # 2FA コードが期限切れの可能性 → 再度要求                                                                    
     sed -i '' '/TWO_FACTOR_CODE/d' .env                                                                          
     cat >> progress.txt << 'MSG'                                                                                 
   WAITING_FOR_HUMAN: 2FA code expired or invalid. 新しい 6桁コードを Slack で送ってください。                    
   MSG                                                                                                            
     exit 0                                                                                                       
   fi                                                                                                             
   \```                                                                                                           
                                                                                                                  
   ### 注意                                                                                                       
   - iris セッション / `asc web auth login` はここでは使わない（US-009 でのみ使う）                               
   - Dais に APP_ID 作成を頼むことは**禁止**。自分で `asc apps create` を実行すること。                           
   - `APPLE_ID` と `APPLE_PASSWORD` は `.env` テンプレートに含める（Step 3 参照）                                 
 ```                                                                                                              
                                                                                                                  
 なぜ直る:                                                                                                        
 - 「iris セッション」の嘘が消える                                                                                
 - 2FA が毎回必要であることが明記                                                                                 
 - ASC_BYPASS_KEYCHAIN が明記                                                                                     
 - コード受け渡しの具体的手順がある                                                                               
 - 期限切れ時のリトライ手順もある                                                                                 
                                                                                                                  
 ────────────────────────────────────────────────────────────────────────────────                                 
                                                                                                                  
 ### パッチ6: us-005-infra.md の .env テンプレート（Step 3）に APPLE_ID/APPLE_PASSWORD 追加                       
                                                                                                                  
 ファイル: .claude/skills/mobileapp-builder/references/us-005-infra.md                                            
 Step 3 の .env テンプレートに追加                                                                                
                                                                                                                  
 ```                                                                                                              
   APPLE_ID=keiodaisuke@gmail.com                                                                                 
   APPLE_PASSWORD=Chatgpt12345                                                                                    
   TWO_FACTOR_CODE=                                                                                               
 ```                                                                                                              
                                                                                                                  
 なぜ直る: CC が Apple ID 認証情報をどこから取るか明確になる。                                                    
                                                                                                                  
 ────────────────────────────────────────────────────────────────────────────────                                 
                                                                                                                  
 ### パッチ7: SETUP.md の PRIVACY_POLICY_DOMAIN                                                                   
                                                                                                                  
 ファイル: .claude/skills/mobileapp-builder/SETUP.md                                                              
 行82-83                                                                                                          
                                                                                                                  
 ```                                                                                                              
   旧: PRIVACY_POLICY_DOMAIN=yourdomain .com                                                                      
   新: PRIVACY_POLICY_DOMAIN=daisuke134.github.io/anicca-products                                                 
 ```                                                                                                              
                                                                                                                  
 ────────────────────────────────────────────────────────────────────────────────                                 
                                                                                                                  
 ### パッチ8: spec-template.md の privacy URL                                                                     
                                                                                                                  
 ファイル: .claude/skills/mobileapp-builder/references/spec-template.md                                           
 行41                                                                                                             
                                                                                                                  
 ```                                                                                                              
   旧: - privacy_policy_url: https://yourdomain.com/privacy                                                       
   新: - privacy_policy_url: https://$PRIVACY_POLICY_DOMAIN/<slug>/privacy                                        
 ```                                                                                                              
                                                                                                                  
 なぜ直る: ハードコードされたドメインが消える。環境変数を参照する。                                               
                                                                                                                  
 ────────────────────────────────────────────────────────────────────────────────                                 
                                                                                                                  
 ### パッチ9: mobileapp-factory/SKILL.md の橋渡しセクション書き直し                                               
                                                                                                                  
 ファイル: ~/.openclaw/skills/mobileapp-factory/SKILL.md                                                          
 行93-145を以下に置換                                                                                             
                                                                                                                  
 ```                                                                                                              
   ## STEP 7: 橋渡し（2箇所）                                                                                     
                                                                                                                  
   ### 7a. 2FA コード（ASC アプリ作成時 — US-005）                                                                
                                                                                                                  
   Slack に来る: `WAITING_FOR_HUMAN: 2FA code needed`                                                             
                                                                                                                  
   Dais が 6桁コードを Slack で返信 → Anicca が即座に:                                                            
   1. `echo "TWO_FACTOR_CODE=XXXXXX" >> $APP_DIR/.env`                                                            
   2. progress.txt から WAITING_FOR_HUMAN 行を削除: `sed -i '' '/WAITING_FOR_HUMAN/d' $APP_DIR/progress.txt`      
   3. ralph.sh の次のイテレーションで CC が .env を読んで自動再開                                                 
                                                                                                                  
   ⚠️ 2FA コードの有効期限は数分。Slack 受信後すぐに書き込むこと。                                                
                                                                                                                  
   ### 7b. RC SK key（RevenueCat プロジェクト作成後 — US-005）                                                    
                                                                                                                  
   Slack に来る: `WAITING_FOR_HUMAN: RC Setup`                                                                    
                                                                                                                  
   Dais が RC でプロジェクト作成 → SK key を Slack で返信 → Anicca が:                                            
   1. `echo "RC_SECRET_KEY=sk_xxxxx" >> $APP_DIR/.env`                                                            
   2. progress.txt から WAITING_FOR_HUMAN 行を削除                                                                
   3. CC が次のイテレーションで RC API v2 を使って自動セットアップ                                                
                                                                                                                  
   ### 7c. 2FA コード（App Privacy apply — US-009）                                                               
                                                                                                                  
   Slack に来る: `WAITING_FOR_HUMAN: iris session expired`                                                        
                                                                                                                  
   Dais が 6桁コードを返信 → Anicca が:                                                                           
   1. `ASC_BYPASS_KEYCHAIN=true asc web auth login --apple-id keiodaisuke@gmail.com --two-factor-code XXXXXX`     
   2. progress.txt から WAITING_FOR_HUMAN 行を削除                                                                
                                                                                                                  
   ## 情報フロー                                                                                                  
                                                                                                                  
   CC → progress.txt に WAITING_FOR_HUMAN → 終了                                                                  
   ralph.sh → progress.txt 読む → WAITING_FOR_HUMAN 検出 → Slack 通知                                             
   Dais → Slack で返信                                                                                            
   Anicca → .env に書き込み + progress.txt クリア                                                                 
   ralph.sh → 次のイテレーション → CC が .env 読んで再開                                                          
 ```                                                                                                              
                                                                                                                  
 なぜ直る:                                                                                                        
 - 「RCプロジェクトURLのみ」の嘘が消える                                                                          
 - 2FA コード、RC SK key、App Privacy の3パターン全部書いてある                                                   
 - Anicca が Slack で受け取ったら何をするかが具体的に書いてある                                                   
 - 「MCPで〜」の古い手順が消える                                                                                  
                                                                                                                  
 ────────────────────────────────────────────────────────────────────────────────                                 
                                                                                                                  
 ### パッチ10: us-009-submit.md の asc web auth チェック修正                                                      
                                                                                                                  
 ファイル: .claude/skills/mobileapp-builder/references/us-009-submit.md                                           
 行61-67を以下に置換                                                                                              
                                                                                                                  
 ```bash                                                                                                          
   # asc web コマンドは iris セッションが必要（App Privacy apply に使う）                                         
   export ASC_BYPASS_KEYCHAIN=true                                                                                
   if ! asc web auth status 2>&1 | grep -q "authenticated"; then                                                  
     cat >> progress.txt << 'MSG'                                                                                 
   WAITING_FOR_HUMAN: iris session expired (App Privacy apply に必要)                                             
   📱 iPhone に届く 6桁コードを Slack で返信してください。                                                        
   MSG                                                                                                            
     exit 0                                                                                                       
   fi                                                                                                             
 ```                                                                                                              
                                                                                                                  
 なぜ直る: US-009 でのみ iris セッションが必要であることが明確。ASC_BYPASS_KEYC HAIN も明記。                     
                                                                                                                  
 ────────────────────────────────────────────────────────────────────────────────                                 
                                                                                                                  
 ### パッチ11: CLAUDE.md.template にルール追加                                                                    
                                                                                                                  
 ファイル: .claude/skills/mobileapp-builder/CLAUDE.md.template                                                    
 ルールテーブル（行36付近）に追加                                                                                 
                                                                                                                  
 ```                                                                                                              
   | XX | **全ての `asc` コマンドに `export ASC_BYPASS_KEYCHAIN=true` を設定すること** |                          
   | XX | **`asc apps create` は Apple ID + 2FA 認証が毎回必要。API Key では動かない** |                          
 ```                                                                                                              
                                                                                                                  
 ────────────────────────────────────────────────────────────────────────────────                                 
                                                                                                                  
 ### パッチ12: SETUP.md の .env テンプレートに APPLE_ID/APPLE_PASSWORD 追加                                       
                                                                                                                  
 ファイル: .claude/skills/mobileapp-builder/SETUP.md                                                              
 行44付近（Apple / ASC セクション）に追加                                                                         
                                                                                                                  
 ```bash                                                                                                          
   # ── Apple ID (for asc apps create — 2FA required every time) ─────────                                        
   APPLE_ID=keiodaisuke@gmail.com                                                                                 
   APPLE_PASSWORD=<your Apple ID password>                                                                     