const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync } = require('child_process');

let testDir, testFile;

beforeEach(() => {
  testDir = fs.mkdtempSync(path.join(os.tmpdir(), 'naist-cmp-'));
  testFile = path.join(testDir, 'deadlines.json');
  fs.writeFileSync(testFile, JSON.stringify({
    schemaVersion: 1,
    deadlines: [
      { id: 'aaa', title: '機械学習レポート', due: '2099-03-10T23:59:00+09:00', done: false, createdAt: '', remindedAt: [] },
      { id: 'bbb', title: 'プログラミング課題', due: '2099-03-15T23:59:00+09:00', done: false, createdAt: '', remindedAt: [] },
    ]
  }), 'utf8');
});

afterEach(() => {
  fs.rmSync(testDir, { recursive: true });
});

function run(args) {
  const env = { ...process.env, PATH: '/opt/homebrew/bin:' + process.env.PATH, DEADLINES_FILE: testFile };
  return execSync('node ' + path.join(__dirname, '../scripts/complete.js') + ' ' + args, { env, encoding: 'utf8' });
}

function readData() {
  return JSON.parse(fs.readFileSync(testFile, 'utf8'));
}

test('タイトル完全一致で完了マーク', () => {
  const out = run('機械学習レポート');
  expect(out).toContain('完了しました');
  const data = readData();
  expect(data.deadlines.find(d => d.id === 'aaa').done).toBe(true);
  expect(data.deadlines.find(d => d.id === 'bbb').done).toBe(false);
});

test('部分一致でも完了マーク', () => {
  run('機械学習');
  const data = readData();
  expect(data.deadlines.find(d => d.id === 'aaa').done).toBe(true);
});

test('存在しない課題のときエラーメッセージ', () => {
  try {
    run('存在しない課題');
    fail('例外が出るべき');
  } catch (e) {
    expect(e.stderr || e.message).toBeTruthy();
  }
});
