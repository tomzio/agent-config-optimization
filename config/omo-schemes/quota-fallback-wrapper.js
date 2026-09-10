/**
 * Coding-Plan 配额感知 Provider Wrapper
 * 解决：coding-plan 自定义 provider 返回 429/配额耗尽时，不触发 OpenCode 内部 fallback 机制
 *
 * 原理：拦截 AI SDK 的 generate 请求，检测 429 或特定错误码，抛出可重试错误触发 fallback
 * 用法：在 opencode.json 的 provider.options 中引入此 wrapper
 */

const { createOpenAICompatible } = require("@ai-sdk/openai-compatible");

// 需要监控的错误特征（根据实际 API 响应调整）
const QUOTA_EXHAUSTED_PATTERNS = [
  /quota.*exhausted/i,
  /insufficient.*quota/i,
  /rate.*limit.*exceeded/i,
  /429/,
  /billing.*limit/i,
  /credit.*exhausted/i,
];

function isQuotaError(error) {
  if (!error) return false;
  const msg = error.message || error.toString();
  const status = error.statusCode || error.status || error.response?.status;
  return (
    status === 429 ||
    QUOTA_EXHAUSTED_PATTERNS.some((p) => p.test(msg))
  );
}

function createQuotaAwareProvider(baseProvider) {
  const originalGenerate = baseProvider.languageModel?.generate;
  const originalStream = baseProvider.languageModel?.stream;

  if (originalGenerate) {
    baseProvider.languageModel.generate = async function (...args) {
      try {
        return await originalGenerate.apply(this, args);
      } catch (error) {
        if (isQuotaError(error)) {
          // 抛出标准的可重试错误，触发 OpenCode 内部 fallback
          const retryError = new Error("QUOTA_EXHAUSTED: Provider quota exhausted, triggering fallback");
          retryError.retryable = true;
          retryError.code = "QUOTA_EXHAUSTED";
          throw retryError;
        }
        throw error;
      }
    };
  }

  if (originalStream) {
    baseProvider.languageModel.stream = async function (...args) {
      try {
        return await originalStream.apply(this, args);
      } catch (error) {
        if (isQuotaError(error)) {
          const retryError = new Error("QUOTA_EXHAUSTED: Provider quota exhausted, triggering fallback");
          retryError.retryable = true;
          retryError.code = "QUOTA_EXHAUSTED";
          throw retryError;
        }
        throw error;
      }
    };
  }

  return baseProvider;
}

// 导出创建函数，供 opencode.json 引用
module.exports = { createQuotaAwareProvider, isQuotaError };

/*
// === 使用示例：在 opencode.json 中配置 ===
// 1. 将此文件放在 ~/.config/opencode/quota-wrapper.js
// 2. 修改 coding-plan provider 配置：
{
  "provider": {
    "coding-plan": {
      "npm": "@ai-sdk/openai-compatible",
      "options": {
        "apiKey": "ark-xxx",
        "baseURL": "https://ark.cn-beijing.volces.com/api/coding/v3",
        "wrapper": "./quota-wrapper.js"  // 自定义字段，需 OpenCode 支持
      }
    }
  }
}
// 3. 或通过环境变量注入：export OPENCODE_PROVIDER_WRAPPER=./quota-wrapper.js
*/