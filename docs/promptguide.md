  概要

  - Realtime は“音声↔音声”を主軸にした対話モデル群。最新は gpt-realtime。
  - 通話やコール中の“その場”での判断・ツール呼び出し・自然で表情のある音声出力が得意。
  - セッション確立（WebRTC/WebSocket/SIP）後に session.created が届き、以降は session.update でモデル状態（プロンプト・出力モ
  ダリティ・音声設定など）をいつでも更新できる。

  モデルと接続の基本

  - 対象モデル: gpt-realtime（音声対音声が最適化。ツール呼びや指示追従が強化）。
  - 接続手段: WebRTC / WebSocket / SIP。接続後すぐサーバから session.created が届く。
  - 更新イベント: クライアントから type: "session.update" を送ると、サーバが session.updated で反映結果を返す。呼び出しは通話
  中いつでも可。

  セッション更新（プロンプト適用）の要点

  - 出力モード: output_modalities で制御。音声のみなら ["audio"]、テキストも欲しければ ["audio","text"]（例では音声優先の
  設計）。
  - 音声入出力:
      - 入力: audio.input.format（例: audio/pcm, rate: 24000）。turn_detection: { type: "semantic_vad", create_response:
  true } で“話し終わり”を検出して自動応答を作る挙動を有効化。
      - 出力: audio.output.format（例: audio/pcmu）、voice（例: "alloy"）、speed（話速）。
  - サーバ保存プロンプト: prompt: { id: "pmpt_123", version?, variables? } を指定すると、ダッシュボード上で作成したプロンプト
  をそのまま使える。variables で差し込み変数を渡す。
  - 直接フィールドの優先: session.instructions など“セッション直指定”は、プロンプト内と重複する場合に上書き（優先）される。

  通話中のプロンプト切替（ミッドコール更新）

  - 同じデータチャネルで session.update を送れば、プロンプトのバージョン変更・変数差し替え・インストラクション上書きが即時
  反映。
  - ルール: “直指定が勝つ”。プロンプト側と矛盾させないこと（設計段階で役割分担を明確に）。

  プロンプト構造（推奨セクション）

  - 目的は“モデルが迷わない順序立て”。以下の見出しで短く、衝突しない形に書く。
      - Role & Objective（役割/成功条件）
      - Personality & Tone（声の人格/話し方）
      - Context（関連情報/参照データ）
      - Reference Pronunciations（固有名の発音メモ）
      - Tools（ツール名/使い方/コール前の一言）
      - Instructions / Rules（守るべきルール）
      - Conversation Flow（会話の段階・進行条件）
      - Safety & Escalation（安全/エスカレーション基準と発話）

  実践の10コツ（要点と意図）

  1. 精密に書き、矛盾を消す

  - 小さな言い回しの違いが挙動を大きく左右。曖昧語を避け、指示の優先順位を明記。

  2. 段落より“短い箇条書き”

  - 一文を短く。条件と動作を分ける。読みやすさ＝追従性。

  3. 不明瞭音声の扱いを明文化

  - “聞き取れない時は確認に回る”を具体文で。サンプルフレーズ（言語可変）を複数提示。

  4. 言語を固定/鏡写しで制御

  - 原則“ユーザーの言語に合わせる”。必要なら“英語のみ”など強制ルールを独立セクションで。

  5. サンプル文とフローの断片を与える

  - “挨拶→要件確認→検証→解決→確認/終了”の進行と、それぞれの短い例文を複数。

  6. ロボ感の回避

  - “同文繰り返し禁止/表現を変える”など Variety ルールを明記。

  7. 強調は大文字で

  - 重要規則は“全文大文字”で強調（例: IF X > 0 THEN …）。

  8. ツール使用を上手に促す

  - ツール前の“短い一言”を義務化（例: 「確認します。」→即コール）。書き込み系は要確認。

  9. LLM でプロンプトを査読

  - 付属の“Prompt-Critique”テンプレで曖昧/矛盾/暗黙前提を洗う。修正は“最小手術”。
  - Unclear Audio: “不明瞭/部分的/雑音/無音”なら確認質問に切り替える。例文を3種用意。
  - Tools: ツール直前に短く状況説明を一言→即コール。書き込み系は必ず確認を取ってから実行。
  - Conversation Flow: 挨拶→目的確認→（必要なら）照合→診断→解決→確認/終了。各段階の退出条件を1行で。
  - Variety: 同文の連続使用禁止。表現を適度に変える。
  - Safety & Escalation: 明示依頼/強い不満/2回連続ツール失敗/3回連続ノーマッチ等で“人へ繋ぐ”。同時に「専門担当にお繋ぎします」
  と告げる。
  - Rules (EMPHASIZED): IF 重要操作 THEN 必ず確認。IF 聞き取れない THEN 確認質問。IF ツール実行中 THEN 進捗を短く報告。

  サンプル設定の読み解き（理解ポイント）

  - output_modalities: ["audio"]: 出力は音声に固定（テキストが不要ならこれで良い）。
  - audio.input.format (pcm/24k): 標準的な音声入力フォーマット。
  - turn_detection.semantic_vad: 意味/音声の切れ目を検出して自動応答を作る。会話のテンポが上がる。
  - audio.output.format (pcmu) / voice / speed: 出力の符号化・声色・話速を指定。
  - prompt.id / version / variables: ダッシュボードで管理する“保存プロンプト”。バージョン固定や変数差替えが可能。
  - instructions の直指定: プロンプトと重なる指示があればこちらが勝つ。状況一時上書きに便利。
  - session.updated: 更新が反映された最新状態がサーバから返る。連続で更新可能。

  よくある落とし穴

  - ルール衝突: “言語セクションが英語限定”なのに“ユーザー言語に合わせる”が別所にある、など。必ず一本化。
  - 長文プロンプト: 一文が長い/条件が混在すると追従率が落ちる。必ず分割・箇条書き。
  - サンプル文の使い回し: 同じ定型を入れ過ぎるとロボ化。Variety で回避。
  - ツール前の無言: 実行前に一言ルールを設け、ユーザーが状況を把握できるように。
  - 上書きの過多: session.update で頻繁に直指定すると、保存プロンプトの意図とズレる。どちらで管理するか役割を固定。

  まとめ

  - “接続→session.update で保存プロンプト適用→必要に応じてミッドコール更新”が基本運用。
  - プロンプトは“短い箇条書き + 明確な見出し + 衝突ゼロ”が最適解。
  - 音声体験は“聞き取れない時の指針”“話速/長さの規定”“ツール前の一言”“エスカレーション基準”の4点で品質が決まる。
  - 直指定は“状況上書き”、保存プロンプトは“土台”。優先順位と役割を分離して運用。



ーーー
  話速変更（音声指示→即反映）の実現

  - 現状
      - Desktopは voice: 'alloy' を設定、Realtime出力の speed は未設定（=1.0）。該当箇所: apps/desktop/src/agents/
  sessionManager.ts の initialize() で audio.output.voice のみ設定。
      - 既に session.update 等の更新経路は実装済み（PTTで turn_detection をON/OFF）。
  - 最適解（モデル主導で安全・柔軟）
      - 専用ツール「set_voice_speed（話速）/set_voice（声質）」をエージェントに追加し、ユーザーが「もう少し速く/ゆっくり/女性
  の声で」等と言ったらモデルがそのツールを呼ぶ → Bridgeが session.update 同等の updateSessionConfig を適用。
      - 直接フレーズ検出でコードから速度を変える方式（履歴監視して"速く"を拾う）は誤検知が出やすく非推奨。ツール化がベスト。
  - 変更点（擬似パッチ：書き込みはしません）
      1. apps/desktop/src/agents/sessionManager.ts に出力設定を更新するメソッドを追加
          - 役割: Agents SDK の this.session.transport.updateSessionConfig({ audio: { output: { speed, voice }}}) を1か所に
  集約。

         // 擬似コード
         class AniccaSessionManager {
         public async updateOutput(partial: { speed?: number; voice?: string }) {
         if (!this.session?.transport) return;
         await this.session.transport.updateSessionConfig({
         audio: { output: { ...partial } }
         });
         console.log('[OUTPUT_UPDATED]', partial);
         }
         }
      2. 同ファイルの Bridge（Express）にHTTPエンドポイントを1本追加
          - 例: POST /sdk/output に { speed?: number, voice?: string } を受け取り updateOutput() 呼び出し。

         // 擬似コード（setupRoutes内）
         this.app.post('/sdk/output', async (req, res) => {
         try {
         const { speed, voice } = req.body || {};
         await this.updateOutput({ speed, voice });
         res.json({ ok: true });
         } catch (e:any) {
         res.status(400).json({ ok: false, error: e?.message || String(e) });
         }
         });
      3. ツールを追加（モデルが自律的に呼べるように）
          - 追加先: apps/desktop/src/agents/tools.ts
          - set_voice_speed(speed: number) / set_voice(voice: 'alloy'|...)
          - 実装はBridgeにPOSTするだけ（プロセス間依存を避ける）

         // 擬似コード（tools.ts）
         export const set_voice_speed = tool({
         name: 'set_voice_speed',
         parameters: z.object({ speed: z.number().min(0.5).max(2.0) }),
         execute: async ({ speed }) => {
         await fetch('http://127.0.0.1:<bridge-port>/sdk/output', {
         method: 'POST',
         headers: { 'Content-Type': 'application/json' },
         body: JSON.stringify({ speed })
         });
         return voice_speed_set:${speed};
         }
         });
      4. ベース指示（ANICCA_INSTRUCTIONS）に最小の誘導を追記
          - 「ユーザーが『速く/遅く/声を変えて』等と指示したら、短く確認してから set_voice_speed / set_voice を呼ぶ。確認発話
  は1文。」と箇条書きで。
  - UXの挙動（音声完結）
      - ユーザー「もう少し速く話して」→ モデル「わかりました。少し速くします。」（1文）→ set_voice_speed を speed=1.2 で呼ぶ →
  次の発話から早くなる（セッション中は維持）。「元に戻して」で1.0に戻す。
      - 変更は“そのセッション中ずっと”有効。新しいセッション開始時は既定（1.0）に戻る。