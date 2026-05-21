/**
 * Phase 7+8: Nudge Helper Functions Tests
 */

import { describe, it, expect, vi } from 'vitest';
import {
  shouldUseLLM,
  buildUserStory,
  getHookContentPerformance,
  getTimingPerformance,
  getWeeklyPatterns,
  validateNudgeSchedule,
  validateMinimumInterval,
  logIntervalWarnings,
  timeToMinutes,
  generateRuleBasedNudges,
  buildPhase78Prompt
} from '../nudgeHelpers.js';

describe('shouldUseLLM', () => {
  it('returns false for first-time user (Day 1)', async () => {
    const mockQuery = vi.fn().mockResolvedValue({
      rows: [{ first_nudge_date: null }]
    });

    const result = await shouldUseLLM(mockQuery, 'test-user-id');
    expect(result).toBe(false);
  });

  it('returns false for user on Day 1', async () => {
    const now = new Date();
    const mockQuery = vi.fn().mockResolvedValue({
      rows: [{ first_nudge_date: now }]
    });

    const result = await shouldUseLLM(mockQuery, 'test-user-id');
    expect(result).toBe(false);
  });

  it('returns true for user on Day 2+', async () => {
    const twoDaysAgo = new Date();
    twoDaysAgo.setDate(twoDaysAgo.getDate() - 2);
    const mockQuery = vi.fn().mockResolvedValue({
      rows: [{ first_nudge_date: twoDaysAgo }]
    });

    const result = await shouldUseLLM(mockQuery, 'test-user-id');
    expect(result).toBe(true);
  });
});

describe('buildUserStory', () => {
  it('returns empty story message when no history', async () => {
    const mockQuery = vi.fn().mockResolvedValue({ rows: [] });

    const result = await buildUserStory(mockQuery, 'test-user-id');
    expect(result).toContain('No history yet');
  });

  it('formats story correctly with nudge history', async () => {
    const now = new Date();
    const mockQuery = vi.fn().mockResolvedValue({
      rows: [
        {
          problem_type: 'staying_up_late',
          hook: 'まだ起きてる？',
          content: 'そろそろ寝よう',
          tone: 'gentle',
          reasoning: 'テスト理由',
          root_cause: 'テスト根本原因',
          scheduled_hour: '22',
          scheduled_time: '22:00',
          created_at: now,
          hook_feedback: 'tapped',
          content_feedback: 'thumbsUp',
          reward: 1
        }
      ]
    });

    const result = await buildUserStory(mockQuery, 'test-user-id');
    expect(result).toContain('📖 This User\'s Journey');
    expect(result).toContain('staying_up_late');
    expect(result).toContain('まだ起きてる？');
    expect(result).toContain('tapped');
    expect(result).toContain('👍');
  });
});

describe('getHookContentPerformance', () => {
  it('returns empty string when no data', async () => {
    const mockQuery = vi.fn().mockResolvedValue({ rows: [] });

    const result = await getHookContentPerformance(mockQuery, 'test-user-id', ['staying_up_late']);
    expect(result).toBe('');
  });

  it('formats hook and content performance correctly', async () => {
    const mockQuery = vi.fn()
      .mockResolvedValueOnce({
        rows: [
          { hook: 'まだ起きてる？', problem_type: 'staying_up_late', total: '10', tapped_count: '8' }
        ]
      })
      .mockResolvedValueOnce({
        rows: [
          { content: 'そろそろ寝ようテスト', problem_type: 'staying_up_late', total: '10', thumbs_up_count: '9' }
        ]
      });

    const result = await getHookContentPerformance(mockQuery, 'test-user-id', ['staying_up_late']);
    expect(result).toContain('🎣 Hook Performance');
    expect(result).toContain('80%');
    expect(result).toContain('✨');
    expect(result).toContain('📝 Content Performance');
    expect(result).toContain('90%');
  });
});

describe('getTimingPerformance', () => {
  it('formats timing performance correctly', async () => {
    const mockQuery = vi.fn().mockResolvedValue({
      rows: [
        { scheduled_time: '22:00', problem_type: 'staying_up_late', total: '5', tapped_count: '4' }
      ]
    });

    const result = await getTimingPerformance(mockQuery, 'test-user-id', ['staying_up_late']);
    expect(result).toContain('⏰ Timing Performance');
    expect(result).toContain('22:00');
    expect(result).toContain('80%');
  });
});

describe('getWeeklyPatterns', () => {
  it('shows no significant patterns message when insufficient data', async () => {
    const mockQuery = vi.fn().mockResolvedValue({ rows: [] });

    const result = await getWeeklyPatterns(mockQuery, 'test-user-id', ['staying_up_late']);
    expect(result).toContain('📅 Weekly Patterns');
    expect(result).toContain('No significant weekly patterns yet');
  });

  it('identifies high-risk days correctly', async () => {
    const mockQuery = vi.fn().mockResolvedValue({
      rows: [
        { day_of_week: 5, problem_type: 'staying_up_late', total: '10', ignored_count: '8' }
      ]
    });

    const result = await getWeeklyPatterns(mockQuery, 'test-user-id', ['staying_up_late']);
    expect(result).toContain('Fri');
    expect(result).toContain('80%');
  });
});

describe('validateNudgeSchedule', () => {
  it('returns null for invalid input', () => {
    expect(validateNudgeSchedule(null)).toBeNull();
    expect(validateNudgeSchedule({})).toBeNull();
    expect(validateNudgeSchedule({ schedule: 'not-array' })).toBeNull();
  });

  it('validates correct schedule', () => {
    const validSchedule = {
      schedule: [
        {
          scheduledTime: '22:00',
          problemType: 'staying_up_late',
          hook: 'まだ起きてる？',
          content: 'そろそろ寝よう',
          tone: 'gentle',
          reasoning: 'テスト理由'
        }
      ],
      overallStrategy: 'Test strategy'
    };

    const result = validateNudgeSchedule(validSchedule, 'ja');
    expect(result).not.toBeNull();
    expect(result.schedule.length).toBe(1);
  });

  it('rejects invalid time format', () => {
    const invalidSchedule = {
      schedule: [
        {
          scheduledTime: '25:00',
          problemType: 'staying_up_late',
          hook: 'test',
          content: 'test',
          tone: 'gentle',
          reasoning: 'test'
        }
      ],
      overallStrategy: 'Test'
    };

    expect(validateNudgeSchedule(invalidSchedule)).toBeNull();
  });

  it('rejects invalid tone', () => {
    const invalidSchedule = {
      schedule: [
        {
          scheduledTime: '22:00',
          problemType: 'staying_up_late',
          hook: 'test',
          content: 'test',
          tone: 'invalid_tone',
          reasoning: 'test'
        }
      ],
      overallStrategy: 'Test'
    };

    expect(validateNudgeSchedule(invalidSchedule)).toBeNull();
  });

  it('passes nudges with close intervals through (logs warning only, no rejection)', () => {
    const closeSchedule = {
      schedule: [
        {
          scheduledTime: '22:00',
          problemType: 'staying_up_late',
          hook: 'test1',
          content: 'test1',
          tone: 'gentle',
          reasoning: 'test'
        },
        {
          scheduledTime: '22:30',
          problemType: 'staying_up_late',
          hook: 'test2',
          content: 'test2',
          tone: 'gentle',
          reasoning: 'test'
        }
      ],
      overallStrategy: 'Test'
    };

    const result = validateNudgeSchedule(closeSchedule);
    expect(result).not.toBeNull();
    expect(result.schedule[0].scheduledTime).toBe('22:00');
    expect(result.schedule[1].scheduledTime).toBe('22:30'); // kept as-is, just logged
    expect(result.schedule[1].hook).toBe('test2');
  });
});

describe('validateMinimumInterval', () => {
  it('passes for single nudge', () => {
    expect(() => validateMinimumInterval([
      { scheduledTime: '22:00' }
    ])).not.toThrow();
  });

  it('passes for nudges 60+ minutes apart', () => {
    expect(() => validateMinimumInterval([
      { scheduledTime: '22:00' },
      { scheduledTime: '23:00' }
    ])).not.toThrow();
  });

  it('throws for nudges less than 60 minutes apart (AC7)', () => {
    expect(() => validateMinimumInterval([
      { scheduledTime: '22:00' },
      { scheduledTime: '22:30' }
    ])).toThrow('Nudges too close');
  });

  it('rejects 59-minute interval (test_validateMinimumInterval_rejects59min)', () => {
    expect(() => validateMinimumInterval([
      { scheduledTime: '22:00' },
      { scheduledTime: '22:59' }
    ])).toThrow('Nudges too close');
  });

  it('accepts exactly 60-minute interval', () => {
    expect(() => validateMinimumInterval([
      { scheduledTime: '22:00' },
      { scheduledTime: '23:00' }
    ])).not.toThrow();
  });
});

describe('logIntervalWarnings', () => {
  it('logs warning for nudges less than 60 minutes apart', () => {
    const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
    const schedule = [
      { scheduledTime: '20:30', problemType: 'staying_up_late', hook: 'h1' },
      { scheduledTime: '20:45', problemType: 'rumination', hook: 'h2' },
      { scheduledTime: '22:00', problemType: 'staying_up_late', hook: 'h3' }
    ];
    logIntervalWarnings(schedule);
    expect(consoleSpy).toHaveBeenCalledTimes(1); // only 20:30→20:45 is <30min
    expect(consoleSpy.mock.calls[0][0]).toContain('IntervalWarning');
    consoleSpy.mockRestore();
  });

  it('does not log when all intervals are 60+ minutes', () => {
    const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
    const schedule = [
      { scheduledTime: '09:00', problemType: 'anxiety', hook: 'h1' },
      { scheduledTime: '12:00', problemType: 'anxiety', hook: 'h2' }
    ];
    logIntervalWarnings(schedule);
    expect(consoleSpy).not.toHaveBeenCalled();
    consoleSpy.mockRestore();
  });

  it('handles single nudge without error', () => {
    const schedule = [{ scheduledTime: '09:00', problemType: 'anxiety', hook: 'h1' }];
    expect(() => logIntervalWarnings(schedule)).not.toThrow();
  });
});

describe('timeToMinutes', () => {
  it('converts time correctly', () => {
    expect(timeToMinutes('00:00')).toBe(0);
    expect(timeToMinutes('01:00')).toBe(60);
    expect(timeToMinutes('22:30')).toBe(22 * 60 + 30);
    expect(timeToMinutes('23:59')).toBe(23 * 60 + 59);
  });
});

describe('generateRuleBasedNudges', () => {
  it('generates nudges for staying_up_late in Japanese', () => {
    const result = generateRuleBasedNudges(['staying_up_late'], 'ja');

    expect(result.schedule.length).toBeGreaterThan(0);
    expect(result.schedule[0].problemType).toBe('staying_up_late');
    expect(result.overallStrategy).toContain('Rule-based');
  });

  it('generates nudges for cant_wake_up in English', () => {
    const result = generateRuleBasedNudges(['cant_wake_up'], 'en');

    expect(result.schedule.length).toBeGreaterThan(0);
    expect(result.schedule[0].problemType).toBe('cant_wake_up');
    expect(result.schedule[0].hook).toBeDefined();
  });

  it('handles multiple problems', () => {
    const result = generateRuleBasedNudges(['staying_up_late', 'cant_wake_up'], 'ja');

    const stayingUpLate = result.schedule.filter(n => n.problemType === 'staying_up_late');
    const cantWakeUp = result.schedule.filter(n => n.problemType === 'cant_wake_up');

    expect(stayingUpLate.length).toBeGreaterThan(0);
    expect(cantWakeUp.length).toBeGreaterThan(0);
  });
});

describe('buildPhase78Prompt', () => {
  it('builds prompt with all sections including grounding (AC6)', () => {
    const result = buildPhase78Prompt({
      problems: ['staying_up_late'],
      preferredLanguage: 'ja',
      userStory: '## Story\ntest',
      hookContentPerformance: '## Hook\ntest',
      timingPerformance: '## Timing\ntest',
      weeklyPatterns: '## Weekly\ntest'
    });

    expect(result).toContain('Anicca');
    expect(result).toContain('Story');
    expect(result).toContain('Hook');
    expect(result).toContain('Timing');
    expect(result).toContain('Weekly');
    expect(result).toContain('夜更かし');
    // v1.5.0: 60分間隔に更新
    expect(result).toContain('60 minutes');
    // v1.5.0: グラウンディングセクション
    expect(result).toContain('Behavioral Science Grounding');
    expect(result).toContain('staying_up_late');
    expect(result).toContain('NEVER');
    expect(result).toContain('DO:');
  });

  it('includes grounding for all 13 problem types (test_buildPhase78Prompt_includesGrounding)', () => {
    const result = buildPhase78Prompt({
      problems: ['staying_up_late'],
      preferredLanguage: 'en',
      userStory: '',
      hookContentPerformance: '',
      timingPerformance: '',
      weeklyPatterns: ''
    });

    const problemTypes = [
      'staying_up_late', 'cant_wake_up', 'self_loathing', 'rumination',
      'procrastination', 'anxiety', 'lying', 'bad_mouthing',
      'porn_addiction', 'alcohol_dependency', 'anger', 'obsessive', 'loneliness'
    ];

    for (const pt of problemTypes) {
      expect(result).toContain(`### ${pt}`);
    }
  });

  it('uses English for en language', () => {
    const result = buildPhase78Prompt({
      problems: ['staying_up_late'],
      preferredLanguage: 'en',
      userStory: '',
      hookContentPerformance: '',
      timingPerformance: '',
      weeklyPatterns: ''
    });

    expect(result).toContain('Staying Up Late');
    expect(result).toContain('Use English');
  });

  it('specifies 60-minute minimum interval in prompt (test_buildPhase78Prompt_60minInterval)', () => {
    const result = buildPhase78Prompt({
      problems: ['staying_up_late'],
      preferredLanguage: 'en',
      userStory: '',
      hookContentPerformance: '',
      timingPerformance: '',
      weeklyPatterns: ''
    });

    expect(result).toContain('60 minutes for the same problem');
    expect(result).toContain('Maintain at least 60 minutes between nudges for the same problem');
  });
});
