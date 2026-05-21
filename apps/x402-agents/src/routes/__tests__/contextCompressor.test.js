/**
 * Context Compressor x402 Route Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import express from 'express';
import request from 'supertest';

// Mock OpenAI before import
vi.mock('openai', () => {
  const mockCreate = vi.fn();
  return {
    default: vi.fn().mockImplementation(() => ({
      chat: {
        completions: {
          create: mockCreate,
        },
      },
    })),
    __mockCreate: mockCreate,
  };
});

vi.mock('../../lib/prisma.js', () => ({
  prisma: {
    agentAuditLog: {
      create: vi.fn().mockResolvedValue({ id: 'test-id' }),
    },
  },
}));

import OpenAI from 'openai';
import contextCompressorRouter from '../contextCompressor.js';

function getOpenAIMock() {
  return new OpenAI().chat.completions.create;
}

function createApp() {
  const app = express();
  app.use(express.json());
  app.use('/context-compressor', contextCompressorRouter);
  return app;
}

const VALID_SUMMARY_RESULT = {
  compressor_id: 'cmp_a1b2c3d4',
  mode: 'summary',
  compressed: 'A concise summary of the input text.',
  original_chars: 500,
  compressed_chars: 36,
  compression_ratio: 13.89,
  key_entities: ['Alice', 'Bob'],
  safe_t_flag: false,
};

const VALID_FACTS_RESULT = {
  compressor_id: 'cmp_e5f6g7h8',
  mode: 'facts',
  compressed: '- Fact one\n- Fact two\n- Fact three',
  original_chars: 1000,
  compressed_chars: 34,
  compression_ratio: 29.41,
  key_entities: ['Tokyo', '2026'],
  safe_t_flag: false,
};

const VALID_EPISODES_RESULT = {
  compressor_id: 'cmp_i9j0k1l2',
  mode: 'episodes',
  compressed: '[Day 1] Event A happened.\n[Day 2] Event B followed.',
  original_chars: 2000,
  compressed_chars: 52,
  compression_ratio: 38.46,
  key_entities: ['Project X', 'Day 1', 'Day 2'],
  safe_t_flag: false,
};

describe('POST /context-compressor', () => {
  let mockCreate;

  beforeEach(() => {
    vi.clearAllMocks();
    mockCreate = getOpenAIMock();
    mockCreate.mockResolvedValue({
      choices: [{ message: { content: JSON.stringify(VALID_SUMMARY_RESULT) } }],
    });
  });

  it('returns compressed result for valid request', async () => {
    const app = createApp();
    const res = await request(app)
      .post('/context-compressor')
      .send({
        text: 'A'.repeat(500),
        target_tokens: 200,
        mode: 'summary',
        language: 'en',
      });

    expect(res.status).toBe(200);
    expect(res.body.compressor_id).toMatch(/^cmp_/);
    expect(res.body).toHaveProperty('mode');
    expect(res.body).toHaveProperty('compressed');
    expect(typeof res.body.original_chars).toBe('number');
    expect(typeof res.body.compressed_chars).toBe('number');
    expect(typeof res.body.compression_ratio).toBe('number');
    expect(Array.isArray(res.body.key_entities)).toBe(true);
    expect(typeof res.body.safe_t_flag).toBe('boolean');
  });

  it('uses gpt-4o-mini with temperature 0.3', async () => {
    const app = createApp();
    await request(app)
      .post('/context-compressor')
      .send({ text: 'Hello world' });

    expect(mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        model: 'gpt-4o-mini',
        temperature: 0.3,
      })
    );
  });

  it('rejects missing text', async () => {
    const app = createApp();
    const res = await request(app)
      .post('/context-compressor')
      .send({ mode: 'summary', language: 'en' });

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('Invalid request');
  });

  it('rejects text exceeding 50000 characters', async () => {
    const app = createApp();
    const res = await request(app)
      .post('/context-compressor')
      .send({ text: 'a'.repeat(50001) });

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('Invalid request');
  });

  it('rejects target_tokens below 100', async () => {
    const app = createApp();
    const res = await request(app)
      .post('/context-compressor')
      .send({ text: 'Hello world', target_tokens: 50 });

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('Invalid request');
  });

  it('rejects target_tokens above 2000', async () => {
    const app = createApp();
    const res = await request(app)
      .post('/context-compressor')
      .send({ text: 'Hello world', target_tokens: 3000 });

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('Invalid request');
  });

  it('rejects invalid mode', async () => {
    const app = createApp();
    const res = await request(app)
      .post('/context-compressor')
      .send({ text: 'Hello world', mode: 'invalid' });

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('Invalid request');
  });

  it('returns facts mode output correctly', async () => {
    mockCreate.mockResolvedValue({
      choices: [{ message: { content: JSON.stringify(VALID_FACTS_RESULT) } }],
    });

    const app = createApp();
    const res = await request(app)
      .post('/context-compressor')
      .send({ text: 'A'.repeat(1000), mode: 'facts' });

    expect(res.status).toBe(200);
    expect(res.body.mode).toBe('facts');
    expect(res.body.compressed).toContain('Fact');
    expect(res.body.key_entities).toContain('Tokyo');
  });

  it('returns episodes mode output correctly', async () => {
    mockCreate.mockResolvedValue({
      choices: [{ message: { content: JSON.stringify(VALID_EPISODES_RESULT) } }],
    });

    const app = createApp();
    const res = await request(app)
      .post('/context-compressor')
      .send({ text: 'A'.repeat(2000), mode: 'episodes' });

    expect(res.status).toBe(200);
    expect(res.body.mode).toBe('episodes');
    expect(res.body.compressed).toContain('Day 1');
  });

  it('defaults mode to summary and target_tokens to 500', async () => {
    const app = createApp();
    await request(app)
      .post('/context-compressor')
      .send({ text: 'Hello world' });

    const callArgs = mockCreate.mock.calls[0][0];
    const userMessage = callArgs.messages[1].content;
    expect(userMessage).toContain('Mode: summary');
    expect(userMessage).toContain('Target tokens: 500');
  });

  it('returns 500 on OpenAI error', async () => {
    mockCreate.mockRejectedValue(new Error('OpenAI down'));
    const app = createApp();
    const res = await request(app)
      .post('/context-compressor')
      .send({ text: 'Hello', mode: 'summary' });

    expect(res.status).toBe(500);
    expect(res.body.error).toBe('Internal server error');
  });
});
