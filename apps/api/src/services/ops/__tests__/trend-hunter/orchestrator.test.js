import { describe, it, expect, vi, beforeEach } from 'vitest';
import { runTrendHunter } from '../../trend-hunter/orchestrator.js';

// Mock all external dependencies
const mockTwitterClient = {
  search: vi.fn(),
};
const mockRedditClient = {
  semanticSearch: vi.fn(),
  getTrends: vi.fn(),
};
const mockTiktokClient = {
  fetchTrends: vi.fn(),
};
const mockLlmClient = {
  filter: vi.fn(),
  generateHooks: vi.fn(),
};
const mockRailwayClient = {
  getHooks: vi.fn(),
  saveHook: vi.fn(),
};

function makeConfig(overrides = {}) {
  return {
    executionCount: 0,
    enabledSources: { x: true, tiktok: true, reddit: true, github: false },
    llmChain: [{ model: 'gpt-4o', timeout: 30000 }],
    dryRun: false,
    similarityThreshold: 0.7,
    clients: {
      twitter: mockTwitterClient,
      reddit: mockRedditClient,
      tiktok: mockTiktokClient,
      llm: mockLlmClient,
      railway: mockRailwayClient,
    },
    ...overrides,
  };
}

function makeTweet(id, text, likes = 5000) {
  return {
    id,
    text,
    likeCount: likes,
    retweetCount: 100,
    replyCount: 50,
    author: { userName: 'user' },
  };
}

describe('orchestrator', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  // #34
  it('happy path: collects, filters, generates, and saves hooks', async () => {
    mockTwitterClient.search.mockResolvedValue(
      JSON.stringify({
        tweets: [makeTweet('1', '夜更かしがやめられない', 50000)],
      })
    );
    mockRedditClient.semanticSearch.mockResolvedValue(
      JSON.stringify({
        success: true,
        data: {
          results: [{
            id: 'r1',
            title: 'Cannot stop staying up',
            content: 'text',
            subreddit: 'r/selfimprovement',
            upvotes: 5000,
            comments: 100,
            url: 'https://reddit.com/r/test/r1',
          }],
        },
      })
    );
    mockRedditClient.getTrends.mockResolvedValue(
      JSON.stringify({ success: true, data: { trends: [] } })
    );
    mockTiktokClient.fetchTrends.mockResolvedValue(
      JSON.stringify([{
        id: 't1',
        name: '#sleepschedule',
        viewCount: 15000000,
        isPromoted: false,
        countryCode: 'JP',
        rank: 10,
        industryName: 'Education',
      }])
    );
    mockLlmClient.filter.mockResolvedValue([
      {
        trend_id: '1',
        relevance_score: 9,
        virality: 'high',
        content_type: 'empathy',
        problemTypes: ['staying_up_late'],
        angle: 'test angle',
        skip_reason: null,
      },
    ]);
    mockLlmClient.generateHooks.mockResolvedValue([
      {
        content: '毎晩同じ約束をして、毎晩破る。',
        contentType: 'empathy',
        problemTypes: ['staying_up_late'],
        platform: 'x',
        trendSource: { platform: 'x', url: null, hashtags: [], metrics: {} },
        angle: 'test',
      },
    ]);
    mockRailwayClient.getHooks.mockResolvedValue({ hooks: [] });
    mockRailwayClient.saveHook.mockResolvedValue({
      status: 'created',
      id: 'hook_001',
      text: '毎晩同じ約束をして、毎晩破る。',
      createdAt: '2026-02-08T05:00:00Z',
    });

    const result = await runTrendHunter(makeConfig());

    expect(result.savedCount).toBeGreaterThanOrEqual(1);
    expect(result.errors).toHaveLength(0);
    expect(mockRailwayClient.saveHook).toHaveBeenCalled();
  });

  // #35
  it('continues with other sources when Twitter is down', async () => {
    mockTwitterClient.search.mockRejectedValue(new Error('Twitter API down'));
    mockRedditClient.semanticSearch.mockResolvedValue(
      JSON.stringify({
        success: true,
        data: {
          results: [{
            id: 'r1',
            title: 'test',
            content: 'text',
            subreddit: 'r/test',
            upvotes: 500,
            comments: 10,
            url: 'https://reddit.com/r/test/r1',
          }],
        },
      })
    );
    mockRedditClient.getTrends.mockResolvedValue(
      JSON.stringify({ success: true, data: { trends: [] } })
    );
    mockTiktokClient.fetchTrends.mockResolvedValue(JSON.stringify([]));
    mockLlmClient.filter.mockResolvedValue([]);
    mockLlmClient.generateHooks.mockResolvedValue([]);
    mockRailwayClient.getHooks.mockResolvedValue({ hooks: [] });

    const result = await runTrendHunter(makeConfig());

    expect(result.errors).toHaveLength(1);
    expect(result.errors[0].source).toBe('x');
  });

  // #36
  it('reports all errors when all sources are down', async () => {
    mockTwitterClient.search.mockRejectedValue(new Error('Twitter down'));
    mockRedditClient.semanticSearch.mockRejectedValue(new Error('Reddit down'));
    mockRedditClient.getTrends.mockRejectedValue(new Error('Reddit trends down'));
    mockTiktokClient.fetchTrends.mockRejectedValue(new Error('TikTok down'));

    const result = await runTrendHunter(makeConfig());

    expect(result.errors.length).toBeGreaterThanOrEqual(3);
    expect(result.savedCount).toBe(0);
    expect(result.scannedCount).toBe(0);
  });

  // #37
  it('falls back to secondary LLM model on failure', async () => {
    mockTwitterClient.search.mockResolvedValue(
      JSON.stringify({ tweets: [makeTweet('1', 'test tweet', 5000)] })
    );
    mockRedditClient.semanticSearch.mockResolvedValue(
      JSON.stringify({ success: true, data: { results: [] } })
    );
    mockRedditClient.getTrends.mockResolvedValue(
      JSON.stringify({ success: true, data: { trends: [] } })
    );
    mockTiktokClient.fetchTrends.mockResolvedValue(JSON.stringify([]));
    mockRailwayClient.getHooks.mockResolvedValue({ hooks: [] });

    // First call fails, second succeeds
    mockLlmClient.filter
      .mockRejectedValueOnce(new Error('gpt-4o timeout'))
      .mockResolvedValueOnce([]);
    mockLlmClient.generateHooks.mockResolvedValue([]);

    const config = makeConfig({
      llmChain: [
        { model: 'gpt-4o', timeout: 30000 },
        { model: 'gpt-4o-mini', timeout: 20000 },
      ],
    });
    const result = await runTrendHunter(config);

    // Should not crash, should continue with fallback
    expect(result).toBeDefined();
  });

  // #38
  it('skips duplicate hooks', async () => {
    mockTwitterClient.search.mockResolvedValue(
      JSON.stringify({ tweets: [makeTweet('1', '夜更かしテスト投稿', 50000)] })
    );
    mockRedditClient.semanticSearch.mockResolvedValue(
      JSON.stringify({ success: true, data: { results: [] } })
    );
    mockRedditClient.getTrends.mockResolvedValue(
      JSON.stringify({ success: true, data: { trends: [] } })
    );
    mockTiktokClient.fetchTrends.mockResolvedValue(JSON.stringify([]));
    mockLlmClient.filter.mockResolvedValue([
      {
        trend_id: '1',
        relevance_score: 9,
        virality: 'high',
        content_type: 'empathy',
        problemTypes: ['staying_up_late'],
        angle: 'test',
        skip_reason: null,
      },
    ]);
    mockLlmClient.generateHooks.mockResolvedValue([
      {
        content: '毎晩同じ約束をして、毎晩破る。6年間ずっとこれ。',
        contentType: 'empathy',
        problemTypes: ['staying_up_late'],
        platform: 'x',
        trendSource: { platform: 'x', url: null, hashtags: [], metrics: {} },
        angle: 'test',
      },
    ]);
    // Existing hook with very similar text
    mockRailwayClient.getHooks.mockResolvedValue({
      hooks: [{
        id: 'existing_001',
        text: '毎晩同じ約束をして、毎晩破る。6年間ずっとこれだ。',
        targetProblemTypes: ['staying_up_late'],
        source: 'trend-hunter',
        xSampleSize: 0,
        xEngagementRate: 0,
      }],
    });

    const result = await runTrendHunter(makeConfig());

    expect(result.skippedDuplicates).toBeGreaterThanOrEqual(1);
    expect(mockRailwayClient.saveHook).not.toHaveBeenCalled();
  });

  // #39
  it('handles Railway API save failure gracefully', async () => {
    mockTwitterClient.search.mockResolvedValue(
      JSON.stringify({ tweets: [makeTweet('1', 'test', 50000)] })
    );
    mockRedditClient.semanticSearch.mockResolvedValue(
      JSON.stringify({ success: true, data: { results: [] } })
    );
    mockRedditClient.getTrends.mockResolvedValue(
      JSON.stringify({ success: true, data: { trends: [] } })
    );
    mockTiktokClient.fetchTrends.mockResolvedValue(JSON.stringify([]));
    mockLlmClient.filter.mockResolvedValue([
      {
        trend_id: '1',
        relevance_score: 9,
        virality: 'high',
        content_type: 'empathy',
        problemTypes: ['staying_up_late'],
        angle: 'test',
        skip_reason: null,
      },
    ]);
    mockLlmClient.generateHooks.mockResolvedValue([
      {
        content: 'unique hook content xyz',
        contentType: 'empathy',
        problemTypes: ['staying_up_late'],
        platform: 'x',
        trendSource: { platform: 'x', url: null, hashtags: [], metrics: {} },
        angle: 'test',
      },
    ]);
    mockRailwayClient.getHooks.mockResolvedValue({ hooks: [] });
    mockRailwayClient.saveHook.mockRejectedValue(new Error('500 Internal Server Error'));

    const result = await runTrendHunter(makeConfig());

    // Should not crash, should record error
    expect(result.savedCount).toBe(0);
    expect(result.errors.length).toBeGreaterThanOrEqual(1);
  });

  // #40
  it('rotates ProblemType groups based on executionCount', async () => {
    // Just verify the orchestrator selects the right group
    mockTwitterClient.search.mockResolvedValue(JSON.stringify({ tweets: [] }));
    mockRedditClient.semanticSearch.mockResolvedValue(
      JSON.stringify({ success: true, data: { results: [] } })
    );
    mockRedditClient.getTrends.mockResolvedValue(
      JSON.stringify({ success: true, data: { trends: [] } })
    );
    mockTiktokClient.fetchTrends.mockResolvedValue(JSON.stringify([]));
    mockLlmClient.filter.mockResolvedValue([]);
    mockLlmClient.generateHooks.mockResolvedValue([]);
    mockRailwayClient.getHooks.mockResolvedValue({ hooks: [] });

    const result0 = await runTrendHunter(makeConfig({ executionCount: 0 }));
    const result1 = await runTrendHunter(makeConfig({ executionCount: 1 }));
    const result2 = await runTrendHunter(makeConfig({ executionCount: 2 }));

    // Each should process different target types
    expect(result0.targetTypes).not.toEqual(result1.targetTypes);
    expect(result1.targetTypes).not.toEqual(result2.targetTypes);
  });

  // #41
  it('handles server-side duplicate response', async () => {
    mockTwitterClient.search.mockResolvedValue(
      JSON.stringify({ tweets: [makeTweet('1', 'unique text for test', 50000)] })
    );
    mockRedditClient.semanticSearch.mockResolvedValue(
      JSON.stringify({ success: true, data: { results: [] } })
    );
    mockRedditClient.getTrends.mockResolvedValue(
      JSON.stringify({ success: true, data: { trends: [] } })
    );
    mockTiktokClient.fetchTrends.mockResolvedValue(JSON.stringify([]));
    mockLlmClient.filter.mockResolvedValue([
      {
        trend_id: '1',
        relevance_score: 9,
        virality: 'high',
        content_type: 'empathy',
        problemTypes: ['staying_up_late'],
        angle: 'test',
        skip_reason: null,
      },
    ]);
    mockLlmClient.generateHooks.mockResolvedValue([
      {
        content: 'completely new hook text here',
        contentType: 'empathy',
        problemTypes: ['staying_up_late'],
        platform: 'x',
        trendSource: { platform: 'x', url: null, hashtags: [], metrics: {} },
        angle: 'test',
      },
    ]);
    mockRailwayClient.getHooks.mockResolvedValue({ hooks: [] });
    mockRailwayClient.saveHook.mockResolvedValue({
      status: 'duplicate',
      existingId: 'hook_existing_001',
    });

    const result = await runTrendHunter(makeConfig());

    expect(result.savedCount).toBe(0);
    expect(result.skippedDuplicates).toBeGreaterThanOrEqual(1);
  });
});
