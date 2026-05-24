let parseDate;

beforeEach(() => {
  jest.resetModules();
  parseDate = require('../scripts/utils/date').parseDate;
});

test('ISO8601文字列をそのまま返す', () => {
  const result = parseDate('2026-03-10T23:59:00+09:00');
  expect(result).toBe('2026-03-10T23:59:00+09:00');
});

test('YYYY-MM-DD形式をパースできる', () => {
  const result = parseDate('2026-03-10');
  expect(result).toMatch(/2026-03-10/);
});

test('自然言語「明日」をパースできる', () => {
  const result = parseDate('明日');
  expect(result).toBeTruthy();
  // ISO文字列から日付部分を取り出して比較
  const dateStr = result.substring(0, 10); // 2026-02-24
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const pad = n => String(n).padStart(2, '0');
  const tomorrowStr = tomorrow.getFullYear() + '-' + pad(tomorrow.getMonth() + 1) + '-' + pad(tomorrow.getDate());
  expect(dateStr).toBe(tomorrowStr);
});

test('「3月10日」形式をパースできる', () => {
  const result = parseDate('3月10日');
  expect(result).toBeTruthy();
  expect(result).toMatch(/03-10|3-10/);
});

test('不正な文字列はnullを返す', () => {
  const result = parseDate('これは日付ではない');
  expect(result).toBeNull();
});
