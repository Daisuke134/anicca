/**
 * ロギングシステム
 * 
 * console.logの代替として使用する統一的なロギングユーティリティ
 * レベル別ログ出力、タイムスタンプ、環境別制御を提供
 */

import { IS_PRODUCTION, DEBUG_CONFIG } from '../config/environment.js';

// ログレベル定義
const LOG_LEVELS = {
  ERROR: 0,
  WARN: 1,
  INFO: 2,
  DEBUG: 3
};

// 現在のログレベルを環境から取得
const getCurrentLogLevel = () => {
  const level = DEBUG_CONFIG.LOG_LEVEL?.toUpperCase();
  return LOG_LEVELS[level] ?? LOG_LEVELS.INFO;
};

// 色定義（ANSIエスケープコード）
const COLORS = {
  ERROR: '\x1b[31m', // 赤
  WARN: '\x1b[33m',  // 黄
  INFO: '\x1b[36m',  // シアン
  DEBUG: '\x1b[90m', // グレー
  RESET: '\x1b[0m'   // リセット
};

// エモジプレフィックス
const EMOJI_PREFIX = {
  ERROR: '❌',
  WARN: '⚠️ ',
  INFO: '✅',
  DEBUG: '🔍'
};

/**
 * ログメッセージをフォーマット
 */
function formatMessage(level, message, ...args) {
  const timestamp = new Date().toISOString();
  const levelStr = level.padEnd(5);
  const emoji = EMOJI_PREFIX[level] || '';
  
  // 本番環境では色なし、開発環境では色付き
  if (IS_PRODUCTION) {
    return [`[${timestamp}] [${levelStr}] ${emoji} ${message}`, ...args];
  } else {
    const color = COLORS[level] || COLORS.RESET;
    return [`${color}[${timestamp}] [${levelStr}] ${emoji} ${message}${COLORS.RESET}`, ...args];
  }
}

/**
 * ログを出力するかどうかを判定
 */
function shouldLog(level) {
  const currentLevel = getCurrentLogLevel();
  return LOG_LEVELS[level] <= currentLevel;
}

/**
 * Loggerクラス
 * 
 * 使用例:
 * ```js
 * import logger from './utils/logger.js';
 * 
 * logger.info('Server started on port', 3000);
 * logger.error('Failed to connect to database', error);
 * logger.debug('Debug information', { data });
 * ```
 */
class Logger {
  constructor(context = '') {
    this.context = context;
  }
  
  /**
   * コンテキスト付きロガーを作成
   * @param {string} context - ログのコンテキスト（例: 'API', 'Database'）
   */
  withContext(context) {
    return new Logger(context);
  }
  
  /**
   * メッセージにコンテキストを追加
   */
  _addContext(message) {
    return this.context ? `[${this.context}] ${message}` : message;
  }
  
  /**
   * エラーログ出力
   */
  error(message, ...args) {
    if (shouldLog('ERROR')) {
      console.error(...formatMessage('ERROR', this._addContext(message), ...args));
    }
  }
  
  /**
   * 警告ログ出力
   */
  warn(message, ...args) {
    if (shouldLog('WARN')) {
      console.warn(...formatMessage('WARN', this._addContext(message), ...args));
    }
  }
  
  /**
   * 情報ログ出力
   */
  info(message, ...args) {
    if (shouldLog('INFO')) {
      console.log(...formatMessage('INFO', this._addContext(message), ...args));
    }
  }
  
  /**
   * デバッグログ出力
   */
  debug(message, ...args) {
    if (shouldLog('DEBUG')) {
      console.log(...formatMessage('DEBUG', this._addContext(message), ...args));
    }
  }
  
  /**
   * console.log互換メソッド（移行を容易にするため）
   */
  log(message, ...args) {
    this.info(message, ...args);
  }
}

// デフォルトロガーインスタンス
const defaultLogger = new Logger();

// console.logからの移行を簡単にするためのヘルパー関数
export const log = defaultLogger.log.bind(defaultLogger);
export const info = defaultLogger.info.bind(defaultLogger);
export const warn = defaultLogger.warn.bind(defaultLogger);
export const error = defaultLogger.error.bind(defaultLogger);
export const debug = defaultLogger.debug.bind(defaultLogger);

// デフォルトエクスポート
export default defaultLogger;

/**
 * グローバルconsole.logを置き換える（オプション）
 * 
 * 使用例:
 * ```js
 * import { replaceConsoleLog } from './utils/logger.js';
 * replaceConsoleLog(); // これ以降のconsole.logは自動的にloggerを使用
 * ```
 */
export function replaceConsoleLog() {
  const originalLog = console.log;
  const originalError = console.error;
  const originalWarn = console.warn;
  
  console.log = (...args) => defaultLogger.info(...args);
  console.error = (...args) => defaultLogger.error(...args);
  console.warn = (...args) => defaultLogger.warn(...args);
  
  // 元のconsole関数を保持（必要な場合のため）
  console._originalLog = originalLog;
  console._originalError = originalError;
  console._originalWarn = originalWarn;
}