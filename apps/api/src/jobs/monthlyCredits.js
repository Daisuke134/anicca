import { query } from '../lib/db.js';
import baseLogger from '../utils/logger.js';
import { grantMinutes, VC_CURRENCY_CODE } from '../services/revenuecat/virtualCurrency.js';
const logger = baseLogger.withContext('MonthlyCredits');
const FREE_MIN = 30;
const PRO_MIN = 300;

function monthStartUTC(d = new Date()) {
  const y = d.getUTCFullYear();
  const m = d.getUTCMonth();
  return new Date(Date.UTC(y, m, 1));
}

export async function runMonthlyCredits(now = new Date()) {
  const monthDate = monthStartUTC(now);
  const monthISO = monthDate.toISOString().slice(0, 10); // YYYY-MM-DD

  // 1) 無料枠付与（当月まだ未実行のユーザーへ）
  const freeTargets = await query(
    `select user_id
     from user_subscriptions
     where coalesce(plan,'free') = 'free'
       and not exists (
         select 1 from monthly_vc_grants
         where user_id = user_subscriptions.user_id
           and grant_month = $1::date and reason = 'free'
       )`,
    [monthISO]
  );
  let freeGrantedCount = 0;

  for (const row of freeTargets.rows) {
    try {
      await grantMinutes({
        appUserId: row.user_id,
        minutes: FREE_MIN,
        currency: VC_CURRENCY_CODE,
        context: { month: monthISO, reason: 'free' }
      });
      await query(
        `insert into monthly_vc_grants(user_id, grant_month, reason, minutes)
         values ($1,$2,'free',$3)`,
        [row.user_id, monthISO, FREE_MIN]
      );
      freeGrantedCount += 1;
    } catch (error) {
      logger.error('Monthly credits grant failed', {
        userId: row.user_id,
        reason: 'free',
        error: error.message
      });
    }
  }

  // 2) 年額アクティブ付与（製品IDでannualを判定。RC payloadに含まれる）
  const annualTargets = await query(
    `select user_id
     from user_subscriptions
     where plan = 'pro'
       and entitlement_source = 'revenuecat'
       and (entitlement_payload->>'product_identifier') = 'ai.anicca.app.ios.annual'
       and (current_period_end is null or current_period_end > timezone('utc', now()))
       and not exists (
         select 1 from monthly_vc_grants
         where user_id = user_subscriptions.user_id
           and grant_month = $1::date and reason = 'annual'
       )`,
    [monthISO]
  );
  let annualGrantedCount = 0;

  for (const row of annualTargets.rows) {
    try {
      await grantMinutes({
        appUserId: row.user_id,
        minutes: PRO_MIN,
        currency: VC_CURRENCY_CODE,
        context: { month: monthISO, reason: 'annual' }
      });
      await query(
        `insert into monthly_vc_grants(user_id, grant_month, reason, minutes)
         values ($1,$2,'annual',$3)`,
        [row.user_id, monthISO, PRO_MIN]
      );
      annualGrantedCount += 1;
    } catch (error) {
      logger.error('Monthly credits grant failed', {
        userId: row.user_id,
        reason: 'annual',
        error: error.message
      });
    }
  }

  logger.info('Monthly credits done', {
    freeGranted: freeGrantedCount,
    annualGranted: annualGrantedCount,
    monthISO
  });
}

