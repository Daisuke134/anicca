import { beforeEach, describe, expect, it, vi } from 'vitest';

const queryMock = vi.fn();

vi.mock('../../../lib/db.js', () => ({
  query: (...args) => queryMock(...args),
}));

import { ensureDeviceProfileId, isUuid, resolveProfileId } from '../userIdResolver.js';

describe('userIdResolver', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('resolveProfileId returns null for orphan uuid (no profiles/mobile mapping)', async () => {
    const incomingUuid = 'aaf185fc-b6e1-4e83-bb12-42e10acf686d';

    queryMock
      .mockResolvedValueOnce({ rows: [] }) // profiles by uuid
      .mockResolvedValueOnce({ rows: [] }) // profiles.metadata.apple_user_id
      .mockResolvedValueOnce({ rows: [] }); // mobile_profiles.device_id

    const result = await resolveProfileId(incomingUuid);
    expect(result).toBeNull();
  });

  it('ensureDeviceProfileId inserts metadata with explicit text cast', async () => {
    queryMock
      .mockResolvedValueOnce({ rows: [] }) // mobile_profiles lookup
      .mockResolvedValueOnce({ rows: [] }) // profiles insert
      .mockResolvedValueOnce({ rows: [] }); // mobile_profiles upsert

    const result = await ensureDeviceProfileId('DEVICE-ID-1');
    expect(isUuid(result)).toBe(true);

    const profileInsertCall = queryMock.mock.calls.find(([sql]) => sql.includes('jsonb_build_object'));
    expect(profileInsertCall).toBeTruthy();
    expect(profileInsertCall[0]).toContain('$2::text');
  });
});
