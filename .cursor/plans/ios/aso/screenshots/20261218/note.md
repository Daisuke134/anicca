⏺ まず、既存キーワードの扱いについて回答して、その後スクリーンショットに移る。                                                      
                                                                                                                                    
  ---                                                                                                                               
  既存キーワードの扱い                                                                                                              
                                                                                                                                    
  方法1: 既存キーワードをすべてPAUSE → 新キーワードをCREATE（推奨）                                                                 
                                                                                                                                    
  同じAd Group内で:                                                                                                                 
  1. 既存142キーワードをすべてPAUSE（またはDELETE）                                                                                 
  2. 新44キーワードをCREATE                                                                                                         
                                                                                                                                    
  方法2: 新しいAd Groupを作成                                                                                                       
                                                                                                                                    
  Campaign: Anicca Discovery                                                                                                        
  ├── Ad Group: Discovery (古い、PAUSE)                                                                                             
  └── Ad Group: Discovery v2 (新規作成、新キーワード)                                                                               
                                                                                                                                    
  俺の推奨: 方法1                                                                                                                   
                                                                                                                                    
  理由：                                                                                                                            
  - Ad Groupを分けると管理が複雑になる                                                                                              
  - 同じAd Group内でキーワード入れ替えの方がシンプル                                                                                
  - 既存キーワードのデータは残る（PAUSEなら後で比較可能）                                                                           
                                                                                                                                    
  やり方：                                                                                                                          
  1. Apple Search Ads Console → Campaign → Ad Group → Keywords                                                                      
  2. 全キーワードを選択 → Pause All                                                                                                 
  3. 新しいCSV（44キーワード）をアップロード                                                                                        
                                                                                                                                    
  ---                                                                                                                               
  では、スクリーンショットに移る。まずNano Bananaのベストプラクティスを確認。                                                       
                                                                                                                                    
⏺ Search(pattern: "**/*nano*banana*.md")                                                                                            
  ⎿  Found 1 file (ctrl+o to expand)                                                                                                
                                                                                                                                    
⏺ Search(pattern: "**/*screenshot*.md")                                                                                             
  ⎿  Found 1 file (ctrl+o to expand)                                                                                                
                                                                                                                                    
⏺ Read(docs/12/dec12/nano-banana-prompts.md)                                                                                        
  ⎿  Read 420 lines                                                                                                                 
                                                                                                                                    
⏺ Read(.cursor/plans/screenshot-prompt.md)                                                                                          
  ⎿  Read 211 lines                                                                                                                 
                                                                                                                                    
⏺ 理解した。既存のテンプレートとベストプラクティスを確認した。                                                                      
                                                                                                                                    
  ---                                                                                                                               
  現行版：6枚のスクリーンショットプロンプト                                                                                         
                                                                                                                                    
  カラーシステムと理由                                                                                                              
                                                                                                                                    
  現行アプリのカラーパレット（コードより）：                                                                                        
  - 背景: #F8F5ED（ウォームベージュ）                                                                                               
  - カード: #FDFCFC（オフホワイト）                                                                                                 
  - テキスト: #393634（ダークブラウン）                                                                                             
  - アクセント: #C9B382（ゴールド）                                                                                                 
  - Orb: ブルーグラデーション #e6f5ff → #4da6ff                                                                                     
                                                                                                                                    
  App Storeスクショの背景色選定理由：                                                                                               
  - ダークパープル系 (#1a1a2e) を使用                                                                                               
  - 理由: アプリ自体がライトモードなので、背景を暗くしてコントラストを出す                                                          
  - 競合（Calm, Headspace）との差別化：仏教的・スピリチュアルな雰囲気                                                               
                                                                                                                                    
  ---                                                                                                                               
  Screenshot 1: Hero/Hook（最重要）                                                                                                 
                                                                                                                                    
  構成                                                                                                                              
  ┌──────────────┬──────────────────────────────────────────────────────────────────────┐                                           
  │     要素     │                                 内容                                 │                                           
  ├──────────────┼──────────────────────────────────────────────────────────────────────┤                                           
  │ 使用画面     │ Talk Tab（4つの感情カード表示）                                      │                                           
  ├──────────────┼──────────────────────────────────────────────────────────────────────┤                                           
  │ ヘッドライン │ EN: "Talk to Your AI Coach Anytime" / JP: "いつでもAIコーチと話せる" │                                           
  ├──────────────┼──────────────────────────────────────────────────────────────────────┤                                           
  │ 背景         │ ダークパープルグラデーション                                         │                                           
  ├──────────────┼──────────────────────────────────────────────────────────────────────┤                                           
  │ 役割         │ アプリの核心機能を一目で伝える                                       │                                           
  └──────────────┴──────────────────────────────────────────────────────────────────────┘                                           
  理由                                                                                                                              
                                                                                                                                    
  - 1枚目は「何ができるアプリか」を3秒で伝える必要がある                                                                            
  - Talk Tabは4つの感情カードが並び、視覚的にリッチ                                                                                 
  - 「AI Coach」というワードでボイスコーチング訴求                                                                                  
                                                                                                                                    
  英語プロンプト                                                                                                                    
                                                                                                                                    
  Create an App Store screenshot for "Anicca" - an AI habit coaching app.                                                           
                                                                                                                                    
  SIZE: 1320 × 2868 pixels (iPhone 6.9" portrait)                                                                                   
                                                                                                                                    
  BACKGROUND:                                                                                                                       
  - Dark purple gradient (#1a1a2e at top to #16213e at bottom)                                                                      
  - Subtle lotus flower pattern at 5% opacity, centered                                                                             
  - Very faint golden glow in the center                                                                                            
                                                                                                                                    
  HEADLINE (top center, about 15% from top):                                                                                        
  - Text: "Talk to Your AI Coach Anytime"                                                                                           
  - Font: Bold sans-serif (SF Pro Display Bold or similar)                                                                          
  - Color: White (#FFFFFF)                                                                                                          
  - Size: Large, prominent                                                                                                          
                                                                                                                                    
  SCREEN DISPLAY:                                                                                                                   
  - Use the attached screenshot of the Talk tab showing 4 emotion cards (Self-Loathing, Anxiety, Irritation, Something Else)        
  - Display as an iPhone 15 Pro frame with rounded corners                                                                          
  - Position: Center horizontally, lower 60% of canvas                                                                              
  - Add subtle drop shadow (10px blur, 20% opacity black)                                                                           
  - Screen should be slightly tilted (2-3 degrees) for dynamic feel                                                                 
                                                                                                                                    
  STYLE: Premium, calm, spiritual, inviting                                                                                         
                                                                                                                                    
  日本語プロンプト                                                                                                                  
                                                                                                                                    
  Create an App Store screenshot for "Anicca" - an AI habit coaching app.                                                           
                                                                                                                                    
  SIZE: 1320 × 2868 pixels (iPhone 6.9" portrait)                                                                                   
                                                                                                                                    
  BACKGROUND:                                                                                                                       
  - Dark purple gradient (#1a1a2e at top to #16213e at bottom)                                                                      
  - Subtle lotus flower pattern at 5% opacity, centered                                                                             
  - Very faint golden glow in the center                                                                                            
                                                                                                                                    
  HEADLINE (top center, about 15% from top):                                                                                        
  - Text: "いつでもAIコーチと話せる"                                                                                                
  - Font: Bold sans-serif (Hiragino Sans Bold or similar)                                                                           
  - Color: White (#FFFFFF)                                                                                                          
  - Size: Large, prominent                                                                                                          
                                                                                                                                    
  SCREEN DISPLAY:                                                                                                                   
  - Use the attached screenshot of the Talk tab showing 4 emotion cards                                                             
  - Display as an iPhone 15 Pro frame with rounded corners                                                                          
  - Position: Center horizontally, lower 60% of canvas                                                                              
  - Add subtle drop shadow (10px blur, 20% opacity black)                                                                           
  - Screen should be slightly tilted (2-3 degrees) for dynamic feel                                                                 
                                                                                                                                    
  STYLE: Premium, calm, spiritual, inviting                                                                                         
                                                                                                                                    
  ---                                                                                                                               
  Screenshot 2: AI Voice Session                                                                                                    
                                                                                                                                    
  構成                                                                                                                              
  ┌──────────────┬────────────────────────────────────────────────────────────┐                                                     
  │     要素     │                            内容                            │                                                     
  ├──────────────┼────────────────────────────────────────────────────────────┤                                                     
  │ 使用画面     │ Voice Session（青いOrb、「Anicca is speaking...」）        │                                                     
  ├──────────────┼────────────────────────────────────────────────────────────┤                                                     
  │ ヘッドライン │ EN: "24/7 AI Voice Coach" / JP: "24時間対応のAI音声コーチ" │                                                     
  ├──────────────┼────────────────────────────────────────────────────────────┤                                                     
  │ 背景         │ ディープブルーグラデーション                               │                                                     
  ├──────────────┼────────────────────────────────────────────────────────────┤                                                     
  │ 役割         │ 差別化要素（他アプリにない音声AI）を強調                   │                                                     
  └──────────────┴────────────────────────────────────────────────────────────┘                                                     
  理由                                                                                                                              
                                                                                                                                    
  - 青いOrbは視覚的にユニークで目を引く                                                                                             
  - 「24/7」で常時利用可能を訴求                                                                                                    
  - 他の習慣アプリとの最大の差別化ポイント                                                                                          
                                                                                                                                    
  英語プロンプト                                                                                                                    
                                                                                                                                    
  Create an App Store screenshot for "Anicca" - an AI voice coaching app.                                                           
                                                                                                                                    
  SIZE: 1320 × 2868 pixels (iPhone 6.9" portrait)                                                                                   
                                                                                                                                    
  BACKGROUND:                                                                                                                       
  - Deep blue gradient (#0a1628 at top to #1e3a5f at bottom)                                                                        
  - Subtle sound wave graphics emanating from center (very faint, 10% opacity)                                                      
  - Golden sparkle effects scattered (5-7 small dots)                                                                               
                                                                                                                                    
  HEADLINE (top center, about 15% from top):                                                                                        
  - Text: "24/7 AI Voice Coach"                                                                                                     
  - Font: Bold sans-serif                                                                                                           
  - Color: White (#FFFFFF)                                                                                                          
  - Size: Large, prominent                                                                                                          
                                                                                                                                    
  SCREEN DISPLAY:                                                                                                                   
  - Use the attached screenshot showing the blue animated orb with "Anicca is speaking..." status                                   
  - Display as an iPhone 15 Pro frame                                                                                               
  - Position: Center, lower 60% of canvas                                                                                           
  - Add a subtle blue glow around the phone frame (matching the orb color)                                                          
  - Drop shadow: 15px blur, 25% opacity                                                                                             
                                                                                                                                    
  STYLE: Premium, futuristic, calming, convey live voice interaction                                                                
                                                                                                                                    
  日本語プロンプト                                                                                                                  
                                                                                                                                    
  Create an App Store screenshot for "Anicca" - an AI voice coaching app.                                                           
                                                                                                                                    
  SIZE: 1320 × 2868 pixels (iPhone 6.9" portrait)                                                                                   
                                                                                                                                    
  BACKGROUND:                                                                                                                       
  - Deep blue gradient (#0a1628 at top to #1e3a5f at bottom)                                                                        
  - Subtle sound wave graphics emanating from center (very faint, 10% opacity)                                                      
  - Golden sparkle effects scattered (5-7 small dots)                                                                               
                                                                                                                                    
  HEADLINE (top center, about 15% from top):                                                                                        
  - Text: "24時間対応のAI音声コーチ"                                                                                                
  - Font: Bold sans-serif (Hiragino Sans Bold)                                                                                      
  - Color: White (#FFFFFF)                                                                                                          
  - Size: Large, prominent                                                                                                          
                                                                                                                                    
  SCREEN DISPLAY:                                                                                                                   
  - Use the attached screenshot showing the blue animated orb                                                                       
  - Display as an iPhone 15 Pro frame                                                                                               
  - Position: Center, lower 60% of canvas                                                                                           
  - Add a subtle blue glow around the phone frame                                                                                   
  - Drop shadow: 15px blur, 25% opacity                                                                                             
                                                                                                                                    
  STYLE: Premium, futuristic, calming                                                                                               
                                                                                                                                    
  ---                                                                                                                               
  Screenshot 3: Habit Setup                                                                                                         
                                                                                                                                    
  構成                                                                                                                              
  ┌──────────────┬──────────────────────────────────────────────────────────────────────────┐                                       
  │     要素     │                                   内容                                   │                                       
  ├──────────────┼──────────────────────────────────────────────────────────────────────────┤                                       
  │ 使用画面     │ Habits Section（Wake Up, Training, Sleep + カスタム習慣）                │                                       
  ├──────────────┼──────────────────────────────────────────────────────────────────────────┤                                       
  │ ヘッドライン │ EN: "Set Habits. We'll Remind You." / JP: "習慣を設定。あとはおまかせ。" │                                       
  ├──────────────┼──────────────────────────────────────────────────────────────────────────┤                                       
  │ 背景         │ ウォームダーク（#1c1917）                                                │                                       
  ├──────────────┼──────────────────────────────────────────────────────────────────────────┤                                       
  │ 役割         │ 習慣トラッカー機能を訴求                                                 │                                       
  └──────────────┴──────────────────────────────────────────────────────────────────────────┘                                       
  理由                                                                                                                              
                                                                                                                                    
  - 「habit tracker」キーワードで来る人に直接訴求                                                                                   
  - シンプルな機能説明で分かりやすさ重視                                                                                            
  - ウォームな背景でアプリのベージュ系カラーと調和                                                                                  
                                                                                                                                    
  英語プロンプト                                                                                                                    
                                                                                                                                    
  Create an App Store screenshot for "Anicca" - an AI habit coaching app.                                                           
                                                                                                                                    
  SIZE: 1320 × 2868 pixels (iPhone 6.9" portrait)                                                                                   
                                                                                                                                    
  BACKGROUND:                                                                                                                       
  - Warm dark tone (#1c1917)                                                                                                        
  - Subtle warm gradient toward center (slightly lighter)                                                                           
  - No patterns, clean                                                                                                              
                                                                                                                                    
  HEADLINE (top center, about 15% from top):                                                                                        
  - Text: "Set Habits. We'll Remind You."                                                                                           
  - Font: Bold sans-serif                                                                                                           
  - Color: Cream (#f5f3ed)                                                                                                          
  - Size: Large, prominent                                                                                                          
                                                                                                                                    
  SCREEN DISPLAY:                                                                                                                   
  - Use the attached screenshot of the Habits tab showing habit list (Wake Up 06:00, Training 18:00, Sleep 23:00, etc.)             
  - Display as an iPhone 15 Pro frame                                                                                               
  - Position: Center, lower 60% of canvas                                                                                           
  - Subtle warm shadow (brown tint)                                                                                                 
                                                                                                                                    
  STYLE: Clean, minimal, functional, warm                                                                                           
                                                                                                                                    
  日本語プロンプト                                                                                                                  
                                                                                                                                    
  Create an App Store screenshot for "Anicca" - an AI habit coaching app.                                                           
                                                                                                                                    
  SIZE: 1320 × 2868 pixels (iPhone 6.9" portrait)                                                                                   
                                                                                                                                    
  BACKGROUND:                                                                                                                       
  - Warm dark tone (#1c1917)                                                                                                        
  - Subtle warm gradient toward center                                                                                              
  - Clean, no patterns                                                                                                              
                                                                                                                                    
  HEADLINE (top center, about 15% from top):                                                                                        
  - Text: "習慣を設定。あとはおまかせ。"                                                                                            
  - Font: Bold sans-serif (Hiragino Sans Bold)                                                                                      
  - Color: Cream (#f5f3ed)                                                                                                          
  - Size: Large, prominent                                                                                                          
                                                                                                                                    
  SCREEN DISPLAY:                                                                                                                   
  - Use the attached screenshot of the Habits tab                                                                                   
  - Display as an iPhone 15 Pro frame                                                                                               
  - Position: Center, lower 60% of canvas                                                                                           
  - Subtle warm shadow                                                                                                              
                                                                                                                                    
  STYLE: Clean, minimal, functional, warm                                                                                           
                                                                                                                                    
  ---                                                                                                                               
  Screenshot 4: Emotional Support                                                                                                   
                                                                                                                                    
  構成                                                                                                                              
  ┌──────────────┬──────────────────────────────────────────────────────────────────────┐                                           
  │     要素     │                                 内容                                 │                                           
  ├──────────────┼──────────────────────────────────────────────────────────────────────┤                                           
  │ 使用画面     │ Talk Tabの感情選択（または Nudge Card）                              │                                           
  ├──────────────┼──────────────────────────────────────────────────────────────────────┤                                           
  │ ヘッドライン │ EN: "Struggling? Anicca Listens." / JP: "悩んでる？Aniccaが聞くよ。" │                                           
  ├──────────────┼──────────────────────────────────────────────────────────────────────┤                                           
  │ 背景         │ ウォームダークグラデーション                                         │                                           
  ├──────────────┼──────────────────────────────────────────────────────────────────────┤                                           
  │ 役割         │ メンタルヘルス系キーワード訴求                                       │                                           
  └──────────────┴──────────────────────────────────────────────────────────────────────┘                                           
  理由                                                                                                                              
                                                                                                                                    
  - 「anxiety」「self-loathing」等のキーワードで来る人に訴求                                                                        
  - 共感的なコピーで安心感を与える                                                                                                  
  - 感情カードの視覚的な見せ方                                                                                                      
                                                                                                                                    
  英語プロンプト                                                                                                                    
                                                                                                                                    
  Create an App Store screenshot for "Anicca" - an AI coaching app.                                                                 
                                                                                                                                    
  SIZE: 1320 × 2868 pixels (iPhone 6.9" portrait)                                                                                   
                                                                                                                                    
  BACKGROUND:                                                                                                                       
  - Warm dark gradient (#1c1917 to #2c2b2a)                                                                                         
  - Subtle radial glow in center (warm orange at 5% opacity)                                                                        
  - Calming, supportive feel                                                                                                        
                                                                                                                                    
  HEADLINE (top center, about 15% from top):                                                                                        
  - Text: "Struggling? Anicca Listens."                                                                                             
  - Font: Bold sans-serif                                                                                                           
  - Color: Warm white (#f5f3ed)                                                                                                     
  - Size: Large, prominent                                                                                                          
                                                                                                                                    
  SCREEN DISPLAY:                                                                                                                   
  - Use the attached screenshot showing the emotion selection screen with cards: Self-Loathing, Anxiety & Worry, Irritation,        
  Something else                                                                                                                    
  - Display as an iPhone 15 Pro frame                                                                                               
  - Position: Center, lower 60% of canvas                                                                                           
  - Warm shadow                                                                                                                     
                                                                                                                                    
  STYLE: Empathetic, warm, supportive, safe                                                                                         
                                                                                                                                    
  日本語プロンプト                                                                                                                  
                                                                                                                                    
  Create an App Store screenshot for "Anicca" - an AI coaching app.                                                                 
                                                                                                                                    
  SIZE: 1320 × 2868 pixels (iPhone 6.9" portrait)                                                                                   
                                                                                                                                    
  BACKGROUND:                                                                                                                       
  - Warm dark gradient (#1c1917 to #2c2b2a)                                                                                         
  - Subtle radial glow in center (warm orange at 5% opacity)                                                                        
                                                                                                                                    
  HEADLINE (top center, about 15% from top):                                                                                        
  - Text: "悩んでる？Aniccaが聞くよ。"                                                                                              
  - Font: Bold sans-serif (Hiragino Sans Bold)                                                                                      
  - Color: Warm white (#f5f3ed)                                                                                                     
  - Size: Large, prominent                                                                                                          
                                                                                                                                    
  SCREEN DISPLAY:                                                                                                                   
  - Use the attached screenshot showing emotion selection                                                                           
  - Display as an iPhone 15 Pro frame                                                                                               
  - Position: Center, lower 60% of canvas                                                                                           
                                                                                                                                    
  STYLE: Empathetic, warm, supportive                                                                                               
                                                                                                                                    
  ---                                                                                                                               
  Screenshot 5: Personalization                                                                                                     
                                                                                                                                    
  構成                                                                                                                              
  ┌──────────────┬────────────────────────────────────────────────────────────────┐                                                 
  │     要素     │                              内容                              │                                                 
  ├──────────────┼────────────────────────────────────────────────────────────────┤                                                 
  │ 使用画面     │ Profile Tab（Ideal Self、Struggles チップ選択）                │                                                 
  ├──────────────┼────────────────────────────────────────────────────────────────┤                                                 
  │ ヘッドライン │ EN: "Personalized to Your Life" / JP: "あなたの人生に合わせて" │                                                 
  ├──────────────┼────────────────────────────────────────────────────────────────┤                                                 
  │ 背景         │ ダークネイビー                                                 │                                                 
  ├──────────────┼────────────────────────────────────────────────────────────────┤                                                 
  │ 役割         │ カスタマイズ性を訴求                                           │                                                 
  └──────────────┴────────────────────────────────────────────────────────────────┘                                                 
  理由                                                                                                                              
                                                                                                                                    
  - 「自分に合う」と思わせることでインストール率向上                                                                                
  - Ideal Self、Struggles の視覚的なチップUIが魅力的                                                                                
                                                                                                                                    
  英語プロンプト                                                                                                                    
                                                                                                                                    
  Create an App Store screenshot for "Anicca" - a personalized AI coaching app.                                                     
                                                                                                                                    
  SIZE: 1320 × 2868 pixels (iPhone 6.9" portrait)                                                                                   
                                                                                                                                    
  BACKGROUND:                                                                                                                       
  - Dark navy (#16213e)                                                                                                             
  - Very subtle geometric pattern at 3% opacity                                                                                     
  - Clean, professional                                                                                                             
                                                                                                                                    
  HEADLINE (top center, about 15% from top):                                                                                        
  - Text: "Personalized to Your Life"                                                                                               
  - Font: Bold sans-serif                                                                                                           
  - Color: White (#FFFFFF)                                                                                                          
  - Size: Large, prominent                                                                                                          
                                                                                                                                    
  SCREEN DISPLAY:                                                                                                                   
  - Use the attached screenshot of Profile tab showing Ideal Self chips (kind, confident, mindful) and Current Struggles chips      
  (procrastination, anxiety, etc.)                                                                                                  
  - Display as an iPhone 15 Pro frame                                                                                               
  - Position: Center, lower 60% of canvas                                                                                           
  - Clean shadow                                                                                                                    
                                                                                                                                    
  STYLE: Minimalist, functional, professional                                                                                       
                                                                                                                                    
  日本語プロンプト                                                                                                                  
                                                                                                                                    
  Create an App Store screenshot for "Anicca" - a personalized AI coaching app.                                                     
                                                                                                                                    
  SIZE: 1320 × 2868 pixels (iPhone 6.9" portrait)                                                                                   
                                                                                                                                    
  BACKGROUND:                                                                                                                       
  - Dark navy (#16213e)                                                                                                             
  - Very subtle geometric pattern at 3% opacity                                                                                     
                                                                                                                                    
  HEADLINE (top center, about 15% from top):                                                                                        
  - Text: "あなたの人生に合わせて"                                                                                                  
  - Font: Bold sans-serif (Hiragino Sans Bold)                                                                                      
  - Color: White (#FFFFFF)                                                                                                          
  - Size: Large, prominent                                                                                                          
                                                                                                                                    
  SCREEN DISPLAY:                                                                                                                   
  - Use the attached screenshot of Profile tab                                                                                      
  - Display as an iPhone 15 Pro frame                                                                                               
  - Position: Center, lower 60% of canvas                                                                                           
                                                                                                                                    
  STYLE: Minimalist, functional, professional                                                                                       
                                                                                                                                    
  ---                                                                                                                               
  Screenshot 6: Social Proof                                                                                                        
                                                                                                                                    
  構成                                                                                                                              
  ┌──────────────┬──────────────────────────────────────────────────────┐                                                           
  │     要素     │                         内容                         │                                                           
  ├──────────────┼──────────────────────────────────────────────────────┤                                                           
  │ 使用画面     │ なし（レビューカードをデザインで生成）               │                                                           
  ├──────────────┼──────────────────────────────────────────────────────┤                                                           
  │ ヘッドライン │ EN: "Users Love Anicca" / JP: "ユーザーに愛されてる" │                                                           
  ├──────────────┼──────────────────────────────────────────────────────┤                                                           
  │ 背景         │ リッチダークパープル + ゴールドグロー                │                                                           
  ├──────────────┼──────────────────────────────────────────────────────┤                                                           
  │ 役割         │ 社会的証明でトドメ                                   │                                                           
  └──────────────┴──────────────────────────────────────────────────────┘                                                           
  理由                                                                                                                              
                                                                                                                                    
  - 最後のスクショは「他の人も使ってる」安心感を与える                                                                              
  - 実際のレビュー引用で信頼性UP                                                                                                    
                                                                                                                                    
  英語プロンプト                                                                                                                    
                                                                                                                                    
  Create an App Store screenshot featuring user reviews for "Anicca" app.                                                           
                                                                                                                                    
  SIZE: 1320 × 2868 pixels (iPhone 6.9" portrait)                                                                                   
                                                                                                                                    
  BACKGROUND:                                                                                                                       
  - Rich dark purple (#1a1a2e)                                                                                                      
  - Radial golden glow in center (subtle, 15% opacity)                                                                              
  - Scattered golden sparkles (8-10 small dots)                                                                                     
                                                                                                                                    
  HEADLINE (top center, about 15% from top):                                                                                        
  - Text: "Users Love Anicca"                                                                                                       
  - Font: Bold sans-serif                                                                                                           
  - Color: White (#FFFFFF)                                                                                                          
  - Size: Large, prominent                                                                                                          
                                                                                                                                    
  CONTENT (no phone screen, just cards):                                                                                            
  Two review cards stacked vertically, centered:                                                                                    
                                                                                                                                    
  Card 1 (upper):                                                                                                                   
  - Background: Semi-transparent white (#FFFFFF at 10% opacity)                                                                     
  - Rounded corners: 20px                                                                                                           
  - ★★★★★ (5 gold stars, #FFD700)                                                                                                   
  - Quote: "This might change my life!"                                                                                             
  - Attribution: "- App Store Review" (smaller, gray text)                                                                          
  - Padding: 24px all sides                                                                                                         
                                                                                                                                    
  Card 2 (lower):                                                                                                                   
  - Same style as Card 1                                                                                                            
  - ★★★★★                                                                                                                           
  - Quote: "It feels like having a companion by my side"                                                                            
  - "- App Store Review"                                                                                                            
                                                                                                                                    
  SPACING: 24px between cards                                                                                                       
  POSITION: Cards centered vertically and horizontally                                                                              
                                                                                                                                    
  STYLE: Trust-building, celebratory, premium                                                                                       
                                                                                                                                    
  日本語プロンプト                                                                                                                  
                                                                                                                                    
  Create an App Store screenshot featuring user reviews for "Anicca" app.                                                           
                                                                                                                                    
  SIZE: 1320 × 2868 pixels (iPhone 6.9" portrait)                                                                                   
                                                                                                                                    
  BACKGROUND:                                                                                                                       
  - Rich dark purple (#1a1a2e)                                                                                                      
  - Radial golden glow in center (subtle, 15% opacity)                                                                              
  - Scattered golden sparkles (8-10 small dots)                                                                                     
                                                                                                                                    
  HEADLINE (top center, about 15% from top):                                                                                        
  - Text: "ユーザーに愛されてる"                                                                                                    
  - Font: Bold sans-serif (Hiragino Sans Bold)                                                                                      
  - Color: White (#FFFFFF)                                                                                                          
  - Size: Large, prominent                                                                                                          
                                                                                                                                    
  CONTENT:                                                                                                                          
  Two review cards stacked vertically, centered:                                                                                    
                                                                                                                                    
  Card 1:                                                                                                                           
  - Background: Semi-transparent white (10% opacity)                                                                                
  - Rounded corners: 20px                                                                                                           
  - ★★★★★ (5 gold stars)                                                                                                            
  - Quote: "人生変わるかも！"                                                                                                       
  - "- App Storeレビュー"                                                                                                           
                                                                                                                                    
  Card 2:                                                                                                                           
  - Same style                                                                                                                      
  - ★★★★★                                                                                                                           
  - Quote: "そばにいてくれる相棒みたい"                                                                                             
  - "- App Storeレビュー"                                                                                                           
                                                                                                                                    
  STYLE: Trust-building, celebratory, premium                                                                                       
                                                                                                                                    
  ---                                                                                                                               
  将来版（Proactive Agent）：6枚の構成設計                                                                                          
                                                                                                                                    
  コンセプトの変化                                                                                                                  
  ┌──────────────┬─────────────────────────┬────────────────────────────────────┐                                                   
  │     項目     │         現行版          │               将来版               │                                                   
  ├──────────────┼─────────────────────────┼────────────────────────────────────┤                                                   
  │ コア機能     │ 音声AIコーチと対話      │ プロアクティブ通知で行動変容       │                                                   
  ├──────────────┼─────────────────────────┼────────────────────────────────────┤                                                   
  │ メイン画面   │ Talk Tab, Voice Session │ Nudge Card, My Path                │                                                   
  ├──────────────┼─────────────────────────┼────────────────────────────────────┤                                                   
  │ 訴求ポイント │ 「話せる」              │ 「あなたをケアする」「刺さる通知」 │                                                   
  ├──────────────┼─────────────────────────┼────────────────────────────────────┤                                                   
  │ タブ構成     │ Habits, Talk, Profile   │ My Path, Profile                   │                                                   
  └──────────────┴─────────────────────────┴────────────────────────────────────┘                                                   
  ---                                                                                                                               
  Screenshot 1: Hero/Hook                                                                                                           
  ┌──────────────┬────────────────────────────────────────────────────────────────────────────────────┐                             
  │     要素     │                                        内容                                        │                             
  ├──────────────┼────────────────────────────────────────────────────────────────────────────────────┤                             
  │ 使用画面     │ 通知プレビュー3つ並べたモックアップ                                                │                             
  ├──────────────┼────────────────────────────────────────────────────────────────────────────────────┤                             
  │ ヘッドライン │ EN: "Your AI That Cares More Than You Do" / JP: "あなた以上にあなたを気にかけるAI" │                             
  ├──────────────┼────────────────────────────────────────────────────────────────────────────────────┤                             
  │ 背景         │ ダークパープル + ゴールドアクセント                                                │                             
  ├──────────────┼────────────────────────────────────────────────────────────────────────────────────┤                             
  │ コンテンツ   │ 3つの通知プレビュー（刺さる文言）                                                  │                             
  └──────────────┴────────────────────────────────────────────────────────────────────────────────────┘                             
  詳細構成                                                                                                                          
                                                                                                                                    
  画面内容:                                                                                                                         
  - 3つの通知カード（縦に並べる）:                                                                                                  
    1. "That 'just 5 more minutes'? You've said it 100 times. ☀️" (6:00 AM)                                                         
    2. "Stop scrolling. Your future self is crying. 🌙" (11:30 PM)                                                                  
    3. "Breathe. You're safe right now. 🧘" (3:00 PM)                                                                               
                                                                                                                                    
  背景色: #1a1a2e (ダークパープル)                                                                                                  
  アクセント: #FFD700 (ゴールド) - 通知アイコンに                                                                                   
                                                                                                                                    
  理由                                                                                                                              
                                                                                                                                    
  - 通知が主役なので、通知を前面に出す                                                                                              
  - 3つの異なる時間帯・問題を見せることで「24時間ケア」を伝える                                                                     
  - 刺さる文言で「他のアプリと違う」を即座に伝える                                                                                  
                                                                                                                                    
  ---                                                                                                                               
  Screenshot 2: Nudge Card（1枚画面）                                                                                               
  ┌──────────────┬───────────────────────────────────────────────────────────────┐                                                  
  │     要素     │                             内容                              │                                                  
  ├──────────────┼───────────────────────────────────────────────────────────────┤                                                  
  │ 使用画面     │ NudgeCardView（通知タップ後の詳細画面）                       │                                                  
  ├──────────────┼───────────────────────────────────────────────────────────────┤                                                  
  │ ヘッドライン │ EN: "Take Action in One Tap" / JP: "ワンタップで行動を起こす" │                                                  
  ├──────────────┼───────────────────────────────────────────────────────────────┤                                                  
  │ 背景         │ ダークウォーム                                                │                                                  
  ├──────────────┼───────────────────────────────────────────────────────────────┤                                                  
  │ コンテンツ   │ フルスクリーンNudge Card                                      │                                                  
  └──────────────┴───────────────────────────────────────────────────────────────┘                                                  
  詳細構成                                                                                                                          
                                                                                                                                    
  画面内容（proactive-agent-specより）:                                                                                             
  - Icon: 🌙                                                                                                                        
  - Problem type: "STAYING UP LATE"                                                                                                 
  - Main quote: "スクロールより、呼吸。"                                                                                            
  - Detail: "夜更かしは明日の自分を傷つける行為。今夜は画面を閉じよう。"                                                            
  - Buttons: 「明日を守る 💪」(Primary左) / 「傷つける」(Ghost右)                                                                   
  - 👍👎 at bottom                                                                                                                  
                                                                                                                                    
  背景色: #1c1917 (ウォームダーク)                                                                                                  
                                                                                                                                    
  理由                                                                                                                              
                                                                                                                                    
  - 通知タップ後の体験を見せる                                                                                                      
  - 「ワンタップで行動」= 低摩擦を訴求                                                                                              
  - 実際のUIを見せることで期待値を設定                                                                                              
                                                                                                                                    
  ---                                                                                                                               
  Screenshot 3: My Path Tab                                                                                                         
  ┌──────────────┬─────────────────────────────────────────────────────────────────────┐                                            
  │     要素     │                                内容                                 │                                            
  ├──────────────┼─────────────────────────────────────────────────────────────────────┤                                            
  │ 使用画面     │ MyPathView（苦しみリスト + 深掘りボタン）                           │                                            
  ├──────────────┼─────────────────────────────────────────────────────────────────────┤                                            
  │ ヘッドライン │ EN: "We Understand Your Struggles" / JP: "あなたの苦しみを理解する" │                                            
  ├──────────────┼─────────────────────────────────────────────────────────────────────┤                                            
  │ 背景         │ ダークネイビー                                                      │                                            
  ├──────────────┼─────────────────────────────────────────────────────────────────────┤                                            
  │ コンテンツ   │ 3-4個の問題カード                                                   │                                            
  └──────────────┴─────────────────────────────────────────────────────────────────────┘                                            
  詳細構成                                                                                                                          
                                                                                                                                    
  画面内容:                                                                                                                         
  - Header: "My Path"                                                                                                               
  - Problem cards:                                                                                                                  
    - 🌙 夜更かし (Staying Up Late)                                                                                                 
    - 💭 反芻 (Overthinking)                                                                                                        
    - 😔 自己嫌悪 (Self-Loathing)                                                                                                   
    - 😰 不安 (Anxiety)                                                                                                             
  - Each card has "深掘りする" button                                                                                               
                                                                                                                                    
  背景色: #16213e (ダークネイビー)                                                                                                  
                                                                                                                                    
  理由                                                                                                                              
                                                                                                                                    
  - 13個の問題 = ユーザーの苦しみに寄り添う                                                                                         
  - 「理解する」というコピーで共感を示す                                                                                            
  - キーワード「anxiety」「self-loathing」等との整合性                                                                              
                                                                                                                                    
  ---                                                                                                                               
  Screenshot 4: Onboarding（苦しみ選択）                                                                                            
  ┌──────────────┬───────────────────────────────────────────────────────────────────┐                                              
  │     要素     │                               内容                                │                                              
  ├──────────────┼───────────────────────────────────────────────────────────────────┤                                              
  │ 使用画面     │ StrugglesStepView（オンボーディング苦しみ選択）                   │                                              
  ├──────────────┼───────────────────────────────────────────────────────────────────┤                                              
  │ ヘッドライン │ EN: "Tell Us What You're Facing" / JP: "今抱えている問題を教えて" │                                              
  ├──────────────┼───────────────────────────────────────────────────────────────────┤                                              
  │ 背景         │ ダークパープル                                                    │                                              
  ├──────────────┼───────────────────────────────────────────────────────────────────┤                                              
  │ コンテンツ   │ 13個の苦しみチップ（複数選択）                                    │                                              
  └──────────────┴───────────────────────────────────────────────────────────────────┘                                              
  詳細構成                                                                                                                          
                                                                                                                                    
  画面内容:                                                                                                                         
  - Flow layout of 13 problem chips:                                                                                                
    - 夜更かし, 起きれない, 自己嫌悪, 反芻, 先延ばし, 不安,                                                                         
    - 嘘をつく, 悪口, ポルノ依存, お酒依存, 怒り, 強迫的思考, 孤独                                                                  
  - Some chips selected (checkmarks)                                                                                                
                                                                                                                                    
  背景色: #1a1a2e (ダークパープル)                                                                                                  
  アクセント: #00D084 (グリーン) - 選択済みチップ                                                                                   
                                                                                                                                    
  理由                                                                                                                              
                                                                                                                                    
  - 「あなた専用」のパーソナライズを訴求                                                                                            
  - 13個の問題 = 幅広いユーザーに刺さる                                                                                             
  - オンボーディングの簡潔さを見せる                                                                                                
                                                                                                                                    
  ---                                                                                                                               
  Screenshot 5: Deep Dive Questions                                                                                                 
  ┌──────────────┬───────────────────────────────────────────────────────────────────────────────┐                                  
  │     要素     │                                     内容                                      │                                  
  ├──────────────┼───────────────────────────────────────────────────────────────────────────────┤                                  
  │ 使用画面     │ DeepDiveSheet（深掘り質問）                                                   │                                  
  ├──────────────┼───────────────────────────────────────────────────────────────────────────────┤                                  
  │ ヘッドライン │ EN: "The More We Know, The Better We Help" / JP: "知れば知るほど、助けられる" │                                  
  ├──────────────┼───────────────────────────────────────────────────────────────────────────────┤                                  
  │ 背景         │ ウォームダーク                                                                │                                  
  ├──────────────┼───────────────────────────────────────────────────────────────────────────────┤                                  
  │ コンテンツ   │ 深掘り質問UI                                                                  │                                  
  └──────────────┴───────────────────────────────────────────────────────────────────────────────┘                                  
  詳細構成                                                                                                                          
                                                                                                                                    
  画面内容:                                                                                                                         
  - Header: "夜更かし" (Staying Up Late)                                                                                            
  - Question 1: "夜更かしして何をしてることが多い？"                                                                                
    - Options: [SNS] [YouTube] [ゲーム] [仕事]                                                                                      
  - Question 2: "なぜ夜更かししてしまう？"                                                                                          
    - Options: [今日やるべきことができなかった] [ストレス解消] [習慣] [寝たくない]                                                  
  - Save button                                                                                                                     
                                                                                                                                    
  背景色: #1c1917 (ウォームダーク)                                                                                                  
                                                                                                                                    
  理由                                                                                                                              
                                                                                                                                    
  - AIがユーザーを「理解する」プロセスを見せる                                                                                      
  - 質問の具体性で「本当に分かってくれる」感を出す                                                                                  
                                                                                                                                    
  ---                                                                                                                               
  Screenshot 6: Social Proof                                                                                                        
  ┌──────────────┬─────────────────────────────────────────────────────────────────────────────────────┐                            
  │     要素     │                                        内容                                         │                            
  ├──────────────┼─────────────────────────────────────────────────────────────────────────────────────┤                            
  │ 使用画面     │ なし（レビューカード生成）                                                          │                            
  ├──────────────┼─────────────────────────────────────────────────────────────────────────────────────┤                            
  │ ヘッドライン │ EN: "Finally, Something That Actually Works" / JP: "やっと見つけた、本当に効くやつ" │                            
  ├──────────────┼─────────────────────────────────────────────────────────────────────────────────────┤                            
  │ 背景         │ リッチダークパープル                                                                │                            
  ├──────────────┼─────────────────────────────────────────────────────────────────────────────────────┤                            
  │ コンテンツ   │ 2つのレビューカード                                                                 │                            
  └──────────────┴─────────────────────────────────────────────────────────────────────────────────────┘                            
  詳細構成                                                                                                                          
                                                                                                                                    
  画面内容:                                                                                                                         
  Card 1:                                                                                                                           
  - ★★★★★                                                                                                                           
  - "The notifications are harsh but they work. I actually put my phone down now."                                                  
  - "- App Store Review"                                                                                                            
                                                                                                                                    
  Card 2:                                                                                                                           
  - ★★★★★                                                                                                                           
  - "It's like having a strict but caring friend who won't let me slack off."                                                       
  - "- App Store Review"                                                                                                            
                                                                                                                                    
  背景色: #1a1a2e (ダークパープル)                                                                                                  
  ゴールドグロー + スパークル                                                                                                       
                                                                                                                                    
  理由                                                                                                                              
                                                                                                                                    
  - 「厳しいけど効く」= Proactive Agentの本質                                                                                       
  - 行動変容の結果を他人の声で伝える                                                                                                
                                                                                                                                    
  ---                                                                                                                               
  まとめ表                                                                                                                          
                                                                                                                                    
  現行版（Voice AI Coach）                                                                                                          
  ┌─────┬───────────────────────────┬───────────────────────────────┬──────────────────────────────┐                                
  │  #  │           画面            │          EN Headline          │         JP Headline          │                                
  ├─────┼───────────────────────────┼───────────────────────────────┼──────────────────────────────┤                                
  │ 1   │ Talk Tab                  │ Talk to Your AI Coach Anytime │ いつでもAIコーチと話せる     │                                
  ├─────┼───────────────────────────┼───────────────────────────────┼──────────────────────────────┤                                
  │ 2   │ Voice Session (Orb)       │ 24/7 AI Voice Coach           │ 24時間対応のAI音声コーチ     │                                
  ├─────┼───────────────────────────┼───────────────────────────────┼──────────────────────────────┤                                
  │ 3   │ Habits Section            │ Set Habits. We'll Remind You. │ 習慣を設定。あとはおまかせ。 │                                
  ├─────┼───────────────────────────┼───────────────────────────────┼──────────────────────────────┤                                
  │ 4   │ Emotion Selection         │ Struggling? Anicca Listens.   │ 悩んでる？Aniccaが聞くよ。   │                                
  ├─────┼───────────────────────────┼───────────────────────────────┼──────────────────────────────┤                                
  │ 5   │ Profile (Personalization) │ Personalized to Your Life     │ あなたの人生に合わせて       │                                
  ├─────┼───────────────────────────┼───────────────────────────────┼──────────────────────────────┤                                
  │ 6   │ Reviews                   │ Users Love Anicca             │ ユーザーに愛されてる         │                                
  └─────┴───────────────────────────┴───────────────────────────────┴──────────────────────────────┘                                
  将来版（Proactive Agent）                                                                                                         
  ┌─────┬─────────────────────┬────────────────────────────────────────┬──────────────────────────────────┐                         
  │  #  │        画面         │              EN Headline               │           JP Headline            │                         
  ├─────┼─────────────────────┼────────────────────────────────────────┼──────────────────────────────────┤                         
  │ 1   │ 通知3つモック       │ Your AI That Cares More Than You Do    │ あなた以上にあなたを気にかけるAI │                         
  ├─────┼─────────────────────┼────────────────────────────────────────┼──────────────────────────────────┤                         
  │ 2   │ Nudge Card          │ Take Action in One Tap                 │ ワンタップで行動を起こす         │                         
  ├─────┼─────────────────────┼────────────────────────────────────────┼──────────────────────────────────┤                         
  │ 3   │ My Path Tab         │ We Understand Your Struggles           │ あなたの苦しみを理解する         │                         
  ├─────┼─────────────────────┼────────────────────────────────────────┼──────────────────────────────────┤                         
  │ 4   │ Struggles Selection │ Tell Us What You're Facing             │ 今抱えている問題を教えて         │                         
  ├─────┼─────────────────────┼────────────────────────────────────────┼──────────────────────────────────┤                         
  │ 5   │ Deep Dive Sheet     │ The More We Know, The Better We Help   │ 知れば知るほど、助けられる       │                         
  ├─────┼─────────────────────┼────────────────────────────────────────┼──────────────────────────────────┤                         
  │ 6   │ Reviews             │ Finally, Something That Actually Works │ やっと見つけた、本当に効くやつ   │                         
  └─────┴─────────────────────┴────────────────────────────────────────┴──────────────────────────────────┘                         
  ---                                                                                                                               
  現行版のプロンプトは上記の通り。使ってNano Bananaで生成してください。                                                             
                                                                                                                                    