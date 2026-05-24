const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync } = require('child_process');

let testDir, testFile;

beforeEach(() => {
  testDir = fs.mkdtempSync(path.join(os.tmpdir(), 'naist-reg-'));
  testFile = path.join(testDir, 'deadlines.json');
  fs.writeFileSync(testFile, JSON.stringify({ schemaVersion: 1, deadlines: [] }), 'utf8');
});

afterEach(() => {
  fs.rmSync(testDir, { recursive: true });
});

function run(args) {
  const env = { ...process.env, PATH: '/opt/homebrew/bin:' + process.env.PATH, DEADLINES_FILE: testFile };
  return execSync('node ' + path.join(__dirname, '../scripts/register.js') + ' ' + args, { env, encoding: 'utf8' });
}

function readData() {
  return JSON.parse(fs.readFileSync(testFile, 'utf8'));
}

test('正常登録: タイトルと日付が保存される', () => {
  const out = run('機械学習レポート 2026-03-10');
  expect(out).toContain('登録しました');
  expect(out).toContain('機械学習レポート');
  const data = readData();
  expect(data.deadlines).toHaveLength(1);
  expect(data.deadlines[0].title).toBe('機械学習レポート');
  expect(data.deadlines[0].done).toBe(false);
});

test('IDが自動生成される', () => {
  run('テスト課題 2026-03-10');
  const data = readData();
  expect(data.deadlines[0].id).toBeTruthy();
  expect(data.deadlines[0].id.length).toBeGreaterThan(8);
});

test('複数件登録できる', () => {
  run('課題A 2026-03-10');
  run('課題B 2026-03-15');
  const data = readData();
  expect(data.deadlines).toHaveLength(2);
});

test('不正な日付のときエラーメッセージが出る', () => {
  try {
    run('課題A これは日付じゃない');
    fail('例外が出るべき');
  } catch (e) {
    expect(e.stderr || e.message).toBeTruthy();
  }
});
