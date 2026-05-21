import { callLLM } from '../../../lib/llm.js';

/**
 * 苦しみ検出結果に基づいてNudge下書きを生成
 *
 * Input: { detections: Array<{text, severity, problemType}> }
 * Output: { nudgeContent: string, targetProblemType: string, severity: number }
 */
export async function executeDraftNudge({ input }) {
  const detections = input.detections || [];
  const topDetection = detections.sort((a, b) => (b.severity || 0) - (a.severity || 0))[0];

  if (!topDetection) {
    return { output: { nudgeContent: null, skipped: true }, events: [] };
  }

  const nudgeContent = await callLLM(`以下の苦しみに対する Nudge メッセージ（通知文）を生成:
苦しみ: "${topDetection.text}"
種別: ${topDetection.problemType}
重要度: ${topDetection.severity}

ルール:
- 責めない、共感するトーン
- 小さすぎるステップを提案
- 50文字以内`);

  return {
    output: {
      nudgeContent,
      targetProblemType: topDetection.problemType,
      severity: topDetection.severity
    },
    events: []
  };
}
