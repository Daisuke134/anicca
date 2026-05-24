const fs = require('fs');
const path = require('path');
const os = require('os');

let testDir, testFile;

beforeEach(() => {
  testDir = fs.mkdtempSync(path.join(os.tmpdir(), 'naist-scan-'));
  testFile = path.join(testDir, 'deadlines.json');
  jest.resetModules();
  process.env.DEADLINES_FILE = testFile;
  process.env.SLACK_BOT_TOKEN = 'test-token';
  process.env.SLACK_CHANNEL_ID = 'C0TEST123';
});

afterEach(() => {
  fs.rmSync(testDir, { recursive: true });
  delete process.env.SLACK_BOT_TOKEN;
  delete process.env.SLACK_CHANNEL_ID;
});

function makeDeadlineAt(minutesFromNow) {
  const d = new Date(Date.now() + minutesFromNow * 60 * 1000);
  return d.toISOString();
}

function writeDeadlines(deadlines) {
  fs.writeFileSync(testFile, JSON.stringify({ schemaVersion: 1, deadlines }), 'utf8');
}

test('リマインド不要（3日後）の場合は通知しない', () => {
  writeDeadlines([
    { id: '1', title: '遠い課題', due: makeDeadlineAt(60 * 24 * 3 + 60), done: false, createdAt: '', remindedAt: [] }
  ]);
  jest.resetModules();
  const { checkAndNotify } = require('../scripts/scan');
  const sent = checkAndNotify({ dryRun: true });
  expect(sent).toHaveLength(0);
});

test('1時間以内の締切は通知する', () => {
  writeDeadlines([
    { id: '1', title: '今すぐ課題', due: makeDeadlineAt(30), done: false, createdAt: '', remindedAt: [] }
  ]);
  jest.resetModules();
  const { checkAndNotify } = require('../scripts/scan');
  const sent = checkAndNotify({ dryRun: true });
  expect(sent.length).toBeGreaterThan(0);
  expect(sent.join('')).toContain('今すぐ課題');
});

test('前日（24時間以内）の締切は通知する', () => {
  writeDeadlines([
    { id: '1', title: '明日の課題', due: makeDeadlineAt(60 * 20), done: false, createdAt: '', remindedAt: [] }
  ]);
  jest.resetModules();
  const { checkAndNotify } = require('../scripts/scan');
  const sent = checkAndNotify({ dryRun: true });
  expect(sent.length).toBeGreaterThan(0);
});

test('既に通知済み（remindedAt）の場合は重複通知しない', () => {
  const hourStr = new Date().toISOString().substring(0, 13);
  const key1h = '1h_' + hourStr;
  const key1d = '1d_' + hourStr;
  writeDeadlines([
    { id: '1', title: '重複課題', due: makeDeadlineAt(30), done: false, createdAt: '', remindedAt: [key1h, key1d] }
  ]);
  jest.resetModules();
  const { checkAndNotify } = require('../scripts/scan');
  const sent = checkAndNotify({ dryRun: true });
  expect(sent).toHaveLength(0);
});

test('done:trueの課題はスキャンしない', () => {
  writeDeadlines([
    { id: '1', title: '完了済み', due: makeDeadlineAt(10), done: true, createdAt: '', remindedAt: [] }
  ]);
  jest.resetModules();
  const { checkAndNotify } = require('../scripts/scan');
  const sent = checkAndNotify({ dryRun: true });
  expect(sent).toHaveLength(0);
});
