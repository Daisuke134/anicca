import { beforeEach, describe, expect, it, vi } from 'vitest';

const queryMock = vi.fn();
const ensureDeviceProfileIdMock = vi.fn();
const resolveProfileIdMock = vi.fn();

vi.mock('../../../lib/db.js', () => ({
  query: (...args) => queryMock(...args),
}));

vi.mock('../userIdResolver.js', () => ({
  isUuid: (v) => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(String(v || '')),
  ensureDeviceProfileId: (...args) => ensureDeviceProfileIdMock(...args),
  resolveProfileId: (...args) => resolveProfileIdMock(...args),
}));

import { upsertProfile } from '../profileService.js';

describe('profileService.upsertProfile', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('continues successfully when user_traits upsert hits foreign key violation', async () => {
    const uuid = 'aaf185fc-b6e1-4e83-bb12-42e10acf686d';
    ensureDeviceProfileIdMock.mockResolvedValue(uuid);
    resolveProfileIdMock.mockResolvedValue(uuid);

    // 1) mobile_profiles upsert
    // 2) ensureProfileRow for user_settings
    // 3) user_settings upsert
    // 4) ensureProfileRow for traits
    // 5) user_traits upsert -> fk error (should be swallowed)
    queryMock
      .mockResolvedValueOnce({ rows: [] })
      .mockResolvedValueOnce({ rows: [] })
      .mockResolvedValueOnce({ rows: [] })
      .mockResolvedValueOnce({ rows: [] })
      .mockRejectedValueOnce({ code: '23503', message: 'fk violation' });

    const result = await upsertProfile({
      deviceId: 'AAF185FC-B6E1-4E83-BB12-42E10ACF686D',
      userId: 'AAF185FC-B6E1-4E83-BB12-42E10ACF686D',
      profile: { ideals: ['calm'] },
      language: 'ja',
    });

    expect(result).toEqual({ profileId: uuid });
  });
});

