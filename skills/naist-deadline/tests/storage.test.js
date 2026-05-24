const fs = require('fs');
const path = require('path');
const os = require('os');

// テスト用の一時ディレクトリを使用
let testDir;
let testFile;
let storage;

beforeEach(() => {
  testDir = fs.mkdtempSync(path.join(os.tmpdir(), 'naist-deadline-test-'));
  testFile = path.join(testDir, 'deadlines.json');
  // モジュールキャッシュをクリアして新しいtestFileを使えるようにする
  jest.resetModules();
  process.env.DEADLINES_FILE = testFile;
  storage = require('../scripts/utils/storage');
});

afterEach(() => {
  fs.rmSync(testDir, { recursive: true });
});

test('read: ファイルが存在しない場合は空のデータを返す', () => {
  const data = storage.read();
  expect(data.schemaVersion).toBe(1);
  expect(data.deadlines).toEqual([]);
});

test('write: データをファイルに保存できる', () => {
  const data = { schemaVersion: 1, deadlines: [{ id: '1', title: 'テスト', due: '2026-03-10', done: false }] };
  storage.write(data);
  const saved = JSON.parse(fs.readFileSync(testFile, 'utf8'));
  expect(saved.deadlines[0].title).toBe('テスト');
});

test('write: 原子的書き込み（一時ファイル経由）', () => {
  const data = { schemaVersion: 1, deadlines: [] };
  storage.write(data);
  // tmpファイルが残っていないことを確認
  expect(fs.existsSync(testFile + '.tmp')).toBe(false);
  expect(fs.existsSync(testFile)).toBe(true);
});

test('read/write: 往復が正確', () => {
  const original = {
    schemaVersion: 1,
    deadlines: [{ id: 'abc', title: '機械学習レポート', due: '2026-03-10T23:59:00+09:00', done: false, createdAt: '2026-02-23', remindedAt: [] }]
  };
  storage.write(original);
  const restored = storage.read();
  expect(restored.deadlines[0].id).toBe('abc');
  expect(restored.deadlines[0].title).toBe('機械学習レポート');
});
