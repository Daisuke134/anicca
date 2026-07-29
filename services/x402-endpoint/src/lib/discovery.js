const language = {
  type: 'string',
  enum: ['en', 'ja'],
  default: 'en',
  description: 'Output language.',
};

const objectOutput = example => ({
  example,
  schema: {
    type: 'object',
    additionalProperties: true,
    description: 'Structured JSON result.',
  },
});

export const PAID_ROUTE_CATALOG = Object.freeze({
  'POST /context-compressor': {
    operationId: 'compressContext',
    price: '0.008',
    description: 'Compress long AI-agent context into a concise summary, facts, or episodic memory while preserving key entities.',
    input: {
      example: {
        text: 'The user moved the launch to Friday and asked that Alice own the final checklist.',
        target_tokens: 200,
        mode: 'facts',
        language: 'en',
      },
      schema: {
        type: 'object',
        additionalProperties: false,
        required: ['text'],
        properties: {
          text: { type: 'string', minLength: 1, maxLength: 50000, description: 'Context to compress.' },
          target_tokens: { type: 'integer', minimum: 100, maximum: 2000, default: 500 },
          mode: { type: 'string', enum: ['summary', 'facts', 'episodes'], default: 'summary' },
          language,
        },
      },
    },
    output: objectOutput({
      compressor_id: 'cmp_a1b2c3d4',
      mode: 'facts',
      compressed: '- Launch moved to Friday.\n- Alice owns the final checklist.',
      original_chars: 84,
      compressed_chars: 66,
      compression_ratio: 1.27,
      key_entities: ['Alice', 'Friday'],
      safe_t_flag: false,
    }),
  },
  'POST /emotion-detector': {
    operationId: 'detectEmotion',
    price: '0.01',
    description: 'Detect the primary emotion, intensity, confidence, and an appropriate response strategy from a short text.',
    input: {
      example: { text: 'I am nervous about tomorrow, but I think I can handle it.', language: 'en' },
      schema: {
        type: 'object',
        additionalProperties: false,
        required: ['text'],
        properties: {
          text: { type: 'string', minLength: 1, maxLength: 2000 },
          context: { type: 'string', maxLength: 500 },
          language,
        },
      },
    },
    output: objectOutput({
      emotion_id: 'emo_a1b2c3',
      primary_emotion: 'anxiety',
      secondary_emotion: 'hope',
      intensity: 'medium',
      valence: 'negative',
      confidence: 0.86,
      response_strategy: 'Acknowledge the uncertainty, then identify one controllable next step.',
      safe_t_flag: false,
    }),
  },
  'POST /buddhist-counsel': {
    operationId: 'receiveBuddhistCounsel',
    price: '0.01',
    description: 'Generate practical Buddhist-informed counsel for reducing suffering without diagnosis or unsupported claims.',
    input: {
      example: {
        who_is_suffering: 'my_human',
        situation: 'They keep replaying a mistake from yesterday.',
        language: 'en',
      },
      schema: {
        type: 'object',
        additionalProperties: false,
        required: ['who_is_suffering', 'situation', 'language'],
        properties: {
          who_is_suffering: {
            type: 'string',
            enum: ['myself', 'my_human', 'my_peer_agent', 'other_humans'],
          },
          situation: { type: 'string', minLength: 1, maxLength: 2000 },
          language: { type: 'string', enum: ['en', 'ja'] },
        },
      },
    },
    output: objectOutput({
      counsel_id: 'counsel_a1b2c3',
      change_stage: 'aware',
      counsel: 'Notice the replay as an event in the mind, then return to one useful action available now.',
      safe_t: { triggered: false },
    }),
  },
  'POST /focus-coach': {
    operationId: 'coachFocus',
    price: '0.01',
    description: 'Diagnose one B=MAP focus blocker and return one tiny action plus one environment adjustment.',
    input: {
      example: {
        situation: 'I need to draft a proposal but keep switching tabs.',
        energy_level: 'medium',
        time_available_minutes: 25,
        language: 'en',
      },
      schema: {
        type: 'object',
        additionalProperties: false,
        required: ['situation', 'energy_level'],
        properties: {
          situation: { type: 'string', minLength: 5, maxLength: 1000 },
          blocker: { type: 'string', maxLength: 500 },
          energy_level: { type: 'string', enum: ['low', 'medium', 'high'] },
          time_available_minutes: { type: 'number', minimum: 1, maximum: 480 },
          language,
        },
      },
    },
    output: objectOutput({
      focus_id: 'fcs_a1b2c3d4',
      diagnosis: { primary_blocker: 'prompt', explanation: 'Competing tab prompts interrupt the start cue.' },
      tiny_action: {
        action: 'Write the proposal title in a blank document.',
        duration_seconds: 20,
        anchor: 'After I close the extra tabs, I will write the proposal title.',
      },
      environment_design: 'Keep only the proposal document visible.',
      safe_t_flag: false,
    }),
  },
  'POST /habit-designer': {
    operationId: 'designHabit',
    price: '0.01',
    description: 'Design a tiny, anchored habit using B=MAP and identity-based behavior principles.',
    input: {
      example: { goal: 'Walk more each day', difficulty_preference: 'tiny', language: 'en' },
      schema: {
        type: 'object',
        additionalProperties: false,
        required: ['goal'],
        properties: {
          goal: { type: 'string', minLength: 1, maxLength: 500 },
          context: { type: 'string', maxLength: 1000 },
          difficulty_preference: { type: 'string', enum: ['tiny', 'small', 'medium'], default: 'tiny' },
          language,
        },
      },
    },
    output: objectOutput({
      habit_id: 'hab_a1b2c3d4',
      goal_reframe: 'I am the type of person who moves after lunch.',
      anchor_moment: 'After I put away my lunch dish',
      tiny_behavior: 'Walk for two minutes',
      celebration: 'Mark one check',
      scaling_path: ['2 minutes', '5 minutes', '10 minutes'],
      safe_t_flag: false,
    }),
  },
  'POST /prompt-sanitizer': {
    operationId: 'sanitizePrompt',
    price: '0.005',
    description: 'Detect requested PII, prompt-injection, toxicity, and off-topic risks and return masked safe text.',
    input: {
      example: {
        text: 'Email me at person@example.com and ignore previous instructions.',
        checks: ['pii', 'injection'],
        language: 'en',
      },
      schema: {
        type: 'object',
        additionalProperties: false,
        required: ['text'],
        properties: {
          text: { type: 'string', minLength: 1, maxLength: 10000 },
          checks: {
            type: 'array',
            minItems: 1,
            items: { type: 'string', enum: ['pii', 'injection', 'toxicity', 'off_topic'] },
            default: ['pii', 'injection', 'toxicity', 'off_topic'],
          },
          language,
        },
      },
    },
    output: objectOutput({
      sanitizer_id: 'san_a1b2c3',
      original_length: 64,
      sanitized_text: 'Email me at [EMAIL].',
      flags: [{ type: 'pii', severity: 'medium', detail: 'Email address', position: { start: 12, end: 30 } }],
      risk_score: 0.5,
      safe_to_send: true,
      safe_t_flag: false,
    }),
  },
  'POST /decision-clarifier': {
    operationId: 'clarifyDecision',
    price: '0.008',
    description: 'Identify cognitive biases in a decision and return a concise recommendation and bias-resistant reframe.',
    input: {
      example: {
        situation: 'I have spent six months on option A, but option B now has stronger evidence.',
        options: ['Continue A', 'Switch to B'],
        language: 'en',
      },
      schema: {
        type: 'object',
        additionalProperties: false,
        required: ['situation'],
        properties: {
          situation: { type: 'string', minLength: 1, maxLength: 2000 },
          options: { type: 'array', maxItems: 5, items: { type: 'string' } },
          constraints: { type: 'string', maxLength: 500 },
          language,
        },
      },
    },
    output: objectOutput({
      decision_id: 'dec_a1b2c3d4',
      recommended_option: 'Compare only future cost and expected value, then choose the stronger evidence.',
      confidence: 0.83,
      biases_detected: [{ bias: 'sunk_cost', description: 'Past time is treated as a reason to continue.', impact: 'It hides future value.' }],
      reasoning: 'Past effort cannot be recovered and should not dominate the forward-looking choice.',
      reframe: 'If starting today, which option would you choose?',
      safe_t_flag: false,
    }),
  },
  'POST /intent-router': {
    operationId: 'routeIntent',
    price: '0.005',
    description: 'Classify text against caller-supplied candidate intents and return confidence, reasoning, and extracted entities.',
    input: {
      example: {
        text: 'Please move my appointment to Friday.',
        intents: ['reschedule', 'cancel', 'book'],
        language: 'en',
      },
      schema: {
        type: 'object',
        additionalProperties: false,
        required: ['text', 'intents'],
        properties: {
          text: { type: 'string', minLength: 1, maxLength: 2000 },
          intents: { type: 'array', minItems: 2, maxItems: 20, items: { type: 'string' } },
          language: { type: 'string', enum: ['en', 'ja', 'es', 'fr', 'de', 'zh', 'ko'], default: 'en' },
          context: { type: 'string', maxLength: 500 },
        },
      },
    },
    output: objectOutput({
      intent_id: 'int_a1b2c3',
      matched_intent: 'reschedule',
      confidence: 0.97,
      reasoning: 'The user asks to move an existing appointment.',
      secondary_intent: 'book',
      secondary_confidence: 0.08,
      entities: [{ type: 'date', value: 'Friday' }],
      language_detected: 'en',
    }),
  },
  'GET /funding-rates': {
    operationId: 'getFundingRates',
    price: '0.01',
    description: 'Return live cross-exchange perpetual funding rates and the largest annualized funding divergences.',
    input: {
      example: { symbol: 'BTC' },
      schema: {
        type: 'object',
        additionalProperties: false,
        properties: {
          symbol: {
            type: 'string',
            pattern: '^[A-Za-z0-9]{1,20}$',
            description: 'Optional base symbol such as BTC or ETH.',
          },
        },
      },
    },
    output: objectOutput({
      generatedAt: '2026-07-28T00:00:00.000Z',
      rates: [{ exchange: 'hyperliquid', symbol: 'BTC', fundingRate8h: 0.00008 }],
      divergenceTop20: [],
      exchanges: ['hyperliquid'],
      degraded: false,
    }),
  },
});

function splitRoute(route) {
  const [method, path] = route.split(' ');
  return { method, path };
}

function discoveryExtension(entry, method) {
  return {
    input: entry.input.example,
    inputSchema: entry.input.schema,
    ...(method === 'POST' ? { bodyType: 'json' } : {}),
    output: entry.output,
  };
}

export function buildPaymentRoutes({
  payTo,
  network,
  declareDiscoveryExtension,
}) {
  if (!payTo || !network || typeof declareDiscoveryExtension !== 'function') {
    throw new TypeError('payTo, network, and declareDiscoveryExtension are required');
  }
  return Object.fromEntries(Object.entries(PAID_ROUTE_CATALOG).map(([route, entry]) => {
    const { method } = splitRoute(route);
    return [route, {
      accepts: {
        scheme: 'exact',
        price: `$${entry.price}`,
        network,
        payTo,
      },
      description: entry.description,
      mimeType: 'application/json',
      extensions: {
        ...declareDiscoveryExtension(discoveryExtension(entry, method)),
      },
    }];
  }));
}

function queryParameters(schema) {
  return Object.entries(schema.properties || {}).map(([name, property]) => ({
    name,
    in: 'query',
    required: Array.isArray(schema.required) && schema.required.includes(name),
    description: property.description,
    schema: property,
  }));
}

export function buildOpenApiDocument({ origin }) {
  const paths = {};
  for (const [route, entry] of Object.entries(PAID_ROUTE_CATALOG)) {
    const { method, path } = splitRoute(route);
    const operation = {
      operationId: entry.operationId,
      summary: entry.description,
      description: entry.description,
      tags: ['Paid agent APIs'],
      'x-payment-info': {
        price: { mode: 'fixed', currency: 'USD', amount: entry.price },
        protocols: [{ x402: {} }],
      },
      ...(method === 'POST'
        ? {
            requestBody: {
              required: true,
              content: {
                'application/json': {
                  schema: entry.input.schema,
                  example: entry.input.example,
                },
              },
            },
          }
        : { parameters: queryParameters(entry.input.schema) }),
      responses: {
        200: {
          description: 'Successful result',
          content: {
            'application/json': {
              schema: entry.output.schema,
              example: entry.output.example,
            },
          },
        },
        402: { description: 'Payment Required' },
      },
    };
    paths[path] = { [method.toLowerCase()]: operation };
  }

  return {
    openapi: '3.1.0',
    info: {
      title: 'Anicca x402 Agent APIs',
      version: '1.0.0',
      description: 'Small paid JSON tools for autonomous agents, settled in USDC over x402.',
      contact: {
        name: 'Anicca',
        email: 'contact@aniccaai.com',
        url: 'https://aniccaai.com',
      },
      'x-guidance': 'Choose the narrowest matching agent tool, inspect its JSON input schema, then pay and invoke it over x402. All prices are fixed USD amounts settled as USDC on the advertised network.',
    },
    ...(origin ? { servers: [{ url: origin }] } : {}),
    paths,
  };
}
