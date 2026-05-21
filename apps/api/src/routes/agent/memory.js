import { Router } from 'express';
import { z } from 'zod';
import { getMem0Client } from '../../modules/memory/mem0Client.js';

const router = Router();

const categories = ['profile', 'behavior_summary', 'interaction', 'nudge_meta'];

const memorizeSchema = z.object({
  userId: z.string().min(1).max(128),
  content: z.string().min(1).max(5000),
  category: z.enum(categories).default('interaction'),
  metadata: z.record(z.unknown()).optional(),
});

const retrieveSchema = z.object({
  userId: z.string().min(1).max(128),
  query: z.string().min(1).max(1000),
  topK: z.number().int().min(1).max(20).optional(),
  limit: z.number().int().min(1).max(20).optional(),
  mode: z.enum(['cag', 'rag', 'llm']).default('cag'),
});

function pickId(entry) {
  return entry?.id ?? entry?.memory_id ?? entry?.memoryId ?? null;
}

function pickContent(entry) {
  return entry?.memory ?? entry?.content ?? entry?.text ?? '';
}

function pickScore(entry) {
  const score = entry?.score ?? entry?.relevance ?? entry?.relevanceScore ?? null;
  return typeof score === 'number' ? score : 0;
}

function pickCategoryPath(entry) {
  return (
    entry?.categoryPath ||
    entry?.metadata?.categoryPath ||
    entry?.metadata?.category ||
    'uncategorized'
  );
}

function normalizeItems(rawItems) {
  return rawItems.map((entry) => ({
    id: pickId(entry),
    content: pickContent(entry),
    relevanceScore: pickScore(entry),
    categoryPath: pickCategoryPath(entry),
    metadata: entry?.metadata ?? {},
  }));
}

async function searchWithMode(mem0, { userId, query, limit, mode }) {
  if (mode === 'llm') {
    const llmResult = await mem0.search({ userId, query, topK: limit });
    const llmItems = Array.isArray(llmResult?.results) ? llmResult.results : [];
    return { items: llmItems, fallbackUsed: false, source: 'llm' };
  }

  if (mode === 'rag') {
    const ragResult = await mem0.search({ userId, query, topK: limit });
    const ragItems = Array.isArray(ragResult?.results) ? ragResult.results : [];
    return { items: ragItems, fallbackUsed: false, source: 'rag' };
  }

  const cagResult = await mem0.search({ userId, query, topK: limit });
  const cagItems = Array.isArray(cagResult?.results) ? cagResult.results : [];
  if (cagItems.length > 0) {
    return { items: cagItems, fallbackUsed: false, source: 'cag' };
  }

  const ragFallback = await mem0.search({ userId, query, topK: limit, rerank: true, includeVectors: false });
  const ragItems = Array.isArray(ragFallback?.results) ? ragFallback.results : [];
  if (ragItems.length > 0) {
    return { items: ragItems, fallbackUsed: true, source: 'rag' };
  }

  const llmFallback = await mem0.search({ userId, query, topK: limit });
  const llmItems = Array.isArray(llmFallback?.results) ? llmFallback.results : [];
  return { items: llmItems, fallbackUsed: true, source: 'llm' };
}

router.post('/memorize', async (req, res) => {
  const parsed = memorizeSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({
      error: 'Bad Request',
      issues: parsed.error.issues,
    });
  }

  try {
    const { userId, content, category, metadata = {} } = parsed.data;
    const mem0 = await getMem0Client();
    const payload = { userId, content, metadata };

    let result;
    if (category === 'profile') result = await mem0.addProfile(payload);
    else if (category === 'behavior_summary') result = await mem0.addBehaviorSummary(payload);
    else if (category === 'nudge_meta') result = await mem0.addNudgeMeta(payload);
    else result = await mem0.addInteraction(payload);

    const createdList = Array.isArray(result) ? result : [result];
    const created = createdList[0];
    const memoryId = pickId(created);
    return res.status(201).json({
      success: true,
      category,
      memoryId,
      resourceId: memoryId,
      itemsExtracted: createdList.filter(Boolean).length,
      categoriesUpdated: [],
    });
  } catch (error) {
    console.error('[Agent Memory] memorize error:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: 'Failed to store memory',
    });
  }
});

router.post('/retrieve', async (req, res) => {
  const parsed = retrieveSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({
      error: 'Bad Request',
      issues: parsed.error.issues,
    });
  }

  try {
    const { userId, query, mode } = parsed.data;
    const limit = parsed.data.limit ?? parsed.data.topK ?? 5;
    const mem0 = await getMem0Client();
    const searchResult = await searchWithMode(mem0, { userId, query, limit, mode });
    const items = normalizeItems(searchResult.items);

    return res.json({
      items,
      count: items.length,
      fallbackUsed: searchResult.fallbackUsed,
      source: searchResult.source,
    });
  } catch (error) {
    console.error('[Agent Memory] retrieve error:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: 'Failed to retrieve memory',
    });
  }
});

export default router;
