import { describe, it, expect, vi, beforeEach } from 'vitest';
import request from 'supertest';
import express from 'express';

vi.mock('../../../middleware/requireInternalAuth.js', () => ({
  default: (req, res, next) => next(),
}));

const jobMocks = vi.hoisted(() => ({
  runMemoryCleanup: vi.fn(),
  runAutonomyCheck: vi.fn(),
  runSufferingDetectorJob: vi.fn(),
  runAppNudgeSenderJob: vi.fn(),
  runProactiveAppNudgeJob: vi.fn(),
  runMoltbookShadowMonitorJob: vi.fn(),
  runMoltbookPosterJob: vi.fn(),
  runProblemNudgeApnsSender: vi.fn(),
}));

vi.mock('../../../jobs/memoryCleanup.js', () => ({
  runMemoryCleanup: jobMocks.runMemoryCleanup,
}));
vi.mock('../../../jobs/autonomyCheck.js', () => ({
  runAutonomyCheck: jobMocks.runAutonomyCheck,
}));
vi.mock('../../../jobs/sufferingDetectorJob.js', () => ({
  runSufferingDetectorJob: jobMocks.runSufferingDetectorJob,
}));
vi.mock('../../../jobs/appNudgeSenderJob.js', () => ({
  runAppNudgeSenderJob: jobMocks.runAppNudgeSenderJob,
}));
vi.mock('../../../jobs/proactiveAppNudgeJob.js', () => ({
  runProactiveAppNudgeJob: jobMocks.runProactiveAppNudgeJob,
}));
vi.mock('../../../jobs/moltbookShadowMonitorJob.js', () => ({
  runMoltbookShadowMonitorJob: jobMocks.runMoltbookShadowMonitorJob,
}));
vi.mock('../../../jobs/moltbookPosterJob.js', () => ({
  runMoltbookPosterJob: jobMocks.runMoltbookPosterJob,
}));
vi.mock('../../../jobs/problemNudgeApnsSenderJob.js', () => ({
  runProblemNudgeApnsSender: jobMocks.runProblemNudgeApnsSender,
}));

import jobsRouter from '../jobs.js';

const app = express();
app.use(express.json());
app.use('/api/admin/jobs', jobsRouter);

describe('admin jobs routes', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('POST /memory-cleanup returns job result', async () => {
    jobMocks.runMemoryCleanup.mockResolvedValueOnce({ deletedExpired: 1 });
    const res = await request(app).post('/api/admin/jobs/memory-cleanup').send({});
    expect(res.status).toBe(200);
    expect(res.body.result.deletedExpired).toBe(1);
  });

  it('POST /autonomy-check returns job result', async () => {
    jobMocks.runAutonomyCheck.mockResolvedValueOnce({ pass: true });
    const res = await request(app).post('/api/admin/jobs/autonomy-check').send({});
    expect(res.status).toBe(200);
    expect(res.body.result.pass).toBe(true);
  });

  it('POST /suffering-detector passes optional feed override', async () => {
    jobMocks.runSufferingDetectorJob.mockResolvedValueOnce({ ok: true, feedCount: 1 });

    const res = await request(app)
      .post('/api/admin/jobs/suffering-detector')
      .send({
        feed: [
          {
            platform: 'moltbook',
            region: 'JP',
            externalPostId: 'synthetic-e2e',
            platformUserId: 'moltbook:synthetic',
            context: 'つらい',
            severityScore: 0.7,
          },
        ],
      });

    expect(res.status).toBe(200);
    expect(jobMocks.runSufferingDetectorJob).toHaveBeenCalledTimes(1);
    expect(jobMocks.runSufferingDetectorJob.mock.calls[0][0]).toMatchObject({
      feed: [{ externalPostId: 'synthetic-e2e' }],
    });
    expect(res.body.result.ok).toBe(true);
  });

  it('POST /proactive-app-nudge passes optional slot', async () => {
    jobMocks.runProactiveAppNudgeJob.mockResolvedValueOnce({ ok: true, slot: 'morning' });
    const res = await request(app).post('/api/admin/jobs/proactive-app-nudge').send({ slot: 'morning' });
    expect(res.status).toBe(200);
    expect(jobMocks.runProactiveAppNudgeJob).toHaveBeenCalledTimes(1);
    expect(jobMocks.runProactiveAppNudgeJob.mock.calls[0][0]).toMatchObject({ slot: 'morning' });
    expect(res.body.result.ok).toBe(true);
  });

  it('POST /moltbook-poster returns job result', async () => {
    jobMocks.runMoltbookPosterJob.mockResolvedValueOnce({ ok: true, externalPostId: 'moltbook-daily-2026-02-10' });
    const res = await request(app).post('/api/admin/jobs/moltbook-poster').send({});
    expect(res.status).toBe(200);
    expect(jobMocks.runMoltbookPosterJob).toHaveBeenCalledTimes(1);
    expect(res.body.result.ok).toBe(true);
  });

  it('POST /moltbook-poster with dry_run: true passes dryRun to job', async () => {
    jobMocks.runMoltbookPosterJob.mockResolvedValueOnce({ ok: true, dryRun: true, externalPostId: 'moltbook-daily-2026-02-11' });
    const res = await request(app).post('/api/admin/jobs/moltbook-poster').send({ dry_run: true });
    expect(res.status).toBe(200);
    expect(jobMocks.runMoltbookPosterJob).toHaveBeenCalledWith({ dryRun: true });
    expect(res.body.result.ok).toBe(true);
  });

  it('POST /problem-nudge-apns-sender returns job result', async () => {
    jobMocks.runProblemNudgeApnsSender.mockResolvedValueOnce({ ok: true, env: 'dev', queued: 1, sent: 1, failed: 0 });
    const res = await request(app).post('/api/admin/jobs/problem-nudge-apns-sender').send({ nowUtcIso: '2026-02-13T15:30:00.000Z' });
    expect(res.status).toBe(200);
    expect(jobMocks.runProblemNudgeApnsSender).toHaveBeenCalledTimes(1);
    expect(res.body.result.ok).toBe(true);
  });
});
