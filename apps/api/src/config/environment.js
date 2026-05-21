/**
 * 環境変数の統一管理
 *
 * iOS API サーバーの設定を一箇所に集約
 */

// 環境判定
export const NODE_ENV = process.env.NODE_ENV || 'development';
export const IS_PRODUCTION = NODE_ENV === 'production';
export const IS_DEVELOPMENT = NODE_ENV === 'development';

// プロキシサーバー設定（RAILWAY_PUBLIC_DOMAIN から自動生成可能）
const rawProxyUrl = process.env.PROXY_BASE_URL
  || (process.env.RAILWAY_PUBLIC_DOMAIN ? `https://${process.env.RAILWAY_PUBLIC_DOMAIN}` : '');
export const PROXY_BASE_URL = rawProxyUrl;

const IS_CRON_JOB = !!process.env.CRON_MODE;
if (IS_PRODUCTION && !PROXY_BASE_URL && !IS_CRON_JOB) {
  console.error('⚠️ PROXY_BASE_URL is not set in production. Set PROXY_BASE_URL or ensure RAILWAY_PUBLIC_DOMAIN is available.');
}

// サーバー設定
export const SERVER_CONFIG = {
  IS_RAILWAY: !!process.env.RAILWAY_ENVIRONMENT,
  PORT: process.env.PORT || 8080,
  PUBLIC_DOMAIN: process.env.RAILWAY_PUBLIC_DOMAIN
};

// API Keys（存在チェックのみ）
export const API_KEYS = {
  OPENAI: !!process.env.OPENAI_API_KEY,
  MEM0: !!process.env.MEM0_API_KEY
};

// 課金関連設定（RevenueCat のみ）
export const BILLING_CONFIG = {
  REVENUECAT_PROJECT_ID: process.env.REVENUECAT_PROJECT_ID || '',
  REVENUECAT_REST_API_KEY: process.env.REVENUECAT_REST_API_KEY || '',
  REVENUECAT_WEBHOOK_SECRET: process.env.REVENUECAT_WEBHOOK_SECRET || '',
  REVENUECAT_ENTITLEMENT_ID: process.env.REVENUECAT_ENTITLEMENT_ID || 'pro',
  REVENUECAT_PAYWALL_ID: process.env.REVENUECAT_PAYWALL_ID || '',
  REVENUECAT_CUSTOMER_CENTER_ID: process.env.REVENUECAT_CUSTOMER_CENTER_ID || '',
  REVENUECAT_VC_CODE: process.env.REVENUECAT_VC_CODE || ''
};

// ディレクトリ設定
export const DIRECTORIES = {
  TEMP_BASE: SERVER_CONFIG.IS_RAILWAY
    ? '/tmp'
    : process.env.TEMP_DIR || './tmp'
};

// デバッグ設定
export const DEBUG_CONFIG = {
  DEBUG: process.env.DEBUG === 'true',
  LOG_LEVEL: process.env.LOG_LEVEL || (IS_PRODUCTION ? 'info' : 'debug')
};

// 環境変数の検証
export function validateEnvironment() {
  const warnings = [];

  if (IS_PRODUCTION) {
    if (!BILLING_CONFIG.REVENUECAT_PROJECT_ID || !BILLING_CONFIG.REVENUECAT_REST_API_KEY) {
      warnings.push('RevenueCat project / REST API key are not set');
    }
    if (!BILLING_CONFIG.REVENUECAT_WEBHOOK_SECRET) {
      warnings.push('REVENUECAT_WEBHOOK_SECRET is not set');
    }
    if (!process.env.PROXY_GUEST_JWT_SECRET) {
      warnings.push('PROXY_GUEST_JWT_SECRET is not set');
    }
  }

  if (!API_KEYS.OPENAI) {
    warnings.push('OPENAI_API_KEY must be set');
  }

  if (!API_KEYS.MEM0) {
    warnings.push('MEM0_API_KEY is not set');
  }

  return warnings;
}

// 環境情報をログ出力（デバッグ用）
export function logEnvironment() {
  console.log('🔧 Environment Configuration:');
  console.log(`  - NODE_ENV: ${NODE_ENV}`);
  console.log(`  - PROXY_BASE_URL: ${PROXY_BASE_URL}`);
  console.log(`  - Server: ${SERVER_CONFIG.IS_RAILWAY ? 'Railway' : 'Local'}`);
  console.log(`  - RC VC code: ${BILLING_CONFIG.REVENUECAT_VC_CODE || 'unset'}`);

  const warnings = validateEnvironment();
  if (warnings.length > 0) {
    console.warn('⚠️ Environment warnings:');
    warnings.forEach(warning => console.warn(`  - ${warning}`));
  }
}
