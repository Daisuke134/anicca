// ★ Mem0テレメトリーは server.js の先頭で無効化済み
// ESモジュールでは import より前に環境変数を設定する必要があるため

import baseLogger from '../../utils/logger.js';
import { MemoryClient } from 'mem0ai';
// OSS version is loaded dynamically to avoid peer dependency issues
// (mem0ai/oss requires ollama, anthropic, etc. at import time)

// mem0 SDK:
// - OSS:      import { Memory } from "mem0ai/oss";
// - Platform: import { MemoryClient } from "mem0ai";
// Ref:
// - https://docs.mem0.ai/open-source/node-quickstart
// - https://docs.mem0.ai/platform/quickstart

const logger = baseLogger.withContext('Mem0Client');

let singleton = null;

function getMode() {
  return process.env.MEM0_API_KEY ? 'platform' : 'oss';
}

export async function getMem0Client() {
  if (singleton) return singleton;
  singleton = await createMem0Client();
  return singleton;
}

export async function createMem0Client() {
  const mode = getMode();
  if (mode === 'platform') {
    // Platform (hosted) - MemoryClient is default export
    const memory = new MemoryClient({ apiKey: process.env.MEM0_API_KEY });
    logger.info('Initialized mem0 platform client');
    return wrapPlatform(memory);
  }
  // OSS fallback (local-friendly) - dynamically import to avoid peer dep issues
  const { Memory: OSSMemory } = await import('mem0ai/oss');
  const memory = new OSSMemory();
  logger.warn('MEM0_API_KEY is not set; using mem0 OSS mode (local storage)');
  return wrapOSS(memory);
}

// Platform版 (MemoryClient) 用ラッパー
// API: client.add({ messages, user_id, metadata }), client.search(query, { user_id })
function wrapPlatform(client) {
  // テレメトリーエラーを無視するためのラッパー
  // mem0aiのcaptureEventは内部で呼ばれるため、直接ラップできない
  // 代わりに、unhandledRejectionでキャッチする（server.jsで実装）
  
  return {
    async addProfile({ userId, content, metadata = {} }) {
      return addTextPlatform(client, userId, content, { category: 'profile', ...metadata });
    },
    async addBehaviorSummary({ userId, content, metadata = {} }) {
      return addTextPlatform(client, userId, content, { category: 'behavior_summary', ...metadata });
    },
    async addInteraction({ userId, content, metadata = {} }) {
      return addTextPlatform(client, userId, content, { category: 'interaction', ...metadata });
    },
    async addNudgeMeta({ userId, content, metadata = {} }) {
      return addTextPlatform(client, userId, content, { category: 'nudge_meta', ...metadata });
    },

    async search({ userId, query, filters, topK = 3 }) {
      return client.search(query, {
        user_id: userId,
        limit: topK,
        ...(filters ? { filters } : {})
      });
    },

    async getAll({ userId }) {
      return client.getAll({ user_id: userId });
    },
    async update(memoryId, patch) {
      return client.update(memoryId, patch);
    },
    async delete(memoryId) {
      return client.delete(memoryId);
    },
    async deleteAll({ userId, runId }) {
      return client.deleteAll({ user_id: userId, ...(runId ? { run_id: runId } : {}) });
    }
  };
}

async function addTextPlatform(client, userId, content, metadata) {
  // Platform API: client.add(messages, { user_id, metadata })
  // Ref: https://docs.mem0.ai/platform/quickstart
  const messages = [
    { role: 'user', content: String(content || '') }
  ];
  return client.add(messages, { user_id: userId, metadata });
}

// OSS版 (Memory) 用ラッパー
// API: memory.add(messages, { userId, metadata }), memory.search(query, { userId })
function wrapOSS(memory) {
  return {
    async addProfile({ userId, content, metadata = {} }) {
      return addTextOSS(memory, userId, content, { category: 'profile', ...metadata });
    },
    async addBehaviorSummary({ userId, content, metadata = {} }) {
      return addTextOSS(memory, userId, content, { category: 'behavior_summary', ...metadata });
    },
    async addInteraction({ userId, content, metadata = {} }) {
      return addTextOSS(memory, userId, content, { category: 'interaction', ...metadata });
    },
    async addNudgeMeta({ userId, content, metadata = {} }) {
      return addTextOSS(memory, userId, content, { category: 'nudge_meta', ...metadata });
    },

    async search({ userId, query, filters, topK = 3, rerank = true, includeVectors = false }) {
      return memory.search(query, {
        userId,
        topK,
        rerank,
        includeVectors,
        ...(filters ? { filters } : {})
      });
    },

    async getAll({ userId }) {
      return memory.getAll({ userId });
    },
    async update(memoryId, patch) {
      return memory.update(memoryId, patch);
    },
    async delete(memoryId) {
      return memory.delete(memoryId);
    },
    async deleteAll({ userId, runId }) {
      return memory.deleteAll({ userId, ...(runId ? { runId } : {}) });
    }
  };
}

async function addTextOSS(memory, userId, content, metadata) {
  const messages = [
    { role: 'user', content: String(content || '') }
  ];
  return memory.add(messages, { userId, metadata });
}

