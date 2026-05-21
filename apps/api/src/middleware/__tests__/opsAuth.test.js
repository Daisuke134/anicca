import { describe, it, expect, vi, beforeEach } from 'vitest';

// T26, T27: opsAuth middleware tests
describe('opsAuth', () => {
  const VALID_TOKEN = 'test-agent-token';
  let opsAuth;

  beforeEach(async () => {
    process.env.ANICCA_AGENT_TOKEN = VALID_TOKEN;
    // Re-import to pick up env change
    const mod = await import('../opsAuth.js');
    opsAuth = mod.opsAuth;
  });

  const mockRes = () => {
    const res = {};
    res.status = vi.fn().mockReturnValue(res);
    res.json = vi.fn().mockReturnValue(res);
    return res;
  };

  // T26: reject when no token
  it('T26: rejects request with no Authorization header', () => {
    const req = { headers: {} };
    const res = mockRes();
    const next = vi.fn();

    opsAuth(req, res, next);

    expect(res.status).toHaveBeenCalledWith(401);
    expect(res.json).toHaveBeenCalledWith({ error: 'Unauthorized' });
    expect(next).not.toHaveBeenCalled();
  });

  // T27: reject with bad token
  it('T27: rejects request with invalid token', () => {
    const req = { headers: { authorization: 'Bearer invalid-token' } };
    const res = mockRes();
    const next = vi.fn();

    opsAuth(req, res, next);

    expect(res.status).toHaveBeenCalledWith(401);
    expect(next).not.toHaveBeenCalled();
  });

  it('allows request with valid token', () => {
    const req = { headers: { authorization: `Bearer ${VALID_TOKEN}` } };
    const res = mockRes();
    const next = vi.fn();

    opsAuth(req, res, next);

    expect(next).toHaveBeenCalled();
    expect(res.status).not.toHaveBeenCalled();
  });
});
