# life-manager 無音/robotic-error call — Postmortem & Fix

- Date: 2026-06-04 / 方法: superpowers:systematic-debugging

## 症状
Anicca が電話してきたが、Charon(男声)でなく機械的女声「We're sorry, an application error has occurred. Goodbye」で切断。別の回では無音(誰も喋らない)。位置追跡(Telegram)・発信(Twilio)は正常。

## Root Cause（Phase 1-3・再現済）
pipecat-phone log:
```
Twilio stream connected — Anicca starting the wake-up call   ← 発信/bridge接続OK
ERROR GeminiLiveLLMService _connect ... 1008 ... Lightning dunning decision is deny for project: projects/650019441095
```
Gemini API を直接叩いて再現:
- GOOGLE_API_KEY → 403 API_KEY_SERVICE_BLOCKED
- GEMINI_API_KEY → 403 "Lightning dunning decision is deny for project: 650019441095"
- 別project 727660390518 の鍵も同 403 dunning

→ **Google Cloud 課金口座 017949-09509F-6A3FB6 が dunning(支払い滞納/カード拒否)で全Gemin鍵がブロック** → Gemini Live 接続不可 → Charon が喋れない → Twilio が既定 error TwiML(機械女声) を流して切断。**コードバグでなく課金問題。** 女声=Twilioデフォルト(Geminiが一度も繋がっていない証拠)。

## Fix
2層:
1. **真の修正(ユーザー行動)**: Google Cloud 課金口座 017949-09509F-6A3FB6 の支払いを解消(declined card 再登録/未払い精算) or funded な別口座の GEMINI_API_KEY に差替。これで Charon 復活。
2. **コード堅牢化(済・b5e66db)**: `place_lateness_call` に発信前 `gemini_reachable()` health gate。Gemini が 403/到達不可なら**壊れた robotic-error call を出さず Slack 警告**(原因+対処を明記)。anicca-oss + ~/.openclaw 両方に適用・検証済(現状 dunning で正しく skip)。誰にも「無言/エラー音声 call」を体験させない。

## 問題はどう変わったか
- Before: Gemini 死 → 毎回 robotic「application error」or 無音 call（原因不明・サイレント）。
- After(コード): Gemini 死 → call せず Slack に「Gemini unreachable: <理由> / 課金を直せ」即通知。壊れた call ゼロ。
- 完全復旧(Anicca が Charon で会話): 課金解消 待ち(ユーザー行動)。解消後は gate が通り通常 call。
