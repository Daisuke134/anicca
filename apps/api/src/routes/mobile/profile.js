import express from 'express';
import { z } from 'zod';
import { getProfile, getProfileByUserId, upsertProfile } from '../../services/mobile/profileService.js';
import { classifyAndSave, deleteEstimate } from '../../services/userTypeService.js';
import baseLogger from '../../utils/logger.js';
import extractUserId from '../../middleware/extractUserId.js';
import { resolveProfileId } from '../../services/mobile/userIdResolver.js';

const router = express.Router();
const logger = baseLogger.withContext('MobileProfile');

// Validation schema
const timeComponentSchema = z.object({
  hour: z.number().int().min(0).max(23),
  minute: z.number().int().min(0).max(59)
});

const profileSchema = z.object({
  displayName: z.string().optional(),
  preferredLanguage: z.enum(['ja', 'en']).optional(),
  // Demographics (onboarding)
  acquisitionSource: z.string().optional(),
  gender: z.string().optional(),
  ageRange: z.string().optional(),
  sleepLocation: z.string().optional(),
  trainingFocus: z.array(z.string()).optional(),
  wakeLocation: z.string().optional(),
  wakeRoutines: z.array(z.string()).optional(),
  sleepRoutines: z.array(z.string()).optional(),
  trainingGoal: z.string().optional(),
  idealTraits: z.array(z.string()).optional(),
  problems: z.array(z.string()).optional(),
  // v0.3: new traits keys（旧キーは互換として残す）
  ideals: z.array(z.string()).optional(),
  struggles: z.array(z.string()).optional(),
  big5: z.object({
    O: z.number().optional(),
    C: z.number().optional(),
    E: z.number().optional(),
    A: z.number().optional(),
    N: z.number().optional(),
    summary: z.string().optional(),
    keyTraits: z.array(z.string()).optional()
  }).optional(),
  keywords: z.array(z.string()).optional(),
  summary: z.string().optional(),
  nudgeIntensity: z.enum(['quiet', 'normal', 'active']).optional(),
  stickyMode: z.boolean().optional(),
  // AlarmKit設定（各習慣ごと）
  useAlarmKitForWake: z.boolean().optional(),
  useAlarmKitForTraining: z.boolean().optional(),
  useAlarmKitForBedtime: z.boolean().optional(),
  useAlarmKitForCustom: z.boolean().optional(),
  // Stickyモード（全習慣共通）
  stickyModeEnabled: z.boolean().optional(),
  // 後方互換用
  wakeStickyModeEnabled: z.boolean().optional(),
  habitSchedules: z.record(timeComponentSchema).optional(),
  habitFollowupCounts: z.record(z.number().int()).optional(),
  customHabits: z.array(z.object({
    id: z.string(),
    name: z.string(),
    updatedAt: z.number().optional()
  })).optional(),
  customHabitSchedules: z.record(timeComponentSchema).optional(),
  customHabitFollowupCounts: z.record(z.number().int()).optional(),
  // v3: Data Integration状態をサーバ保存
  sensorAccess: z.object({
    screenTimeEnabled: z.boolean().optional(),
    sleepEnabled: z.boolean().optional(),
    stepsEnabled: z.boolean().optional(),
    motionEnabled: z.boolean().optional()
  }).optional()
});

/**
 * GET /mobile/profile
 * Get user profile by device ID
 */
router.get('/', async (req, res) => {
  const deviceId = (req.get('device-id') || '').toString().trim();
  const userId = await extractUserId(req, res);
  if (!userId) return;
  
  try {
    let profileData = await getProfileByUserId(userId);
    if (!profileData) {
      profileData = await getProfile(deviceId);
    }
    
    if (!profileData) {
      return res.json({
        displayName: '',
        preferredLanguage: 'en',
        sleepLocation: '',
        trainingFocus: [],
        wakeLocation: '',
        wakeRoutines: [],
        sleepRoutines: [],
        trainingGoal: '',
        idealTraits: [],
        problems: [],
        useAlarmKitForWake: false,
        useAlarmKitForTraining: false,
        useAlarmKitForBedtime: false,
        useAlarmKitForCustom: false,
        stickyModeEnabled: true,
        habitSchedules: {},
        habitFollowupCounts: {},
        customHabits: [],
        customHabitSchedules: {},
        customHabitFollowupCounts: {}
      });
    }
    
    const profile = profileData.profile || {};
    const preferredLanguage = profile.preferredLanguage ||
      profileData.language ||
      profileData.userSettingsLanguage ||
      'en';
    
    return res.json({
      displayName: profile.displayName || '',
      preferredLanguage,
      // Demographics
      acquisitionSource: profile.acquisitionSource || null,
      gender: profile.gender || null,
      ageRange: profile.ageRange || null,
      sleepLocation: profile.sleepLocation || '',
      trainingFocus: profile.trainingFocus || [],
      wakeLocation: profile.wakeLocation || '',
      wakeRoutines: profile.wakeRoutines || [],
      sleepRoutines: profile.sleepRoutines || [],
      trainingGoal: profile.trainingGoal || '',
      idealTraits: profile.idealTraits || [],
      problems: profile.problems || [],
      // v0.3: new fields (best-effort; profileService upserts to user_traits)
      ideals: profile.ideals || profile.idealTraits || [],
      struggles: profile.struggles || profile.problems || [],
      big5: profile.big5 || null,
      keywords: profile.keywords || [],
      summary: profile.summary || '',
      nudgeIntensity: profile.nudgeIntensity || 'normal',
      stickyMode: profile.stickyMode ?? profile.stickyModeEnabled ?? profile.wakeStickyModeEnabled ?? true,
      useAlarmKitForWake: profile.useAlarmKitForWake ?? false,
      useAlarmKitForTraining: profile.useAlarmKitForTraining ?? false,
      useAlarmKitForBedtime: profile.useAlarmKitForBedtime ?? false,
      useAlarmKitForCustom: profile.useAlarmKitForCustom ?? false,
      // 後方互換: stickyModeEnabled を優先、なければ wakeStickyModeEnabled を使用
      stickyModeEnabled: profile.stickyModeEnabled ?? profile.wakeStickyModeEnabled ?? true,
      habitSchedules: profile.habitSchedules || {},
      habitFollowupCounts: profile.habitFollowupCounts || {},
      customHabits: profile.customHabits || [],
      customHabitSchedules: profile.customHabitSchedules || {},
      customHabitFollowupCounts: profile.customHabitFollowupCounts || {},
      sensorAccess: profile.sensorAccess || null
    });
  } catch (error) {
    logger.error('Failed to get profile', error);
    return res.status(500).json({ error: { code: 'INTERNAL_ERROR', message: 'Failed to get profile' } });
  }
});

/**
 * PUT /mobile/profile
 * Upsert user profile
 */
router.put('/', async (req, res) => {
  const deviceId = (req.get('device-id') || '').toString().trim();
  const userId = await extractUserId(req, res);
  if (!userId) return;
  
  try {
    const validationResult = profileSchema.safeParse(req.body);
    
    if (!validationResult.success) {
      logger.warn('Invalid profile data', validationResult.error);
      return res.status(400).json({
        error: { code: 'INVALID_REQUEST', message: 'Invalid profile data', details: validationResult.error.errors }
      });
    }
    
    const profileData = validationResult.data;
    const language = profileData.preferredLanguage || 'en';
    
    await upsertProfile({
      deviceId,
      userId,
      profile: profileData,
      language
    });

    // 1.5.0: User type classification trigger (A6+A7)
    try {
      const struggles = profileData.struggles || profileData.problems || [];
      if (struggles.length > 0) {
        const profileId = (await resolveProfileId(userId)) || null;
        if (profileId) await classifyAndSave(profileId, struggles);
      } else {
        const profileId = (await resolveProfileId(userId)) || null;
        if (profileId) await deleteEstimate(profileId);
      }
    } catch (classifyError) {
      // Non-blocking: classification failure should not break profile upsert
      logger.warn('User type classification failed (non-blocking)', classifyError);
    }

    return res.json({ success: true });
  } catch (error) {
    logger.error('Failed to upsert profile', error);
    return res.status(500).json({ error: { code: 'INTERNAL_ERROR', message: 'Failed to upsert profile' } });
  }
});

export default router;
