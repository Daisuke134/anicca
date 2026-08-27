import test from 'node:test';
import assert from 'node:assert/strict';

import { the402ServiceProfile } from '../lib/the402-service-profiles.mjs';

test('selects the evergreen HTTP 402 explainer contract without research-brief leakage', () => {
  const profile = the402ServiceProfile('svc_explainer', {
    researchServiceId: 'svc_research',
    explainerServiceId: 'svc_explainer',
  });

  assert.equal(profile.kind, 'http402_explainer');
  assert.equal(profile.minWords, 600);
  assert.equal(profile.maxWords, 900);
  assert.match(profile.instructions, /exactly four .*sections/i);
  assert.match(profile.instructions, /no specific companies, products, current events/i);
  assert.doesNotMatch(profile.instructions, /3[–-]5 concrete examples|12 months/i);
  assert.deepEqual(profile.sources.map(({ url }) => url), [
    'https://www.rfc-editor.org/rfc/rfc9110.html#section-15.5.3',
    'https://www.rfc-editor.org/rfc/rfc7231#section-6.5.2',
    'https://www.iana.org/assignments/http-status-codes/http-status-codes.xhtml',
  ]);
});
