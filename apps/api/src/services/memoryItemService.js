import { prisma } from '../lib/prisma.js';

export const MEMORY_CATEGORIES = ['safety', 'policy', 'content_style', 'ops', 'growth'];

export async function upsertMemoryItem(input) {
  const {
    scope,
    category,
    key,
    value,
    confidence = 0,
    source,
    expiresAt = null,
  } = input || {};

  if (!scope || typeof scope !== 'string') throw new Error('scope is required');
  if (!MEMORY_CATEGORIES.includes(category)) throw new Error('invalid category');
  if (!key || typeof key !== 'string') throw new Error('key is required');
  if (typeof value !== 'string' || value.length === 0) throw new Error('value is required');
  if (!source || typeof source !== 'string') throw new Error('source is required');

  const normalizedValue = value.length > 800 ? value.slice(0, 800) : value;

  return prisma.memoryItem.upsert({
    where: {
      scope_category_key: { scope, category, key },
    },
    create: {
      scope,
      category,
      key,
      value: normalizedValue,
      confidence,
      source,
      expiresAt,
    },
    update: {
      value: normalizedValue,
      confidence,
      source,
      expiresAt,
      updatedAt: new Date(),
    },
  });
}

export default {
  upsertMemoryItem,
  MEMORY_CATEGORIES,
};
