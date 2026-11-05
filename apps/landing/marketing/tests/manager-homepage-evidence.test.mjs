import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

const root = new URL('../', import.meta.url);
const read = (path) => readFileSync(new URL(path, root), 'utf8');
const sha256 = (path) => createHash('sha256').update(readFileSync(new URL(path, root))).digest('hex');
const visibleText = (html) => html.replace(/<[^>]+>/g, ' ').replace(/&amp;/g, '&').replace(/\s+/g, ' ');

test('English Manager homepage exposes current evidence, research, and honest limits', () => {
  const html = read('pages/en.html');
  const text = visibleText(html);

  assert.match(text, /one persistent manager we are building to study how behavior change can reduce suffering/i);
  assert.match(text, /does not ask every beneficiary to use a dedicated app or chat/i);
  assert.match(text, /observed actions, follow-up, and harm/i);
  assert.match(text, /67 published articles: 38 in English and 29 in Japanese/i);
  assert.match(text, /90 existing AI evaluations/i);
  assert.match(text, /P07-1 analyzed 269,603 published human-choice trials/);
  assert.match(text, /P07-2 compared next-observation brooding and stress forecasts/);
  assert.match(text, /COM-B/);
  assert.match(text, /OIDC checkpoint restore/i);
  assert.match(text, /positive canary[^.]*STOP \/ rollback[^.]*native-observation/i);
  assert.match(text, /Our early held-out human-data studies do not yet establish reliable generalization across populations, tasks, or interventions/i);
  assert.match(text, /what Anicca aims to build/i);
  assert.match(text, /beneficiaries should not need a dedicated app or chat/i);
  assert.match(text, /operator oversight, audit, and stop controls remain/i);
  assert.match(html, /href="https:\/\/aniccaai\.com\/blog\/manager"/);
  assert.match(html, /href="https:\/\/aniccaai\.com\/blog\/manager-eba-benchmark-landscape-en"/);
  assert.match(text, /Ampersand/);
  assert.match(text, /Persimmon/);
  assert.match(text, /Boba/);
  assert.match(text, /persuasive|persuasion/i);
  assert.match(html, /href="https:\/\/github\.com\/Daisuke134\/life-manager\/blob\/main\/products\/manager\/docs\/verification\/E16_CLOUD_EXECUTION_20261023\.md"/);
  assert.doesNotMatch(html, /blob\/docs\/manager-learning-20261017/);

  const manifest = JSON.parse(read('route-manifest.json'));
  assert.equal(manifest.files.find((file) => file.public_route === '/')?.sha256, sha256('pages/en.html'));
});

test('Japanese Manager homepage exposes the same evidence boundaries and research library', () => {
  const html = read('pages/ja.html');
  const text = visibleText(html);

  assert.match(text, /行動変容が苦しみを減らしうる条件を調べるために私たちがつくる、ひとつの持続的なマネージャーです/);
  assert.match(text, /受益者全員に専用アプリやチャット操作を求めません/);
  assert.match(text, /実際の行動、追跡、害を観測して評価します/);
  assert.match(text, /英語38本・日本語29本、計67本の記事/);
  assert.match(text, /AI評価90件/);
  assert.match(text, /P07-1では5研究の公開実人間選択269,603試行/);
  assert.match(text, /P07-2では別々の公開ESMデータ/);
  assert.match(text, /COM-B/);
  assert.match(text, /GitHub OIDCによるcheckpoint restore・update・release/i);
  assert.match(text, /positive canary[^.]*STOP \/ rollback[^.]*native observation/i);
  assert.match(text, /実人間データによる初期の参加者分離評価はありますが、未知の集団・行動・介入に一般化する信頼性はまだ確立していません/);
  assert.match(text, /Aniccaがつくることを目指す、ひとつのマネージャー/);
  assert.match(text, /受益者に専用のアプリやチャット操作を求めない構想/);
  assert.match(text, /運営者の監督・監査・停止手段は保ちます/);
  assert.match(html, /href="https:\/\/aniccaai\.com\/blog\/manager"/);
  assert.match(html, /href="https:\/\/aniccaai\.com\/blog\/manager-eba-benchmark-landscape-en"/);
  assert.match(text, /Ampersand/);
  assert.match(text, /Persimmon/);
  assert.match(text, /Boba/);
  assert.match(text, /説得/);
  assert.match(html, /href="https:\/\/github\.com\/Daisuke134\/life-manager\/blob\/main\/products\/manager\/docs\/verification\/E16_CLOUD_EXECUTION_20261023\.md"/);
  assert.doesNotMatch(html, /blob\/docs\/manager-learning-20261017/);

  const manifest = JSON.parse(read('route-manifest.json'));
  assert.equal(manifest.files.find((file) => file.public_route === '/ja')?.sha256, sha256('pages/ja.html'));
});
