import { describe, it, expect } from 'vitest';
import {
  SCHEDULE_MAP,
  NUDGE_TONES,
  parseTime,
  timeSortKey,
  buildFlattenedSlotTable,
  trimSlots,
  getScheduleMap,
} from '../scheduleMap.js';

// ===== v1.6.0 iOS一致検証用データ =====
const IOS_EXPECTED = {
  staying_up_late:     ['20:00', '22:00', '23:30', '00:00', '01:00'],  // 5スロット
  cant_wake_up:        ['06:00', '06:45', '07:15'],
  self_loathing:       ['08:00', '13:00', '19:00'],
  rumination:          ['08:30', '14:00', '21:00'],
  procrastination:     ['09:15', '13:30', '17:00'],
  anxiety:             ['07:30', '12:15', '18:45'],
  lying:               ['08:15', '13:15', '18:15'],
  bad_mouthing:        ['09:30', '14:30', '19:30'],
  porn_addiction:      ['20:30', '22:30', '23:45'],  // 3スロット
  alcohol_dependency:  ['16:00', '18:00', '20:15'],
  anger:               ['07:45', '12:30', '17:30'],
  obsessive:           ['09:00', '13:45', '18:30'],
  loneliness:          ['10:00', '15:00', '19:45'],
};

// ===== SCHEDULE_MAP (v1.6.0) =====

describe('SCHEDULE_MAP', () => {
  it('has 13 problem types', () => {
    expect(Object.keys(SCHEDULE_MAP)).toHaveLength(13);
  });

  it('v1.6.0: staying_up_late has 5 slots, others have 3', () => {
    expect(SCHEDULE_MAP.staying_up_late).toHaveLength(5);
    for (const [pt, times] of Object.entries(SCHEDULE_MAP)) {
      if (pt === 'staying_up_late') continue;
      expect(times).toHaveLength(3);
    }
  });

  it('all time strings match HH:MM format', () => {
    for (const times of Object.values(SCHEDULE_MAP)) {
      for (const t of times) {
        expect(t).toMatch(/^\d{2}:\d{2}$/);
      }
    }
  });

  it('matches iOS ProblemType.notificationSchedule', () => {
    for (const [problem, times] of Object.entries(IOS_EXPECTED)) {
      expect(SCHEDULE_MAP[problem]).toEqual(times);
    }
  });
});

// ===== getScheduleMap (v1.6.0 バージョン分岐) =====

describe('getScheduleMap', () => {
  it('returns OLD schedule for version 1.5.0', () => {
    const map = getScheduleMap('1.5.0');
    // 旧スケジュールは6スロット
    expect(map.staying_up_late).toHaveLength(6);
    expect(map.staying_up_late).toEqual(['20:00', '21:00', '22:00', '23:00', '00:00', '01:00']);
  });

  it('returns NEW schedule for version 1.6.0', () => {
    const map = getScheduleMap('1.6.0');
    // 新スケジュールは5スロット
    expect(map.staying_up_late).toHaveLength(5);
    expect(map.staying_up_late).toEqual(['20:00', '22:00', '23:30', '00:00', '01:00']);
  });

  it('returns NEW schedule for version 1.7.0', () => {
    const map = getScheduleMap('1.7.0');
    expect(map.staying_up_late).toHaveLength(5);
  });

  it('returns OLD schedule for null/undefined version', () => {
    const map1 = getScheduleMap(null);
    const map2 = getScheduleMap(undefined);
    const map3 = getScheduleMap('');
    expect(map1.staying_up_late).toHaveLength(6);
    expect(map2.staying_up_late).toHaveLength(6);
    expect(map3.staying_up_late).toHaveLength(6);
  });

  it('returns OLD schedule for invalid version string', () => {
    const map = getScheduleMap('invalid');
    expect(map.staying_up_late).toHaveLength(6);
  });

  it('handles version with build number (e.g., 1.6.0.1)', () => {
    const map = getScheduleMap('1.6.0.1');
    expect(map.staying_up_late).toHaveLength(5);
  });
});

// ===== v1.6.0: 間隔検証テスト =====

describe('slot intervals', () => {
  it('all slots have at least 15 minutes interval', () => {
    const allProblems = Object.keys(SCHEDULE_MAP);
    const slots = buildFlattenedSlotTable(allProblems);

    for (let i = 1; i < slots.length; i++) {
      const prev = slots[i - 1];
      const curr = slots[i];
      const prevMin = (prev.scheduledHour < 6 ? prev.scheduledHour + 24 : prev.scheduledHour) * 60 + prev.scheduledMinute;
      const currMin = (curr.scheduledHour < 6 ? curr.scheduledHour + 24 : curr.scheduledHour) * 60 + curr.scheduledMinute;
      const diff = currMin - prevMin;
      expect(diff).toBeGreaterThanOrEqual(15);
    }
  });

  it('total slot count is 41 (5 + 3*12)', () => {
    const allProblems = Object.keys(SCHEDULE_MAP);
    const slots = buildFlattenedSlotTable(allProblems);
    expect(slots).toHaveLength(41);
  });
});

// ===== NUDGE_TONES =====

describe('NUDGE_TONES', () => {
  it('has 5 tones', () => {
    expect(NUDGE_TONES).toHaveLength(5);
  });

  it('includes strict, gentle, empathetic, analytical, playful', () => {
    expect(NUDGE_TONES).toEqual(['strict', 'gentle', 'empathetic', 'analytical', 'playful']);
  });
});

// ===== parseTime =====

describe('parseTime', () => {
  it('parses "09:00" correctly', () => {
    expect(parseTime('09:00')).toEqual({ hour: 9, minute: 0 });
  });

  it('parses "22:30" correctly', () => {
    expect(parseTime('22:30')).toEqual({ hour: 22, minute: 30 });
  });

  it('parses "00:15" correctly', () => {
    expect(parseTime('00:15')).toEqual({ hour: 0, minute: 15 });
  });
});

// ===== timeSortKey =====

describe('timeSortKey', () => {
  it('normal hours return hour*60+minute', () => {
    expect(timeSortKey('09:00')).toBe(9 * 60);
    expect(timeSortKey('22:30')).toBe(22 * 60 + 30);
  });

  it('00:00-05:59 get +24h offset (date boundary rule)', () => {
    expect(timeSortKey('00:00')).toBe(24 * 60);
    expect(timeSortKey('01:30')).toBe(25 * 60 + 30);
    expect(timeSortKey('05:59')).toBe(29 * 60 + 59);
  });

  it('06:00 does NOT get offset', () => {
    expect(timeSortKey('06:00')).toBe(6 * 60);
  });

  it('23:00 < 00:00 in sort order (date boundary)', () => {
    expect(timeSortKey('23:00')).toBeLessThan(timeSortKey('00:00'));
  });

  it('00:00 < 01:00 in sort order', () => {
    expect(timeSortKey('00:00')).toBeLessThan(timeSortKey('01:00'));
  });
});

// ===== buildFlattenedSlotTable =====

describe('buildFlattenedSlotTable', () => {
  it('returns empty array for empty problems', () => {
    expect(buildFlattenedSlotTable([])).toEqual([]);
  });

  it('returns empty for unknown problem type', () => {
    expect(buildFlattenedSlotTable(['unknown_type'])).toEqual([]);
  });

  it('v1.6.0: single problem returns sorted slots with sequential slotIndex (3 slots)', () => {
    const slots = buildFlattenedSlotTable(['procrastination']);
    expect(slots).toHaveLength(3);
    expect(slots[0].slotIndex).toBe(0);
    expect(slots[2].slotIndex).toBe(2);
    // All should be procrastination
    for (const s of slots) {
      expect(s.problemType).toBe('procrastination');
    }
  });

  it('two problems are sorted by time then alphabetical', () => {
    const slots = buildFlattenedSlotTable(['staying_up_late', 'procrastination']);
    // First slot should be earliest time (v1.6.0: procrastination 09:15)
    expect(slots[0].scheduledTime).toBe('09:15');
    expect(slots[0].problemType).toBe('procrastination');

    // slotIndex is sequential
    for (let i = 0; i < slots.length; i++) {
      expect(slots[i].slotIndex).toBe(i);
    }
  });

  it('v1.6.0: date boundary: staying_up_late 23:30 < 00:00 < 01:00', () => {
    const slots = buildFlattenedSlotTable(['staying_up_late']);
    const times = slots.map(s => s.scheduledTime);
    // v1.6.0: Should be: 20:00, 22:00, 23:30, 00:00, 01:00
    expect(times).toEqual(['20:00', '22:00', '23:30', '00:00', '01:00']);
  });

  it('accepts optional scheduleMap parameter', () => {
    const customMap = { test_problem: ['10:00', '15:00'] };
    const slots = buildFlattenedSlotTable(['test_problem'], customMap);
    expect(slots).toHaveLength(2);
    expect(slots[0].scheduledTime).toBe('10:00');
    expect(slots[1].scheduledTime).toBe('15:00');
  });
});

// ===== trimSlots =====

describe('trimSlots', () => {
  it('v1.6.0: returns all slots when under maxSlots (3 slots)', () => {
    const slots = buildFlattenedSlotTable(['procrastination']);
    const trimmed = trimSlots(slots, ['procrastination'], 32);
    expect(trimmed).toHaveLength(3);
  });

  it('v1.6.0: trims to maxSlots with equal distribution (41 total > 32)', () => {
    // v1.6.0: 5 + 3*12 = 41 total > 32
    const allProblems = Object.keys(SCHEDULE_MAP);
    const slots = buildFlattenedSlotTable(allProblems);
    expect(slots.length).toBe(41);
    expect(slots.length).toBeGreaterThan(32);

    const trimmed = trimSlots(slots, allProblems, 32);
    expect(trimmed.length).toBeLessThanOrEqual(32);
  });

  it('each problem gets at least floor(max/n) slots', () => {
    const problems = ['staying_up_late', 'procrastination', 'anxiety'];
    const slots = buildFlattenedSlotTable(problems);
    const trimmed = trimSlots(slots, problems, 6);

    // floor(6/3) = 2 per problem
    for (const pt of problems) {
      const count = trimmed.filter(s => s.problemType === pt).length;
      expect(count).toBeGreaterThanOrEqual(2);
    }
  });

  it('re-assigns slotIndex after trimming', () => {
    const allProblems = Object.keys(SCHEDULE_MAP);
    const slots = buildFlattenedSlotTable(allProblems);
    const trimmed = trimSlots(slots, allProblems, 10);

    for (let i = 0; i < trimmed.length; i++) {
      expect(trimmed[i].slotIndex).toBe(i);
    }
  });

  it('trimmed slots are still sorted by time', () => {
    const problems = ['staying_up_late', 'procrastination', 'anxiety'];
    const slots = buildFlattenedSlotTable(problems);
    // v1.6.0: 5 + 3 + 3 = 11 slots total, trim to 9
    const trimmed = trimSlots(slots, problems, 9);

    for (let i = 1; i < trimmed.length; i++) {
      const prevKey = timeSortKey(trimmed[i - 1].scheduledTime);
      const currKey = timeSortKey(trimmed[i].scheduledTime);
      if (prevKey === currKey) {
        // Same time → alphabetical
        expect(trimmed[i - 1].problemType.localeCompare(trimmed[i].problemType)).toBeLessThanOrEqual(0);
      } else {
        expect(prevKey).toBeLessThan(currKey);
      }
    }
  });
});
