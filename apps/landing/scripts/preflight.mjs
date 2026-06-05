// taste-skill §14 機械チェックの一部を built `out/` に対して実行。
// 使い方: npm run build && node scripts/preflight.mjs [glob-or-dir]
//   default: out/ 配下の全 *.html
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    const s = statSync(p);
    if (s.isDirectory()) walk(p, out);
    else if (s.isFile() && p.endsWith('.html')) out.push(p);
  }
  return out;
}

const root = process.argv[2] || 'out';
let files = [];
try {
  const s = statSync(root);
  if (s.isDirectory()) files = walk(root);
  else if (s.isFile() && root.endsWith('.html')) files = [root];
  else {
    console.error(`preflight: ${root} is not a dir or .html file`);
    process.exit(2);
  }
} catch (e) {
  console.error(`preflight: cannot read ${root}: ${e.message}`);
  process.exit(2);
}

// strict=1 (env or --strict) → em-dash も blocking (per-page Tier A redesign 時)
// 既定 (foundation 段階) → Inter のみ blocking、em-dash は report-only
const strict =
  process.env.PREFLIGHT_STRICT === '1' || process.argv.includes('--strict');

let fail = 0;
let emDashReport = 0;
let pages = 0;
for (const f of files) {
  pages++;
  const html = readFileSync(f, 'utf8');
  // §9.G em-dash / en-dash 完全禁止 (本文表示部のみ。<head> や meta の URL 等を素朴に
  // チェックすると false positive を生むため body 内テキスト系のみ大雑把に抽出)。
  const visible = html
    .replace(/<head[\s\S]*?<\/head>/gi, '')
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<style[\s\S]*?<\/style>/gi, '');
  const emdash = (visible.match(/[—–]/g) || []).length;
  // §4.1 Inter 残存禁止 (next/font は __Inter_xxx を吐く)
  const inter = /__Inter[_-]|font-inter/i.test(html);
  if (emdash > 0) {
    if (strict) {
      console.log(`FAIL em-dash x${emdash}: ${f}`);
      fail++;
    } else {
      emDashReport += emdash;
    }
  }
  if (inter) {
    console.log(`FAIL Inter ref: ${f}`);
    fail++;
  }
}
if (!strict && emDashReport > 0) {
  console.log(
    `report-only: em-dash x${emDashReport} across pages (re-run with --strict at per-page Tier A redesign)`,
  );
}
console.log(
  fail === 0
    ? `PREFLIGHT OK (${pages} html files, mode=${strict ? 'strict' : 'foundation'})`
    : `PREFLIGHT FAIL (${fail} violations across ${pages} files, mode=${strict ? 'strict' : 'foundation'})`,
);
process.exit(fail === 0 ? 0 : 1);
