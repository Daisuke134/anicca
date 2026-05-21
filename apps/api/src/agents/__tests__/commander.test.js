import { describe, it, expect } from 'vitest';
import { 
  applyGuardrails, 
  normalizeToDecision, 
  AgentRawOutputSchema,
  validateAppNudgesSlotIndexes,
  estimateMaxTokens,
  MODEL_MAX_TOKENS,
  MAX_SLOTS_PER_DAY,
  runCommanderAgent,
  validateNoDuplicates,
} from '../commander.js';

// ===== Test fixtures =====

function makeSlotTable() {
  return [
    { slotIndex: 0, problemType: 'procrastination', scheduledTime: '09:00', scheduledHour: 9, scheduledMinute: 0 },
    { slotIndex: 1, problemType: 'procrastination', scheduledTime: '09:15', scheduledHour: 9, scheduledMinute: 15 },
    { slotIndex: 2, problemType: 'procrastination', scheduledTime: '11:00', scheduledHour: 11, scheduledMinute: 0 },
    { slotIndex: 3, problemType: 'anxiety', scheduledTime: '14:00', scheduledHour: 14, scheduledMinute: 0 },
    { slotIndex: 4, problemType: 'anxiety', scheduledTime: '23:30', scheduledHour: 23, scheduledMinute: 30 },
    { slotIndex: 5, problemType: 'staying_up_late', scheduledTime: '23:00', scheduledHour: 23, scheduledMinute: 0 },
    { slotIndex: 6, problemType: 'staying_up_late', scheduledTime: '00:00', scheduledHour: 0, scheduledMinute: 0 },
  ];
}

function makeNudges() {
  return [
    { slotIndex: 0, hook: 'h0', content: 'c0', tone: 'strict', enabled: true, reasoning: 'r0' },
    { slotIndex: 1, hook: 'h1', content: 'c1', tone: 'gentle', enabled: true, reasoning: 'r1' },
    { slotIndex: 2, hook: 'h2', content: 'c2', tone: 'playful', enabled: true, reasoning: 'r2' },
    { slotIndex: 3, hook: 'h3', content: 'c3', tone: 'analytical', enabled: true, reasoning: 'r3' },
    { slotIndex: 4, hook: 'h4', content: 'c4', tone: 'empathetic', enabled: true, reasoning: 'r4' },
    { slotIndex: 5, hook: 'h5', content: 'c5', tone: 'strict', enabled: true, reasoning: 'r5' },
    { slotIndex: 6, hook: 'h6', content: 'c6', tone: 'gentle', enabled: true, reasoning: 'r6' },
  ];
}

// ===== AgentRawOutputSchema =====

describe('AgentRawOutputSchema', () => {
  it('validates valid output (without enabled in appNudges)', () => {
    const valid = {
      rootCauseHypothesis: 'test',
      overallStrategy: 'test strategy',
      frequencyReasoning: 'test reasoning',
      appNudges: [
        { slotIndex: 0, hook: 'h', content: 'c', tone: 'strict', reasoning: 'r' },
      ],
      tiktokPosts: [
        { slot: 'morning', caption: 'c1', hashtags: ['#test'], tone: 't', reasoning: 'r', enabled: true },
        { slot: 'evening', caption: 'c2', hashtags: ['#test'], tone: 't', reasoning: 'r', enabled: true },
      ],
      xPosts: [
        { slot: 'morning', text: 'tweet1', reasoning: 'r', enabled: true },
        { slot: 'evening', text: 'tweet2', reasoning: 'r', enabled: true },
      ],
    };
    expect(() => AgentRawOutputSchema.parse(valid)).not.toThrow();
  });

  it('rejects invalid tone', () => {
    const invalid = {
      rootCauseHypothesis: 'test',
      overallStrategy: 'test',
      frequencyReasoning: 'test',
      appNudges: [
        { slotIndex: 0, hook: 'h', content: 'c', tone: 'aggressive', reasoning: 'r' },
      ],
    };
    expect(() => AgentRawOutputSchema.parse(invalid)).toThrow();
  });

  it('validates required tiktokPosts and xPosts (2 each)', () => {
    const withPosts = {
      rootCauseHypothesis: 'test',
      overallStrategy: 'test',
      frequencyReasoning: 'test',
      appNudges: [],  // LLM output has no enabled field in appNudges
      tiktokPosts: [
        { slot: 'morning', caption: 'c1', hashtags: ['#anicca'], tone: 't', reasoning: 'r', enabled: true },
        { slot: 'evening', caption: 'c2', hashtags: ['#test'], tone: 't', reasoning: 'r', enabled: true },
      ],
      xPosts: [
        { slot: 'morning', text: 'tweet1', reasoning: 'r', enabled: true },
        { slot: 'evening', text: 'tweet2', reasoning: 'r', enabled: true },
      ],
    };
    expect(() => AgentRawOutputSchema.parse(withPosts)).not.toThrow();
  });

  it('rejects missing tiktokPosts/xPosts or invalid slots', () => {
    const invalid = {
      rootCauseHypothesis: 'test',
      overallStrategy: 'test',
      frequencyReasoning: 'test',
      appNudges: [],
      tiktokPosts: [{ slot: 'morning', caption: 'c', hashtags: [], tone: 't', reasoning: 'r', enabled: true }],
      xPosts: [{ slot: 'noon', text: 'tweet', reasoning: 'r', enabled: true }],
    };
    expect(() => AgentRawOutputSchema.parse(invalid)).toThrow();
  });

  it('rejects overly long TikTok captions (B2)', () => {
    const tooLong = {
      rootCauseHypothesis: 'test',
      overallStrategy: 'test',
      frequencyReasoning: 'test',
      appNudges: [],
      tiktokPosts: [
        { slot: 'morning', caption: 'a'.repeat(2001), hashtags: [], tone: 't', reasoning: 'r', enabled: true },
        { slot: 'evening', caption: 'ok', hashtags: [], tone: 't', reasoning: 'r', enabled: true },
      ],
      xPosts: [
        { slot: 'morning', text: 'tweet1', reasoning: 'r', enabled: true },
        { slot: 'evening', text: 'tweet2', reasoning: 'r', enabled: true },
      ],
    };
    expect(() => AgentRawOutputSchema.parse(tooLong)).toThrow();
  });

  it('rejects overly long X texts (B2)', () => {
    const tooLong = {
      rootCauseHypothesis: 'test',
      overallStrategy: 'test',
      frequencyReasoning: 'test',
      appNudges: [],
      tiktokPosts: [
        { slot: 'morning', caption: 'ok', hashtags: [], tone: 't', reasoning: 'r', enabled: true },
        { slot: 'evening', caption: 'ok', hashtags: [], tone: 't', reasoning: 'r', enabled: true },
      ],
      xPosts: [
        { slot: 'morning', text: 'a'.repeat(261), reasoning: 'r', enabled: true },
        { slot: 'evening', text: 'tweet2', reasoning: 'r', enabled: true },
      ],
    };
    expect(() => AgentRawOutputSchema.parse(tooLong)).toThrow();
  });
});

// ===== applyGuardrails =====

describe('applyGuardrails', () => {
  it('warns but does NOT disable non-exempt problems in night hours (23:00-05:59)', () => {
    const slotTable = makeSlotTable();
    const nudges = makeNudges();

    const result = applyGuardrails(nudges, slotTable);

    // anxiety at 23:30 should remain ENABLED (warning only, user wants all nudges delivered)
    const anxietyNight = result.find(n => n.slotIndex === 4);
    expect(anxietyNight.enabled).toBe(true);
    expect(anxietyNight.reasoning).toContain('warning: night curfew zone');
  });

  it('keeps exempt problems enabled at night', () => {
    const slotTable = makeSlotTable();
    const nudges = makeNudges();

    const result = applyGuardrails(nudges, slotTable);

    // staying_up_late at 23:00 and 00:00 should remain enabled
    const sulNight = result.find(n => n.slotIndex === 5);
    expect(sulNight.enabled).toBe(true);
    const sulMidnight = result.find(n => n.slotIndex === 6);
    expect(sulMidnight.enabled).toBe(true);
  });

  it('warns but does NOT disable same-problem slots <30min apart', () => {
    const slotTable = makeSlotTable();
    const nudges = makeNudges();

    const result = applyGuardrails(nudges, slotTable);

    // procrastination: 09:00 (enabled), 09:15 (<30min, warning but ENABLED), 11:00 (enabled)
    // User wants all nudges delivered - warning only
    expect(result.find(n => n.slotIndex === 0).enabled).toBe(true);
    expect(result.find(n => n.slotIndex === 1).enabled).toBe(true);
    expect(result.find(n => n.slotIndex === 1).reasoning).toContain('warning: <30min interval');
    expect(result.find(n => n.slotIndex === 2).enabled).toBe(true);
  });

  it('keeps non-exempt problems enabled at night (warning only, no disable)', () => {
    const slotTable = [
      { slotIndex: 0, problemType: 'anxiety', scheduledTime: '23:30', scheduledHour: 23, scheduledMinute: 30 },
    ];
    const nudges = [
      { slotIndex: 0, hook: 'h', content: 'c', tone: 'strict', enabled: true, reasoning: 'r' },
    ];

    const result = applyGuardrails(nudges, slotTable);

    // anxiety (non-exempt) at 23:30 stays ENABLED — user wants all nudges delivered
    expect(result[0].enabled).toBe(true);
    expect(result[0].reasoning).toContain('warning: night curfew zone');
  });

  it('re-enables exempt problems at night for min-1 rule', () => {
    const slotTable = [
      { slotIndex: 0, problemType: 'staying_up_late', scheduledTime: '23:30', scheduledHour: 23, scheduledMinute: 30 },
    ];
    const nudges = [
      { slotIndex: 0, hook: 'h', content: 'c', tone: 'strict', enabled: false, reasoning: 'r' },
    ];

    const result = applyGuardrails(nudges, slotTable);

    // staying_up_late (exempt) should be re-enabled by min-1 rule
    expect(result[0].enabled).toBe(true);
    expect(result[0].reasoning).toContain('re-enabled');
  });

  it('caps at 32 enabled nudges', () => {
    const slotTable = [];
    const nudges = [];
    for (let i = 0; i < 35; i++) {
      slotTable.push({ slotIndex: i, problemType: 'procrastination', scheduledTime: `${String(7 + Math.floor(i / 2)).padStart(2, '0')}:${i % 2 === 0 ? '00' : '30'}`, scheduledHour: 7 + Math.floor(i / 2), scheduledMinute: i % 2 === 0 ? 0 : 30 });
      nudges.push({ slotIndex: i, hook: `h${i}`, content: `c${i}`, tone: 'strict', enabled: true, reasoning: `r${i}` });
    }

    const result = applyGuardrails(nudges, slotTable);
    const enabledCount = result.filter(n => n.enabled).length;
    expect(enabledCount).toBeLessThanOrEqual(32);
  });

  it('does not mutate input', () => {
    const slotTable = makeSlotTable();
    const nudges = makeNudges();
    const originalNudges = nudges.map(n => ({ ...n }));

    applyGuardrails(nudges, slotTable);

    for (let i = 0; i < nudges.length; i++) {
      expect(nudges[i]).toEqual(originalNudges[i]);
    }
  });
});

// ===== normalizeToDecision =====

describe('normalizeToDecision', () => {
  it('enriches nudges with slot metadata and sets enabled=true by default', () => {
    const agentOutput = {
      rootCauseHypothesis: 'hypothesis',
      overallStrategy: 'strategy',
      frequencyReasoning: 'freq reasoning',
      appNudges: [
        { slotIndex: 0, hook: 'h', content: 'c', tone: 'strict', reasoning: 'r' },  // no enabled (LLM output)
      ],
      tiktokPosts: [
        { slot: 'morning', caption: 'c1', hashtags: [], tone: 't', reasoning: 'r', enabled: true },
        { slot: 'evening', caption: 'c2', hashtags: [], tone: 't', reasoning: 'r', enabled: true },
      ],
      xPosts: [
        { slot: 'morning', text: 't1', reasoning: 'r', enabled: true },
        { slot: 'evening', text: 't2', reasoning: 'r', enabled: true },
      ],
    };
    const slotTable = [
      { slotIndex: 0, problemType: 'procrastination', scheduledTime: '09:00', scheduledHour: 9, scheduledMinute: 0 },
    ];

    const decision = normalizeToDecision(agentOutput, slotTable, 'user-123');

    expect(decision.userId).toBe('user-123');
    expect(decision.appNudges[0].problemType).toBe('procrastination');
    expect(decision.appNudges[0].scheduledTime).toBe('09:00');
    expect(decision.appNudges[0].scheduledHour).toBe(9);
    expect(decision.appNudges[0].scheduledMinute).toBe(0);
    expect(decision.appNudges[0].enabled).toBe(true);  // Default enabled=true
  });

  it('counts enabled nudges in frequencyDecision (all enabled by default)', () => {
    // LLM output doesn't include enabled field - normalizeToDecision sets enabled=true by default
    const agentOutput = {
      rootCauseHypothesis: 'h',
      overallStrategy: 's',
      frequencyReasoning: 'f',
      appNudges: [
        { slotIndex: 0, hook: 'h', content: 'c', tone: 'strict', reasoning: 'r' },  // no enabled
        { slotIndex: 1, hook: 'h', content: 'c', tone: 'gentle', reasoning: 'r' },  // no enabled
        { slotIndex: 2, hook: 'h', content: 'c', tone: 'playful', reasoning: 'r' }, // no enabled
      ],
      tiktokPosts: [
        { slot: 'morning', caption: 'c1', hashtags: [], tone: 't', reasoning: 'r', enabled: true },
        { slot: 'evening', caption: 'c2', hashtags: [], tone: 't', reasoning: 'r', enabled: true },
      ],
      xPosts: [
        { slot: 'morning', text: 't1', reasoning: 'r', enabled: true },
        { slot: 'evening', text: 't2', reasoning: 'r', enabled: true },
      ],
    };
    const slotTable = [
      { slotIndex: 0, problemType: 'p', scheduledTime: '09:00', scheduledHour: 9, scheduledMinute: 0 },
      { slotIndex: 1, problemType: 'p', scheduledTime: '11:00', scheduledHour: 11, scheduledMinute: 0 },
      { slotIndex: 2, problemType: 'p', scheduledTime: '13:00', scheduledHour: 13, scheduledMinute: 0 },
    ];

    const decision = normalizeToDecision(agentOutput, slotTable, 'u');

    // All 3 slots enabled by default (all >30min apart, daytime, same problem)
    expect(decision.frequencyDecision.count).toBe(3);
    expect(decision.frequencyDecision.reasoning).toBe('f');
    expect(decision.tiktokPosts.length).toBe(2);
    expect(decision.xPosts.length).toBe(2);
  });

  it('filters out nudges with invalid slotIndex', () => {
    const agentOutput = {
      rootCauseHypothesis: 'h',
      overallStrategy: 's',
      frequencyReasoning: 'f',
      appNudges: [
        { slotIndex: 0, hook: 'valid', content: 'c', tone: 'strict', reasoning: 'r' },  // no enabled
        { slotIndex: 999, hook: 'invalid', content: 'c', tone: 'strict', reasoning: 'r' },
      ],
    };
    const slotTable = [
      { slotIndex: 0, problemType: 'procrastination', scheduledTime: '09:00', scheduledHour: 9, scheduledMinute: 0 },
    ];

    const decision = normalizeToDecision(agentOutput, slotTable, 'u');

    expect(decision.appNudges.length).toBe(1);
    expect(decision.appNudges[0].hook).toBe('valid');
  });

  it('fills missing slots with enabled=true by default, guardrails may disable', () => {
    const agentOutput = {
      rootCauseHypothesis: 'h',
      overallStrategy: 's',
      frequencyReasoning: 'f',
      appNudges: [
        { slotIndex: 0, hook: 'h0', content: 'c0', tone: 'strict', reasoning: 'r0' },  // no enabled (LLM output)
      ],
    };
    const slotTable = [
      { slotIndex: 0, problemType: 'procrastination', scheduledTime: '09:00', scheduledHour: 9, scheduledMinute: 0 },
      { slotIndex: 1, problemType: 'procrastination', scheduledTime: '11:00', scheduledHour: 11, scheduledMinute: 0 },
      { slotIndex: 2, problemType: 'anxiety', scheduledTime: '14:00', scheduledHour: 14, scheduledMinute: 0 },
    ];

    const decision = normalizeToDecision(agentOutput, slotTable, 'u');

    expect(decision.appNudges.length).toBe(3);
    // Slot 0: LLM output, enabled=true by default
    expect(decision.appNudges[0].enabled).toBe(true);
    expect(decision.appNudges[0].hook).toBe('h0');
    // Slot 1: Missing, filled with fallback (enabled=true), >30min from slot 0, so stays enabled
    expect(decision.appNudges[1].enabled).toBe(true);
    expect(decision.appNudges[1].problemType).toBe('procrastination');
    // Slot 2: Missing, filled with fallback (enabled=true), daytime anxiety
    expect(decision.appNudges[2].enabled).toBe(true);
    expect(decision.appNudges[2].problemType).toBe('anxiety');
  });

  it('preserves rootCauseHypothesis in decision', () => {
    const agentOutput = {
      rootCauseHypothesis: 'deep cause',
      overallStrategy: 'strategy',
      frequencyReasoning: 'f',
      appNudges: [],
    };

    const decision = normalizeToDecision(agentOutput, [], 'u');

    expect(decision.rootCauseHypothesis).toBe('deep cause');
  });

  it('preserves tiktokPosts array in decision (#13)', () => {
    const agentOutput = {
      rootCauseHypothesis: 'h',
      overallStrategy: 's',
      frequencyReasoning: 'f',
      appNudges: [],  // no appNudges
      tiktokPosts: [
        { slot: 'morning', caption: 'cap1', hashtags: [], tone: 't', reasoning: 'r', enabled: true },
        { slot: 'evening', caption: 'cap2', hashtags: [], tone: 't', reasoning: 'r', enabled: true },
      ],
      xPosts: [
        { slot: 'morning', text: 'tweet1', reasoning: 'r', enabled: true },
        { slot: 'evening', text: 'tweet2', reasoning: 'r', enabled: true },
      ],
    };

    const decision = normalizeToDecision(agentOutput, [], 'u');

    expect(decision.tiktokPosts).toHaveLength(2);
    expect(decision.tiktokPosts[0].slot).toBe('morning');
    expect(decision.tiktokPosts[1].slot).toBe('evening');
    expect(decision.xPosts).toHaveLength(2);
    expect(decision.xPosts[0].text).toBe('tweet1');
  });
});

// ===== Additional Schema Tests (spec #18, #19, #20, #23) =====

describe('AgentRawOutputSchema - additional', () => {
  it('requires two xPosts (#19)', () => {
    const withOneXPost = {
      rootCauseHypothesis: 'test',
      overallStrategy: 'test',
      frequencyReasoning: 'test',
      appNudges: [],
      tiktokPosts: [
        { slot: 'morning', caption: 'c1', hashtags: [], tone: 't', reasoning: 'r', enabled: true },
        { slot: 'evening', caption: 'c2', hashtags: [], tone: 't', reasoning: 'r', enabled: true },
      ],
      xPosts: [{ slot: 'morning', text: 'tweet1', reasoning: 'r', enabled: true }],
    };
    expect(() => AgentRawOutputSchema.parse(withOneXPost)).toThrow();
  });

  // Note: The Zod schema allows duplicate slots (length=2 only).
  // Slot uniqueness is validated by validateSlotUniqueness() post-parse.
  // These tests verify that schema parsing passes but post-parse validation catches duplicates.
  it('schema accepts duplicate xPosts slots but validateSlotUniqueness rejects (#20)', async () => {
    const { validateSlotUniqueness } = await import('../commander.js');
    const duplicateMorning = {
      rootCauseHypothesis: 'test',
      overallStrategy: 'test',
      frequencyReasoning: 'test',
      appNudges: [],
      tiktokPosts: [
        { slot: 'morning', caption: 'c1', hashtags: [], tone: 't', reasoning: 'r', enabled: true },
        { slot: 'evening', caption: 'c2', hashtags: [], tone: 't', reasoning: 'r', enabled: true },
      ],
      xPosts: [
        { slot: 'morning', text: 'tweet1', reasoning: 'r', enabled: true },
        { slot: 'morning', text: 'tweet2', reasoning: 'r', enabled: true },
      ],
    };
    // Schema parsing passes (only checks length=2)
    const parsed = AgentRawOutputSchema.parse(duplicateMorning);
    // But post-parse validation should fail
    expect(() => validateSlotUniqueness(parsed)).toThrow();
  });

  it('schema accepts duplicate tiktokPosts slots but validateSlotUniqueness rejects (#23)', async () => {
    const { validateSlotUniqueness } = await import('../commander.js');
    const duplicateEvening = {
      rootCauseHypothesis: 'test',
      overallStrategy: 'test',
      frequencyReasoning: 'test',
      appNudges: [],
      tiktokPosts: [
        { slot: 'evening', caption: 'c1', hashtags: [], tone: 't', reasoning: 'r', enabled: true },
        { slot: 'evening', caption: 'c2', hashtags: [], tone: 't', reasoning: 'r', enabled: true },
      ],
      xPosts: [
        { slot: 'morning', text: 'tweet1', reasoning: 'r', enabled: true },
        { slot: 'evening', text: 'tweet2', reasoning: 'r', enabled: true },
      ],
    };
    // Schema parsing passes (only checks length=2)
    const parsed = AgentRawOutputSchema.parse(duplicateEvening);
    // But post-parse validation should fail
    expect(() => validateSlotUniqueness(parsed)).toThrow();
  });
});

// ===== Prompt Test (#18) =====

describe('buildCommanderPrompt', () => {
  // buildCommanderPrompt is not exported, so we test via the prompt content
  // included in commander.js source. We verify the schema/prompt expectations
  // by checking that the module's SYSTEM_PROMPT or buildCommanderPrompt output
  // includes the morning/evening table.
  // Since buildCommanderPrompt is internal, we test indirectly via normalizeToDecision
  // ensuring the schema enforces the morning/evening structure.
  it('schema enforces morning/evening structure matching prompt table (#18)', () => {
    // The prompt includes a table with morning/evening slots.
    // We verify the schema enforces this constraint.
    const valid = {
      rootCauseHypothesis: 'test',
      overallStrategy: 'test',
      frequencyReasoning: 'test',
      appNudges: [],
      tiktokPosts: [
        { slot: 'morning', caption: 'c1', hashtags: [], tone: 't', reasoning: 'r', enabled: true },
        { slot: 'evening', caption: 'c2', hashtags: [], tone: 't', reasoning: 'r', enabled: true },
      ],
      xPosts: [
        { slot: 'morning', text: 't1', reasoning: 'r', enabled: true },
        { slot: 'evening', text: 't2', reasoning: 'r', enabled: true },
      ],
    };
    const result = AgentRawOutputSchema.parse(valid);
    expect(result.tiktokPosts[0].slot).toBe('morning');
    expect(result.tiktokPosts[1].slot).toBe('evening');
    expect(result.xPosts[0].slot).toBe('morning');
    expect(result.xPosts[1].slot).toBe('evening');
  });
});

// ===== validateAppNudgesSlotIndexes =====

describe('validateAppNudgesSlotIndexes', () => {
  it('passes for valid sequential slotIndexes', () => {
    const appNudges = [
      { slotIndex: 0, hook: 'h', content: 'c', tone: 't', enabled: true, reasoning: 'r' },
      { slotIndex: 1, hook: 'h', content: 'c', tone: 't', enabled: true, reasoning: 'r' },
      { slotIndex: 2, hook: 'h', content: 'c', tone: 't', enabled: true, reasoning: 'r' },
    ];
    expect(() => validateAppNudgesSlotIndexes(appNudges, 3)).not.toThrow();
  });

  it('throws for duplicate slotIndex', () => {
    const appNudges = [
      { slotIndex: 0, hook: 'h', content: 'c', tone: 't', enabled: true, reasoning: 'r' },
      { slotIndex: 0, hook: 'h', content: 'c', tone: 't', enabled: true, reasoning: 'r' }, // duplicate
      { slotIndex: 2, hook: 'h', content: 'c', tone: 't', enabled: true, reasoning: 'r' },
    ];
    expect(() => validateAppNudgesSlotIndexes(appNudges, 3)).toThrow('Duplicate slotIndex: 0');
  });

  it('throws for slotIndex out of range (too high)', () => {
    const appNudges = [
      { slotIndex: 0, hook: 'h', content: 'c', tone: 't', enabled: true, reasoning: 'r' },
      { slotIndex: 1, hook: 'h', content: 'c', tone: 't', enabled: true, reasoning: 'r' },
      { slotIndex: 5, hook: 'h', content: 'c', tone: 't', enabled: true, reasoning: 'r' }, // out of range
    ];
    expect(() => validateAppNudgesSlotIndexes(appNudges, 3)).toThrow('slotIndex 5 out of range');
  });

  it('throws for slotIndex out of range (negative)', () => {
    const appNudges = [
      { slotIndex: -1, hook: 'h', content: 'c', tone: 't', enabled: true, reasoning: 'r' }, // negative
      { slotIndex: 1, hook: 'h', content: 'c', tone: 't', enabled: true, reasoning: 'r' },
      { slotIndex: 2, hook: 'h', content: 'c', tone: 't', enabled: true, reasoning: 'r' },
    ];
    expect(() => validateAppNudgesSlotIndexes(appNudges, 3)).toThrow('slotIndex -1 out of range');
  });

  it('throws for missing slotIndex', () => {
    const appNudges = [
      { slotIndex: 0, hook: 'h', content: 'c', tone: 't', enabled: true, reasoning: 'r' },
      { slotIndex: 2, hook: 'h', content: 'c', tone: 't', enabled: true, reasoning: 'r' },
      { slotIndex: 3, hook: 'h', content: 'c', tone: 't', enabled: true, reasoning: 'r' }, // skipped 1
    ];
    expect(() => validateAppNudgesSlotIndexes(appNudges, 4)).toThrow('Missing slotIndex: 1');
  });
});

// ===== estimateMaxTokens =====

describe('estimateMaxTokens', () => {
  it('returns estimated tokens for small slotCount', () => {
    const result = estimateMaxTokens(3, 0);
    // base(500) + 3*150 + 400 = 1350, * 1.3 = 1755
    expect(result).toBe(1755);
  });

  it('increases buffer on retry', () => {
    const attempt0 = estimateMaxTokens(5, 0);
    const attempt1 = estimateMaxTokens(5, 1);
    const attempt2 = estimateMaxTokens(5, 2);
    expect(attempt1).toBeGreaterThan(attempt0);
    expect(attempt2).toBeGreaterThan(attempt1);
  });

  it('clips at MODEL_MAX_TOKENS for large slotCount', () => {
    // Extreme case: 200 slots would exceed limit
    const result = estimateMaxTokens(200, 5);
    expect(result).toBe(MODEL_MAX_TOKENS);
    expect(result).toBe(16384);
  });

  it('clips at MODEL_MAX_TOKENS on high retry attempts', () => {
    // 100 slots with high retry buffer
    const result = estimateMaxTokens(100, 10);
    expect(result).toBe(MODEL_MAX_TOKENS);
  });
});

// ===== runCommanderAgent input validation =====

describe('runCommanderAgent input validation', () => {
  it('throws for undefined slotCount', async () => {
    const grounding = { problems: 'test' };
    await expect(runCommanderAgent({ grounding }))
      .rejects.toThrow('slotCount must be a positive integer');
  });

  it('throws for zero slotCount', async () => {
    const grounding = { problems: 'test' };
    await expect(runCommanderAgent({ grounding, slotCount: 0 }))
      .rejects.toThrow('slotCount must be a positive integer');
  });

  it('throws for negative slotCount', async () => {
    const grounding = { problems: 'test' };
    await expect(runCommanderAgent({ grounding, slotCount: -5 }))
      .rejects.toThrow('slotCount must be a positive integer');
  });

  it('throws for non-integer slotCount', async () => {
    const grounding = { problems: 'test' };
    await expect(runCommanderAgent({ grounding, slotCount: 3.5 }))
      .rejects.toThrow('slotCount must be a positive integer');
  });

  it('throws for string slotCount', async () => {
    const grounding = { problems: 'test' };
    await expect(runCommanderAgent({ grounding, slotCount: '5' }))
      .rejects.toThrow('slotCount must be a positive integer');
  });

  it('throws for slotCount exceeding MAX_SLOTS_PER_DAY', async () => {
    const grounding = { problems: 'test' };
    await expect(runCommanderAgent({ grounding, slotCount: MAX_SLOTS_PER_DAY + 1 }))
      .rejects.toThrow(`slotCount exceeds maximum ${MAX_SLOTS_PER_DAY}`);
  });

  it('accepts slotCount at MAX_SLOTS_PER_DAY boundary', async () => {
    // This will fail later (no OpenAI key in test), but should pass slotCount validation
    const grounding = { problems: 'test' };
    // We can't fully test this without mocking OpenAI, but we can verify the error is NOT about slotCount
    try {
      await runCommanderAgent({ grounding, slotCount: MAX_SLOTS_PER_DAY });
    } catch (error) {
      // Should fail for OpenAI reasons, not slotCount validation
      expect(error.message).not.toContain('slotCount');
    }
  });
});

// ===== validateNoDuplicates =====

describe('validateNoDuplicates', () => {
  it('returns valid=true for unique hooks and content', () => {
    const nudges = [
      { slotIndex: 0, hook: 'hook1', content: 'content1' },
      { slotIndex: 1, hook: 'hook2', content: 'content2' },
      { slotIndex: 2, hook: 'hook3', content: 'content3' },
    ];
    const result = validateNoDuplicates(nudges);
    expect(result.valid).toBe(true);
    expect(result.duplicates).toHaveLength(0);
  });

  it('detects duplicate hooks', () => {
    const nudges = [
      { slotIndex: 0, hook: 'same hook', content: 'content1' },
      { slotIndex: 1, hook: 'same hook', content: 'content2' },
    ];
    const result = validateNoDuplicates(nudges);
    expect(result.valid).toBe(false);
    expect(result.duplicates).toHaveLength(1);
    expect(result.duplicates[0].type).toBe('hook');
  });

  it('detects duplicate content', () => {
    const nudges = [
      { slotIndex: 0, hook: 'hook1', content: 'same content' },
      { slotIndex: 1, hook: 'hook2', content: 'same content' },
    ];
    const result = validateNoDuplicates(nudges);
    expect(result.valid).toBe(false);
    expect(result.duplicates).toHaveLength(1);
    expect(result.duplicates[0].type).toBe('content');
  });

  it('is case-insensitive', () => {
    const nudges = [
      { slotIndex: 0, hook: 'SAME HOOK', content: 'Content A' },
      { slotIndex: 1, hook: 'same hook', content: 'content a' },
    ];
    const result = validateNoDuplicates(nudges);
    expect(result.valid).toBe(false);
    expect(result.duplicates.length).toBeGreaterThan(0);
  });

  it('trims whitespace before comparison', () => {
    const nudges = [
      { slotIndex: 0, hook: '  hook  ', content: 'content' },
      { slotIndex: 1, hook: 'hook', content: '  content  ' },
    ];
    const result = validateNoDuplicates(nudges);
    expect(result.valid).toBe(false);
  });

  it('handles empty and null values gracefully', () => {
    const nudges = [
      { slotIndex: 0, hook: '', content: null },
      { slotIndex: 1, hook: null, content: '' },
    ];
    const result = validateNoDuplicates(nudges);
    // Empty strings should not trigger duplicates (skipped)
    expect(result.valid).toBe(true);
  });
});
