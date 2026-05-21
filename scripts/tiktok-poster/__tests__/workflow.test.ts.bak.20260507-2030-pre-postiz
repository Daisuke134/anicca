import { describe, it, expect, beforeAll } from 'vitest';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { parse as parseYaml } from 'yaml';

const WORKFLOW_PATH = resolve(
  import.meta.dirname ?? '.',
  '../../../.github/workflows/tiktok-card-post.yml',
);

let yaml: string;
let parsed: Record<string, unknown>;

beforeAll(async () => {
  yaml = await readFile(WORKFLOW_PATH, 'utf-8');
  parsed = parseYaml(yaml) as Record<string, unknown>;
});

describe('Workflow YAML static verification', () => {
  // ─────────────────────────────────────────────
  // Test #13: four cron entries (2 JA + 2 EN)
  // ─────────────────────────────────────────────
  it('test_workflow_has_four_cron_entries', () => {
    const cronMatches = yaml.match(/- cron:/g);
    expect(cronMatches).toHaveLength(4);
  });

  // ─────────────────────────────────────────────
  // Test: correct cron times
  // ─────────────────────────────────────────────
  it('test_cron_times_match_spec', () => {
    // JA朝: 09:00 JST = 00:00 UTC
    expect(yaml).toContain("'0 0 * * *'");
    // JA夜: 19:00 JST = 10:00 UTC
    expect(yaml).toContain("'0 10 * * *'");
    // EN朝: 14:00 UTC
    expect(yaml).toContain("'0 14 * * *'");
    // EN夜: 01:00 UTC
    expect(yaml).toContain("'0 1 * * *'");
  });

  // ─────────────────────────────────────────────
  // Test #14: language resolution (schedule vs dispatch)
  // ─────────────────────────────────────────────
  it('test_language_resolution_schedule_and_dispatch', () => {
    expect(yaml).toContain('github.event.inputs.language');
    // JA crons (0 0 and 0 10) resolve to ja
    expect(yaml).toContain('0 0 * * *');
    expect(yaml).toContain('0 10 * * *');
    expect(yaml).toMatch(/value=ja/);
    // EN (fallback else) resolves to en
    expect(yaml).toMatch(/value=en/);
  });

  // ─────────────────────────────────────────────
  // Test #15: workflow_dispatch manual run
  // ─────────────────────────────────────────────
  it('test_workflow_dispatch_manual_run', () => {
    expect(yaml).toContain('workflow_dispatch:');
    expect(yaml).toContain('type: choice');
    expect(yaml).toContain('- en');
    expect(yaml).toContain('- ja');
  });

  // ─────────────────────────────────────────────
  // Test #16: tracker commit on success AND rollback on failure
  // ─────────────────────────────────────────────
  it('test_tracker_commit_on_success_and_rollback_on_failure', () => {
    expect(yaml).toContain("if: always()");
    const commitMatches = yaml.match(/git commit -m/g);
    expect(commitMatches!.length).toBeGreaterThanOrEqual(2);
  });

  // ─────────────────────────────────────────────
  // Test #18: Blotato API key masking
  // ─────────────────────────────────────────────
  it('test_workflow_has_mask_step_for_blotato', () => {
    expect(yaml).toContain('::add-mask::');
    expect(yaml).toContain('BLOTATO_API_KEY');
  });

  // ─────────────────────────────────────────────
  // Test: no TikTok OAuth secrets
  // ─────────────────────────────────────────────
  it('test_no_tiktok_oauth_secrets', () => {
    expect(yaml).not.toContain('TIKTOK_CLIENT_ID');
    expect(yaml).not.toContain('TIKTOK_CLIENT_SECRET');
    expect(yaml).not.toContain('TIKTOK_REFRESH_TOKEN');
    expect(yaml).not.toContain('IMAGE_BASE_URL');
  });

  // ─────────────────────────────────────────────
  // Test: Blotato account ID vars
  // ─────────────────────────────────────────────
  it('test_blotato_account_id_vars', () => {
    expect(yaml).toContain('BLOTATO_ACCOUNT_ID_EN');
    expect(yaml).toContain('BLOTATO_ACCOUNT_ID_JA');
    expect(yaml).toContain('vars.BLOTATO_ACCOUNT_ID_EN');
    expect(yaml).toContain('vars.BLOTATO_ACCOUNT_ID_JA');
  });

  // ─────────────────────────────────────────────
  // Test #20: concurrency exclusion
  // ─────────────────────────────────────────────
  it('test_workflow_has_concurrency_group', () => {
    expect(yaml).toContain('concurrency:');
    expect(yaml).toContain('group: tiktok-post');
    expect(yaml).toContain('cancel-in-progress: false');
  });

  // ─────────────────────────────────────────────
  // Test #21/#22: push conflict retry (MAX_RETRIES=3)
  // ─────────────────────────────────────────────
  it('test_push_retry_logic_exists', () => {
    expect(yaml).toContain('MAX_RETRIES=3');
    expect(yaml).toContain('git pull --rebase');
    expect(yaml).toContain('exit 1');
  });

  // ─────────────────────────────────────────────
  // Test #32: 2-stage push (reserve + post)
  // ─────────────────────────────────────────────
  it('test_two_stage_push', () => {
    expect(yaml).toContain('Stage 1: Reserve in_flight');
    expect(yaml).toContain('Stage 1: Push reservation');
    expect(yaml).toContain('Stage 2: Post to TikTok via Blotato');
    expect(yaml).toContain('Stage 2: Push tracker update');
  });

  // ─────────────────────────────────────────────
  // Test #37: SHA pinning for major actions
  // ─────────────────────────────────────────────
  it('test_actions_use_sha_pinning', () => {
    const usesLines = yaml.match(/uses:\s+.+/g) ?? [];
    expect(usesLines.length).toBeGreaterThanOrEqual(2);

    for (const line of usesLines) {
      expect(line).toMatch(/@[0-9a-f]{40}/);
    }
  });

  // ─────────────────────────────────────────────
  // Checkout with ref: dev and fetch-depth: 0
  // ─────────────────────────────────────────────
  it('test_checkout_has_ref_dev_and_full_fetch', () => {
    expect(yaml).toContain('ref: dev');
    expect(yaml).toContain('fetch-depth: 0');
  });

  // ─────────────────────────────────────────────
  // Permissions: strictly contents: write only
  // ─────────────────────────────────────────────
  it('test_minimal_permissions', () => {
    const perms = parsed.permissions as Record<string, string>;
    expect(perms).toBeDefined();
    expect(Object.keys(perms)).toEqual(['contents']);
    expect(perms.contents).toBe('write');

    const jobs = parsed.jobs as Record<string, Record<string, unknown>>;
    for (const [, jobDef] of Object.entries(jobs)) {
      expect(jobDef.permissions).toBeUndefined();
    }

    const on = parsed.on as Record<string, unknown>;
    expect(on).not.toHaveProperty('pull_request_target');
  });

  // ─────────────────────────────────────────────
  // npm ci (without --ignore-scripts for sharp compatibility)
  // ─────────────────────────────────────────────
  it('test_npm_ci_without_ignore_scripts', () => {
    expect(yaml).toContain('npm ci');
    expect(yaml).not.toContain('--ignore-scripts');
  });

  // ─────────────────────────────────────────────
  // Image verification step
  // ─────────────────────────────────────────────
  it('test_assets_directory_and_image_verification', () => {
    expect(yaml).toMatch(/No card images found/);
    expect(yaml).toContain('EXPECTED=189');
    expect(yaml).toContain('CardScreenshotGenerator');
  });

  // ─────────────────────────────────────────────
  // timeout-minutes: 10
  // ─────────────────────────────────────────────
  it('test_timeout_minutes', () => {
    const jobs = parsed.jobs as Record<string, Record<string, unknown>>;
    expect(jobs.post['timeout-minutes']).toBe(10);
  });
});
