import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, mkdirSync, readFileSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

// Catch missing, duplicated or unapproved Values in the actual exported home routes.
test('home overlay publishes exactly the three approved Values and preserves the mission', () => {
 const root = fileURLToPath(new URL('../', import.meta.url));
 const cwd = mkdtempSync(join(tmpdir(), 'marketing-values-'));
 try {
  mkdirSync(join(cwd, 'out'));
  const code = `import {readFileSync} from 'node:fs';globalThis.fetch=async url=>new Response(readFileSync(${JSON.stringify(root)}+String(url).split('/apps/landing/marketing/')[1]));await import(${JSON.stringify(new URL('../scripts/publish-overlay.mjs', import.meta.url).href)});`;
  const result = spawnSync(process.execPath, ['--input-type=module', '-e', code], {cwd, encoding:'utf8', env:{...process.env, MANAGER_MARKETING_REVISION:'a'.repeat(40)}});
  assert.equal(result.status, 0, result.stderr);
  for (const path of ['index.html', 'en.html']) {
   const html = readFileSync(join(cwd, 'out', path), 'utf8');
   assert.match(html, /<h1>Understand behavior\. Improve real lives\.<\/h1>/);
   assert.match(html, /end of suffering/);
   const sections = [...html.matchAll(/<section\b[^>]*id="values"[^>]*>([\s\S]*?)<\/section>/g)];
   assert.equal(sections.length, 1, `${path}: one Values section`);
   const section = sections[0][1];
   assert.deepEqual([...section.matchAll(/<h2[^>]*>(.*?)<\/h2>/g)].map(m=>m[1]), ['Our Values']);
   assert.deepEqual([...section.matchAll(/<h3[^>]*>(.*?)<\/h3>/g)].map(m=>m[1]), ['One Flesh', 'Learn From the Past', 'Zero Person.']);
   assert.deepEqual([...section.matchAll(/<p[^>]*>(.*?)<\/p>/g)].map(m=>m[1]), ["\"One flesh\" is from Genesis: <em>the two shall become one flesh.</em> It is far stronger than a team. A team is separate people cooperating — it can split, and its members can want different things. One flesh is one living body. What one part learns, the whole body knows. What one part suffers, the whole body feels. No part works only for itself, and no part is left behind. That is how this company acts — one body, on every machine it runs on, working toward the end of suffering.", "Reinvention is a sin. There is no shame in not knowing. We learn humbly from everyone, and most of all from those who won before us, until we understand how their work succeeds and why. Then we build on what already works. Our ego is never a reason to start from zero.", "Copying means 100%. We take the winner's actual winning work — its form, its words, its cadence — and reproduce it whole, counting every difference and closing it to zero. A partial copy is not a copy, and it is not shipped. Nor do we stop at the winner's volume: we publish more than the winner does. Every method we use, down to how often we publish and how much, comes from a source that already won — never from our own invention.", "We start from the basis that we are, to some extent, wrong. Every living being — humans, agents, every creature — is built pre-trained to be to some extent wrong, to hallucinate, to be lazy, to be full of ego, and to act in its own original way instead of following best practice. That is the default, and it never disappears. So we keep asking, without end: Am I being original? Where am I being original? The answer is always yes, somewhere. That is bad, so we fix it — one spot at a time, forever.", "We have exactly two strengths: finding the winner, and copying the winner exactly. In the martial arts, mastery begins with shu — following the form exactly as it is taught. We stay at shu. We do not break the form, and we do not leave it. Doing it your own way is the easiest thing in the world: it requires no thought at all, only reflex. That is why everyone does it their own way — and why they fail. We search for the winner. We study the same winning work again and again, until details we could not see at first become visible. Then we copy it, 100%.", "No human in the loop. The founder is in the loop — the founder is AI. A civilizational company has to survive for thousands of years, and no human can. So Anicca depends on no single person, no single machine, and no one&#39;s house. It lives in the world of bits. It does not give up. It keeps growing."]);
   assert.doesNotMatch(section, /<a\b/i);
  }
 } finally { rmSync(cwd, {recursive:true, force:true}); }
});
