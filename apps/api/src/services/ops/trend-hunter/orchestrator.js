/**
 * orchestrator — Main trend-hunter pipeline
 * collect → filter → generate → deduplicate → save
 */
import { selectRotationGroup } from './rotationSelector.js';
import { buildQuery } from './queryBuilder.js';
import { parseTwitterResponse } from './twitterResponseParser.js';
import { parseRedditResponse } from './redditResponseParser.js';
import { parseTikTokResponse } from './tiktokResponseParser.js';
import { filterByVirality } from './viralityFilter.js';
import { jaccardBigram } from './textSimilarity.js';
import { formatSlackMessage } from './slackFormatter.js';
import {
  VIRALITY_THRESHOLDS,
  SIMILARITY_THRESHOLD,
  WARMUP_THRESHOLD,
  ROTATION_GROUPS,
} from './config.js';

/**
 * Run the trend-hunter pipeline.
 *
 * @param {OrchestratorConfig} config
 * @returns {Promise<ExecutionResult>}
 */
export async function runTrendHunter(config) {
  const startTime = Date.now();
  const errors = [];

  // Step 0: Determine target ProblemTypes
  const targetTypes = config.targetTypes || selectRotationGroup(config.executionCount);

  // Step 1: Collect trends from all enabled sources
  const allTrends = [];
  const sourceCounts = { x: 0, reddit: 0, tiktok: 0, github: 0 };

  // Collect in parallel
  const collectors = [];

  if (config.enabledSources.x) {
    collectors.push(
      collectFromTwitter(config.clients.twitter, targetTypes, config)
        .then(trends => {
          allTrends.push(...trends);
          sourceCounts.x = trends.length;
        })
        .catch(err => {
          errors.push({ source: 'x', error: err.message });
        })
    );
  }

  if (config.enabledSources.reddit) {
    collectors.push(
      collectFromReddit(config.clients.reddit, targetTypes, config)
        .then(trends => {
          allTrends.push(...trends);
          sourceCounts.reddit = trends.length;
        })
        .catch(err => {
          errors.push({ source: 'reddit', error: err.message });
        })
    );
  }

  if (config.enabledSources.tiktok) {
    collectors.push(
      collectFromTikTok(config.clients.tiktok, config)
        .then(trends => {
          allTrends.push(...trends);
          sourceCounts.tiktok = trends.length;
        })
        .catch(err => {
          errors.push({ source: 'tiktok', error: err.message });
        })
    );
  }

  await Promise.all(collectors);

  const scannedCount = allTrends.length;

  // If no trends at all, return early
  if (scannedCount === 0) {
    return {
      scannedCount: 0,
      filteredCount: 0,
      savedCount: 0,
      skippedDuplicates: 0,
      errors,
      targetTypes,
      duration: Date.now() - startTime,
      events: [],
    };
  }

  // Step 1.5: Apply virality filter
  const viralTrends = filterByVirality(allTrends, VIRALITY_THRESHOLDS);

  // Step 2: LLM Filter with fallback
  let filteredTrends = [];
  if (viralTrends.length > 0) {
    filteredTrends = await callLlmFilterWithFallback(
      config.clients.llm,
      viralTrends,
      config.llmChain
    ).catch(err => {
      errors.push({ source: 'llm_filter', error: err.message });
      return [];
    });
  }

  const filteredCount = filteredTrends.length;

  // Step 3: Generate hooks from filtered trends
  let hookCandidates = [];
  if (filteredTrends.length > 0) {
    hookCandidates = await callLlmGenerateWithFallback(
      config.clients.llm,
      filteredTrends,
      config.llmChain
    ).catch(err => {
      errors.push({ source: 'llm_generate', error: err.message });
      return [];
    });
  }

  // Step 4: Deduplicate and save
  let savedCount = 0;
  let skippedDuplicates = 0;
  const events = [];
  const threshold = config.similarityThreshold ?? SIMILARITY_THRESHOLD;

  if (hookCandidates.length > 0) {
    // Get existing hooks for duplicate check
    let existingHooks = [];
    try {
      const hooksResponse = await config.clients.railway.getHooks();
      existingHooks = hooksResponse.hooks || [];
    } catch (err) {
      errors.push({ source: 'railway_get', error: err.message });
    }

    for (const candidate of hookCandidates) {
      // Local duplicate check via Jaccard
      const isLocalDuplicate = existingHooks.some(
        h => jaccardBigram(candidate.content, h.text) >= threshold
      );

      if (isLocalDuplicate) {
        skippedDuplicates++;
        continue;
      }

      // Save to Railway API
      try {
        const saveResult = await config.clients.railway.saveHook({
          text: candidate.content,
          targetProblemTypes: candidate.problemTypes,
          source: 'trend-hunter',
          platform: candidate.platform || 'both',
          contentType: candidate.contentType,
          metadata: {
            trendSource: candidate.trendSource,
            angle: candidate.angle,
          },
        });

        if (saveResult.status === 'created') {
          savedCount++;
          events.push({
            source: 'trend-hunter',
            kind: 'hook_saved',
            tags: ['hook_candidate', 'found'],
            payload: {
              hookId: saveResult.id,
              hookType: candidate.contentType,
              targetTypes: candidate.problemTypes,
            },
          });
        } else if (saveResult.status === 'duplicate') {
          skippedDuplicates++;
        }
      } catch (err) {
        errors.push({ source: 'railway_save', error: err.message });
      }
    }
  }

  // Summary event
  const empathyCount = hookCandidates.filter(h => h.contentType === 'empathy').length;
  const solutionCount = hookCandidates.filter(h => h.contentType === 'solution').length;

  if (errors.length < 3) {
    events.push({
      source: 'trend-hunter',
      kind: 'scan_completed',
      tags: ['scan', 'completed'],
      payload: {
        savedCount,
        empathyCount,
        solutionCount,
        targetTypes,
      },
    });
  } else {
    events.push({
      source: 'trend-hunter',
      kind: 'scan_failed',
      tags: ['scan', 'failed', 'alert'],
      payload: { errors },
    });
  }

  return {
    scannedCount,
    filteredCount,
    savedCount,
    skippedDuplicates,
    errors,
    targetTypes,
    duration: Date.now() - startTime,
    events,
  };
}

async function collectFromTwitter(client, targetTypes, config) {
  const trends = [];
  for (const problemType of targetTypes) {
    for (const contentType of ['empathy', 'solution']) {
      for (const lang of ['en', 'ja']) {
        const query = buildQuery(problemType, contentType, lang);
        const raw = await client.search(query);
        const parsed = parseTwitterResponse(raw, {
          problemType,
          type: contentType,
          lang,
        });
        trends.push(...parsed);
      }
    }
  }
  return trends;
}

async function collectFromReddit(client, targetTypes, config) {
  const trends = [];
  for (const problemType of targetTypes) {
    for (const contentType of ['empathy', 'solution']) {
      const query = buildQuery(problemType, contentType, 'en');
      const raw = await client.semanticSearch(query);
      const parsed = parseRedditResponse(raw, {
        problemType,
        type: contentType,
        minScore: 100,
      });
      trends.push(...parsed);
    }
  }
  // Also get trending topics
  try {
    const trendingRaw = await client.getTrends();
    // trending data is supplementary, not parsed into NormalizedTrend
  } catch {
    // non-critical, ignore
  }
  return trends;
}

async function collectFromTikTok(client, config) {
  const raw = await client.fetchTrends();
  return parseTikTokResponse(raw);
}

async function callLlmFilterWithFallback(llmClient, trends, chain) {
  let lastError;
  for (const modelConfig of chain) {
    try {
      return await llmClient.filter(trends, modelConfig);
    } catch (err) {
      lastError = err;
      continue;
    }
  }
  throw lastError || new Error('All LLM models failed for filter');
}

async function callLlmGenerateWithFallback(llmClient, filteredTrends, chain) {
  let lastError;
  for (const modelConfig of chain) {
    try {
      return await llmClient.generateHooks(filteredTrends, modelConfig);
    } catch (err) {
      lastError = err;
      continue;
    }
  }
  throw lastError || new Error('All LLM models failed for hook generation');
}
