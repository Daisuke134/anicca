# Contract: x402 Endpoint Template

**Type**: Railway Express route (ESM)
**Pattern**: buddhist-counsel verbatim（FR-003）

---

## ファイル構成（新スキル追加時）

### 1. ハンドラファイル（新規作成）

**Path**: `apps/api/src/routes/x402/<skillName>.js`

```javascript
// Template: apps/api/src/routes/x402/<skillName>.js
import { Router } from 'express';
import OpenAI from 'openai';

const router = Router();
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

// SYSTEM PROMPT: スキル固有（ここだけカスタマイズ）
const SYSTEM_PROMPT = `<skill-specific system prompt here>`;

router.post('/', async (req, res) => {
  try {
    const { /* skill-specific inputs */ } = req.body;

    const completion = await openai.chat.completions.create({
      model: 'gpt-4o',
      messages: [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user', content: JSON.stringify(req.body) }
      ],
      response_format: { type: 'json_object' }
    });

    const result = JSON.parse(completion.choices[0].message.content);
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

export default router;
```

### 2. index.js 追加エントリ（差分のみ）

**Path**: `apps/api/src/routes/x402/index.js`（既存ファイルに追記）

```javascript
// 追加: paymentMiddleware の routes オブジェクトに追加
'POST /<skill_name>': {
  accepts: {
    scheme: 'exact',
    price: '$0.01',
    network,
    payTo: PAY_TO,
  },
  description: '<skill description>',
  mimeType: 'application/json',
  extensions: {
    ...declareDiscoveryExtension({
      output: {
        example: { /* skill-specific example */ },
        schema: {
          properties: { /* skill-specific schema */ }
        }
      }
    })
  }
},

// 追加: router.use に追加
import <skillName>Router from './<skillName>.js';
router.use('/<skill_name>', <skillName>Router);
```

---

## 不変条件（新スキル追加時に必ず守ること）

| Rule | Detail |
|------|--------|
| middleware 順序 | CORS → express.json → paymentMiddleware（固定） |
| scheme | `"exact"` 固定 |
| price | `"$0.01"` 固定 |
| facilitator | `isMainnet ? cdpFacilitator : x402.org/facilitator` |
| syncFacilitatorOnStart | `false`（HTTPFacilitatorClient 使用のため不要） |
| response format | `application/json` |
| model | `gpt-4o` |

---

## テスト方法（awal）

```bash
# testnet（staging）
npx awal@2.0.3 x402 pay https://anicca-proxy-staging.up.railway.app/api/x402/<skill_name> \
  -X POST \
  -d '{"<input_key>": "<input_value>"}'

# 期待結果: HTTP 200 OK + JSON レスポンス
# 失敗（非200）: ClawHub publish を絶対に実行しない
```
