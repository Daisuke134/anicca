const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');

const {
  validateWriterArticle,
  publicPreview,
  publicManifestJson,
} = require('../writer-article-contract.js');

const sha = (value) => crypto.createHash('sha256').update(value, 'utf8').digest('hex');

function fixture(overrides = {}) {
  const preview = '# Preview\n\nA useful public explanation.';
  const paid = '## Paid evidence\n\nThe complete implementation and receipts.';
  return {
    slug: 'reader-useful-proof',
    run_id: '20260802-010000',
    artifact_id: '20260802-010000__self-owned__en',
    lang: 'en',
    title: 'A useful article readers can verify',
    source_sha256: sha(`${preview}\n\n${paid}`),
    preview_markdown: preview,
    preview_sha256: sha(preview),
    paid_markdown: paid,
    paid_sha256: sha(paid),
    access_model: 'both',
    ...overrides,
  };
}

test('valid contract exposes metadata and preview but never paid body', () => {
  const value = fixture({ internal_notes: 'never publish this operational note' });
  const valid = validateWriterArticle(value);
  const visible = publicPreview(valid);

  assert.equal(visible.slug, value.slug);
  assert.equal(visible.preview_markdown, value.preview_markdown);
  assert.equal(visible.paid_sha256, value.paid_sha256);
  assert.equal(Object.hasOwn(visible, 'paid_markdown'), false);
  assert.equal(Object.hasOwn(visible, 'internal_notes'), false);
  assert.equal(JSON.stringify(visible).includes('complete implementation'), false);
  assert.equal(JSON.stringify(visible).includes('operational note'), false);
});

test('contract rejects changed bytes, missing lineage, and unsupported values', () => {
  const invalid = [
    fixture({ preview_sha256: '0'.repeat(64) }),
    fixture({ paid_sha256: 'f'.repeat(64) }),
    fixture({ source_sha256: 'a'.repeat(64) }),
    fixture({ run_id: '' }),
    fixture({ artifact_id: '' }),
    fixture({ lang: 'fr' }),
    fixture({ access_model: 'free' }),
  ];
  for (const value of invalid) {
    assert.throws(() => validateWriterArticle(value));
  }
});

test('contract rejects copying the public preview into the paid body', () => {
  const preview = fixture().preview_markdown;
  const paid = `${preview}\n\nSecret appendix`;
  assert.throws(
    () => validateWriterArticle(fixture({
      paid_markdown: paid,
      paid_sha256: sha(paid),
      source_sha256: sha(`${preview}\n\n${paid}`),
    })),
    /paid body duplicates preview/,
  );
});

test('public manifest is script-safe and contains no paid body', () => {
  const value = fixture({
    title: 'A title </script><script>alert(1)</script>',
  });
  const manifest = publicManifestJson(value);

  assert.equal(manifest.includes('</script>'), false);
  assert.equal(manifest.includes(value.paid_markdown), false);
  assert.equal(manifest.includes(value.preview_sha256), true);
  assert.deepEqual(JSON.parse(manifest), publicPreview(value));
});
