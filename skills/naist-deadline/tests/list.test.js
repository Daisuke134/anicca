const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync } = require('child_process');

let testDir, testFile;

beforeEach(() => {
  testDir = fs.mkdtempSync(path.join(os.tmpdir(), 'naist-list-'));
  testFile = path.join(testDir, 'deadlines.json');
});

afterEach(() => {
  fs.rmSync(testDir, { recursive: true });
});

function run(args = '') {
  const env = { ...process.env, PATH: '/opt/homebrew/bin:' + process.env.PATH, DEADLINES_FILE: testFile };
  return execSync('node ' + path.join(__dirname, '../scripts/list.js') + ' ' + args, { env, encoding: 'utf8' });
}

function writeDeadlines(deadlines) {
  fs.writeFileSync(testFile, JSON.stringify({ schemaVersion: 1, deadlines }), 'utf8');
}

test('締切なしの場合「登録されている締切はありません」を返す', () => {
  writeDeadlines([]);
  const out = run();
  expect(out).toContain('締切はありません');
});

test('done:falseの締切のみ表示される', () => {
  writeDeadlines([
    { id: '1', title: '課題A', due: '2099-03-10T23:59:00+09:00', done: false, createdAt: '', remindedAt: [] },
    { id: '2', title: '課題B（完了）', due: '2099-03-11T23:59:00+09:00', done: true, createdAt: '', remindedAt: [] },
  ]);
  const out = run();
  expect(out).toContain('課題A');
  expect(out).not.toContain('課題B（完了）');
});

test('複数件が直近順に表示される', () => {
  writeDeadlines([
    { id: '2', title: '後の課題', due: '2099-04-01T23:59:00+09:00', done: false, createdAt: '', remindedAt: [] },
    { id: '1', title: '早い課題', due: '2099-03-01T23:59:00+09:00', done: false, createdAt: '', remindedAt: [] },
  ]);
  const out = run();
  const posA = out.indexOf('早い課題');
  const posB = out.indexOf('後の課題');
  expect(posA).toBeLessThan(posB);
});
