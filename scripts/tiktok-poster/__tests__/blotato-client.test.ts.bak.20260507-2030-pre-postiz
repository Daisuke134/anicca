import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { BlotatoClient } from '../src/blotato-client.js';

describe('BlotatoClient', () => {
  // ─────────────────────────────────────────────
  // Dry-run tests
  // ─────────────────────────────────────────────
  it('uploadMedia dryRun returns a URL', async () => {
    const client = new BlotatoClient({ dryRun: true });
    const result = await client.uploadMedia('https://example.com/image.png');
    expect(result.url).toBeTruthy();
    expect(typeof result.url).toBe('string');
  });

  it('postPhoto dryRun returns postSubmissionId', async () => {
    const client = new BlotatoClient({ dryRun: true });
    const result = await client.postPhoto('account-1', 'https://cdn.example.com/img.jpg', 'Test caption');
    expect(result.postSubmissionId).toBeTruthy();
    expect(typeof result.postSubmissionId).toBe('string');
  });

  it('checkPostStatus dryRun returns null', async () => {
    const client = new BlotatoClient({ dryRun: true });
    expect(await client.checkPostStatus('post-123')).toBeNull();
  });

  it('throws without apiKey in real mode', () => {
    expect(() => new BlotatoClient()).toThrow('BLOTATO_API_KEY required');
  });

  // ─────────────────────────────────────────────
  // Fetch-mocked tests (non-dryRun API paths)
  // ─────────────────────────────────────────────
  let fetchMock: ReturnType<typeof vi.fn>;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    fetchMock = vi.fn();
    globalThis.fetch = fetchMock as unknown as typeof fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  function mockJsonResponse(body: unknown, status = 200): Response {
    return {
      ok: status >= 200 && status < 300,
      status,
      json: async () => body,
      text: async () => JSON.stringify(body),
    } as Response;
  }

  const API_KEY = 'test-blotato-key';

  it('uploadMedia succeeds and returns CDN URL', async () => {
    fetchMock.mockResolvedValueOnce(
      mockJsonResponse({ url: 'https://cdn.blotato.com/img123.jpg' }),
    );

    const client = new BlotatoClient({ apiKey: API_KEY });
    const result = await client.uploadMedia('https://example.com/image.png');

    expect(result.url).toBe('https://cdn.blotato.com/img123.jpg');
    expect(fetchMock).toHaveBeenCalledTimes(1);

    const call = fetchMock.mock.calls[0];
    expect(call[0]).toContain('/v2/media');
    expect(call[1].headers['blotato-api-key']).toBe(API_KEY);
    const body = JSON.parse(call[1].body as string);
    expect(body.url).toBe('https://example.com/image.png');
  });

  it('uploadMedia throws on HTTP error', async () => {
    fetchMock.mockResolvedValueOnce(mockJsonResponse({ error: 'bad' }, 500));

    const client = new BlotatoClient({ apiKey: API_KEY });
    await expect(client.uploadMedia('data')).rejects.toThrow(/media upload failed/);
  });

  it('uploadMedia throws when no URL returned', async () => {
    fetchMock.mockResolvedValueOnce(mockJsonResponse({}));

    const client = new BlotatoClient({ apiKey: API_KEY });
    await expect(client.uploadMedia('data')).rejects.toThrow(/no URL/);
  });

  it('postPhoto succeeds and returns postSubmissionId', async () => {
    fetchMock.mockResolvedValueOnce(
      mockJsonResponse({ postSubmissionId: 'post-sub-abc' }),
    );

    const client = new BlotatoClient({ apiKey: API_KEY });
    const result = await client.postPhoto('acct-1', 'https://cdn.example.com/img.jpg', 'my caption');

    expect(result.postSubmissionId).toBe('post-sub-abc');
    expect(fetchMock).toHaveBeenCalledTimes(1);

    const call = fetchMock.mock.calls[0];
    expect(call[0]).toContain('/v2/posts');
    const body = JSON.parse(call[1].body as string);
    expect(body.post.accountId).toBe('acct-1');
    expect(body.post.content.text).toBe('my caption');
    expect(body.post.content.mediaUrls).toEqual(['https://cdn.example.com/img.jpg']);
    expect(body.post.content.platform).toBe('tiktok');
  });

  it('postPhoto throws on HTTP error', async () => {
    fetchMock.mockResolvedValueOnce(mockJsonResponse({ error: 'forbidden' }, 403));

    const client = new BlotatoClient({ apiKey: API_KEY });
    await expect(client.postPhoto('acct-1', 'url', 'caption')).rejects.toThrow(/post failed/);
  });

  it('postPhoto throws when no ID returned', async () => {
    fetchMock.mockResolvedValueOnce(mockJsonResponse({ status: 'ok' }));

    const client = new BlotatoClient({ apiKey: API_KEY });
    await expect(client.postPhoto('acct-1', 'url', 'caption')).rejects.toThrow(/no ID/);
  });

  it('postPhoto falls back to id field when postSubmissionId missing', async () => {
    fetchMock.mockResolvedValueOnce(
      mockJsonResponse({ id: 'fallback-id-123' }),
    );

    const client = new BlotatoClient({ apiKey: API_KEY });
    const result = await client.postPhoto('acct-1', 'url', 'caption');
    expect(result.postSubmissionId).toBe('fallback-id-123');
  });

  it('postPhoto truncates caption to 2000 chars', async () => {
    fetchMock.mockResolvedValueOnce(
      mockJsonResponse({ postSubmissionId: 'post-trunc' }),
    );

    const longCaption = 'x'.repeat(3000);
    const client = new BlotatoClient({ apiKey: API_KEY });
    await client.postPhoto('acct-1', 'url', longCaption);

    const body = JSON.parse(fetchMock.mock.calls[0][1].body as string);
    expect(body.post.content.text.length).toBe(2000);
  });

  it('checkPostStatus returns published status', async () => {
    fetchMock.mockResolvedValueOnce(
      mockJsonResponse({ status: 'published', publicUrl: 'https://tiktok.com/abc' }),
    );

    const client = new BlotatoClient({ apiKey: API_KEY });
    const result = await client.checkPostStatus('post-123');

    expect(result).toEqual({ status: 'published', publicUrl: 'https://tiktok.com/abc' });
  });

  it('checkPostStatus returns null on HTTP error', async () => {
    fetchMock.mockResolvedValueOnce(mockJsonResponse({}, 500));

    const client = new BlotatoClient({ apiKey: API_KEY });
    const result = await client.checkPostStatus('post-123');
    expect(result).toBeNull();
  });

  it('checkPostStatus returns null when no status field', async () => {
    fetchMock.mockResolvedValueOnce(mockJsonResponse({ id: 'post-123' }));

    const client = new BlotatoClient({ apiKey: API_KEY });
    const result = await client.checkPostStatus('post-123');
    expect(result).toBeNull();
  });

  it('checkPostStatus returns null on network error', async () => {
    fetchMock.mockRejectedValueOnce(new Error('network failure'));

    const client = new BlotatoClient({ apiKey: API_KEY });
    const result = await client.checkPostStatus('post-123');
    expect(result).toBeNull();
  });
});
