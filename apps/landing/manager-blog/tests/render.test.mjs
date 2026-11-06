import test from 'node:test';
import assert from 'node:assert/strict';
import { renderManagerMarkdown, managerShareMetadata, blogPairLanguages, blogPairAlternates } from '../lib/render-manager-markdown.mjs';

test('renders comparison tables, numbered steps and escaped fenced code', () => {
 const html = renderManagerMarkdown('# Test\n\n| Method | Cost |\n| --- | --- |\n| IPF | Low |\n\n1. Get data\n2. Compare\n\n```js\n<script>bad()</script>\n```');
 assert.match(html, /<table/); assert.match(html, /<th[^>]*>Method/); assert.match(html, /<td[^>]*>IPF/);
 assert.match(html, /<ol/); assert.match(html, /<li>Compare/);
 assert.match(html, /&lt;script&gt;bad\(\)&lt;\/script&gt;/); assert.doesNotMatch(html, /<script>/);
});
test('blocks executable and protocol-relative links and attribute injections', () => {
 const html = renderManagerMarkdown('[bad](javascript:alert) ![x](data:bad) [bad](//evil.test) [slash](/\\evil.test) ![quote\"](/safe.png) <img onerror=bad>');
 assert.doesNotMatch(html, /href="(?:javascript|\/\/|\/\\)|src="data|alt="quote""|<img onerror/);
 assert.match(html, /alt="quote&quot;"/); assert.match(html, /&lt;img/);
});
test('keeps citations, local media, readable paragraphs and formatting', () => {
 const html = renderManagerMarkdown('## Result\n\n**Better** with `IPF` and [source](https://example.org/a?q=1&x=2).\n\n![Result](/blog/manager/media/abc.png)\n\n- One\n- Two');
 assert.match(html, /<strong>Better/); assert.match(html, /<code/); assert.match(html, /href="https:\/\/example.org\/a\?q=1&amp;x=2"/);
 assert.match(html, /src="\/blog\/manager\/media\/abc.png"/); assert.match(html, /<ul/);
});

test('Manager sharing uses the original first image and language, escaping URL schemes', () => {
 const post={project:'Manager',slug:'manager-every-pro-an-amateur-ja',lang:'ja',title:'AIの論考',date:'2026-11-03',description:'論考',markdown:'![Hero](https://aniccaai.com/blog/manager/media/abc.png)'};
 const meta=managerShareMetadata(post);
 assert.equal(meta.openGraph.images[0].url,'https://aniccaai.com/blog/manager/media/abc.png');
 assert.equal(meta.openGraph.locale,'ja_JP');
 assert.equal(meta.openGraph.type,'article');
 assert.equal(meta.twitter.card,'summary_large_image');
 assert.deepEqual(managerShareMetadata({...post,project:'Other'}),{});
 assert.deepEqual(managerShareMetadata({...post,markdown:'![bad](javascript:bad)'}),{});
});

test('blog pair hreflang links only complete -en/-ja pairs, x-default at EN', () => {
 const slugs=['manager-behavior-data-audit-en','manager-behavior-data-audit-ja','tiktok-ad-script-ja','tokens-to-money','best-affirmation-apps-2026-11-05'];
 const expected={en:'https://aniccaai.com/blog/manager-behavior-data-audit-en',ja:'https://aniccaai.com/blog/manager-behavior-data-audit-ja','x-default':'https://aniccaai.com/blog/manager-behavior-data-audit-en'};
 assert.deepEqual(blogPairLanguages('manager-behavior-data-audit-en',slugs),expected);
 assert.deepEqual(blogPairLanguages('manager-behavior-data-audit-ja',slugs),expected);
 assert.deepEqual(blogPairAlternates('manager-behavior-data-audit-ja',slugs),{languages:expected});
 // Counterpart missing, no suffix, and date-suffixed slugs get no alternates.
 assert.equal(blogPairLanguages('tiktok-ad-script-ja',slugs),null);
 assert.equal(blogPairLanguages('tokens-to-money',slugs),null);
 assert.equal(blogPairLanguages('best-affirmation-apps-2026-11-05',slugs),null);
 assert.deepEqual(blogPairAlternates('tiktok-ad-script-ja',slugs),{});
 // A word merely ending in "en" is not a language suffix.
 assert.equal(blogPairLanguages('the-golden-rule',[...slugs,'the-golden-rule-ja']),null);
});
