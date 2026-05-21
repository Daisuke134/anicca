# Gemini Live API Focus Watch 実装計画

## 実現したいユーザー体験：Anicca　一方的な声かけ

### 概要

Aniccaは、画面を監視し、集中を妨げる行動を検知したときに音声で優しく声をかける機能です。時間ベースのリマインダーと、イベントベースの行動検知を組み合わせます。

Aniccaのペルソナ
トーン: ユーザーの設定（Calm/Strict/Focus）に合わせるが、基本は「冷静で、慈悲深く、しかし断固とした」態度。
音声: 一方的な語りかけ（ユーザーのマイク入力は基本不要。Aniccaが画面を見て話しかけるスタイル）。

### 1. セットアップ（初回のみ）

**ユーザーの行動：**

- アプリの設定画面を開く
- 「Focus Watch」タブを選択
- 「注意キーワード」に「YouTube」「Twitter」「Instagram」などを入力
- 「褒めキーワード」に「タスク完了」「作業終了」などを入力
- 「開始」ボタンをクリック

**システムの反応：**

- 画面キャプチャが2秒間隔で開始
- Live APIセッションが確立
- 設定画面に「Focus Watch: 実行中」と表示

### 2. 日常の使用シーン

#### シーンA: 朝の作業中にYouTubeを開いてしまった

**時間：午前10:30**

**ユーザーの行動：**

- 作業中にYouTubeを開く
- 動画を見始める

**Aniccaの反応：**

- 画面を検知し、2〜3秒後に音声で：
  - 「YouTubeを開いたね。観たい気持ちは分かるけど、あと2分で一度閉じようか？作業に戻れるよ。」
- ユーザーが閉じない場合、さらに：
  - 「さっきと同じパターンになりそう。観たい気持ちは尊重するけど、約束した作業時間を思い出して。あと1分で閉じようか？」

**ユーザーの反応：**

- 動画を閉じて作業に戻る

**Aniccaの反応：**

- 「戻ってくれてありがとう。その調子で続けよう。」

#### シーンB: タスク完了を検知して褒める

**時間：午後2:15**

**ユーザーの行動：**

- タスク管理アプリで「完了」をクリック
- 画面に「タスク完了」と表示

**Aniccaの反応：**

- 画面を検知し、音声で：
  - 「タスク完了、おつかれさま。その調子で続けよう。」

#### シーンC: 長時間の集中をサポート

**時間：午後3:00**

**ユーザーの行動：**

- 2時間集中して作業を続ける
- 途中でTwitterを開きそうになる

**Aniccaの反応：**

- Twitterを開く前に検知し、音声で：
  - 「集中が続いているね。もう少しで区切りがつきそう。Twitterは後回しにして、このまま続けようか？」

#### シーンD: 時間ベースのリマインダーとの連携

**時間：朝7:30**

**Anicca（時間ベースリマインダー）の反応：**

- 「1、2、3、起きろ。スマホに逃げるな、今立ち上がれ。」

**ユーザーの行動：**

- 起きてスマホを触る
- YouTubeを開く

**Anicca（Focus Watch）の反応：**

- 画面を検知し、音声で：
  - 「今日は2回目の動画だね。さっきと同じパターンになりそう。観たい気持ちは尊重するけど、あと2分で一度閉じよう？」
- ユーザーが閉じない場合：
  - 「起きたばかりだし、動画に逃げるのは分かる。でも、約束した時間だよ。一度閉じて、朝の準備を始めようか？」

### 3. 終了操作

**ユーザーの行動：**

- トレイアイコンをクリック
- 「Focus Watch 停止」を選択

**Aniccaの反応：**

- 「監視終了。終日つきあわせてくれてありがとう。次に必要になったらまた一声かけて。」

**システムの反応：**

- 画面キャプチャが停止
- Live APIセッションが終了
- 設定画面に「Focus Watch: 停止中」と表示

### 4. 体験の特徴

#### 時間ベース × イベントベースのハイブリッド

- **時間ベース**: 起床・就寝など、決まった時刻のリマインダー
- **イベントベース**: 画面の行動を検知してリアルタイムに声をかける

#### 優しくも確信のある声かけ

- 最初は優しく促す
- 続く場合は段階的に厳しく
- 完了時は褒める

#### 自然な会話

- 画面の文脈を理解して声をかける
- パターンを認識して適切に介入
- ユーザーの気持ちに寄り添う

## 調査結果サマリー

### Gemini Live API仕様確認済み

- **WebSocketエンドポイント**: `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent`
- **認証方式**: API KeyまたはEphemeral Token（`client.authTokens.create()`）
- **SDK**: `@google/genai` パッケージを使用（`GoogleGenAI`クラス）
- **モデル**: `gemini-2.5-flash-native-audio-preview-09-2025` または `gemini-2.0-flash-live-preview-04-09`
- **音声形式**: 入力16kHz PCM16、出力24kHz PCM
- **WebRTC**: 使用しない（WebSocketベース）

### Ephemeral Token生成

- **エンドポイント**: `POST https://generativelanguage.googleapis.com/v1alpha/authTokens`（SDK経由）
- **パラメータ**: `uses: 1`, `expireTime`, `newSessionExpireTime`, `liveConnectConstraints`（オプション）
- **レスポンス**: `token.name` をクライアントに返す

## 実装ファイルと変更内容

### 1. apps/desktop/package.json

**変更箇所**: `dependencies`セクションに追加

```json
"@google/genai": "^1.0.0"
```

### 2. apps/api/package.json  

**変更箇所**: `dependencies`セクションに追加

```json
"@google/genai": "^1.0.0"
```

### 3. apps/desktop/src/config.ts

**変更箇所**: `API_ENDPOINTS`オブジェクト内（163行目付近）

```typescript
SLACK: {
  OAUTH_URL: `${PROXY_URL}/api/auth/slack/oauth/url`
},
GEMINI: {
  LIVE_TOKEN: `${PROXY_URL}/api/gemini/live/token`,
},
```

### 4. apps/api/src/routes/index.js

**変更箇所**: ルーター登録セクション（51行目付近）

```javascript
import geminiLiveRouter from './gemini/live.js';

// ... 既存のimport ...

router.use('/mcp/gcal', mcpGcalRouter);

router.use('/gemini/live', geminiLiveRouter);

router.use('/tools/news', newsRouter);
```

### 5. apps/api/src/routes/gemini/live.js（新規作成）

**完全なファイル内容**:

```javascript
import express from 'express';
import { GoogleGenAI } from '@google/genai';
import baseLogger from '../../utils/logger.js';

const router = express.Router();
const logger = baseLogger.withContext('GeminiLive');

router.post('/token', async (req, res) => {
  try {
    const geminiApiKey = process.env.GEMINI_API_KEY;
    if (!geminiApiKey) {
      return res.status(500).json({ error: 'GEMINI_API_KEY not configured on proxy' });
    }

    const userId = req.get('user-id') || req.body.userId;
    if (!userId) {
      return res.status(401).json({ error: 'user-id is required' });
    }

    const client = new GoogleGenAI({ apiKey: geminiApiKey });
    const expireTime = new Date(Date.now() + 30 * 60 * 1000).toISOString();
    const newSessionExpireTime = new Date(Date.now() + 1 * 60 * 1000).toISOString();

    const token = await client.authTokens.create({
      config: {
        uses: 1,
        expireTime: expireTime,
        newSessionExpireTime: newSessionExpireTime,
        liveConnectConstraints: {
          model: 'gemini-2.5-flash-native-audio-preview-09-2025',
          config: {
            responseModalities: ['AUDIO'],
            systemInstruction: {
              parts: [{ text: 'You are a focus assistant that helps users stay focused by monitoring their screen activity and providing gentle reminders when they get distracted.' }]
            }
          }
        },
        httpOptions: {
          apiVersion: 'v1alpha'
        }
      }
    });

    return res.json({
      token: token.name,
      expiresAt: expireTime
    });
  } catch (err) {
    logger.error(`gemini-live-token error: ${err?.message || String(err)}`);
    return res.status(500).json({ error: 'failed to create ephemeral token', message: err?.message || String(err) });
  }
});

export default router;
```

### 6. apps/desktop/src/services/onboardingWriter.ts

**変更箇所1**: 13行目付近（定数定義の後）

```typescript
const promptsDir = path.join(baseDir, 'prompts');
const groundedPromptPath = path.join(promptsDir, 'common.txt');
const focusRulesPath = path.join(baseDir, 'focus_rules.json');

export interface FocusRules {
  attentionKeywords: string[];
  praiseKeywords: string[];
}
```

**変更箇所2**: 14行目付近（OnboardingPayloadインターフェース）

```typescript
export interface OnboardingPayload {
  wake: { enabled: boolean; time: string; location?: string };
  sleep: { enabled: boolean; time: string; location?: string };
  profile: { name: string; language?: 'Japanese' | 'English' };
  focus: FocusRules;
}
```

**変更箇所3**: 19行目付近（DEFAULT_FOCUS_RULES定数追加）

```typescript
const DEFAULT_FOCUS_RULES: FocusRules = {
  attentionKeywords: ['YouTube'],
  praiseKeywords: ['タスク完了']
};

function normalizeFocusList(list?: string[]): string[] {
  if (!Array.isArray(list)) return [];
  return list.map((item) => String(item).trim()).filter(Boolean);
}

function normalizeFocusRules(source?: FocusRules | null): FocusRules {
  const attention = normalizeFocusList(source?.attentionKeywords);
  const praise = normalizeFocusList(source?.praiseKeywords);
  return {
    attentionKeywords: attention.length ? attention : DEFAULT_FOCUS_RULES.attentionKeywords,
    praiseKeywords: praise.length ? praise : DEFAULT_FOCUS_RULES.praiseKeywords
  };
}

export async function writeFocusRules(rules?: FocusRules): Promise<void> {
  const normalized = normalizeFocusRules(rules);
  await fs.promises.mkdir(baseDir, { recursive: true, mode: 0o700 });
  await fs.promises.writeFile(
    focusRulesPath,
    JSON.stringify(normalized, null, 2),
    { encoding: 'utf8', mode: 0o600 }
  );
}

export async function readFocusRules(): Promise<FocusRules> {
  try {
    const raw = await fs.promises.readFile(focusRulesPath, 'utf8');
    const parsed = JSON.parse(raw);
    return normalizeFocusRules(parsed);
  } catch {
    await writeFocusRules(DEFAULT_FOCUS_RULES);
    return DEFAULT_FOCUS_RULES;
  }
}
```

**変更箇所4**: 180行目付近（applyOnboardingData関数内）

```typescript
export async function applyOnboardingData(payload: OnboardingPayload): Promise<void> {
  await ensureBaselineFiles();
  await updateProfile(payload);
  await updateScheduledTasks(payload);
  await writeGroundedPrompt(payload);
  await writeFocusRules(payload.focus ?? DEFAULT_FOCUS_RULES);
  syncTodayTasksFromMarkdown();
}
```

**変更箇所5**: 188行目付近（loadSettingsFromFiles関数内）

```typescript
export async function loadSettingsFromFiles(): Promise<OnboardingPayload> {
  await ensureBaselineFiles();
  const assets = resolveLanguageAssets();
  
  // ... 既存のコード ...
  
  const focus = await readFocusRules();

  return {
    wake: {
      enabled: !!wakeTask,
      time: wakeTime,
      location: sleepPlace
    },
    sleep: {
      enabled: !!sleepTask,
      time: sleepTime,
      location: sleepPlace
    },
    profile: {
      name: userName,
      language: language
    },
    focus
  };
}
```

### 7. apps/desktop/src/onboarding/preload.ts

**変更箇所**: 21行目付近（contextBridge.exposeInMainWorld内）

```typescript
contextBridge.exposeInMainWorld('onboarding', {
  save: (payload: any) => ipcRenderer.invoke('onboarding:save', payload),
  loadSettings: () => ipcRenderer.invoke('onboarding:load-settings'),
  openGoogle: () => ipcRenderer.invoke('onboarding:google-oauth'),
  complete: () => ipcRenderer.invoke('onboarding:complete'),
  close: () => ipcRenderer.invoke('onboarding:close'),
  onShowSettings: (callback: () => void) => {
    ipcRenderer.on('show-settings', callback);
  },
  removeShowSettingsListener: (callback: () => void) => {
    ipcRenderer.removeListener('show-settings', callback);
  },
  onAuthCompleted: (callback: () => void) => {
    ipcRenderer.on('auth-completed', callback);
  },
  removeAuthCompletedListener: (callback: () => void) => {
    ipcRenderer.removeListener('auth-completed', callback);
  },
  focus: {
    start: () => ipcRenderer.invoke('focus:command', { action: 'start' }),
    stop: () => ipcRenderer.invoke('focus:command', { action: 'stop' }),
    status: () => ipcRenderer.invoke('focus:command', { action: 'status' }),
  },
});
```

### 8. apps/desktop/src/services/geminiLiveClient.ts（新規作成）

**完全なファイル内容**:

```typescript
import { GoogleGenAI, Modality } from '@google/genai';
import { API_ENDPOINTS } from '../config';
import { readFocusRules } from './onboardingWriter';
import screenshot from 'screenshot-desktop';
import sharp from 'sharp';

export interface GeminiLiveSession {
  close: () => void;
  sendRealtimeInput: (input: { video?: { data: string; mimeType: string } }) => void;
}

export class GeminiLiveClient {
  private client: GoogleGenAI;
  private session: any = null;
  private isConnected = false;
  private screenCaptureInterval: NodeJS.Timeout | null = null;
  private audioQueue: Float32Array[] = [];

  constructor(token: string) {
    this.client = new GoogleGenAI({ apiKey: token });
  }

  async connect(): Promise<void> {
    if (this.isConnected) return;

    const focusRules = await readFocusRules();
    const systemInstruction = `You are a focus assistant monitoring screen activity. 
When you detect ${focusRules.attentionKeywords.join(', ')}, gently remind the user to stay focused.
When you detect ${focusRules.praiseKeywords.join(', ')}, praise the user for completing tasks.
Speak in a calm, supportive tone.`;

    const responseQueue: any[] = [];

    this.session = await this.client.live.connect({
      model: 'gemini-2.5-flash-native-audio-preview-09-2025',
      config: {
        responseModalities: [Modality.AUDIO],
        systemInstruction: {
          parts: [{ text: systemInstruction }]
        }
      },
      callbacks: {
        onopen: () => {
          console.log('Gemini Live session opened');
          this.isConnected = true;
        },
        onmessage: (message: any) => {
          responseQueue.push(message);
          this.handleServerMessage(message);
        },
        onerror: (e: ErrorEvent) => {
          console.error('Gemini Live session error:', e.message);
        },
        onclose: (e: CloseEvent) => {
          console.log('Gemini Live session closed:', e.reason);
          this.isConnected = false;
        }
      }
    });
  }

  private async handleServerMessage(message: any): Promise<void> {
    if (message.serverContent?.modelTurn?.parts) {
      for (const part of message.serverContent.modelTurn.parts) {
        if (part.inlineData?.mimeType === 'audio/pcm' && part.inlineData.data) {
          const audioData = Buffer.from(part.inlineData.data, 'base64');
          this.audioQueue.push(new Float32Array(audioData.buffer));
        }
      }
    }
  }

  startScreenCapture(intervalMs: number = 2000): void {
    if (this.screenCaptureInterval) return;

    this.screenCaptureInterval = setInterval(async () => {
      try {
        const img = await screenshot();
        const resized = await sharp(img)
          .resize(640, 360, { fit: 'inside' })
          .jpeg({ quality: 80 })
          .toBuffer();
        const base64 = resized.toString('base64');

        if (this.session && this.isConnected) {
          this.session.sendRealtimeInput({
            video: {
              data: base64,
              mimeType: 'image/jpeg'
            }
          });
        }
      } catch (error) {
        console.error('Screen capture error:', error);
      }
    }, intervalMs);
  }

  stopScreenCapture(): void {
    if (this.screenCaptureInterval) {
      clearInterval(this.screenCaptureInterval);
      this.screenCaptureInterval = null;
    }
  }

  getAudioQueue(): Float32Array[] {
    return this.audioQueue.splice(0);
  }

  close(): void {
    this.stopScreenCapture();
    if (this.session) {
      this.session.close();
      this.session = null;
    }
    this.isConnected = false;
  }
}
```

### 9. apps/desktop/src/services/screenShareSession.ts（新規作成）

**完全なファイル内容**:

```typescript
import { GeminiLiveClient } from './geminiLiveClient';
import { API_ENDPOINTS } from '../config';

export class ScreenShareSession {
  private client: GeminiLiveClient | null = null;
  private token: string | null = null;
  private isActive = false;

  async start(userId: string): Promise<void> {
    if (this.isActive) return;

    try {
      const response = await fetch(API_ENDPOINTS.GEMINI.LIVE_TOKEN, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'user-id': userId
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to get token: ${response.status}`);
      }

      const data = await response.json();
      this.token = data.token;

      this.client = new GeminiLiveClient(this.token);
      await this.client.connect();
      this.client.startScreenCapture(2000);
      this.isActive = true;
    } catch (error) {
      console.error('Failed to start screen share session:', error);
      throw error;
    }
  }

  stop(): void {
    if (this.client) {
      this.client.close();
      this.client = null;
    }
    this.isActive = false;
  }

  getAudioQueue(): Float32Array[] {
    return this.client?.getAudioQueue() || [];
  }

  isRunning(): boolean {
    return this.isActive;
  }
}
```

### 10. apps/desktop/src/main-voice-simple.ts

**変更箇所1**: インポートセクション（27行目付近）

```typescript
import { ScreenShareSession } from './services/screenShareSession';
```

**変更箇所2**: グローバル変数セクション（67行目付近）

```typescript
let onboardingFinalMessageSent = false;
let screenShareSession: ScreenShareSession | null = null;
```

**変更箇所3**: setupIpcHandlers関数内（84行目付近、onboarding/window.tsのsetupIpcHandlers関数内）

```typescript
// Focus Watch IPCハンドラ
ipcMain.handle('focus:command', async (_event, { action }: { action: 'start' | 'stop' | 'status' }) => {
  try {
    if (!currentUserId) {
      return { success: false, error: 'User not authenticated' };
    }

    if (action === 'start') {
      if (!screenShareSession) {
        screenShareSession = new ScreenShareSession();
      }
      await screenShareSession.start(currentUserId);
      return { success: true, status: 'started' };
    } else if (action === 'stop') {
      if (screenShareSession) {
        screenShareSession.stop();
        screenShareSession = null;
      }
      return { success: true, status: 'stopped' };
    } else if (action === 'status') {
      return { success: true, status: screenShareSession?.isRunning() ? 'running' : 'stopped' };
    }
    return { success: false, error: 'Invalid action' };
  } catch (error: any) {
    console.error('Focus command error:', error);
    return { success: false, error: error.message };
  }
});
```

## 実装前の確認事項と手動設定

### 1. Railway環境変数設定（必須・手動）

**Railwayの`apps/api`サービスに以下を設定：**

- 変数名: `GEMINI_API_KEY`
- 値: Google AI Studioで取得したGemini APIキー
- 設定場所: Railway Dashboard → `apps/api`サービス → Variablesタブ

**設定手順：**

1. [Google AI Studio](https://aistudio.google.com/apikey)でAPIキーを取得
2. Railway Dashboardにログイン
3. `apps/api`サービスを選択
4. Variablesタブを開く
5. `GEMINI_API_KEY`を追加（値はAPIキー）

### 2. macOS画面キャプチャ権限（必須・手動）

**アプリにScreen Recording権限を付与：**

1. システム設定 → プライバシーとセキュリティ → 画面収録
2. `anicca-agi`（またはアプリ名）にチェックを入れる
3. 初回実行時に権限ダイアログが表示される場合は「許可」を選択

**注意**: `screenshot-desktop`パッケージは既にインストール済みだが、権限がないとエラーになる

### 3. 音声再生の統合方法（実装詳細）

**既存システムとの統合：**

- 既存の`audioQueue`（`main-voice-simple.ts`の`hiddenWindow`内）に統合
- Gemini Live APIからの音声は24kHz PCM（既存システムも24kHz対応済み）
- `screenShareSession.getAudioQueue()`で取得した`Float32Array[]`を既存の`audioQueue`に追加
- 既存の`playNextPCM16Audio()`関数で自動再生される

**実装箇所**: `main-voice-simple.ts`の`createHiddenWindow()`内で、定期的に`screenShareSession.getAudioQueue()`をチェックし、取得した音声を`audioQueue`に追加

### 4. UI実装（既存UIへの追加）

**既存の`onboarding.html`にFocus Watchタブを追加：**

- 設定画面（`settings-screen`）に新しいタブ「Focus Watch」を追加
- 開始/停止ボタンとステータス表示を実装
- `onboarding.focus.start()` / `onboarding.focus.stop()` / `onboarding.focus.status()`を呼び出す

**実装箇所**: `apps/desktop/src/ui/onboarding.html`と`onboarding.js`に追加

### 5. 音声フォーマット変換（確認済み）

**問題なし：**

- Gemini Live API出力: 24kHz PCM（`audio/pcm` MIME type、base64エンコード）
- 既存システム: 24kHz PCM16対応済み（`AUDIO_SAMPLE_RATE = 24000`）
- 変換処理: `geminiLiveClient.ts`でbase64デコード → `Float32Array`に変換済み

### 6. エラーハンドリングの詳細

**トークン取得失敗時：**

- `apps/api/src/routes/gemini/live.js`で`GEMINI_API_KEY`未設定時は500エラー
- `user-id`ヘッダー未設定時は401エラー
- クライアント側（`screenShareSession.ts`）でエラーメッセージをログ出力

**セッション接続失敗時：**

- `geminiLiveClient.ts`の`onerror`コールバックでエラーログ出力
- 再接続は自動で行わない（ユーザーが手動で再試行）

### 7. セッション管理（既存システムとの関係）

**独立したセッション：**

- `ScreenShareSession`は既存の`AniccaSessionManager`（OpenAI Realtime）とは独立
- 同時実行可能（時間ベースのOpenAI Realtime + イベントベースのGemini Live）
- リソース管理: アプリ終了時（`app.on('before-quit')`）に`screenShareSession.stop()`を呼び出す

### 8. 画面キャプチャの実装詳細

**キャプチャ間隔：**

- デフォルト: 2秒間隔（`startScreenCapture(2000)`）
- 解像度: 640x360（`sharp`でリサイズ）
- フォーマット: JPEG（品質80%）
- 送信: base64エンコードして`session.sendRealtimeInput()`で送信

**パフォーマンス考慮：**

- 2秒間隔でCPU負荷は低い
- `sharp`によるリサイズで転送データ量を削減

### 9. 実装時の依存関係インストール

**両方のディレクトリで実行：**

```bash
cd apps/desktop && npm install
cd ../api && npm install
```

**追加されるパッケージ：**

- `@google/genai`: Gemini Live API SDK

### 10. テスト手順（詳細）

1. **Railway設定確認**

   - `GEMINI_API_KEY`が設定されていることを確認
   - Proxyサーバーが起動していることを確認

2. **macOS権限確認**

   - システム設定でScreen Recording権限を確認
   - アプリを再起動して権限ダイアログが表示されることを確認

3. **デスクトップアプリ起動**

   - `npm run voice:simple`で起動
   - 設定画面を開く

4. **Focus Watch開始**

   - 設定画面の「Focus Watch」タブで「開始」ボタンをクリック
   - コンソールログで「Gemini Live session opened」を確認

5. **画面キャプチャ確認**

   - コンソールログで「Screen capture error」が出ないことを確認
   - 2秒間隔でキャプチャが送信されることを確認

6. **音声レスポンス確認**

   - Gemini Live APIから音声が返ることを確認
   - 既存の音声再生システムで再生されることを確認

7. **停止確認**

   - 「停止」ボタンをクリック
   - セッションが終了することを確認