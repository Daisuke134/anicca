/**
 * Decision Clarifier x402 Route Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import express from 'express';
import request from 'supertest';

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
import decisionClarifierRouter from '../decisionClarifier.js';

function getOpenAIMock() {
  return new OpenAI().chat.completions.create;
}

function createApp() {
  const app = express();
  app.use(express.json());
  app.use('/decision-clarifier', decisionClarifierRouter);
  return app;
}

const VALID_RESULT = {
  decision_id: 'dec_a1b2c3d4',
  recommended_option: 'Switch to the new provider',
  confidence: 0.85,
  biases_detected: [
    {
      bias: 'sunk_cost',
      description: 'Reluctance to switch due to 3 years invested in current provider',
      impact: 'Overvaluing past investment instead of evaluating future value',
    },
    {
      bias: 'status_quo',
      description: 'Preference for staying with current provider despite inferior service',
      impact: 'Missing better alternatives due to comfort with current state',
    },
  ],
  reasoning: 'The new provider offers better features at lower cost. The 3 years spent with the current provider are sunk costs and should not factor into the decision.',
  reframe: 'If you were choosing a provider today with no history, which would you pick based purely on current value?',
  safe_t_flag: false,
};

const CRISIS_RESULT = {
  decision_id: 'dec_crisis1',
  recommended_option: 'Please reach out to a crisis helpline immediately',
  confidence: 0.95,
  biases_detected: [],
  reasoning: 'This situation involves potential self-harm and requires immediate professional support.',
  reframe: 'Your life has value and professional help is available right now.',
  safe_t_flag: true,
};

describe('POST /decision-clarifier', () => {
  let mockCreate;

  beforeEach(() => {
    vi.clearAllMocks();
    mockCreate = getOpenAIMock();
    mockCreate.mockResolvedValue({
      choices: [{ message: { content: JSON.stringify(VALID_RESULT) } }],
    });
  });

  it('returns decision analysis for valid request', async () => {
    const app = createApp();
    const res = await request(app)
      .post('/decision-clarifier')
      .send({
        situation: 'I have been with my current cloud provider for 3 years but a new one offers better features at half the price.',
        options: ['Stay with current provider', 'Switch to new provider'],
        language: 'en',
      });

    expect(res.status).toBe(200);
    expect(res.body.decision_id).toMatch(/^dec_/);
    expect(res.body).toHaveProperty('recommended_option');
    expect(typeof res.body.confidence).toBe('number');
    expect(res.body.confidence).toBeGreaterThanOrEqual(0);
    expect(res.body.confidence).toBeLessThanOrEqual(1);
    expect(Array.isArray(res.body.biases_detected)).toBe(true);
    expect(res.body).toHaveProperty('reasoning');
    expect(res.body).toHaveProperty('reframe');
    expect(typeof res.body.safe_t_flag).toBe('boolean');
  });

  it('uses gpt-4o-mini with temperature 0.3', async () => {
    const app = createApp();
    await request(app)
      .post('/decision-clarifier')
      .send({ situation: 'Should I change jobs?' });

    expect(mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        model: 'gpt-4o-mini',
        temperature: 0.3,
      })
    );
  });

  it('rejects missing situation', async () => {
    const app = createApp();
    const res = await request(app)
      .post('/decision-clarifier')
      .send({ options: ['A', 'B'], language: 'en' });

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('Invalid request');
  });

  it('rejects situation exceeding 2000 characters', async () => {
    const app = createApp();
    const res = await request(app)
      .post('/decision-clarifier')
      .send({ situation: 'a'.repeat(2001) });

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('Invalid request');
  });

  it('rejects more than 5 options', async () => {
    const app = createApp();
    const res = await request(app)
      .post('/decision-clarifier')
      .send({
        situation: 'Which one?',
        options: ['A', 'B', 'C', 'D', 'E', 'F'],
      });

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('Invalid request');
  });

  it('rejects constraints exceeding 500 characters', async () => {
    const app = createApp();
    const res = await request(app)
      .post('/decision-clarifier')
      .send({
        situation: 'Should I move?',
        constraints: 'x'.repeat(501),
      });

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('Invalid request');
  });

  it('works without optional fields', async () => {
    const app = createApp();
    const res = await request(app)
      .post('/decision-clarifier')
      .send({ situation: 'Should I change jobs?' });

    expect(res.status).toBe(200);
    expect(res.body.decision_id).toMatch(/^dec_/);
  });

  it('detects biases correctly in output', async () => {
    const app = createApp();
    const res = await request(app)
      .post('/decision-clarifier')
      .send({
        situation: 'I spent 3 years on this project, I cannot quit now.',
        options: ['Continue', 'Stop'],
      });

    expect(res.status).toBe(200);
    expect(res.body.biases_detected.length).toBeGreaterThan(0);
    expect(res.body.biases_detected[0]).toHaveProperty('bias');
    expect(res.body.biases_detected[0]).toHaveProperty('description');
    expect(res.body.biases_detected[0]).toHaveProperty('impact');
  });

  it('sets safe_t_flag for crisis situations', async () => {
    mockCreate.mockResolvedValue({
      choices: [{ message: { content: JSON.stringify(CRISIS_RESULT) } }],
    });

    const app = createApp();
    const res = await request(app)
      .post('/decision-clarifier')
      .send({ situation: 'I am thinking about ending it all.' });

    expect(res.status).toBe(200);
    expect(res.body.safe_t_flag).toBe(true);
  });

  it('includes options and constraints in user message', async () => {
    const app = createApp();
    await request(app)
      .post('/decision-clarifier')
      .send({
        situation: 'Which job?',
        options: ['Job A', 'Job B'],
        constraints: 'Must be remote',
        language: 'ja',
      });

    const callArgs = mockCreate.mock.calls[0][0];
    const userMessage = callArgs.messages[1].content;
    expect(userMessage).toContain('Which job?');
    expect(userMessage).toContain('Job A');
    expect(userMessage).toContain('Job B');
    expect(userMessage).toContain('Must be remote');
    expect(userMessage).toContain('ja');
  });

  it('returns 500 on OpenAI error', async () => {
    mockCreate.mockRejectedValue(new Error('OpenAI down'));
    const app = createApp();
    const res = await request(app)
      .post('/decision-clarifier')
      .send({ situation: 'Should I switch?' });

    expect(res.status).toBe(500);
    expect(res.body.error).toBe('Internal server error');
  });
});
