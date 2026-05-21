/**
 * 1.5.0 Cross-User Learning: User Type Classification Service
 *
 * Classifies users into 4 types based on their selected ProblemTypes:
 *   T1 (完璧主義), T2 (比較傾向), T3 (衝動型), T4 (不安型)
 *
 * Uses Prisma for CRUD, Raw SQL for generated column reads.
 */

import prisma from '../lib/prisma.js';
import baseLogger from '../utils/logger.js';

const logger = baseLogger.withContext('UserTypeService');

// Weight matrix: ProblemType × UserType
const WEIGHT_MATRIX = {
  self_loathing:      { T1: 3, T2: 2, T3: 0, T4: 1 },
  procrastination:    { T1: 3, T2: 0, T3: 1, T4: 1 },
  rumination:         { T1: 1, T2: 3, T3: 0, T4: 3 },
  staying_up_late:    { T1: 0, T2: 0, T3: 3, T4: 1 },
  porn_addiction:     { T1: 0, T2: 0, T3: 3, T4: 0 },
  anxiety:            { T1: 1, T2: 1, T3: 0, T4: 3 },
  cant_wake_up:       { T1: 1, T2: 0, T3: 2, T4: 1 },
  lying:              { T1: 0, T2: 1, T3: 2, T4: 1 },
  bad_mouthing:       { T1: 0, T2: 2, T3: 2, T4: 0 },
  alcohol_dependency: { T1: 0, T2: 1, T3: 3, T4: 1 },
  anger:              { T1: 1, T2: 1, T3: 3, T4: 0 },
  obsessive:          { T1: 2, T2: 0, T3: 0, T4: 2 },
  loneliness:         { T1: 0, T2: 2, T3: 0, T4: 2 },
};

// Type display names (API response)
export const TYPE_NAMES = {
  T1: '完璧主義',
  T2: '比較傾向',
  T3: '衝動型',
  T4: '不安型',
};

/**
 * Score-based user type classification.
 * @param {string[]} selectedProblems - Array of ProblemType keys
 * @returns {{ primaryType: string, scores: object, confidence: number }}
 */
export function classifyUserType(selectedProblems) {
  if (!selectedProblems || selectedProblems.length === 0) {
    return { primaryType: 'T4', scores: { T1: 0, T2: 0, T3: 0, T4: 0 }, confidence: 0 };
  }

  const scores = { T1: 0, T2: 0, T3: 0, T4: 0 };

  for (const problem of selectedProblems) {
    const weights = WEIGHT_MATRIX[problem];
    if (!weights) continue;
    for (const type of Object.keys(scores)) {
      scores[type] += weights[type] || 0;
    }
  }

  const totalScore = Object.values(scores).reduce((a, b) => a + b, 0);
  const primaryType = Object.entries(scores)
    .sort((a, b) => b[1] - a[1])[0][0];
  const confidence = totalScore > 0 ? scores[primaryType] / totalScore : 0;

  return { primaryType, scores, confidence };
}

/**
 * Classify and save (UPSERT) user type estimate.
 * Called on onboarding completion and profile update.
 * @param {string} userId - UUID
 * @param {string[]} problems - Array of ProblemType keys
 */
export async function classifyAndSave(userId, problems) {
  const result = classifyUserType(problems);

  if (result.confidence <= 0) {
    logger.info(`User ${userId}: confidence=0, skipping save`);
    return result;
  }

  // Verify profiles record exists before FK-dependent upsert (P2003 fix)
  const profileExists = await prisma.profile.findUnique({ where: { id: userId }, select: { id: true } });
  if (!profileExists) {
    logger.warn(`User ${userId}: profiles record not found, skipping user type estimate save`);
    return result;
  }

  try {
    await prisma.userTypeEstimate.upsert({
      where: { userId },
      create: {
        userId,
        primaryType: result.primaryType,
        typeScores: result.scores,
        confidence: result.confidence,
      },
      update: {
        primaryType: result.primaryType,
        typeScores: result.scores,
        confidence: result.confidence,
        updatedAt: new Date(),
      },
    });
  } catch (error) {
    // Belt-and-suspenders: handle race condition where profile is deleted between check and upsert
    if (error.code === 'P2003') {
      logger.warn(`User ${userId}: FK constraint failed during upsert (profile deleted concurrently), skipping`);
      return result;
    }
    throw error;
  }

  logger.info(`User ${userId}: classified as ${result.primaryType} (confidence: ${result.confidence.toFixed(4)})`);
  return result;
}

/**
 * Delete user type estimate (when problems are cleared).
 * @param {string} userId - UUID
 */
export async function deleteEstimate(userId) {
  try {
    await prisma.userTypeEstimate.delete({ where: { userId } });
    logger.info(`User ${userId}: user type estimate deleted`);
  } catch (error) {
    // P2025 = record not found (OK to ignore)
    if (error.code === 'P2025') {
      logger.info(`User ${userId}: no estimate to delete`);
      return;
    }
    throw error;
  }
}

/**
 * Get user type for API response (4-case logic per db-schema-spec Section 4).
 * @param {string} userId - UUID
 * @returns {object|null} - null means profile not found (404)
 */
export async function getUserType(userId) {
  // 1. Check existing estimate
  const existing = await prisma.userTypeEstimate.findUnique({ where: { userId } });
  if (existing) {
    return formatApiResponse(existing, existing.updatedAt);
  }

  // 2. Check profile exists
  const profile = await prisma.profile.findUnique({ where: { id: userId } });
  if (!profile) {
    return null; // Case 0: profile not found → 404
  }

  // 3. Get problems from mobile_profiles (same pattern as generateNudges.js)
  const mpResult = await prisma.$queryRaw`
    SELECT COALESCE(
      profile->'struggles',
      profile->'problems',
      '[]'::jsonb
    ) as problems
    FROM mobile_profiles
    WHERE user_id = ${userId}::uuid
    LIMIT 1
  `;

  const problems = mpResult.length > 0
    ? (Array.isArray(mpResult[0].problems) ? mpResult[0].problems : JSON.parse(mpResult[0].problems || '[]'))
    : [];

  if (problems.length === 0) {
    // Case 3: empty problems → return default T4/0 (don't save)
    return formatApiResponse(
      { primaryType: 'T4', confidence: 0, scores: { T1: 0, T2: 0, T3: 0, T4: 0 } },
      new Date()
    );
  }

  // Case 2: compute on-the-fly → UPSERT → return
  const result = await classifyAndSave(userId, problems);
  return formatApiResponse(result, new Date());
}

/**
 * Format DB/computed data to API response shape.
 */
function formatApiResponse(data, updatedAt) {
  return {
    primaryType: data.primaryType,
    typeName: TYPE_NAMES[data.primaryType] || data.primaryType,
    confidence: Number(data.confidence),
    scores: data.typeScores || data.scores,
    lastUpdated: updatedAt,
  };
}
